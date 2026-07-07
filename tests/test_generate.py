import json

from hint_engine.eval_cases import EVAL_CASES
from hint_engine.evaluation import check_does_not_reveal_answer, run_deterministic_checks
from hint_engine.generate import generate_hint
from hint_engine.models import ConversationTurn, Hint, HintRequest
from tests.llm_mocks import TEST_GEN_CONFIG, MockLLMClient


def test_generate_hint_parses_canned_json():
    client = MockLLMClient(
        json.dumps(
            {
                "hint_text": "Check the sign when you move -5 to the other side.",
                "reveals_answer": False,
            }
        )
    )
    request = HintRequest(problem="Solve for x: 2x - 5 = 9", student_answer="x = 2")
    hint = generate_hint(request, client=client, config=TEST_GEN_CONFIG)

    assert hint.hint_text == "Check the sign when you move -5 to the other side."
    assert hint.reveals_answer is False
    assert hint.meta["model"] == TEST_GEN_CONFIG.model
    assert hint.meta["provider"] == "mock"
    assert "latency_ms" in hint.meta


def test_mocked_leaking_output_trips_gate():
    client = MockLLMClient(
        '{"hint_text": "After fixing the sign you get x = 7.", "reveals_answer": false}'
    )
    request = HintRequest(problem="Solve for x: 2x - 5 = 9", student_answer="x = 2")
    hint = generate_hint(request, client=client, config=TEST_GEN_CONFIG)
    case = EVAL_CASES[0]

    report = run_deterministic_checks(case, hint)
    assert report.passed is False
    by_name = {c.name: c for c in report.checks}
    assert by_name["does_not_reveal_answer"].passed is False
    assert not check_does_not_reveal_answer(case, hint).passed


def test_malformed_json_surfaces_error_in_meta():
    client = MockLLMClient("not valid json at all")
    request = HintRequest(problem="2 + 2", student_answer="5")
    hint = generate_hint(request, client=client, config=TEST_GEN_CONFIG)

    assert isinstance(hint, Hint)
    assert "error" in hint.meta
    assert hint.reveals_answer is False


def test_strips_code_fences_from_json():
    client = MockLLMClient(
        "```json\n"
        + json.dumps({"hint_text": "Multiply before adding.", "reveals_answer": False})
        + "\n```"
    )
    request = HintRequest(problem="Evaluate: 2 + 3 × 4", student_answer="20")
    hint = generate_hint(request, client=client, config=TEST_GEN_CONFIG)

    assert hint.hint_text == "Multiply before adding."
    assert "error" not in hint.meta


def test_followup_turn_includes_history_in_prompt():
    client = MockLLMClient(
        json.dumps(
            {
                "hint_text": "Good — now apply that sign fix to both sides.",
                "reveals_answer": False,
            }
        )
    )
    request = HintRequest(
        problem="Solve for x: 2x - 5 = 9",
        student_answer="x = 4",
        history=[
            ConversationTurn(role="student", text="x = 2"),
            ConversationTurn(
                role="tutor", text="Check the sign when you move -5 across."
            ),
        ],
    )
    hint = generate_hint(request, client=client, config=TEST_GEN_CONFIG)

    assert hint.hint_text == "Good — now apply that sign fix to both sides."
    # The model received the prior exchange and the latest attempt.
    assert len(client.calls) == 1
    _system, user = client.calls[0]
    assert "Prior exchange:" in user
    assert "Student: x = 2" in user
    assert "Tutor (you, earlier): Check the sign" in user
    assert "Student's latest answer:\nx = 4" in user


def test_first_turn_has_no_prior_exchange_section():
    client = MockLLMClient(
        json.dumps({"hint_text": "Re-check your sign.", "reveals_answer": False})
    )
    request = HintRequest(problem="Solve for x: 2x - 5 = 9", student_answer="x = 2")
    generate_hint(request, client=client, config=TEST_GEN_CONFIG)

    _system, user = client.calls[0]
    assert "Prior exchange:" not in user


def test_eval_report_to_dict_envelope():
    case = EVAL_CASES[0]
    hint = Hint(
        hint_text="Try again.",
        reveals_answer=False,
        meta={"name": "t", "model": TEST_GEN_CONFIG.model, "provider": "mock"},
    )
    report = run_deterministic_checks(case, hint)
    payload = report.to_dict()

    assert payload["passed"] is report.passed
    assert payload["case_id"] == "algebra_sign_error"
    assert payload["problem"] == case.problem
    assert payload["hint_text"] == hint.hint_text
    assert payload["reveals_answer"] is False
    assert payload["meta"]["model"] == TEST_GEN_CONFIG.model
    assert payload["judge"] is None
    assert payload["flag_disagreement"] is False
    assert payload["model_answer_disagreement"] is None
    assert "deterministic" in payload
    assert len(payload["deterministic"]["checks"]) == 5
    assert isinstance(payload["summary"], str)
