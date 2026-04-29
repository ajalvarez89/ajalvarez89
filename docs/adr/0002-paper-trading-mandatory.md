# ADR 0002 — Mandatory testnet/paper before live

Date: 2026-04-29
Status: Accepted

## Context

The user wants the system to eventually trade with real money. The temptation is to enable live trading early to start "earning". The reality of algorithmic trading: most strategies that look profitable in-sample fail out-of-sample. Premature live deployment is the single largest source of capital loss for retail algo traders.

## Decision

`TRADING_MODE` defaults to `testnet`. Promotion to `live` requires:

1. `I_UNDERSTAND_RISK=yes` set explicitly in `.env`.
2. Compose override `docker-compose.prod.yml` used (`make up-live`).
3. Backtest passing strict thresholds (drawdown < 20%, Sharpe > 1.0).
4. At least 30 days in testnet + 14 days in paper.
5. Interactive confirmation script `scripts/enable_live.sh`.
6. Hard capital cap `LIVE_CAPITAL_CAP_USDT` (default 200 USDT) enforced in code, not just config.

## Rationale

The friction is intentional. Each gate adds a real check that prevents accidental losses. The user can override these in their fork, but the defaults must protect against the most common failure mode: enthusiasm.

## Consequences

Positive:
- Reduces probability of premature deployment.
- Forces validation discipline.

Negative:
- Slower path from idea to live.
- Some users will perceive friction as annoying. That's OK.
