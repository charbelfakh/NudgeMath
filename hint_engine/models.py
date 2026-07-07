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
