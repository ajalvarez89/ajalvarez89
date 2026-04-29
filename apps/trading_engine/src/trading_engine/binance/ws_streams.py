"""Binance market data WebSocket streams.

Subscribes to public kline streams for the configured pairs/timeframes and
publishes events to Redis Streams. This service centralizes Binance WS so
the rest of the system has a single market-data source of truth.

Phase 1: kline streams only. Phase 2+: trade streams, depth streams, user data.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Iterable

import structlog
from binance import AsyncClient, BinanceSocketManager

from trading_engine.config import settings
from trading_engine.messaging.redis_publisher import RedisStreamPublisher

log = structlog.get_logger(__name__)


class MarketStreamManager:
    """Owns the Binance WS connection and republishes to Redis."""

    STREAM_KLINES = "market.klines"
    STREAM_TICKS = "market.ticks"

    def __init__(
        self,
        publisher: RedisStreamPublisher,
        *,
        symbols: Iterable[str],
        interval: str = "1m",
        testnet: bool = True,
    ) -> None:
        self.publisher = publisher
        self.symbols = [s.upper() for s in symbols]
        self.interval = interval
        self.testnet = testnet

        self._client: AsyncClient | None = None
        self._socket_manager: BinanceSocketManager | None = None
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._client = await AsyncClient.create(testnet=self.testnet)
        self._socket_manager = BinanceSocketManager(self._client)
        self._task = asyncio.create_task(self._run(), name="market-stream-manager")
        log.info("market_stream.started", symbols=self.symbols, interval=self.interval, testnet=self.testnet)

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._client is not None:
            await self._client.close_connection()
            self._client = None

    async def _run(self) -> None:
        assert self._socket_manager is not None
        streams = [f"{s.lower()}@kline_{self.interval}" for s in self.symbols]

        async with self._socket_manager.multiplex_socket(streams) as stream:
            log.info("market_stream.connected", streams=streams)
            while not self._stop.is_set():
                msg = await stream.recv()
                await self._handle_message(msg)

    async def _handle_message(self, msg: dict) -> None:
        if msg.get("e") == "error":
            log.warning("market_stream.error", msg=msg)
            return

        data = msg.get("data") or msg
        if data.get("e") != "kline":
            return

        k = data["k"]
        symbol = k["s"]
        kline = {
            "symbol": symbol,
            "interval": k["i"],
            "open_time_ms": k["t"],
            "close_time_ms": k["T"],
            "open": float(k["o"]),
            "high": float(k["h"]),
            "low": float(k["l"]),
            "close": float(k["c"]),
            "volume": float(k["v"]),
            "trades": int(k["n"]),
            "is_closed": bool(k["x"]),
            "received_at_ms": int(time.time() * 1000),
        }

        # Always publish a tick (last close); publish full kline on every update
        # so consumers can decide what to do with closed vs in-progress candles.
        tick = {
            "symbol": symbol,
            "timestamp_ms": kline["close_time_ms"],
            "price": kline["close"],
            "volume": kline["volume"],
            "source": "binance_testnet" if self.testnet else "binance",
        }

        await self.publisher.publish(self.STREAM_KLINES, kline)
        await self.publisher.publish(self.STREAM_TICKS, tick)


def stream_manager_from_settings(publisher: RedisStreamPublisher) -> MarketStreamManager:
    return MarketStreamManager(
        publisher,
        symbols=settings.pairs_list,
        interval=settings.default_timeframe,
        testnet=settings.binance_testnet,
    )


__all__ = ["MarketStreamManager", "stream_manager_from_settings"]


# Allow `python -m trading_engine.binance.ws_streams` for ad-hoc smoke testing.
async def _smoke() -> None:
    publisher = RedisStreamPublisher.from_url(settings.redis_url)
    manager = stream_manager_from_settings(publisher)
    await manager.start()
    try:
        await asyncio.sleep(60)
    finally:
        await manager.stop()
        await publisher.close()


if __name__ == "__main__":
    asyncio.run(_smoke())
