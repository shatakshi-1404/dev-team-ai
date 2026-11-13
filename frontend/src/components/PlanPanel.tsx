import { useState } from "react";
import type { RunState } from "../types";

interface Props {
  state: RunState;
  canDecide: boolean;
  busy: boolean;
  onApprove: (confirmDependencies: boolean) => void;
  onReject: () => void;
}

export function PlanPanel({ state, canDecide, busy, onApprove, onReject }: Props) {
  const [confirmed, setConfirmed] = useState(false);
  const flagged = state.dependencies_needing_approval ?? [];
  if (!state.spec || !state.architecture || !state.plan) return null;
  return (
    <section className="space-y-4 rounded border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold">Plan for approval</h2>
      <div>
        <h3 className="font-medium">Product spec</h3>
        <p className="text-sm text-slate-700">{state.spec.summary}</p>
        <ul className="mt-2 list-disc pl-5 text-sm">
          {state.spec.acceptance_criteria.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </div>
      <div>
        <h3 className="font-medium">Architecture</h3>
        <p className="text-sm text-slate-700">{state.architecture.overview}</p>
        <table className="mt-2 w-full text-left text-sm">
          <tbody>
            {state.architecture.api_endpoints.map((e) => (
              <tr key={e.method + e.path} className="border-t border-slate-100">
                <td className="py-1 pr-2 font-mono text-xs">{e.method}</td>
                <td className="py-1 pr-2 font-mono text-xs">{e.path}</td>
                <td className="py-1 text-slate-600">{e.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div>
        <h3 className="font-medium">Tasks ({state.plan.tasks.length})</h3>
        <ol className="list-decimal pl-5 text-sm">
          {state.plan.tasks.map((t) => (
            <li key={t.id}>
              {t.title} <span className="font-mono text-xs text-slate-500">{t.files.join(", ")}</span>
            </li>
          ))}
        </ol>
      </div>
      {flagged.length > 0 && (
        <label className="flex items-start gap-2 rounded border border-amber-300 bg-amber-50 p-3 text-sm">
          <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
          <span>
            I approve these dependencies, which are not in the sandbox image: <b>{flagged.join(", ")}</b>.
            They are only listed in project files; nothing is installed automatically.
          </span>
        </label>
      )}
      {canDecide && (
        <div className="flex gap-2">
          <button
            disabled={busy || (flagged.length > 0 && !confirmed)}
            onClick={() => onApprove(confirmed)}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Approve plan &amp; start development
          </button>
          <button
            disabled={busy}
            onClick={onReject}
            className="rounded border border-slate-300 px-4 py-2 text-sm"
          >
            Reject
          </button>
        </div>
      )}
    </section>
  );
}
