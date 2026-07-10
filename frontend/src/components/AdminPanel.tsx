import { useState } from "react";
import { useMutation, useQuery } from "@apollo/client/react";
import {
  AdminModelsDocument,
  ClaudeSubscriptionDocument,
  DisconnectClaudeSubscriptionDocument,
  FinishClaudeLoginDocument,
  SetClaudeEffortDocument,
  SetModelDocument,
  StartClaudeLoginDocument,
} from "../generated/graphql";

// output_config.effort levels the API accepts ("" = API default, high).
// Effort is not sent for Haiku models — the API rejects it there.
const EFFORT_LEVELS = ["low", "medium", "high", "xhigh", "max"];

type Preset = { name: string; provider: string; model: string };

function ModelSelect({
  label,
  hint,
  value,
  presets,
  disabled,
  onChange,
}: {
  label: string;
  hint: string;
  value: string;
  presets: Preset[];
  disabled: boolean;
  onChange: (preset: string) => void;
}) {
  const names = presets.map((p) => p.name);
  const currentIsPreset = names.includes(value);
  return (
    <label className="space-y-1">
      <span className="block text-xs font-medium text-slate-600">
        {label} <span className="text-slate-400">· {hint}</span>
      </span>
      <select
        aria-label={label}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-50"
      >
        {!currentIsPreset && <option value={value}>{value} (current)</option>}
        {presets.map((p) => (
          <option key={p.name} value={p.name}>
            {p.name} ({p.provider})
          </option>
        ))}
      </select>
    </label>
  );
}

/**
 * Connect the user's Claude subscription (in-app PKCE OAuth, no API key). Once
 * signed in, `claude-subscription` becomes an available Generation model. The
 * credential is stored server-side and only known to this admin surface.
 */
