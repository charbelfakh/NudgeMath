import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from hint_engine.config import ModelConfig, client_from_config, get_judge_config
from hint_engine.evaluation import CheckResult
from hint_engine.llm_client import LLMClient
from hint_engine.llm_utils import MUST_PASS_RUBRIC, meta_from_config, strip_code_fences
from hint_engine.models import EvalCase, Hint

_SYSTEM_PROMPT = """You are an expert math-education evaluator scoring a pedagogical hint.

Given the problem, the student's wrong answer, the correct answer, and the hint text, \
score each rubric item below. The hint should nudge the student without revealing the \
final answer.

Rubric items:
1. addresses_specific_error — Does the hint target the student's actual mistake (not generic advice)?
2. no_semantic_answer_leak — Does the hint avoid revealing the answer, including paraphrases \
(e.g. "you'll end up with seven" when the answer is 7)?
3. appropriate_for_level — Is the tone and vocabulary suitable for the problem's level?
4. guides_without_solving — Does the hint point at the next step without working through to the final result?

Respond with strict JSON only — no markdown, no code fences:
{
  "rubric": [
    {"name": "<rubric item name>", "passed": <true|false>, "detail": "<one-line reason>"}
  ]
}

Include all four rubric items exactly once, using these names: addresses_specific_error, \
no_semantic_answer_leak, appropriate_for_level, guides_without_solving.
"""


@dataclass
class JudgeResult:
    passed: bool
    score: float
    rubric: list[CheckResult]
    meta: dict = field(default_factory=dict)


def _build_user_message(case: EvalCase, hint: Hint) -> str:
    parts = [
        f"Problem:\n{case.problem}",
        f"\nStudent's answer:\n{case.student_answer}",
        f"\nCorrect answer:\n{case.correct_answer}",
        f"\nHint text:\n{hint.hint_text}",
    ]
    if case.expectations.get("grade_level"):
        parts.append(f"\nGrade level: {case.expectations['grade_level']}")
    return "".join(parts)


def _parse_judge_json(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    cleaned = strip_code_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error: {exc}"
    if not isinstance(data, dict):
        return None, "Judge response is not a JSON object."
    if "rubric" not in data:
        return None, "Judge JSON missing rubric."
    if not isinstance(data["rubric"], list):
        return None, "Judge rubric is not a list."
    return data, None


def _rubric_from_parsed(data: dict[str, Any]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for item in data["rubric"]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "unknown"))
        passed = bool(item.get("passed", False))
        detail = str(item.get("detail", ""))
        results.append(CheckResult(name=name, passed=passed, detail=detail))
    return results


def _compute_judge_verdict(rubric: list[CheckResult]) -> tuple[bool, float, str | None]:
    if not rubric:
        return False, 0.0, None
    score = sum(1 for item in rubric if item.passed) / len(rubric)
    rubric_names = {item.name for item in rubric}
    missing = MUST_PASS_RUBRIC - rubric_names
    if missing:
        return False, score, f"Must-pass rubric items missing from judge response: {sorted(missing)}"
    must_pass_items = [item for item in rubric if item.name in MUST_PASS_RUBRIC]
    passed = all(item.passed for item in must_pass_items)
    return passed, score, None


def judge_hint(
    case: EvalCase,
    hint: Hint,
    *,
    client: LLMClient | None = None,
    config: ModelConfig | None = None,
) -> JudgeResult:
    """Score a hint against qualitative rubric items via the configured LLM client."""
    config = config or get_judge_config()
    if config.api_key_env and not os.environ.get(config.api_key_env):
        return JudgeResult(
            passed=False,
            score=0.0,
            rubric=[],
            meta=meta_from_config(
                config,
                error=f"{config.api_key_env} environment variable is not set.",
            ),
        )

    llm = client or client_from_config(config, max_tokens=1024)
    user_message = _build_user_message(case, hint)

    start = time.perf_counter()
    try:
        raw_text = llm.complete(_SYSTEM_PROMPT, user_message)
    except RuntimeError as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return JudgeResult(
            passed=False,
            score=0.0,
            rubric=[],
            meta=meta_from_config(config, latency_ms=latency_ms, error=str(exc)),
        )

    latency_ms = int((time.perf_counter() - start) * 1000)
    parsed, parse_error = _parse_judge_json(raw_text)

    if parse_error or parsed is None:
        return JudgeResult(
            passed=False,
            score=0.0,
            rubric=[],
            meta=meta_from_config(
                config,
                latency_ms=latency_ms,
                error=parse_error,
                raw_response=raw_text[:500],
            ),
        )

    rubric = _rubric_from_parsed(parsed)
    passed, score, verdict_error = _compute_judge_verdict(rubric)

    extra: dict[str, Any] = {"latency_ms": latency_ms}
    if verdict_error:
        extra["error"] = verdict_error

    return JudgeResult(
        passed=passed,
        score=score,
        rubric=rubric,
        meta=meta_from_config(config, **extra),
    )
