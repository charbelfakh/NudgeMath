"""Grade-based practice-problem generation (hybrid: templates + LLM).

Two sources, one shape (``GeneratedProblem``):

* **template** — deterministic parametric generators (one per grade band). Seeded and
  reproducible, and the answer is *computed*, so it is exact and ``verified=True``.
* **llm** — the model authors a grade-appropriate problem + answer. Wider variety,
  but non-reproducible and ``verified=False`` (the answer is the model's claim).

The generated ``correct_answer`` is for teacher-side gating and eval only. It is never
passed into ``generate_hint()`` — the answer-blind boundary is preserved by
construction (nothing here calls the hint generator).
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable

from hint_engine.config import ModelConfig, client_from_config, get_generation_config
from hint_engine.curriculum import band_for_grade, default_template_topic, find_topic
from hint_engine.llm_client import LLMClient
from hint_engine.llm_utils import (
    meta_from_config,
    missing_api_key_error,
    parse_json_object,
)
from hint_engine.models import GeneratedProblem

# Difficulty -> operand ceiling for the template generators.
_DIFFICULTY_RANGE = {"easy": 10, "medium": 30, "hard": 100}


def _range_for(difficulty: str) -> int:
    return _DIFFICULTY_RANGE.get(difficulty, _DIFFICULTY_RANGE["medium"])


def _gen_arithmetic(rng: random.Random, difficulty: str) -> tuple[str, str]:
    """Elementary: whole-number add/subtract/multiply with an exact answer."""
    hi = _range_for(difficulty)
    op = rng.choice(["+", "-", "×"])
    if op == "×":
        a, b = rng.randint(2, max(3, hi // 5)), rng.randint(2, max(3, hi // 5))
        answer = a * b
    elif op == "-":
        a, b = rng.randint(1, hi), rng.randint(1, hi)
        a, b = max(a, b), min(a, b)  # keep it non-negative for early grades
        answer = a - b
    else:
        a, b = rng.randint(1, hi), rng.randint(1, hi)
        answer = a + b
    return f"What is {a} {op} {b}?", str(answer)


def _gen_linear_equations(rng: random.Random, difficulty: str) -> tuple[str, str]:
    """Middle: ax + b = c with an integer solution."""
    hi = _range_for(difficulty)
    a = rng.randint(2, max(3, hi // 5))
    x = rng.randint(-hi // 3 or -1, hi // 3 or 1)
    b = rng.randint(-hi, hi)
    c = a * x + b
    sign = "+" if b >= 0 else "-"
    return f"Solve for x: {a}x {sign} {abs(b)} = {c}", f"x = {x}"


def _gen_quadratics(rng: random.Random, difficulty: str) -> tuple[str, str]:
    """High: x^2 + bx + c = 0 with integer roots, by factoring."""
    hi = max(4, _range_for(difficulty) // 6)
    r1 = rng.randint(-hi, hi)
    r2 = rng.randint(-hi, hi)
    b = -(r1 + r2)
    c = r1 * r2
    b_term = "" if b == 0 else (f" + {b}x" if b > 0 else f" - {abs(b)}x")
    c_term = "" if c == 0 else (f" + {c}" if c > 0 else f" - {abs(c)}")
    roots = sorted({r1, r2})
    answer = " or ".join(f"x = {r}" for r in roots)
    return f"Solve for x: x^2{b_term}{c_term} = 0", answer


# Integer Pythagorean triples (a^2 + b^2 = c^2), legs first.
_PYTHAGOREAN_TRIPLES = [
    (3, 4, 5),
    (6, 8, 10),
    (5, 12, 13),
    (8, 15, 17),
    (9, 12, 15),
    (7, 24, 25),
]


def _gen_geometry(rng: random.Random, difficulty: str) -> tuple[str, str]:
    """Geometry with exact integer answers: rectangles, right triangles, angles."""
    hi = _range_for(difficulty)
    side_hi = max(4, hi // 3)
    kind = rng.choice(
        [
            "rect_area",
            "rect_perimeter",
            "pythagorean",
            "triangle_area",
            "angle_triangle",
            "angle_line",
        ]
    )
    if kind == "rect_area":
        a, b = rng.randint(2, side_hi), rng.randint(2, side_hi)
        return f"A rectangle has sides {a} and {b}. What is its area?", str(a * b)
    if kind == "rect_perimeter":
        a, b = rng.randint(2, side_hi), rng.randint(2, side_hi)
        return (
            f"A rectangle has sides {a} and {b}. What is its perimeter?",
            str(2 * (a + b)),
        )
    if kind == "pythagorean":
        a, b, c = rng.choice(_PYTHAGOREAN_TRIPLES)
        if rng.random() < 0.5:
            return (
                f"A right triangle has legs {a} and {b}. "
                "What is the length of the hypotenuse?",
                str(c),
            )
        return (
            f"A right triangle has one leg {a} and a hypotenuse of {c}. "
            "What is the length of the other leg?",
            str(b),
        )
    if kind == "triangle_area":
        base = rng.randint(2, side_hi)
        height = rng.randint(2, side_hi)
        if (base * height) % 2 == 1:
            height += 1  # keep the area a whole number
        return (
            f"A triangle has a base of {base} and a height of {height}. "
            "What is its area?",
            str(base * height // 2),
        )
    if kind == "angle_triangle":
        a = rng.randint(30, 80)
        b = rng.randint(20, 80)
        while a + b >= 160:
            b = rng.randint(20, 80)
        return (
            f"Two angles of a triangle measure {a}° and {b}°. "
            "What is the measure of the third angle?",
            str(180 - a - b),
        )
    # angle_line
    a = rng.randint(20, 160)
    return (
        f"Two angles lie on a straight line and one measures {a}°. "
        "What is the measure of the other angle?",
        str(180 - a),
    )


_TEMPLATE_GENERATORS: dict[str, Callable[[random.Random, str], tuple[str, str]]] = {
    "arithmetic": _gen_arithmetic,
    "linear_equations": _gen_linear_equations,
    "quadratics": _gen_quadratics,
    "geometry": _gen_geometry,
}


_LLM_SYSTEM_PROMPT = """You are a math teacher writing one practice problem.

