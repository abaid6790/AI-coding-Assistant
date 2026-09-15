import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../services/api.js";
import { useAuth } from "../../context/AuthContext.jsx";

/**
 * Mounted once at the app root (see App.jsx) so Ctrl/Cmd+K works from
 * anywhere the user is logged in — the "command/search interface" the
 * original spec calls for. Scoped for now to project search/jump/create;
 * per-project actions (jump to file, open chat) live in the workspace
 * itself since this component sits above the router and doesn't have
 * access to a specific project's local state.
 */
export default function CommandPalette() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      const isK = e.key === "k" || e.key === "K";
      if ((e.metaKey || e.ctrlKey) && isK) {
        e.preventDefault();
        setOpen((o) => !o);
      } else if (e.key === "Escape" && open) {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  useEffect(() => {
    if (!open || !user) return;
    setQuery("");
    setActiveIndex(0);
    setLoading(true);
    api
      .listProjects()
      .then((data) => setProjects(data.projects))
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));
    setTimeout(() => inputRef.current?.focus(), 0);
  }, [open, user]);

  if (!open || !user) return null;

  const matches = projects.filter((p) => p.name.toLowerCase().includes(query.toLowerCase()));
  const showCreate = query.trim().length > 0;

  const items = [
    ...matches.map((p) => ({ type: "project", project: p })),
    ...(showCreate ? [{ type: "create", name: query.trim() }] : []),
  ];

  const runItem = async (item) => {
    if (!item) return;
    if (item.type === "project") {
      navigate(`/projects/${item.project.id}`);
      setOpen(false);
    } else if (item.type === "create") {
      try {
        const data = await api.createProject({ name: item.name });
        navigate(`/projects/${data.project.id}`);
        setOpen(false);
      } catch {
        // Swallow — the dashboard's own create-project flow already
        // surfaces validation errors; this is a convenience shortcut.
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      runItem(items[activeIndex]);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[200] flex items-start justify-center bg-black/60 pt-24"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-lg rounded-lg border border-surface-700 bg-surface-900 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActiveIndex(0);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Search projects, or type a name to create one…"
          className="w-full border-b border-surface-800 bg-transparent px-4 py-3 text-sm text-gray-100 placeholder-gray-500 outline-none"
        />
        <div className="max-h-80 overflow-y-auto p-1.5">
          {loading && <p className="px-3 py-2 text-xs text-gray-500">Loading…</p>}
          {!loading && items.length === 0 && (
            <p className="px-3 py-2 text-xs text-gray-500">No projects yet — type a name to create one.</p>
          )}
          {items.map((item, i) => (
            <button
              key={item.type === "project" ? item.project.id : "create"}
              onClick={() => runItem(item)}
              onMouseEnter={() => setActiveIndex(i)}
              className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm ${
                i === activeIndex ? "bg-accent-600/20 text-accent-300" : "text-gray-300"
              }`}
            >
              {item.type === "project" ? (
                <>
                  <span>📁</span>
                  <span className="truncate">{item.project.name}</span>
                </>
              ) : (
                <>
                  <span>+</span>
                  <span>Create project "{item.name}"</span>
                </>
              )}
            </button>
          ))}
        </div>
        <div className="border-t border-surface-800 px-3 py-1.5 text-[10px] text-gray-600">
          ↑↓ to navigate · Enter to select · Esc to close
        </div>
      </div>
    </div>
  );
}
