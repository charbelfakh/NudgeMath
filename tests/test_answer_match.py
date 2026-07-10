import pytest

from hint_engine.answer_match import (
    answers_equivalent,
    extract_primary_value,
    has_multiple_conflicting_values,
    resolve_correct_answer,
)
from hint_engine.eval_cases import EVAL_CASES


@pytest.mark.parametrize(
    ("student", "correct", "expected"),
    [
        ("2", "2", True),
        ("=2", "2", True),
        ("= 2", "2", True),
        ("x = 2", "2", True),
        ("x=2", "2", True),
        ("variable = 2", "2", True),
        ("x = 7", "x = 7", True),
        ("7", "x = 7", True),
        ("=7", "x = 7", True),
        ("X = 7", "x = 7", True),
        ("x = 2", "x = 7", False),
        ("=2 =3", "2", False),
        ("=2 = 3", "2", False),
        ("x = 2, y = 3", "2", False),
        ("20", "14", False),
    ],
)
def test_answers_equivalent(student: str, correct: str, expected: bool):
    assert answers_equivalent(student, correct) is expected


@pytest.mark.parametrize(
    ("student", "correct", "label"),
    [
        ("1/2", "2/4", "equivalent fractions"),
        ("0.5", "1/2", "decimal vs fraction"),
        (".5", "1/2", "bare-dot decimal"),
        ("x = 0.5", "x = 1/2", "decimal vs fraction, assigned"),
        ("7", "7.0", "integer vs decimal"),
        ("-3", "- 3", "space after sign"),
        ("−3", "-3", "unicode minus"),
        ("–3", "-3", "en-dash minus"),
        ("x = 1, 2, 3", "x = 3, 2, 1", "solution set, reordered"),
        ("1 or 2", "2, 1", "'or' separator"),
        ("1; 2", "2, 1", "semicolon separator"),
        ("x=1, y=2", "y = 2, x = 1", "system, reordered"),
        ("X = 7.", "x = 7", "case + trailing period"),
    ],
)
def test_equivalences_that_must_be_recognized(student, correct, label):
    """Judging these different costs the student a hint they don't need."""
    assert answers_equivalent(student, correct) is True, label


@pytest.mark.parametrize(
    ("student", "correct", "label"),
    [
        ("0.33", "1/3", "approximate decimal is not exact"),
        ("1.414", "sqrt(2)", "irrational, not modelled"),
        ("50%", "1/2", "percent, not modelled"),
        ("7 cm", "7", "units, not modelled"),
        ("x + 1", "1 + x", "algebraic rearrangement, not modelled"),
        ("x = 2", "x = 7", "plainly wrong"),
        ("=2 =3", "2", "hedged across two values"),
        ("x = 2, y = 3", "2", "system vs scalar"),
        ("x = 1, 2", "x = 1", "student gave a superset"),
        ("x = 1", "x = 1, 2", "student gave a subset"),
        ("x=1, y=2", "x=1, y=3", "system, one value wrong"),
        ("x=1, y=2", "x=2, y=1", "system, values swapped between vars"),
        ("", "2", "empty student answer"),
        ("2", "", "empty correct answer"),
    ],
)
def test_non_equivalences_never_claim_correct(student, correct, label):
    """The dangerous direction: telling a wrong student they are right."""
    assert answers_equivalent(student, correct) is False, label


def test_zero_denominator_does_not_crash():
    assert answers_equivalent("1/0", "1/2") is False


def test_extract_primary_value_forms():
    assert extract_primary_value("2") == "2"
    assert extract_primary_value("=2") == "2"
    assert extract_primary_value("x = 7") == "7"


def test_has_multiple_conflicting_values():
    assert has_multiple_conflicting_values("=2 =3") is True
    assert has_multiple_conflicting_values("x = 2") is False
    assert has_multiple_conflicting_values("7") is False


def test_resolve_correct_answer_prefers_teacher_value():
    resolved = resolve_correct_answer(
        "Unknown problem",
        EVAL_CASES,
        teacher_correct_answer="42",
    )
    assert resolved == "42"


def test_resolve_correct_answer_falls_back_to_seed_case():
    resolved = resolve_correct_answer(
        "Solve for x: 2x - 5 = 9",
        EVAL_CASES,
    )
    assert resolved == "x = 7"
