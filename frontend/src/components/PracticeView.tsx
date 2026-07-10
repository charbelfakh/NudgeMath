import { useState } from "react";
import { useLazyQuery, useMutation, useQuery } from "@apollo/client/react";
import {
  CurriculumDocument,
  GenerateProblemDocument,
  RevealAnswerDocument,
} from "../generated/graphql";
import { HintView } from "./HintView";
import { MathText } from "./MathText";
import { SolveProblem } from "./SolveProblem";

const GRADES = ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"];

/** Admin-only: reveal the server-side stored answer for the current problem. */
function RevealAnswer({ problemId }: { problemId: string }) {
  const [reveal, { data, loading }] = useLazyQuery(RevealAnswerDocument);
  const result = data?.revealAnswer;

  return (
    <div className="mt-4 border-t border-slate-100 pt-3">
      {!result ? (
        <button
          type="button"
          onClick={() => reveal({ variables: { problemId } })}
          disabled={loading}
          className="rounded-lg bg-amber-100 px-3 py-2 text-sm font-medium text-amber-900 hover:bg-amber-200 disabled:opacity-50"
        >
          {loading ? "Revealing…" : "Reveal answer (admin)"}
        </button>
      ) : result.found ? (
        <p className="text-sm text-slate-700">
          <span className="font-medium">Correct answer:</span>{" "}
          <MathText>{result.correctAnswer ?? ""}</MathText>
        </p>
      ) : (
        <p className="text-sm text-slate-500">
          No stored answer for this problem (it may have expired).
        </p>
      )}
    </div>
  );
}

export function PracticeView({ isAdmin = false }: { isAdmin?: boolean }) {
  const [grade, setGrade] = useState("7");
  const [topic, setTopic] = useState(""); // "" = auto (default topic for the band)
  const [difficulty, setDifficulty] = useState("medium");
  const [generateProblem, { data, loading, error }] = useMutation(
    GenerateProblemDocument,
  );

  // Server returns only this grade band's topics — no band logic on the client.
  const { data: curriculumData } = useQuery(CurriculumDocument, {
    variables: { gradeLevel: grade },
  });
  const topics = curriculumData?.curriculum ?? [];
  const difficulties = topics.find((t) => t.topic === topic)?.difficulties ?? [
    "easy",
    "medium",
    "hard",
  ];

  const problem = data?.generateProblem;
  const genError = problem?.meta.error;

  function onGradeChange(next: string) {
    setGrade(next);
    setTopic(""); // topics are band-specific; reset to auto on grade change
  }

  async function onGenerate() {
    await generateProblem({
      variables: {
        gradeLevel: grade,
        topic: topic || null,
        difficulty,
        mode: "auto",
      },
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Practice mode</h2>
        <p className="mt-1 text-sm text-slate-600">
          Generate a grade-appropriate problem, then solve it with answer-blind
          hints. Template problems have exact answers; harder topics are authored by
          the model. The tutor never sees the answer — only you (via gating).
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <label className="space-y-1">
          <span className="block text-sm font-medium text-slate-700">Grade</span>
          <select
            aria-label="Grade"
            value={grade}
            onChange={(e) => onGradeChange(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            {GRADES.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="block text-sm font-medium text-slate-700">Topic</span>
          <select
            aria-label="Topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Auto</option>
            {topics.map((t) => (
              <option key={t.topic} value={t.topic}>
                {t.topic.replace(/_/g, " ")}
                {t.template ? " (exact)" : " (model)"}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="block text-sm font-medium text-slate-700">
            Difficulty
          </span>
          <select
            aria-label="Difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            {difficulties.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={onGenerate}
          disabled={loading}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Generating…" : "Generate problem"}
        </button>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
        >
          Request failed: {error.message}
        </div>
      )}

      {genError && (
        <div
          role="alert"
          className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          Generation error: {genError}
        </div>
      )}

      {problem && problem.problem && !genError && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {problem.topic} · grade {problem.gradeLevel} · {problem.difficulty} ·{" "}
              {problem.source === "template"
                ? "exact answer"
                : "model-authored"}
            </p>
            <p className="mt-2 text-lg text-slate-900">
              <MathText>{problem.problem}</MathText>
            </p>
            {isAdmin && (
              <>
                <RevealAnswer key={problem.problemId} problemId={problem.problemId} />
                <SolveProblem
                  key={`solve-${problem.problemId}`}
                  problem={problem.problem}
                  gradeLevel={problem.gradeLevel}
                />
              </>
            )}
          </div>

          {/* Reuse the multi-turn hint flow, seeded with this problem. The answer
              stays on the server — only the opaque problemId is passed, and the
              server gates correctness. */}
          <HintView
            key={problem.problemId}
            initialProblem={problem.problem}
            initialStudentAnswer=""
            problemId={problem.problemId}
            practiceMode
          />
        </div>
      )}
    </div>
  );
}
