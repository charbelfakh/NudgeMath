"""Request-context accessors: who is calling, and under which bucket.

Two orthogonal questions the resolvers ask of every request:

* **Authorization** — ``IsAdmin`` reads ``admin_username``, set by
  ``app.get_context`` from a verified bearer token.
* **Cost** — ``client_key`` names the rate-limit bucket. This is a spend ceiling,
  not an authorization boundary; see ``hint_engine/rate_limit.py``.
"""

from __future__ import annotations

from typing import Any

import strawberry
from strawberry.permission import BasePermission

LLM_RATE_MESSAGE = (
    "Too many requests — please wait a moment before asking for another hint."
)
LOGIN_RATE_MESSAGE = "Too many sign-in attempts — please wait and try again."


def context_of(info: strawberry.Info) -> dict[str, Any]:
    """Strawberry passes ``None`` when a query runs with no context (in-process
    schema execution), so never dereference ``info.context`` directly."""
    return info.context or {}


class IsAdmin(BasePermission):
    """Gate a field behind a valid admin session token (set by the context getter)."""

    message = "Admin authentication required."

    def has_permission(self, source: Any, info: strawberry.Info, **kwargs: Any) -> bool:
        return bool(context_of(info).get("admin_username"))


def client_key(info: strawberry.Info) -> str:
    """Rate-limit bucket key: the caller's address, or a shared anonymous bucket
    when the transport didn't supply one (tests, in-process schema execution)."""
    return context_of(info).get("client_key") or "anonymous"