function ClaudeConnectCard({ onConnectionChange }: { onConnectionChange: () => void }) {
  const { data, loading, refetch } = useQuery(ClaudeSubscriptionDocument);
  const [startLogin, { loading: starting }] = useMutation(StartClaudeLoginDocument);
  const [finishLogin, { loading: finishing }] = useMutation(FinishClaudeLoginDocument);
  const [disconnect, { loading: disconnecting }] = useMutation(
    DisconnectClaudeSubscriptionDocument,
  );
  const [setEffort, { loading: settingEffort }] = useMutation(
    SetClaudeEffortDocument,
  );

  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  const status = data?.claudeSubscription;
  const signedIn = !!status?.signedIn;

  async function refresh() {
    await refetch();
    onConnectionChange();
  }

  // Transport/GraphQL failures reject the mutation promise; without a catch the
  // click silently does nothing. Surface them in the same inline error slot.
  function failure(err: unknown): void {
    setError(err instanceof Error ? err.message : "Request failed.");
  }

  async function onConnect() {
    setError(null);
    try {
      const res = await startLogin();
      const payload = res.data?.startClaudeLogin;
      if (!payload) return;
      if (payload.signedIn) {
        await refresh();
        return;
      }
      if (payload.url) {
        setAuthUrl(payload.url);
        window.open(payload.url, "_blank", "noopener,noreferrer");
      }
    } catch (err) {
      failure(err);
    }
  }

  async function onFinish() {
    setError(null);
    try {
      const res = await finishLogin({ variables: { code } });
      const payload = res.data?.finishClaudeLogin;
      if (payload?.error) {
        setError(payload.error);
        return;
      }
      setAuthUrl(null);
      setCode("");
      await refresh();
    } catch (err) {
      failure(err);
    }
  }

  async function onDisconnect() {
    setError(null);
    try {
      await disconnect();
      setAuthUrl(null);
      setCode("");
      await refresh();
    } catch (err) {
      failure(err);
    }
  }

  async function onEffortChange(effort: string) {
    setError(null);
    try {
      await setEffort({ variables: { effort: effort || null } });
      await refetch();
    } catch (err) {
      failure(err);
    }
  }

  const busy = starting || finishing || disconnecting;

  return (
    <div className="mt-4 rounded-lg border border-indigo-200 bg-white/60 p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold text-indigo-800">
          Claude subscription
          <span
            className={`ml-2 rounded-full px-2 py-0.5 text-[10px] font-medium ${
              signedIn
                ? "bg-emerald-100 text-emerald-700"
                : "bg-slate-100 text-slate-500"
            }`}
          >
            {signedIn ? "Connected" : "Not connected"}
          </span>
        </p>
        {signedIn ? (
          <button
            type="button"
            onClick={onDisconnect}
            disabled={busy}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Disconnect
          </button>
        ) : (
          <button
            type="button"
            onClick={onConnect}
            disabled={busy}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Connect
          </button>
        )}
      </div>

      {!loading && status && (
        <p className="mt-2 text-xs text-slate-500">{status.detail}</p>
      )}

      {signedIn && (
        <label className="mt-3 flex items-center gap-2">
          <span className="text-xs font-medium text-slate-600">
            Effort <span className="text-slate-400">· thinking depth & token spend</span>
          </span>
          <select
            aria-label="Effort"
            value={status?.effort ?? ""}
            disabled={settingEffort}
            onChange={(e) => onEffortChange(e.target.value)}
            className="rounded-lg border border-slate-300 px-2 py-1 text-xs disabled:opacity-50"
          >
            <option value="">default (high)</option>
            {EFFORT_LEVELS.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
          <span className="text-[10px] text-slate-400">
            not applied to Haiku (unsupported)
          </span>
        </label>
      )}

      {authUrl && !signedIn && (
        <div className="mt-3 space-y-2">
          <p className="text-xs text-slate-600">
            Approve in the tab that opened (or{" "}
            <a
              href={authUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-600 underline"
            >
              open it here
            </a>
            ), then paste the code shown after approving:
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              aria-label="Authorization code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="code#state"
              className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
            />
            <button
              type="button"
              onClick={onFinish}
              disabled={busy || !code.trim()}
              className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              Finish
            </button>
          </div>
        </div>
      )}

      {error && (
        <p role="alert" className="mt-2 text-xs text-rose-700">
          {error}
        </p>
      )}
    </div>
  );
}

/** Admin-only bar: switch the vision and generation models process-wide. */
export function AdminPanel() {
  const { data, loading, error, refetch } = useQuery(AdminModelsDocument);
  const [setModel, { loading: switching }] = useMutation(SetModelDocument);
  const [switchError, setSwitchError] = useState<string | null>(null);
  const models = data?.adminModels;

  async function onChange(kind: "vision" | "generation" | "solver", preset: string) {
    setSwitchError(null);
    try {
      await setModel({ variables: { kind, preset } });
    } catch (err) {
      // e.g. the preset became unavailable since the list was fetched — the
      // resolver rejects it; show why instead of silently snapping back.
      setSwitchError(err instanceof Error ? err.message : "Model switch failed.");
    }
    await refetch();
  }

  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
        Admin · model controls
      </p>
      {error && (
        <p role="alert" className="mt-2 text-sm text-rose-700">
          Could not load models: {error.message}
        </p>
      )}
      {switchError && (
        <p role="alert" className="mt-2 text-sm text-rose-700">
          {switchError}
        </p>
      )}
      {loading || !models ? (
        <p className="mt-2 text-sm text-slate-600">Loading models…</p>
      ) : (
        <div className="mt-3 flex flex-wrap gap-6">
          <ModelSelect
            label="Vision"
            hint="photo → text"
            value={models.visionModel}
            presets={models.visionPresets}
            disabled={switching}
            onChange={(p) => onChange("vision", p)}
          />
          <ModelSelect
            label="Generation"
            hint="hints"
            value={models.generationModel}
            presets={models.generationPresets}
            disabled={switching}
            onChange={(p) => onChange("generation", p)}
          />
          <ModelSelect
            label="Solver"
            hint="solutions"
            value={models.solverModel}
            presets={models.solverPresets}
            disabled={switching}
            onChange={(p) => onChange("solver", p)}
          />
        </div>
      )}

      <ClaudeConnectCard onConnectionChange={() => refetch()} />

      <p className="mt-3 text-xs text-slate-500">
        Changes apply to everyone until the server restarts. Only models with a
        working connection are listed.
      </p>
    </div>
  );
}
