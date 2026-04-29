"""Sentiment filter — blocks entries when recent news lean strongly against the trade.

Subscribes to Redis Stream `news.scored` and keeps a small per-symbol rolling
average of the sentiment score. When evaluating a signal, it asks: is the
average over the last `window_minutes` minutes opposed to the trade direction
above `block_threshold` (in absolute value)? If so, return None.

This filter never opens trades by itself.
"""
from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque

import structlog
from redis import asyncio as aioredis

log = structlog.get_logger(__name__)


@dataclass
class SentimentFilterParams:
    redis_url: str = "redis://redis:6379/0"
    window_seconds: int = 6 * 3600
    block_threshold: float = 0.6  # only block when sentiment is strongly opposite
    min_items: int = 5


class SentimentBuffer:
    """Per-symbol rolling buffer of (timestamp_ms, score) tuples."""

    def __init__(self, params: SentimentFilterParams) -> None:
        self.params = params
        self._items: dict[str, Deque[tuple[int, float]]] = defaultdict(lambda: deque(maxlen=500))
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._redis: aioredis.Redis | None = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._redis = aioredis.from_url(self.params.redis_url, decode_responses=True)
        self._task = asyncio.create_task(self._run(), name="sentiment-buffer")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    def aggregate(self, symbol: str) -> tuple[int, float] | None:
        cutoff = int((time.time() - self.params.window_seconds) * 1000)
        items = [s for ts, s in self._items.get(_base(symbol), ()) if ts >= cutoff]
        if len(items) < self.params.min_items:
            return None
        return (len(items), sum(items) / len(items))

    async def _run(self) -> None:
        last_id = "$"
        assert self._redis is not None
        while not self._stop.is_set():
            try:
                resp = await self._redis.xread({"news.scored": last_id}, block=5_000, count=200)
            except Exception as e:  # noqa: BLE001
                log.warning("sentiment_buffer.xread_error", error=str(e))
                await asyncio.sleep(2.0)
                continue
            if not resp:
                continue
            for _stream, entries in resp:
                for entry_id, fields in entries:
                    last_id = entry_id
                    payload = self._decode(fields)
                    if payload is None:
                        continue
                    score = (payload.get("sentiment") or {}).get("score")
                    if score is None:
                        continue
                    ts = int(payload.get("published_at_ms") or time.time() * 1000)
                    for sym in payload.get("symbols") or []:
                        if not sym:
                            continue
                        self._items[sym.upper()].append((ts, float(score)))

    @staticmethod
    def _decode(fields):
        if isinstance(fields, dict):
            data = fields.get("data")
        else:
            d = dict(zip(fields[::2], fields[1::2]))
            data = d.get("data")
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None


def _base(symbol: str) -> str:
    """Map BTCUSDT -> BTC for matching news currencies."""
    s = symbol.upper()
    for q in ("USDT", "BUSD", "USDC", "USD", "BTC", "ETH"):
        if s.endswith(q) and len(s) > len(q):
            return s[: -len(q)]
    return s


class SentimentFilter:
    """Reads from a SentimentBuffer and blocks signals that disagree strongly."""

    def __init__(self, buffer: SentimentBuffer, params: SentimentFilterParams | None = None) -> None:
        self.buffer = buffer
        self.params = params or buffer.params

    def should_block(self, symbol: str, side: str) -> tuple[bool, str | None]:
        agg = self.buffer.aggregate(symbol)
        if agg is None:
            return False, None
        n, avg = agg
        if side == "buy" and avg <= -self.params.block_threshold:
            return True, f"sentiment_avg={avg:.2f} (n={n}) opposes long"
        if side == "sell" and avg >= self.params.block_threshold:
            return True, f"sentiment_avg={avg:.2f} (n={n}) opposes short"
        return False, None
