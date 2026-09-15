/**
 * Turns a flat list of files (each with a folder_path like "src/utils")
 * into a nested tree: { folders: { name: <node> }, files: [file, ...] }.
 * There's no separate folder table (see server/api/projects.py),
 * so folders only exist here as long as at least one file references them.
 */
export function buildFileTree(files) {
  const root = { folders: {}, files: [] };

  for (const file of files) {
    const parts = (file.folder_path || "").split("/").filter(Boolean);
    let node = root;
    for (const part of parts) {
      if (!node.folders[part]) {
        node.folders[part] = { folders: {}, files: [] };
      }
      node = node.folders[part];
    }
    node.files.push(file);
  }

  return root;
}

export function languageIcon(language) {
  const map = {
    python: "🐍",
    javascript: "📜",
    typescript: "📘",
    java: "☕",
    cpp: "⚙️",
    c: "⚙️",
    html: "🌐",
    css: "🎨",
    sql: "🗄️",
    json: "🧾",
    markdown: "📝",
  };
  return map[language] || "📄";
}
