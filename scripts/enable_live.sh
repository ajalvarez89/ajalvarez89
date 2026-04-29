#!/usr/bin/env bash
# Interactive gate before going live. Forces the user to acknowledge specific risks.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

cat <<'BANNER'
==========================================================================
  ENABLE LIVE TRADING — REAL MONEY
==========================================================================

You are about to start the bot with TRADING_MODE=live. This means:

  - Real orders will be submitted to Binance.
  - Real funds can be lost, partially or entirely.
  - Bugs, network issues, or extreme market conditions can cause damage.

Before continuing, confirm that you have:

  [ ] Run at least 30 days in testnet with documented metrics.
  [ ] Run at least 14 days in paper mode.
  [ ] Verified backtest drawdown < 20% out-of-sample.
  [ ] Set a low LIVE_CAPITAL_CAP_USDT (recommended: start with 50-100 USDT).
  [ ] Confirmed Binance API keys have NO Withdraw permission and have IP whitelist.
  [ ] Have a way to monitor and trigger 'make kill' from your phone.

==========================================================================
BANNER

read -r -p $'\nType the word LIVE to proceed: ' confirm
[[ "$confirm" == "LIVE" ]] || { echo "Aborted."; exit 1; }

read -r -p "Type the value of LIVE_CAPITAL_CAP_USDT to confirm: " cap
[[ "$cap" == "${LIVE_CAPITAL_CAP_USDT:-}" ]] || { echo "Cap mismatch (env=${LIVE_CAPITAL_CAP_USDT:-unset}). Aborted."; exit 1; }

if [[ "${I_UNDERSTAND_RISK:-no}" != "yes" ]]; then
  echo "ERROR: I_UNDERSTAND_RISK must be 'yes' in .env. Aborted."
  exit 1
fi

echo
echo "All confirmations OK. Proceeding to launch live stack."
