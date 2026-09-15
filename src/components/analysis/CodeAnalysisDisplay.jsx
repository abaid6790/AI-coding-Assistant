export const SEVERITY_STYLES = {
  Critical: "bg-red-500/20 text-red-300 border-red-500/40",
  High: "bg-orange-500/20 text-orange-300 border-orange-500/40",
  Medium: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  Low: "bg-blue-500/20 text-blue-300 border-blue-500/40",
  Suggestion: "bg-gray-500/20 text-gray-300 border-gray-500/40",
};

export function ScoreBar({ label, value }) {
  if (value === null || value === undefined) return null;
  const color = value >= 80 ? "bg-emerald-500" : value >= 50 ? "bg-amber-500" : "bg-red-500";
  return (
    <div>
      <div className="flex justify-between text-[11px] text-gray-400">
        <span>{label}</span>
        <span>{value}/100</span>
      </div>
      <div className="mt-0.5 h-1.5 rounded-full bg-surface-800">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

export function FindingsList({ findings }) {
  if (!findings || findings.length === 0) {
    return <p className="text-xs text-gray-500">No issues found.</p>;
  }
  return (
    <div className="space-y-2">
      {findings.map((f, i) => (
        <div key={i} className={`rounded-md border px-3 py-2 ${SEVERITY_STYLES[f.severity] || SEVERITY_STYLES.Suggestion}`}>
          <div className="flex items-center justify-between text-xs font-medium">
            <span>{f.title}</span>
            <span className="rounded-full bg-black/20 px-2 py-0.5 text-[10px]">
              {f.severity}{f.line ? ` · line ${f.line}` : ""}
            </span>
          </div>
          <p className="mt-1 text-xs opacity-90">{f.description}</p>
        </div>
      ))}
    </div>
  );
}
