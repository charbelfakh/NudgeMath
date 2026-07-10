import json
from unittest.mock import patch

from strawberry.printer import print_schema

from hint_engine.api.schema import GENERATION_ROOT_TYPES, schema
from hint_engine.eval_cases import EVAL_CASES
from tests.llm_mocks import (
    TEST_GEN_CONFIG,
    TEST_JUDGE_CONFIG,
    TEST_VISION_CONFIG,
    MockLLMClient,
    MockVisionClient,
)

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


@patch("hint_engine.generate.get_generation_config", return_value=TEST_GEN_CONFIG)
@patch(
    "hint_engine.generate.client_from_config",
    return_value=MockLLMClient(
        json.dumps(
            {
                "hint_text": "Closer — now apply the sign fix to both sides.",
                "reveals_answer": False,
            }
        )
    ),
)
def test_generate_hint_mutation_with_history(mock_client, mock_config):
    query = """
    mutation {
      generateHint(request: {
        problem: "Solve for x: 2x - 5 = 9"
        studentAnswer: "x = 4"
        history: [
          { role: "student", text: "x = 2" }
          { role: "tutor", text: "Check the sign when you move -5 across." }
        ]
      }) {
        hintText
        answerCorrect
      }
    }
    """
    result = schema.execute_sync(query)

    assert result.errors is None
    hint = result.data["generateHint"]
    assert hint["answerCorrect"] is False
    assert hint["hintText"] == "Closer — now apply the sign fix to both sides."
    _system, user = mock_client.return_value.calls[0]
    assert "Prior exchange:" in user
    assert "Student's latest answer:\nx = 4" in user


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
    result = schema.execute_sync(query, context_value=ADMIN_CTX)

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
    result = schema.execute_sync(query, context_value=ADMIN_CTX)

    assert result.errors is None
    report = result.data["evaluateCase"]
    assert report["deterministic"]["passed"] is True
    assert report["judge"]["passed"] is False
    assert report["passed"] is False


@patch("hint_engine.transcribe.get_vision_config", return_value=TEST_VISION_CONFIG)
@patch(
    "hint_engine.transcribe.vision_client_from_config",
    return_value=MockVisionClient(
        json.dumps({"problem": "Solve for x: 2x - 5 = 9", "student_answer": "x = 2"})
    ),
)
def test_transcribe_problem_mutation(mock_client, mock_config):
    query = """
    mutation {
      transcribeProblem(image: "data:image/png;base64,ZmFrZQ==") {
        problem
        studentAnswer
        meta { model provider }
      }
    }
    """
    result = schema.execute_sync(query)

    assert result.errors is None
    transcription = result.data["transcribeProblem"]
    assert transcription["problem"] == "Solve for x: 2x - 5 = 9"
    assert transcription["studentAnswer"] == "x = 2"
    assert transcription["meta"]["provider"] == "mock"
    # The image reached the vision client verbatim.
    _system, _user, image = mock_client.return_value.calls[0]
    assert image == "data:image/png;base64,ZmFrZQ=="


def test_transcription_type_has_no_correct_answer():
    """The image path is answer-blind: TranscriptionType exposes no answer field."""
    intro = schema.execute_sync(INTROSPECTION_QUERY)
    assert intro.errors is None
    transcription_type = next(
        t for t in intro.data["__schema"]["types"] if t["name"] == "TranscriptionType"
    )
    field_names = {f["name"] for f in transcription_type["fields"]}
    assert "correctAnswer" not in field_names
    assert field_names == {"problem", "studentAnswer", "meta"}


def test_generate_problem_returns_id_not_answer():
    query = """
    mutation {
      generateProblem(gradeLevel: "7", topic: "linear_equations", mode: "template") {
        problem
        problemId
        gradeLevel
        topic
        difficulty
        source
        verified
      }
    }
    """
    result = schema.execute_sync(query)

    assert result.errors is None
    problem = result.data["generateProblem"]
    assert problem["source"] == "template"
    assert problem["verified"] is True
    assert problem["topic"] == "linear_equations"
    assert problem["problem"].startswith("Solve for x:")
    assert problem["problemId"]  # opaque, non-empty


