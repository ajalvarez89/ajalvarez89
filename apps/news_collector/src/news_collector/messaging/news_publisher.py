"""Redis Streams publisher for news items."""
from __future__ import annotations

import json
from typing import Any

from redis import asyncio as aioredis


STREAM_RAW = "news.raw"
STREAM_SCORED = "news.scored"


class NewsPublisher:
    def __init__(self, client: aioredis.Redis, *, default_maxlen: int = 5_000) -> None:
        self._client = client
        self._maxlen = default_maxlen

    @classmethod
    def from_url(cls, url: str) -> "NewsPublisher":
        client = aioredis.from_url(url, decode_responses=True)
        return cls(client)

    async def publish_raw(self, item: dict) -> str:
        return await self._publish(STREAM_RAW, item)

    async def publish_scored(self, item: dict) -> str:
        return await self._publish(STREAM_SCORED, item)

    async def _publish(self, stream: str, payload: dict) -> str:
        return await self._client.xadd(
            stream,
            {"data": json.dumps(payload, separators=(",", ":"))},
            maxlen=self._maxlen,
            approximate=True,
        )

    async def close(self) -> None:
        await self._client.aclose()
