"""Inference endpoints — stubs in Phase 0, real models in Phase 3+."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["inference"])


class PredictRequest(BaseModel):
    symbol: str
    horizon_minutes: int = 60


class PredictResponse(BaseModel):
    symbol: str
    horizon_minutes: int
    forecast: float | None = None
    lower: float | None = None
    upper: float | None = None
    direction_prob: float | None = None
    note: str = "Phase 0 stub. Real N-HiTS inference in Phase 3."


@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest) -> PredictResponse:
    return PredictResponse(symbol=req.symbol.upper(), horizon_minutes=req.horizon_minutes)


@router.post("/sentiment/score")
async def score_sentiment(payload: dict) -> dict:
    # Phase 4: FinBERT scoring
    return {"text": payload.get("text", ""), "score": None, "label": None, "note": "Phase 0 stub"}
