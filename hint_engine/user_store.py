"""Persistent store of admin accounts (username -> scrypt password hash).

Kept separate from ``problem_store``: accounts must survive restarts, so the
default backend is a **file-backed JSON store** (atomic write), gitignored. Same
Protocol pattern as the LLM providers / problem store — swap the backend without
touching callers.

Only the hash is stored, never the password. Records are created out-of-band via
``python -m hint_engine.manage_users`` so credentials never live in code or git.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


def normalize_username(username: str) -> str:
    """Usernames are case-insensitive and whitespace-trimmed (`Admin` == `admin`)."""
    return username.strip().lower()


@dataclass(frozen=True)
class UserRecord:
    username: str
    password_hash: str
    role: str = "admin"
    created_at: str = ""


@runtime_checkable
class UserStore(Protocol):
    def get(self, username: str) -> UserRecord | None:
        """Return the record for a username, or None if unknown."""

    def put(self, record: UserRecord) -> None:
        """Create or overwrite an account."""

    def delete(self, username: str) -> bool:
        """Remove an account; True if it existed."""

    def list_usernames(self) -> list[str]:
        """Sorted list of known usernames."""


class InMemoryUserStore:
    """Process-local account map (used in tests and offline demos)."""

    def __init__(self, records: list[UserRecord] | None = None) -> None:
        self._items: dict[str, UserRecord] = {r.username: r for r in records or []}

    def get(self, username: str) -> UserRecord | None:
        return self._items.get(username)

    def put(self, record: UserRecord) -> None:
        self._items[record.username] = record

    def delete(self, username: str) -> bool:
        return self._items.pop(username, None) is not None

    def list_usernames(self) -> list[str]:
        return sorted(self._items)


class FileUserStore:
    """JSON-file account store with atomic writes (survives restarts)."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self._path = Path(path)

    def _load(self) -> dict[str, UserRecord]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        items: dict[str, UserRecord] = {}
        for entry in raw.get("users", []):
            try:
                rec = UserRecord(
                    username=entry["username"],
                    password_hash=entry["password_hash"],
                    role=entry.get("role", "admin"),
                    created_at=entry.get("created_at", ""),
                )
            except (KeyError, TypeError):
                continue
            items[rec.username] = rec
        return items

    def _save(self, items: dict[str, UserRecord]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"users": [asdict(rec) for rec in items.values()]}
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            os.replace(tmp, self._path)  # atomic on POSIX and Windows
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def get(self, username: str) -> UserRecord | None:
        return self._load().get(username)

    def put(self, record: UserRecord) -> None:
        items = self._load()
        items[record.username] = record
        self._save(items)

    def delete(self, username: str) -> bool:
        items = self._load()
        if username not in items:
            return False
        del items[username]
        self._save(items)
        return True

    def list_usernames(self) -> list[str]:
        return sorted(self._load())


def default_users_path() -> Path:
    """Where the account file lives: ``NUDGEMATH_USERS_PATH`` or ``<repo>/.nudgemath/users.json``."""
    env = os.environ.get("NUDGEMATH_USERS_PATH")
    if env and env.strip():
        return Path(env.strip())
    return Path(__file__).resolve().parent.parent / ".nudgemath" / "users.json"


def build_user_store() -> UserStore:
    """File-backed store at :func:`default_users_path` (resolved per call)."""
    return FileUserStore(default_users_path())


USER_STORE: UserStore = build_user_store()
