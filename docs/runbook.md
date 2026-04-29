# Runbook

## First-time setup

1. **Get Binance Testnet credentials**
   - Register at https://testnet.binance.vision
   - Generate API key + secret. Permissions: Reading + Spot Trading. **Never** enable Withdrawals.
   - Add IP whitelist (your local public IP).

2. **Configure environment**
   ```bash
   cp .env.example .env
   chmod 600 .env
   # Edit .env: paste BINANCE_API_KEY, BINANCE_API_SECRET, leave TRADING_MODE=testnet
   ```

3. **Verify config**
   ```bash
   make preflight
   ```
   Should report green for: env vars present, key format valid, Docker available.

4. **Build and start**
   ```bash
   make up
   ```
   First time will pull images and build (~5-10 min).

5. **Check health**
   ```bash
   make status
   ```
   All services should report 200.

6. **Open dashboard**
   - http://localhost:3000

## Daily operation

- **Start the stack**: `make up`
- **Authorize order execution for the next 24h**: `make approve`
- **View logs**: `make logs` (or `make logs-trading`, `make logs-ml`, `make logs-phoenix`)
- **Trigger kill switch**: `make kill` (cancels orders, closes positions)
- **Resume after kill**: `make resume`
- **Stop the stack**: `make down`

## Going to live trading (Phase 7+, REAL MONEY)

**Do NOT skip any of these steps.**

1. Run at least 30 days in `testnet` and 14 days in `paper` with documented metrics in `data/backtests/`.
2. Verify: drawdown < 20%, Sharpe > 1.0, profit factor > 1.3, no risk violations.
3. Generate live API keys with the same permissions (Reading + Spot Trading, NO Withdrawals, IP whitelist).
4. Set `LIVE_CAPITAL_CAP_USDT` low (e.g. 50-200 USDT for canary).
5. Run `bash scripts/enable_live.sh` (interactive, requires typing confirmation).
6. `make up-live` instead of `make up`.
7. **Monitor continuously** during the first week. Have `make kill` accessible from your phone.

## Incident response

| Symptom | Action |
|---|---|
| Service unhealthy in dashboard | `make logs-<service>`, check error, restart with `docker compose restart <service>` |
| Binance API errors / rate limit | Check IP whitelist; verify keys; back off automatically via `tenacity` |
| Drawdown alarm triggered | Already kill-switched automatically. Inspect `audit_log`, decide whether to resume |
| Unexpected open position | Inspect SQLite `positions` table; if untracked, manually close in Binance UI; investigate audit log |
| Disk full | DuckDB and SQLite grow; rotate with `scripts/archive_data.sh` (Phase 6+) |

## Backups

- SQLite DB: copy `data/sqlite/trading.db` (atomic snapshot via `sqlite3 .backup`).
- DuckDB warehouse: copy `data/duckdb/warehouse.duckdb`.
- ML models: `apps/ml_service/models/` (gitignored, back up separately).
- Encrypt all backups; they may contain trading history considered sensitive.

## Troubleshooting

- **Phoenix won't start: "secret_key_base missing"**: ensure `.env` has `SECRET_KEY_BASE` (≥64 chars). Generate with `openssl rand -base64 64`.
- **Trading engine: "BINANCE_API_KEY is not set"**: edit `.env`, restart container.
- **Dashboard "Connecting..." forever**: check that `NEXT_PUBLIC_PHOENIX_WS_URL` is reachable from your browser; CORS plug allows `http://localhost:3000`.
- **Tests failing locally**: run `make test` inside containers (`docker compose exec <service> pytest`).
