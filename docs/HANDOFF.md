# Handoff — crypto-trading-bot

Documento de transferencia de contexto. Léelo si vas a continuar este proyecto y no estabas en la sesión que lo construyó.

---

## 1. De dónde sale este repo

El usuario (ajalvarez89) pidió "una aplicación que opere por mí en Binance, con UI de P&L diario/semanal/mensual, posiciones abiertas, alimentado por modelos de IA que se retroalimenten con tendencias y noticias, y que ejecute localmente para ahorrar infra". Quería **garantía de ganancias** — primera advertencia explícita en la conversación: ningún sistema garantiza eso, y el plan se construyó con esa honestidad por delante.

### Decisiones tomadas con el usuario antes de codear

| Pregunta | Respuesta del usuario |
|---|---|
| Stack | **Phoenix híbrido (Phoenix/Elixir + Python + Next.js)** sobre Next.js solo o Python puro |
| Ubicación | **Repo separado** `ajalvarez89/crypto-trading-bot` (privado). El código se desarrolló en una rama del repo de perfil `ajalvarez89/ajalvarez89` por restricción de scope; debe migrarse |
| Modo trading | **Paper + capital real limitado** (cap inicial 200 USDT, canary 50 USDT antes) |
| Nivel ML V1 | **ML avanzado desde V1** — el usuario pidió ensemble + sentimiento desde la primera versión |

### Aprendizajes de los videos del usuario que dieron forma al diseño

El usuario pasó dos transcripciones de YouTube (la tercera no la pudo abrir). Resumen y cómo se aplicaron:

**Video 1 — Polymarket copy-trading bot con Claude Code + Bullpen Klee** (no es Binance, son mercados de predicción). Lo aplicable:
- **Pre-flight check** explícito antes de operar → `scripts/preflight.sh`.
- **Aprobación previa de órdenes** (`bullpen polymarket approve yes`) → flag `orders_approved` en SQLite con TTL 24h. Sin esa flag activa, `OrderRouter` rechaza todo.
- **Logging JSON estructurado** por trade → ya cubierto por `audit_log` + Redis Streams.
- **Auto-redeem** cuando un mercado se resuelve → en Binance no aplica igual; equivale a `paper_broker.py` cerrando la posición cuando precio toca SL/TP, ya implementado.
- **Disclaimer del autor del video**: "tu win rate = el de los traders que copias" — refuerza que no hay magia. Replicado en disclaimers.md.

**Video 2 — MetaTrader 5 con Claude (MQL5, Forex/Oro)**. Lo aplicable:
- **Estrategia "MultiSignal"** con 4 indicadores (EMA50/200 + RSI 65/35 + MACD + ATR) → reemplazó el MA crossover simple del plan original. Es el `BaseStrategy` por defecto en `apps/trading_engine/src/trading_engine/strategies/multi_signal.py`.
- **Stops dinámicos por ATR** (1.5·ATR stop, 3·ATR take-profit, RR 1:2) → en `risk/manager.py` y `multi_signal.py`.
- **Drawdown semaforizado** (🟢 <20% / 🟠 20-30% / 🔴 >30%) como criterio de promoción → en `apps/ml_service/src/ml_service/backtest/runner.py::_compute_metrics`.
- **Optimización en 2 etapas con cap de 3 grados de libertad** para evitar overfit. Diseñado pero no implementado: hay TODO en pendientes.
- **Escaneo multi-par** (la estrategia rara vez funciona en todos los mercados) → `scan_pairs()` en `runner.py`.
- **Cuidado con sobreoptimización**: el video mostró un 35.944% con DD inasumible — síntoma claro de overfit. La gate del drawdown band lo bloquea.

---

## 2. Arquitectura final

