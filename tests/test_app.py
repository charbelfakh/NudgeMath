"""Tests for the FastAPI layer: body-size guard and request-context resolution."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from hint_engine.api.app import _client_key, app, get_context
from hint_engine.api.limits import MAX_REQUEST_BYTES


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_oversized_body_is_rejected_before_buffering(client):
    """Starlette has no default body limit; transcribeProblem reads a base64 image
    straight into memory, so an unbounded POST is a memory-exhaustion vector."""
    response = client.post(
        "/graphql",
        content=b"x" * 32,
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(MAX_REQUEST_BYTES + 1),
        },
    )
    assert response.status_code == 413
    assert "too large" in response.json()["detail"]


def test_malformed_content_length_is_rejected(client):
    response = client.post(
        "/graphql",
        content=b"{}",
        headers={"Content-Type": "application/json", "Content-Length": "not-a-number"},
    )
    assert response.status_code == 400


def test_normal_request_passes_the_body_guard(client):
    """A well-formed query still reaches the schema (the guard is not a blanket deny)."""
    response = client.post("/graphql", json={"query": "{ curriculum { topic } }"})
    assert response.status_code == 200
    assert response.json()["data"]["curriculum"]


class _FakeRequest:
    def __init__(self, headers: dict, host: str | None = "10.0.0.1") -> None:
        self.headers = headers
        self.client = type("C", (), {"host": host})() if host else None


def test_client_key_prefers_forwarded_for():
    request = _FakeRequest({"X-Forwarded-For": "203.0.113.7, 10.0.0.1"})
    assert _client_key(request) == "203.0.113.7"


def test_client_key_falls_back_to_peer_then_anonymous():
    assert _client_key(_FakeRequest({})) == "10.0.0.1"
    assert _client_key(_FakeRequest({}, host=None)) == "anonymous"


@pytest.mark.anyio
async def test_get_context_resolves_admin_and_client_key():
    from hint_engine.auth import create_token

    token = create_token("admin")
    request = _FakeRequest({"Authorization": f"Bearer {token}"})
    context = await get_context(request)
    assert context["admin_username"] == "admin"
    assert context["client_key"] == "10.0.0.1"

    anon = await get_context(_FakeRequest({}))
    assert anon["admin_username"] is None


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_shutdown_closes_the_pooled_http_client():
    with patch("hint_engine.llm_client.close_http_client") as close:
        with TestClient(app):
            pass
    close.assert_called_once()
