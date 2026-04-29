"""Normalizer + deduper for incoming news items.

Deduplication is by stable hash of (source, url, title) over a sliding window
kept in-memory. Phase 4 keeps it local-only; Phase 5+ may persist seen IDs in
Redis for restarts.
"""
from __future__ import annotations

import hashlib
import time
from collections import OrderedDict


class Deduper:
    def __init__(self, *, ttl_seconds: int = 24 * 3600, max_items: int = 50_000) -> None:
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._seen: OrderedDict[str, float] = OrderedDict()

    def is_new(self, item: dict) -> bool:
        key = self._key(item)
        now = time.time()
        # purge expired
        if self._seen and (now - next(iter(self._seen.values()))) > self.ttl:
            cutoff = now - self.ttl
            keys_to_drop = [k for k, t in self._seen.items() if t < cutoff]
            for k in keys_to_drop:
                self._seen.pop(k, None)
        if key in self._seen:
            return False
        self._seen[key] = now
        if len(self._seen) > self.max_items:
            self._seen.popitem(last=False)
        return True

    @staticmethod
    def _key(item: dict) -> str:
        text = f"{item.get('source','?')}|{item.get('url','?')}|{item.get('title','?')}"
        return hashlib.sha1(text.encode("utf-8")).hexdigest()
