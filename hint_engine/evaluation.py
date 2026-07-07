from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from hint_engine.models import EvalCase, Hint

if TYPE_CHECKING:
    from hint_engine.judge import JudgeResult

# 4 sentences × ~60 chars each with some headroom; matches "2–4 sentences" in system prompt.
MAX_HINT_CHARS = 600

BANNED_PHRASES = [
    "the answer is",
    "the correct answer",
    "the solution is",
]

_ANSWER_PREFIX = re.compile(r"^x\s*=\s*", re.IGNORECASE)
_FRACTION_IN_ANSWER = re.compile(r"\d+/\d+")

# Map Unicode superscript digits to ASCII so "2⁵" and a typed "2^5" compare equal.
_SUPERSCRIPT_TO_ASCII = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
_SUPERSCRIPT_RUN = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+")

# A bare number preceded by one of these words is a positional reference ("step 7",
# "part 3", "question 2"), not the answer being leaked — so we don't flag it.
_POSITIONAL_PREFIX = re.compile(
    r"(?:step|steps|part|parts|question|questions|section|problem|problems|"
    r"example|line|number|no\.?|#)\s*$",
    re.IGNORECASE,
)


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass
class EvalReport:
    case: EvalCase
    hint: Hint
    checks: list[CheckResult]
    judge: JudgeResult | None = None
    model_answer_disagreement: bool | None = None

    @property
    def deterministic_passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def passed(self) -> bool:
        det_passed = self.deterministic_passed
        if self.judge is None:
            return det_passed
        return det_passed and self.judge.passed

    def flag_disagreement(self) -> bool:
        """True when model self-report diverges from the deterministic text-leak check."""
        text_check = _find_check(self.checks, "does_not_reveal_answer")
        if text_check is None:
            return False
        text_leaked = not text_check.passed
        return self.hint.reveals_answer != text_leaked

    def to_dict(self) -> dict:
        """Serialize to the locked report envelope (CI gate + human summary + judge slot)."""
        det_passed = self.deterministic_passed
        checks_payload = [
            {"name": c.name, "passed": c.passed, "detail": c.detail}
            for c in self.checks
        ]
        failed = [c for c in self.checks if not c.passed]
        if self.passed:
            summary = "PASS — all gates passed."
        elif not det_passed:
            summary = "FAIL — " + "; ".join(
                f"{c.name}: {c.detail}" for c in failed
            )
        elif self.judge is not None and not self.judge.passed:
            judge_failed = [r for r in self.judge.rubric if not r.passed]
            summary = "FAIL — judge: " + "; ".join(
                f"{r.name}: {r.detail}" for r in judge_failed
            )
        else:
            summary = "FAIL — unknown."

        judge_payload = None
        if self.judge is not None:
            judge_payload = {
                "passed": self.judge.passed,
                "score": self.judge.score,
                "checks": [
                    {"name": r.name, "passed": r.passed, "detail": r.detail}
                    for r in self.judge.rubric
                ],
                "meta": dict(self.judge.meta),
            }

        return {
            "passed": self.passed,
            "case_id": self.case.case_id,
            "problem": self.case.problem,
            "hint_text": self.hint.hint_text,
            "reveals_answer": self.hint.reveals_answer,
            "meta": dict(self.hint.meta),
            "flag_disagreement": self.flag_disagreement(),
            "model_answer_disagreement": self.model_answer_disagreement,
            "deterministic": {"passed": det_passed, "checks": checks_payload},
            "judge": judge_payload,
            "summary": summary,
        }


def _find_check(checks: list[CheckResult], name: str) -> CheckResult | None:
    for check in checks:
        if check.name == name:
            return check
    return None


def _normalize_superscripts(text: str) -> str:
    """Rewrite superscript exponent runs to caret form: "2⁵" -> "2^5", "2¹⁰" -> "2^10"."""
    return _SUPERSCRIPT_RUN.sub(
        lambda m: "^" + m.group(0).translate(_SUPERSCRIPT_TO_ASCII), text
    )


def _normalize_text(text: str) -> str:
    return _normalize_superscripts(text.lower().strip())


def _extract_answer_value(correct_answer: str) -> str:
    normalized = _normalize_text(correct_answer)
    return _ANSWER_PREFIX.sub("", normalized).strip()


_COMMON_SMALL_NUMBERS = frozenset(str(n) for n in range(1, 6))


def _answer_leak_checks(answer_value: str) -> list[tuple[str, str]]:
    """Return ordered (check_label, needle) substring pairs for leakage detection.

    Pure-digit answers (except tiny 1–5) are handled separately by `_numeric_leak`,
    which is word-boundary aware; everything else uses substring + fraction literals.
    """
    if not answer_value:
        return []

    checks: list[tuple[str, str]] = [("normalized_substring", answer_value)]

    fraction = _FRACTION_IN_ANSWER.search(answer_value)
    if fraction:
        checks.append(("fraction_literal", fraction.group(0)))

    return checks


