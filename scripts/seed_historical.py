"""Download historical klines from Binance into DuckDB.

Reads `TRADING_PAIRS`, intervals, and `HISTORICAL_DAYS` from env.
Writes one parquet file per (symbol, interval) under DATA_DIR/klines and
registers a DuckDB view `klines` over them.

Run inside the ml_service container:
    docker compose exec ml_service python /app/scripts/seed_historical.py
or via Make:
    make seed
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

BINANCE_BASE = "https://api.binance.com"
TESTNET_BASE = "https://testnet.binance.vision"

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
KLINES_DIR = DATA_DIR / "klines"
DUCKDB_PATH = Path(os.environ.get("DUCKDB_PATH", str(DATA_DIR / "duckdb" / "warehouse.duckdb")))

PAIRS = [p.strip().upper() for p in os.environ.get("TRADING_PAIRS", "BTCUSDT,ETHUSDT,SOLUSDT").split(",") if p.strip()]
INTERVALS = os.environ.get("HISTORICAL_INTERVALS", "1m,5m,1h,1d").split(",")
DAYS = int(os.environ.get("HISTORICAL_DAYS", "90"))
TESTNET = os.environ.get("BINANCE_TESTNET", "1") == "1"

BASE = TESTNET_BASE if TESTNET else BINANCE_BASE


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def fetch_klines(symbol: str, interval: str, start_ms: int, end_ms: int) -> list[list]:
    """Page through Binance REST until end_ms is reached."""
    rows: list[list] = []
    cursor = start_ms

    with httpx.Client(timeout=20.0) as client:
        while cursor < end_ms:
            r = client.get(
                f"{BASE}/api/v3/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": 1000,
                },
            )
            r.raise_for_status()
            chunk = r.json()
            if not chunk:
                break
            rows.extend(chunk)
            last_close = chunk[-1][6]
            if last_close <= cursor:
                break
            cursor = last_close + 1
            time.sleep(0.05)  # mild rate-limit courtesy

    return rows


def write_parquet(symbol: str, interval: str, rows: list[list]) -> Path:
    import pandas as pd

    if not rows:
        raise RuntimeError(f"No rows fetched for {symbol} {interval}")

    df = pd.DataFrame(
        rows,
        columns=[
            "open_time_ms",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time_ms",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "_ignore",
        ],
    )
    df = df.drop(columns=["_ignore"])
    for col in ["open", "high", "low", "close", "volume", "quote_volume", "taker_buy_base", "taker_buy_quote"]:
        df[col] = df[col].astype(float)
    for col in ["open_time_ms", "close_time_ms", "trades"]:
        df[col] = df[col].astype("int64")
    df.insert(0, "symbol", symbol)
    df.insert(1, "interval", interval)

    out_dir = KLINES_DIR / symbol / interval
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "klines.parquet"
    df.to_parquet(out_path, index=False)
    return out_path


def register_duckdb_view() -> None:
    import duckdb

    DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DUCKDB_PATH))
    pattern = str(KLINES_DIR / "*" / "*" / "*.parquet")
    con.execute("CREATE OR REPLACE VIEW klines AS SELECT * FROM read_parquet(?)", [pattern])
    n = con.execute("SELECT count(*) FROM klines").fetchone()
    con.close()
    print(f"  duckdb view 'klines' created — {n[0]} rows")


def main() -> int:
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=DAYS)

    print(f"[seed_historical] base={BASE} testnet={TESTNET}")
    print(f"  range: {start.isoformat()} -> {end.isoformat()} ({DAYS} days)")
    print(f"  pairs: {PAIRS}")
    print(f"  intervals: {INTERVALS}")

    for symbol in PAIRS:
        for interval in INTERVALS:
            print(f"  fetching {symbol} {interval} ...", end=" ", flush=True)
            try:
                rows = fetch_klines(symbol, interval, _ms(start), _ms(end))
            except httpx.HTTPError as e:
                print(f"FAIL ({e})")
                continue
            path = write_parquet(symbol, interval, rows)
            print(f"{len(rows)} rows -> {path}")

    print()
    print("Registering DuckDB view ...")
    register_duckdb_view()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
