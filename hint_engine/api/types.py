"""Strawberry types and dataclass→GraphQL converters.

Shapes only, no resolvers — behavior lives in ``api/schema.py``. Keeping them
apart matters here because ``GENERATION_ROOT_TYPES`` (the answer-blind boundary)
is defined next to the types it names, so a reviewer can see the whole contract
in one file instead of scrolling past 300 lines of resolvers.

Python remains the source of truth: these mirror ``hint_engine/models.py`` and
``EvalReport.to_dict()``; ``schema.graphql`` and the TypeScript client are
derived from them, never the reverse.
"""

from __future__ import annotations

from typing import Any

import strawberry
from strawberry.scalars import JSON

from hint_engine import claude_oauth, config
from hint_engine.config import ModelConfig
from hint_engine.evaluation import CheckResult, EvalReport
from hint_engine.judge import JudgeResult
from hint_engine.models import EvalCase, Hint

# --- generation path (answer-blind) -------------------------------------------


@strawberry.input
class ConversationTurnInput:
    role: str  # "student" | "tutor"
    text: str


@strawberry.input
class HintRequestInput:
    problem: str
    student_answer: str
    grade_level: str | None = None
    subject: str | None = None
    correct_answer: str | None = None
    # Opaque id from generateProblem (practice mode). Gates correctness server-side
    # so the answer never travels to the client. Not forwarded to generate_hint().
    problem_id: str | None = None
    history: list[ConversationTurnInput] | None = None


@strawberry.type
class HintMetaType:
    name: str | None = None
    model: str | None = None
    provider: str | None = None
    latency_ms: int | None = None
    error: str | None = None


@strawberry.type
class HintType:
    hint_text: str
    reveals_answer: bool
    answer_correct: bool
    meta: HintMetaType


# Type names on the answer-blind generation path. Nothing reachable from these
# may expose a correct answer — enforced by introspection tests in test_api.py.
GENERATION_ROOT_TYPES = frozenset({"HintRequestInput", "HintType", "HintMetaType"})


@strawberry.type
class TranscriptionType:
    """Text read off an image — answer-blind, feeds an ordinary HintRequestInput."""

    problem: str
    student_answer: str
    meta: HintMetaType


@strawberry.type
class GeneratedProblemType:
    """A generated practice problem. The correct answer is **not** included — it is
    held server-side keyed by ``problemId`` (see ``problem_store``), so the student
    never receives it. Correctness is gated on the server when a hint is requested."""

    problem: str
    problem_id: str
    grade_level: str
    topic: str
    difficulty: str
    source: str
    verified: bool
    meta: HintMetaType


@strawberry.type
class CurriculumTopicType:
    grade_band: str
    grade_range: str
    topic: str
    template: bool
    difficulties: list[str]
    description: str


# --- eval surface --------------------------------------------------------------


@strawberry.type
class EvalCaseType:
    case_id: str | None
    problem: str
    student_answer: str
    correct_answer: str
    expectations: JSON


@strawberry.type
class CheckResultType:
    name: str
    passed: bool
    detail: str


@strawberry.type
class DeterministicResultType:
    passed: bool
    checks: list[CheckResultType]


@strawberry.type
class JudgeMetaType:
    name: str | None = None
    model: str | None = None
    provider: str | None = None
    latency_ms: int | None = None
    error: str | None = None


@strawberry.type
class JudgeResultType:
    passed: bool
    score: float
    checks: list[CheckResultType]
    meta: JudgeMetaType


@strawberry.type
class EvalReportType:
    passed: bool
    case_id: str | None
    problem: str
    hint_text: str
    reveals_answer: bool
    meta: HintMetaType
    flag_disagreement: bool
    model_answer_disagreement: bool | None
    deterministic: DeterministicResultType
    judge: JudgeResultType | None
    summary: str


# --- admin surface (auth-gated; deliberately off the generation path) -----------


@strawberry.type
class AuthPayloadType:
    token: str | None = None
    username: str | None = None
    expires_at: int | None = None
    error: str | None = None


@strawberry.type
class RevealedAnswerType:
    """Admin-only reveal of a stored practice answer. Deliberately **off** the
    answer-blind generation path (not in GENERATION_ROOT_TYPES): the answer only
    surfaces here, behind auth, and never on HintType / GeneratedProblemType."""

    problem_id: str
    correct_answer: str | None
    found: bool


@strawberry.type
class SolutionType:
    """Admin-only worked solution (separate solver model). Like
    RevealedAnswerType, deliberately **off** the answer-blind generation path —
    not in GENERATION_ROOT_TYPES, produced behind IsAdmin, never fed to the
    student hint flow."""

    solution_text: str
    final_answer: str
    meta: HintMetaType


@strawberry.type
class ModelPresetType:
    name: str
    provider: str
    model: str


@strawberry.type
class AdminModelsType:
    vision_model: str
    generation_model: str
    solver_model: str
    vision_presets: list[ModelPresetType]
    generation_presets: list[ModelPresetType]
    solver_presets: list[ModelPresetType]


@strawberry.type
class ClaudeSubscriptionStatusType:
    """Admin-only status of the in-app Claude-subscription connection.

    Config surface only — off the answer-blind generation path (not in
    GENERATION_ROOT_TYPES) and never touches generate_hint()."""

    signed_in: bool
    detail: str
    model: str
    # Current effort level ("low"…"max"); null = the API default ("high").
    effort: str | None


