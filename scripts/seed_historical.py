"""Download historical klines from Binance into DuckDB.

Phase 1+: actually fetches and stores. Phase 0: stub that prints what it would do.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone


def main() -> int:
    pairs = os.environ.get("TRADING_PAIRS", "BTCUSDT,ETHUSDT,SOLUSDT").split(",")
    timeframes = ["1m", "5m", "1h", "1d"]
    days = int(os.environ.get("HISTORICAL_DAYS", "90"))

    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=days)

    print(f"[seed_historical] Phase 0 stub.")
    print(f"  Pairs: {pairs}")
    print(f"  Timeframes: {timeframes}")
    print(f"  Range: {start.isoformat()} → {end.isoformat()}")
    print(f"  Output: DuckDB at {os.environ.get('DUCKDB_PATH', '/data/duckdb/warehouse.duckdb')}")
    print()
    print("  Real implementation lands in Phase 1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