```
┌─────────────┐   WebSocket    ┌──────────────────┐
│  Next.js 15 │◄── Channels ──►│  Phoenix 1.7     │
│  Dashboard  │                │  (Elixir)        │
└─────────────┘                │  Gateway + WS    │
                               │  SQLite (Ecto)   │
                               └──┬──────────┬────┘
                                  │          │
                          ┌───────▼──┐  ┌────▼─────────┐
                          │  Redis   │  │  audit_log   │
                          │ Streams  │  │  orders, P&L │
                          └─┬──┬───┬─┘  └──────────────┘
                            │  │   │
        ┌───────────────────┘  │   └────────────────────┐
        │                      │                        │
┌───────▼─────────┐  ┌─────────▼──────────┐   ┌────────▼─────────┐
│ trading_engine  │  │     ml_service     │   │  news_collector  │
│ (Python/FastAPI)│  │  (Python/FastAPI)  │   │   (Python)       │
│ Binance client  │  │  Direction class.  │   │  CryptoPanic +   │
│ Risk manager    │  │  Feature store     │   │  lexicon scoring │
│ Paper broker    │  │  (DuckDB)          │   │  → Redis news.*  │
│ Live broker     │  │  Backtester        │   │                  │
│ (gated)         │  │  (vectorised)      │   │                  │
└─────────────────┘  └────────────────────┘   └──────────────────┘
        │
        │  REST + WebSocket
        ▼
   Binance Testnet / Live
```

Reglas de aislamiento (críticas — NO romper):
- API keys de Binance solo en `trading_engine`
- Solo Phoenix y trading_engine escriben SQLite (Phoenix dueño del schema)
- `ml_service` solo lee/escribe DuckDB
- `web` solo habla con Phoenix, nunca con Python ni Binance directo

---

## 3. Cronología por fases (cómo se construyó)

Cada fase = un commit en `claude/crypto-trading-bot-app-W1MEp`:

| Commit | Fase | Resumen |
|---|---|---|
| `01adda2` | **0** | Scaffold monorepo, Docker Compose, 5 servicios con `/health`, JSON Schemas, ADRs, scripts de seguridad, `config/risk.yml` |
| `64bbf3e` | **1** | WS Binance multiplex → Redis Streams → Phoenix Channels → Next.js + TradingView Lightweight Charts v5; `seed_historical.py` real (parquet + DuckDB view) |
| `2860988` | **2** | MultiSignal real, paper broker con slippage+fees, RiskManager full (kill-switch + drawdown + cooldown + rate limit), P&L diario/semanal/mensual, AdminBar con kill switch UI |
| `58a1c8f` | **3** | Feature engineering pandas-ta, `BaselineDirectionModel` (HistGradientBoosting), registry champion/challenger, `MLConfirmedStrategy` (filtra señales de MultiSignal con prob ML) |
| `4e4e7dc` | **4** | CryptoPanic poller, dedupe, lexicon sentiment scorer, NewsConsumer (Phoenix), NewsChannel WS, NewsFeed UI, **SentimentFilter** que bloquea trades opuestos al consenso de noticias |
| `fed4b2b` | **5** | `max_open_positions_per_symbol`, `DirectionEnsemble` (avg de 2 versiones), CopyTradingPoller opt-in con cap de notional |
| `e3e83e1` | **6** | Vector backtester (Sharpe/Sortino/PF/DD/winrate), drawdown semaforizado, multi-pair scan, `/backtests` UI, `make backtest` |
| `42042aa` | **7** | LiveBroker real (gated), Telegram alerting opcional, Grafana stub. Default sigue paper |

8 commits, 186 archivos.

---

## 4. Convenciones e invariantes a respetar

- **Modos**: `testnet | paper | live`. Por defecto testnet. Live requiere TODOS estos a la vez:
  1. `TRADING_MODE=live` en `.env`
  2. `I_UNDERSTAND_RISK=yes` en `.env`
  3. `bash scripts/enable_live.sh` (gate interactivo: pide tipear "LIVE" y reconfirmar el cap en USDT)
  4. `make up-live` (compose override `docker-compose.prod.yml`)
  5. Approval activo (`make approve`)
  6. RiskManager pasa todos los checks
  7. Notional ≤ `LIVE_CAPITAL_CAP_USDT`
- **Drawdown band gate** para promover una estrategia a paper/live: 🟢 <20% en out-of-sample, Sharpe >1.0, profit factor >1.3, ≥30 trades.
- **Sentiment NUNCA abre trades, solo bloquea**.
- **ML NUNCA abre trades sin confirmación de MultiSignal**.
- **Risk per trade**: 1% del equity (configurable). Stop ATR ×1.5, TP ATR ×3.
- **Audit log es insert-only**. Cada acción (system, user, strategy_id) deja huella.

