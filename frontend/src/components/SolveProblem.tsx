import { useMutation } from "@apollo/client/react";
import { SolveProblemDocument } from "../generated/graphql";
import { MathText } from "./MathText";

/**
 * Admin-only: generate a worked solution for the given problem with the
 * separate solver model. Server-gated (IsAdmin) — this control just surfaces
 * it. Re-clickable so the admin can re-solve after switching the Solver model.
 */
export function SolveProblem({
  problem,
  gradeLevel,
}: {
  problem: string;
  gradeLevel?: string | null;
}) {
  const [solve, { data, loading, error }] = useMutation(SolveProblemDocument);
  const solution = data?.solveProblem;
  const solveError = solution?.meta.error;

  return (
    <div className="mt-4 border-t border-slate-100 pt-3">
      <button
        type="button"
        onClick={() =>
          // Errors render via the hook's `error` state; catch the rejected
          // promise so the click doesn't leak an unhandled rejection.
          void solve({ variables: { problem, gradeLevel: gradeLevel ?? null } }).catch(
            () => {},
          )
        }
        disabled={loading || !problem.trim()}
        className="rounded-lg bg-sky-100 px-3 py-2 text-sm font-medium text-sky-900 hover:bg-sky-200 disabled:opacity-50"
      >
        {loading
          ? "Solving…"
          : solution
            ? "Re-generate solution (admin)"
            : "Generate solution (admin)"}
      </button>

      {error && (
        <p role="alert" className="mt-2 text-sm text-rose-700">
          Request failed: {error.message}
        </p>
      )}
      {solveError && (
        <p role="alert" className="mt-2 text-sm text-amber-800">
          Solver error: {solveError}
        </p>
      )}

      {solution && !solveError && (
        <div className="mt-3 space-y-2 rounded-lg border border-sky-100 bg-sky-50/60 p-3">
          <p className="whitespace-pre-line text-sm text-slate-800">
            <MathText>{solution.solutionText}</MathText>
          </p>
          {solution.finalAnswer && (
            <p className="text-sm text-slate-900">
              <span className="font-medium">Final answer:</span>{" "}
              <MathText>{solution.finalAnswer}</MathText>
            </p>
          )}
          <p className="text-xs text-slate-500">
            solver: {solution.meta.model ?? "?"} ({solution.meta.provider ?? "?"})
            {solution.meta.latencyMs != null && <> · {solution.meta.latencyMs} ms</>}
          </p>
        </div>
      )}
    </div>
  );
}
