import json
from unittest.mock import patch

from strawberry.printer import print_schema

from hint_engine.api.schema import GENERATION_ROOT_TYPES, schema
from hint_engine.eval_cases import EVAL_CASES

from tests.llm_mocks import MockLLMClient, TEST_GEN_CONFIG, TEST_JUDGE_CONFIG

INTROSPECTION_QUERY = """
query Introspection {
  __schema {
    types {
      name
      kind
      fields {
        name
        type {
          name
          kind
          ofType {
            name
            kind
            ofType {
              name
              kind
            }
          }
        }
      }
      inputFields {
        name
        type {
          name
          kind
          ofType {
            name
            kind
          }
        }
      }
    }
  }
}
"""


def _unwrap_type_name(type_ref: dict) -> str | None:
    if type_ref.get("name"):
        return type_ref["name"]
    inner = type_ref.get("ofType")
    if inner:
        return _unwrap_type_name(inner)
    return None


def _collect_reachable_type_names(intro_result, root_names: set[str]) -> set[str]:
    types_by_name = {
        t["name"]: t for t in intro_result.data["__schema"]["types"] if t["name"]
    }
    reachable: set[str] = set()
    queue = list(root_names)

    while queue:
        type_name = queue.pop()
        if type_name in reachable or type_name not in types_by_name:
            continue
        reachable.add(type_name)
        type_def = types_by_name[type_name]
        field_defs = (type_def.get("fields") or []) + (type_def.get("inputFields") or [])
        for field in field_defs:
            nested = _unwrap_type_name(field["type"])
            if nested and nested not in ("String", "Boolean", "Int", "Float", "JSON"):
                queue.append(nested)

    return reachable


@patch("hint_engine.generate.get_generation_config", return_value=TEST_GEN_CONFIG)
@patch(
    "hint_engine.generate.client_from_config",
    return_value=MockLLMClient(
        json.dumps(
            {
                "hint_text": "Check the sign when moving terms.",
                "reveals_answer": False,
            }
        )
    ),
)
def test_generate_hint_mutation(mock_client, mock_config):
    query = """
    mutation {
      generateHint(request: {
        problem: "Solve for x: 2x - 5 = 9"
        studentAnswer: "x = 2"
        gradeLevel: "8"
        subject: "algebra"
      }) {
        hintText
        revealsAnswer
        answerCorrect
        meta { name model provider latencyMs error }
      }
    }
    """
    result = schema.execute_sync(query)

    assert result.errors is None
    hint = result.data["generateHint"]
    assert hint["hintText"] == "Check the sign when moving terms."
    assert hint["revealsAnswer"] is False
    assert hint["answerCorrect"] is False
    assert hint["meta"]["model"] == TEST_GEN_CONFIG.model
    assert hint["meta"]["provider"] == "mock"


def test_generate_hint_skips_when_answer_is_correct():
    query = """
    mutation {
      generateHint(request: {
        problem: "Solve for x: 2x - 5 = 9"
        studentAnswer: "x = 7"
      }) {
        hintText
        answerCorrect
        meta { error }
      }
    }
    """
    result = schema.execute_sync(query)

    assert result.errors is None
    hint = result.data["generateHint"]
    assert hint["answerCorrect"] is True
    assert hint["hintText"] == ""


@patch("hint_engine.generate.get_generation_config", return_value=TEST_GEN_CONFIG)
@patch(
    "hint_engine.generate.client_from_config",
    return_value=MockLLMClient(
        json.dumps(
            {
                "hint_text": "should not be called",
                "reveals_answer": False,
            }
        )
    ),
)
def test_generate_hint_accepts_equivalent_answer_forms(mock_client, mock_config):
    for student_answer in ("7", "=7", "x = 7"):
        query = f"""
        mutation {{
          generateHint(request: {{
            problem: "Solve for x: 2x - 5 = 9"
            studentAnswer: "{student_answer}"
          }}) {{
            answerCorrect
            hintText
          }}
        }}
        """
        result = schema.execute_sync(query)
        assert result.errors is None
        assert result.data["generateHint"]["answerCorrect"] is True
        assert result.data["generateHint"]["hintText"] == ""

    mock_client.assert_not_called()


