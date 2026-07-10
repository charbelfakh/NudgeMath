from hint_engine.api.problem_store import (
    InMemoryProblemStore,
    ProblemStore,
    RedisProblemStore,
    build_problem_store,
)


class FakeRedis:
    """Minimal dict-backed stand-in for a redis client (set/get with ex kwarg)."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def set(self, name: str, value: str, ex: int | None = None) -> None:
        self.store[name] = value
        if ex is not None:
            self.ttls[name] = ex

    def get(self, name: str):
        return self.store.get(name)


# --- in-memory backend --------------------------------------------------------
def test_put_returns_opaque_id_and_get_round_trips():
    store = InMemoryProblemStore()
    pid = store.put("x = 7")
    assert isinstance(pid, str) and pid
    assert "x = 7" not in pid  # the id must not encode the answer
    assert store.get(pid) == "x = 7"


def test_unknown_id_returns_none():
    assert InMemoryProblemStore().get("nope") is None


def test_ids_are_unique_per_put():
    store = InMemoryProblemStore()
    ids = {store.put("a") for _ in range(50)}
    assert len(ids) == 50


def test_oldest_entries_are_evicted_past_capacity():
    store = InMemoryProblemStore(max_size=3)
    first = store.put("1")
    store.put("2")
    store.put("3")
    store.put("4")  # evicts the oldest
    assert store.get(first) is None
    assert len(store._items) == 3


# --- Redis backend (injected fake client) -------------------------------------
def test_redis_store_round_trips_and_sets_ttl():
    fake = FakeRedis()
    store = RedisProblemStore(fake, ttl_seconds=1234)
    pid = store.put("x = 42")
    assert store.get(pid) == "x = 42"
    assert "x = 42" not in pid
    # Stored under a namespaced key with the configured TTL.
    assert fake.ttls[f"nudgemath:problem:{pid}"] == 1234


def test_redis_store_decodes_bytes_values():
    fake = FakeRedis()
    store = RedisProblemStore(fake)
    pid = store.put("x = 5")
    fake.store[f"nudgemath:problem:{pid}"] = b"x = 5"  # simulate decode_responses=False
    assert store.get(pid) == "x = 5"


def test_redis_store_unknown_id_returns_none():
    assert RedisProblemStore(FakeRedis()).get("missing") is None


# --- backend selection --------------------------------------------------------
def test_build_uses_in_memory_without_redis_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert isinstance(build_problem_store(), InMemoryProblemStore)


def test_build_uses_redis_when_url_set(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    store = build_problem_store()  # from_url does not connect until a command
    assert isinstance(store, RedisProblemStore)


def test_both_backends_satisfy_protocol():
    assert isinstance(InMemoryProblemStore(), ProblemStore)
    assert isinstance(RedisProblemStore(FakeRedis()), ProblemStore)
