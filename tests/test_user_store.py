from hint_engine.user_store import (
    FileUserStore,
    InMemoryUserStore,
    UserRecord,
    default_users_path,
    normalize_username,
)


def _record(username: str = "admin") -> UserRecord:
    return UserRecord(username=username, password_hash="scrypt$fake", role="admin")


def test_in_memory_crud():
    store = InMemoryUserStore()
    assert store.get("admin") is None
    store.put(_record("admin"))
    assert store.get("admin").password_hash == "scrypt$fake"
    assert store.list_usernames() == ["admin"]
    assert store.delete("admin") is True
    assert store.delete("admin") is False
    assert store.get("admin") is None


def test_file_store_persists_across_instances(tmp_path):
    path = tmp_path / "users.json"
    FileUserStore(path).put(_record("teacher"))
    # A fresh instance reads what the previous one wrote.
    reopened = FileUserStore(path)
    rec = reopened.get("teacher")
    assert rec is not None
    assert rec.username == "teacher"
    assert rec.role == "admin"


def test_file_store_overwrites_and_lists(tmp_path):
    path = tmp_path / "users.json"
    store = FileUserStore(path)
    store.put(_record("a"))
    store.put(_record("b"))
    store.put(UserRecord(username="a", password_hash="scrypt$new"))
    assert store.list_usernames() == ["a", "b"]
    assert store.get("a").password_hash == "scrypt$new"
    assert store.delete("a") is True
    assert store.list_usernames() == ["b"]


def test_file_store_missing_file_is_empty(tmp_path):
    store = FileUserStore(tmp_path / "nope.json")
    assert store.list_usernames() == []
    assert store.get("anyone") is None


def test_normalize_username_is_case_and_space_insensitive():
    assert normalize_username("  Admin ") == "admin"
    assert normalize_username("ADMIN") == "admin"
    assert normalize_username("admin") == "admin"


def test_default_users_path_honors_env(monkeypatch, tmp_path):
    target = tmp_path / "custom" / "users.json"
    monkeypatch.setenv("NUDGEMATH_USERS_PATH", str(target))
    assert default_users_path() == target
