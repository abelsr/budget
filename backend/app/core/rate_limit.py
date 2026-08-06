from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    """Small fixed-window limiter for one Uvicorn process, keyed by route and client."""

    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = monotonic()
        with self._lock:
            attempts = self._attempts[key]
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


limiter = InMemoryRateLimiter()


def client_ip(request: Request) -> str:
    # Trusting proxy forwarding headers belongs to the reverse-proxy deployment,
    # not the application: use the directly connected address here.
    return request.client.host if request.client is not None else "unknown"
