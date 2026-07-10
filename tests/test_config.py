import pytest

from hint_engine.config import (
    ANTHROPIC_SONNET,
    OLLAMA_DEFAULT,
    PINNED_COMPARISON_JUDGE,
    clear_model_override,
    client_from_config,
    get_comparison_judge_config,
    get_generation_config,
    get_judge_config,
    get_vision_config,
    list_model_presets,
    set_model_override,
    vision_client_from_config,
)
from hint_engine.evaluation import run_deterministic_checks
from hint_engine.judge import JudgeResult
from hint_engine.model_comparison import build_comparison_table, format_comparison_table
from hint_engine.models import Hint
from tests.fixtures_hints import ALGEBRA_CASE, GOOD_ALGEBRA_HINT


def test_ollama_clients_disable_reasoning():
    # Ollama reasoning models (qwen3, ...) must get reasoning_effort="none" or they
    # return empty content; other providers must not receive the parameter.
    assert vision_client_from_config(OLLAMA_DEFAULT)._reasoning_effort == "none"
    assert client_from_config(OLLAMA_DEFAULT)._reasoning_effort == "none"
    assert vision_client_from_config(ANTHROPIC_SONNET)._reasoning_effort is None
    assert client_from_config(ANTHROPIC_SONNET)._reasoning_effort is None


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


@pytest.fixture(autouse=True)
def clear_model_overrides():
    # Overrides are process-wide global state; never leak them between tests.
    yield
    clear_model_override("vision")
    clear_model_override("generation")


def test_vision_override_wins_over_default():
    assert get_vision_config().model == "llama3.2-vision"  # baseline
    set_model_override("vision", "qwen3.5:9b")
    assert get_vision_config().model == "qwen3.5:9b"
    assert get_vision_config().provider == "ollama"


def test_generation_override_wins_over_env(monkeypatch):
    monkeypatch.setenv("LLM_GEN_MODEL", "from-env")
    assert get_generation_config().model == "from-env"
    set_model_override("generation", "sonnet-4.6")
    assert get_generation_config().model == "claude-sonnet-4-6"
    assert get_generation_config().provider == "anthropic"


def test_clear_override_restores_env_and_default(monkeypatch):
    set_model_override("vision", "llava:7b")
    assert get_vision_config().model == "llava:7b"
    clear_model_override("vision")
    assert get_vision_config().model == "llama3.2-vision"


def test_set_model_override_rejects_unknown():
    with pytest.raises(ValueError):
        set_model_override("vision", "no-such-model")
    with pytest.raises(ValueError):
        set_model_override("bogus-kind", "qwen3.5:9b")


def test_vision_presets_are_multimodal_capable_names():
    names = {cfg.name for cfg in list_model_presets("vision")}
    assert {"qwen3.5:9b", "llava:7b", "moondream"} <= names


SUBSCRIPTION_PRESET_NAMES = ("claude-sonnet-5", "claude-opus-4-8", "claude-haiku-4-5")


def test_claude_subscription_tiers_are_presets_for_every_kind():
    from hint_engine.config import CLAUDE_SUBSCRIPTION

    for kind in ("generation", "vision", "solver"):
        names = [cfg.name for cfg in list_model_presets(kind)]
        for sub in SUBSCRIPTION_PRESET_NAMES:
            assert sub in names, (kind, sub)
    assert CLAUDE_SUBSCRIPTION.provider == "claude_subscription"
    assert CLAUDE_SUBSCRIPTION.model == "claude-sonnet-5"  # canonical default
    assert CLAUDE_SUBSCRIPTION.api_key_env is None  # auth is the OAuth bearer token


def test_client_from_config_builds_subscription_clients():
    from hint_engine.config import CLAUDE_SUBSCRIPTION
    from hint_engine.llm_client import ClaudeSubscriptionClient
    from hint_engine.vision_client import ClaudeSubscriptionVisionClient

    assert isinstance(client_from_config(CLAUDE_SUBSCRIPTION), ClaudeSubscriptionClient)
    assert isinstance(
        vision_client_from_config(CLAUDE_SUBSCRIPTION), ClaudeSubscriptionVisionClient
    )


def test_available_presets_hide_uncredentialed_models(monkeypatch):
    from hint_engine import claude_oauth, config

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(claude_oauth, "is_signed_in", lambda: False)

    for kind in ("generation", "vision", "solver"):
        available = [c.name for c in config.list_available_model_presets(kind)]
        for sub in SUBSCRIPTION_PRESET_NAMES:
            assert sub not in available, (kind, sub)  # not signed in
        assert "sonnet-4.6" not in available, kind  # no API key
    assert "llama3.2" in [
        c.name for c in config.list_available_model_presets("generation")
    ]  # ollama is the offline default, always available


