import { useState } from "react";
import { languageIcon } from "../../utils/fileTree.js";

function FolderNode({ name, node, path, activeFileId, onSelectFile, onRenameFolder, onDeleteFolderFiles }) {
  const [open, setOpen] = useState(true);
  const fullPath = path ? `${path}/${name}` : name;

  return (
    <div>
      <div className="group flex items-center justify-between rounded px-1 py-1 hover:bg-surface-800">
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex flex-1 items-center gap-1 truncate text-left text-sm text-gray-300"
        >
          <span className="text-gray-500">{open ? "▾" : "▸"}</span>
          <span className="truncate">📁 {name}</span>
        </button>
        <div className="hidden gap-2 pr-1 text-xs text-gray-500 group-hover:flex">
          <button onClick={() => onRenameFolder(fullPath)} className="hover:text-accent-500" title="Rename folder">
            ✎
          </button>
        </div>
      </div>
      {open && (
        <div className="ml-3 border-l border-surface-800 pl-2">
          <TreeLevel
            node={node}
            path={fullPath}
            activeFileId={activeFileId}
            onSelectFile={onSelectFile}
            onRenameFolder={onRenameFolder}
            onDeleteFolderFiles={onDeleteFolderFiles}
          />
        </div>
      )}
    </div>
  );
}

function TreeLevel({ node, path, activeFileId, onSelectFile, onRenameFolder }) {
  const folderNames = Object.keys(node.folders).sort();
  const files = [...node.files].sort((a, b) => a.filename.localeCompare(b.filename));

  return (
    <>
      {folderNames.map((name) => (
        <FolderNode
          key={name}
          name={name}
          node={node.folders[name]}
          path={path}
          activeFileId={activeFileId}
          onSelectFile={onSelectFile}
          onRenameFolder={onRenameFolder}
        />
      ))}
      {files.map((file) => (
        <button
          key={file.id}
          onClick={() => onSelectFile(file)}
          className={`flex w-full items-center gap-1.5 truncate rounded px-1 py-1 text-left text-sm ${
            activeFileId === file.id
              ? "bg-accent-600/20 text-accent-500"
              : "text-gray-400 hover:bg-surface-800 hover:text-gray-200"
          }`}
        >
          <span>{languageIcon(file.language)}</span>
          <span className="truncate">{file.filename}</span>
        </button>
      ))}
      {folderNames.length === 0 && files.length === 0 && (
        <p className="px-1 py-1 text-xs text-gray-600">Empty</p>
      )}
    </>
  );
}

export default function ProjectExplorer({ tree, activeFileId, onSelectFile, onRenameFolder }) {
  return (
    <div className="space-y-0.5">
      <TreeLevel node={tree} path="" activeFileId={activeFileId} onSelectFile={onSelectFile} onRenameFolder={onRenameFolder} />
    </div>
  );
}
