from collections import defaultdict, deque
from threading import Lock
import time


class FixedWindowRateLimiter:
    def __init__(self):
        self._lock = Lock()
        self._windows = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.monotonic()

        with self._lock:
            q = self._windows[key]

            cutoff = now - window_seconds
            while q and q[0] <= cutoff:
                q.popleft()

            if len(q) >= limit:
                return False

            q.append(now)
            return True


rate_limiter = FixedWindowRateLimiter()
