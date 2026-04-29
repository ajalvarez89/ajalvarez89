"""Train the baseline direction classifier and register it as champion if better.

Run inside ml_service container:
    docker compose exec ml_service python -m ml_service.training.train_baseline \
        --symbol BTCUSDT --interval 5m --horizon 12
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import structlog

from ml_service.config import settings
from ml_service.features.feature_store import FeatureStore
from ml_service.forecasting.baseline import BaselineDirectionModel
from ml_service.forecasting.registry import ModelRegistry

log = structlog.get_logger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="5m")
    parser.add_argument("--horizon", type=int, default=12)
    parser.add_argument("--registry", default=os.environ.get("MODEL_REGISTRY", "/app/models"))
    parser.add_argument("--promote", action="store_true", help="Mark this version as champion if it beats the current one")
    args = parser.parse_args(argv)

    fs = FeatureStore(settings.duckdb_path)
    if not fs.has_klines():
        print("No klines table in DuckDB. Run `make seed` first.")
        return 1

    feats = fs.build_features_table(args.symbol, args.interval)
    if feats.empty:
        print(f"No klines for {args.symbol} {args.interval}.")
        return 1

    model = BaselineDirectionModel(horizon_steps=args.horizon)
    result = model.fit(feats)
    log.info("training_complete", **{k: v for k, v in result.__dict__.items() if k != "feature_cols"})

    registry = ModelRegistry(args.registry)
    name = f"baseline_direction_{args.symbol.lower()}_{args.interval}"
    base = model.save(registry.root / name, result.version)

    metrics_path = base / "metrics.json"
    metrics_path.write_text(json.dumps(_to_dict(result), indent=2))

    if args.promote:
        champ = registry.champion(name)
        is_better = champ is None or _accuracy(champ) < result.accuracy_oos
        if is_better:
            registry.set_champion(name, result.version)
            log.info("champion_updated", name=name, version=result.version, accuracy_oos=result.accuracy_oos)
        else:
            log.info("champion_kept", name=name, current_version=champ.version)

    print(json.dumps(_to_dict(result), indent=2))
    return 0


def _accuracy(entry) -> float:
    metrics_file = entry.base_dir / "metrics.json"
    if not metrics_file.exists():
        return 0.0
    return float(json.loads(metrics_file.read_text()).get("accuracy_oos", 0.0))


def _to_dict(result) -> dict:
    out = {**result.__dict__}
    return out


if __name__ == "__main__":
    sys.exit(main())