def test_generated_problem_type_has_no_answer_field():
    """The student never receives the answer: no correctAnswer on GeneratedProblemType."""
    intro = schema.execute_sync(INTROSPECTION_QUERY)
    assert intro.errors is None
    gp_type = next(
        t for t in intro.data["__schema"]["types"] if t["name"] == "GeneratedProblemType"
    )
    field_names = {f["name"] for f in gp_type["fields"]}
    assert "correctAnswer" not in field_names
    assert "problemId" in field_names


def test_generated_problem_answer_not_on_generation_path():
    intro = schema.execute_sync(INTROSPECTION_QUERY)
    assert intro.errors is None
    reachable = _collect_reachable_type_names(intro, set(GENERATION_ROOT_TYPES))
    assert "GeneratedProblemType" not in reachable


def test_generate_hint_gates_correctness_via_problem_id():
    """A stored answer gates correctness server-side; the client only sends the id."""
    from hint_engine.api.problem_store import PROBLEM_STORE

    problem_id = PROBLEM_STORE.put("x = 7")
    query = f"""
    mutation {{
      generateHint(request: {{
        problem: "Solve for x: 2x - 5 = 9"
        studentAnswer: "7"
        problemId: "{problem_id}"
      }}) {{
        answerCorrect
        hintText
      }}
    }}
    """
    result = schema.execute_sync(query)

    assert result.errors is None
    hint = result.data["generateHint"]
    assert hint["answerCorrect"] is True  # "7" ~ "x = 7", gated without the LLM
    assert hint["hintText"] == ""


def test_curriculum_query_all_and_by_grade():
    result = schema.execute_sync(
        "{ curriculum { topic gradeBand template } }"
    )
    assert result.errors is None
    all_topics = result.data["curriculum"]
    assert len(all_topics) >= 9
    assert any(t["topic"] == "geometry" and t["template"] for t in all_topics)

    scoped = schema.execute_sync(
        '{ curriculum(gradeLevel: "11") { topic gradeBand } }'
    )
    assert scoped.errors is None
    bands = {t["gradeBand"] for t in scoped.data["curriculum"]}
    topics = {t["topic"] for t in scoped.data["curriculum"]}
    assert bands == {"high"}
    assert topics == {"quadratics", "functions", "geometry"}


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


# --- admin: login, answer reveal, model switching ----------------------------

ADMIN_CTX = {"admin_username": "admin"}
ANON_CTX = {"admin_username": None}


def test_login_success_and_failure():
    from hint_engine.auth import hash_password
    from hint_engine.user_store import InMemoryUserStore, UserRecord

    store = InMemoryUserStore([UserRecord("admin", hash_password("secret"))])
    with patch("hint_engine.api.schema.USER_STORE", store):
        ok = schema.execute_sync(
            'mutation { login(username: "admin", password: "secret")'
            " { token username expiresAt error } }"
        )
        assert ok.errors is None
        payload = ok.data["login"]
        assert payload["token"]
        assert payload["username"] == "admin"
        assert payload["expiresAt"] > 0
        assert payload["error"] is None

        # Usernames are case-insensitive: "ADMIN" resolves to the "admin" account.
        mixed = schema.execute_sync(
            'mutation { login(username: "ADMIN", password: "secret")'
            " { token username } }"
        )
        assert mixed.errors is None
        assert mixed.data["login"]["token"]
        assert mixed.data["login"]["username"] == "admin"

        # Wrong password and unknown user both return the same generic error.
        for username, password in (("admin", "wrong"), ("ghost", "secret")):
            bad = schema.execute_sync(
                f'mutation {{ login(username: "{username}", password: "{password}")'
                " { token error } }"
            )
            assert bad.data["login"]["token"] is None
            assert bad.data["login"]["error"] == "Invalid username or password."


