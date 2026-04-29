#!/usr/bin/env bash
# Engages the kill switch: cancels open orders and closes positions.
# Calls the trading_engine admin endpoint.

set -euo pipefail

ENGINE_URL="${TRADING_ENGINE_URL:-http://localhost:8001}"

echo "Engaging kill switch via ${ENGINE_URL}/admin/kill ..."
response=$(curl -fsS -X POST "${ENGINE_URL}/admin/kill" -H "Content-Type: application/json")
echo "Response: $response"

echo
echo "Kill switch engaged. To resume: make resume"
