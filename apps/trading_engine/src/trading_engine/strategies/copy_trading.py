"""Copy-trading strategy stub.

Subscribes to the public Binance Futures Copy Trading leaderboard and
mirrors trades from a configured list of trader UUIDs into paper mode.

Phase 5 ships this as opt-in (disabled by default). It needs a separate
approval flag and is gated behind `ENABLE_COPY_TRADING=1`. The Binance
endpoints used here are public read-only.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import httpx
import structlog

from trading_engine.strategies.base import TradingSignal

log = structlog.get_logger(__name__)


@dataclass
class CopyTradingParams:
    enabled: bool = False
    trader_uids: list[str] = field(default_factory=list)
    poll_interval_sec: int = 60
    base_url: str = "https://www.binance.com"
    leaderboard_path: str = "/bapi/futures/v1/public/future/leaderboard/getOtherPosition"
    timeout_sec: float = 5.0
    fixed_notional_usdt: float = 10.0


class CopyTradingPoller:
    """Periodically fetches positions from each followed trader and emits
    `TradingSignal`s for the ones we don't already mirror."""

    name = "binance_copy"

    def __init__(self, params: CopyTradingParams, *, on_signal) -> None:
        self.params = params
        self.on_signal = on_signal
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._mirrored: dict[str, dict] = {}

    async def start(self) -> None:
        if not self.params.enabled or not self.params.trader_uids:
            log.info("copy_trading.disabled", enabled=self.params.enabled, n_uids=len(self.params.trader_uids))
            return
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="copy-trading-poller")
        log.info("copy_trading.started", trader_uids=self.params.trader_uids, interval=self.params.poll_interval_sec)

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception as e:  # noqa: BLE001
                log.warning("copy_trading.tick_error", error=str(e))
            await asyncio.sleep(self.params.poll_interval_sec)

    async def _tick(self) -> None:
        async with httpx.AsyncClient(timeout=self.params.timeout_sec) as client:
            for uid in self.params.trader_uids:
                positions = await self._fetch_positions(client, uid)
                for pos in positions:
                    await self._maybe_emit(uid, pos)

    async def _fetch_positions(self, client: httpx.AsyncClient, uid: str) -> list[dict]:
        url = f"{self.params.base_url}{self.params.leaderboard_path}"
        try:
            resp = await client.post(url, json={"encryptedUid": uid, "tradeType": "PERPETUAL"})
            if resp.status_code != 200:
                return []
            data = resp.json().get("data") or {}
            return data.get("otherPositionRetList") or []
        except httpx.HTTPError:
            return []

    async def _maybe_emit(self, uid: str, pos: dict) -> None:
        symbol = pos.get("symbol")
        if not symbol:
            return
        # Only spot pairs we already trade.
        if not symbol.endswith("USDT"):
            return

        side = "buy" if (pos.get("amount", 0) or 0) > 0 else "sell"
        key = f"{uid}:{symbol}"
        prev = self._mirrored.get(key)
        if prev and prev.get("side") == side:
            return  # already mirrored this side

        self._mirrored[key] = {"side": side, "amount": pos.get("amount", 0)}

        last = float(pos.get("markPrice") or pos.get("entryPrice") or 0.0)
        if last <= 0:
            return

        signal = TradingSignal(
            symbol=symbol,
            side=side,
            confidence=0.5,
            horizon_minutes=240,
            target_price=last,
            stop_loss=last * (0.98 if side == "buy" else 1.02),
            take_profit=last * (1.04 if side == "buy" else 0.96),
            strategy=self.name,
        )

        log.info("copy_trading.signal", uid=uid, symbol=symbol, side=side, last=last)
        await self.on_signal(signal, last)
