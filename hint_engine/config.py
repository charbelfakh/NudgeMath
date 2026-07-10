"""Model/provider configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from hint_engine.llm_client import LLMClient, OpenAICompatibleClient
from hint_engine.runtime_settings import SETTINGS
from hint_engine.vision_client import OpenAICompatibleVisionClient, VisionClient


@dataclass(frozen=True)
class ModelConfig:
    """Resolved LLM endpoint + model identity."""

    name: str
    provider: str
    base_url: str
    model: str
    api_key_env: str | None = None


# Offline-by-default: Ollama at localhost, no API key required.
OLLAMA_DEFAULT = ModelConfig(
    name="llama3.2",
    provider="ollama",
    base_url="http://localhost:11434/v1",
    model="llama3.2",
    api_key_env=None,
)

ANTHROPIC_SONNET = ModelConfig(
    name="sonnet-4.6",
    provider="anthropic",
    base_url="https://api.anthropic.com/v1/",
    model="claude-sonnet-4-6",
    api_key_env="ANTHROPIC_API_KEY",
)

# Claude via the user's subscription (no API key): authenticated by the in-app
# OAuth token (see hint_engine/claude_oauth.py) and routed through
# ClaudeSubscriptionClient. base_url has no /v1 suffix — the client appends
# /v1/messages. api_key_env is None because auth is the Bearer token.
# Three selectable tiers; all are multimodal, so each appears in every kind's
# dropdown. CLAUDE_SUBSCRIPTION_MODEL (env) still pins the model for ALL
# subscription presets when set — leave it unset to choose via the dropdowns.
_ANTHROPIC_NATIVE_URL = "https://api.anthropic.com"

CLAUDE_SUBSCRIPTION_PRESETS: list[ModelConfig] = [
    ModelConfig("claude-sonnet-5", "claude_subscription", _ANTHROPIC_NATIVE_URL, "claude-sonnet-5"),
    ModelConfig("claude-opus-4-8", "claude_subscription", _ANTHROPIC_NATIVE_URL, "claude-opus-4-8"),
    ModelConfig("claude-haiku-4-5", "claude_subscription", _ANTHROPIC_NATIVE_URL, "claude-haiku-4-5"),
]

# Canonical default (status display, docs): the Sonnet tier.
CLAUDE_SUBSCRIPTION = CLAUDE_SUBSCRIPTION_PRESETS[0]

# Vision default is distinct: the text default (llama3.2) is not multimodal, so
# image transcription needs its own vision-capable model.
OLLAMA_VISION_DEFAULT = ModelConfig(
    name="llama3.2-vision",
    provider="ollama",
    base_url="http://localhost:11434/v1",
    model="llama3.2-vision",
    api_key_env=None,
)

# Neutral external judge for cross-model comparison (held constant unless LLM_JUDGE_* set).
PINNED_COMPARISON_JUDGE = ANTHROPIC_SONNET


def claude_subscription_model(default: str | None = None) -> str:
    """Resolved Claude-subscription model id: ``CLAUDE_SUBSCRIPTION_MODEL`` env,
    else ``default`` (the preset's own model), else the canonical preset's."""
    return (
        os.environ.get("CLAUDE_SUBSCRIPTION_MODEL")
        or default
        or CLAUDE_SUBSCRIPTION.model
    )


# --- Claude effort level -------------------------------------------------------
# One global setting for the subscription: how hard Claude thinks/works per
# request, sent as the Messages API's output_config.effort. Resolution mirrors
# the model overrides: admin override › CLAUDE_SUBSCRIPTION_EFFORT env › unset
# (the API default, "high"). Never sent for Haiku — the API rejects it there.

CLAUDE_EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


def get_claude_effort() -> str | None:
    """Current effort level (override › env › None, meaning the API default)."""
    override = SETTINGS.get_claude_effort()
    if override is not None:
        return override
    env = os.environ.get("CLAUDE_SUBSCRIPTION_EFFORT", "").strip().lower()
    return env if env in CLAUDE_EFFORT_LEVELS else None


def set_claude_effort(effort: str | None) -> None:
    """Set (or clear, with None/empty) the process-wide Claude effort level."""
    if not effort:
        SETTINGS.set_claude_effort(None)
        return
    if effort not in CLAUDE_EFFORT_LEVELS:
        raise ValueError(
            f"Unknown effort {effort!r}. Known: {', '.join(CLAUDE_EFFORT_LEVELS)}"
        )
    SETTINGS.set_claude_effort(effort)


def _model_supports_effort(model: str) -> bool:
    """Haiku-tier models reject output_config.effort; Sonnet 5 / Opus support it."""
    return not model.startswith("claude-haiku")


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is not None and value.strip():
        return value.strip()
    return default


def _provider_default_config(provider: str | None) -> ModelConfig | None:
    if provider == "ollama":
        return OLLAMA_DEFAULT
    if provider == "anthropic":
        return ANTHROPIC_SONNET
    return None


def _resolve_judge_fallback() -> ModelConfig:
    """Baseline for partial LLM_JUDGE_* overrides — provider-aware, not hardcoded Sonnet."""
    if not _judge_env_overrides_set():
        return get_generation_config()
    provider = _env("LLM_JUDGE_PROVIDER")
    return _provider_default_config(provider) or get_generation_config()


def _config_from_prefix(prefix: str, fallback: ModelConfig) -> ModelConfig:
    """Resolve ModelConfig from LLM_{PREFIX}_* env vars."""
    model_env = _env(f"{prefix}_MODEL")
    name_env = _env(f"{prefix}_NAME")
    provider = _env(f"{prefix}_PROVIDER", fallback.provider) or fallback.provider
    base_url = _env(f"{prefix}_BASE_URL", fallback.base_url) or fallback.base_url
    model = model_env or fallback.model
    name = name_env or (model if model_env else fallback.name)
    api_key_env_raw = _env(f"{prefix}_API_KEY_ENV")
    api_key_env = api_key_env_raw if api_key_env_raw else fallback.api_key_env
    if provider == "ollama":
        api_key_env = None
        if not _env(f"{prefix}_BASE_URL"):
            base_url = OLLAMA_DEFAULT.base_url
    return ModelConfig(
        name=name,
        provider=provider,
        base_url=base_url,
        model=model,
        api_key_env=api_key_env,
    )


def get_generation_config() -> ModelConfig:
    """Generation model config. Env: LLM_GEN_NAME, LLM_GEN_PROVIDER, LLM_GEN_BASE_URL, LLM_GEN_MODEL, LLM_GEN_API_KEY_ENV.

    An admin runtime override (see :func:`set_model_override`) wins over env + default.
    """
    override = SETTINGS.get_model_override("generation")
    if override is not None:
        return override
    default = _resolve_default_config()
    return _config_from_prefix("LLM_GEN", default)


def _resolve_vision_default_config() -> ModelConfig:
    """Vision baseline — provider-aware, never the text-only generation default."""
    provider = _env("LLM_DEFAULT_PROVIDER", "ollama") or "ollama"
    if provider == "anthropic":
        return ANTHROPIC_SONNET  # Sonnet is multimodal.
    return OLLAMA_VISION_DEFAULT


def get_vision_config() -> ModelConfig:
    """Vision model config. Env: LLM_VISION_* (defaults to a vision-capable model).

    An admin runtime override (see :func:`set_model_override`) wins over env + default.
    """
    override = SETTINGS.get_model_override("vision")
    if override is not None:
        return override
    return _config_from_prefix("LLM_VISION", _resolve_vision_default_config())


def get_solver_config() -> ModelConfig:
    """Solver model config (admin-only solution generation). Env: LLM_SOLVER_*.

    Resolution: admin runtime override › ``LLM_SOLVER_*`` env › the provider
    default — fully independent of the generation selection, so switching the
    generation model never moves the solver (and vice versa).
    """
    override = SETTINGS.get_model_override("solver")
    if override is not None:
        return override
    return _config_from_prefix("LLM_SOLVER", _resolve_default_config())


def _judge_env_overrides_set() -> bool:
    return any(
        os.environ.get(key)
        for key in (
            "LLM_JUDGE_NAME",
            "LLM_JUDGE_PROVIDER",
            "LLM_JUDGE_BASE_URL",
            "LLM_JUDGE_MODEL",
            "LLM_JUDGE_API_KEY_ENV",
        )
    )


def get_judge_config() -> ModelConfig:
    """Judge model config. Env: LLM_JUDGE_* (defaults to generation config when unset)."""
    return _config_from_prefix("LLM_JUDGE", _resolve_judge_fallback())


def get_comparison_judge_config() -> ModelConfig:
    """Pinned neutral judge for model_comparison --judge (override via LLM_JUDGE_*)."""
    if _judge_env_overrides_set():
        return get_judge_config()
    return PINNED_COMPARISON_JUDGE


def _resolve_default_config() -> ModelConfig:
    provider = _env("LLM_DEFAULT_PROVIDER", "ollama") or "ollama"
    if provider == "anthropic":
        return ANTHROPIC_SONNET
    return OLLAMA_DEFAULT


# Ollama reasoning models (qwen3, …) return empty content unless thinking is
# disabled; "none" makes them answer directly. Other providers reject the value,
# so it is only sent for Ollama.
def _reasoning_effort_for(config: ModelConfig) -> str | None:
    return "none" if config.provider == "ollama" else None


def client_from_config(
    config: ModelConfig, *, max_tokens: int = 512, thinking: bool = False
) -> LLMClient:
    if config.provider == "claude_subscription":
        # Subscription auth (Bearer token) needs the native Messages API, not the
        # OpenAI-compatible chat path. Env overrides win over the preset defaults.
        from hint_engine.llm_client import ClaudeSubscriptionClient

        model = claude_subscription_model(config.model)
        return ClaudeSubscriptionClient(
            model=model,
            base_url=os.environ.get("ANTHROPIC_BASE_URL") or config.base_url,
            max_tokens=max_tokens,
            thinking=thinking,
            effort=get_claude_effort() if _model_supports_effort(model) else None,
        )
    api_key = None
    if config.api_key_env:
        api_key = os.environ.get(config.api_key_env)
    return OpenAICompatibleClient(
        base_url=config.base_url,
        model=config.model,
        api_key=api_key,
        max_tokens=max_tokens,
        reasoning_effort=_reasoning_effort_for(config),
    )


def vision_client_from_config(config: ModelConfig, *, max_tokens: int = 512) -> VisionClient:
    if config.provider == "claude_subscription":
        from hint_engine.vision_client import ClaudeSubscriptionVisionClient

        model = claude_subscription_model(config.model)
        return ClaudeSubscriptionVisionClient(
            model=model,
            base_url=os.environ.get("ANTHROPIC_BASE_URL") or config.base_url,
            max_tokens=max_tokens,
            effort=get_claude_effort() if _model_supports_effort(model) else None,
        )
    api_key = None
    if config.api_key_env:
        api_key = os.environ.get(config.api_key_env)
    return OpenAICompatibleVisionClient(
        base_url=config.base_url,
        model=config.model,
        api_key=api_key,
        max_tokens=max_tokens,
        reasoning_effort=_reasoning_effort_for(config),
    )


COMPARISON_PRESETS: list[ModelConfig] = [
    OLLAMA_DEFAULT,
    ModelConfig(
        name="llama3.2:3b",
        provider="ollama",
        base_url="http://localhost:11434/v1",
        model="llama3.2:3b",
    ),
    ANTHROPIC_SONNET,
    ModelConfig(
        name="haiku-4.5",
        provider="anthropic",
        base_url="https://api.anthropic.com/v1/",
        model="claude-haiku-4-5-20251001",
        api_key_env="ANTHROPIC_API_KEY",
    ),
]


def parse_model_list(raw: str | None) -> list[ModelConfig]:
    """Parse comma-separated model names into configs from COMPARISON_PRESETS."""
    if not raw:
        return [get_generation_config()]
    names = [part.strip() for part in raw.split(",") if part.strip()]
    presets = {cfg.name: cfg for cfg in COMPARISON_PRESETS}
    configs: list[ModelConfig] = []
    for name in names:
        if name not in presets:
            raise ValueError(f"Unknown comparison model {name!r}. Known: {sorted(presets)}")
        configs.append(presets[name])
    return configs


# --- admin runtime model switching -------------------------------------------
# Named presets the admin can switch to from the UI (in-memory, process-wide).
# Vision presets must be multimodal; generation presets are the text models.

_OLLAMA_URL = OLLAMA_DEFAULT.base_url

_VISION_PRESETS: list[ModelConfig] = [
    ModelConfig("qwen3.5:9b", "ollama", _OLLAMA_URL, "qwen3.5:9b"),
    ModelConfig("llava:7b", "ollama", _OLLAMA_URL, "llava:7b"),
    ModelConfig("moondream", "ollama", _OLLAMA_URL, "moondream"),
    OLLAMA_VISION_DEFAULT,  # llama3.2-vision
    ANTHROPIC_SONNET,  # Sonnet is multimodal
    *CLAUDE_SUBSCRIPTION_PRESETS,  # all multimodal; shown only while signed in
]

# Generation presets = the comparison models plus the Claude subscription tiers
# (only *shown* in the admin dropdown once signed in — see availability filter).
_GENERATION_PRESETS: list[ModelConfig] = [
    *COMPARISON_PRESETS,
    *CLAUDE_SUBSCRIPTION_PRESETS,
]

MODEL_PRESETS: dict[str, list[ModelConfig]] = {
    "vision": _VISION_PRESETS,
    "generation": _GENERATION_PRESETS,
    # The admin-only solver picks from the same text models as generation.
    "solver": list(_GENERATION_PRESETS),
}

# Admin overrides live in the shared, lock-guarded RuntimeSettings (see
# hint_engine/runtime_settings.py); consulted first in get_*_config().


def list_model_presets(kind: str) -> list[ModelConfig]:
    """Full canonical preset list for ``kind`` ("vision" | "generation").

    Used for lookups and override validation; the admin UI shows only the
    *available* subset (see :func:`list_available_model_presets`).
    """
    if kind not in MODEL_PRESETS:
        raise ValueError(f"Unknown model kind {kind!r}. Known: {sorted(MODEL_PRESETS)}")
    return list(MODEL_PRESETS[kind])


def is_config_available(config: ModelConfig) -> bool:
    """Whether a preset can actually be used right now (credential/sign-in present).

    Ollama is the offline default and always counts as available (no probe). A
    Claude subscription is available once signed in; API-key providers once their
    key env var is set. Unavailable presets are hidden from the admin dropdowns so
    the UI never offers a model that would fail on the next request.
    """
    if config.provider == "ollama":
        return True
    if config.provider == "claude_subscription":
        from hint_engine import claude_oauth

        return claude_oauth.is_signed_in()
    if config.api_key_env:
        return bool(os.environ.get(config.api_key_env))
    return True


def list_available_model_presets(kind: str) -> list[ModelConfig]:
    """Presets for ``kind`` whose credential/connection is currently satisfied."""
    return [cfg for cfg in list_model_presets(kind) if is_config_available(cfg)]


def set_model_override(kind: str, preset_name: str) -> ModelConfig:
    """Point ``kind`` at a named preset for every subsequent request (until restart)."""
    presets = {cfg.name: cfg for cfg in list_model_presets(kind)}
    if preset_name not in presets:
        raise ValueError(
            f"Unknown {kind} preset {preset_name!r}. Known: {sorted(presets)}"
        )
    SETTINGS.set_model_override(kind, presets[preset_name])
    return presets[preset_name]


def clear_model_override(kind: str) -> None:
    """Drop the override for ``kind`` (falls back to env + default)."""
    SETTINGS.clear_model_override(kind)


def clear_overrides_for_provider(provider: str) -> None:
    """Drop every kind's override that points at ``provider``.

    Used when a provider's credential goes away (e.g. subscription disconnect)
    so no model kind keeps routing to a client that can no longer authenticate.
    """
    SETTINGS.clear_overrides_for_provider(provider)


def get_model_override(kind: str) -> ModelConfig | None:
    return SETTINGS.get_model_override(kind)
