import { useState } from "react";
import type { Step } from "../types";
import { Badge } from "./Badge";

const LABELS: Record<string, string> = {
  product_manager: "Product Manager",
  architect: "Architect",
  task_planner: "Task Planner",
  developer: "Developer",
  reviewer: "Code Reviewer",
  testing: "Testing Agent",
  sandbox: "Sandbox (Docker)",
  debugger: "Debugger",
  final_review: "Final Review",
  documentation: "Documentation",
  supervisor: "Supervisor (rule-based routing)",
};

export function AgentMonitor({ steps }: { steps: Step[] }) {
  const [open, setOpen] = useState<number | null>(null);
  if (!steps.length) return <p className="text-sm text-slate-500">No agent activity yet.</p>;
  return (
    <ol className="space-y-2" aria-label="Agent execution monitor">
      {steps.map((s) => (
        <li key={s.id} className="rounded border border-slate-200 bg-white p-3">
          <button
            className="flex w-full items-center justify-between gap-2 text-left"
            onClick={() => setOpen(open === s.id ? null : s.id)}
          >
            <span className="font-medium">{LABELS[s.agent] ?? s.agent}</span>
            <span className="flex items-center gap-2">
              <span className="text-xs text-slate-500">{new Date(s.started_at).toLocaleTimeString()}</span>
              <Badge value={s.status} />
            </span>
          </button>
          {s.error && <p className="mt-2 text-sm text-red-700">{s.error}</p>}
          {open === s.id && s.output != null && (
            <pre className="mt-2 max-h-72 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-100">
              {JSON.stringify(s.output, null, 2)}
            </pre>
          )}
        </li>
      ))}
    </ol>
  );
}
