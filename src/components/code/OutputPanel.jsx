import Spinner from "../common/Spinner.jsx";

/**
 * status: "running" | "success" | "error"
 * A failed run (non-zero exit, timeout, or truncated output) is still
 * a completed request — the distinction the spec cares about is
 * success vs. error, not request-succeeded vs. request-failed. Timeout
 * and truncation get their own explicit message rather than being
 * folded into a generic "error" line, per the spec's requirement that
 * timeout/failure states be clearly distinguished from an ordinary
 * runtime error.
 */
export default function OutputPanel({
  status,
  stdout,
  stderr,
  exitCode,
  timedOut,
  truncated,
  onClose,
  onFixWithAI,
  fixingWithAi,
}) {
  const isRunning = status === "running";
  const isSuccess = status === "success";
  const isError = status === "error";

  const statusLine = timedOut
    ? "Process terminated — execution timed out."
    : truncated
    ? "Process terminated — output limit exceeded."
    : `Process finished with exit code ${exitCode ?? "—"}`;

  return (
    <div className="flex h-60 flex-shrink-0 flex-col border-t border-surface-700 bg-surface-950">
      <div className="flex items-center justify-between border-b border-surface-800 bg-surface-900 px-3 py-1.5">
        <span
          className={`text-xs font-semibold uppercase tracking-wide ${
            isRunning ? "text-gray-400" : isError ? "text-red-400" : "text-emerald-400"
          }`}
        >
          {isRunning ? "Running…" : isError ? "Error" : "Output"}
        </span>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-300" title="Close output panel">
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 font-mono text-xs">
        {isRunning ? (
          <Spinner label="Running…" />
        ) : (
          <>
            {stdout && <pre className="whitespace-pre-wrap text-gray-200">{stdout}</pre>}
            {isError && stderr && (
              <pre className="mt-2 whitespace-pre-wrap text-red-400">{stderr}</pre>
            )}
            {!stdout && !stderr && (
              <p className="text-gray-600">(no output)</p>
            )}

            <p className={`mt-3 ${isSuccess ? "text-emerald-500" : "text-red-500"}`}>{statusLine}</p>

            {isError && onFixWithAI && (
              <button
                onClick={onFixWithAI}
                disabled={fixingWithAi}
                className="mt-3 flex items-center gap-1.5 rounded-md border border-accent-500 px-3 py-1.5 text-xs font-medium text-accent-400 hover:bg-accent-500/10 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {fixingWithAi ? (
                  <>
                    <span className="h-3 w-3 animate-spin rounded-full border-2 border-accent-400/40 border-t-accent-400" />
                    Asking AI…
                  </>
                ) : (
                  <>✨ Fix with AI</>
                )}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