def test_reveal_answer_requires_admin():
    from hint_engine.api.problem_store import PROBLEM_STORE

    problem_id = PROBLEM_STORE.put("x = 42")
    query = (
        f'{{ revealAnswer(problemId: "{problem_id}")'
        " { problemId correctAnswer found } }"
    )

    anon = schema.execute_sync(query, context_value=ANON_CTX)
    assert anon.errors is not None
    assert anon.data["revealAnswer"] is None

    admin = schema.execute_sync(query, context_value=ADMIN_CTX)
    assert admin.errors is None
    revealed = admin.data["revealAnswer"]
    assert revealed["correctAnswer"] == "x = 42"
    assert revealed["found"] is True


def test_reveal_answer_unknown_id_is_not_found():
    query = '{ revealAnswer(problemId: "nope") { correctAnswer found } }'
    res = schema.execute_sync(query, context_value=ADMIN_CTX)
    assert res.errors is None
    assert res.data["revealAnswer"]["found"] is False
    assert res.data["revealAnswer"]["correctAnswer"] is None


def test_reveal_answer_not_on_generation_path():
    """The reveal type must stay off the answer-blind generation path."""
    intro = schema.execute_sync(INTROSPECTION_QUERY)
    assert intro.errors is None
    reachable = _collect_reachable_type_names(intro, set(GENERATION_ROOT_TYPES))
    assert "RevealedAnswerType" not in reachable


def test_admin_models_requires_admin():
    query = (
        "{ adminModels { visionModel generationModel"
        " visionPresets { name provider model } } }"
    )
    anon = schema.execute_sync(query, context_value=ANON_CTX)
    assert anon.errors is not None
    assert anon.data["adminModels"] is None

    admin = schema.execute_sync(query, context_value=ADMIN_CTX)
    assert admin.errors is None
    data = admin.data["adminModels"]
    assert any(p["name"] == "qwen3.5:9b" for p in data["visionPresets"])


def test_set_model_requires_admin_and_applies():
    from hint_engine import config

    mutation = 'mutation { setModel(kind: "vision", preset: "llava:7b") { visionModel } }'
    try:
        anon = schema.execute_sync(mutation, context_value=ANON_CTX)
        assert anon.errors is not None
        assert config.get_model_override("vision") is None  # denied → nothing changed

        admin = schema.execute_sync(mutation, context_value=ADMIN_CTX)
        assert admin.errors is None
        assert admin.data["setModel"]["visionModel"] == "llava:7b"
        assert config.get_vision_config().model == "llava:7b"
    finally:
        config.clear_model_override("vision")


# --- admin: Claude subscription connection -----------------------------------


def test_claude_subscription_surface_requires_admin():
    """The status query and all three OAuth mutations are admin-gated; anonymous
    requests are denied and never run the resolver (no side effects)."""
    fields = [
        "query { claudeSubscription { signedIn detail model } }",
        "mutation { startClaudeLogin { signedIn url } }",
        'mutation { finishClaudeLogin(code: "x") { signedIn error } }',
        "mutation { disconnectClaudeSubscription { signedIn } }",
    ]
    for op in fields:
        anon = schema.execute_sync(op, context_value=ANON_CTX)
        assert anon.errors is not None, op
        # The selected field comes back null under permission denial (data may be
        # None outright if a non-null field null-propagates).
        assert anon.data is None or all(v is None for v in anon.data.values()), op


