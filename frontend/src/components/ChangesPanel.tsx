import { useState } from "react";
import { diffStats } from "../lib/diff";
import type { Change } from "../types";
import { Badge } from "./Badge";
import { DiffViewer } from "./DiffViewer";

interface Props {
  changes: Change[];
  decidableOrigin: string | null; // which origin can currently be approved/rejected
  busy: boolean;
  onDecide: (id: number, approve: boolean) => void;
  onApply?: () => void;
}

export function ChangesPanel({ changes, decidableOrigin, busy, onDecide, onApply }: Props) {
  const [open, setOpen] = useState<Set<number>>(new Set());
  if (!changes.length) return <p className="text-sm text-slate-500">No file changes yet.</p>;
  const toggle = (id: number) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const undecided = changes.filter((c) => c.origin === "developer" && c.status === "pending").length;
  return (
    <div className="space-y-3">
      {onApply && (
        <div className="flex flex-wrap items-center gap-3 rounded border border-slate-200 bg-white p-3">
          <button
            disabled={busy || undecided > 0}
            onClick={onApply}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Apply approved changes &amp; run tests
          </button>
          {undecided > 0 && (
            <span className="text-sm text-amber-700">{undecided} change(s) still need a decision.</span>
          )}
        </div>
      )}
      {changes.map((c) => {
        const { added, removed } = diffStats(c.diff);
        const decidable =
          decidableOrigin === c.origin && ["pending", "approved", "rejected"].includes(c.status);
        return (
          <div key={c.id} className="rounded border border-slate-200 bg-white">
            <div className="flex flex-wrap items-center justify-between gap-2 p-3">
              <button onClick={() => toggle(c.id)} className="text-left">
                <span className="font-mono text-sm">{c.path}</span>
                <span className="ml-2 text-xs text-emerald-700">+{added}</span>
                <span className="ml-1 text-xs text-red-700">-{removed}</span>
              </button>
              <div className="flex items-center gap-2">
                <Badge value={c.action} />
                <span className="text-xs text-slate-500">{c.origin}</span>
                <Badge value={c.status} />
                {decidable && (
                  <>
                    <button
                      disabled={busy}
                      onClick={() => onDecide(c.id, true)}
                      className="rounded bg-emerald-600 px-2 py-1 text-xs text-white"
                    >
                      Approve
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => onDecide(c.id, false)}
                      className="rounded border border-slate-300 px-2 py-1 text-xs"
                    >
                      Reject
                    </button>
                  </>
                )}
              </div>
            </div>
            {c.action === "delete" && (
              <p className="px-3 pb-2 text-sm font-medium text-red-700">
                Destructive change: deletes this file.
              </p>
            )}
            {c.rationale && <p className="px-3 pb-2 text-sm text-slate-600">{c.rationale}</p>}
            {open.has(c.id) && (
              <div className="p-3 pt-0">
                <DiffViewer diff={c.diff} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
