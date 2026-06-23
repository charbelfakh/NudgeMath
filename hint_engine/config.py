"""Model/provider configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from hint_engine.llm_client import LLMClient, OpenAICompatibleClient


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

# Neutral external judge for cross-model comparison (held constant unless LLM_JUDGE_* set).
PINNED_COMPARISON_JUDGE = ANTHROPIC_SONNET


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
    """Generation model config. Env: LLM_GEN_NAME, LLM_GEN_PROVIDER, LLM_GEN_BASE_URL, LLM_GEN_MODEL, LLM_GEN_API_KEY_ENV."""
    default = _resolve_default_config()
    return _config_from_prefix("LLM_GEN", default)


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


def client_from_config(config: ModelConfig, *, max_tokens: int = 512) -> LLMClient:
    api_key = None
    if config.api_key_env:
        api_key = os.environ.get(config.api_key_env)
    return OpenAICompatibleClient(
        base_url=config.base_url,
        model=config.model,
        api_key=api_key,
        max_tokens=max_tokens,
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
