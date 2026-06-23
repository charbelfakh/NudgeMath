import { useState } from "react";
import { HintView } from "./components/HintView";
import { EvalView } from "./components/EvalView";

type Tab = "hint" | "eval";

export default function App() {
  const [tab, setTab] = useState<Tab>("hint");

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">NudgeMath</h1>
            <p className="text-sm text-slate-600">
              Typed hints &amp; evaluation harness
            </p>
          </div>
          <nav className="flex gap-2">
            <button
              type="button"
              onClick={() => setTab("hint")}
              className={`rounded-lg px-3 py-2 text-sm font-medium ${
                tab === "hint"
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-100 text-slate-700"
              }`}
            >
              Hint
            </button>
            <button
              type="button"
              onClick={() => setTab("eval")}
              className={`rounded-lg px-3 py-2 text-sm font-medium ${
                tab === "eval"
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-100 text-slate-700"
              }`}
            >
              Eval
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8">
        {tab === "hint" ? <HintView /> : <EvalView />}
      </main>
    </div>
  );
}
