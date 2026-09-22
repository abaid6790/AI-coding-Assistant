import { useRef, useState } from "react";
import Editor from "@monaco-editor/react";
import { toMonacoLanguage, supportsBuiltinFormat } from "../../utils/monacoLanguage.js";

const LANGUAGES = [
  "python", "javascript", "typescript", "java", "cpp", "c", "csharp",
  "php", "html", "css", "sql", "json", "markdown", "text",
];

// Backend support (server/services/execution/) — currently Python and
// JavaScript (Node). Kept as a small local constant rather than an API
// call since it changes rarely and the Run button needs it
// synchronously to decide whether to enable itself.
const RUNNABLE_LANGUAGES = new Set(["python", "javascript"]);

export default function CodeEditor({
  value,
  language,
  onChange,
  onLanguageChange,
  onSave,
  onClear,
  onSendSelection,
  onOpenAiActions,
  onRun,
  running,
}) {
  const editorRef = useRef(null);
  const [copied, setCopied] = useState(false);

  const handleMount = (editor, monaco) => {
    editorRef.current = editor;
    // Ctrl/Cmd+S saves instead of triggering the browser's save-page dialog.
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      onSave?.();
    });
    // Ctrl/Cmd+Enter runs the code — the standard shortcut in most
    // browser-based editors/notebooks for this exact action.
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      onRun?.();
    });
  };

  const handleFormat = () => {
    editorRef.current?.getAction("editor.action.formatDocument")?.run();
  };

  const handleSendSelection = () => {
    const editor = editorRef.current;
    if (!editor) return;
    const selection = editor.getSelection();
    const text = selection ? editor.getModel().getValueInRange(selection) : "";
    if (!text) {
      window.alert("Select some code first, then send it to chat.");
      return;
    }
    onSendSelection?.(text);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value || "");
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API can fail without HTTPS/permissions — fail silently,
      // the button just won't show the "Copied" confirmation.
    }
  };

  const handleClear = () => {
    if (!value || window.confirm("Clear all content in this file? You can still undo with Ctrl+Z before saving.")) {
      onClear?.();
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-surface-800 bg-surface-900 px-3 py-1.5">
        <select
          value={language || "text"}
          onChange={(e) => onLanguageChange?.(e.target.value)}
          className="rounded border border-surface-700 bg-surface-800 px-2 py-1 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-accent-500"
        >
          {LANGUAGES.map((lang) => (
            <option key={lang} value={lang}>
              {lang}
            </option>
          ))}
        </select>

        <div className="mx-1 h-4 w-px bg-surface-700" />

        <button
          onClick={handleFormat}
          disabled={!supportsBuiltinFormat(language)}
          title={
            supportsBuiltinFormat(language)
              ? "Format document"
              : "No built-in formatter for this language yet"
          }
          className="rounded px-2 py-1 text-xs text-gray-400 hover:bg-surface-800 hover:text-gray-200 disabled:cursor-not-allowed disabled:opacity-30"
        >
          Format
        </button>

        <button
          onClick={handleCopy}
          className="rounded px-2 py-1 text-xs text-gray-400 hover:bg-surface-800 hover:text-gray-200"
        >
          {copied ? "Copied!" : "Copy"}
        </button>

        <button
          onClick={handleClear}
          className="rounded px-2 py-1 text-xs text-gray-400 hover:bg-surface-800 hover:text-gray-200"
        >
          Clear
        </button>

        <div className="mx-1 h-4 w-px bg-surface-700" />

        <button
          onClick={handleSendSelection}
          className="rounded px-2 py-1 text-xs text-gray-400 hover:bg-surface-800 hover:text-gray-200"
          title="Send the selected code to the AI chat panel"
        >
          Ask about selection →
        </button>

        <button
          onClick={onOpenAiActions}
          className="rounded px-2 py-1 text-xs font-medium text-accent-400 hover:bg-surface-800"
          title="Explain, review, optimize, debug, generate tests, or generate docs for this code"
        >
          Analyze ✨
        </button>

        <span className="ml-auto text-[11px] text-gray-600">⌘/Ctrl+S to save</span>

        <button
          onClick={onRun}
          disabled={running || !RUNNABLE_LANGUAGES.has(language)}
          title={
            RUNNABLE_LANGUAGES.has(language)
              ? "Run this code (⌘/Ctrl+Enter)"
              : `Running ${language || "this language"} isn't supported yet — only Python for now`
          }
          className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {running ? (
            <>
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/40 border-t-white" />
              Running…
            </>
          ) : (
            <>▶ Run Code</>
          )}
        </button>
      </div>

      <div className="flex-1">
        <Editor
          height="100%"
          theme="vs-dark"
          language={toMonacoLanguage(language)}
          value={value}
          onChange={(v) => onChange?.(v ?? "")}
          onMount={handleMount}
          options={{
            fontSize: 13,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 2,
            wordWrap: "off",
            lineNumbers: "on",
          }}
        />
      </div>
    </div>
  );
}
