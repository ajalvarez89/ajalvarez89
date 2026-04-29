"""CryptoPanic API client.

Free tier: https://cryptopanic.com/developers/api/
We use the public endpoint and respect ?auth_token=<key> when configured.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

import httpx
import structlog

log = structlog.get_logger(__name__)


@dataclass
class CryptoPanicConfig:
    api_key: str = ""
    base_url: str = "https://cryptopanic.com/api/v1"
    public_endpoint: str = "/posts/"
    timeout_sec: float = 10.0


class CryptoPanicClient:
    def __init__(self, cfg: CryptoPanicConfig) -> None:
        self.cfg = cfg

    def fetch_recent(self, *, currencies: Iterable[str] | None = None, kind: str = "news", limit: int = 50) -> list[dict]:
        if not self.cfg.api_key:
            log.debug("cryptopanic.no_api_key, skipping")
            return []

        params: dict[str, str] = {
            "auth_token": self.cfg.api_key,
            "kind": kind,
            "public": "true",
        }
        if currencies:
            params["currencies"] = ",".join(currencies)

        url = f"{self.cfg.base_url}{self.cfg.public_endpoint}"
        try:
            with httpx.Client(timeout=self.cfg.timeout_sec) as client:
                resp = client.get(url, params=params)
            if resp.status_code != 200:
                log.warning("cryptopanic.bad_status", status=resp.status_code, body=resp.text[:200])
                return []
            data = resp.json().get("results", [])
        except httpx.HTTPError as e:
            log.warning("cryptopanic.http_error", error=str(e))
            return []

        return [self._normalize(item) for item in data[:limit] if item]

    def _normalize(self, raw: dict) -> dict:
        currencies = [c.get("code") for c in (raw.get("currencies") or []) if c.get("code")]
        published = raw.get("published_at")
        ts = _to_ms(published) if published else int(time.time() * 1000)
        return {
            "id": raw.get("id") or raw.get("url"),
            "source": "cryptopanic",
            "title": raw.get("title", ""),
            "url": raw.get("url"),
            "summary": (raw.get("metadata") or {}).get("description"),
            "symbols": currencies,
            "published_at_ms": ts,
            "votes": raw.get("votes"),
        }


def _to_ms(iso: str) -> int:
    from datetime import datetime
    try:
        return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return int(time.time() * 1000)