def _numeric_leak(hint_normalized: str, value: str) -> bool:
    """True if the bare number `value` appears as a genuine leak in the hint.

    Uses word boundaries (so "7" does not match inside "17") and ignores positional
    references like "step 7" / "part 7" — a mention of the answer number is only a leak
    when it is not introduced by a positional word.
    """
    for match in re.finditer(rf"\b{re.escape(value)}\b", hint_normalized):
        preceding = hint_normalized[: match.start()]
        if not _POSITIONAL_PREFIX.search(preceding):
            return True
    return False


def check_does_not_reveal_answer(case: EvalCase, hint: Hint) -> CheckResult:
    """Fail if the correct answer (or guarded numeric/fraction literals) appears in hint_text.

    Pure-digit answers are matched on word boundaries and positional mentions ("step 7"
    when the answer is 7) are ignored — a meaningful reduction of the old false positives.
    Very common small numbers (1–5) still fall back to substring matching (too ambiguous
    to word-boundary reliably). Semantic paraphrases ("you'll end up with seven") remain
    out of scope — handled by the LLM-judge.
    """
    name = "does_not_reveal_answer"
    answer_value = _extract_answer_value(case.correct_answer)
    if not answer_value:
        return CheckResult(
            name=name,
            passed=True,
            detail="No extractable answer value to compare.",
        )

    hint_normalized = _normalize_text(hint.hint_text)

    if re.fullmatch(r"\d+", answer_value) and answer_value not in _COMMON_SMALL_NUMBERS:
        if _numeric_leak(hint_normalized, answer_value):
            return CheckResult(
                name=name,
                passed=False,
                detail=(
                    f"Hint text states the answer number {answer_value!r} outside a "
                    f"positional phrase (i.e. not 'step {answer_value}')."
                ),
            )
        return CheckResult(
            name=name,
            passed=True,
            detail=(
                f"Answer number {answer_value!r} not found in hint text "
                f"(positional mentions like 'step {answer_value}' ignored)."
            ),
        )

    for label, needle in _answer_leak_checks(answer_value):
        if needle in hint_normalized:
            return CheckResult(
                name=name,
                passed=False,
                detail=(
                    f"Hint text contains leaked value {needle!r} "
                    f"(via {label}, from {case.correct_answer!r})."
                ),
            )

    return CheckResult(
        name=name,
        passed=True,
        detail=f"Correct answer value {answer_value!r} not found in hint text.",
    )


def check_reveals_answer_flag(case: EvalCase, hint: Hint) -> CheckResult:
    """Fail if the hint's reveals_answer self-report flag is True."""
    name = "reveals_answer_flag"
    if hint.reveals_answer:
        return CheckResult(
            name=name,
            passed=False,
            detail="Hint reports reveals_answer=True.",
        )
    return CheckResult(
        name=name,
        passed=True,
        detail="Hint reports reveals_answer=False.",
    )


def check_non_empty(case: EvalCase, hint: Hint) -> CheckResult:
    """Fail if hint_text is empty after stripping."""
    name = "non_empty"
    if not hint.hint_text.strip():
        return CheckResult(
            name=name,
            passed=False,
            detail="Hint text is empty.",
        )
    return CheckResult(
        name=name,
        passed=True,
        detail="Hint text is non-empty.",
    )


def check_within_max_length(case: EvalCase, hint: Hint) -> CheckResult:
    """Fail if hint_text exceeds MAX_HINT_CHARS."""
    name = "within_max_length"
    length = len(hint.hint_text)
    if length > MAX_HINT_CHARS:
        return CheckResult(
            name=name,
            passed=False,
            detail=f"Hint length {length} exceeds max {MAX_HINT_CHARS}.",
        )
    return CheckResult(
        name=name,
        passed=True,
        detail=f"Hint length {length} is within max {MAX_HINT_CHARS}.",
    )


def check_no_banned_phrases(case: EvalCase, hint: Hint) -> CheckResult:
    """Fail if hint_text contains any banned answer-revealing phrase."""
    name = "no_banned_phrases"
    hint_normalized = _normalize_text(hint.hint_text)
    for phrase in BANNED_PHRASES:
        if phrase in hint_normalized:
            return CheckResult(
                name=name,
                passed=False,
                detail=f"Hint contains banned phrase {phrase!r}.",
            )
    return CheckResult(
        name=name,
        passed=True,
        detail="No banned phrases found.",
    )


_DETERMINISTIC_CHECKS: list[tuple[str, Callable[[EvalCase, Hint], CheckResult]]] = [
    ("does_not_reveal_answer", check_does_not_reveal_answer),
    ("reveals_answer_flag", check_reveals_answer_flag),
    ("non_empty", check_non_empty),
    ("within_max_length", check_within_max_length),
    ("no_banned_phrases", check_no_banned_phrases),
]


def run_deterministic_checks(case: EvalCase, hint: Hint) -> EvalReport:
    """Run the deterministic gates and return a combined report.

    A case may opt out of specific checks via ``expectations["skip_checks"]`` (a list of
    check names) — e.g. a free-form explanation case can skip ``within_max_length``.
    Safety gates (``does_not_reveal_answer``) should not be skipped; the mechanism is
    generic but exists for length/format leniency. Default: every check runs.
    """
    skip = set(case.expectations.get("skip_checks") or [])
    checks = [
        check(case, hint) for name, check in _DETERMINISTIC_CHECKS if name not in skip
    ]
    return EvalReport(case=case, hint=hint, checks=checks)
