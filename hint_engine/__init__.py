"""NudgeMath hint engine — pedagogical hint generation and evaluation."""

from hint_engine.evaluation import CheckResult, EvalReport, run_deterministic_checks
from hint_engine.generate import generate_hint
from hint_engine.judge import JudgeResult, judge_hint
from hint_engine.models import EvalCase, Hint, HintRequest

__all__ = [
    "CheckResult",
    "EvalCase",
    "EvalReport",
    "Hint",
    "HintRequest",
    "JudgeResult",
    "generate_hint",
    "judge_hint",
    "run_deterministic_checks",
]
