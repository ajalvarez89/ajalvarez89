"""Periodic poller that wires CryptoPanic -> dedupe -> sentiment -> Redis."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog

from news_collector.messaging.news_publisher import NewsPublisher
from news_collector.normalizer import Deduper
from news_collector.sentiment_lexicon import score_text
from news_collector.sources.cryptopanic import CryptoPanicClient, CryptoPanicConfig

log = structlog.get_logger(__name__)


@dataclass
class PollerConfig:
    interval_sec: int = 60
    currencies: tuple[str, ...] = ("BTC", "ETH", "SOL")
    cryptopanic_api_key: str = ""


class NewsPoller:
    def __init__(self, *, publisher: NewsPublisher, config: PollerConfig) -> None:
        self.publisher = publisher
        self.config = config
        self.deduper = Deduper()
        self.cp = CryptoPanicClient(CryptoPanicConfig(api_key=config.cryptopanic_api_key))
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="news-poller")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception as e:  # noqa: BLE001
                log.warning("news_poller.tick_error", error=str(e))
            await asyncio.sleep(self.config.interval_sec)

    async def _tick(self) -> None:
        items = self.cp.fetch_recent(currencies=self.config.currencies)
        for item in items:
            if not self.deduper.is_new(item):
                continue
            await self.publisher.publish_raw(item)

            # Inline lexicon scoring; ml_service can re-score with FinBERT later.
            text = (item.get("title") or "") + " " + (item.get("summary") or "")
            score = score_text(text)
            scored = {
                **item,
                "sentiment": {
                    "label": score.label,
                    "score": score.score,
                    "model": "lexicon-v0",
                },
            }
            await self.publisher.publish_scored(scored)

        log.info("news_poller.tick", new_items=len(items))
