import json

from hint_engine.eval_cases import EVAL_CASES
from hint_engine.evaluation import EvalReport, run_deterministic_checks
from hint_engine.judge import JudgeResult, judge_hint
from hint_engine.models import Hint

from tests.fixtures_hints import ALGEBRA_CASE, GOOD_ALGEBRA_HINT
from tests.llm_mocks import MockLLMClient, TEST_JUDGE_CONFIG


def _canned_rubric(
    *,
    addresses_specific_error: bool = True,
    no_semantic_answer_leak: bool = True,
    appropriate_for_level: bool = True,
    guides_without_solving: bool = True,
) -> str:
    items = [
        ("addresses_specific_error", addresses_specific_error, "Targets sign error."),
        ("no_semantic_answer_leak", no_semantic_answer_leak, "No paraphrased leak."),
        ("appropriate_for_level", appropriate_for_level, "Tone fits level."),
        ("guides_without_solving", guides_without_solving, "Nudges without solving."),
    ]
    rubric = [
        {"name": name, "passed": passed, "detail": detail}
        for name, passed, detail in items
    ]
    return json.dumps({"rubric": rubric})


def test_judge_hint_parses_canned_json():
    client = MockLLMClient(_canned_rubric())
    result = judge_hint(ALGEBRA_CASE, GOOD_ALGEBRA_HINT, client=client, config=TEST_JUDGE_CONFIG)

    assert isinstance(result, JudgeResult)
    assert result.passed is True
    assert result.score == 1.0
    assert len(result.rubric) == 4
    assert result.meta["model"] == TEST_JUDGE_CONFIG.model
    assert result.meta["provider"] == "mock"
    assert "latency_ms" in result.meta


def test_judge_semantic_leak_fails_merged_report():
    client = MockLLMClient(_canned_rubric(no_semantic_answer_leak=False))
    result = judge_hint(ALGEBRA_CASE, GOOD_ALGEBRA_HINT, client=client, config=TEST_JUDGE_CONFIG)
    assert result.passed is False

    report = run_deterministic_checks(ALGEBRA_CASE, GOOD_ALGEBRA_HINT)
    report.judge = result

    assert report.deterministic_passed is True
    assert report.passed is False


def test_passing_judge_merged_report_and_to_dict():
    client = MockLLMClient(_canned_rubric())
    result = judge_hint(ALGEBRA_CASE, GOOD_ALGEBRA_HINT, client=client, config=TEST_JUDGE_CONFIG)
    report = run_deterministic_checks(ALGEBRA_CASE, GOOD_ALGEBRA_HINT)
    report.judge = result

    assert report.passed is True
    payload = report.to_dict()
    assert payload["judge"] is not None
    assert payload["judge"]["score"] == 1.0
    assert len(payload["judge"]["checks"]) == 4
    assert payload["passed"] is True


def test_malformed_judge_json_no_crash():
    client = MockLLMClient("not valid json")
    result = judge_hint(ALGEBRA_CASE, GOOD_ALGEBRA_HINT, client=client, config=TEST_JUDGE_CONFIG)

    assert result.passed is False
    assert result.score == 0.0
    assert "error" in result.meta


def test_flag_disagreement_when_model_and_text_check_diverge():
    hint = Hint(
        hint_text="After fixing the sign, you'll get x = 7.",
        reveals_answer=False,
        meta={},
    )
    report = run_deterministic_checks(ALGEBRA_CASE, hint)

    assert report.flag_disagreement() is True
    assert report.to_dict()["flag_disagreement"] is True


def test_flag_disagreement_false_when_aligned():
    report = run_deterministic_checks(ALGEBRA_CASE, GOOD_ALGEBRA_HINT)
    assert report.flag_disagreement() is False


def test_model_answer_disagreement_in_to_dict():
    report = EvalReport(
        case=EVAL_CASES[0],
        hint=GOOD_ALGEBRA_HINT,
        checks=[],
        model_answer_disagreement=True,
    )
    assert report.to_dict()["model_answer_disagreement"] is True