@strawberry.type
class ClaudeLoginStartType:
    """Result of starting the OAuth sign-in: the URL to approve at claude.ai."""

    signed_in: bool
    url: str | None = None


@strawberry.type
class ClaudeLoginResultType:
    """Result of exchanging the pasted code. Errors surface here (not raised),
    mirroring AuthPayloadType so the client renders them inline."""

    signed_in: bool
    detail: str
    error: str | None = None


# --- converters ----------------------------------------------------------------


def _meta_fields(meta: dict[str, Any]) -> dict[str, Any]:
    """Common meta envelope fields, shared by HintMetaType and JudgeMetaType
    (distinct GraphQL types by design — the hint and judge meta contracts may
    diverge — but built from the same dict shape)."""
    latency = meta.get("latency_ms")
    return {
        "name": meta.get("name"),
        "model": meta.get("model"),
        "provider": meta.get("provider"),
        "latency_ms": int(latency) if latency is not None else None,
        "error": meta.get("error"),
    }


def meta_from_dict(meta: dict[str, Any]) -> HintMetaType:
    return HintMetaType(**_meta_fields(meta))


def judge_meta_from_dict(meta: dict[str, Any]) -> JudgeMetaType:
    return JudgeMetaType(**_meta_fields(meta))


def check_result_type(check: CheckResult) -> CheckResultType:
    return CheckResultType(name=check.name, passed=check.passed, detail=check.detail)


def hint_type(hint: Hint, *, answer_correct: bool = False) -> HintType:
    return HintType(
        hint_text=hint.hint_text,
        reveals_answer=hint.reveals_answer,
        answer_correct=answer_correct,
        meta=meta_from_dict(hint.meta),
    )


def eval_case_type(case: EvalCase) -> EvalCaseType:
    return EvalCaseType(
        case_id=case.case_id,
        problem=case.problem,
        student_answer=case.student_answer,
        correct_answer=case.correct_answer,
        expectations=case.expectations,
    )


def judge_result_type(judge: JudgeResult) -> JudgeResultType:
    return JudgeResultType(
        passed=judge.passed,
        score=judge.score,
        checks=[check_result_type(item) for item in judge.rubric],
        meta=judge_meta_from_dict(judge.meta),
    )


def eval_report_type(report: EvalReport) -> EvalReportType:
    payload = report.to_dict()
    judge_payload = payload["judge"]
    judge = None
    if judge_payload is not None:
        judge = JudgeResultType(
            passed=judge_payload["passed"],
            score=judge_payload["score"],
            checks=[
                CheckResultType(name=c["name"], passed=c["passed"], detail=c["detail"])
                for c in judge_payload["checks"]
            ],
            meta=judge_meta_from_dict(judge_payload["meta"]),
        )

    det = payload["deterministic"]
    return EvalReportType(
        passed=payload["passed"],
        case_id=payload["case_id"],
        problem=payload["problem"],
        hint_text=payload["hint_text"],
        reveals_answer=payload["reveals_answer"],
        meta=meta_from_dict(payload["meta"]),
        flag_disagreement=payload["flag_disagreement"],
        model_answer_disagreement=payload["model_answer_disagreement"],
        deterministic=DeterministicResultType(
            passed=det["passed"],
            checks=[
                CheckResultType(name=c["name"], passed=c["passed"], detail=c["detail"])
                for c in det["checks"]
            ],
        ),
        judge=judge,
        summary=payload["summary"],
    )


def curriculum_topic_type(entry: object) -> CurriculumTopicType:
    return CurriculumTopicType(
        grade_band=entry.grade_band,
        grade_range=entry.grade_range,
        topic=entry.topic,
        template=entry.template,
        difficulties=list(entry.difficulties),
        description=entry.description,
    )


def model_preset_type(cfg: ModelConfig) -> ModelPresetType:
    return ModelPresetType(name=cfg.name, provider=cfg.provider, model=cfg.model)


def admin_models_type() -> AdminModelsType:
    # Only *available* presets (credential/sign-in present) are offered, so the
    # UI never lists a model that would fail on the next request.
    return AdminModelsType(
        vision_model=config.get_vision_config().name,
        generation_model=config.get_generation_config().name,
        solver_model=config.get_solver_config().name,
        vision_presets=[
            model_preset_type(c) for c in config.list_available_model_presets("vision")
        ],
        generation_presets=[
            model_preset_type(c)
            for c in config.list_available_model_presets("generation")
        ],
        solver_presets=[
            model_preset_type(c) for c in config.list_available_model_presets("solver")
        ],
    )


def claude_status_type() -> ClaudeSubscriptionStatusType:
    signed_in = claude_oauth.is_signed_in()
    detail = (
        "Signed in — pick a Claude model (Sonnet/Opus/Haiku) in the dropdowns above."
        if signed_in
        else "Not signed in — click Connect to sign in with your Claude subscription."
    )
    return ClaudeSubscriptionStatusType(
        signed_in=signed_in,
        detail=detail,
        model=config.claude_subscription_model(),
        effort=config.get_claude_effort(),
    )
