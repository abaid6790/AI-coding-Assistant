import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { api, ApiError } from "../services/api.js";
import Modal from "../components/common/Modal.jsx";
import AiProviderBadge from "../components/chat/AiProviderBadge.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import Spinner from "../components/common/Spinner.jsx";
import { inputClass, primaryButtonClass } from "../components/auth/AuthShell.jsx";

export default function Dashboard() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  const [renaming, setRenaming] = useState(null); // project being renamed
  const [renameValue, setRenameValue] = useState("");
  const [deleting, setDeleting] = useState(null); // project pending delete confirmation

  const loadProjects = async (searchTerm = "") => {
    setLoading(true);
    setError("");
    try {
      const data = await api.listProjects(searchTerm);
      setProjects(data.projects);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load projects.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => loadProjects(search), 300);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreateError("");
    setCreating(true);
    try {
      const data = await api.createProject({ name: newName, description: newDescription });
      setShowCreate(false);
      setNewName("");
      setNewDescription("");
      toast.success(`Created "${data.project.name}"`);
      navigate(`/projects/${data.project.id}`);
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : "Could not create project.");
    } finally {
      setCreating(false);
    }
  };

  const handleRename = async (e) => {
    e.preventDefault();
    if (!renaming) return;
    try {
      await api.updateProject(renaming.id, { name: renameValue });
      setRenaming(null);
      toast.success("Project renamed");
      loadProjects(search);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not rename project.");
    }
  };

  const handleDelete = async () => {
    if (!deleting) return;
    try {
      await api.deleteProject(deleting.id);
      setDeleting(null);
      toast.success(`Deleted "${deleting.name}"`);
      loadProjects(search);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete project.");
    }
  };

  return (
    <div className="min-h-screen bg-surface-950 text-gray-100">
      <header className="flex items-center justify-between border-b border-surface-700 bg-surface-900 px-6 py-4">
        <span className="font-semibold">AI Coding Assistant</span>
        <div className="flex items-center gap-4 text-sm text-gray-400">
          <AiProviderBadge />
          <span className="hidden text-xs text-gray-600 sm:inline">
            <kbd className="rounded border border-surface-700 px-1.5 py-0.5">⌘K</kbd> to search
          </span>
          <span>{user?.email}</span>
          <button
            onClick={logout}
            className="rounded-md border border-surface-700 px-3 py-1 hover:bg-surface-800"
          >
            Log out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl p-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-medium">
              Welcome{user?.display_name ? `, ${user.display_name}` : ""}.
            </h1>
            <p className="mt-1 text-sm text-gray-400">
              {projects.length} project{projects.length === 1 ? "" : "s"}
            </p>
          </div>
          <button onClick={() => setShowCreate(true)} className="rounded-md bg-accent-600 px-4 py-2 text-sm font-medium text-white hover:bg-accent-500">
            + New project
          </button>
        </div>

        <input
          className={`${inputClass} mb-6`}
          placeholder="Search projects…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

        {loading ? (
          <div className="flex justify-center py-10">
            <Spinner label="Loading projects…" />
          </div>
        ) : projects.length === 0 ? (
          <EmptyState
            icon={search ? "🔍" : "📁"}
            title={search ? "No projects match your search." : "No projects yet."}
            subtitle={search ? "Try a different search term." : "Create your first project to get started, or press ⌘K."}
            action={
              !search && (
                <button onClick={() => setShowCreate(true)} className={primaryButtonClass}>
                  + New project
                </button>
              )
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <div
                key={project.id}
                className="group relative rounded-lg border border-surface-700 bg-surface-900 p-4 transition hover:border-accent-500"
              >
                <Link to={`/projects/${project.id}`} className="block">
                  <h3 className="truncate font-medium text-gray-100">{project.name}</h3>
                  <p className="mt-1 line-clamp-2 text-xs text-gray-500">
                    {project.description || "No description."}
                  </p>
                </Link>
                <div className="mt-3 flex gap-3 text-xs text-gray-500">
                  <button
                    onClick={() => {
                      setRenaming(project);
                      setRenameValue(project.name);
                    }}
                    className="hover:text-accent-500"
                  >
                    Rename
                  </button>
                  <button onClick={() => setDeleting(project)} className="hover:text-red-400">
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {showCreate && (
        <Modal title="New project" onClose={() => setShowCreate(false)}>
          {createError && <p className="mb-3 text-sm text-red-400">{createError}</p>}
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-400">Name</label>
              <input
                autoFocus
                required
                className={inputClass}
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-400">Description (optional)</label>
              <textarea
                className={inputClass}
                rows={3}
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
              />
            </div>
            <button type="submit" disabled={creating} className={primaryButtonClass}>
              {creating ? "Creating…" : "Create project"}
            </button>
          </form>
        </Modal>
      )}

      {renaming && (
        <Modal title="Rename project" onClose={() => setRenaming(null)}>
          <form onSubmit={handleRename} className="space-y-4">
            <input
              autoFocus
              required
              className={inputClass}
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
            />
            <button type="submit" className={primaryButtonClass}>
              Save
            </button>
          </form>
        </Modal>
      )}

      {deleting && (
        <Modal title="Delete project" onClose={() => setDeleting(null)}>
          <p className="mb-4 text-sm text-gray-300">
            Delete <span className="font-medium">{deleting.name}</span>? This also deletes all of its
            files and conversations. This can't be undone.
          </p>
          <div className="flex gap-3">
            <button
              onClick={handleDelete}
              className="flex-1 rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-500"
            >
              Delete
            </button>
            <button
              onClick={() => setDeleting(null)}
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
