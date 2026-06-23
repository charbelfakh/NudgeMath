import pytest

from hint_engine.config import (
    PINNED_COMPARISON_JUDGE,
    get_comparison_judge_config,
    get_generation_config,
    get_judge_config,
)
from hint_engine.evaluation import run_deterministic_checks
from hint_engine.judge import JudgeResult
from hint_engine.model_comparison import build_comparison_table, format_comparison_table
from hint_engine.models import Hint

from tests.fixtures_hints import ALGEBRA_CASE, GOOD_ALGEBRA_HINT

JUDGE_ENV_KEYS = (
    "LLM_JUDGE_NAME",
    "LLM_JUDGE_PROVIDER",
    "LLM_JUDGE_BASE_URL",
    "LLM_JUDGE_MODEL",
    "LLM_JUDGE_API_KEY_ENV",
)


@pytest.fixture(autouse=True)
def clear_judge_env(monkeypatch):
    for key in JUDGE_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_comparison_judge_default_is_pinned_sonnet():
    cfg = get_comparison_judge_config()
    assert cfg.name == PINNED_COMPARISON_JUDGE.name
    assert cfg.model == PINNED_COMPARISON_JUDGE.model
    assert cfg.provider == "anthropic"


def test_judge_env_override_resolves_ollama_endpoint(monkeypatch):
    monkeypatch.setenv("LLM_JUDGE_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_JUDGE_MODEL", "llama3.2")

    cfg = get_comparison_judge_config()
    assert cfg.provider == "ollama"
    assert cfg.model == "llama3.2"
    assert cfg.name == "llama3.2"
    assert cfg.base_url == "http://localhost:11434/v1"
    assert cfg.api_key_env is None


def test_judge_header_and_self_judge_use_same_resolved_config():
    judge_config = get_comparison_judge_config()

    hint = Hint(
        hint_text=GOOD_ALGEBRA_HINT.hint_text,
        reveals_answer=False,
        meta={"name": "llama3.2", "model": "llama3.2", "provider": "ollama"},
    )
    report = run_deterministic_checks(ALGEBRA_CASE, hint)
    report.judge = JudgeResult(
        passed=True,
        score=0.75,
        rubric=[],
        meta={
            "name": "sonnet-4.6",
            "model": "llama3.2",
            "provider": "ollama",
        },
    )

    table = build_comparison_table([report], judge_config=judge_config)
    text = format_comparison_table(table, with_judge=True)

    assert f"Judge held constant: {judge_config.name}" in text
    assert table.cells[("algebra_sign_error", "llama3.2")].self_judged is False


def test_judge_env_override_changes_header_and_self_judge(monkeypatch):
    monkeypatch.setenv("LLM_JUDGE_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_JUDGE_MODEL", "llama3.2")

    judge_config = get_comparison_judge_config()
    assert judge_config.name == "llama3.2"

    hint = Hint(
        hint_text=GOOD_ALGEBRA_HINT.hint_text,
        reveals_answer=False,
        meta={"name": "llama3.2", "model": "llama3.2", "provider": "ollama"},
    )
    report = run_deterministic_checks(ALGEBRA_CASE, hint)
    report.judge = JudgeResult(
        passed=False,
        score=0.0,
        rubric=[],
        meta={"name": "sonnet-4.6", "model": "llama3.2", "provider": "ollama"},
    )

    table = build_comparison_table([report], judge_config=judge_config)
    text = format_comparison_table(table, with_judge=True)

    assert "Judge held constant: llama3.2" in text
    assert "Judge held constant: sonnet-4.6" not in text
    assert table.cells[("algebra_sign_error", "llama3.2")].self_judged is True


def test_get_judge_config_without_override_defaults_to_generation():
    cfg = get_judge_config()
    gen = get_generation_config()
    assert cfg.model == gen.model
    assert cfg.provider == gen.provider
