"""Lightweight async Redis Streams publisher.

Uses redis.asyncio. Each XADD includes MAXLEN ~ N to cap memory growth without
requiring a separate retention process.
"""
from __future__ import annotations

import json
from typing import Any

import structlog
from redis import asyncio as aioredis

log = structlog.get_logger(__name__)


class RedisStreamPublisher:
    DEFAULT_MAXLEN = 10_000

    def __init__(self, client: aioredis.Redis, *, default_maxlen: int = DEFAULT_MAXLEN) -> None:
        self._client = client
        self._default_maxlen = default_maxlen

    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> "RedisStreamPublisher":
        client = aioredis.from_url(url, decode_responses=True)
        return cls(client, **kwargs)

    async def publish(self, stream: str, payload: dict, *, maxlen: int | None = None) -> str:
        """Append to `stream` with approximate trimming. Returns the entry ID."""
        # Stream entries take key/value pairs; we serialize the whole payload as JSON
        # to keep schemas close to the JSON Schemas under /contracts.
        entry = {"data": json.dumps(payload, separators=(",", ":"))}
        return await self._client.xadd(
            stream,
            entry,
            maxlen=maxlen or self._default_maxlen,
            approximate=True,
        )

    async def close(self) -> None:
        await self._client.aclose()
