import { DiffEditor } from "@monaco-editor/react";
import Modal from "../common/Modal.jsx";
import { toMonacoLanguage } from "../../utils/monacoLanguage.js";

/**
 * Shows the AI-suggested change against the current draft using Monaco's
 * real diff view (the same rendering VS Code uses) rather than a plain
 * side-by-side text dump. Nothing touches the editor's actual content
 * until the person explicitly clicks Accept — this is the "user must be
 * able to review changes before applying them" requirement from the
 * spec, not a shortcut version of it.
 */
export default function DiffReviewModal({ original, modified, language, title = "Review AI suggestion", onAccept, onReject }) {
  return (
    <Modal title={title} onClose={onReject}>
      <div className="space-y-3">
        <div className="flex gap-4 text-[11px] text-gray-500">
          <span><span className="inline-block h-2 w-2 rounded-sm bg-red-500/60 align-middle" /> removed</span>
          <span><span className="inline-block h-2 w-2 rounded-sm bg-emerald-500/60 align-middle" /> added</span>
        </div>
        <div className="h-96 overflow-hidden rounded-md border border-surface-700">
          <DiffEditor
            height="100%"
            theme="vs-dark"
            language={toMonacoLanguage(language)}
            original={original}
            modified={modified}
            options={{
              readOnly: true,
              renderSideBySide: true,
              minimap: { enabled: false },
              fontSize: 12,
              scrollBeyondLastLine: false,
            }}
          />
        </div>
        <div className="flex gap-3">
          <button
            onClick={onAccept}
            className="flex-1 rounded-md bg-accent-600 px-3 py-2 text-sm font-medium text-white hover:bg-accent-500"
          >
            Accept — apply to editor
          </button>
          <button
            onClick={onReject}
            className="flex-1 rounded-md border border-surface-700 px-3 py-2 text-sm hover:bg-surface-800"
          >
            Reject
          </button>
        </div>
      </div>
    </Modal>
  );
}
