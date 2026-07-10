"""Shared utilities for LLM client modules (generate, judge, solve, problem_gen)."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from hint_engine.config import ModelConfig

_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

# Rubric items that must pass for a judge verdict of passed=True.
MUST_PASS_RUBRIC = frozenset({"addresses_specific_error", "no_semantic_answer_leak"})


def strip_code_fences(text: str) -> str:
    return _CODE_FENCE.sub("", text.strip()).strip()


def meta_from_config(config: ModelConfig, **extra: Any) -> dict[str, Any]:
    return {
        "name": config.name,
        "model": config.model,
        "provider": config.provider,
        **extra,
    }


def missing_api_key_error(config: ModelConfig) -> str | None:
    """The standard meta["error"] message when a config's API key env is unset."""
    if config.api_key_env and not os.environ.get(config.api_key_env):
        return f"{config.api_key_env} environment variable is not set."
    return None


def parse_json_object(raw: str, *, required_key: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse a strict-JSON LLM reply into (object, error).

    Shared by the generation-shaped paths (hint, solve, problem): strips code
    fences, requires a JSON object containing ``required_key``, and returns a
    stable error string otherwise.
    """
    cleaned = strip_code_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error: {exc}"
    if not isinstance(data, dict):
        return None, "Model response is not a JSON object."
    if required_key not in data:
        return None, f"Model JSON missing {required_key}."
    return data, None
