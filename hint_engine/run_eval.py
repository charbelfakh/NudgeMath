"""Run seed eval cases through LLM generation, deterministic gates, and optional judge."""

import argparse

from hint_engine.eval_cases import EVAL_CASES
from hint_engine.evaluation import EvalReport, run_deterministic_checks
from hint_engine.generate import generate_hint
from hint_engine.judge import judge_hint
from hint_engine.models import EvalCase, HintRequest


def case_to_request(case: EvalCase) -> HintRequest:
    return HintRequest(
        problem=case.problem,
        student_answer=case.student_answer,
        grade_level=case.expectations.get("grade_level"),
        subject=case.expectations.get("subject"),
    )


def run_case(case: EvalCase, *, with_judge: bool = False) -> EvalReport:
    request = case_to_request(case)
    hint = generate_hint(request)
    report = run_deterministic_checks(case, hint)
    if with_judge:
        report.judge = judge_hint(case, hint)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NudgeMath seed eval cases.")
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Also run LLM-judge scoring per case (slower, extra API cost).",
    )
    args = parser.parse_args()

    reports: list[EvalReport] = []
    for case in EVAL_CASES:
        report = run_case(case, with_judge=args.judge)
        reports.append(report)
        label = case.case_id or case.problem[:40]
        status = "PASS" if report.passed else "FAIL"
        line = f"[{status}] {label}: {report.to_dict()['summary']}"
        if args.judge and report.judge is not None:
            line += f" (judge score: {report.judge.score:.2f})"
        print(line)

    det_passed = sum(1 for r in reports if r.deterministic_passed)
    merged_passed = sum(1 for r in reports if r.passed)
    total = len(reports)
    print(f"\nDeterministic: {det_passed}/{total} passed")
    if args.judge:
        judge_passed = sum(1 for r in reports if r.judge is not None and r.judge.passed)
        print(f"Judge: {judge_passed}/{total} passed")
    print(f"Overall: {merged_passed}/{total} passed")
    return 0 if merged_passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
