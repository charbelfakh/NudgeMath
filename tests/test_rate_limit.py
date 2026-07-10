"""Tests for the token-bucket rate limiter (no sleeping — the clock is injected)."""

from __future__ import annotations

import pytest

from hint_engine.rate_limit import RateLimiter, RateLimitExceeded


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_burst_capacity_then_denies():
    clock = _FakeClock()
    limiter = RateLimiter(capacity=3, per_minute=60, clock=clock)
    assert [limiter.allow("a") for _ in range(3)] == [True, True, True]
    assert limiter.allow("a") is False  # bucket empty


def test_refills_over_time():
    clock = _FakeClock()
    limiter = RateLimiter(capacity=2, per_minute=60, clock=clock)  # 1 token/second
    assert limiter.allow("a") and limiter.allow("a")
    assert limiter.allow("a") is False

    clock.advance(1.0)
    assert limiter.allow("a") is True  # one token refilled
    assert limiter.allow("a") is False

    clock.advance(30.0)  # would refill 30, but capacity caps at 2
    assert limiter.allow("a") and limiter.allow("a")
    assert limiter.allow("a") is False


def test_keys_are_independent():
    clock = _FakeClock()
    limiter = RateLimiter(capacity=1, per_minute=60, clock=clock)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    assert limiter.allow("b") is True  # b has its own bucket


def test_key_set_is_bounded_lru():
    """A client rotating addresses must not grow the bucket map without limit."""
    clock = _FakeClock()
    limiter = RateLimiter(capacity=1, per_minute=60, max_keys=2, clock=clock)
    limiter.allow("a")
    limiter.allow("b")
    limiter.allow("c")  # evicts the least-recently-used ("a")
    assert len(limiter._buckets) == 2
    assert limiter.allow("a") is True  # a's bucket was evicted, so it starts fresh


def test_check_raises_with_message():
    limiter = RateLimiter(capacity=1, per_minute=60)
    limiter.check("a", message="slow down")
    with pytest.raises(RateLimitExceeded, match="slow down"):
        limiter.check("a", message="slow down")


def test_reset_clears_buckets():
    limiter = RateLimiter(capacity=1, per_minute=60)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    limiter.reset()
    assert limiter.allow("a") is True


def test_rejects_nonsense_configuration():
    with pytest.raises(ValueError):
        RateLimiter(capacity=0, per_minute=60)
    with pytest.raises(ValueError):
        RateLimiter(capacity=1, per_minute=0)


def test_env_toggle_disables_limiting(monkeypatch):
    from hint_engine import rate_limit

    monkeypatch.setenv("NUDGEMATH_RATE_LIMIT", "off")
    limiter = rate_limit.LLM_LIMITER
    # Far beyond any configured burst; every call is allowed while disabled.
    assert all(limiter.allow("someone") for _ in range(100))
