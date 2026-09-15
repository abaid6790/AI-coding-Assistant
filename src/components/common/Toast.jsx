export default function Toast({ toasts, onDismiss }) {
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className={`pointer-events-auto flex max-w-sm items-start gap-2 rounded-md border px-3 py-2 text-sm shadow-lg backdrop-blur-sm animate-[fadeIn_0.15s_ease-out] ${
            t.kind === "success"
              ? "border-emerald-500/40 bg-emerald-950/90 text-emerald-200"
              : t.kind === "error"
              ? "border-red-500/40 bg-red-950/90 text-red-200"
              : "border-surface-700 bg-surface-900/95 text-gray-200"
          }`}
        >
          <span className="flex-1">{t.message}</span>
          <button onClick={() => onDismiss(t.id)} className="text-current opacity-60 hover:opacity-100">
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