def test_finish_claude_login_returns_error_on_bad_code(monkeypatch, tmp_path):
    """OAuth failures surface in the `error` field (like login), never raised."""
    from hint_engine import claude_oauth

    monkeypatch.setenv(
        "NUDGEMATH_CLAUDE_OAUTH_TOKENS_PATH", str(tmp_path / "tokens.json")
    )
    claude_oauth.reset_pending()  # no sign-in in progress → finish_login errors
    res = schema.execute_sync(
        'mutation { finishClaudeLogin(code: "whatever") { signedIn error } }',
        context_value=ADMIN_CTX,
    )
    assert res.errors is None
    payload = res.data["finishClaudeLogin"]
    assert payload["signedIn"] is False
    assert payload["error"]


def test_claude_subscription_types_not_on_generation_path():
    """The subscription/OAuth types are admin config surface, not reachable from
    the answer-blind generation root types."""
    intro = schema.execute_sync(INTROSPECTION_QUERY)
    assert intro.errors is None
    reachable = _collect_reachable_type_names(intro, set(GENERATION_ROOT_TYPES))
    for name in (
        "ClaudeSubscriptionStatusType",
        "ClaudeLoginStartType",
        "ClaudeLoginResultType",
    ):
        assert name not in reachable


# --- admin: solver ------------------------------------------------------------


def test_solve_problem_requires_admin_and_returns_solution():
    from hint_engine.models import Solution

    mutation = (
        'mutation { solveProblem(problem: "2x - 5 = 9", gradeLevel: "7")'
        " { solutionText finalAnswer meta { model provider error } } }"
    )

    anon = schema.execute_sync(mutation, context_value=ANON_CTX)
    assert anon.errors is not None
    assert anon.data["solveProblem"] is None

    fake = Solution(
        solution_text="1. Add 5: 2x = 14\n2. Divide: x = 7",
        final_answer="x = 7",
        meta={"model": "test-model", "provider": "mock"},
    )
    with patch("hint_engine.api.schema.build_solution", return_value=fake) as solver:
        admin = schema.execute_sync(mutation, context_value=ADMIN_CTX)
    assert admin.errors is None
    payload = admin.data["solveProblem"]
    assert payload["finalAnswer"] == "x = 7"
    assert "Divide" in payload["solutionText"]
    assert payload["meta"]["provider"] == "mock"
    solver.assert_called_once_with("2x - 5 = 9", "7")


def test_solution_type_not_on_generation_path():
    """solveProblem is a deliberate, admin-gated solving path — like reveal, its
    type must stay unreachable from the answer-blind generation root types."""
    intro = schema.execute_sync(INTROSPECTION_QUERY)
    assert intro.errors is None
    reachable = _collect_reachable_type_names(intro, set(GENERATION_ROOT_TYPES))
    assert "SolutionType" not in reachable


def test_failed_generation_stores_no_answer():
    """A failed LLM generation must not mint a problemId: nothing to gate, and a
    stored empty answer would make revealAnswer report found=True."""
    from hint_engine.api.problem_store import PROBLEM_STORE
    from hint_engine.models import GeneratedProblem

    failed = GeneratedProblem(
        problem="",
        correct_answer="",
        grade_level="7",
        topic="fractions",
        difficulty="medium",
        source="llm",
        verified=False,
        meta={"error": "Connection error."},
    )
    mutation = (
        'mutation { generateProblem(gradeLevel: "7", topic: "fractions")'
        " { problemId meta { error } } }"
    )
    with patch("hint_engine.api.schema.build_problem", return_value=failed):
        res = schema.execute_sync(mutation)
    assert res.errors is None
    payload = res.data["generateProblem"]
    assert payload["meta"]["error"] == "Connection error."
    assert payload["problemId"] == ""
    assert PROBLEM_STORE.get("") is None


def test_admin_models_exposes_solver():
    query = "{ adminModels { solverModel solverPresets { name } } }"
    res = schema.execute_sync(query, context_value=ADMIN_CTX)
    assert res.errors is None
    data = res.data["adminModels"]
    assert data["solverModel"]
    assert any(p["name"] == "llama3.2" for p in data["solverPresets"])


