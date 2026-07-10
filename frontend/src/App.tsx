import { useState } from "react";
import { HintView } from "./components/HintView";
import { PracticeView } from "./components/PracticeView";
import { EvalView } from "./components/EvalView";
import { AdminLogin } from "./components/AdminLogin";
import { AdminPanel } from "./components/AdminPanel";
import { useAuth } from "./auth/AuthContext";

type Tab = "hint" | "practice" | "eval";

function AdminControls() {
  const { isAdmin, session, logout } = useAuth();
  const [showLogin, setShowLogin] = useState(false);

  if (isAdmin) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-sm text-slate-600">
          Admin: <span className="font-medium text-slate-900">{session?.username}</span>
        </span>
        <button
          type="button"
          onClick={logout}
          className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
        >
          Log out
        </button>
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setShowLogin((v) => !v)}
        className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
      >
        Admin login
      </button>
      {showLogin && (
        <div className="absolute right-0 z-10 mt-2">
          <AdminLogin onDone={() => setShowLogin(false)} />
        </div>
      )}
    </div>
  );
}

// `eval` is admin-only: evaluateCase is teacher/portfolio tooling and the
// costliest mutation on the server (withJudge fires a second LLM call), so it
// is gated by IsAdmin server-side. Hiding the tab keeps the UI honest.
const TABS: { id: Tab; label: string; adminOnly?: boolean }[] = [
  { id: "hint", label: "Hint" },
  { id: "practice", label: "Practice" },
  { id: "eval", label: "Eval", adminOnly: true },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("hint");
  const { isAdmin } = useAuth();

  const visibleTabs = TABS.filter((t) => isAdmin || !t.adminOnly);
  // An admin viewing Eval who signs out must not be left on a blank tab.
  const activeTab = visibleTabs.some((t) => t.id === tab) ? tab : "hint";

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
          <div className="flex items-center gap-4">
            <nav className="flex gap-2">
              {visibleTabs.map(({ id, label }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setTab(id)}
                  className={`rounded-lg px-3 py-2 text-sm font-medium ${
                    activeTab === id
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-100 text-slate-700"
                  }`}
                >
                  {label}
                </button>
              ))}
            </nav>
            <AdminControls />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 px-4 py-8">
        {isAdmin && <AdminPanel />}
        {activeTab === "hint" && <HintView isAdmin={isAdmin} />}
        {activeTab === "practice" && <PracticeView isAdmin={isAdmin} />}
        {activeTab === "eval" && isAdmin && <EvalView />}
      </main>
    </div>
  );
}
