import { useEffect, useState } from "react";
import { api } from "../api";
import { buildTree, type TreeNode } from "../lib/tree";

function Node({
  node,
  depth,
  selected,
  onSelect,
}: {
  node: TreeNode;
  depth: number;
  selected: string | null;
  onSelect: (p: string) => void;
}) {
  const pad = { paddingLeft: depth * 12 + 4 };
  if (node.isFile)
    return (
      <button
        style={pad}
        onClick={() => onSelect(node.path)}
        className={`block w-full truncate py-0.5 text-left text-sm hover:bg-slate-100 ${selected === node.path ? "bg-slate-200 font-medium" : ""}`}
      >
        {node.name}
      </button>
    );
  return (
    <div>
      <div style={pad} className="py-0.5 text-sm font-medium text-slate-600">
        📁 {node.name}
      </div>
      {node.children.map((c) => (
        <Node key={c.path} node={c} depth={depth + 1} selected={selected} onSelect={onSelect} />
      ))}
    </div>
  );
}

export function FilesPanel({ projectId, refreshKey }: { projectId: number; refreshKey: string }) {
  const [files, setFiles] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .files(projectId)
      .then(setFiles)
      .catch((e: Error) => setError(e.message));
  }, [projectId, refreshKey]);

  useEffect(() => {
    if (!selected) return;
    api
      .fileContent(projectId, selected)
      .then((r) => setContent(r.content))
      .catch((e: Error) => setError(e.message));
  }, [projectId, selected]);

  const download = async () => {
    const url = URL.createObjectURL(await api.downloadZip(projectId));
    const a = document.createElement("a");
    a.href = url;
    a.download = `project-${projectId}.zip`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (error) return <p className="text-sm text-red-700">{error}</p>;
  if (!files.length)
    return (
      <p className="text-sm text-slate-500">
        No files yet. Files appear here after you approve and apply changes.
      </p>
    );
  return (
    <div className="grid gap-3 md:grid-cols-[260px_1fr]">
      <div className="rounded border border-slate-200 bg-white p-2">
        <button onClick={download} className="mb-2 rounded border border-slate-300 px-2 py-1 text-xs">
          Download .zip
        </button>
        {buildTree(files).map((n) => (
          <Node key={n.path} node={n} depth={0} selected={selected} onSelect={setSelected} />
        ))}
      </div>
      <pre
        className="max-h-[32rem] overflow-auto rounded border border-slate-200 bg-white p-3 text-xs"
        aria-label="File preview"
      >
        {selected ? content : "Select a file to preview."}
      </pre>
    </div>
  );
}
