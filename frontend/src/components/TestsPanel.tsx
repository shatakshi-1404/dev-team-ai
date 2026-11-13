import type { Run } from "../types";
import { Badge } from "./Badge";

export function TestsPanel({ run }: { run: Run }) {
  if (!run.test_runs.length) return <p className="text-sm text-slate-500">Tests have not been run yet.</p>;
  const latest = run.test_runs[run.test_runs.length - 1];
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 rounded border border-slate-200 bg-white p-3">
        <span className="font-medium">Latest result:</span>
        <Badge value={latest.status} />
        <span className="text-sm text-slate-600">Repair attempts used: {run.repair_attempts}</span>
        {latest.status === "unavailable" && (
          <span className="text-sm text-amber-700">Docker was unavailable, so no tests were executed.</span>
        )}
      </div>
      {run.test_runs.map((t) => (
        <div key={t.id} className="rounded border border-slate-200 bg-white p-3">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-sm font-medium">
              {t.attempt === 0 ? "Initial run" : `After repair #${t.attempt}`}
            </span>
            <Badge value={t.status} />
            <span className="text-xs text-slate-500">
              exit {t.exit_code ?? "–"} · {t.duration_seconds.toFixed(1)}s
            </span>
          </div>
          <pre className="max-h-64 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-100">
            {t.output || "(no output)"}
          </pre>
        </div>
      ))}
    </div>
  );
}