Write a single, self-contained problem appropriate for the given grade band, topic, and \
difficulty. Then give its correct final answer.

Respond with strict JSON only — no markdown, no code fences:
{"problem": "<the problem>", "correct_answer": "<the final answer>"}
"""


def _generate_via_llm(
    grade_level: str,
    topic: str,
    difficulty: str,
    *,
    client: LLMClient | None,
    config: ModelConfig | None,
) -> GeneratedProblem:
    config = config or get_generation_config()
    key_error = missing_api_key_error(config)
    if key_error:
        return GeneratedProblem(
            problem="",
            correct_answer="",
            grade_level=grade_level,
            topic=topic,
            difficulty=difficulty,
            source="llm",
            verified=False,
            meta=meta_from_config(config, error=key_error),
        )
    llm = client or client_from_config(config)
    user = f"Grade band: {grade_level}\nTopic: {topic}\nDifficulty: {difficulty}"

    start = time.perf_counter()
    try:
        raw = llm.complete(_LLM_SYSTEM_PROMPT, user)
    except RuntimeError as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return GeneratedProblem(
            problem="",
            correct_answer="",
            grade_level=grade_level,
            topic=topic,
            difficulty=difficulty,
            source="llm",
            verified=False,
            meta=meta_from_config(config, latency_ms=latency_ms, error=str(exc)),
        )
    latency_ms = int((time.perf_counter() - start) * 1000)

    data, error = parse_json_object(raw, required_key="problem")
    problem = ""
    answer = ""
    if data is not None:
        problem = str(data.get("problem", "")).strip()
        answer = str(data.get("correct_answer", "")).strip()

    return GeneratedProblem(
        problem=problem,
        correct_answer=answer,
        grade_level=grade_level,
        topic=topic,
        difficulty=difficulty,
        source="llm",
        verified=False,
        meta=meta_from_config(
            config,
            latency_ms=latency_ms,
            error=error,
            **({"raw_response": raw[:500]} if error else {}),
        ),
    )


def generate_problem(
    grade_level: str,
    *,
    topic: str | None = None,
    difficulty: str = "medium",
    mode: str = "template",
    seed: int | None = None,
    client: LLMClient | None = None,
    config: ModelConfig | None = None,
) -> GeneratedProblem:
    """Generate a practice problem for a grade level.

    ``mode``:
      * ``"template"`` — deterministic generator (raises if the topic has none).
      * ``"llm"`` — model-authored problem.
      * ``"auto"`` — template when the resolved topic supports it, else llm.

    ``grade_level`` may be a numeric grade ("3", "7", "11") or a band name
    ("elementary"/"middle"/"high"). ``seed`` makes template output reproducible.
    """
    band = band_for_grade(grade_level)
    entry = find_topic(band, topic) if topic else default_template_topic(band)
    if entry is None:
        raise ValueError(f"Unknown topic {topic!r} for grade band {band!r}.")

    resolved_mode = mode
    if mode == "auto":
        resolved_mode = "template" if entry.template else "llm"

    if resolved_mode == "template":
        generator = _TEMPLATE_GENERATORS.get(entry.topic)
        if generator is None:
            raise ValueError(
                f"No template generator for topic {entry.topic!r}; use mode='llm'."
            )
        rng = random.Random(seed)
        problem, answer = generator(rng, difficulty)
        return GeneratedProblem(
            problem=problem,
            correct_answer=answer,
            grade_level=grade_level,
            topic=entry.topic,
            difficulty=difficulty,
            source="template",
            verified=True,
            meta={"grade_band": band},
        )

    if resolved_mode == "llm":
        return _generate_via_llm(
            grade_level, entry.topic, difficulty, client=client, config=config
        )

    raise ValueError(f"Unknown mode {mode!r}. Use 'template', 'llm', or 'auto'.")