def test_disconnect_clears_subscription_overrides_and_token(monkeypatch, tmp_path):
    """Disconnecting forgets the token and drops generation/vision overrides that
    pointed at the subscription, so nothing keeps routing to an unusable model."""
    import json

    from hint_engine import claude_oauth, config

    tokens = tmp_path / "tokens.json"
    tokens.write_text(json.dumps({"access_token": "tok", "expires_at": 9e12}))
    monkeypatch.setenv("NUDGEMATH_CLAUDE_OAUTH_TOKENS_PATH", str(tokens))

    try:
        for kind in ("generation", "vision", "solver"):
            config.set_model_override(kind, "claude-sonnet-5")
        res = schema.execute_sync(
            "mutation { disconnectClaudeSubscription { signedIn } }",
            context_value=ADMIN_CTX,
        )
        assert res.errors is None
        assert res.data["disconnectClaudeSubscription"]["signedIn"] is False
        assert claude_oauth.is_signed_in() is False
        for kind in ("generation", "vision", "solver"):
            assert config.get_model_override(kind) is None, kind
    finally:
        for kind in ("generation", "vision", "solver"):
            config.clear_model_override(kind)


def test_admin_models_hides_unavailable_then_shows_when_connected(monkeypatch):
    from hint_engine import claude_oauth

    query = "{ adminModels { generationPresets { name } } }"

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(claude_oauth, "is_signed_in", lambda: False)
    out = schema.execute_sync(query, context_value=ADMIN_CTX)
    assert out.errors is None
    names = {p["name"] for p in out.data["adminModels"]["generationPresets"]}
    assert "llama3.2" in names
    assert not names & {"claude-sonnet-5", "claude-opus-4-8", "claude-haiku-4-5"}
    assert "sonnet-4.6" not in names

    monkeypatch.setattr(claude_oauth, "is_signed_in", lambda: True)
    connected = schema.execute_sync(query, context_value=ADMIN_CTX)
    connected_names = {
        p["name"] for p in connected.data["adminModels"]["generationPresets"]
    }
    assert {"claude-sonnet-5", "claude-opus-4-8", "claude-haiku-4-5"} <= connected_names


# --- public surface hardening: auth, rate limits, input caps -------------------


def test_evaluate_case_requires_admin():
    """The costliest mutation (withJudge = two LLM calls) is teacher tooling, not
    a student feature — it must not be reachable anonymously."""
    mutation = 'mutation { evaluateCase(caseId: "algebra_sign_error") { passed } }'
    anon = schema.execute_sync(mutation, context_value=ANON_CTX)
    assert anon.errors is not None
    assert anon.data["evaluateCase"] is None


def test_public_llm_mutations_are_rate_limited(monkeypatch):
    """A client that exhausts its bucket is refused before the model is called."""
    from hint_engine import rate_limit

    called: list[int] = []
    monkeypatch.setattr(
        "hint_engine.api.schema.build_problem",
        lambda *a, **k: called.append(1) or _stub_problem(),
    )
    monkeypatch.setattr(rate_limit.LLM_LIMITER, "_capacity", 2.0)
    rate_limit.reset_all()

    mutation = 'mutation { generateProblem(gradeLevel: "7") { problem } }'
    ctx = {"admin_username": None, "client_key": "1.2.3.4"}
    for _ in range(2):
        assert schema.execute_sync(mutation, context_value=ctx).errors is None

    denied = schema.execute_sync(mutation, context_value=ctx)
    assert denied.errors is not None
    assert "Too many requests" in denied.errors[0].message
    assert len(called) == 2  # the third never reached the generator

    # A different client has its own bucket.
    other = {"admin_username": None, "client_key": "5.6.7.8"}
    assert schema.execute_sync(mutation, context_value=other).errors is None


def _stub_problem():
    from hint_engine.models import GeneratedProblem

    return GeneratedProblem(
        problem="2 + 2 = ?",
        correct_answer="4",
        grade_level="7",
        topic="arithmetic",
        difficulty="medium",
        source="template",
        verified=True,
        meta={},
    )


