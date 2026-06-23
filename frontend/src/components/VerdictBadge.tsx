type VerdictBadgeProps = {
  passed: boolean;
  label?: string;
};

export function VerdictBadge({ passed, label }: VerdictBadgeProps) {
  const text = label ?? (passed ? "PASS" : "FAIL");
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-semibold ${
        passed
          ? "bg-emerald-100 text-emerald-800"
          : "bg-rose-100 text-rose-800"
      }`}
    >
      <span aria-hidden="true">{passed ? "✓" : "✗"}</span>
      {text}
    </span>
  );
}
