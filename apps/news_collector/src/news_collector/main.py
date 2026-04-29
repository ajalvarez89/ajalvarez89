"""News collector entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from news_collector.config import settings
from news_collector.messaging.news_publisher import NewsPublisher
from news_collector.scheduler import NewsPoller, PollerConfig


def _configure_logging() -> None:
    logging.basicConfig(level=settings.log_level.upper(), format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer(),
        ]
    )


_configure_logging()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    publisher = NewsPublisher.from_url(settings.redis_url)
    app.state.publisher = publisher

    poller = NewsPoller(
        publisher=publisher,
        config=PollerConfig(
            interval_sec=settings.news_poll_interval_sec,
            cryptopanic_api_key=settings.cryptopanic_api_key,
        ),
    )
    app.state.poller = poller
    if settings.cryptopanic_api_key:
        await poller.start()
        log.info("news_collector.started", interval_sec=settings.news_poll_interval_sec)
    else:
        log.warning("news_collector.no_api_key", note="Set CRYPTOPANIC_API_KEY to enable polling")

    yield

    await poller.stop()
    await publisher.close()


app = FastAPI(title="news_collector", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "news_collector",
        "version": "0.1.0",
        "cryptopanic_configured": bool(settings.cryptopanic_api_key),
        "poll_interval_sec": settings.news_poll_interval_sec,
    }


@app.post("/score")
async def score(payload: dict) -> dict:
    """Local lexicon-based scoring exposed for testing / offline use."""
    from news_collector.sentiment_lexicon import score_text

    text = payload.get("text", "")
    s = score_text(text)
    return {"label": s.label, "score": s.score, "pos_hits": s.pos_hits, "neg_hits": s.neg_hits}
