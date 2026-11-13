import { useState } from "react";
import { api } from "../api";
import type { OutlineEntry, SearchHit } from "../types";

export function SearchPanel({ projectId }: { projectId: number }) {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [outline, setOutline] = useState<OutlineEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      setHits(await api.search(projectId, q));
    } catch (err) {
      setError((err as Error).message);
    }
  };
  const loadOutline = async () => {
    try {
      setOutline(await api.outline(projectId));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <form onSubmit={run} className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search the repository (min. 2 chars)"
          aria-label="Search query"
          className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <button className="rounded bg-slate-800 px-4 py-2 text-sm text-white">Search</button>
        <button
          type="button"
          onClick={loadOutline}
          className="rounded border border-slate-300 px-4 py-2 text-sm"
        >
          Code outline
        </button>
      </form>
      {error && <p className="text-sm text-red-700">{error}</p>}
      {hits &&
        (hits.length ? (
          <ul className="divide-y divide-slate-100 rounded border border-slate-200 bg-white text-sm">
            {hits.map((h, i) => (
              <li key={i} className="p-2">
                <span className="font-mono text-xs text-slate-500">
                  {h.path}:{h.line}
                </span>
                <br />
                <code>{h.text}</code>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">No matches.</p>
        ))}
      {outline &&
        (outline.length ? (
          outline.map((o) => (
            <div key={o.path} className="rounded border border-slate-200 bg-white p-2 text-sm">
              <p className="font-mono text-xs font-medium">{o.path}</p>
              <ul className="pl-4">
                {o.symbols.map((s) => (
                  <li key={s.name + s.line}>
                    {s.kind} <b>{s.name}</b> <span className="text-slate-400">:{s.line}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))
        ) : (
          <p className="text-sm text-slate-500">No symbols found.</p>
        ))}
    </div>
  );
}
