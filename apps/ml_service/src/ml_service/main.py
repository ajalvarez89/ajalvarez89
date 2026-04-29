"""FastAPI entrypoint for the ML service."""
from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI

from ml_service.config import settings
from ml_service.inference import server as inference_server


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

app = FastAPI(title="ml_service", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "ml_service", "version": "0.1.0"}


app.include_router(inference_server.router, prefix="/inference")


@app.get("/backtests")
async def list_backtests() -> dict:
    from ml_service.backtest.listing import list_runs
    return {"runs": list_runs()}
