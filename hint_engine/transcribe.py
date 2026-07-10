"""Turn an image of a math problem into text for the answer-blind hint pipeline.

The vision model transcribes only — it reads the problem (and any visible student
attempt) off the page and never solves it or supplies a correct answer. The result
feeds an ordinary ``HintRequest``, so the answer-blind boundary in ``generate.py``
is untouched.
"""

from __future__ import annotations

import json
import os
import re
import time

from hint_engine.config import ModelConfig, get_vision_config, vision_client_from_config
from hint_engine.llm_utils import meta_from_config, strip_code_fences
from hint_engine.models import TranscriptionResult
from hint_engine.vision_client import VisionClient

_TRAILING_COMMA = re.compile(r",\s*([}\]])")
_PROBLEM_FIELD = re.compile(r'"problem"\s*:\s*"([^"]*)"', re.IGNORECASE)
_ANSWER_FIELD = re.compile(r'"student_answer"\s*:\s*"([^"]*)"', re.IGNORECASE)

_SYSTEM_PROMPT = """You transcribe a math problem from an image into text.

Read the image and extract:
- the problem statement exactly as written (preserve numbers, symbols, exponents, \
fractions)
- the student's own attempted answer if one is visibly written on the page, else an \
empty string

Do NOT solve the problem. Do NOT provide, compute, or guess the correct answer. Only \
transcribe what is actually on the page.

Respond with strict JSON only — no markdown, no code fences:
{"problem": "<the problem text>", "student_answer": "<student's attempt or empty string>"}
"""

_USER_MESSAGE = "Transcribe the math problem in this image as strict JSON."


def _loads_dict(text: str) -> dict | None:
    """Parse a JSON object, tolerating a trailing comma before a closing brace."""
    for candidate in (text, _TRAILING_COMMA.sub(r"\1", text)):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _parse_transcription(cleaned: str) -> tuple[str, str, str | None]:
    """Extract (problem, student_answer, error) from a vision model's reply.

    Tolerant by design: vision models return sloppy JSON (trailing commas, preamble,
    or the object embedded in prose). Falls back to a regex field-grab, then to
    treating a non-JSON reply as the problem text itself, since the student edits it
    before requesting a hint.
    """
    data = _loads_dict(cleaned)
    if data is None:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            data = _loads_dict(cleaned[start : end + 1])
    if isinstance(data, dict) and "problem" in data:
        return (
            str(data["problem"]).strip(),
            str(data.get("student_answer", "")).strip(),
            None,
        )

    field = _PROBLEM_FIELD.search(cleaned)
    if field:
        answer = _ANSWER_FIELD.search(cleaned)
        return field.group(1).strip(), (answer.group(1).strip() if answer else ""), None

    if "{" not in cleaned:  # plain-text transcription, no JSON attempted
        return cleaned.strip(), "", None

    return "", "", "Could not parse the transcription from the model response."


def transcribe_problem(
    image_data_url: str,
    *,
    client: VisionClient | None = None,
    config: ModelConfig | None = None,
) -> TranscriptionResult:
    """Extract problem text from an image (a base64 ``data:`` URL) via the vision client.

    Answer-blind: returns only the problem and any visible student attempt, never a
    correct answer. On config/LLM/parse failure the error surfaces into ``meta["error"]``
    with an empty ``problem`` rather than raising.
    """
    config = config or get_vision_config()
    if config.api_key_env and not os.environ.get(config.api_key_env):
        return TranscriptionResult(
            problem="",
            meta=meta_from_config(
                config,
                error=f"{config.api_key_env} environment variable is not set.",
            ),
        )

    vision = client or vision_client_from_config(config)

    start = time.perf_counter()
    try:
        raw_text = vision.complete_with_image(_SYSTEM_PROMPT, _USER_MESSAGE, image_data_url)
    except RuntimeError as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return TranscriptionResult(
            problem="",
            meta=meta_from_config(config, latency_ms=latency_ms, error=str(exc)),
        )

    latency_ms = int((time.perf_counter() - start) * 1000)
    cleaned = strip_code_fences(raw_text)
    if not cleaned.strip():
        return TranscriptionResult(
            problem="",
            meta=meta_from_config(
                config,
                latency_ms=latency_ms,
                error=(
                    "The vision model returned an empty response. Try a clearer image "
                    "or a different LLM_VISION_MODEL."
                ),
            ),
        )

    problem, student_answer, parse_error = _parse_transcription(cleaned)
    if parse_error or not problem:
        return TranscriptionResult(
            problem="",
            meta=meta_from_config(
                config,
                latency_ms=latency_ms,
                error=parse_error or "No problem text found in the image.",
                raw_response=cleaned[:500],
            ),
        )

    return TranscriptionResult(
        problem=problem,
        student_answer=student_answer,
        meta=meta_from_config(config, latency_ms=latency_ms),
    )
