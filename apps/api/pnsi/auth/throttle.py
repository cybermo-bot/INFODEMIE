"""Login throttling per account, in process memory.

Enough for one API process in dev and demo. The pilot needs a shared store
(Redis) when several API workers run.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class LoginThrottle:
    def __init__(self, max_failures: int = 5, window_seconds: int = 900) -> None:
        self.max_failures = max_failures
        self.window = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._failures[key]
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def retry_after(self, key: str, now: float | None = None) -> int | None:
        """Seconds to wait if the key is blocked, else None."""
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._prune(key, now)
            if len(q) >= self.max_failures:
                return max(1, int(self.window - (now - q[0])))
        return None

    def record_failure(self, key: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


login_throttle = LoginThrottle()
