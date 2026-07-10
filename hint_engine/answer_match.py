"""Compare student answers to known correct answers before hint generation.

This gate decides whether to *skip* the hint ("your answer looks correct"), so
the two failure modes are not symmetric:

* a **false negative** (equivalent answers judged different) costs the student an
  unnecessary hint — mildly annoying;
* a **false positive** (different answers judged equivalent) tells a wrong
  student they are right — the bug that actually hurts.

So equivalence is only claimed where it is exact. Values are compared as
``Fraction`` when they parse as rational numbers (``1/2 == 2/4 == 0.5``), and
otherwise as normalized strings. Nothing is ever approximated: no float
tolerance, no rounding, no unit conversion. Anything the parser doesn't
understand falls back to string comparison, which errs toward "not equivalent".

Supported equivalence classes
-----------------------------
* Whitespace, case, trailing punctuation:  ``x=2``  ≡ ``X = 2.``
* Assignment forms:                        ``x = 7`` ≡ ``= 7`` ≡ ``7``
* Rational values:                         ``1/2`` ≡ ``2/4`` ≡ ``0.5`` ≡ ``.5``
* Integers written as decimals:            ``7`` ≡ ``7.0``
* Unicode minus / en-dash:                 ``−3`` ≡ ``- 3`` ≡ ``-3``
* Solution **sets**, order-insensitive:    ``x = 1, 2, 3`` ≡ ``x = 3, 2, 1``
  (also split on ``;`` and the word ``or``)
* Systems of equations, order-insensitive: ``x=1, y=2`` ≡ ``y = 2, x = 1``

Explicitly **not** supported (compared as strings, so they read as different):
irrational/symbolic forms (``sqrt(2)`` vs ``1.414``), percentages vs fractions
(``50%`` vs ``1/2``), units (``7 cm`` vs ``7``), and algebraic rearrangements
(``x + 1`` vs ``1 + x``). Extending any of these means extending this docstring
and the test matrix together.
"""

from __future__ import annotations

import re
from fractions import Fraction

_VAR_ASSIGNMENT = re.compile(
    r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)$",
    re.DOTALL,
)
_LEADING_EQUALS = re.compile(r"^\s*=\s*(.+)$")

# Two or more of these means a system ("x = 1, y = 2"), not a solution set.
# The value stops at a separator, so "x = 1, 2, 3" yields exactly one match.
_ASSIGNMENT_SCAN = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([^,;]+)")

# Solution-set separators: "1, 2", "1; 2", "1 or 2".
_VALUE_SEPARATORS = re.compile(r"\s*(?:,|;|\bor\b)\s*", re.IGNORECASE)

# Characters that look like a minus sign but are not U+002D.
_MINUS_LOOKALIKES = str.maketrans({"−": "-", "–": "-", "—": "-"})


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


def _canonical_scalar(token: str) -> Fraction | str:
    """Exact rational when the token is one, else a normalized string.

    ``Fraction`` handles ``"1/2"``, ``"0.5"``, ``".5"``, ``"7.0"`` and ``"-3"``
    exactly — no float rounding — so ``2/4`` and ``0.5`` collapse to the same
    value. Anything else (``"sqrt(2)"``, ``"7cm"``, ``"no solution"``) stays a
    string and only matches another identical string.
    """
    cleaned = token.strip().rstrip(".,;").translate(_MINUS_LOOKALIKES)
    cleaned = re.sub(r"\s+", "", cleaned)
    if not cleaned:
        return ""
    try:
        return Fraction(cleaned)
    except (ValueError, ZeroDivisionError, OverflowError):
        return cleaned.lower()


def _canonical_value_set(text: str) -> frozenset[Fraction | str]:
    """A solution set: order- and separator-insensitive, exact per element."""
    parts = [p for p in _VALUE_SEPARATORS.split(text) if p.strip()]
    return frozenset(_canonical_scalar(part) for part in parts)


def _canonical_assignments(text: str) -> dict[str, Fraction | str] | None:
    """``{var: value}`` for a system of two or more distinct variables, else None.

    Returns None for a single assignment (``x = 1, 2``, a solution set) and for a
    variable assigned twice with different values (a hedged answer).
    """
    matches = _ASSIGNMENT_SCAN.findall(text)
    if len(matches) < 2:
        return None
    assignments: dict[str, Fraction | str] = {}
    for name, value in matches:
        key = name.lower()
        canonical = _canonical_scalar(value)
        if key in assignments and assignments[key] != canonical:
            return None  # same variable, two values — hedging, not a system
        assignments[key] = canonical
    return assignments


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
    """Return True when the student's answer is exactly equivalent to the correct one.

    See the module docstring for the supported equivalence classes. Never
    approximates: anything unrecognized compares as a string and reads as
    different, so a wrong student is never told they are right.
    """
    if not student_answer.strip() or not correct_answer.strip():
        return False

    # Systems ("x=1, y=2") are compared as variable→value maps, order-insensitive.
    # Checked before the hedging guard, which would otherwise reject every system
    # (it sees two distinct values after the "=" splits).
    student_system = _canonical_assignments(student_answer)
    correct_system = _canonical_assignments(correct_answer)
    if student_system is not None or correct_system is not None:
        return student_system is not None and student_system == correct_system

    # A student hedging across several values ("=2 =3") is not a solution set.
    if has_multiple_conflicting_values(student_answer):
        return False

    student_values = _canonical_value_set(extract_primary_value(student_answer))
    correct_values = _canonical_value_set(extract_primary_value(correct_answer))
    if student_values and student_values == correct_values:
        return True

    # Last resort for forms the parser doesn't model ("no solution", prose).
    return _normalize_whitespace(student_answer) == _normalize_whitespace(correct_answer)
