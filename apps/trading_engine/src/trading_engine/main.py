"""FastAPI entrypoint for the trading engine."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from trading_engine.api import (
    routes_admin,
    routes_health,
    routes_market,
    routes_orders,
    routes_strategies,
)
from trading_engine.binance.client import BinanceClient
from trading_engine.binance.ws_streams import stream_manager_from_settings
from trading_engine.config import settings
from trading_engine.engine_loop import StrategyLoop
from trading_engine.execution.order_router import OrderRouter
from trading_engine.execution.paper_broker import PaperBroker
from trading_engine.messaging.redis_publisher import RedisStreamPublisher
from trading_engine.risk.kill_switch import KillSwitch
from trading_engine.risk.manager import RiskConfig, RiskManager
from trading_engine.strategies.multi_signal import MultiSignalParams, MultiSignalStrategy


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

KILL_SWITCH = KillSwitch()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("trading_engine.startup", mode=settings.trading_mode.value, pairs=settings.pairs_list)

    if settings.is_live and settings.i_understand_risk != "yes":
        log.error("live_mode_blocked", reason="I_UNDERSTAND_RISK is not set to 'yes'")
        raise RuntimeError("Refusing to start in live mode without I_UNDERSTAND_RISK=yes")

    client = BinanceClient.from_settings(settings)
    app.state.binance = client
    app.state.kill_switch = KILL_SWITCH

    try:
        balance = await client.ping_and_balance()
        log.info("binance_connected", testnet=settings.binance_testnet, balance_keys=list(balance.keys()))
    except Exception as e:  # noqa: BLE001
        log.warning("binance_connect_failed", error=str(e))

    publisher = RedisStreamPublisher.from_url(settings.redis_url)
    app.state.redis_publisher = publisher

    stream_manager = stream_manager_from_settings(publisher)
    app.state.market_stream = stream_manager
    try:
        await stream_manager.start()
    except Exception as e:  # noqa: BLE001
        log.warning("market_stream_start_failed", error=str(e))

    risk_config = _load_risk_config()
    risk_manager = RiskManager(risk_config, kill_switch=KILL_SWITCH)
    paper_broker = PaperBroker(mode=settings.trading_mode.value)
    order_router = OrderRouter(risk=risk_manager, paper_broker=paper_broker, mode=settings.trading_mode.value)

    strategy = MultiSignalStrategy(MultiSignalParams(timeframe=settings.default_timeframe))
    loop = StrategyLoop(
        redis_url=settings.redis_url,
        strategy=strategy,
        order_router=order_router,
        timeframe=settings.default_timeframe,
    )
    app.state.strategy_loop = loop
    app.state.risk_manager = risk_manager

    try:
        await loop.start()
    except Exception as e:  # noqa: BLE001
        log.warning("strategy_loop_start_failed", error=str(e))

    yield

    log.info("trading_engine.shutdown")
    try:
        await loop.stop()
    except Exception as e:  # noqa: BLE001
        log.warning("strategy_loop_stop_failed", error=str(e))
    try:
        await stream_manager.stop()
    except Exception as e:  # noqa: BLE001
        log.warning("market_stream_stop_failed", error=str(e))
    await publisher.close()
    await client.close()


def _load_risk_config() -> RiskConfig:
    path = settings.risk_config_path
    if path and os.path.exists(path):
        try:
            return RiskConfig.from_yaml(path)
        except Exception as e:  # noqa: BLE001
            log.warning("risk_config_load_failed", error=str(e), path=path)
    return RiskConfig()


app = FastAPI(title="trading_engine", version="0.1.0", lifespan=lifespan)

app.include_router(routes_health.router)
app.include_router(routes_admin.router, prefix="/admin")
app.include_router(routes_orders.router, prefix="/orders")
app.include_router(routes_market.router, prefix="/market")
app.include_router(routes_strategies.router, prefix="/strategies")
