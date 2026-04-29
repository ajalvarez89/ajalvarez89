# Disclaimers

## Not financial advice

This software is provided for **educational and experimental purposes only**. It is **not** financial advice, investment recommendation, or any form of regulated financial guidance. The author and contributors are not registered financial advisors.

## Risk of total loss

Cryptocurrency trading carries **significant risk of total loss of capital**. Sources of risk include but are not limited to:

- Extreme volatility (intraday moves of >20% are common in crypto).
- Liquidity gaps and slippage during stress events.
- Counterparty risk (exchange hacks, insolvency, account freezes).
- Network risk (chain congestion, failed transactions).
- Regulatory risk (sudden bans, delistings, KYC enforcement).
- Operational risk (bugs, latency, race conditions in this software).

## No guarantee of profit

Past performance — including backtests and historical simulations — **does not predict future results**. Backtests are particularly susceptible to:

- **Overfitting**: parameters tuned to past data may fail in live conditions.
- **Survivorship bias**: tokens that have failed are not in the historical dataset.
- **Look-ahead bias**: subtle bugs that allow the model to "see" future data.
- **Slippage and fees underestimation**: live execution costs differ from simulations.

The walk-forward validation and out-of-sample testing in this project mitigate but do **not eliminate** these biases.

## Mandatory testnet / paper trading first

Before any live trading is enabled, the user **must**:

1. Run the system in `testnet` mode for at least 30 days.
2. Run in `paper` mode for at least 14 days.
3. Document metrics (P&L, Sharpe, drawdown, win rate) in `data/backtests/`.
4. Verify all risk parameters are conservative.
5. Start with a hard capital cap (`LIVE_CAPITAL_CAP_USDT`) of no more than what you can comfortably lose.

## API key security

- Use **dedicated** Binance API keys for this bot (don't reuse keys from other apps).
- **Never enable Withdrawals.** A compromised key without withdraw permission limits damage to existing positions.
- Activate **IP whitelist** in Binance for the API keys.
- Store `.env` with `chmod 600` and keep it out of version control.
- Rotate keys periodically (`scripts/rotate_api_keys.sh`).

## Capital sizing

Use only **risk capital** — money whose total loss would not affect your living standards, debt obligations, or financial commitments. A common rule: never trade with money you cannot afford to lose entirely.

## Regulatory compliance

You are solely responsible for:
- Verifying that automated crypto trading is legal in your jurisdiction.
- Reporting profits/losses for tax purposes.
- Complying with KYC/AML requirements at the exchange.
- Any other applicable regulatory obligations.

## Software warranty

This software is provided **AS-IS, without warranty of any kind**. See [LICENSE](../LICENSE) for the full MIT terms. The authors assume no liability for any losses, damages, or other consequences arising from the use of this software.

## Recommended deployment posture

If you proceed to live trading:

- Run on a dedicated machine (not your daily laptop) with UPS power.
- Monitor 24/7 with alerting (Telegram, PagerDuty).
- Keep `make kill` scriptable from your phone (SSH + alias).
- Review trades daily for the first month.
- Have a written exit plan for shutting down operations.

## In summary

> Don't run this bot with money you can't afford to lose, on a setup you can't monitor, in a jurisdiction where you haven't checked the law, with API keys that can withdraw.
