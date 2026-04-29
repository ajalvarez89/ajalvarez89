#!/usr/bin/env bash
# Preflight checks — validates configuration and connectivity before arming the bot.
# Returns non-zero on any failed check so it can gate `make up`.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
RESET='\033[0m'

pass=0
warn=0
fail=0

check() {
  local label="$1" status="$2" detail="${3:-}"
  case "$status" in
    pass) printf "  ${GREEN}✓${RESET} %-50s %s\n" "$label" "$detail"; pass=$((pass+1)) ;;
    warn) printf "  ${YELLOW}!${RESET} %-50s %s\n" "$label" "$detail"; warn=$((warn+1)) ;;
    fail) printf "  ${RED}✗${RESET} %-50s %s\n" "$label" "$detail"; fail=$((fail+1)) ;;
  esac
}

echo
echo "=========================================================================="
echo "  crypto-trading-bot — preflight"
echo "=========================================================================="
echo

# 1. .env exists
if [[ -f .env ]]; then
  check ".env present" pass
  # shellcheck disable=SC1091
  set -a; source .env; set +a
else
  check ".env present" fail "run 'cp .env.example .env' and edit it"
  echo
  echo "Aborting — fix above and re-run."
  exit 1
fi

# 2. .env permissions
perm=$(stat -c "%a" .env 2>/dev/null || stat -f "%A" .env 2>/dev/null)
if [[ "$perm" == "600" ]]; then
  check ".env permissions (600)" pass
else
  check ".env permissions" warn "current=$perm; recommend 'chmod 600 .env'"
fi

# 3. Trading mode
case "${TRADING_MODE:-}" in
  testnet) check "TRADING_MODE" pass "testnet (safe)" ;;
  paper)   check "TRADING_MODE" pass "paper (safe, simulated)" ;;
  live)    check "TRADING_MODE" warn "live (REAL MONEY)";;
  *)       check "TRADING_MODE" fail "invalid value: '${TRADING_MODE:-unset}'";;
esac

# 4. I_UNDERSTAND_RISK gate
if [[ "${TRADING_MODE:-}" == "live" ]]; then
  if [[ "${I_UNDERSTAND_RISK:-no}" == "yes" ]]; then
    check "I_UNDERSTAND_RISK" pass "yes"
  else
    check "I_UNDERSTAND_RISK" fail "must be 'yes' to run live mode"
  fi
fi

# 5. Binance API keys present
if [[ -n "${BINANCE_API_KEY:-}" && "${BINANCE_API_KEY}" != "replace_me" ]]; then
  check "BINANCE_API_KEY set" pass
else
  check "BINANCE_API_KEY set" fail "edit .env"
fi

if [[ -n "${BINANCE_API_SECRET:-}" && "${BINANCE_API_SECRET}" != "replace_me" ]]; then
  check "BINANCE_API_SECRET set" pass
else
  check "BINANCE_API_SECRET set" fail "edit .env"
fi

# 6. Docker
if command -v docker >/dev/null 2>&1; then
  check "Docker available" pass "$(docker --version | head -1)"
else
  check "Docker available" fail "install Docker"
fi

if docker compose version >/dev/null 2>&1; then
  check "Docker Compose v2" pass
else
  check "Docker Compose v2" fail "install or update Docker Compose"
fi

# 7. Required directories
for d in data/sqlite data/duckdb data/klines data/news config; do
  mkdir -p "$d"
done
check "Data directories created" pass

# 8. risk.yml present
if [[ -f config/risk.yml ]]; then
  check "config/risk.yml present" pass
else
  check "config/risk.yml present" fail "missing — see config/risk.yml.example"
fi

# 9. Binance connectivity (only if running services)
if curl -sfm 5 https://testnet.binance.vision/api/v3/ping >/dev/null 2>&1; then
  check "Binance Testnet reachable" pass
else
  check "Binance Testnet reachable" warn "no internet or Binance issue"
fi

echo
echo "=========================================================================="
printf "  Result: ${GREEN}%d passed${RESET}, ${YELLOW}%d warnings${RESET}, ${RED}%d failed${RESET}\n" "$pass" "$warn" "$fail"
echo "=========================================================================="
echo

if [[ $fail -gt 0 ]]; then
  echo "Fix the failures above and re-run 'make preflight' before 'make up'."
  exit 1
fi

echo "Preflight OK. You can now run 'make up'."
