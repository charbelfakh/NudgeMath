import {
  useState,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
} from "react";
import { useMutation } from "@apollo/client/react";
import {
  GenerateHintDocument,
  TranscribeProblemDocument,
} from "../generated/graphql";
import { MathText } from "./MathText";
import { SolveProblem } from "./SolveProblem";

type Turn = { role: "student" | "tutor"; text: string };

// Raster formats a vision model can read. Used for both the file-picker `accept`
// filter and drag-and-drop validation.
const ACCEPTED_IMAGE_TYPES = [
  "image/png",
  "image/jpeg",
  "image/gif",
  "image/webp",
  "image/bmp",
];
const ACCEPTED_LABEL = "PNG, JPEG, GIF, WebP, or BMP";

// Mirrors the server's MAX_IMAGE_CHARS (8M base64 chars ≈ 6 MB of bytes).
// Caught here so a huge file fails instantly instead of after a slow upload.
const MAX_IMAGE_BYTES = 6 * 1024 * 1024;

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

type HintViewProps = {
  initialProblem?: string;
  initialStudentAnswer?: string;
  initialCorrectAnswer?: string;
  // Practice mode: the image-upload / teacher-answer controls are hidden, and
  // correctness is gated server-side via problemId (the answer never reaches here).
  practiceMode?: boolean;
  problemId?: string;
  // Admin: shows the solver control for the current problem (server-gated too).
  isAdmin?: boolean;
};

