from hint_engine.evaluation import (
    check_does_not_reveal_answer,
    check_no_banned_phrases,
    check_non_empty,
    check_within_max_length,
    run_deterministic_checks,
)
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


def test_individual_check_helpers():
    assert check_does_not_reveal_answer(ALGEBRA_CASE, GOOD_ALGEBRA_HINT).passed
    assert not check_does_not_reveal_answer(ALGEBRA_CASE, BAD_LEAKING_ALGEBRA_HINT).passed
    assert not check_non_empty(ALGEBRA_CASE, EMPTY_HINT).passed
    assert not check_within_max_length(ALGEBRA_CASE, OVER_LENGTH_HINT).passed
    assert not check_no_banned_phrases(ALGEBRA_CASE, BANNED_PHRASE_HINT).passed