def test_available_presets_include_models_once_credentialed(monkeypatch):
    from hint_engine import claude_oauth, config

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(claude_oauth, "is_signed_in", lambda: True)

    for kind in ("generation", "vision", "solver"):
        available = [c.name for c in config.list_available_model_presets(kind)]
        for sub in SUBSCRIPTION_PRESET_NAMES:
            assert sub in available, (kind, sub)
        assert "sonnet-4.6" in available, kind


SOLVER_ENV_KEYS = (
    "LLM_SOLVER_NAME",
    "LLM_SOLVER_PROVIDER",
    "LLM_SOLVER_BASE_URL",
    "LLM_SOLVER_MODEL",
    "LLM_SOLVER_API_KEY_ENV",
)


@pytest.fixture(autouse=True)
def clear_solver_env(monkeypatch):
    for key in SOLVER_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def clear_claude_effort(monkeypatch):
    from hint_engine.config import set_claude_effort

    monkeypatch.delenv("CLAUDE_SUBSCRIPTION_EFFORT", raising=False)
    set_claude_effort(None)
    yield
    set_claude_effort(None)


def test_claude_effort_set_get_clear_and_validate():
    from hint_engine.config import get_claude_effort, set_claude_effort

    assert get_claude_effort() is None  # API default
    set_claude_effort("xhigh")
    assert get_claude_effort() == "xhigh"
    set_claude_effort(None)
    assert get_claude_effort() is None
    with pytest.raises(ValueError):
        set_claude_effort("turbo")


def test_claude_effort_env_fallback(monkeypatch):
    from hint_engine.config import get_claude_effort, set_claude_effort

    monkeypatch.setenv("CLAUDE_SUBSCRIPTION_EFFORT", "medium")
    assert get_claude_effort() == "medium"
    set_claude_effort("max")  # override beats env
    assert get_claude_effort() == "max"
    monkeypatch.setenv("CLAUDE_SUBSCRIPTION_EFFORT", "bogus")
    set_claude_effort(None)
    assert get_claude_effort() is None  # invalid env value is ignored


def test_subscription_client_effort_omitted_for_haiku():
    """Haiku rejects output_config.effort — the factory must never pass it."""
    from hint_engine.config import (
        CLAUDE_SUBSCRIPTION_PRESETS,
        set_claude_effort,
    )

    set_claude_effort("max")
    by_name = {c.name: c for c in CLAUDE_SUBSCRIPTION_PRESETS}
    assert client_from_config(by_name["claude-opus-4-8"])._effort == "max"
    assert client_from_config(by_name["claude-haiku-4-5"])._effort is None
    assert vision_client_from_config(by_name["claude-haiku-4-5"])._effort is None


def test_solver_defaults_to_provider_default():
    from hint_engine.config import get_solver_config

    solver = get_solver_config()
    assert solver.model == OLLAMA_DEFAULT.model
    assert solver.provider == "ollama"


def test_solver_selection_is_independent_of_generation():
    """Switching the generation model must not move the solver (and vice versa)."""
    from hint_engine.config import get_solver_config

    try:
        set_model_override("generation", "llama3.2:3b")
        assert get_solver_config().model == OLLAMA_DEFAULT.model  # unmoved

        set_model_override("solver", "sonnet-4.6")
        assert get_solver_config().model == ANTHROPIC_SONNET.model
        assert get_generation_config().model == "llama3.2:3b"  # unmoved
    finally:
        clear_model_override("generation")
        clear_model_override("solver")


def test_solver_env_override_wins(monkeypatch):
    from hint_engine.config import get_solver_config

    monkeypatch.setenv("LLM_SOLVER_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_SOLVER_MODEL", "qwen3.5:9b")
    solver = get_solver_config()
    assert solver.model == "qwen3.5:9b"
    assert solver.provider == "ollama"


def test_solver_admin_override_wins_over_env(monkeypatch):
    from hint_engine.config import get_solver_config

    monkeypatch.setenv("LLM_SOLVER_MODEL", "qwen3.5:9b")
    set_model_override("solver", "llama3.2:3b")
    try:
        assert get_solver_config().model == "llama3.2:3b"
    finally:
        clear_model_override("solver")
    assert get_solver_config().model == "qwen3.5:9b"
