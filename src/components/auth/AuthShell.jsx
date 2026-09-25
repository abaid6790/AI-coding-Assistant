export function AuthShell({ title, subtitle, children }) {
  return (
    <div className="auth-shell flex min-h-screen items-center justify-center px-4 py-8">
      <div className="auth-card w-full max-w-sm p-8">
        <div className="mb-6 flex items-center gap-3">
          <div className="auth-mark">AI</div>
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-accent-400">Developer Studio</div>
            <div className="text-xs text-gray-500">AI Coding Assistant</div>
          </div>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-gray-100">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-gray-400">{subtitle}</p>}
        <div className="mt-6">{children}</div>
      </div>
    </div>
  );
}

export function FieldError({ message }) {
  if (!message) return null;
  return <p className="mt-1 text-xs text-red-400">{message}</p>;
}

export function Banner({ kind = "error", children }) {
  if (!children) return null;
  const styles =
    kind === "error"
      ? "border-red-500/30 bg-red-500/10 text-red-300"
      : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
  return <div className={`mb-4 rounded-md border px-3 py-2 text-sm ${styles}`}>{children}</div>;
}

export const inputClass =
  "w-full rounded-md border border-surface-700 bg-surface-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500";

export const primaryButtonClass =
  "w-full rounded-md bg-accent-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-accent-500 disabled:cursor-not-allowed disabled:opacity-50";
