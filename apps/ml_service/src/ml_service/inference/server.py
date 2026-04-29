"""Inference endpoints for the ML service."""
from __future__ import annotations

import os
import time
from collections import OrderedDict
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ml_service.config import settings
from ml_service.features.feature_store import FeatureStore
from ml_service.forecasting.baseline import BaselineDirectionModel
from ml_service.forecasting.registry import ModelRegistry

log = structlog.get_logger(__name__)
router = APIRouter(tags=["inference"])


class PredictRequest(BaseModel):
    symbol: str
    interval: str = "5m"
    horizon_minutes: int = 60


class PredictResponse(BaseModel):
    symbol: str
    interval: str
    horizon_minutes: int
    direction_prob: float | None = None
    forecast: float | None = None
    lower: float | None = None
    upper: float | None = None
    model_version: str | None = None
    note: str = ""


_REGISTRY = ModelRegistry(os.environ.get("MODEL_REGISTRY", "/app/models"))
_FEATURE_STORE = FeatureStore(settings.duckdb_path)
_CACHE: "OrderedDict[str, tuple[float, PredictResponse]]" = OrderedDict()
_CACHE_TTL_SEC = 60


@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest) -> PredictResponse:
    symbol = req.symbol.upper()
    cache_key = f"{symbol}:{req.interval}:{req.horizon_minutes}"

    cached = _CACHE.get(cache_key)
    if cached and (time.time() - cached[0] < _CACHE_TTL_SEC):
        return cached[1]

    name = f"baseline_direction_{symbol.lower()}_{req.interval}"
    champion = _REGISTRY.champion(name)

    if champion is None:
        return PredictResponse(
            symbol=symbol,
            interval=req.interval,
            horizon_minutes=req.horizon_minutes,
            note="No champion model trained yet. Run `make train`.",
        )

    try:
        model = BaselineDirectionModel.load(_REGISTRY.root / name, champion.version)
    except Exception as e:  # noqa: BLE001
        log.warning("model_load_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to load model: {e}") from e

    feats = _FEATURE_STORE.latest_features(symbol, req.interval, n=10)
    if feats.empty:
        return PredictResponse(
            symbol=symbol,
            interval=req.interval,
            horizon_minutes=req.horizon_minutes,
            note="No features in DuckDB yet. Run `make seed` then `make train`.",
        )

    last = feats.iloc[-1]
    try:
        prob_up = model.predict_proba_up(last)
    except ValueError as e:
        return PredictResponse(
            symbol=symbol,
            interval=req.interval,
            horizon_minutes=req.horizon_minutes,
            note=f"Insufficient features: {e}",
        )

    last_close = float(last.get("close", 0.0))
    response = PredictResponse(
        symbol=symbol,
        interval=req.interval,
        horizon_minutes=req.horizon_minutes,
        direction_prob=round(prob_up, 4),
        forecast=last_close,
        model_version=champion.version,
        note="ok",
    )
    _CACHE[cache_key] = (time.time(), response)
    if len(_CACHE) > 64:
        _CACHE.popitem(last=False)
    return response


@router.post("/sentiment/score")
async def score_sentiment(payload: dict[str, Any]) -> dict:
    # Wired up in Phase 4.
    return {"text": payload.get("text", ""), "score": None, "label": None, "note": "Phase 4 wires FinBERT scorer."}
