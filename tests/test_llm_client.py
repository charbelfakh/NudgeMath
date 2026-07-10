import json

import pytest

from hint_engine.generate import generate_hint
from hint_engine.judge import judge_hint
from hint_engine.llm_client import ClaudeSubscriptionClient, OpenAICompatibleClient
from hint_engine.models import HintRequest
from tests.fixtures_hints import ALGEBRA_CASE, GOOD_ALGEBRA_HINT
from tests.llm_mocks import TEST_GEN_CONFIG, TEST_JUDGE_CONFIG, MockLLMClient


def test_openai_compatible_client_complete(monkeypatch):
    class FakeMessage:
        content = '{"hint_text": "ok", "reveals_answer": false}'

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(
        "hint_engine.llm_client.OpenAI",
        lambda **kwargs: FakeClient(),
    )
    client = OpenAICompatibleClient(
        base_url="http://localhost:11434/v1",
        model="llama3.2",
    )
    text = client.complete("system", "user")
    assert "hint_text" in text


def test_generate_hint_uses_mock_client():
    client = MockLLMClient(
        json.dumps({"hint_text": "Check the sign.", "reveals_answer": False})
    )
    hint = generate_hint(
        HintRequest(problem="2x-5=9", student_answer="x=2"),
        client=client,
        config=TEST_GEN_CONFIG,
    )
    assert hint.hint_text == "Check the sign."
    assert hint.meta["provider"] == "mock"
    assert hint.meta["model"] == "test-model"
    assert len(client.calls) == 1


def test_judge_hint_uses_mock_client():
    rubric = {
        "rubric": [
            {"name": "addresses_specific_error", "passed": True, "detail": "ok"},
            {"name": "no_semantic_answer_leak", "passed": True, "detail": "ok"},
            {"name": "appropriate_for_level", "passed": True, "detail": "ok"},
            {"name": "guides_without_solving", "passed": True, "detail": "ok"},
        ]
    }
    client = MockLLMClient(json.dumps(rubric))
    result = judge_hint(ALGEBRA_CASE, GOOD_ALGEBRA_HINT, client=client, config=TEST_JUDGE_CONFIG)
    assert result.passed is True
    assert result.meta["provider"] == "mock"


class _FakeMessagesResponse:
    status_code = 200
    text = ""

    def json(self):
        return {"content": [{"type": "text", "text": "Check the sign."}]}


