"""In-memory kill switch (Phase 0).

Phase 2 will persist `engaged` state in SQLite for crash-recovery.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone


class KillSwitch:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._engaged = False
        self._reason: str | None = None
        self._engaged_at: datetime | None = None

    def engage(self, reason: str) -> None:
        with self._lock:
            self._engaged = True
            self._reason = reason
            self._engaged_at = datetime.now(timezone.utc)

    def disengage(self) -> None:
        with self._lock:
            self._engaged = False
            self._reason = None
            self._engaged_at = None

    def is_engaged(self) -> bool:
        with self._lock:
            return self._engaged

    def status(self) -> dict:
        with self._lock:
            return {
                "engaged": self._engaged,
                "reason": self._reason,
                "engaged_at": self._engaged_at.isoformat() if self._engaged_at else None,
            }
