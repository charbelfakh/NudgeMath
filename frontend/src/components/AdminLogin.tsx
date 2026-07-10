import { useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";

/** Compact admin sign-in form shown from the header when signed out. */
export function AdminLogin({ onDone }: { onDone?: () => void }) {
  const { login, loggingIn } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const message = await login(username.trim(), password);
    if (message) {
      setError(message);
      return;
    }
    setPassword("");
    onDone?.();
  }

  return (
    <form
      onSubmit={onSubmit}
      className="w-72 space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-lg"
    >
      <p className="text-sm font-semibold text-slate-900">Admin sign in</p>
      <label className="block space-y-1">
        <span className="block text-xs font-medium text-slate-600">Username</span>
        <input
          aria-label="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="block space-y-1">
        <span className="block text-xs font-medium text-slate-600">Password</span>
        <div className="relative">
          <input
            aria-label="Password"
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 pr-14 text-sm"
          />
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            aria-pressed={showPassword}
            className="absolute inset-y-0 right-0 flex items-center px-3 text-xs font-medium text-slate-500 hover:text-slate-700"
          >
            {showPassword ? "Hide" : "Show"}
          </button>
        </div>
      </label>
      {error && (
        <p role="alert" className="text-xs text-rose-700">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={loggingIn || !username || !password}
        className="w-full rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {loggingIn ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
