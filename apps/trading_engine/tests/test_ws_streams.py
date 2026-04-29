"""Unit test for the kline message handler — verifies the Redis payloads
without touching Binance or a real Redis."""
from __future__ import annotations

import asyncio
import json

import pytest

from trading_engine.binance.ws_streams import MarketStreamManager


class _FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, stream: str, payload: dict, **_: object) -> str:
        self.events.append((stream, payload))
        return "0-0"


@pytest.mark.asyncio
async def test_handle_message_publishes_kline_and_tick():
    publisher = _FakePublisher()
    mgr = MarketStreamManager(publisher, symbols=["BTCUSDT"], interval="1m", testnet=True)

    msg = {
        "stream": "btcusdt@kline_1m",
        "data": {
            "e": "kline",
            "E": 1700000000000,
            "s": "BTCUSDT",
            "k": {
                "t": 1700000000000,
                "T": 1700000059999,
                "s": "BTCUSDT",
                "i": "1m",
                "o": "30000.00",
                "c": "30050.00",
                "h": "30100.00",
                "l": "29950.00",
                "v": "12.5",
                "n": 47,
                "x": False,
                "q": "375312.5",
                "V": "6.0",
                "Q": "180000",
                "B": "0",
            },
        },
    }

    await mgr._handle_message(msg)

    streams = [s for s, _ in publisher.events]
    assert MarketStreamManager.STREAM_KLINES in streams
    assert MarketStreamManager.STREAM_TICKS in streams

    kline_payload = next(p for s, p in publisher.events if s == MarketStreamManager.STREAM_KLINES)
    assert kline_payload["symbol"] == "BTCUSDT"
    assert kline_payload["interval"] == "1m"
    assert kline_payload["close"] == 30050.0
    assert kline_payload["is_closed"] is False

    tick_payload = next(p for s, p in publisher.events if s == MarketStreamManager.STREAM_TICKS)
    assert tick_payload["symbol"] == "BTCUSDT"
    assert tick_payload["price"] == 30050.0
    assert tick_payload["source"] == "binance_testnet"


@pytest.mark.asyncio
async def test_handle_message_ignores_non_kline():
    publisher = _FakePublisher()
    mgr = MarketStreamManager(publisher, symbols=["BTCUSDT"], interval="1m")

    await mgr._handle_message({"stream": "x", "data": {"e": "trade", "s": "BTCUSDT"}})
    await mgr._handle_message({"e": "error", "m": "boom"})

    assert publisher.events == []
