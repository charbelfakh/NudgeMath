from dataclasses import dataclass, field


@dataclass
class HintRequest:
    """Input to the hint generator."""

    problem: str
    student_answer: str
    grade_level: str | None = None
    subject: str | None = None


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
