"""List previous backtest runs from data/backtests."""
from __future__ import annotations

import json
from pathlib import Path

BACKTESTS_DIR = Path("/data/backtests")


def list_runs() -> list[dict]:
    if not BACKTESTS_DIR.exists():
        return []
    runs = []
    for d in sorted(BACKTESTS_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        summary_path = d / "summary.json"
        if not summary_path.exists():
            continue
        try:
            data = json.loads(summary_path.read_text())
            runs.append({"id": d.name, **data})
        except json.JSONDecodeError:
            continue
    return runs
