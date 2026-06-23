import json
import os
import re
import time
from typing import Any

from hint_engine.config import ModelConfig, client_from_config, get_generation_config
from hint_engine.llm_client import LLMClient
from hint_engine.models import Hint, HintRequest

# Backward-compatible aliases for tests and docs.
DEFAULT_MODEL = "claude-sonnet-4-6"
FAST_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """You are a math tutor generating a single pedagogical hint.

The student submitted a wrong answer. Your job is to nudge them toward the correct \
approach without revealing the final answer.

Guidelines:
- Name the likely error type (e.g. sign error, order-of-operations mistake, \
fraction misconception).
- Point at the next step they should reconsider — do not solve the problem for them.
- Never state the correct final answer, numeric result, or "x = …" value.
- Keep the hint concise (2–4 sentences).

Respond with strict JSON only — no markdown, no code fences:
{"hint_text": "<your hint>", "reveals_answer": <true if you stated the final answer, else false>}
"""

_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _build_user_message(request: HintRequest) -> str:
    parts = [
        f"Problem:\n{request.problem}",
        f"\nStudent's answer:\n{request.student_answer}",
    ]
    if request.grade_level:
        parts.append(f"\nGrade level: {request.grade_level}")
    if request.subject:
        parts.append(f"\nSubject: {request.subject}")
    return "".join(parts)


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE.sub("", text.strip()).strip()


def _parse_model_json(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    cleaned = _strip_code_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error: {exc}"
    if not isinstance(data, dict):
        return None, "Model response is not a JSON object."
    if "hint_text" not in data:
        return None, "Model JSON missing hint_text."
    return data, None


def _meta_from_config(config: ModelConfig, **extra: Any) -> dict[str, Any]:
    return {
        "name": config.name,
        "model": config.model,
        "provider": config.provider,
        **extra,
    }


def generate_hint(
    request: HintRequest,
    *,
    client: LLMClient | None = None,
    config: ModelConfig | None = None,
) -> Hint:
    """Produce a pedagogical hint via the configured LLM client."""
    config = config or get_generation_config()
    if config.api_key_env and not os.environ.get(config.api_key_env):
        return Hint(
            hint_text="",
            reveals_answer=False,
            meta=_meta_from_config(
                config,
                error=f"{config.api_key_env} environment variable is not set.",
            ),
        )

    llm = client or client_from_config(config)
    user_message = _build_user_message(request)

    start = time.perf_counter()
    try:
        raw_text = llm.complete(_SYSTEM_PROMPT, user_message)
    except RuntimeError as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return Hint(
            hint_text="",
            reveals_answer=False,
            meta=_meta_from_config(config, latency_ms=latency_ms, error=str(exc)),
        )

    latency_ms = int((time.perf_counter() - start) * 1000)
    parsed, parse_error = _parse_model_json(raw_text)

    if parse_error or parsed is None:
        return Hint(
            hint_text=raw_text.strip() or "Unable to parse model response.",
            reveals_answer=False,
            meta=_meta_from_config(
                config,
                latency_ms=latency_ms,
                error=parse_error,
                raw_response=raw_text[:500],
            ),
        )

    hint_text = str(parsed.get("hint_text", "")).strip()
    reveals_answer = bool(parsed.get("reveals_answer", False))

    return Hint(
        hint_text=hint_text,
        reveals_answer=reveals_answer,
        meta=_meta_from_config(config, latency_ms=latency_ms),
    )
