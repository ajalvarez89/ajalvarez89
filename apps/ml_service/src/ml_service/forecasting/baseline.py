"""Baseline forecaster: gradient-boosted direction classifier.

Phase 3 ships a *real* trainable + servable model that does not require torch.
We use a simple LightGBM-style classifier from sklearn (HistGradientBoosting)
to keep deps small. Phase 5 swaps this for a NeuralForecast ensemble.
"""
from __future__ import annotations

import json
import math
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

try:
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:  # pragma: no cover
    SKLEARN_AVAILABLE = False


FEATURE_COLS = [
    "rsi",
    "macd",
    "macd_signal",
    "macd_hist",
    "atr",
    "bb_pct",
    "bb_width",
    "adx",
    "log_ret_1",
    "log_ret_5",
    "log_ret_15",
    "log_ret_60",
    "close_to_ema_fast",
    "close_to_ema_slow",
]


@dataclass
class TrainResult:
    model_name: str
    version: str
    accuracy_in_sample: float
    accuracy_oos: float
    n_train: int
    n_test: int
    horizon_steps: int
    feature_cols: list[str]


class BaselineDirectionModel:
    """Predicts P(up) over a `horizon_steps` horizon based on features.

    `horizon_steps` is in candles (e.g. 12 for 1h ahead on 5m timeframe).
    """

    def __init__(self, horizon_steps: int = 12) -> None:
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn is not installed. Add it to ml_service deps.")
        self.horizon_steps = horizon_steps
        self.model: HistGradientBoostingClassifier | None = None
        self.feature_cols: list[str] = list(FEATURE_COLS)

    # -- Training ----------------------------------------------------------

    def fit(self, features: pd.DataFrame) -> TrainResult:
        X, y = self._prepare(features)
        if len(X) < 200:
            raise ValueError(f"Not enough rows after dropping NaNs: {len(X)}")

        # Time-ordered split: 80/20 train/test
        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        clf = HistGradientBoostingClassifier(
            max_depth=6,
            learning_rate=0.05,
            max_iter=400,
            l2_regularization=1.0,
            early_stopping=True,
            validation_fraction=0.1,
            random_state=42,
        )
        clf.fit(X_train.values, y_train.values)
        self.model = clf

        acc_train = accuracy_score(y_train, clf.predict(X_train.values))
        acc_test = accuracy_score(y_test, clf.predict(X_test.values))

        return TrainResult(
            model_name="baseline_direction_hgbc",
            version=_version_stamp(),
            accuracy_in_sample=float(acc_train),
            accuracy_oos=float(acc_test),
            n_train=len(X_train),
            n_test=len(X_test),
            horizon_steps=self.horizon_steps,
            feature_cols=self.feature_cols,
        )

    # -- Inference ---------------------------------------------------------

    def predict_proba_up(self, features_row: pd.Series) -> float:
        if self.model is None:
            raise RuntimeError("Model not loaded.")
        x = np.array([[features_row.get(c, np.nan) for c in self.feature_cols]], dtype=float)
        if np.isnan(x).any():
            raise ValueError("Feature row has NaNs")
        return float(self.model.predict_proba(x)[0, 1])

    # -- Persistence -------------------------------------------------------

    def save(self, base_dir: str | Path, version: str) -> Path:
        base = Path(base_dir) / version
        base.mkdir(parents=True, exist_ok=True)
        with open(base / "model.pkl", "wb") as f:
            pickle.dump(self.model, f)
        with open(base / "metadata.json", "w") as f:
            json.dump(
                {
                    "horizon_steps": self.horizon_steps,
                    "feature_cols": self.feature_cols,
                    "version": version,
                },
                f,
                indent=2,
            )
        return base

    @classmethod
    def load(cls, base_dir: str | Path, version: str) -> "BaselineDirectionModel":
        base = Path(base_dir) / version
        with open(base / "metadata.json") as f:
            meta = json.load(f)
        m = cls(horizon_steps=meta["horizon_steps"])
        m.feature_cols = meta["feature_cols"]
        with open(base / "model.pkl", "rb") as f:
            m.model = pickle.load(f)
        return m

    # -- Helpers -----------------------------------------------------------

    def _prepare(self, features: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        df = features.copy()
        df["future_close"] = df["close"].shift(-self.horizon_steps)
        df["target_up"] = (df["future_close"] > df["close"]).astype(int)
        df = df.dropna(subset=self.feature_cols + ["target_up"])
        return df[self.feature_cols], df["target_up"]


def _version_stamp() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
