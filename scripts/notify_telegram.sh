#!/usr/bin/env bash
# Send a Telegram message via the bot API. Wired up only if TELEGRAM_BOT_TOKEN
# and TELEGRAM_CHAT_ID are set in .env.
# Usage: scripts/notify_telegram.sh "your message"

set -euo pipefail

if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

token="${TELEGRAM_BOT_TOKEN:-}"
chat="${TELEGRAM_CHAT_ID:-}"
text="${1:-}"

if [[ -z "$token" || -z "$chat" ]]; then
  echo "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set; skipping."
  exit 0
fi
if [[ -z "$text" ]]; then
  echo "usage: $0 'message'" >&2
  exit 1
fi

curl -sf -X POST "https://api.telegram.org/bot${token}/sendMessage" \
  -d "chat_id=${chat}" \
  --data-urlencode "text=${text}"
echo
