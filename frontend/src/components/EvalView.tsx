import { useState } from "react";
import { useMutation, useQuery } from "@apollo/client/react";
import {
  EvaluateCaseDocument,
  HintsDocument,
} from "../generated/graphql";
import { EvalReportCard } from "./EvalReportCard";

export function EvalView() {
  const { data: hintsData, loading: hintsLoading } = useQuery(HintsDocument);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [withJudge, setWithJudge] = useState(false);

  const [evaluateCase, { data: evalData, loading: evalLoading, error }] =
    useMutation(EvaluateCaseDocument);

  const hints = hintsData?.hints ?? [];
  const report = evalData?.evaluateCase;

  async function runEval() {
    if (!selectedCaseId) return;
    await evaluateCase({
      variables: { caseId: selectedCaseId, withJudge },
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Eval harness</h2>
        <p className="mt-1 text-sm text-slate-600">
          Admin/portfolio view — answer-aware seed cases and full report.
        </p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {hintsLoading ? (
          <p className="text-sm text-slate-600">Loading seed cases…</p>
        ) : (
          <div className="space-y-4">
            <label className="block space-y-1">
              <span className="text-sm font-medium text-slate-700">
                Seed case
              </span>
              <select
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={selectedCaseId ?? ""}
                onChange={(e) => setSelectedCaseId(e.target.value || null)}
              >
                <option value="">Select a case…</option>
                {hints.map((hintCase) => (
                  <option key={hintCase.caseId} value={hintCase.caseId ?? ""}>
                    {hintCase.caseId} — {hintCase.problem.slice(0, 48)}
                  </option>
                ))}
              </select>
            </label>

            {selectedCaseId && (
              <div className="rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-700">
                {hints
                  .filter((c) => c.caseId === selectedCaseId)
                  .map((c) => (
                    <div key={c.caseId}>
                      <p>
                        <span className="font-medium">Student:</span>{" "}
                        {c.studentAnswer}
                      </p>
                      <p className="mt-1">
                        <span className="font-medium">Correct:</span>{" "}
                        {c.correctAnswer}
                      </p>
                    </div>
                  ))}
              </div>
            )}

            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={withJudge}
                onChange={(e) => setWithJudge(e.target.checked)}
              />
              Run LLM judge (withJudge)
            </label>

            <button
              type="button"
              onClick={runEval}
              disabled={!selectedCaseId || evalLoading}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {evalLoading ? "Running…" : "Run evaluation"}
            </button>
          </div>
        )}
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
        >
          Evaluation failed: {error.message}
        </div>
      )}

      {report && <EvalReportCard report={report} />}
    </div>
  );
}
