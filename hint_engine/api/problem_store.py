"""Store mapping opaque problem ids to generated correct answers.

Practice mode keeps the answer server-side: ``generateProblem`` stores the correct
answer here and returns only an opaque ``problemId``, so the answer never reaches the
browser. The id is used purely for server-side correctness gating *before* the
answer-blind hint is generated.

Two backends, one Protocol (chosen by env, like the LLM providers):

* **in-memory** (default) — process-local, offline, zero setup. Fine for the dev
  server / demo, but not shared across workers and lost on restart.
* **Redis** (``REDIS_URL`` set) — shared across workers/instances, with a TTL so
  answers expire. The answer still never travels to the client.
"""

from __future__ import annotations

import os
import uuid
from collections import OrderedDict
from typing import Protocol, runtime_checkable

# One hour: long enough to solve a problem, short enough not to accumulate answers.
DEFAULT_TTL_SECONDS = 3600


@runtime_checkable
class ProblemStore(Protocol):
    """Opaque-id -> correct-answer store. Implementations must not encode the answer
    in the id (it would defeat the point)."""

    def put(self, correct_answer: str) -> str:
        """Store an answer and return a fresh opaque id for it."""

    def get(self, problem_id: str) -> str | None:
        """Return the stored answer for an id, or None if unknown/expired."""


class InMemoryProblemStore:
    """Bounded, process-local id -> answer map with FIFO eviction of oldest entries."""

    def __init__(self, max_size: int = 1000) -> None:
        self._max_size = max_size
        self._items: OrderedDict[str, str] = OrderedDict()

    def put(self, correct_answer: str) -> str:
        problem_id = uuid.uuid4().hex
        self._items[problem_id] = correct_answer  # fresh uuid key inserts at the end
        while len(self._items) > self._max_size:
            self._items.popitem(last=False)
        return problem_id

    def get(self, problem_id: str) -> str | None:
        return self._items.get(problem_id)


class RedisProblemStore:
    """Shared id -> answer store backed by Redis, with per-key TTL.

    Takes an injected client (any object with ``set(name, value, ex=...)`` and
    ``get(name)``) so it is testable without a running Redis.
    """

    def __init__(
        self,
        client: object,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        key_prefix: str = "nudgemath:problem:",
    ) -> None:
        self._client = client
        self._ttl = ttl_seconds
        self._prefix = key_prefix

    def put(self, correct_answer: str) -> str:
        problem_id = uuid.uuid4().hex
        self._client.set(self._prefix + problem_id, correct_answer, ex=self._ttl)
        return problem_id

    def get(self, problem_id: str) -> str | None:
        value = self._client.get(self._prefix + problem_id)
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)


def build_problem_store() -> ProblemStore:
    """Select the backend from the environment: Redis if ``REDIS_URL`` is set, else
    in-memory. ``redis`` is imported lazily so the offline default needs no dependency.
    """
    url = os.environ.get("REDIS_URL")
    if url and url.strip():
        import redis  # lazy: only needed when a shared store is configured

        client = redis.Redis.from_url(url.strip(), decode_responses=True)
        return RedisProblemStore(client)
    return InMemoryProblemStore()


PROBLEM_STORE: ProblemStore = build_problem_store()
