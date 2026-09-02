"""Eviction behaviour of the in-memory rate limiter (issue #45).

Before #45, ``InMemoryRateLimiter._attempts`` never dropped inactive keys, so
a long-running process would accumulate one entry per client IP forever
(memory leak). These tests pin the fix using an injected fake clock so the
window can be advanced deterministically without sleeping.
"""

from fastapi import HTTPException

from app.core.rate_limit import InMemoryRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def test_inactivity_evicts_keys_on_sweep():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(evict_interval_seconds=10, clock=clock)

    # Three clients touch the limiter.
    for key in ("a", "b", "c"):
        limiter.check(key, limit=5, window_seconds=60)
    assert len(limiter._attempts) == 3

    # Let every window elapse (60s) and cross the 10s evict interval.
    clock.advance(120)
    limiter.check("d", limit=5, window_seconds=60)  # triggers the sweep

    # a/b/c are gone; only the just-used key "d" remains.
    assert set(limiter._attempts) == {"d"}
    assert set(limiter._windows) == {"d"}


def test_expired_key_gets_fresh_window_after_eviction():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(evict_interval_seconds=10, clock=clock)

    # Exhaust the bucket: 5 of 5 used within the window.
    for _ in range(5):
        limiter.check("login:1.2.3.4", limit=5, window_seconds=60)
    try:
        limiter.check("login:1.2.3.4", limit=5, window_seconds=60)
        raise AssertionError("expected 429")
    except HTTPException as exc:
        assert exc.status_code == 429

    # After the window elapses the sweep drops the key, so the next attempt
    # starts a fresh window instead of staying throttled forever.
    clock.advance(120)
    limiter.check("login:1.2.3.4", limit=5, window_seconds=60)  # sweep + fresh hit
    # One of the 5 budget used again; the other 4 still available.
    for _ in range(4):
        limiter.check("login:1.2.3.4", limit=5, window_seconds=60)
    try:
        limiter.check("login:1.2.3.4", limit=5, window_seconds=60)
        raise AssertionError("expected 429 after re-filling the bucket")
    except HTTPException as exc:
        assert exc.status_code == 429


def test_evict_expired_reports_removed_count():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(evict_interval_seconds=10, clock=clock)

    limiter.check("x", limit=1, window_seconds=30)
    clock.advance(60)
    assert limiter.evict_expired() == 1
    assert limiter._attempts == {}

    # Nothing left to evict on a second call.
    assert limiter.evict_expired() == 0


def test_active_key_is_not_evicted():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(evict_interval_seconds=10, clock=clock)

    limiter.check("hot", limit=5, window_seconds=60)
    # Cross the evict interval but NOT the window: "hot" is still in-window.
    clock.advance(30)
    limiter.check("other", limit=5, window_seconds=60)  # sweeps

    assert "hot" in limiter._attempts
    assert "other" in limiter._attempts
