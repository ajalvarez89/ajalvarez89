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

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close_connection()
            self._client = None
