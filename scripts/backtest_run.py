"""Backtest CLI.

Runs the MultiSignal vector backtester over each configured pair and
emits a JSON report under data/backtests/.

Usage (inside ml_service container):
    python /app/scripts/backtest_run.py --interval 5m
or via Make:
    make backtest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", default="5m")
    parser.add_argument("--pairs", default=os.environ.get("TRADING_PAIRS", "BTCUSDT,ETHUSDT,SOLUSDT"))
    parser.add_argument("--out", default="/data/backtests")
    args = parser.parse_args(argv)

    # Local imports so the script remains usable without optional torch deps loaded.
    sys.path.insert(0, "/app/src")
    from ml_service.backtest.runner import StrategyParams, scan_pairs
    from ml_service.config import settings
    from ml_service.features.feature_store import FeatureStore

    fs = FeatureStore(settings.duckdb_path)
    if not fs.has_klines():
        print("No klines table. Run `make seed` first.")
        return 1

    pairs = [p.strip().upper() for p in args.pairs.split(",") if p.strip()]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out) / ts
    reports = scan_pairs(fs, pairs, args.interval, params=StrategyParams(), out_dir=out_dir)

    summary = {
        "timestamp": ts,
        "interval": args.interval,
        "results": [
            {
                "symbol": r.symbol,
                **r.metrics.to_dict(),
            }
            for r in reports.values()
        ],
    }
    summary_path = out_dir / "summary.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    bands = {r.symbol: r.metrics.drawdown_band for r in reports.values()}
    n_green = sum(1 for b in bands.values() if b == "green")
    print(f"\n{n_green}/{len(bands)} pairs in green drawdown band (<20%).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
