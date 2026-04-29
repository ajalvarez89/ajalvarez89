# CLAUDE.md

Contexto para sesiones de Claude Code que continúen este proyecto.

## Qué es este repo

Bot local de trading de criptomonedas en Binance, **Phoenix-centric híbrido**: gateway Phoenix/Elixir + microservicios Python (trading_engine, ml_service, news_collector) + Next.js dashboard. Orquestado por Docker Compose.

Estado actual: **fases 0–7 implementadas y commiteadas**. Por defecto corre en testnet con paper broker. Live trading existe pero está detrás de gates manuales (`scripts/enable_live.sh` + `make up-live`).

## Documentos clave para tener en mente

1. **`README.md`** — quickstart, tabla de fases, disclaimers visibles arriba.
2. **`docs/HANDOFF.md`** — narrativa completa de cómo se construyó, qué se aprendió de los videos del usuario, decisiones, gotchas, y trabajo pendiente. **Léelo primero.**
3. **`docs/architecture.md`** — flujos de datos, responsabilidades por servicio, reglas de aislamiento.
4. **`docs/risk-management.md`** — política de riesgo, gates, criterios de promoción de estrategias (drawdown semaforizado).
5. **`docs/disclaimers.md`** — qué riesgos asume el usuario.
6. **`docs/adr/`** — 4 ADRs (Phoenix-centric, paper-trading-mandatory, Redis Streams, SQLite+DuckDB).
7. **Plan original** (no en git): `/root/.claude/plans/necesito-elaborar-un-plan-memoized-falcon.md`. El HANDOFF lo resume; si necesitas más detalle pídelo al usuario.

## Convenciones que ya están establecidas — respétalas

- **Aislamiento de keys**: API keys de Binance solo viven en `trading_engine`. El frontend SOLO habla con Phoenix. `ml_service` SOLO toca DuckDB. Phoenix dueño del schema SQLite (Ecto migrations); Python escribe en tablas concretas sin migrar.
- **Mensajería entre servicios**: Redis Streams (`market.klines`, `market.ticks`, `news.raw`, `news.scored`, `signals`, `orders.events`) con MAXLEN ~ N para retención. Phoenix Channels solo para frontend.
- **Persistencia OLTP** (orders, positions, trades, audit_log, approvals, strategies): SQLite + Ecto / SQLAlchemy. **OLAP** (klines, features, backtests): DuckDB + parquet bajo `data/`.
- **Modos de trading**: `TRADING_MODE` ∈ {`testnet`, `paper`, `live`}. Default testnet. Live requiere `I_UNDERSTAND_RISK=yes` Y `enable_live.sh` Y `make up-live`.
- **Aprobación 24h**: el `OrderRouter` rechaza órdenes sin un row activo en `approvals` (TTL 24h). El usuario lo activa con `make approve` o el botón del dashboard.
- **Estrategia baseline**: `MultiSignalStrategy` (EMA50/200 + RSI 35-65 + MACD + ATR×1.5 stop / ×3 TP). Confluencia obligatoria. El ML filtra encima como confirmación direccional, nunca opera solo.
- **Drawdown semaforizado** para promover estrategias: 🟢 <20% / 🟠 20-30% / 🔴 >30%. Implementado en `apps/ml_service/src/ml_service/backtest/runner.py`.
- **Comments**: por defecto NO. Solo añade comentarios cuando la razón (no el qué) es no-obvia. Sigue las reglas globales del prompt del sistema.

## Cómo arrancar el sistema (verificación rápida)

```bash
cp .env.example .env
# Edita BINANCE_API_KEY/SECRET (testnet keys de testnet.binance.vision)
chmod 600 .env
make preflight        # checks env + conectividad
make up               # levanta los 6 contenedores
make status           # 200 en cada /health
make seed             # 90 días de klines a DuckDB
make train            # baseline classifier + promueve campeón
make approve          # autoriza órdenes 24h
make backtest         # backtest multi-par con drawdown band
```

Dashboard: `http://localhost:3000`. Backtests: `http://localhost:3000/backtests`.

## Cosas que sé que no cumplí del plan original (trabajo pendiente)

Listadas y priorizadas en `docs/HANDOFF.md` § "Pendiente / próximos pasos". Resumen ejecutivo:
- El forecasting es un classifier sklearn, **no** N-HiTS / N-BEATSx (NeuralForecast). Sustitución directa pero requiere `torch` + `neuralforecast` en `ml_service`.
- El sentiment es lexicón VADER-style, **no** FinBERT. Misma sustitución: añadir `transformers` + modelo HuggingFace al ml_service y exponer `/inference/sentiment/score` real.
- Tests de integración (Playwright para UI, soak test 14 días testnet) no escritos.
- Backtester usa solo MultiSignal vectorizado; no llama a ML ni a sentiment. Walk-forward CV está implementado en train_baseline pero no en el report de backtests.
- Live broker no respeta `LOT_SIZE / stepSize / minNotional` de Binance — formatea qty con 6 decimales y deja que Binance rechace si no cumple. **Antes de live real, esto debe cumplirse.**
- Copy trading usa el endpoint público de Binance Futures sin auth. Probable que cambie de schema; defensive parsing + reintentos no implementados.

## Scope restrictions reales (lo aprendí a la mala)

- Las sesiones de Claude Code en web tienen el scope de repos fijado al arranque vía proxy local. **No se puede pushear a un repo que no esté en el allowlist desde dentro.** La sesión que generó este código tenía scope a `ajalvarez89/ajalvarez89` solamente; el repo destino real (`ajalvarez89/crypto-trading-bot`) requirió que el usuario migrara manualmente vía Codespaces o un segundo chat scopeado al repo nuevo.
- Las MCP `mcp__github__*` también respetan el allowlist del proxy.
- Si necesitas crear ramas/PRs en este repo, hazlo dentro del scope. Si necesitas saltar repos, dile al usuario.

## Cómo seguir iterando

1. Lee `docs/HANDOFF.md` § "Pendiente". Pregunta al usuario qué priorizar.
2. Una fase = una rama (`claude/<descriptive>`) + commit con mensaje en el formato de los anteriores (resumen accionable + bullets por área).
3. Antes de tocar `live_broker.py`, `risk/manager.py`, o `enable_live.sh`, considera el blast radius — son los gates de seguridad.
4. Tests: `make test` (corre los 4 stacks). Añade tests cuando toques algo crítico de risk/execution/ML.

## Fallos conocidos en el flujo de la sesión generadora (cuidado al re-aplicar diffs)

- Hubo un par de archivos donde `Edit/Write` parecía aplicarse pero el commit subsiguiente no incluía el cambio (`admin_controller.ex` y `trading_engine_client.ex` quedaron en su versión Fase 0/1 hasta que se reescribieron en Fase 6). Si cambias archivos críticos, **verifica con `git diff HEAD` antes de commitear** y comprueba que `git log -- <file>` muestra el commit que esperas.