---

## 5. Pendiente / próximos pasos sugeridos

Ordenado por valor:

### A. Sustituir el classifier baseline por NeuralForecast (N-HiTS + N-BEATSx)
El plan original especificaba esto pero por simplicidad de deps Phase 3 quedó con `HistGradientBoostingClassifier` de sklearn. Pasos:
1. Añadir `neuralforecast`, `torch`, `pytorch-lightning` al `apps/ml_service/pyproject.toml` (extra `[ml]` ya existe).
2. Crear `apps/ml_service/src/ml_service/forecasting/nhits.py` que implemente la misma interfaz pública que `BaselineDirectionModel.fit/save/load/predict_proba_up`. Usar `NHITS` y `NBEATSx` de NeuralForecast.
3. Walk-forward CV (ya hay un placeholder en `training/`).
4. Cambiar `training/train_baseline.py` o crear `training/train_nhits.py` paralelo.
5. La inferencia ya está parametrizada por `name` en el registry — solo registrar el ensemble como campeón cuando bata al baseline.

### B. Sustituir el lexicon sentiment por FinBERT
1. Añadir `transformers` + un modelo concreto (sugerido: `ProsusAI/finbert` o `burakutf/finetuned-finbert-crypto` mencionado en la investigación).
2. Cargar el modelo en `ml_service`, exponer `/inference/sentiment/score` (ya existe el stub).
3. Reescribir el path de scoring: `news_collector` deja de hacer scoring inline y llama al `ml_service` (HTTP). El `news_collector` actual ya publica `news.raw` además de `news.scored` — el consumer puede ser un job dentro de `ml_service` que lea raw, scoree con FinBERT, y publique scored.

### C. Walk-forward + Optuna en backtester
Falta:
1. Walk-forward CV en `runner.py` (ahora hace un solo run con todo el histórico).
2. Optimización de hiperparámetros con Optuna respetando el cap de 3 grados de libertad (lección Video 2). Sugerido: optimizar `(ema_fast, ema_slow, stop_atr_mult)` en una etapa, fijarlos, optimizar `risk_per_trade_pct` en otra.
3. Reporte HTML interactivo (curva de equity + distribución de trades). Hoy se emite JSON por par.

### D. Validación de filtros de Binance en LiveBroker
`live_broker.py::_round_qty` formatea con 6 decimales y deja que Binance rechace. Antes de cualquier producción real:
1. Cargar `exchangeInfo` al startup, cachear `LOT_SIZE.stepSize`, `MIN_NOTIONAL.minNotional`, `PRICE_FILTER.tickSize` por símbolo.
2. Redondear qty/price a `stepSize`/`tickSize` matemáticamente (no string format).
3. Si `qty * price < minNotional`, rechazar y loguear, no enviar a Binance.

### E. Tests E2E
Hoy hay tests unitarios decentes (4 suites). Falta:
1. Playwright contra el dashboard (botón Approve, Kill switch, render del chart).
2. Integration test: arrancar Compose, esperar 30s, verificar via REST que llegan klines y que el WS emite ticks.
3. Soak test 14 días testnet documentado (`docs/runbook.md` ya tiene la receta).

### F. Phase-7 dashboards de Grafana
`infra/grafana/README.md` lista 3 sugeridos: bot_overview, risk_health, ml_health. Esquema todavía sin escribir.

### G. Migración con conservación del schema SQLite
Phoenix corre las migraciones en cada arranque. Cuando el usuario suba esto a una máquina nueva, los archivos parquet/sqlite en `data/` no migran automáticamente (gitignored). Documentar un `make backup` / `make restore` ayudaría.

### H. Ajustes de la reglas de la estrategia
La MultiSignal de Fase 2 puede emitir señales muy seguidas si hay choppy markets. Sugerencia: añadir un cooldown post-trade (e.g. no abrir nueva posición en mismo símbolo durante N velas tras cierre). Probable que el backtest lo haga visible.

