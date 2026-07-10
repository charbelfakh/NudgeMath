"""GraphQL resolvers and schema assembly.

Shapes live in ``api/types.py``; request-context concerns (``IsAdmin``, the
rate-limit bucket key) live in ``api/context.py``. This module is behavior only:
what each field does, what it costs, and who may call it.

Two boundaries run through every resolver here:

* **Answer-blind** — the generation path (``generateHint`` and the front-stages
  that feed it) never receives or returns a correct answer. Admin paths that do
  produce answers (``revealAnswer``, ``solveProblem``) are auth-gated and
  unreachable from ``GENERATION_ROOT_TYPES``.
* **Cost** — public mutations are paid; each rate-limits and size-caps before
  touching a model. See ``api/limits.py`` and ``hint_engine/rate_limit.py``.
"""

from __future__ import annotations

import time

import strawberry

from hint_engine import claude_oauth, config
from hint_engine.answer_match import answers_equivalent, resolve_correct_answer
from hint_engine.api import limits
from hint_engine.api.context import (
    LLM_RATE_MESSAGE,
    LOGIN_RATE_MESSAGE,
    IsAdmin,
    client_key,
)
from hint_engine.api.problem_store import PROBLEM_STORE
from hint_engine.api.types import (
    GENERATION_ROOT_TYPES,
    AdminModelsType,
    AuthPayloadType,
    ClaudeLoginResultType,
    ClaudeLoginStartType,
    ClaudeSubscriptionStatusType,
    CurriculumTopicType,
    EvalCaseType,
    EvalReportType,
    GeneratedProblemType,
    HintMetaType,
    HintRequestInput,
    HintType,
    RevealedAnswerType,
    SolutionType,
    TranscriptionType,
    admin_models_type,
    claude_status_type,
    curriculum_topic_type,
    eval_case_type,
    eval_report_type,
    hint_type,
    meta_from_dict,
)
from hint_engine.auth import SESSION_TTL_SECONDS, create_token, verify_password
from hint_engine.curriculum import CURRICULUM, band_for_grade, topics_for_band
from hint_engine.eval_cases import EVAL_CASES
from hint_engine.generate import generate_hint
from hint_engine.judge import judge_hint
from hint_engine.models import ConversationTurn, EvalCase, HintRequest
from hint_engine.problem_gen import generate_problem as build_problem
from hint_engine.rate_limit import LLM_LIMITER, LOGIN_LIMITER
from hint_engine.solve import solve_problem as build_solution
from hint_engine.transcribe import transcribe_problem
from hint_engine.user_store import USER_STORE, normalize_username

__all__ = ["GENERATION_ROOT_TYPES", "Mutation", "Query", "schema"]


def _get_eval_case(case_id: str) -> EvalCase:
    for case in EVAL_CASES:
        if case.case_id == case_id:
            return case
    raise ValueError(f"Unknown eval case id: {case_id!r}")


@strawberry.type
class Query:
    @strawberry.field
    def hints(self) -> list[EvalCaseType]:
        """List seed eval cases (eval-side; includes correct_answer for harness use)."""
        return [eval_case_type(case) for case in EVAL_CASES]

    @strawberry.field
    def curriculum(self, grade_level: str | None = None) -> list[CurriculumTopicType]:
        """K-12 topic taxonomy. With ``gradeLevel``, returns only that band's topics,
        so the client renders grade-appropriate pickers without duplicating band logic.
        """
        entries = CURRICULUM
        if grade_level:
            entries = topics_for_band(band_for_grade(grade_level))
        return [curriculum_topic_type(entry) for entry in entries]

    @strawberry.field(permission_classes=[IsAdmin])
    def reveal_answer(self, problem_id: str) -> RevealedAnswerType | None:
        """Admin-only: the stored correct answer for a practice ``problemId``.

        Reads the same server-side PROBLEM_STORE the hint path gates against — no
        solving, no answer on any student-facing type.
        """
        answer = PROBLEM_STORE.get(problem_id)
        return RevealedAnswerType(
            problem_id=problem_id, correct_answer=answer, found=answer is not None
        )

    @strawberry.field(permission_classes=[IsAdmin])
    def admin_models(self) -> AdminModelsType | None:
        """Admin-only: current vision/generation models + selectable presets."""
        return admin_models_type()

    @strawberry.field(permission_classes=[IsAdmin])
    def claude_subscription(self) -> ClaudeSubscriptionStatusType | None:
        """Admin-only: whether the Claude subscription is connected (OAuth signed in)."""
        return claude_status_type()