export function HintView({
  initialProblem,
  initialStudentAnswer,
  initialCorrectAnswer,
  practiceMode = false,
  problemId,
  isAdmin = false,
}: HintViewProps = {}) {
  const [problem, setProblem] = useState(
    initialProblem ?? "Solve for x: 2x - 5 = 9",
  );
  const [studentAnswer, setStudentAnswer] = useState(
    initialStudentAnswer ?? "x = 2",
  );
  const [correctAnswer, setCorrectAnswer] = useState(initialCorrectAnswer ?? "");
  const [gradeLevel, setGradeLevel] = useState("");
  const [subject, setSubject] = useState("");
  const [history, setHistory] = useState<Turn[]>([]);

  const [generateHint, { data, loading, error }] = useMutation(
    GenerateHintDocument,
  );
  const [transcribeProblem, { loading: transcribing }] = useMutation(
    TranscribeProblemDocument,
  );
  const [transcribeError, setTranscribeError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  // Data URL of the uploaded/dropped image, shown so the user can check the
  // transcription against the original picture.
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  const hint = data?.generateHint;
  const metaError = hint?.meta.error;
  const isFollowUp = history.length > 0;

  function onProblemChange(value: string) {
    setProblem(value);
    // History and the teacher's correct answer are tied to one problem; editing
    // the problem starts a fresh thread and must not gate against a stale answer.
    if (history.length > 0) setHistory([]);
    if (correctAnswer) setCorrectAnswer("");
  }

  async function processImageFile(file: File | undefined) {
    if (!file) return;
    setTranscribeError(null);
    if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
      setTranscribeError(
        `Unsupported file type${file.type ? ` (${file.type})` : ""}. Use ${ACCEPTED_LABEL}.`,
      );
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      const mb = (file.size / (1024 * 1024)).toFixed(1);
      setTranscribeError(
        `That image is too large (${mb} MB). Use one under ${MAX_IMAGE_BYTES / (1024 * 1024)} MB.`,
      );
      return;
    }
    let dataUrl: string;
    try {
      dataUrl = await readFileAsDataUrl(file);
    } catch {
      setTranscribeError("Could not read that file.");
      return;
    }
    // Show the image as soon as it's readable — also on transcription failure,
    // so the user can see what the model was looking at.
    setImagePreview(dataUrl);
    const result = await transcribeProblem({ variables: { image: dataUrl } });
    const transcription = result.data?.transcribeProblem;
    if (!transcription || transcription.meta.error) {
      setTranscribeError(
        transcription?.meta.error ?? "Transcription failed — try another image.",
      );
      return;
    }
    if (!transcription.problem) {
      setTranscribeError("No problem text found in that image.");
      return;
    }
    // Transcription is answer-blind: it only fills the problem + the student's own
    // visible attempt, which the student can correct before asking for a hint.
    // A teacher answer typed for the previous problem must not gate this one.
    setProblem(transcription.problem);
    setStudentAnswer(transcription.studentAnswer || "");
    setCorrectAnswer("");
    setHistory([]);
  }

  function onImageSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow re-selecting the same file
    void processImageFile(file);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    void processImageFile(event.dataTransfer.files?.[0]);
  }

  function onDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    if (!isDragging) setIsDragging(true);
  }

  function onDragLeave(event: DragEvent<HTMLDivElement>) {
    // Ignore drag-leave bubbling from children still inside the drop zone.
    if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
    setIsDragging(false);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const attempt = studentAnswer;
    const result = await generateHint({
      variables: {
        request: {
          problem,
          studentAnswer: attempt,
          correctAnswer: correctAnswer || null,
          problemId: problemId ?? null,
          gradeLevel: gradeLevel || null,
          subject: subject || null,
          history:
            history.length > 0
              ? history.map((t) => ({ role: t.role, text: t.text }))
              : null,
        },
      },
    });
    const next = result.data?.generateHint;
    // Extend the thread only on a real hint — not "already correct", not a generation error.
    if (next && !next.answerCorrect && next.hintText && !next.meta.error) {
      setHistory((prev) => [
        ...prev,
        { role: "student", text: attempt },
        { role: "tutor", text: next.hintText },
      ]);
      setStudentAnswer("");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Get a hint</h2>
        <p className="mt-1 text-sm text-slate-600">
          Hint generation is answer-blind. Submit another attempt after a hint to
          build a multi-turn nudge — the tutor sees the prior exchange but never
          the correct answer. Optional correct answer is used only to skip hints
          when the student is already right (seed cases match automatically).
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        {!practiceMode && (
          <div
            data-testid="image-dropzone"
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            className={`space-y-1 rounded-lg border border-dashed p-4 transition-colors ${
              isDragging
                ? "border-indigo-500 bg-indigo-100"
                : "border-slate-300 bg-slate-50"
            }`}
          >
            <span className="text-sm font-medium text-slate-700">
              Stuck on a problem? Drag an image here, or upload a photo or screenshot
            </span>
            <input
              type="file"
              accept={ACCEPTED_IMAGE_TYPES.join(",")}
              onChange={onImageSelected}
              disabled={transcribing}
              aria-label="Upload a photo or screenshot of a problem"
              className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-indigo-700 hover:file:bg-indigo-100 disabled:opacity-50"
            />
            <span className="block text-xs text-slate-500">
              {ACCEPTED_LABEL}. We read the question off the image so you can check
              and edit it below — the tutor still never sees the correct answer.
            </span>
            {transcribing && (
              <p className="text-xs text-slate-500">Reading your image…</p>
            )}
            {transcribeError && (
              <div
                role="alert"
                className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900"
              >
                Couldn't read the image: {transcribeError}
              </div>
            )}
            {imagePreview && (
              <div className="space-y-1 pt-2">
                <img
                  src={imagePreview}
                  alt="Uploaded problem image"
                  className="max-h-48 max-w-full rounded-lg border border-slate-200 bg-white object-contain"
                />
                <button
                  type="button"
                  onClick={() => setImagePreview(null)}
                  className="text-xs font-medium text-slate-500 underline hover:text-slate-700"
                >
                  Remove image
                </button>
              </div>
            )}
          </div>
        )}

        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700">Problem</span>
          <textarea
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            rows={3}
            value={problem}
            onChange={(e) => onProblemChange(e.target.value)}
            required
          />
          {problem.trim() && (
            <span className="block text-xs text-slate-500">
              Preview: <MathText className="text-slate-700">{problem}</MathText>
            </span>
          )}
        </label>
        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700">
            {isFollowUp ? "Your next attempt" : "Student answer"}
          </span>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={studentAnswer}
            onChange={(e) => setStudentAnswer(e.target.value)}
            required
          />
        </label>
        {!practiceMode && (
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
        )}
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
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading
              ? "Generating…"
              : isFollowUp
                ? "Send next attempt"
                : "Generate hint"}
          </button>
          {isFollowUp && (
            <button
              type="button"
              onClick={() => setHistory([])}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Reset conversation
            </button>
          )}
        </div>
        {isAdmin && (
          <SolveProblem problem={problem} gradeLevel={gradeLevel || null} />
        )}
      </form>

      {history.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Conversation
          </h3>
          {history.map((turn, i) => (
            <div
              key={i}
              className={
                turn.role === "student"
                  ? "rounded-xl border border-slate-200 bg-slate-50 px-4 py-3"
                  : "rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3"
              }
            >
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {turn.role === "student" ? "Student attempt" : "Tutor hint"}
              </p>
              <p className="mt-1 text-sm text-slate-800">
                <MathText>{turn.text}</MathText>
              </p>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
        >
          Request failed: {error.message}
        </div>
      )}

      {hint &&
        !hint.answerCorrect &&
        (metaError ? (
          <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div
              role="alert"
              className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
            >
              Generation error: {metaError}
            </div>
            <p className="mt-2 text-slate-700">
              {hint.hintText ? <MathText>{hint.hintText}</MathText> : "—"}
            </p>
          </div>
        ) : (
          <div className="space-y-1 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
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
        ))}

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
