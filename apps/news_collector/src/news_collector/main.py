"""News collector entrypoint."""
from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI

from news_collector.config import settings


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

app = FastAPI(title="news_collector", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "news_collector",
        "version": "0.1.0",
        "cryptopanic_configured": bool(settings.cryptopanic_api_key),
    }
