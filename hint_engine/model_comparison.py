"""Cross-model comparison harness — aggregation layer over EvalReport atoms."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field

from hint_engine.config import ModelConfig, get_comparison_judge_config, parse_model_list
from hint_engine.eval_cases import EVAL_CASES
from hint_engine.evaluation import EvalReport, run_deterministic_checks
from hint_engine.generate import generate_hint
from hint_engine.judge import judge_hint
from hint_engine.llm_client import LLMClient
from hint_engine.models import EvalCase, HintRequest
from hint_engine.run_eval import case_to_request


@dataclass
class ComparisonCell:
    deterministic_passed: bool
    judge_score: float | None
    judge_passed: bool | None
    self_judged: bool
    report: EvalReport


@dataclass
class ModelAggregate:
    deterministic_passed: int
    deterministic_total: int
    judge_passed: int | None
    judge_total: int | None
    judge_mean_score: float | None
    judge_parse_failures: int = 0


@dataclass
class ComparisonTable:
    """Rows = cases, columns = generation models. References EvalReports; does not reshape them."""

    model_names: list[str]
    case_ids: list[str]
    judge_name: str | None = None
    cells: dict[tuple[str, str], ComparisonCell] = field(default_factory=dict)
    aggregates: dict[str, ModelAggregate] = field(default_factory=dict)


def _judge_parse_failed(report: EvalReport) -> bool:
    """Derived in aggregation layer — EvalReport atom unchanged."""
    if report.judge is None:
        return False
    return bool(report.judge.meta.get("error"))


def _is_self_judged(report: EvalReport, judge_config: ModelConfig | None = None) -> bool:
    if report.judge is None:
        return False
    gen_model = report.hint.meta.get("model")
    if not gen_model:
        return False
    if judge_config is not None:
        return gen_model == judge_config.model
    judge_model = report.judge.meta.get("model")
    return bool(judge_model and gen_model == judge_model)


def run_case_for_model(
    case: EvalCase,
    gen_config: ModelConfig,
    *,
    gen_client: LLMClient | None = None,
    with_judge: bool = False,
    judge_config: ModelConfig | None = None,
    judge_client: LLMClient | None = None,
) -> EvalReport:
    hint = generate_hint(case_to_request(case), client=gen_client, config=gen_config)
    report = run_deterministic_checks(case, hint)
    if with_judge:
        report.judge = judge_hint(
            case,
            hint,
            client=judge_client,
            config=judge_config,
        )
    return report


def run_comparison(
    gen_configs: list[ModelConfig],
    *,
    with_judge: bool = False,
    judge_config: ModelConfig | None = None,
) -> list[EvalReport]:
    """Produce a flat list of EvalReports — one per (case, generation model)."""
    reports: list[EvalReport] = []
    for gen_config in gen_configs:
        for case in EVAL_CASES:
            reports.append(
                run_case_for_model(
                    case,
                    gen_config,
                    with_judge=with_judge,
                    judge_config=judge_config,
                )
            )
    return reports


def _model_name_from_report(report: EvalReport) -> str:
    return str(report.hint.meta.get("name") or report.hint.meta.get("model") or "unknown")


def build_comparison_table(
    reports: list[EvalReport],
    *,
    judge_config: ModelConfig | None = None,
) -> ComparisonTable:
    """Group flat EvalReports into a cases × models table."""
    model_names = sorted({_model_name_from_report(r) for r in reports}, key=str.lower)
    report_case_ids = {
        r.case.case_id or r.case.problem[:40] for r in reports
    }
    case_ids = [
        case.case_id or case.problem[:40]
        for case in EVAL_CASES
        if (case.case_id or case.problem[:40]) in report_case_ids
    ]

    judge_name = judge_config.name if judge_config else None
    if judge_name is None:
        for report in reports:
            if report.judge is not None:
                judge_name = str(
                    report.judge.meta.get("name")
                    or report.judge.meta.get("model")
                    or "unknown"
                )
                break

    cells: dict[tuple[str, str], ComparisonCell] = {}
    for report in reports:
        case_id = report.case.case_id or report.case.problem[:40]
        model_name = _model_name_from_report(report)
        judge_score = report.judge.score if report.judge is not None else None
        judge_passed = report.judge.passed if report.judge is not None else None
        cells[(case_id, model_name)] = ComparisonCell(
            deterministic_passed=report.deterministic_passed,
            judge_score=judge_score,
            judge_passed=judge_passed,
            self_judged=_is_self_judged(report, judge_config),
            report=report,
        )

    aggregates: dict[str, ModelAggregate] = {}
    for model_name in model_names:
        model_reports = [r for r in reports if _model_name_from_report(r) == model_name]
        det_passed = sum(1 for r in model_reports if r.deterministic_passed)
        judged = [r for r in model_reports if r.judge is not None]
        judge_passed_count = sum(1 for r in judged if r.judge and r.judge.passed)
        scores = [r.judge.score for r in judged if r.judge is not None]
        parse_failures = sum(1 for r in judged if _judge_parse_failed(r))
        aggregates[model_name] = ModelAggregate(
            deterministic_passed=det_passed,
            deterministic_total=len(model_reports),
            judge_passed=judge_passed_count if judged else None,
            judge_total=len(judged) if judged else None,
            judge_mean_score=(sum(scores) / len(scores)) if scores else None,
            judge_parse_failures=parse_failures,
        )

    return ComparisonTable(
        model_names=model_names,
        case_ids=case_ids,
        judge_name=judge_name,
        cells=cells,
        aggregates=aggregates,
    )


def format_comparison_table(table: ComparisonTable, *, with_judge: bool) -> str:
    """Render a readable cases × models grid."""
    header_models = table.model_names
    col_width = max(16, max((len(m) for m in header_models), default=16) + 2)
    lines: list[str] = []

    if with_judge and table.judge_name:
        lines.append(f"Judge held constant: {table.judge_name}")

    header = "case_id".ljust(28)
    for model in header_models:
        header += model.rjust(col_width)
    lines.append(header)
    lines.append("-" * len(header))

    has_self_judged = False
    for case_id in table.case_ids:
        row = case_id[:28].ljust(28)
        for model in header_models:
            cell = table.cells.get((case_id, model))
            if cell is None:
                text = "—"
            elif with_judge and cell.judge_score is not None:
                det = "PASS" if cell.deterministic_passed else "FAIL"
                jpass = "PASS" if cell.judge_passed else "FAIL"
                text = f"{det}/{jpass} {cell.judge_score:.2f}"
                if cell.self_judged:
                    text += "*"
                    has_self_judged = True
            else:
                text = "PASS" if cell.deterministic_passed else "FAIL"
            row += text.rjust(col_width)
        lines.append(row)

    lines.append("")
    lines.append("Aggregates per model:")
    for model in header_models:
        agg = table.aggregates[model]
        det_rate = agg.deterministic_passed / agg.deterministic_total
        line = (
            f"  {model}: det {agg.deterministic_passed}/{agg.deterministic_total} "
            f"({det_rate:.0%})"
        )
        if with_judge and agg.judge_total:
            jrate = agg.judge_passed / agg.judge_total if agg.judge_passed is not None else 0
            mean = agg.judge_mean_score if agg.judge_mean_score is not None else 0.0
            judge_ok = agg.judge_total - agg.judge_parse_failures
            ok_rate = judge_ok / agg.judge_total
            line += (
                f", judge {agg.judge_passed}/{agg.judge_total} ({jrate:.0%}), "
                f"mean score {mean:.2f}, "
                f"judge_ok {judge_ok}/{agg.judge_total} ({ok_rate:.0%}), "
                f"parse_fail {agg.judge_parse_failures}/{agg.judge_total}"
            )
        lines.append(line)

    if has_self_judged:
        lines.append("")
        lines.append("* self-judged — not comparable")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare generation models across seed cases.")
    parser.add_argument(
        "--models",
        default=None,
        help="Comma-separated preset names (e.g. llama3.2,sonnet-4.6). Default: current gen config.",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Run LLM judge (pinned neutral judge unless LLM_JUDGE_* set).",
    )
    args = parser.parse_args()

    gen_configs = parse_model_list(args.models)
    judge_config = get_comparison_judge_config() if args.judge else None
    reports = run_comparison(gen_configs, with_judge=args.judge, judge_config=judge_config)
    table = build_comparison_table(reports, judge_config=judge_config)
    print(format_comparison_table(table, with_judge=args.judge))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
