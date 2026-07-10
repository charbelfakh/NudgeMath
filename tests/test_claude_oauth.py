"""Tests for the in-app Claude-subscription OAuth flow. httpx is fully mocked."""

from __future__ import annotations

import pytest

from hint_engine import claude_oauth


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = ""

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise claude_oauth.httpx.HTTPStatusError(
                "err", request=None, response=self
            )

    def json(self) -> dict:
        return self._payload


@pytest.fixture(autouse=True)
def _isolated_token_store(tmp_path, monkeypatch):
    """Point the token store at a throwaway path so tests never touch a real
    sign-in, and clear any in-flight login before/after each test."""
    monkeypatch.setenv(
        "NUDGEMATH_CLAUDE_OAUTH_TOKENS_PATH", str(tmp_path / "tokens.json")
    )
    claude_oauth.reset_pending()
    yield
    claude_oauth.reset_pending()


def _seed_signed_in(monkeypatch, *, access="acc", expires_in=3600):
    claude_oauth.start_login()
    monkeypatch.setattr(
        claude_oauth.httpx,
        "post",
        lambda *a, **k: _FakeResponse(
            {"access_token": access, "refresh_token": "ref", "expires_in": expires_in}
        ),
    )
    claude_oauth.finish_login("thecode")


def test_start_login_builds_pkce_url():
    out = claude_oauth.start_login()
    assert out["url"].startswith("https://claude.ai/oauth/authorize?")
    assert "code_challenge=" in out["url"]
    assert "code_challenge_method=S256" in out["url"]


def test_signed_out_by_default():
    assert claude_oauth.is_signed_in() is False
    assert claude_oauth.valid_access_token() is None


def test_finish_login_exchanges_code_and_stores_token(monkeypatch):
    claude_oauth.start_login()
    captured: dict = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse(
            {"access_token": "acc", "refresh_token": "ref", "expires_in": 3600}
        )

    monkeypatch.setattr(claude_oauth.httpx, "post", fake_post)
    out = claude_oauth.finish_login("thecode")

    assert out["signed_in"] is True
    assert captured["url"] == claude_oauth.TOKEN_URL
    assert captured["json"]["grant_type"] == "authorization_code"
    assert captured["json"]["code"] == "thecode"
    assert claude_oauth.is_signed_in() is True
    assert claude_oauth.valid_access_token() == "acc"


def test_finish_login_without_start_errors():
    with pytest.raises(claude_oauth.ClaudeOAuthError):
        claude_oauth.finish_login("code")


def test_finish_login_state_mismatch_errors():
    claude_oauth.start_login()
    with pytest.raises(claude_oauth.ClaudeOAuthError, match="State mismatch"):
        claude_oauth.finish_login("code#not-the-real-state")


def test_valid_access_token_refreshes_when_near_expiry(monkeypatch):
    _seed_signed_in(monkeypatch, access="old", expires_in=-100)  # already expired

    calls = {"n": 0}

    def fake_refresh_post(url, json=None, headers=None, timeout=None):
        calls["n"] += 1
        assert json["grant_type"] == "refresh_token"
        return _FakeResponse(
            {"access_token": "new", "refresh_token": "ref2", "expires_in": 3600}
        )

    monkeypatch.setattr(claude_oauth.httpx, "post", fake_refresh_post)
    assert claude_oauth.valid_access_token() == "new"
    assert calls["n"] == 1


def test_logout_forgets_tokens(monkeypatch):
    _seed_signed_in(monkeypatch)
    assert claude_oauth.is_signed_in() is True
    claude_oauth.logout()
    assert claude_oauth.is_signed_in() is False


def test_refresh_without_rotation_keeps_refresh_token(monkeypatch):
    """A refresh response may omit refresh_token; the stored one must survive or
    every later refresh silently becomes impossible."""
    _seed_signed_in(monkeypatch, access="old", expires_in=-100)

    def refresh_without_rotation(url, json=None, headers=None, timeout=None):
        return _FakeResponse({"access_token": "new", "expires_in": -100})

    monkeypatch.setattr(claude_oauth.httpx, "post", refresh_without_rotation)
    assert claude_oauth.valid_access_token() == "new"
    # Still refreshable: the original refresh token was retained.
    assert claude_oauth._load_tokens()["refresh_token"] == "ref"
    assert claude_oauth.valid_access_token() == "new"  # second refresh still works


def test_finish_login_rejects_expired_pending(monkeypatch):
    claude_oauth.start_login()
    assert claude_oauth._pending is not None
    claude_oauth._pending["started_at"] -= claude_oauth._PENDING_MAX_AGE_S + 1
    with pytest.raises(claude_oauth.ClaudeOAuthError, match="expired"):
        claude_oauth.finish_login("code")
