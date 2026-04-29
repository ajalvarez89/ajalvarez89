"""DuckDB-backed feature store.

Materialises feature tables from the parquet klines warehouse and serves them
to training (offline) and inference (online) code paths.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from ml_service.features.technical import FeatureConfig, compute_features


class FeatureStore:
    def __init__(self, duckdb_path: str | Path) -> None:
        self.path = str(duckdb_path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(self.path)

    def has_klines(self) -> bool:
        with self._connect() as con:
            try:
                con.execute("SELECT 1 FROM klines LIMIT 1").fetchone()
                return True
            except duckdb.CatalogException:
                return False

    def load_klines(self, symbol: str, interval: str) -> pd.DataFrame:
        with self._connect() as con:
            return con.execute(
                "SELECT * FROM klines WHERE symbol = ? AND interval = ? ORDER BY open_time_ms ASC",
                [symbol, interval],
            ).fetch_df()

    def build_features_table(self, symbol: str, interval: str, cfg: FeatureConfig | None = None) -> pd.DataFrame:
        df = self.load_klines(symbol, interval)
        if df.empty:
            return df
        feats = compute_features(df, cfg)

        with self._connect() as con:
            con.execute("CREATE SCHEMA IF NOT EXISTS features")
            table = f"features.f_{symbol.lower()}_{interval}"
            con.register("feats_df", feats)
            con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM feats_df")
            con.unregister("feats_df")
        return feats

    def latest_features(self, symbol: str, interval: str, n: int = 50) -> pd.DataFrame:
        with self._connect() as con:
            table = f"features.f_{symbol.lower()}_{interval}"
            try:
                return con.execute(
                    f"SELECT * FROM {table} ORDER BY open_time_ms DESC LIMIT {int(n)}"
                ).fetch_df().iloc[::-1]
            except duckdb.CatalogException:
                return pd.DataFrame()
