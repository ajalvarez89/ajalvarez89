"""Async wrapper around python-binance.

Phase 0: read-only ping + balance fetch.
Phase 1+: market WS streams, user data WS, order placement.
"""
from __future__ import annotations

import structlog
from binance import AsyncClient

from trading_engine.config import Settings

log = structlog.get_logger(__name__)


class BinanceClient:
    def __init__(self, client: AsyncClient, *, testnet: bool):
        self._client = client
        self.testnet = testnet

    @classmethod
    def from_settings(cls, settings: Settings) -> "BinanceClient":
        # AsyncClient.create() is the proper async factory but it requires await.
        # We wrap it lazily in `connect()` to keep `from_settings` synchronous.
        instance = cls.__new__(cls)
        instance._client = None
        instance.testnet = settings.binance_testnet
        instance._api_key = settings.binance_api_key
        instance._api_secret = settings.binance_api_secret
        return instance

    async def _ensure_connected(self) -> AsyncClient:
        if self._client is None:
            if not self._api_key or self._api_key == "replace_me":
                raise RuntimeError(
                    "BINANCE_API_KEY is not set. Get testnet keys at "
                    "https://testnet.binance.vision and update .env"
                )
            self._client = await AsyncClient.create(
                api_key=self._api_key,
                api_secret=self._api_secret,
                testnet=self.testnet,
            )
        return self._client

    async def ping_and_balance(self) -> dict:
        """Verify connectivity and return non-zero balances. Read-only."""
        client = await self._ensure_connected()
        await client.ping()
        account = await client.get_account()

        balances = {
            b["asset"]: float(b["free"]) + float(b["locked"])
            for b in account.get("balances", [])
            if float(b["free"]) > 0 or float(b["locked"]) > 0
        }
        return balances

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> list[dict]:
        """Fetch historical klines (REST). Public endpoint, no API key required.

        Returns a list of normalized dicts matching the kline contract used in
        Redis streams, so the same shape works for live and historical data.
        """
        client = await self._ensure_public_or_connected()
        kwargs: dict = {"symbol": symbol.upper(), "interval": interval, "limit": min(limit, 1000)}
        if start_ms is not None:
            kwargs["startTime"] = int(start_ms)
        if end_ms is not None:
            kwargs["endTime"] = int(end_ms)

        raw = await client.get_klines(**kwargs)
        return [
            {
                "symbol": symbol.upper(),
                "interval": interval,
                "open_time_ms": int(row[0]),
                "close_time_ms": int(row[6]),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
                "trades": int(row[8]),
                "is_closed": True,
            }
            for row in raw
        ]

    async def _ensure_public_or_connected(self) -> AsyncClient:
        """Public endpoints don't need API keys. Use a public client when possible."""
        if self._client is not None:
            return self._client
        if self._api_key and self._api_key != "replace_me":
            return await self._ensure_connected()
        # Public-only client (no auth)
        self._client = await AsyncClient.create(testnet=self.testnet)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close_connection()
            self._client = None
