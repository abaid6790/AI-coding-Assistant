import { useState } from "react";
import { api, ApiError } from "../../services/api.js";
import Modal from "../common/Modal.jsx";
import ChatMessageContent from "../chat/ChatMessageContent.jsx";
import { ScoreBar, FindingsList } from "../analysis/CodeAnalysisDisplay.jsx";
import { inputClass, primaryButtonClass } from "../auth/AuthShell.jsx";

const TABS = [
  { id: "explain", label: "Explain" },
  { id: "review", label: "Review" },
  { id: "optimize", label: "Optimize" },
  { id: "debug", label: "Debug" },
  { id: "tests", label: "Tests" },
  { id: "documentation", label: "Docs" },
  { id: "generate", label: "Generate" },
];

export default function AiActionsModal({ file, code, onApplyCode, onCreateFile, onClose }) {
  const [tab, setTab] = useState("explain");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState({}); // keyed by tab, so switching tabs doesn't lose results

  // Per-tab input state
  const [description, setDescription] = useState("");
  const [genLanguage, setGenLanguage] = useState(file?.language || "python");
  const [errorMessage, setErrorMessage] = useState("");
  const [stackTrace, setStackTrace] = useState("");
  const [framework, setFramework] = useState("pytest");
  const [docType, setDocType] = useState("docstring");

  const result = results[tab];

  const setResult = (data) => setResults((prev) => ({ ...prev, [tab]: data }));

  const run = async (fn) => {
    setLoading(true);
    setError("");
    try {
      const data = await fn();
      setResult(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const baseSource = file ? { file_id: file.id, code, language: file.language } : { code };

  const handleExplain = () => run(() => api.explainCode(baseSource));
  const handleReview = () => run(() => api.reviewCode(baseSource));
  const handleOptimize = () => run(() => api.optimizeCode(baseSource));
  const handleDebug = () =>
    run(() => api.debugCode({ ...baseSource, error_message: errorMessage, stack_trace: stackTrace }));
  const handleTests = () => run(() => api.generateTestsForCode({ ...baseSource, framework }));
  const handleDocumentation = () => run(() => api.generateDocumentation({ ...baseSource, doc_type: docType }));
  const handleGenerate = () => run(() => api.generateCode({ description, language: genLanguage }));

  return (
    <Modal title="AI Actions" onClose={onClose}>
      <div className="mb-4 flex flex-wrap gap-1 border-b border-surface-800 pb-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded px-2.5 py-1 text-xs ${
              tab === t.id ? "bg-accent-600 text-white" : "text-gray-400 hover:bg-surface-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1 text-sm">
        {error && <p className="text-xs text-red-400">{error}</p>}

        {tab === "explain" && (
          <>
            {!result && (
              <button onClick={handleExplain} disabled={loading} className={primaryButtonClass}>
                {loading ? "Explaining…" : `Explain ${file ? file.filename : "this code"}`}
              </button>
            )}
            {result && <ChatMessageContent content={result.explanation} />}
          </>
        )}

        {tab === "review" && (
          <>
            {!result && (
              <button onClick={handleReview} disabled={loading} className={primaryButtonClass}>
                {loading ? "Reviewing…" : "Run code review"}
              </button>
            )}
            {result && (
              <div className="space-y-4">
                {Object.keys(result.scores || {}).length > 0 && (
                  <div className="grid grid-cols-2 gap-3 rounded-md border border-surface-700 p-3">
                    <ScoreBar label="Quality" value={result.scores.quality} />
                    <ScoreBar label="Security" value={result.scores.security} />
                    <ScoreBar label="Performance" value={result.scores.performance} />
                    <ScoreBar label="Maintainability" value={result.scores.maintainability} />
                  </div>
                )}
                {result.complexity && (
                  <p className="text-xs text-gray-400"><b className="text-gray-300">Complexity:</b> {result.complexity}</p>
                )}
                <p className="text-[11px] text-gray-500">AI-assisted estimate, not an authoritative security certification.</p>
                <FindingsList findings={result.findings} />
              </div>
            )}
          </>
        )}

        {tab === "optimize" && (
          <>
            {!result && (
              <button onClick={handleOptimize} disabled={loading} className={primaryButtonClass}>
                {loading ? "Optimizing…" : "Suggest optimizations"}
              </button>
            )}
            {result && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <p className="mb-1 text-[11px] text-gray-500">Original</p>
                    <pre className="max-h-48 overflow-auto rounded-md bg-surface-950 p-2 font-mono text-xs text-gray-300">{result.original_code}</pre>
                  </div>
                  <div>
                    <p className="mb-1 text-[11px] text-gray-500">Suggested</p>
                    <pre className="max-h-48 overflow-auto rounded-md bg-surface-950 p-2 font-mono text-xs text-emerald-300">{result.optimized_code}</pre>
                  </div>
                </div>
                <p className="text-xs text-gray-400">{result.explanation}</p>
                {file && result.optimized_code && (
                  <button
                    onClick={() => onApplyCode?.(result.optimized_code)}
                    className="rounded-md border border-accent-500 px-3 py-1.5 text-xs text-accent-400 hover:bg-accent-500/10"
                  >
                    Apply to editor
                  </button>
                )}
              </div>
            )}
          </>
        )}

        {tab === "debug" && (
          <div className="space-y-2">
            <textarea
              placeholder="Error message"
              className={`${inputClass} text-xs`}
              rows={2}
              value={errorMessage}
              onChange={(e) => setErrorMessage(e.target.value)}
            />
            <textarea
              placeholder="Stack trace (optional)"
              className={`${inputClass} text-xs`}
              rows={3}
              value={stackTrace}
              onChange={(e) => setStackTrace(e.target.value)}
            />
            <button onClick={handleDebug} disabled={loading} className={primaryButtonClass}>
              {loading ? "Diagnosing…" : "Diagnose"}
            </button>
            {result && (
              <div className="space-y-2 rounded-md border border-surface-700 p-3">
                <p className="text-[11px] font-medium uppercase tracking-wide text-amber-400">
                  Suggestion, not a guaranteed fix
                </p>
                {result.likely_cause && <p className="text-xs"><b>Likely cause:</b> {result.likely_cause}</p>}
                {result.suggested_fix && <p className="text-xs"><b>Suggested fix:</b> {result.suggested_fix}</p>}
                {result.corrected_code && (
                  <pre className="overflow-auto rounded-md bg-surface-950 p-2 font-mono text-xs text-emerald-300">{result.corrected_code}</pre>
                )}
                {result.explanation && <ChatMessageContent content={result.explanation} />}
                {file && result.corrected_code && (
                  <button
                    onClick={() => onApplyCode?.(result.corrected_code)}
                    className="rounded-md border border-accent-500 px-3 py-1.5 text-xs text-accent-400 hover:bg-accent-500/10"
                  >
                    Apply to editor
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {tab === "tests" && (
          <div className="space-y-2">
            <select className={`${inputClass} text-xs`} value={framework} onChange={(e) => setFramework(e.target.value)}>
              {["pytest", "unittest", "jest", "mocha", "junit"].map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
            <button onClick={handleTests} disabled={loading} className={primaryButtonClass}>
              {loading ? "Generating…" : "Generate tests"}
            </button>
            {result && (
              <div className="space-y-2">
                <pre className="max-h-56 overflow-auto rounded-md bg-surface-950 p-2 font-mono text-xs text-gray-200">{result.generated_code}</pre>
                {file && (
                  <button
                    onClick={() => onCreateFile?.(`test_${file.filename}`, result.generated_code, file.language)}
                    className="rounded-md border border-accent-500 px-3 py-1.5 text-xs text-accent-400 hover:bg-accent-500/10"
                  >
                    Save as new file
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {tab === "documentation" && (
          <div className="space-y-2">
            <select className={`${inputClass} text-xs`} value={docType} onChange={(e) => setDocType(e.target.value)}>
              <option value="docstring">Docstrings</option>
              <option value="comments">Inline comments</option>
              <option value="readme">README section</option>
              <option value="api_docs">API docs</option>
            </select>
            <button onClick={handleDocumentation} disabled={loading} className={primaryButtonClass}>
              {loading ? "Generating…" : "Generate documentation"}
            </button>
            {result && <ChatMessageContent content={result.content} />}
          </div>
        )}

        {tab === "generate" && (
          <div className="space-y-2">
            <textarea
              placeholder="Describe the code you want, e.g. 'a Flask endpoint that validates an email and returns 400 if invalid'"
              className={`${inputClass} text-xs`}
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <select className={`${inputClass} text-xs`} value={genLanguage} onChange={(e) => setGenLanguage(e.target.value)}>
              {["python", "javascript", "typescript", "java", "cpp", "sql", "html", "css"].map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
            <button onClick={handleGenerate} disabled={loading || !description.trim()} className={primaryButtonClass}>
              {loading ? "Generating…" : "Generate code"}
            </button>
            {result && (
              <div className="space-y-2">
                <pre className="max-h-56 overflow-auto rounded-md bg-surface-950 p-2 font-mono text-xs text-gray-200">{result.code}</pre>
                <p className="text-xs text-gray-400">{result.explanation}</p>
                {file && (
                  <button
                    onClick={() => onApplyCode?.(result.code)}
                    className="rounded-md border border-accent-500 px-3 py-1.5 text-xs text-accent-400 hover:bg-accent-500/10"
                  >
                    Insert into editor
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}
