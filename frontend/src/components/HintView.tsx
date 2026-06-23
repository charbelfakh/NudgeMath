import { useState, type FormEvent } from "react";
import { useMutation } from "@apollo/client/react";
import { GenerateHintDocument } from "../generated/graphql";

export function HintView() {
  const [problem, setProblem] = useState("Solve for x: 2x - 5 = 9");
  const [studentAnswer, setStudentAnswer] = useState("x = 2");
  const [correctAnswer, setCorrectAnswer] = useState("");
  const [gradeLevel, setGradeLevel] = useState("");
  const [subject, setSubject] = useState("");

  const [generateHint, { data, loading, error }] = useMutation(
    GenerateHintDocument,
  );

  const hint = data?.generateHint;
  const metaError = hint?.meta.error;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    await generateHint({
      variables: {
        request: {
          problem,
          studentAnswer,
          correctAnswer: correctAnswer || null,
          gradeLevel: gradeLevel || null,
          subject: subject || null,
        },
      },
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Get a hint</h2>
        <p className="mt-1 text-sm text-slate-600">
          Hint generation is answer-blind. Optional correct answer is used only
          to skip hints when the student is already right (seed cases match
          automatically).
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700">Problem</span>
          <textarea
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            rows={3}
            value={problem}
            onChange={(e) => setProblem(e.target.value)}
            required
          />
        </label>
        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700">
            Student answer
          </span>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={studentAnswer}
            onChange={(e) => setStudentAnswer(e.target.value)}
            required
          />
        </label>
        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700">
            Correct answer (teacher only, optional)
          </span>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={correctAnswer}
            onChange={(e) => setCorrectAnswer(e.target.value)}
            placeholder="e.g. x = 7 — for custom problems not in the seed set"
          />
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-1">
            <span className="text-sm font-medium text-slate-700">
              Grade level (optional)
            </span>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={gradeLevel}
              onChange={(e) => setGradeLevel(e.target.value)}
            />
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-medium text-slate-700">
              Subject (optional)
            </span>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </label>
        </div>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Generating…" : "Generate hint"}
        </button>
      </form>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
        >
          Request failed: {error.message}
        </div>
      )}

      {hint && !hint.answerCorrect && (
        <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          {metaError && (
            <div
              role="alert"
              className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
            >
              Generation error: {metaError}
            </div>
          )}
          <div>
            <h3 className="font-medium text-slate-900">Hint</h3>
            <p className="mt-2 text-slate-700">{hint.hintText || "—"}</p>
          </div>
          <p className="text-sm text-slate-600">
            Model self-report — reveals answer:{" "}
            <span className="font-medium">
              {hint.revealsAnswer ? "yes" : "no"}
            </span>
          </p>
          {hint.meta.model && (
            <p className="text-xs text-slate-500">Model: {hint.meta.model}</p>
          )}
        </div>
      )}

      {hint?.answerCorrect && (
        <div
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"
        >
          Your answer looks correct — no hint needed.
        </div>
      )}
    </div>
  );
}
