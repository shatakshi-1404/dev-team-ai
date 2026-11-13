import { useEffect, useState } from "react";
import { api } from "../api";
import type { Change } from "../types";

const DOCS = ["README.md", "docs/API.md"];

export function DocsPanel({ projectId, changes }: { projectId: number; changes: Change[] }) {
  const [applied, setApplied] = useState<Record<string, string>>({});
  useEffect(() => {
    DOCS.forEach((p) =>
      api
        .fileContent(projectId, p)
        .then((r) => setApplied((a) => ({ ...a, [p]: r.content })))
        .catch(() => undefined),
    );
  }, [projectId, changes.length]);
  const pending = changes.filter((c) => c.origin === "documentation" && c.status === "pending");
  if (!pending.length && !Object.keys(applied).length)
    return <p className="text-sm text-slate-500">Documentation is generated after testing.</p>;
  return (
    <div className="space-y-3">
      {pending.map((c) => (
        <div key={c.id} className="rounded border border-amber-300 bg-white p-3">
          <p className="mb-1 text-sm font-medium">
            {c.path} <span className="text-amber-700">(awaiting final approval; see the Changes tab)</span>
          </p>
        </div>
      ))}
      {Object.entries(applied).map(([p, content]) => (
        <div key={p} className="rounded border border-slate-200 bg-white p-3">
          <p className="mb-1 text-sm font-medium">{p}</p>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap text-xs">{content}</pre>
        </div>
      ))}
    </div>
  );
}
