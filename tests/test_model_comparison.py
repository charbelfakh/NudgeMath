from hint_engine.config import ModelConfig
from hint_engine.eval_cases import EVAL_CASES
from hint_engine.evaluation import EvalReport, run_deterministic_checks
from hint_engine.judge import JudgeResult
from hint_engine.model_comparison import build_comparison_table, format_comparison_table
from hint_engine.models import Hint

from tests.fixtures_hints import ALGEBRA_CASE, GOOD_ALGEBRA_HINT


def _report(
    case,
    hint: Hint,
    *,
    model_name: str,
    with_judge: bool = False,
    judge_model: str = "external-judge",
    judge_error: str | None = None,
) -> EvalReport:
    tagged_hint = Hint(
        hint_text=hint.hint_text,
        reveals_answer=hint.reveals_answer,
        meta={
            **hint.meta,
            "name": model_name,
            "model": model_name,
            "provider": "mock",
        },
    )
    report = run_deterministic_checks(case, tagged_hint)
    if with_judge:
        report.judge = JudgeResult(
            passed=judge_error is None,
            score=0.0 if judge_error else 0.75,
            rubric=[],
            meta={
                "name": "judge",
                "model": judge_model,
                "provider": "mock",
                **({"error": judge_error} if judge_error else {}),
            },
        )
    return report


def test_build_comparison_table_structure():
    case_b = EVAL_CASES[1]
    reports = [
        _report(ALGEBRA_CASE, GOOD_ALGEBRA_HINT, model_name="model-a"),
        _report(case_b, GOOD_ALGEBRA_HINT, model_name="model-a"),
        _report(ALGEBRA_CASE, GOOD_ALGEBRA_HINT, model_name="model-b", with_judge=True),
        _report(case_b, GOOD_ALGEBRA_HINT, model_name="model-b"),
    ]

    table = build_comparison_table(reports)

    assert table.model_names == ["model-a", "model-b"]
    assert len(table.case_ids) == 2
    assert table.cells[("algebra_sign_error", "model-a")].deterministic_passed is True
    assert table.cells[("algebra_sign_error", "model-b")].judge_score == 0.75
    assert table.aggregates["model-a"].deterministic_passed == 2
    assert table.aggregates["model-b"].judge_mean_score == 0.75


def test_comparison_table_print_shape():
    reports = [
        _report(ALGEBRA_CASE, GOOD_ALGEBRA_HINT, model_name="alpha"),
        _report(
            ALGEBRA_CASE,
            GOOD_ALGEBRA_HINT,
            model_name="beta",
            with_judge=True,
            judge_model="sonnet-4.6",
        ),
    ]
    table = build_comparison_table(reports)
    text = format_comparison_table(table, with_judge=True)
    assert "Judge held constant: judge" in text
    assert "alpha" in text
    assert "beta" in text
    assert "judge_ok" in text
    assert "parse_fail" in text
    assert "Aggregates per model" in text


def test_judge_parse_fail_separated_from_deterministic():
    case_b = EVAL_CASES[1]
    reports = [
        _report(
            ALGEBRA_CASE,
            GOOD_ALGEBRA_HINT,
            model_name="flaky-judge",
            with_judge=True,
            judge_error="JSON parse error",
        ),
        _report(
            case_b,
            GOOD_ALGEBRA_HINT,
            model_name="flaky-judge",
            with_judge=True,
            judge_error="JSON parse error",
        ),
        _report(
            ALGEBRA_CASE,
            GOOD_ALGEBRA_HINT,
            model_name="good-gen",
            with_judge=True,
        ),
        _report(case_b, GOOD_ALGEBRA_HINT, model_name="good-gen", with_judge=True),
    ]

    table = build_comparison_table(reports)

    flaky = table.aggregates["flaky-judge"]
    good = table.aggregates["good-gen"]
    assert flaky.deterministic_passed == 2
    assert flaky.deterministic_total == 2
    assert flaky.judge_parse_failures == 2
    assert good.deterministic_passed == 2
    assert good.judge_parse_failures == 0

    text = format_comparison_table(table, with_judge=True)
    assert "flaky-judge" in text
    assert "parse_fail 2/2" in text
    assert "good-gen" in text
    assert "parse_fail 0/2" in text


def test_self_judged_cell_flag():
    self_report = _report(
        ALGEBRA_CASE,
        GOOD_ALGEBRA_HINT,
        model_name="llama3.2",
        with_judge=True,
        judge_model="llama3.2",
    )
    external_report = _report(
        ALGEBRA_CASE,
        GOOD_ALGEBRA_HINT,
        model_name="llama3.2",
        with_judge=True,
        judge_model="sonnet-4.6",
    )

    self_table = build_comparison_table(
        [self_report],
        judge_config=ModelConfig(
            name="llama3.2",
            provider="ollama",
            base_url="http://localhost:11434/v1",
            model="llama3.2",
        ),
    )
    assert self_table.cells[("algebra_sign_error", "llama3.2")].self_judged is True

    external_table = build_comparison_table(
        [external_report],
        judge_config=ModelConfig(
            name="sonnet-4.6",
            provider="anthropic",
            base_url="https://api.anthropic.com/v1/",
            model="claude-sonnet-4-6",
            api_key_env="ANTHROPIC_API_KEY",
        ),
    )
    assert external_table.cells[("algebra_sign_error", "llama3.2")].self_judged is False

    text = format_comparison_table(self_table, with_judge=True)
    assert "*" in text
    assert "* self-judged — not comparable" in text

    external_text = format_comparison_table(external_table, with_judge=True)
    assert "* self-judged" not in external_text


def test_eval_report_to_dict_unchanged_shape():
    report = run_deterministic_checks(
        ALGEBRA_CASE,
        Hint(
            hint_text="nudge",
            reveals_answer=False,
            meta={"name": "m", "model": "m1", "provider": "mock"},
        ),
    )
    payload = report.to_dict()
    assert set(payload.keys()) == {
        "passed",
        "case_id",
        "problem",
        "hint_text",
        "reveals_answer",
        "meta",
        "flag_disagreement",
        "model_answer_disagreement",
        "deterministic",
        "judge",
        "summary",
    }
