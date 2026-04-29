import math
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("sklearn")

from ml_service.features.technical import compute_features
from ml_service.forecasting.baseline import BaselineDirectionModel


def _make_features() -> pd.DataFrame:
    n = 800
    prices = [100.0 + math.sin(i / 12.0) * 5 + i * 0.02 for i in range(n)]
    df = pd.DataFrame(
        {
            "open_time_ms": list(range(n)),
            "open": prices,
            "high": [p * 1.001 for p in prices],
            "low": [p * 0.999 for p in prices],
            "close": prices,
            "volume": [1.0] * n,
        }
    )
    return compute_features(df)


def test_fit_and_predict_round_trip(tmp_path: Path):
    feats = _make_features()
    model = BaselineDirectionModel(horizon_steps=12)
    result = model.fit(feats)

    assert result.n_train > 0 and result.n_test > 0
    assert 0 <= result.accuracy_oos <= 1.0
    assert result.horizon_steps == 12

    base = model.save(tmp_path / "baseline_direction_btcusdt_5m", result.version)
    assert (base / "model.pkl").exists()

    loaded = BaselineDirectionModel.load(tmp_path / "baseline_direction_btcusdt_5m", result.version)
    last_row = feats.dropna().iloc[-1]
    p = loaded.predict_proba_up(last_row)
    assert 0.0 <= p <= 1.0
