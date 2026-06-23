"""Compare student answers to known correct answers before hint generation."""

from __future__ import annotations

import re

_VAR_ASSIGNMENT = re.compile(
    r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)$",
    re.DOTALL,
)
_LEADING_EQUALS = re.compile(r"^\s*=\s*(.+)$")


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _normalize_value(value: str) -> str:
    return _normalize_whitespace(value.rstrip(".,;"))


def extract_primary_value(text: str) -> str:
    """Pull the answer value from bare, leading-equals, or variable-assignment forms."""
    stripped = text.strip()
    if not stripped:
        return ""

    var_match = _VAR_ASSIGNMENT.match(stripped)
    if var_match:
        return var_match.group(2).strip()

    equals_match = _LEADING_EQUALS.match(stripped)
    if equals_match:
        return equals_match.group(1).strip()

    return stripped


def _values_after_equals(text: str) -> list[str]:
    if "=" not in text:
        return []
    return [
        _normalize_value(part)
        for part in text.split("=")[1:]
        if part.strip()
    ]


def has_multiple_conflicting_values(student_answer: str) -> bool:
    """True when the student gave more than one distinct value (e.g. '=2 =3')."""
    values = _values_after_equals(student_answer)
    if len(values) < 2:
        return False
    return len(set(values)) > 1


def lookup_correct_answer(problem: str, cases) -> str | None:
    """Match a free-form problem string to a seed case's known correct answer."""
    normalized = _normalize_whitespace(problem)
    for case in cases:
        if _normalize_whitespace(case.problem) == normalized:
            return case.correct_answer
    return None


def resolve_correct_answer(
    problem: str,
    cases,
    *,
    teacher_correct_answer: str | None = None,
) -> str | None:
    """Teacher-provided answer takes precedence; else match a seed case by problem text."""
    if teacher_correct_answer and teacher_correct_answer.strip():
        return teacher_correct_answer.strip()
    return lookup_correct_answer(problem, cases)


def answers_equivalent(student_answer: str, correct_answer: str) -> bool:
    """Return True when the student's answer matches the known correct answer."""
    if not student_answer.strip() or not correct_answer.strip():
        return False

    if has_multiple_conflicting_values(student_answer):
        return False

    student_value = _normalize_value(extract_primary_value(student_answer))
    correct_value = _normalize_value(extract_primary_value(correct_answer))

    if student_value == correct_value:
        return True

    if _normalize_whitespace(student_answer) == _normalize_whitespace(correct_answer):
        return True

    return False
