"""FastAPI entrypoint for the trading engine."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from trading_engine.api import routes_admin, routes_health, routes_orders
from trading_engine.binance.client import BinanceClient
from trading_engine.config import settings


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
    log.info("trading_engine.startup", mode=settings.trading_mode.value, pairs=settings.pairs_list)

    if settings.is_live and settings.i_understand_risk != "yes":
        log.error("live_mode_blocked", reason="I_UNDERSTAND_RISK is not set to 'yes'")
        raise RuntimeError("Refusing to start in live mode without I_UNDERSTAND_RISK=yes")

    client = BinanceClient.from_settings(settings)
    app.state.binance = client

    try:
        balance = await client.ping_and_balance()
        log.info("binance_connected", testnet=settings.binance_testnet, balance_keys=list(balance.keys()))
    except Exception as e:  # noqa: BLE001
        log.warning("binance_connect_failed", error=str(e))

    yield

    log.info("trading_engine.shutdown")


app = FastAPI(title="trading_engine", version="0.1.0", lifespan=lifespan)

app.include_router(routes_health.router)
app.include_router(routes_admin.router, prefix="/admin")
app.include_router(routes_orders.router, prefix="/orders")
