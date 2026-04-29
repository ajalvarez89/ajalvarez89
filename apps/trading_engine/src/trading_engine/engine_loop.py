"""Strategy loop.

Consumes the `market.klines` Redis stream, maintains a per-symbol candle
buffer, runs the active strategy on each closed candle, and dispatches
signals to the order router.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict, deque
from typing import Deque

import structlog
from redis import asyncio as aioredis

from trading_engine.execution.order_router import OrderRouter
from trading_engine.persistence import repos
from trading_engine.persistence.db import session_scope
from trading_engine.risk.manager import RiskState
from trading_engine.strategies.multi_signal import MultiSignalStrategy
from trading_engine.strategies.sentiment_filter import SentimentFilter

log = structlog.get_logger(__name__)


class StrategyLoop:
    BUFFER_LEN = 400  # enough for EMA200 + tail

    def __init__(
        self,
        *,
        redis_url: str,
        strategy: MultiSignalStrategy,
        order_router: OrderRouter,
        timeframe: str,
        starting_equity: float = 10_000.0,
        sentiment_filter: SentimentFilter | None = None,
    ) -> None:
        self._redis = aioredis.from_url(redis_url, decode_responses=True)
        self.strategy = strategy
        self.order_router = order_router
        self.timeframe = timeframe
        self.starting_equity = starting_equity
        self.sentiment_filter = sentiment_filter
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._buffers: dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=self.BUFFER_LEN))
        self._last_processed_open: dict[str, int] = {}

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="strategy-loop")
        log.info("strategy_loop.started", strategy=self.strategy.name, timeframe=self.timeframe)

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._redis.aclose()

    async def _run(self) -> None:
        last_id = "$"  # only new entries
        while not self._stop.is_set():
            try:
                resp = await self._redis.xread({"market.klines": last_id}, block=5_000, count=200)
            except Exception as e:  # noqa: BLE001
                log.warning("strategy_loop.xread_error", error=str(e))
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
                    if payload.get("interval") != self.timeframe:
                        continue
                    await self._on_kline(payload)

    async def _on_kline(self, k: dict) -> None:
        symbol = k["symbol"]
        buf = self._buffers[symbol]

        # Replace last in-progress candle if same open_time, else append.
        if buf and buf[-1].get("open_time_ms") == k["open_time_ms"]:
            buf[-1] = k
        else:
            buf.append(k)

        if not k.get("is_closed"):
            return  # only run on closed candles to avoid intra-bar churn

        # Skip duplicate close events for the same candle
        if self._last_processed_open.get(symbol) == k["open_time_ms"]:
            return
        self._last_processed_open[symbol] = k["open_time_ms"]

        signal = self.strategy.evaluate(symbol, list(buf))
        if signal is None:
            return

        if self.sentiment_filter is not None:
            blocked, reason = self.sentiment_filter.should_block(symbol, signal.side)
            if blocked:
                log.info("signal_blocked_by_sentiment", symbol=symbol, side=signal.side, reason=reason)
                return

        log.info("signal_emitted", symbol=symbol, side=signal.side, strategy=signal.strategy)

        state = await self._build_state()
        await self.order_router.handle(signal, state=state, last_price=float(k["close"]))

    async def _build_state(self) -> RiskState:
        async with session_scope() as s:
            open_positions = len(await repos.list_open_positions(s))
        # Phase 2 simplification: equity tracked from a fixed starting balance + sum(realized_pnl).
        # Phase 5 will wire live equity from the broker.
        equity = self.starting_equity
        async with session_scope() as s:
            trades = await repos.list_recent_trades(s, limit=10_000)
        realized = sum((t.realized_pnl or 0.0) for t in trades)
        return RiskState(
            equity=equity + realized,
            open_positions=open_positions,
            consecutive_losses=_consecutive_losses(trades),
            daily_pnl=realized,
            daily_starting_equity=equity,
        )

    @staticmethod
    def _decode(fields: dict | list) -> dict | None:
        if isinstance(fields, dict):
            data = fields.get("data")
        else:
            # list form
            d = dict(zip(fields[::2], fields[1::2]))
            data = d.get("data")
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None


def _consecutive_losses(trades) -> int:
    n = 0
    for t in trades:  # already ordered by executed_at desc
        if t.realized_pnl is None:
            continue
        if t.realized_pnl < 0:
            n += 1
        else:
            break
    return n