---

## 6. Gotchas y cosas raras que aprendí en el camino

### File-overwrite race en la sesión anterior
En Phase 2 hubo dos archivos donde mi `Edit/Write` parecía aplicarse correctamente (la respuesta del tool decía "updated"), pero al commitear no entraban en el diff:
- `apps/phoenix_app/lib/phoenix_app/bridges/trading_engine_client.ex`
- `apps/phoenix_app/lib/phoenix_app_web/controllers/admin_controller.ex`

Resultado: los stubs de Phase 0 sobrevivieron hasta Phase 6, donde tuve que reescribirlos. Si haces cambios críticos, **verifica con `git diff HEAD <file>` antes de commitear** y revisa `git log -- <file>` para confirmar que el último commit que tocó el archivo es el que esperas.

### Scope de sesión bloquea cross-repo
Las sesiones de Claude Code (web) tienen scope estricto vía proxy local. La sesión que generó este código solo podía pushear a `ajalvarez89/ajalvarez89`. Migrar a `ajalvarez89/crypto-trading-bot` requirió Codespaces o un segundo chat scopeado al repo nuevo. **Si te pasa lo mismo, no insistas — cambia de sesión.**

### YouTube WebFetch bloqueado
El sandbox bloquea WebFetch directo a youtube.com (403). La transcripción tiene que pasarla el usuario manualmente o usar un servicio externo de transcripción. El usuario pasó 2 de 3 transcripciones; la tercera nunca llegó.

### El video 1 era de Polymarket, no Binance
La primera transcripción era un copy-trading bot en Polymarket (mercados de predicción binarios). NO es 1:1 con Binance (spot/futures con apalancamiento). Lo que se extrajo fue el patrón conceptual (pre-flight, approve, copy trading), no la lógica.

### CryptoPanic free tier
El plan free tiene rate limit. El poller default está en 60s. Si se reduce mucho, puede haber 429. Honor el `Retry-After` si aparece.

### Binance Futures Copy Trading endpoint
`/bapi/futures/v1/public/future/leaderboard/getOtherPosition` es un endpoint público pero **no es API oficial**. Puede cambiar de schema sin aviso. Defensive parsing en `copy_trading.py` está al mínimo.

---

## 7. Cómo verificar que todo sigue funcionando en una sesión nueva

```bash
# 1. clonar (en repo nuevo)
git clone https://github.com/ajalvarez89/crypto-trading-bot.git
cd crypto-trading-bot

# 2. setup
cp .env.example .env
# editar .env: BINANCE_API_KEY/SECRET de testnet (https://testnet.binance.vision)
# opcional: CRYPTOPANIC_API_KEY
chmod 600 .env

# 3. preflight + arranque
make preflight       # debe terminar "Preflight OK"
make up              # 6 contenedores levantan
make status          # 5 servicios reportan 200

# 4. dashboard
# abrir http://localhost:3000
# debe mostrar: ConnectionBadge=Connected, MarketView con velas live, ServiceStatusGrid verde

# 5. ML offline
make seed            # 90 días BTCUSDT/ETHUSDT/SOLUSDT a DuckDB
make train           # entrena baseline + lo promueve

# 6. orquestación trading
make approve         # autoriza órdenes 24h
# espera a que MultiSignal emita una señal en testnet (puede tardar horas)
# o fuerza paper mode con cualquier señal generada manualmente vía /signals (no expuesto pero fácil de añadir)

# 7. backtests
make backtest        # produce data/backtests/<ts>/summary.json
# abrir http://localhost:3000/backtests
```

---

## 8. Disclaimer recordatorio (no quitar nunca)

> Ningún sistema de trading puede garantizar ganancias. El trading de criptomonedas conlleva riesgo real de pérdida total del capital. Este software es experimental, AS-IS, sin garantías. El usuario es responsable de su capital, del cumplimiento regulatorio en su jurisdicción, y de monitorear continuamente el sistema cuando opere con dinero real.

Si en algún punto el proyecto pivota a "vender este bot" o "ofrecer señales", **revisa la regulación aplicable antes** — en muchas jurisdicciones eso es asesoramiento financiero regulado.
