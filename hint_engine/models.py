from dataclasses import dataclass, field
from typing import Literal

TurnRole = Literal["student", "tutor"]


@dataclass
class ConversationTurn:
    """One prior message in a multi-turn hint exchange.

    Only ever holds student attempts and prior tutor hints — never the correct
    answer — so the conversation history stays answer-blind by construction.
    """

    role: TurnRole
    text: str


@dataclass
class HintRequest:
    """Input to the hint generator."""

    problem: str
    student_answer: str
    grade_level: str | None = None
    subject: str | None = None
    history: list[ConversationTurn] = field(default_factory=list)


@dataclass
class Hint:
    """Output from the hint generator."""

    hint_text: str
    reveals_answer: bool
    meta: dict = field(default_factory=dict)


@dataclass
class Solution:
    """A worked solution produced by the admin-only solver path.

    Deliberately separate from ``Hint``: this is teacher-side tooling (verify a
    model-authored problem, answer a photo problem with no stored answer). It is
    produced by ``solve.solve_problem`` behind admin auth and never feeds the
    answer-blind student hint flow.
    """

    solution_text: str
    final_answer: str = ""
    meta: dict = field(default_factory=dict)


@dataclass
class TranscriptionResult:
    """Text read off an image of a math problem.

    Answer-blind by construction: holds only the problem statement and, if visible,
    the student's own attempt as written on the page — never a correct answer. Feeds
    an ordinary ``HintRequest``; the vision step is transcription, not solving.
    """

    problem: str
    student_answer: str = ""
    meta: dict = field(default_factory=dict)


@dataclass
class GeneratedProblem:
    """A freshly generated practice problem.

    Holds the ``correct_answer`` because the generator knows it — but that answer is
    for teacher-side gating and eval only. It must never be passed into
    ``generate_hint()``; the hint path reads only ``problem`` (and the student's
    attempt), preserving the answer-blind boundary. ``source`` is "template"
    (deterministic, exact answer) or "llm" (model-authored, ``verified=False``).
    """

    problem: str
    correct_answer: str
    grade_level: str
    topic: str
    difficulty: str
    source: str
    verified: bool = False
    meta: dict = field(default_factory=dict)


@dataclass
class EvalCase:
    """One evaluation test case with rubric expectations."""

    problem: str
    student_answer: str
    correct_answer: str
    expectations: dict = field(default_factory=dict)
    case_id: str | None = None


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
