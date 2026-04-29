# ML pipeline

## Overview

End-to-end pipeline:

```
Historical klines (Binance REST)
    │
    └─► seed_historical.py ─► DuckDB raw_klines
                                     │
                                     ▼
News (CryptoPanic, NewsAPI)         features/technical.py (pandas-ta)
    │                               features/sentiment.py (FinBERT)
    └─► news_collector ──┐                │
                         ▼                ▼
                    Redis "news.raw"   feature_store (DuckDB)
                         │                │
                         ▼                ▼
                  finbert_scorer ─► news_sentiment ─► aggregations (15m, 1h, 6h, 24h)
                                          │
                                          ▼
                                  forecasting/train_nhits.py
                                          │
                                          ▼ walk-forward CV
                                  models/{name}/{version}/
                                          │
                                          ▼
                              inference/server.py (/predict)
                                          │
                                          ▼
                                  signal_publisher → Redis "signals"
                                          │
                                          ▼
                              trading_engine.strategies.ml_signal_consumer
```

## Components

### Features (Phase 3)

`apps/ml_service/src/ml_service/features/technical.py`:
- EMA(50, 200), RSI(14), MACD(12,26,9), ATR(14), ADX(14), OBV, Bollinger(20,2)
- Returns log multi-horizon (1, 5, 15, 60 min)

`apps/ml_service/src/ml_service/features/sentiment.py` (Phase 4):
- Rolling aggregations of FinBERT scores by symbol and window (15m, 1h, 6h, 24h)
- News count, sentiment delta vs baseline

### Forecasting (Phase 3+)

`apps/ml_service/src/ml_service/forecasting/`:
- `nhits_model.py` — wrapper around `neuralforecast.models.NHITS`
- `nbeats_model.py` — `NBEATSx` for ensemble
- `ensemble.py` — weighted average / stacking
- `walk_forward.py` — expanding window CV

Multi-horizon: 15min and 1h forecasts simultaneously.

### Sentiment (Phase 4+)

`apps/ml_service/src/ml_service/sentiment/`:
- `finbert_loader.py` — loads HuggingFace FinBERT (or fine-tuned variant)
- `scorer.py` — batch scoring with caching

### Inference (Phase 3+)

FastAPI endpoints:
- `POST /inference/predict` → `{forecast, lower, upper, direction_prob}` with TTL cache.
- `POST /inference/sentiment/score` → `{label, score}` for a text.

### Training & registry

- `training/train_nhits.py` — main training script.
- `training/walk_forward.py` — CV with expanding windows.
- `training/registry.py` — local champion/challenger versioning under `apps/ml_service/models/{name}/{version}/`.
- `training/retrain_job.py` — APScheduler job, daily.

## Notebooks

`apps/ml_service/notebooks/`:
- `01_eda_btc.ipynb` — exploratory analysis.
- `02_baseline_nhits.ipynb` — first NHITS model + metrics.
- `03_walk_forward_validation.ipynb` — out-of-sample validation.

## Metrics

- **Forecasting**: MAE, MAPE, MASE, hit-rate direccional.
- **Strategy** (after VectorBT): total return, Sharpe, Sortino, max drawdown, win rate, profit factor, expectancy.

## Promotion policy (champion/challenger)

A new model version is promoted only if:
1. Walk-forward median MASE < champion's.
2. Direction hit-rate out-of-sample > champion's by ≥ 2 percentage points.
3. Backtest (with the same strategy interface) does not regress drawdown.

## Anti-overfit safeguards

- Walk-forward instead of train/test split.
- Limit hyperparameter search to ≤ 3 simultaneous degrees of freedom (lesson from Video 2 in the planning doc).
- Hold out 20% of recent data as a final test set, untouched during training.
- Report consistent performance across symbols (multi-pair scan in Phase 6).
