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
