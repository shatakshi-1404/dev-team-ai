import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { AgentMonitor } from "../components/AgentMonitor";
import { Badge } from "../components/Badge";
import { ChangesPanel } from "../components/ChangesPanel";
import { DocsPanel } from "../components/DocsPanel";
import { FilesPanel } from "../components/FilesPanel";
import { PlanPanel } from "../components/PlanPanel";
import { SearchPanel } from "../components/SearchPanel";
import { TestsPanel } from "../components/TestsPanel";
import type { Change, Project, Run, SystemStatus } from "../types";

const TABS = ["Workflow", "Changes", "Files", "Tests", "Docs", "Search"] as const;
type Tab = (typeof TABS)[number];
const TERMINAL = ["completed", "rejected", "failed"];

export function ProjectPage({ status }: { status: SystemStatus | null }) {
  const id = Number(useParams().id);
  const [project, setProject] = useState<Project | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [changes, setChanges] = useState<Change[]>([]);
  const [tab, setTab] = useState<Tab>("Workflow");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [p, runs] = await Promise.all([api.project(id), api.runs(id)]);
      setProject(p);
      const latest = runs[0] ?? null;
      setRun(latest);
      setChanges(latest ? await api.changes(latest.id) : []);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    void refresh();
  }, [refresh]);
  useEffect(() => {
    if (!run?.status.startsWith("running")) return;
    const t = setInterval(() => void refresh(), 2000);
    return () => clearInterval(t);
  }, [run?.status, refresh]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!project) return <p>{error ?? "Loading…"}</p>;
  const canStart = !run || TERMINAL.includes(run.status);
  const decidableOrigin =
    run?.status === "awaiting_change_approval"
      ? "developer"
      : run?.status === "awaiting_final_approval"
        ? "documentation"
        : null;

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold">{project.name}</h1>
          <p className="max-w-3xl text-sm text-slate-600">{project.requirements}</p>
        </div>
        {run && <Badge value={run.status} />}
      </header>
      {error && (
        <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <nav className="flex gap-1 overflow-x-auto border-b border-slate-200" aria-label="Project sections">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`whitespace-nowrap px-4 py-2 text-sm ${tab === t ? "border-b-2 border-slate-900 font-medium" : "text-slate-500"}`}
          >
            {t}
            {t === "Changes" && changes.length ? ` (${changes.length})` : ""}
          </button>
        ))}
      </nav>

      {tab === "Workflow" && (
        <div className="space-y-4">
          {canStart && (
            <div className="flex flex-wrap items-center gap-3">
              <button
                disabled={busy || !status?.llm_configured}
                onClick={() => act(() => api.startRun(id))}
                className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                {run ? "Start a new run" : "Start agent workflow"}
              </button>
              {!status?.llm_configured && (
                <span className="text-sm text-amber-700">
                  Configure GROQ_API_KEY on the backend to enable the agents.
                </span>
              )}
            </div>
          )}
          {run?.status.startsWith("running") && (
            <p className="text-sm text-blue-700">Agents are working… this page refreshes automatically.</p>
          )}
          {run?.status === "failed" && (
            <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              <p>Run failed: {run.error}</p>
              <button
                disabled={busy}
                onClick={() => act(() => api.retry(run.id))}
                className="mt-2 rounded border border-red-300 px-3 py-1"
              >
                Retry last phase
              </button>
            </div>
          )}
          {run &&
            [
              "awaiting_plan_approval",
              "running_development",
              "awaiting_change_approval",
              "running_testing",
              "awaiting_final_approval",
              "completed",
              "rejected",
            ].includes(run.status) &&
            run.state.plan && (
              <PlanPanel
                state={run.state}
                canDecide={run.status === "awaiting_plan_approval"}
                busy={busy}
                onApprove={(c) => act(() => api.approvePlan(run.id, c))}
                onReject={() => act(() => api.rejectPlan(run.id))}
              />
            )}
          {run?.status === "awaiting_change_approval" && (
            <div className="rounded border border-slate-200 bg-white p-4 text-sm">
              <p className="font-medium">Review required</p>
              {run.state.review && (
                <p className="mt-1 text-slate-700">
                  Reviewer ({run.state.review.verdict}): {run.state.review.summary}
                </p>
              )}
              <ul className="mt-1 list-disc pl-5">
                {run.state.review?.issues.map((i, n) => (
                  <li key={n}>
                    [{i.severity}] {i.path} {i.message}
                  </li>
                ))}
              </ul>
              <button className="mt-3 underline" onClick={() => setTab("Changes")}>
                Go to proposed file changes →
              </button>
            </div>
          )}
          {run?.status === "awaiting_final_approval" && (
            <div className="space-y-2 rounded border border-slate-200 bg-white p-4 text-sm">
              <p className="font-medium">Final approval</p>
              <p>
                Measured test status: <Badge value={run.state.final_test_status ?? "not_run"} /> (repair
                attempts: {run.repair_attempts}/{status?.max_repair_attempts ?? 2})
              </p>
              {run.state.final_review && (
                <p className="text-slate-700">
                  Final review ({run.state.final_review.verdict}): {run.state.final_review.summary}
                </p>
              )}
              <ul className="list-disc pl-5">
                {run.state.final_review?.risks.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
              <div className="flex gap-2 pt-2">
                <button
                  disabled={busy}
                  onClick={() => act(() => api.approveFinal(run.id))}
                  className="rounded bg-emerald-600 px-4 py-2 text-white"
                >
                  Approve &amp; write docs
                </button>
                <button
                  disabled={busy}
                  onClick={() => act(() => api.rejectFinal(run.id))}
                  className="rounded border border-slate-300 px-4 py-2"
                >
                  Reject
                </button>
              </div>
            </div>
          )}
          <h2 className="text-lg font-semibold">Agent execution monitor</h2>
          <AgentMonitor steps={run?.steps ?? []} />
        </div>
      )}
      {tab === "Changes" && (
        <ChangesPanel
          changes={changes}
          decidableOrigin={decidableOrigin}
          busy={busy}
          onDecide={(cid, ok) => act(() => (ok ? api.approveChange(cid) : api.rejectChange(cid)))}
          onApply={
            run?.status === "awaiting_change_approval" ? () => act(() => api.applyChanges(run.id)) : undefined
          }
        />
      )}
      {tab === "Files" && <FilesPanel projectId={id} refreshKey={`${run?.id}-${run?.status}`} />}
      {tab === "Tests" &&
        (run ? <TestsPanel run={run} /> : <p className="text-sm text-slate-500">No run yet.</p>)}
      {tab === "Docs" && <DocsPanel projectId={id} changes={changes} />}
      {tab === "Search" && <SearchPanel projectId={id} />}
    </div>
  );
}