def test_generation_path_has_no_correct_answer_on_output():
    intro = schema.execute_sync(INTROSPECTION_QUERY)
    assert intro.errors is None

    reachable = _collect_reachable_type_names(intro, set(GENERATION_ROOT_TYPES))
    types_by_name = {
        t["name"]: t for t in intro.data["__schema"]["types"] if t["name"]
    }

    forbidden = "correctAnswer"
    violations: list[str] = []
    for type_name in reachable:
        type_def = types_by_name[type_name]
        for field in type_def.get("fields") or []:
            if field["name"] == forbidden:
                violations.append(f"{type_name}.{forbidden}")

    assert violations == [], (
        "Answer-blind boundary violated — correctAnswer on generation response: "
        + ", ".join(violations)
    )

    input_fields = {
        f["name"] for f in types_by_name["HintRequestInput"]["inputFields"]
    }
    assert "correctAnswer" in input_fields


def test_generate_hint_skips_with_teacher_correct_answer_for_custom_problem():
    query = """
    mutation {
      generateHint(request: {
        problem: "What is 3 + 4?"
        studentAnswer: "7"
        correctAnswer: "7"
      }) {
        hintText
        answerCorrect
      }
    }
    """
    result = schema.execute_sync(query)

    assert result.errors is None
    hint = result.data["generateHint"]
    assert hint["answerCorrect"] is True
    assert hint["hintText"] == ""


@patch("hint_engine.generate.get_generation_config", return_value=TEST_GEN_CONFIG)
@patch(
    "hint_engine.generate.client_from_config",
    return_value=MockLLMClient(
        json.dumps({"hint_text": "Check the sign when moving terms.", "reveals_answer": False})
    ),
)
def test_evaluate_case_deterministic(mock_client, mock_config):
    query = """
    mutation {
      evaluateCase(caseId: "algebra_sign_error") {
        passed
        caseId
        hintText
        summary
        deterministic {
          passed
          checks { name passed }
        }
        judge { passed score }
      }
    }
    """
    result = schema.execute_sync(query)

    assert result.errors is None
    report = result.data["evaluateCase"]
    assert report["caseId"] == "algebra_sign_error"
    assert report["deterministic"]["passed"] is True
    assert report["passed"] is True
    assert report["judge"] is None
    assert len(report["deterministic"]["checks"]) == 5


@patch("hint_engine.generate.get_generation_config", return_value=TEST_GEN_CONFIG)
@patch("hint_engine.judge.get_judge_config", return_value=TEST_JUDGE_CONFIG)
@patch(
    "hint_engine.generate.client_from_config",
    return_value=MockLLMClient(
        json.dumps({"hint_text": "Check the sign when moving terms.", "reveals_answer": False})
    ),
)
@patch(
    "hint_engine.judge.client_from_config",
    return_value=MockLLMClient(
        json.dumps(
            {
                "rubric": [
                    {"name": "addresses_specific_error", "passed": True, "detail": "ok"},
                    {"name": "no_semantic_answer_leak", "passed": False, "detail": "leaked"},
                    {"name": "appropriate_for_level", "passed": True, "detail": "ok"},
                    {"name": "guides_without_solving", "passed": True, "detail": "ok"},
                ]
            }
        )
    ),
)
def test_evaluate_case_with_judge_gates_merged_pass(
    mock_judge_client, mock_gen_client, mock_judge_cfg, mock_gen_cfg
):
    query = """
    mutation {
      evaluateCase(caseId: "algebra_sign_error", withJudge: true) {
        passed
        deterministic { passed }
        judge { passed score checks { name passed } }
      }
    }
    """
    result = schema.execute_sync(query)

    assert result.errors is None
    report = result.data["evaluateCase"]
    assert report["deterministic"]["passed"] is True
    assert report["judge"]["passed"] is False
    assert report["passed"] is False


def test_hints_query_lists_seed_cases():
    query = """
    query {
      hints {
        caseId
        problem
        correctAnswer
      }
    }
    """
    result = schema.execute_sync(query)

    assert result.errors is None
    assert len(result.data["hints"]) == len(EVAL_CASES)
    assert result.data["hints"][0]["caseId"] == "algebra_sign_error"


def test_eval_report_type_fields_match_to_dict_envelope():
    """EvalReportType top-level fields must track EvalReport.to_dict() exactly."""
    intro = schema.execute_sync(INTROSPECTION_QUERY)
    assert intro.errors is None

    report_type = next(
        t for t in intro.data["__schema"]["types"] if t["name"] == "EvalReportType"
    )
    graphql_fields = {f["name"] for f in report_type["fields"]}

    expected_from_to_dict = {
        "passed",
        "caseId",
        "problem",
        "hintText",
        "revealsAnswer",
        "meta",
        "flagDisagreement",
        "modelAnswerDisagreement",
        "deterministic",
        "judge",
        "summary",
    }

    assert graphql_fields == expected_from_to_dict


def test_schema_sdl_is_available():
    sdl = print_schema(schema)
    assert "type HintType" in sdl
    assert "generateHint" in sdl
