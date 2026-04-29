"""Vector-style backtester for the MultiSignal strategy.

We re-implement the strategy's decision logic in vectorized form against the
features table built by features.feature_store. This avoids importing the
trading_engine package and keeps the backtester self-contained.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from ml_service.features.feature_store import FeatureStore
from ml_service.features.technical import FeatureConfig


@dataclass
class StrategyParams:
    rsi_lower_band: float = 35.0
    rsi_upper_band: float = 65.0
    stop_atr_mult: float = 1.5
    tp_atr_mult: float = 3.0
    fee_rate: float = 0.001
    slippage_bps: float = 5.0


@dataclass
class BacktestMetrics:
    total_return_pct: float
    sharpe: float
    sortino: float
    max_drawdown_pct: float
    profit_factor: float
    win_rate: float
    n_trades: int
    n_winners: int
    n_losers: int
    expectancy: float
    drawdown_band: str  # green / amber / red

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BacktestReport:
    symbol: str
    interval: str
    metrics: BacktestMetrics
    equity_curve: list[float] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)
    params: dict = field(default_factory=dict)


def run_backtest(
    feats: pd.DataFrame,
    *,
    symbol: str,
    interval: str,
    params: StrategyParams | None = None,
    starting_equity: float = 10_000.0,
) -> BacktestReport:
    """Run the MultiSignal logic over a feature dataframe and return metrics."""
    p = params or StrategyParams()
    df = feats.dropna(subset=["ema_fast", "ema_slow", "rsi", "macd_hist", "atr", "close"]).reset_index(drop=True)
    if len(df) < 30:
        raise ValueError("Not enough data after dropna")

    long_trend = (df["close"] > df["ema_fast"]) & (df["ema_fast"] > df["ema_slow"])
    short_trend = (df["close"] < df["ema_fast"]) & (df["ema_fast"] < df["ema_slow"])
    rsi_ok = (df["rsi"] > p.rsi_lower_band) & (df["rsi"] < p.rsi_upper_band)

    hist = df["macd_hist"]
    cross_up = (hist.shift(1) <= 0) & (hist > 0)
    cross_down = (hist.shift(1) >= 0) & (hist < 0)

    long_entry = long_trend & rsi_ok & cross_up
    short_entry = short_trend & rsi_ok & cross_down

    equity = starting_equity
    equity_curve = [equity]
    trades: list[dict] = []
    open_pos: dict | None = None

    for i in range(1, len(df)):
        price = float(df["close"].iat[i])
        atr = float(df["atr"].iat[i])

        # Manage open position first
        if open_pos:
            side = open_pos["side"]
            stop = open_pos["stop"]
            tp = open_pos["tp"]
            qty = open_pos["qty"]
            entry = open_pos["entry"]

            hit_stop = (side == "long" and price <= stop) or (side == "short" and price >= stop)
            hit_tp = (side == "long" and price >= tp) or (side == "short" and price <= tp)
            if hit_stop or hit_tp:
                exit_price = stop if hit_stop else tp
                slip = exit_price * (p.slippage_bps / 10_000.0)
                exit_price = exit_price - slip if side == "long" else exit_price + slip
                pnl = (exit_price - entry) * qty if side == "long" else (entry - exit_price) * qty
                fee = (entry + exit_price) * qty * p.fee_rate
                pnl -= fee
                equity += pnl
                trades.append(
                    {
                        "side": side,
                        "entry": entry,
                        "exit": exit_price,
                        "qty": qty,
                        "pnl": pnl,
                        "outcome": "tp" if hit_tp else "stop",
                    }
                )
                open_pos = None

        # New entries only when flat
        if open_pos is None:
            if long_entry.iat[i]:
                stop = price - p.stop_atr_mult * atr
                tp = price + p.tp_atr_mult * atr
                qty = (equity * 0.01) / max(price - stop, 1e-9)
                open_pos = {"side": "long", "entry": price, "stop": stop, "tp": tp, "qty": qty}
            elif short_entry.iat[i]:
                stop = price + p.stop_atr_mult * atr
                tp = price - p.tp_atr_mult * atr
                qty = (equity * 0.01) / max(stop - price, 1e-9)
                open_pos = {"side": "short", "entry": price, "stop": stop, "tp": tp, "qty": qty}

        equity_curve.append(equity)

    metrics = _compute_metrics(equity_curve, trades, starting_equity)
    return BacktestReport(
        symbol=symbol,
        interval=interval,
        metrics=metrics,
        equity_curve=equity_curve,
        trades=trades,
        params=asdict(p),
    )


def _compute_metrics(curve: list[float], trades: Sequence[dict], starting_equity: float) -> BacktestMetrics:
    equity = np.array(curve, dtype=float)
    rets = np.diff(equity) / equity[:-1]
    rets = rets[~np.isnan(rets)]
    rets = rets[~np.isinf(rets)]

    if len(rets) > 1 and rets.std() > 0:
        sharpe = (rets.mean() / rets.std()) * math.sqrt(365 * 24)  # rough annualization for hourly-ish data
        downside = rets[rets < 0]
        sortino = (rets.mean() / downside.std()) * math.sqrt(365 * 24) if len(downside) > 0 and downside.std() > 0 else 0.0
    else:
        sharpe, sortino = 0.0, 0.0

    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd_pct = abs(float(dd.min())) if len(dd) else 0.0

    pnls = np.array([t["pnl"] for t in trades], dtype=float)
    winners = (pnls > 0).sum()
    losers = (pnls < 0).sum()
    win_rate = float(winners) / max(1, len(pnls))
    gross_win = float(pnls[pnls > 0].sum()) if (pnls > 0).any() else 0.0
    gross_loss = float(-pnls[pnls < 0].sum()) if (pnls < 0).any() else 0.0
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (math.inf if gross_win > 0 else 0.0)
    expectancy = float(pnls.mean()) if len(pnls) else 0.0

    if max_dd_pct < 0.20:
        band = "green"
    elif max_dd_pct < 0.30:
        band = "amber"
    else:
        band = "red"

    total_return_pct = float((equity[-1] / starting_equity - 1) * 100) if len(equity) else 0.0

    return BacktestMetrics(
        total_return_pct=round(total_return_pct, 4),
        sharpe=round(float(sharpe), 4),
        sortino=round(float(sortino), 4),
        max_drawdown_pct=round(max_dd_pct * 100, 4),
        profit_factor=round(profit_factor if math.isfinite(profit_factor) else 999.0, 4),
        win_rate=round(win_rate, 4),
        n_trades=int(len(trades)),
        n_winners=int(winners),
        n_losers=int(losers),
        expectancy=round(expectancy, 4),
        drawdown_band=band,
    )


def scan_pairs(
    fs: FeatureStore,
    pairs: Sequence[str],
    interval: str,
    *,
    params: StrategyParams | None = None,
    out_dir: Path | None = None,
) -> dict[str, BacktestReport]:
    """Run a backtest per pair and return the per-pair report."""
    out: dict[str, BacktestReport] = {}
    for pair in pairs:
        feats = fs.build_features_table(pair, interval, FeatureConfig())
        if feats.empty:
            continue
        try:
            report = run_backtest(feats, symbol=pair, interval=interval, params=params)
        except ValueError:
            continue
        out[pair] = report
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{pair}_{interval}.json").write_text(
                json.dumps(
                    {
                        "symbol": report.symbol,
                        "interval": report.interval,
                        "metrics": report.metrics.to_dict(),
                        "trades": report.trades[:200],
                        "equity_curve_tail": report.equity_curve[-200:],
                        "params": report.params,
                    },
                    indent=2,
                )
            )
    return out
