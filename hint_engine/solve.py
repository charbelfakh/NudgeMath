"""Admin-only problem solver — a separate, answer-producing path.

Deliberately the opposite of ``generate.py``: this module *does* solve. It backs
the admin-gated ``solveProblem`` mutation so a teacher can verify a
model-authored practice problem or get an answer for a typed/photo problem that
has no stored answer. It runs on its own **solver** model config
(``get_solver_config`` — override › ``LLM_SOLVER_*`` env › generation config)
and never touches ``generate_hint()`` or any student-facing type.
"""

from __future__ import annotations

import time

from hint_engine.config import ModelConfig, client_from_config, get_solver_config
from hint_engine.llm_client import LLMClient
from hint_engine.llm_utils import (
    meta_from_config,
    missing_api_key_error,
    parse_json_object,
)
from hint_engine.models import Solution

_SYSTEM_PROMPT = """You are a math teacher writing a model solution for another teacher.

Solve the given problem completely and show your work.

Guidelines:
- Work step by step, numbering the steps, so the reasoning is easy to check.
- Keep each step short; use plain notation (e.g. 3x + 2 = 11) or simple LaTeX.
- End with the final answer on its own, in its simplest exact form.
- If the problem is ambiguous or unsolvable, say why in solution_text and leave \
final_answer empty.

Respond with strict JSON only — no markdown, no code fences:
{"solution_text": "<numbered worked solution>", "final_answer": "<the final answer only>"}
"""


def _build_user_message(problem: str, grade_level: str | None) -> str:
    parts = [f"Problem:\n{problem}"]
    if grade_level:
        parts.append(f"\nGrade level: {grade_level}")
    return "".join(parts)


def solve_problem(
    problem: str,
    grade_level: str | None = None,
    *,
    client: LLMClient | None = None,
    config: ModelConfig | None = None,
) -> Solution:
    """Produce a worked solution via the configured solver LLM client."""
    config = config or get_solver_config()
    key_error = missing_api_key_error(config)
    if key_error:
        return Solution(
            solution_text="",
            meta=meta_from_config(config, error=key_error),
        )

    # Solving benefits from model reasoning (thinking=True), unlike the hint and
    # judge paths where it starves the visible reply. The larger budget leaves
    # room for thinking blocks plus the full worked solution.
    llm = client or client_from_config(config, max_tokens=4096, thinking=True)
    user_message = _build_user_message(problem, grade_level)

    start = time.perf_counter()
    try:
        raw_text = llm.complete(_SYSTEM_PROMPT, user_message)
    except RuntimeError as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return Solution(
            solution_text="",
            meta=meta_from_config(config, latency_ms=latency_ms, error=str(exc)),
        )

    latency_ms = int((time.perf_counter() - start) * 1000)
    parsed, parse_error = parse_json_object(raw_text, required_key="solution_text")

    if parse_error or parsed is None:
        return Solution(
            solution_text=raw_text.strip() or "Unable to parse model response.",
            meta=meta_from_config(
                config,
                latency_ms=latency_ms,
                error=parse_error,
                raw_response=raw_text[:500],
            ),
        )

    return Solution(
        solution_text=str(parsed.get("solution_text", "")).strip(),
        final_answer=str(parsed.get("final_answer", "")).strip(),
        meta=meta_from_config(config, latency_ms=latency_ms),
    )
