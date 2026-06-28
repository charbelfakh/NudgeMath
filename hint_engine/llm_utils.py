"""Shared utilities for LLM client modules (generate, judge)."""

from __future__ import annotations

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
