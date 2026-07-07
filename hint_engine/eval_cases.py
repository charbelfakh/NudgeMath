"""Seed evaluation cases.

The dataset lives in ``data/eval_cases.jsonl`` (one JSON object per line) so it can grow
without touching Python and be diffed/reviewed as data. ``EVAL_CASES`` is loaded once at
import time; the first entry (``algebra_sign_error``) is the canonical demo case.
"""

from __future__ import annotations

import json
from pathlib import Path

from hint_engine.models import EvalCase

DATA_PATH = Path(__file__).parent / "data" / "eval_cases.jsonl"


def load_eval_cases(path: Path = DATA_PATH) -> list[EvalCase]:
    """Parse the JSONL dataset into EvalCase objects, preserving file order."""
    cases: list[EvalCase] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{line_no}: invalid JSON — {exc}") from exc
        cases.append(
            EvalCase(
                problem=obj["problem"],
                student_answer=obj["student_answer"],
                correct_answer=obj["correct_answer"],
                expectations=obj.get("expectations", {}),
                case_id=obj.get("case_id"),
            )
        )
    return cases


EVAL_CASES: list[EvalCase] = load_eval_cases()