def test_claude_subscription_client_uses_bearer_and_identity_block(monkeypatch):
    from hint_engine import claude_oauth

    monkeypatch.setattr(claude_oauth, "valid_access_token", lambda: "tok-xyz")

    captured: dict = {}

    def fake_post(url, headers=None, json=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeMessagesResponse()

    client = ClaudeSubscriptionClient(model="claude-sonnet-5")
    monkeypatch.setattr(client._client, "post", fake_post)

    text = client.complete("SYSTEM RULES", "the user prompt")

    assert text == "Check the sign."
    assert captured["url"].endswith("/v1/messages")
    assert captured["headers"]["Authorization"] == "Bearer tok-xyz"
    assert captured["headers"]["anthropic-beta"] == claude_oauth.OAUTH_BETA_HEADER
    system_blocks = captured["json"]["system"]
    # The Claude Code identity must be the FIRST system block (API requirement),
    # with the caller's real system prompt following it.
    assert system_blocks[0]["text"].startswith("You are Claude Code")
    assert system_blocks[1]["text"] == "SYSTEM RULES"
    assert captured["json"]["messages"] == [{"role": "user", "content": "the user prompt"}]
    # Claude 5 models think adaptively by default and can spend the whole token
    # budget on thinking blocks (empty text reply) — must be disabled by default.
    assert captured["json"]["thinking"] == {"type": "disabled"}


def test_claude_subscription_client_can_opt_into_thinking(monkeypatch):
    from hint_engine import claude_oauth

    monkeypatch.setattr(claude_oauth, "valid_access_token", lambda: "tok")

    captured: dict = {}

    def fake_post(url, headers=None, json=None):
        captured["json"] = json
        return _FakeMessagesResponse()

    client = ClaudeSubscriptionClient(model="claude-sonnet-5", thinking=True)
    monkeypatch.setattr(client._client, "post", fake_post)
    client.complete("s", "u")
    # Explicit adaptive: omitting `thinking` would mean OFF on Opus models,
    # silently defeating the solver's opt-in after a model switch.
    assert captured["json"]["thinking"] == {"type": "adaptive"}


def test_claude_subscription_client_sends_effort_when_set(monkeypatch):
    from hint_engine import claude_oauth

    monkeypatch.setattr(claude_oauth, "valid_access_token", lambda: "tok")

    captured: dict = {}

    def fake_post(url, headers=None, json=None):
        captured["json"] = json
        return _FakeMessagesResponse()

    client = ClaudeSubscriptionClient(model="claude-opus-4-8", effort="xhigh")
    monkeypatch.setattr(client._client, "post", fake_post)
    client.complete("s", "u")
    assert captured["json"]["output_config"] == {"effort": "xhigh"}

    # Unset effort = the API default; the key must be absent entirely.
    default_client = ClaudeSubscriptionClient(model="claude-opus-4-8")
    monkeypatch.setattr(default_client._client, "post", fake_post)
    default_client.complete("s", "u")
    assert "output_config" not in captured["json"]


def test_claude_subscription_client_requires_sign_in(monkeypatch):
    from hint_engine import claude_oauth

    monkeypatch.setattr(claude_oauth, "valid_access_token", lambda: None)
    client = ClaudeSubscriptionClient(model="claude-sonnet-5")
    with pytest.raises(RuntimeError, match="Not signed in"):
        client.complete("s", "u")


def test_openai_client_raises_on_truncated_response(monkeypatch):
    """finish_reason="length" means the reply was cut off; parsing it yields a
    confusing JSON error (or a silently incomplete hint) instead of the cause."""

    class FakeMessage:
        content = '{"hint_text": "You are on the right tra'

    class FakeChoice:
        message = FakeMessage()
        finish_reason = "length"

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr("hint_engine.llm_client.OpenAI", lambda **kwargs: FakeClient())
    client = OpenAICompatibleClient(
        base_url="http://localhost:11434/v1", model="llama3.2", max_tokens=512
    )
    with pytest.raises(RuntimeError, match="truncated at max_tokens=512"):
        client.complete("s", "u")


def test_claude_subscription_client_raises_on_truncated_response(monkeypatch):
    """A high effort level can spend the whole budget on thinking blocks."""
    from hint_engine import claude_oauth

    monkeypatch.setattr(claude_oauth, "valid_access_token", lambda: "tok")

    class _Truncated:
        status_code = 200
        text = ""

        def json(self):
            return {"stop_reason": "max_tokens", "content": [{"type": "thinking"}]}

    client = ClaudeSubscriptionClient(model="claude-opus-4-8", max_tokens=512)
    monkeypatch.setattr(client._client, "post", lambda *a, **k: _Truncated())
    with pytest.raises(RuntimeError, match="truncated at max_tokens=512"):
        client.complete("s", "u")


def test_truncation_surfaces_into_hint_meta_error():
    """End to end: the caller turns it into an actionable meta.error, not a hint."""
    from hint_engine.generate import generate_hint
    from hint_engine.llm_client import truncation_error
    from hint_engine.models import HintRequest

    class TruncatingClient:
        def complete(self, system: str, user: str) -> str:
            raise truncation_error(512)

    hint = generate_hint(
        HintRequest(problem="2x = 4", student_answer="x = 1"),
        client=TruncatingClient(),
        config=TEST_GEN_CONFIG,
    )
    assert hint.hint_text == ""
    assert "truncated at max_tokens=512" in hint.meta["error"]
    assert "lower the Claude effort level" in hint.meta["error"]


def test_claude_subscription_client_wraps_transport_errors(monkeypatch):
    """httpx transport failures must surface as RuntimeError — the contract every
    caller (generate/judge/solve/transcribe) catches into meta["error"]. An httpx
    type escaping would 500 the GraphQL request instead."""
    import httpx

    from hint_engine import claude_oauth

    monkeypatch.setattr(claude_oauth, "valid_access_token", lambda: "tok")
    client = ClaudeSubscriptionClient(model="claude-sonnet-5")

    def fail_post(url, headers=None, json=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(client._client, "post", fail_post)
    with pytest.raises(RuntimeError, match="request failed"):
        client.complete("s", "u")


def test_claude_subscription_vision_client_sends_image_source_block(monkeypatch):
    from hint_engine import claude_oauth
    from hint_engine.vision_client import ClaudeSubscriptionVisionClient

    monkeypatch.setattr(claude_oauth, "valid_access_token", lambda: "tok-xyz")

    captured: dict = {}

    def fake_post(url, headers=None, json=None):
        captured["headers"] = headers
        captured["json"] = json
        return _FakeMessagesResponse()

    client = ClaudeSubscriptionVisionClient(model="claude-sonnet-5")
    monkeypatch.setattr(client._client, "post", fake_post)

    text = client.complete_with_image(
        "TRANSCRIBE RULES", "read the problem", "data:image/jpeg;base64,QUJD"
    )

    assert text == "Check the sign."
    assert captured["headers"]["Authorization"] == "Bearer tok-xyz"
    # Same identity-first system contract as the text client.
    assert captured["json"]["system"][0]["text"].startswith("You are Claude Code")
    content = captured["json"]["messages"][0]["content"]
    image_block = content[0]
    assert image_block["type"] == "image"
    assert image_block["source"] == {
        "type": "base64",
        "media_type": "image/jpeg",
        "data": "QUJD",
    }
    assert content[1] == {"type": "text", "text": "read the problem"}


def test_claude_subscription_vision_client_rejects_non_data_url(monkeypatch):
    from hint_engine import claude_oauth
    from hint_engine.vision_client import ClaudeSubscriptionVisionClient

    monkeypatch.setattr(claude_oauth, "valid_access_token", lambda: "tok")
    client = ClaudeSubscriptionVisionClient(model="claude-sonnet-5")
    with pytest.raises(RuntimeError, match="data: URL"):
        client.complete_with_image("s", "u", "https://example.com/pic.png")
