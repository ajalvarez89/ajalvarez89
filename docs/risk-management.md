# Risk management

## Principles

1. **No order without explicit user approval** (`make approve`, expires every 24h).
2. **All orders must have a stop-loss** (default ATR-based, fallback 2% fixed).
3. **Daily drawdown caps trigger automatic kill switch.**
4. **Capital caps are hard limits in code**, not just config.
5. **Audit trail is insert-only**: every action (system or user) logged.

## Modes

| Mode | What it does | Real money? |
|---|---|---|
| `testnet` | Connects to Binance Testnet | No |
| `paper` | Simulates fills locally with `paper_broker` | No |
| `live` | Submits real orders to Binance | **YES** — gated by `I_UNDERSTAND_RISK=yes` + `enable_live.sh` |

## Risk parameters (`config/risk.yml`)

| Parameter | Default | Description |
|---|---|---|
| `risk_per_trade_pct` | 1% | % of equity risked per trade. Lot size derived from this. |
| `max_position_pct_equity` | 5% | Absolute cap on a single position relative to equity |
| `max_open_positions` | 3 | Max concurrent open positions |
| `stop_atr_multiplier` | 1.5 | Stop-loss distance = N · ATR(14) |
| `tp_atr_multiplier` | 3.0 | Take-profit distance = N · ATR(14). RR objective 1:2 |
| `mandatory_stop_loss_pct` | 2% | Fallback when ATR not available |
| `daily_max_drawdown_pct` | 3% | Daily DD that triggers automatic kill switch |
| `max_consecutive_losses` | 4 | Streak that triggers 1h cooldown |
| `max_orders_per_minute` | 5 | Internal rate limit |
| `max_slippage_bps` | 50 | Max acceptable slippage on execution |

## Order approval flow

1. User runs `make approve` (or POST `/api/admin/approve`). Inserts row into `approvals` table with `granted_at` and `expires_at = granted_at + 24h`.
2. `trading_engine`, before submitting any order, queries the `approvals` table:
   - If no valid (non-revoked, non-expired) row exists → reject with message: `Run 'make approve' to authorize order execution`.
3. To revoke early: `make kill` engages the kill switch (also cancels orders and closes positions).

## Kill switch

Behavior when engaged:
- Cancel all open orders (Binance + paper).
- Close all positions to market (configurable).
- Persist `kill_engaged=true` in SQLite.
- Reject all new signals until `POST /admin/resume`.

Trigger sources:
- Manual: `make kill`, UI button (double confirmation), `POST /admin/kill`.
- Automatic: daily drawdown breach, consecutive loss streak, repeated rejected orders, exchange disconnection > N seconds.

## Promotion criteria for strategies

Before a strategy is allowed in paper or live trading, its backtest must pass:

| Metric | Threshold |
|---|---|
| Max drawdown out-of-sample | 🟢 < 20% |
| Sharpe ratio | > 1.0 |
| Profit factor | > 1.3 |
| Total trades | > 30 (statistical validity) |
| Walk-forward median Sharpe | > 0.8 |

🟠 20-30% drawdown requires manual review and a note in `data/backtests/{ts}.md`.
🔴 > 30% rejected automatically.

## What this system does NOT protect against

- Exchange insolvency or hack.
- Network outages on the user's side.
- Black swan price moves outside model expectations.
- Bugs in this software (it's experimental).
- User error (running `make up-live` without the canary phase).

For these, the only protection is small capital and constant vigilance.
