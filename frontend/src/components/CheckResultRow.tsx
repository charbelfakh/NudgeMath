export type CheckResultData = {
  name: string;
  passed: boolean;
  detail: string;
};

type CheckResultRowProps = {
  check: CheckResultData;
};

export function CheckResultRow({ check }: CheckResultRowProps) {
  return (
    <li
      className={`flex items-start gap-3 rounded-lg border px-3 py-2 ${
        check.passed
          ? "border-emerald-200 bg-emerald-50"
          : "border-rose-200 bg-rose-50"
      }`}
    >
      <span
        className={`mt-0.5 text-lg font-bold ${
          check.passed ? "text-emerald-700" : "text-rose-700"
        }`}
        aria-hidden="true"
      >
        {check.passed ? "✓" : "✗"}
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-medium text-slate-900">{check.name}</p>
        <p className="text-sm text-slate-600">{check.detail}</p>
      </div>
    </li>
  );
}
