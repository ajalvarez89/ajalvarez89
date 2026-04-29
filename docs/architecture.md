# Architecture

## Overview

Phoenix-centric híbrido. Cinco servicios orquestados por Docker Compose, comunicándose vía Redis Streams (eventos) + HTTP (RPC) + Phoenix Channels (UI).

## Services

| Service | Lang | Port | Responsibility |
|---|---|---|---|
| `phoenix_app` | Elixir 1.16 / Phoenix 1.7 | 4000 | Gateway HTTP + WebSocket Channels, persistencia transaccional (SQLite/Ecto), broadcast a UI, P&L, audit log, autenticación local |
| `trading_engine` | Python 3.11 / FastAPI | 8001 | **Único punto que toca Binance**. Cliente REST/WS, risk manager, paper/live broker, kill switch |
| `ml_service` | Python 3.11 / FastAPI | 8002 | Forecasting (NeuralForecast), sentiment (FinBERT), feature store (DuckDB), training/registry |
| `news_collector` | Python 3.11 | 8003 | Polling de CryptoPanic/NewsAPI, normalización, dedupe, publica a Redis |
| `web` | Next.js 15 | 3000 | Dashboard, charts (TradingView), control kill switch, configuración |
| `redis` | Redis 7 | 6379 | Pub/sub via Streams (`market.ticks`, `signals`, `news.raw`, `news.scored`, `orders.events`) |

## Isolation rules

- **API keys de Binance solo viven en `trading_engine`** (env vars, IP whitelist, sin permisos de Withdraw).
- Solo `phoenix_app` y `trading_engine` escriben SQLite. Phoenix es dueño del schema (Ecto migrations). Python escribe en tablas concretas (`orders`, `trades`, `audit_log`) sin migrar.
- `ml_service` solo lee/escribe DuckDB; nunca toca SQLite ni Binance.
- `web` solo habla con `phoenix_app` (HTTP + WS). Nunca con Python o Binance directamente.

## Communication patterns

- **Eventos pub/sub**: Redis Streams. Productores hacen `XADD key MAXLEN ~ N entries...`. Consumidores con `XREADGROUP` para entrega at-least-once.
- **RPC**: HTTP/JSON entre Phoenix y Python (httpx). Uvicorn maneja concurrencia async.
- **Frontend ↔ Phoenix**: Phoenix Channels sobre WebSocket (cliente JS oficial `phoenix` npm).

## Data flows

### Market tick (Phase 1+)
```
Binance WS → trading_engine.ws_streams
          → Redis Stream "market.ticks"
          → phoenix_app.bridges.redis_consumer
          → ETS tick_cache + Phoenix.PubSub.broadcast("market:btcusdt")
          → MarketChannel push("tick", payload)
          → Next.js Zustand store → CandlestickChart
          
ml_service en paralelo consume "market.ticks" para features online.
```

### Trading decision (Phase 3+)
```
ml_service: cada N ticks o ventanas
  - lee features (technical + sentiment) de DuckDB
  - infiere con N-HiTS ensemble
  - publica TradingSignal en Redis Stream "signals"

trading_engine consumer "signals":
  - risk_manager.check_signal(signal)
      * kill switch?
      * size <= max_position_pct * equity
      * stop_loss obligatorio
      * daily drawdown < limit
      * circuit breakers
  - paper_broker o live_broker → ejecutar orden
  - persistir order/fill en SQLite + audit_log
  - publicar OrderEvent en "orders.events"
  - phoenix_app broadcast a TradingChannel → UI
```

### News & sentiment (Phase 4+)
```
news_collector (cada 60s) → CryptoPanic/NewsAPI
                          → normalize + dedupe
                          → Redis Stream "news.raw"

ml_service consumer "news.raw":
  - finbert_scorer(text) → {pos, neg, neu, label}
  - escribe en DuckDB.feature_store.news_sentiment
  - publica "news.scored" para feed de UI
  - feature pipeline genera ventanas agregadas
```

## Strategies

Implementan `BaseStrategy.generate_signal(features) -> TradingSignal | None`:

- **MultiSignal** (Phase 2): EMA 50/200 + RSI 65/35 + MACD + ATR-based stops/TP
- **MLSignal** (Phase 3+): N-HiTS direction_prob + threshold + confirmación MultiSignal
- **CopyTrading** (Phase 5+, opcional): replica top traders de Binance Futures Copy Trading
- **Sentiment** (Phase 4+): filtro direccional, no abre por sentiment solo

## Configuration

- **Modos**: `TRADING_MODE` ∈ {`testnet`, `paper`, `live`}. Default `testnet`.
- **Risk**: `config/risk.yml` define límites duros del risk manager.
- **Pre-flight**: `scripts/preflight.sh` valida config antes de arrancar.
- **Aprobación**: `make approve` requerido cada 24h para autorizar ejecución de órdenes.

## Phases

Ver [README](../README.md) y [Plan completo](../README.md#estado-del-proyecto).