@strawberry.type
class Mutation:
    # --- public, paid: rate-limited + size-capped before any model call --------

    @strawberry.mutation
    def generate_hint(self, info: strawberry.Info, request: HintRequestInput) -> HintType:
        """Generate a pedagogical hint. LLM path is answer-blind; correct_answer gates only.

        Public + paid: rate-limited per client and size-capped before the LLM call.
        """
        LLM_LIMITER.check(client_key(info), message=LLM_RATE_MESSAGE)
        limits.check_length(
            request.problem, limit=limits.MAX_PROBLEM_CHARS, field="Problem"
        )
        limits.check_length(
            request.student_answer, limit=limits.MAX_ANSWER_CHARS, field="Student answer"
        )
        limits.check_length(
            request.correct_answer, limit=limits.MAX_ANSWER_CHARS, field="Correct answer"
        )
        limits.check_length(
            request.grade_level, limit=limits.MAX_LABEL_CHARS, field="Grade level"
        )
        limits.check_length(request.subject, limit=limits.MAX_LABEL_CHARS, field="Subject")
        limits.check_history(request.history or [])

        history = [
            ConversationTurn(
                role="student" if turn.role == "student" else "tutor",
                text=turn.text,
            )
            for turn in (request.history or [])
        ]
        hint_request = HintRequest(
            problem=request.problem,
            student_answer=request.student_answer,
            grade_level=request.grade_level,
            subject=request.subject,
            history=history,
        )
        # Practice mode: the answer lives only on the server, looked up by problem_id.
        # Falls back to seed-case / teacher-supplied resolution for other flows.
        correct_answer: str | None = None
        if request.problem_id:
            correct_answer = PROBLEM_STORE.get(request.problem_id)
        if correct_answer is None:
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
        return hint_type(generate_hint(hint_request))

    @strawberry.mutation
    def transcribe_problem(self, info: strawberry.Info, image: str) -> TranscriptionType:
        """Transcribe a math problem from an image (a base64 ``data:`` URL).

        Answer-blind: returns only the extracted problem text and any visible student
        attempt — never a correct answer — for the client to feed into generateHint.

        Public + paid: rate-limited per client, and the image is size-capped before
        it is decoded or sent to a vision model.
        """
        LLM_LIMITER.check(client_key(info), message=LLM_RATE_MESSAGE)
        limits.check_image_data_url(image)
        result = transcribe_problem(image)
        return TranscriptionType(
            problem=result.problem,
            student_answer=result.student_answer,
            meta=meta_from_dict(result.meta),
        )

    @strawberry.mutation
    def generate_problem(
        self,
        info: strawberry.Info,
        grade_level: str,
        topic: str | None = None,
        difficulty: str = "medium",
        mode: str = "auto",
    ) -> GeneratedProblemType:
        """Generate a grade-appropriate practice problem.

        ``correctAnswer`` is practice/teacher-side (for gating + eval) and is never
        passed into generate_hint — the student's hint flow stays answer-blind.

        Public + potentially paid (``mode="llm"``): rate-limited per client.
        """
        LLM_LIMITER.check(client_key(info), message=LLM_RATE_MESSAGE)
        for label, value in (
            ("Grade level", grade_level),
            ("Topic", topic),
            ("Difficulty", difficulty),
            ("Mode", mode),
        ):
            limits.check_length(value, limit=limits.MAX_LABEL_CHARS, field=label)
        problem = build_problem(
            grade_level, topic=topic, difficulty=difficulty, mode=mode
        )
        # Keep the answer server-side; hand the client only an opaque id — and
        # only for a real problem: a failed generation has nothing to gate, and
        # storing its empty answer would make revealAnswer report found=True.
        problem_id = ""
        if problem.problem and not problem.meta.get("error"):
            problem_id = PROBLEM_STORE.put(problem.correct_answer)
        return GeneratedProblemType(
            problem=problem.problem,
            problem_id=problem_id,
            grade_level=problem.grade_level,
            topic=problem.topic,
            difficulty=problem.difficulty,
            source=problem.source,
            verified=problem.verified,
            meta=meta_from_dict(problem.meta),
        )

    @strawberry.mutation
    def login(
        self, info: strawberry.Info, username: str, password: str
    ) -> AuthPayloadType:
        """Exchange admin credentials for a signed session token.

        The error is deliberately generic (no user-enumeration): a wrong username
        and a wrong password return the same message.

        Rate-limited per client: this is the one unauthenticated path that runs
        scrypt (~16 MB of work per attempt), so it is both a brute-force surface
        and a memory-amplification one.
        """
        LOGIN_LIMITER.check(client_key(info), message=LOGIN_RATE_MESSAGE)
        limits.check_length(username, limit=limits.MAX_LABEL_CHARS, field="Username")
        limits.check_length(password, limit=limits.MAX_ANSWER_CHARS, field="Password")
        record = USER_STORE.get(normalize_username(username))
        if record is None or not verify_password(password, record.password_hash):
            return AuthPayloadType(error="Invalid username or password.")
        expires_at = int(time.time()) + SESSION_TTL_SECONDS
        return AuthPayloadType(
            token=create_token(record.username),
            username=record.username,
            expires_at=expires_at,
        )

    # --- admin: teacher tooling and runtime config -----------------------------

    @strawberry.mutation(permission_classes=[IsAdmin])
    def evaluate_case(
        self,
        case_id: str,
        with_judge: bool = False,
    ) -> EvalReportType | None:
        """Admin-only: run a seed eval case through generation and evaluation.

        Teacher/portfolio tooling, never a student feature — and the costliest
        mutation on the server (``withJudge`` fires a *second* LLM call), so it
        must not be reachable anonymously.
        """
        from hint_engine.evaluation import run_deterministic_checks
        from hint_engine.run_eval import case_to_request

        case = _get_eval_case(case_id)
        hint = generate_hint(case_to_request(case))
        report = run_deterministic_checks(case, hint)
        if with_judge:
            report.judge = judge_hint(case, hint)
        return eval_report_type(report)

    @strawberry.mutation(permission_classes=[IsAdmin])
    def set_model(self, kind: str, preset: str) -> AdminModelsType | None:
        """Admin-only: point the vision or generation model at a named preset
        (in-memory, process-wide, until the server restarts)."""
        # Reject a preset whose credential/connection is missing, so the app is
        # never switched onto a model that would fail on the next request (the UI
        # already hides these, but guard the resolver too).
        chosen = {c.name: c for c in config.list_model_presets(kind)}.get(preset)
        if chosen is not None and not config.is_config_available(chosen):
            raise ValueError(
                f"{preset!r} is not available — connect its provider first."
            )
        config.set_model_override(kind, preset)
        return admin_models_type()

    @strawberry.mutation(permission_classes=[IsAdmin])
    def set_claude_effort(
        self, effort: str | None = None
    ) -> ClaudeSubscriptionStatusType | None:
        """Admin-only: set the effort level for Claude-subscription requests
        (in-memory, process-wide). Null/empty resets to the API default ("high").
        Not sent for Haiku models, which reject the parameter."""
        config.set_claude_effort(effort or None)
        return claude_status_type()

    @strawberry.mutation(permission_classes=[IsAdmin])
    def start_claude_login(self) -> ClaudeLoginStartType | None:
        """Admin-only: begin the in-browser Claude-subscription sign-in.

        Returns the claude.ai authorize URL to open; the admin approves there,
        copies the one-time code, and pastes it into finishClaudeLogin."""
        if claude_oauth.is_signed_in():
            return ClaudeLoginStartType(signed_in=True)
        return ClaudeLoginStartType(signed_in=False, **claude_oauth.start_login())

    @strawberry.mutation(permission_classes=[IsAdmin])
    def finish_claude_login(self, code: str) -> ClaudeLoginResultType | None:
        """Admin-only: exchange the pasted ``code#state`` for subscription tokens.

        OAuth failures are returned in ``error`` (not raised), like login()."""
        try:
            claude_oauth.finish_login(code)
        except claude_oauth.ClaudeOAuthError as exc:
            return ClaudeLoginResultType(signed_in=False, detail="", error=str(exc))
        status = claude_status_type()
        return ClaudeLoginResultType(signed_in=status.signed_in, detail=status.detail)

    @strawberry.mutation(permission_classes=[IsAdmin])
    def disconnect_claude_subscription(self) -> ClaudeSubscriptionStatusType | None:
        """Admin-only: forget the stored subscription tokens.

        Any model kind currently pointed at the subscription drops its override
        so it falls back to the env/default instead of a now-unavailable model."""
        claude_oauth.logout()
        config.clear_overrides_for_provider("claude_subscription")
        return claude_status_type()

    @strawberry.mutation(permission_classes=[IsAdmin])
    def solve_problem(
        self, problem: str, grade_level: str | None = None
    ) -> SolutionType | None:
        """Admin-only: produce a worked solution with the **solver** model.

        A separate, deliberate solving path (teacher tooling) — like revealAnswer
        it sits off the answer-blind generation path and never feeds the student
        hint flow. Runs on get_solver_config(), not the generation model."""
        solution = build_solution(problem, grade_level)
        return SolutionType(
            solution_text=solution.solution_text,
            final_answer=solution.final_answer,
            meta=meta_from_dict(solution.meta),
        )


schema = strawberry.Schema(query=Query, mutation=Mutation)
