"""Token-bucket rate limiting for the unauthenticated surface.

The student-facing LLM mutations and the ``login`` mutation are reachable with no
token. Each LLM call spends real money (or the admin's connected Claude
subscription quota), and each login attempt spends ~16 MB of scrypt work — so
both need a ceiling before they face a network.

Buckets are in-memory and **per-process**: with multiple uvicorn workers each
worker gets its own allowance. That still bounds total spend (workers × limit)
and needs no external dependency, matching the offline-by-default posture of the
in-memory ``ProblemStore``. The key set is bounded (LRU) so a client rotating
addresses cannot grow it without limit.
"""

from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from collections.abc import Callable


class RateLimitExceeded(RuntimeError):
    """Raised when a client has exhausted its allowance for a bucket."""


class _Bucket:
    __slots__ = ("tokens", "updated_at")

    def __init__(self, tokens: float, updated_at: float) -> None:
        self.tokens = tokens
        self.updated_at = updated_at


class RateLimiter:
    """Fixed-capacity token bucket per key, refilled continuously.

    ``capacity`` is the burst allowance; ``per_minute`` is the sustained rate.
    Thread-safe: resolvers run on a thread pool, and the buckets are shared.
    """

    def __init__(
        self,
        *,
        capacity: int,
        per_minute: float,
        max_keys: int = 4096,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if capacity < 1 or per_minute <= 0:
            raise ValueError("capacity must be >= 1 and per_minute > 0")
        self._capacity = float(capacity)
        self._refill_per_second = per_minute / 60.0
        self._max_keys = max_keys
        self._clock = clock
        self._lock = threading.Lock()
        self._buckets: OrderedDict[str, _Bucket] = OrderedDict()

    def allow(self, key: str) -> bool:
        """Consume one token for ``key``; False when the bucket is empty."""
        with self._lock:
            now = self._clock()
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(self._capacity, now)
                self._buckets[key] = bucket
            else:
                elapsed = max(0.0, now - bucket.updated_at)
                bucket.tokens = min(
                    self._capacity, bucket.tokens + elapsed * self._refill_per_second
                )
                bucket.updated_at = now
            self._buckets.move_to_end(key)
            # Bound memory: a client rotating keys must not grow the map forever.
            while len(self._buckets) > self._max_keys:
                self._buckets.popitem(last=False)
            if bucket.tokens < 1.0:
                return False
            bucket.tokens -= 1.0
            return True

    def check(self, key: str, *, message: str) -> None:
        """Consume one token or raise :class:`RateLimitExceeded`."""
        if not self.allow(key):
            raise RateLimitExceeded(message)

    def reset(self) -> None:
        """Forget every bucket (tests, and admin recovery)."""
        with self._lock:
            self._buckets.clear()


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 1 else default


def rate_limiting_enabled() -> bool:
    """Read at call time so tests (and ops) can toggle without reimporting."""
    return os.environ.get("NUDGEMATH_RATE_LIMIT", "").strip().lower() not in {
        "0",
        "false",
        "off",
    }


class _ToggleableLimiter(RateLimiter):
    """A limiter that is a no-op while rate limiting is disabled by env."""

    def allow(self, key: str) -> bool:
        if not rate_limiting_enabled():
            return True
        return super().allow(key)


# Public LLM mutations: generateHint / transcribeProblem / generateProblem.
# Each is one paid model call; the burst covers a student's normal back-and-forth.
LLM_LIMITER = _ToggleableLimiter(
    capacity=_env_int("NUDGEMATH_LLM_RATE_BURST", 10),
    per_minute=_env_int("NUDGEMATH_LLM_RATE_PER_MINUTE", 20),
)

# Login: brute-force ceiling *and* a cap on unauthenticated scrypt work.
LOGIN_LIMITER = _ToggleableLimiter(
    capacity=_env_int("NUDGEMATH_LOGIN_RATE_BURST", 5),
    per_minute=_env_int("NUDGEMATH_LOGIN_RATE_PER_MINUTE", 5),
)


def reset_all() -> None:
    LLM_LIMITER.reset()
    LOGIN_LIMITER.reset()