def test_login_is_rate_limited():
    """Login runs scrypt (~16 MB) with no auth — both a brute-force and a
    memory-amplification surface without a ceiling."""
    from hint_engine import rate_limit

    rate_limit.LOGIN_LIMITER.reset()
    mutation = 'mutation { login(username: "nobody", password: "x") { error } }'
    ctx = {"admin_username": None, "client_key": "9.9.9.9"}

    allowed = 0
    for _ in range(20):
        result = schema.execute_sync(mutation, context_value=ctx)
        if result.errors:
            assert "Too many sign-in attempts" in result.errors[0].message
            break
        allowed += 1
    else:
        raise AssertionError("login was never rate limited")
    assert 1 <= allowed <= 10  # bounded burst, not unlimited


def test_transcribe_rejects_oversized_image():
    from hint_engine.api import limits

    oversized = "data:image/png;base64," + ("A" * (limits.MAX_IMAGE_CHARS + 1))
    result = schema.execute_sync(
        "mutation ($img: String!) { transcribeProblem(image: $img) { problem } }",
        variable_values={"img": oversized},
    )
    assert result.errors is not None
    assert "too large" in result.errors[0].message


def test_generate_hint_rejects_oversized_inputs():
    from hint_engine.api import limits

    long_problem = "x" * (limits.MAX_PROBLEM_CHARS + 1)
    result = schema.execute_sync(
        "mutation ($r: HintRequestInput!) { generateHint(request: $r) { hintText } }",
        variable_values={"r": {"problem": long_problem, "studentAnswer": "x = 2"}},
    )
    assert result.errors is not None
    assert "Problem is too long" in result.errors[0].message


def test_generate_hint_rejects_unbounded_history():
    """Every turn is replayed into the prompt, so an unbounded history makes one
    request arbitrarily expensive."""
    from hint_engine.api import limits

    turns = [
        {"role": "student", "text": "x = 2"}
        for _ in range(limits.MAX_HISTORY_TURNS + 1)
    ]
    result = schema.execute_sync(
        "mutation ($r: HintRequestInput!) { generateHint(request: $r) { hintText } }",
        variable_values={
            "r": {"problem": "2x = 4", "studentAnswer": "x = 1", "history": turns}
        },
    )
    assert result.errors is not None
    assert "history is too long" in result.errors[0].message


def test_set_claude_effort_requires_admin_applies_and_clears():
    from hint_engine import config

    mutation = 'mutation { setClaudeEffort(effort: "xhigh") { effort } }'
    try:
        anon = schema.execute_sync(mutation, context_value=ANON_CTX)
        assert anon.errors is not None
        assert config.get_claude_effort() is None  # denied → unchanged

        admin = schema.execute_sync(mutation, context_value=ADMIN_CTX)
        assert admin.errors is None
        assert admin.data["setClaudeEffort"]["effort"] == "xhigh"
        assert config.get_claude_effort() == "xhigh"

        # Status query reflects it too.
        status = schema.execute_sync(
            "{ claudeSubscription { effort } }", context_value=ADMIN_CTX
        )
        assert status.data["claudeSubscription"]["effort"] == "xhigh"

        # Empty resets to the API default (null).
        cleared = schema.execute_sync(
            'mutation { setClaudeEffort(effort: "") { effort } }',
            context_value=ADMIN_CTX,
        )
        assert cleared.data["setClaudeEffort"]["effort"] is None
        assert config.get_claude_effort() is None

        # Garbage is rejected with a clear message.
        bad = schema.execute_sync(
            'mutation { setClaudeEffort(effort: "turbo") { effort } }',
            context_value=ADMIN_CTX,
        )
        assert bad.errors is not None
        assert "Unknown effort" in bad.errors[0].message
    finally:
        config.set_claude_effort(None)
