"""Ensemble of two BaselineDirectionModels (different horizons) for robustness.

When both models agree (>0.55 long or <0.45 short), the combined probability
is the average. Disagreement yields a neutral 0.5 — the strategy will then
pass through to the technical decision.
"""
from __future__ import annotations

from dataclasses import dataclass

from ml_service.forecasting.baseline import BaselineDirectionModel
from ml_service.forecasting.registry import ModelRegistry


@dataclass
class EnsembleResult:
    direction_prob: float
    short_prob: float
    long_prob: float
    agree: bool


class DirectionEnsemble:
    def __init__(
        self,
        models: list[BaselineDirectionModel],
        *,
        agree_threshold: float = 0.05,
    ) -> None:
        self.models = models
        self.agree_threshold = agree_threshold

    def predict(self, features_row) -> EnsembleResult:
        probs = [m.predict_proba_up(features_row) for m in self.models]
        avg = sum(probs) / len(probs)
        max_dev = max(abs(p - avg) for p in probs)
        agree = max_dev <= self.agree_threshold
        return EnsembleResult(direction_prob=float(avg), short_prob=1 - avg, long_prob=avg, agree=agree)


def load_ensemble(name: str, registry: ModelRegistry) -> DirectionEnsemble | None:
    """Load up to 2 most recent versions of a model name as an ensemble."""
    versions = registry.list_versions(name)[-2:]
    if not versions:
        return None
    models = [BaselineDirectionModel.load(registry.root / name, v) for v in versions]
    return DirectionEnsemble(models)
