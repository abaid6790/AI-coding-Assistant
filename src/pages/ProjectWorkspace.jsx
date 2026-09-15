import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../services/api.js";
import { useToast } from "../context/ToastContext.jsx";
import Modal from "../components/common/Modal.jsx";
import ProjectExplorer from "../components/code/ProjectExplorer.jsx";
import CodeEditor from "../components/code/CodeEditor.jsx";
import ChatPanel from "../components/chat/ChatPanel.jsx";
import AiActionsModal from "../components/code/AiActionsModal.jsx";
import DiffReviewModal from "../components/code/DiffReviewModal.jsx";
import AnalysisDashboardModal from "../components/analysis/AnalysisDashboardModal.jsx";
import { buildFileTree, languageIcon } from "../utils/fileTree.js";
import EmptyState from "../components/common/EmptyState.jsx";
import Spinner from "../components/common/Spinner.jsx";
import { inputClass, primaryButtonClass } from "../components/auth/AuthShell.jsx";

const LANGUAGES = [
  "python", "javascript", "typescript", "java", "cpp", "c", "csharp",
  "php", "html", "css", "sql", "json", "markdown", "text",
];

export default function ProjectWorkspace() {
  const { projectId } = useParams();
  const toast = useToast();

  const [project, setProject] = useState(null);
  const [files, setFiles] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [activeFile, setActiveFile] = useState(null);
  const [draftContent, setDraftContent] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  const [showNewFile, setShowNewFile] = useState(false);
  const [newFilename, setNewFilename] = useState("");
  const [newFolder, setNewFolder] = useState("");
  const [newLanguage, setNewLanguage] = useState("python");
  const [createError, setCreateError] = useState("");

  const [renamingFolder, setRenamingFolder] = useState(null);
  const [renameFolderValue, setRenameFolderValue] = useState("");

  const [deletingFile, setDeletingFile] = useState(null);
  const [pendingSelection, setPendingSelection] = useState(null);
  const [showAiActions, setShowAiActions] = useState(false);
  const [diffProposal, setDiffProposal] = useState(null);
  const [showAnalysisDashboard, setShowAnalysisDashboard] = useState(false);

  const load = async (searchTerm = "") => {
    setLoading(true);
    setError("");
    try {
      const [projectData, filesData] = await Promise.all([
        api.getProject(projectId),
        api.listFiles(projectId, searchTerm),
      ]);
      setProject(projectData.project);
      setFiles(filesData.files);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load project.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useEffect(() => {
    const timeout = setTimeout(() => load(search), 300);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const tree = useMemo(() => buildFileTree(files), [files]);

  const openFile = async (fileSummary) => {
    if (dirty && !window.confirm("Discard unsaved changes?")) return;
    try {
      const data = await api.getFile(projectId, fileSummary.id);
      setActiveFile(data.file);
      setDraftContent(data.file.content);
      setDirty(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not open file.");
    }
  };

  const handleSave = async () => {
    if (!activeFile) return;
    setSaving(true);
    try {
      const data = await api.updateFile(projectId, activeFile.id, { content: draftContent });
      setActiveFile(data.file);
      setDirty(false);
      setFiles((prev) => prev.map((f) => (f.id === data.file.id ? { ...f, ...data.file } : f)));
      toast.success(`Saved ${data.file.filename}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save file.");
    } finally {
      setSaving(false);
    }
  };

  const handleCreateFile = async (e) => {
    e.preventDefault();
    setCreateError("");
    try {
      const data = await api.createFile(projectId, {
        filename: newFilename,
        folder_path: newFolder,
        language: newLanguage,
        content: "",
      });
      setShowNewFile(false);
      setNewFilename("");
      setNewFolder("");
      await load(search);
      setActiveFile(data.file);
      setDraftContent(data.file.content);
      toast.success(`Created ${data.file.filename}`);
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : "Could not create file.");
    }
  };

  const handleRenameFolder = async (oldPath) => {
    setRenamingFolder(oldPath);
    setRenameFolderValue(oldPath);
  };

  const submitRenameFolder = async (e) => {
    e.preventDefault();
    try {
      const data = await api.renameFolder(projectId, renamingFolder, renameFolderValue);
      setRenamingFolder(null);
      toast.success(`Moved ${data.moved} file${data.moved === 1 ? "" : "s"}`);
      await load(search);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not rename folder.");
    }
  };

  const handleLanguageChange = async (newLanguage) => {
    if (!activeFile) return;
    try {
      const data = await api.updateFile(projectId, activeFile.id, { language: newLanguage });
      setActiveFile(data.file);
      setFiles((prev) => prev.map((f) => (f.id === data.file.id ? { ...f, ...data.file } : f)));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not change language.");
    }
  };

  const handleCreateFileFromAi = async (filename, content, language) => {
    try {
      const data = await api.createFile(projectId, { filename, content, language, folder_path: activeFile?.folder_path || "" });
      await load(search);
      setActiveFile(data.file);
      setDraftContent(data.file.content);
      setShowAiActions(false);
      toast.success(`Created ${data.file.filename}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save the generated file.");
    }
  };

  const handleDeleteFile = async () => {
    if (!deletingFile) return;
    try {
      const deletedName = deletingFile.filename;
      await api.deleteFile(projectId, deletingFile.id);
      if (activeFile?.id === deletingFile.id) {
        setActiveFile(null);
        setDraftContent("");
      }
      setDeletingFile(null);
      await load(search);
      toast.success(`Deleted ${deletedName}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete file.");
    }
  };

  if (loading && !project) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner label="Loading project…" size="lg" />
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-surface-950 text-gray-100">
      <header className="flex items-center justify-between border-b border-surface-700 bg-surface-900 px-4 py-2.5">
        <div className="flex items-center gap-2 text-sm">
          <Link to="/dashboard" className="text-gray-500 hover:text-gray-300">
            ← Dashboard
          </Link>
          <span className="text-gray-600">/</span>
          <span className="font-medium">{project?.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAnalysisDashboard(true)}
            className="rounded-md border border-surface-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-surface-800"
          >
            📊 Code Analysis
          </button>
          {activeFile && (
            <button
              onClick={handleSave}
              disabled={!dirty || saving}
              className="rounded-md bg-accent-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {saving ? "Saving…" : dirty ? "Save" : "Saved"}
            </button>
          )}
        </div>
      </header>

      {error && <div className="border-b border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-300">{error}</div>}

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar / Project Explorer */}
        <aside className="flex w-64 flex-col border-r border-surface-700 bg-surface-900">
          <div className="border-b border-surface-800 p-3">
            <input
              className={`${inputClass} text-xs`}
              placeholder="Search files…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            <ProjectExplorer
              tree={tree}
              activeFileId={activeFile?.id}
              onSelectFile={openFile}
              onRenameFolder={handleRenameFolder}
            />
          </div>
          <div className="border-t border-surface-800 p-2">
            <button
              onClick={() => setShowNewFile(true)}
              className="w-full rounded-md border border-surface-700 py-1.5 text-xs text-gray-300 hover:bg-surface-800"
            >
              + New file
            </button>
          </div>
        </aside>

        {/* Main content: Monaco-based editor (Phase 5) */}
        <main className="flex flex-1 flex-col overflow-hidden">
          {activeFile ? (
            <>
              <div className="flex items-center justify-between border-b border-surface-800 px-4 py-2 text-xs text-gray-400">
                <span>
                  {languageIcon(activeFile.language)} {activeFile.folder_path ? `${activeFile.folder_path}/` : ""}
                  {activeFile.filename}
                </span>
                <button
                  onClick={() => setDeletingFile(activeFile)}
                  className="text-gray-500 hover:text-red-400"
                >
                  Delete file
                </button>
              </div>
              <div className="flex-1 overflow-hidden">
                <CodeEditor
                  value={draftContent}
                  language={activeFile.language}
                  onChange={(v) => {
                    setDraftContent(v);
                    setDirty(true);
                  }}
                  onLanguageChange={handleLanguageChange}
                  onSave={handleSave}
                  onClear={() => {
                    setDraftContent("");
                    setDirty(true);
                  }}
                  onSendSelection={(text) => setPendingSelection(text)}
                  onOpenAiActions={() => setShowAiActions(true)}
                />
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center p-6">
              <EmptyState
                icon="📄"
                title="No file open"
                subtitle="Select a file from the explorer, or create a new one to get started."
                action={
                  <button
                    onClick={() => setShowNewFile(true)}
                    className="rounded-md border border-surface-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-surface-800"
                  >
                    + New file
                  </button>
                }
              />
            </div>
          )}
        </main>

        {/* AI Chat panel (Phase 7) */}
        <div className="w-80 flex-shrink-0">
          <ChatPanel
            projectId={projectId}
            activeFile={activeFile}
            pendingSelection={pendingSelection}
            onConsumeSelection={() => setPendingSelection(null)}
          />
        </div>
      </div>

      {showNewFile && (
        <Modal title="New file" onClose={() => setShowNewFile(false)}>
          {createError && <p className="mb-3 text-sm text-red-400">{createError}</p>}
          <form onSubmit={handleCreateFile} className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-400">Filename</label>
              <input
                autoFocus
                required
                placeholder="main.py"
                className={inputClass}
                value={newFilename}
                onChange={(e) => setNewFilename(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-400">Folder (optional)</label>
              <input
                placeholder="src/utils"
                className={inputClass}
                value={newFolder}
                onChange={(e) => setNewFolder(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-400">Language</label>
              <select
                className={inputClass}
                value={newLanguage}
                onChange={(e) => setNewLanguage(e.target.value)}
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang} value={lang}>
                    {lang}
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" className={primaryButtonClass}>
              Create file
            </button>
          </form>
        </Modal>
      )}

      {renamingFolder !== null && (
        <Modal title="Rename folder" onClose={() => setRenamingFolder(null)}>
          <form onSubmit={submitRenameFolder} className="space-y-4">
            <p className="text-xs text-gray-500">Renaming moves every file inside this folder.</p>
            <input
              autoFocus
              required
              className={inputClass}
              value={renameFolderValue}
              onChange={(e) => setRenameFolderValue(e.target.value)}
            />
            <button type="submit" className={primaryButtonClass}>
              Rename
            </button>
          </form>
        </Modal>
      )}

      {showAiActions && activeFile && (
        <AiActionsModal
          file={activeFile}
          code={draftContent}
          onApplyCode={(newCode) => {
            setDiffProposal(newCode);
            setShowAiActions(false);
          }}
          onCreateFile={handleCreateFileFromAi}
          onClose={() => setShowAiActions(false)}
        />
      )}

      {diffProposal !== null && (
        <DiffReviewModal
          original={draftContent}
          modified={diffProposal}
          language={activeFile?.language}
          onAccept={() => {
            setDraftContent(diffProposal);
            setDirty(true);
            setDiffProposal(null);
            toast.info("Applied — remember to Save");
          }}
          onReject={() => setDiffProposal(null)}
        />
      )}

      {showAnalysisDashboard && (
        <AnalysisDashboardModal projectId={projectId} onClose={() => setShowAnalysisDashboard(false)} />
      )}

      {deletingFile && (
        <Modal title="Delete file" onClose={() => setDeletingFile(null)}>
          <p className="mb-4 text-sm text-gray-300">
            Delete <span className="font-medium">{deletingFile.filename}</span>? This can't be undone.
          </p>
          <div className="flex gap-3">
            <button
              onClick={handleDeleteFile}
              className="flex-1 rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-500"
            >
              Delete
            </button>
            <button
              onClick={() => setDeletingFile(null)}
              className="flex-1 rounded-md border border-surface-700 px-3 py-2 text-sm hover:bg-surface-800"
            >
              Cancel
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
