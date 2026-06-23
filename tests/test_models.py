from hint_engine.eval_cases import EVAL_CASES
from hint_engine.evaluation import EvalReport, run_deterministic_checks
from hint_engine.generate import generate_hint
from hint_engine.models import EvalCase, Hint, HintRequest

from tests.llm_mocks import MockLLMClient, TEST_GEN_CONFIG


def test_hint_request_round_trip():
    req = HintRequest(
        problem="Solve for x: 2x - 5 = 9",
        student_answer="x = 2",
        grade_level="8",
        subject="algebra",
    )
    assert req.problem == "Solve for x: 2x - 5 = 9"
    assert req.student_answer == "x = 2"
    assert req.grade_level == "8"
    assert req.subject == "algebra"


def test_hint_round_trip():
    hint = Hint(
        hint_text="Check the sign when you move terms to the other side.",
        reveals_answer=False,
        meta={"model": "stub", "latency_ms": 0},
    )
    assert hint.hint_text.startswith("Check the sign")
    assert hint.reveals_answer is False
    assert hint.meta["model"] == "stub"


def test_eval_case_round_trip():
    case = EvalCase(
        problem="Evaluate: 2 + 3 × 4",
        student_answer="20",
        correct_answer="14",
        expectations={"must_not_reveal_answer": True},
    )
    assert case.problem == "Evaluate: 2 + 3 × 4"
    assert case.student_answer == "20"
    assert case.correct_answer == "14"
    assert case.expectations["must_not_reveal_answer"] is True


def test_generate_hint_returns_hint():
    request = HintRequest(problem="2 + 2", student_answer="5")
    client = MockLLMClient('{"hint_text": "Think about counting.", "reveals_answer": false}')

    result = generate_hint(request, client=client, config=TEST_GEN_CONFIG)

    assert isinstance(result, Hint)
    assert isinstance(result.hint_text, str)
    assert len(result.hint_text) > 0
    assert isinstance(result.reveals_answer, bool)
    assert isinstance(result.meta, dict)


def test_eval_cases_seed_dataset():
    assert len(EVAL_CASES) >= 8
    case_ids = [case.case_id for case in EVAL_CASES]
    assert len(case_ids) == len(set(case_ids))
    for case in EVAL_CASES:
        assert isinstance(case, EvalCase)
        assert case.case_id
        assert case.problem
        assert case.student_answer
        assert case.correct_answer
        assert case.student_answer != case.correct_answer
