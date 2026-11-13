import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export const EXAMPLE_REQUIREMENTS =
  "Build a URL shortener with user authentication. Backend: Python FastAPI + SQLAlchemy + SQLite with JWT login " +
  "and registration (bcrypt), endpoints to create a short link for a long URL, list my links with click counts, " +
  "delete a link, and a public redirect endpoint GET /{code} that increments the click count. " +
  "Frontend: React + TypeScript + Vite with login/register pages, a dashboard listing my links, and a form to " +
  "shorten a URL. Include pytest tests for auth and link endpoints.";

export function NewProject() {
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [requirements, setRequirements] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const p = await api.createProject(name, requirements);
      nav(`/projects/${p.id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold">New project</h1>
      <label className="block text-sm font-medium">
        Name
        <input
          required
          maxLength={100}
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 font-normal"
        />
      </label>
      <label className="block text-sm font-medium">
        Requirements (natural language)
        <textarea
          required
          minLength={20}
          maxLength={8000}
          rows={9}
          value={requirements}
          onChange={(e) => setRequirements(e.target.value)}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 font-normal"
          placeholder="Describe the software you want built…"
        />
      </label>
      <button
        type="button"
        className="text-sm underline"
        onClick={() => {
          setName("URL Shortener");
          setRequirements(EXAMPLE_REQUIREMENTS);
        }}
      >
        Use the URL shortener example
      </button>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      <div>
        <button disabled={busy} className="rounded bg-slate-900 px-5 py-2 text-white disabled:opacity-50">
          Create project
        </button>
      </div>
    </form>
  );
}
