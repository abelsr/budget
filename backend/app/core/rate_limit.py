import time
from collections import defaultdict, deque
from threading import Lock
from typing import Callable

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    """Small fixed-window limiter for one Uvicorn process, keyed by route and client.

    Inactivity no longer leaks: every ``evict_interval_seconds`` a sweep drops
    keys whose newest attempt is already older than their window (i.e. keys
    whose whole bucket has elapsed). A key touched again after the sweep gets
    a fresh window. The sweep runs under the same lock as ``check`` and only
    iterates the (bounded) key table, so it is cheap even with many clients.

    Deployment note (issue #45): this limiter is per-process. With N Uvicorn
    workers the effective limit is N x the configured one, and the table
    resets on deploy. Endpoints that require auth (e.g. ticket scan) are
    keyed per household, not per IP, so one client cannot self-DoS other
    households; the unauthenticated auth routes can only be keyed by the
    directly connected IP.
    """

    def __init__(
        self,
        evict_interval_seconds: float = 300.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._windows: dict[str, int] = {}
        self._evict_interval = evict_interval_seconds
        self._clock = clock
        self._last_evict = clock()
        self._lock = Lock()

    def _evict_expired_locked(self, now: float) -> int:
        """Drop keys whose whole window has elapsed (or whose deque emptied)."""
        removed = 0
        for key in list(self._attempts):
            window = self._windows.get(key)
            if window is None:
                continue
            attempts = self._attempts[key]
            if not attempts or attempts[-1] + window <= now:
                del self._attempts[key]
                del self._windows[key]
                removed += 1
        return removed

    def evict_expired(self) -> int:
        """Drop all keys whose window has elapsed; returns how many were removed."""
        with self._lock:
            return self._evict_expired_locked(self._clock())

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = self._clock()
        with self._lock:
            if now - self._last_evict >= self._evict_interval:
                self._last_evict = now
                self._evict_expired_locked(now)
            attempts = self._attempts[key]
            self._windows[key] = window_seconds
            while attempts and attempts[0] <= now - window_seconds:
                attempts.popleft()
            if len(attempts) >= limit:
                retry_after = max(1, int(attempts[0] + window_seconds - now) + 1)
                raise HTTPException(
                    status_code=429,
                    detail="Demasiados intentos. Espera unos minutos antes de volver a intentarlo.",
                    headers={"Retry-After": str(retry_after)},
                )
            attempts.append(now)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()
            self._windows.clear()


limiter = InMemoryRateLimiter()


def client_ip(request: Request) -> str:
    # Trusting proxy forwarding headers belongs to the reverse-proxy deployment,
    # not the application: use the directly connected address here.
    return request.client.host if request.client is not None else "unknown"
