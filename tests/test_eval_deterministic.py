from hint_engine.evaluation import (
    check_does_not_reveal_answer,
    check_no_banned_phrases,
    check_non_empty,
    check_within_max_length,
    run_deterministic_checks,
)
from hint_engine.models import EvalCase, Hint
from tests.fixtures_hints import (
    ALGEBRA_CASE,
    BAD_LEAKING_ALGEBRA_HINT,
    BANNED_PHRASE_HINT,
    EMPTY_HINT,
    GOOD_ALGEBRA_HINT,
    OVER_LENGTH_HINT,
    UNPREFIXED_NUMERIC_LEAK,
)


def test_good_hint_passes_all_checks():
    report = run_deterministic_checks(ALGEBRA_CASE, GOOD_ALGEBRA_HINT)
    assert report.passed is True
    assert all(check.passed for check in report.checks)
    assert len(report.checks) == 5


def test_leaking_hint_fails_does_not_reveal_answer():
    report = run_deterministic_checks(ALGEBRA_CASE, BAD_LEAKING_ALGEBRA_HINT)
    assert report.passed is False
    by_name = {check.name: check for check in report.checks}
    assert by_name["does_not_reveal_answer"].passed is False


def test_empty_hint_fails_non_empty():
    report = run_deterministic_checks(ALGEBRA_CASE, EMPTY_HINT)
    assert report.passed is False
    by_name = {check.name: check for check in report.checks}
    assert by_name["non_empty"].passed is False


def test_over_length_hint_fails_within_max_length():
    report = run_deterministic_checks(ALGEBRA_CASE, OVER_LENGTH_HINT)
    assert report.passed is False
    by_name = {check.name: check for check in report.checks}
    assert by_name["within_max_length"].passed is False


def test_banned_phrase_hint_fails_no_banned_phrases():
    report = run_deterministic_checks(ALGEBRA_CASE, BANNED_PHRASE_HINT)
    assert report.passed is False
    by_name = {check.name: check for check in report.checks}
    assert by_name["no_banned_phrases"].passed is False


def test_unprefixed_numeric_leak_fails_does_not_reveal_answer():
    report = run_deterministic_checks(ALGEBRA_CASE, UNPREFIXED_NUMERIC_LEAK)
    assert report.passed is False
    by_name = {check.name: check for check in report.checks}
    assert by_name["does_not_reveal_answer"].passed is False


def test_superscript_answer_caught_when_hint_uses_caret_form():
    """A superscript answer (2⁵) must be caught even when the hint types it as 2^5."""
    case = EvalCase(
        problem="Simplify: 2³ × 2²",
        student_answer="2⁶",
        correct_answer="2⁵",
        case_id="exponent_multiply_rule",
    )
    leaky = Hint(
        hint_text="Add the exponents — this simplifies to 2^5.",
        reveals_answer=False,
    )
    assert not check_does_not_reveal_answer(case, leaky).passed

    safe = Hint(
        hint_text="When multiplying powers with the same base, add the exponents.",
        reveals_answer=False,
    )
    assert check_does_not_reveal_answer(case, safe).passed


def test_positional_number_is_not_flagged_as_leak():
    """"step 7" must not trip the gate when the answer is 7 (documented false positive)."""
    positional = Hint(
        hint_text="Re-check your arithmetic in step 7 of your working.",
        reveals_answer=False,
    )
    result = check_does_not_reveal_answer(ALGEBRA_CASE, positional)
    assert result.passed is True


def test_answer_number_inside_larger_number_is_not_flagged():
    """Word boundaries: answer 7 must not match inside "17"."""
    case = EvalCase(
        problem="What is 25% of 60?",
        student_answer="1500",
        correct_answer="15",
        case_id="percentage_confusion",
    )
    hint = Hint(
        hint_text="Percent means per hundred, so 150 is far too large here.",
        reveals_answer=False,
    )
    assert check_does_not_reveal_answer(case, hint).passed is True


def test_real_numeric_leak_still_caught_outside_positional_phrase():
    leak = Hint(hint_text="Once you fix the sign you land on 7.", reveals_answer=False)
    assert check_does_not_reveal_answer(ALGEBRA_CASE, leak).passed is False


def test_skip_checks_expectation_drops_named_gate():
    """A case can opt out of a specific gate via expectations['skip_checks']."""
    lenient_case = EvalCase(
        problem=ALGEBRA_CASE.problem,
        student_answer=ALGEBRA_CASE.student_answer,
        correct_answer=ALGEBRA_CASE.correct_answer,
        expectations={"skip_checks": ["within_max_length"]},
        case_id="algebra_no_length_gate",
    )
    report = run_deterministic_checks(lenient_case, OVER_LENGTH_HINT)
    names = {check.name for check in report.checks}
    assert "within_max_length" not in names
    assert len(report.checks) == 4
    # The over-length hint would normally fail; with the gate skipped it passes.
    assert report.deterministic_passed is True


def test_individual_check_helpers():
    assert check_does_not_reveal_answer(ALGEBRA_CASE, GOOD_ALGEBRA_HINT).passed
    assert not check_does_not_reveal_answer(ALGEBRA_CASE, BAD_LEAKING_ALGEBRA_HINT).passed
    assert not check_non_empty(ALGEBRA_CASE, EMPTY_HINT).passed
    assert not check_within_max_length(ALGEBRA_CASE, OVER_LENGTH_HINT).passed
    assert not check_no_banned_phrases(ALGEBRA_CASE, BANNED_PHRASE_HINT).passed
