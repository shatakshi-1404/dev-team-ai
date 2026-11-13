import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Badge } from "../components/Badge";
import type { Project } from "../types";

export function Dashboard() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    api
      .projects()
      .then(setProjects)
      .catch((e: Error) => setError(e.message));
  useEffect(() => {
    void load();
  }, []);

  const remove = async (p: Project) => {
    if (!window.confirm(`Delete "${p.name}" and all its generated files?`)) return;
    await api.deleteProject(p.id);
    await load();
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <Link to="/projects/new" className="rounded bg-slate-900 px-4 py-2 text-sm text-white">
          New project
        </Link>
      </div>
      {error && (
        <p role="alert" className="text-red-700">
          {error}
        </p>
      )}
      {projects && projects.length === 0 && (
        <p className="rounded border border-dashed border-slate-300 p-8 text-center text-slate-500">
          No projects yet. Describe an application and let the agent team build it.
        </p>
      )}
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {projects?.map((p) => (
          <li key={p.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <Link to={`/projects/${p.id}`} className="text-lg font-medium hover:underline">
              {p.name}
            </Link>
            <p className="mt-1 line-clamp-3 text-sm text-slate-600">{p.requirements}</p>
            <div className="mt-3 flex items-center justify-between">
              {p.latest_run_status ? (
                <Badge value={p.latest_run_status} />
              ) : (
                <span className="text-xs text-slate-400">no runs</span>
              )}
              <button onClick={() => remove(p)} className="text-xs text-red-700 hover:underline">
                Delete
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
