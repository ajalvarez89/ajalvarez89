#!/usr/bin/env bash
# Documented procedure for rotating Binance API keys.
# This script just walks through the steps; it does NOT call Binance directly.

set -euo pipefail

cat <<'STEPS'
==========================================================================
  Binance API key rotation
==========================================================================

1. Log in to Binance (or testnet.binance.vision for testnet).

2. Create a NEW API key with the same permissions as the old one:
   - Reading: ENABLED
   - Spot Trading: ENABLED
   - Withdrawals: DISABLED (always)
   - IP whitelist: enabled with your local public IP

3. Edit .env and replace BINANCE_API_KEY and BINANCE_API_SECRET with the new
   values. Save.

4. Restart trading_engine to pick up the new keys:
       make down && make up

5. Verify:
       make status
       curl http://localhost:8001/health/binance

6. Once the new key is confirmed working, DELETE the old key in Binance.

7. Audit log: an entry should appear in the audit_log table for the rotation.

==========================================================================
STEPS
