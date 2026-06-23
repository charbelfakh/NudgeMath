from __future__ import annotations

from typing import Any

import strawberry
from strawberry.scalars import JSON

from hint_engine.answer_match import answers_equivalent, resolve_correct_answer
from hint_engine.eval_cases import EVAL_CASES
from hint_engine.evaluation import CheckResult, EvalReport
from hint_engine.generate import generate_hint
from hint_engine.judge import JudgeResult, judge_hint
from hint_engine.models import EvalCase, Hint, HintRequest


def _get_eval_case(case_id: str) -> EvalCase:
    for case in EVAL_CASES:
        if case.case_id == case_id:
            return case
    raise ValueError(f"Unknown eval case id: {case_id!r}")


@strawberry.input
class HintRequestInput:
    problem: str
    student_answer: str
    grade_level: str | None = None
    subject: str | None = None
    correct_answer: str | None = None


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


def _meta_from_dict(meta: dict[str, Any]) -> HintMetaType:
    latency = meta.get("latency_ms")
    return HintMetaType(
        name=meta.get("name"),
        model=meta.get("model"),
        provider=meta.get("provider"),
        latency_ms=int(latency) if latency is not None else None,
        error=meta.get("error"),
    )


def _judge_meta_from_dict(meta: dict[str, Any]) -> JudgeMetaType:
    latency = meta.get("latency_ms")
    return JudgeMetaType(
        name=meta.get("name"),
        model=meta.get("model"),
        provider=meta.get("provider"),
        latency_ms=int(latency) if latency is not None else None,
        error=meta.get("error"),
    )


def _check_result_type(check: CheckResult) -> CheckResultType:
    return CheckResultType(name=check.name, passed=check.passed, detail=check.detail)


def _hint_type(hint: Hint, *, answer_correct: bool = False) -> HintType:
    return HintType(
        hint_text=hint.hint_text,
        reveals_answer=hint.reveals_answer,
        answer_correct=answer_correct,
        meta=_meta_from_dict(hint.meta),
    )


def _eval_case_type(case: EvalCase) -> EvalCaseType:
    return EvalCaseType(
        case_id=case.case_id,
        problem=case.problem,
        student_answer=case.student_answer,
        correct_answer=case.correct_answer,
        expectations=case.expectations,
    )


def _judge_result_type(judge: JudgeResult) -> JudgeResultType:
    return JudgeResultType(
        passed=judge.passed,
        score=judge.score,
        checks=[_check_result_type(item) for item in judge.rubric],
        meta=_judge_meta_from_dict(judge.meta),
    )


def _eval_report_type(report: EvalReport) -> EvalReportType:
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
            meta=_judge_meta_from_dict(judge_payload["meta"]),
        )

    det = payload["deterministic"]
    return EvalReportType(
        passed=payload["passed"],
        case_id=payload["case_id"],
        problem=payload["problem"],
        hint_text=payload["hint_text"],
        reveals_answer=payload["reveals_answer"],
        meta=_meta_from_dict(payload["meta"]),
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


@strawberry.type
class Query:
    @strawberry.field
    def hints(self) -> list[EvalCaseType]:
        """List seed eval cases (eval-side; includes correct_answer for harness use)."""
        return [_eval_case_type(case) for case in EVAL_CASES]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def generate_hint(self, request: HintRequestInput) -> HintType:
        """Generate a pedagogical hint. LLM path is answer-blind; correct_answer gates only."""
        hint_request = HintRequest(
            problem=request.problem,
            student_answer=request.student_answer,
            grade_level=request.grade_level,
            subject=request.subject,
        )
        correct_answer = resolve_correct_answer(
            request.problem,
            EVAL_CASES,
            teacher_correct_answer=request.correct_answer,
        )
        if correct_answer is not None and answers_equivalent(
            request.student_answer, correct_answer
        ):
            return HintType(
                hint_text="",
                reveals_answer=False,
                answer_correct=True,
                meta=HintMetaType(),
            )
        return _hint_type(generate_hint(hint_request))

    @strawberry.mutation
    def evaluate_case(
        self,
        case_id: str,
        with_judge: bool = False,
    ) -> EvalReportType:
        """Run a seed eval case through generation and evaluation."""
        from hint_engine.evaluation import run_deterministic_checks
        from hint_engine.run_eval import case_to_request

        case = _get_eval_case(case_id)
        hint = generate_hint(case_to_request(case))
        report = run_deterministic_checks(case, hint)
        if with_judge:
            report.judge = judge_hint(case, hint)
        return _eval_report_type(report)


schema = strawberry.Schema(query=Query, mutation=Mutation)

# Type names on the answer-blind generation path (verified by schema test).
GENERATION_ROOT_TYPES = frozenset({"HintRequestInput", "HintType", "HintMetaType"})
