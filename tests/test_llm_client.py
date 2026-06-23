import json

from hint_engine.config import ModelConfig
from hint_engine.generate import generate_hint
from hint_engine.judge import judge_hint
from hint_engine.llm_client import OpenAICompatibleClient
from hint_engine.models import HintRequest

from tests.fixtures_hints import ALGEBRA_CASE, GOOD_ALGEBRA_HINT
from tests.llm_mocks import MockLLMClient, TEST_GEN_CONFIG, TEST_JUDGE_CONFIG


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
