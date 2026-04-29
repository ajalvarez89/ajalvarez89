# crypto-trading-bot

Sistema de trading automatizado de criptomonedas en Binance con ML/IA, ejecutable localmente.

Stack: **Phoenix/Elixir** (gateway real-time) + **Python/FastAPI** (trading engine + ML + news) + **Next.js 15** (UI) + **Redis** + **SQLite/DuckDB**, todo orquestado por **Docker Compose**.

## ⚠️ Disclaimers (lee antes de continuar)

- **No es asesoramiento financiero.** Software experimental con fines educativos.
- **El trading de criptomonedas conlleva riesgo de pérdida total** del capital. Volatilidad extrema, gaps, riesgo de exchange.
- **Sin garantía de rentabilidad.** Resultados pasados (incluso backtests) no predicen resultados futuros. El overfitting es un riesgo real.
- **Empieza obligatoriamente en Binance Testnet o paper trading.** No pasar a `live` sin al menos 30 días de paper exitoso y revisión manual del audit log.
- **Permisos mínimos en API keys.** Nunca habilitar withdrawals. Activar IP whitelist.
- **Solo capital de riesgo.** Únicamente opera con dinero cuya pérdida total no afecte tu situación financiera.
- **Riesgo técnico.** Bugs, caídas de red, latencia, race conditions y fallos del exchange pueden causar pérdidas.
- **Cumplimiento regulatorio.** Eres responsable de verificar legalidad, impuestos y reporting en tu jurisdicción.
- **Software AS-IS, sin garantías.** Ver [LICENSE](LICENSE).

Documento extendido: [docs/disclaimers.md](docs/disclaimers.md).

---

## Arquitectura

```
┌─────────────┐     WebSocket      ┌──────────────────┐
│  Next.js 15 │ ◄───── Channels ─► │  Phoenix 1.7     │
│  Dashboard  │                    │  (Elixir)        │
└─────────────┘                    │  Gateway + WS    │
                                   │  SQLite (Ecto)   │
                                   └──┬──────────┬────┘
                                      │          │
                              ┌───────▼──┐  ┌────▼─────────┐
                              │  Redis   │  │  audit_log   │
                              │ Streams  │  │  orders, P&L │
                              └─┬──┬───┬─┘  └──────────────┘
                                │  │   │
        ┌───────────────────────┘  │   └────────────────────┐
        │                          │                        │
┌───────▼─────────┐    ┌───────────▼──────────┐   ┌────────▼─────────┐
│ trading_engine  │    │     ml_service       │   │  news_collector  │
│ (Python/FastAPI)│    │  (Python/FastAPI)    │   │   (Python)       │
│ Binance client  │    │  N-HiTS forecasting  │   │  CryptoPanic +   │
│ Risk manager    │    │  FinBERT sentiment   │   │  NewsAPI poller  │
│ Paper/live      │    │  Feature store       │   │  Dedupe + norm   │
│ broker          │    │  (DuckDB)            │   │                  │
└─────────────────┘    └──────────────────────┘   └──────────────────┘
        │
        │  REST + WebSocket
        ▼
   Binance Testnet / Live
```

## Quickstart

### Requisitos
- Docker + Docker Compose
- (opcional para dev local sin Docker) `asdf` con elixir 1.16, erlang 26, python 3.11, node 20
- Cuenta de Binance Testnet: https://testnet.binance.vision

### Setup
```bash
cp .env.example .env
# Editar .env con tus claves de Binance Testnet
chmod 600 .env

make preflight       # Valida config y conectividad
make up              # Levanta todos los servicios en testnet
make logs            # Ver logs
make down            # Detener
```

### Operación
```bash
make approve         # Autoriza ejecución de órdenes (expira en 24h)
make kill            # Kill switch: cancela órdenes y cierra posiciones
make backtest        # Corre backtest con la estrategia activa
```

### URLs locales
- Dashboard: http://localhost:3000
- Phoenix API: http://localhost:4000
- Trading engine: http://localhost:8001/health
- ML service: http://localhost:8002/health
- News collector: http://localhost:8003/health

## Estado del proyecto

**Fase actual: 5 — Multi-par + ensemble ML + risk endurecido + copy trading opcional**

Hoja de ruta: ver [docs/architecture.md](docs/architecture.md).

| Fase | Estado | Descripción |
|---|---|---|
| 0 | Completada | Scaffold + Docker Compose + Testnet read-only |
| 1 | Completada | Ingesta de datos + persistencia + UI velas |
| 2 | Completada | Estrategia MultiSignal + paper + dashboard P&L |
| 3 | Completada | Pipeline ML básico (1 par) |
| 4 | Completada | Noticias + sentimiento |
| 5 | En progreso | Estrategia ML completa + multi-par |
| 6 | Pendiente | Backtesting + optimización |
| 7 | Pendiente | (opcional) Live con capital limitado |

## Documentación

- [Arquitectura](docs/architecture.md)
- [Runbook](docs/runbook.md)
- [Gestión de riesgo](docs/risk-management.md)
- [Pipeline ML](docs/ml-pipeline.md)
- [Disclaimers extendidos](docs/disclaimers.md)
- [ADRs](docs/adr/)

## Licencia

MIT — ver [LICENSE](LICENSE). **Software AS-IS, sin garantías.**
