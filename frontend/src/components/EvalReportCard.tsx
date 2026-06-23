import { CheckResultRow } from "./CheckResultRow";
import { VerdictBadge } from "./VerdictBadge";
import type { EvaluateCaseMutation } from "../generated/graphql";

export type EvalReportData = NonNullable<
  EvaluateCaseMutation["evaluateCase"]
>;

type EvalReportCardProps = {
  report: EvalReportData;
};

export function EvalReportCard({ report }: EvalReportCardProps) {
  return (
    <article className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">
            {report.caseId ?? "Eval report"}
          </h3>
          <p className="mt-1 text-sm text-slate-600">{report.problem}</p>
        </div>
        <VerdictBadge passed={report.passed} label="Overall" />
      </header>

      <p className="rounded-lg bg-slate-100 px-4 py-3 text-sm text-slate-700">
        {report.summary}
      </p>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-slate-900">Deterministic gates</h4>
          <VerdictBadge passed={report.deterministic.passed} />
        </div>
        <ul className="space-y-2">
          {report.deterministic.checks.map((check) => (
            <CheckResultRow key={check.name} check={check} />
          ))}
        </ul>
      </section>

      {report.judge && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-slate-900">
              LLM judge{" "}
              <span className="text-sm font-normal text-slate-500">
                (score {(report.judge.score * 100).toFixed(0)}%)
              </span>
            </h4>
            <VerdictBadge passed={report.judge.passed} />
          </div>
          <ul className="space-y-2">
            {report.judge.checks.map((check) => (
              <CheckResultRow key={check.name} check={check} />
            ))}
          </ul>
        </section>
      )}

      <section className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-slate-200 px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Hint preview
          </p>
          <p className="mt-1 text-sm text-slate-800">{report.hintText}</p>
          <p className="mt-2 text-xs text-slate-500">
            Model self-report reveals answer:{" "}
            <span className="font-medium">
              {report.revealsAnswer ? "yes" : "no"}
            </span>
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 px-4 py-3 text-sm">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Advisory signals
          </p>
          <ul className="mt-2 space-y-1 text-slate-700">
            <li>
              Flag disagreement:{" "}
              <span className="font-medium">
                {report.flagDisagreement ? "yes" : "no"}
              </span>
            </li>
            <li>
              Model answer disagreement:{" "}
              <span className="font-medium">
                {report.modelAnswerDisagreement == null
                  ? "not computed"
                  : report.modelAnswerDisagreement
                    ? "yes"
                    : "no"}
              </span>
            </li>
          </ul>
        </div>
      </section>
    </article>
  );
}
