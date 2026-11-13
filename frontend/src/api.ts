import type { Change, OutlineEntry, Project, Run, SearchHit, SystemStatus } from "./types";

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";
const TOKEN_KEY = "devteam_token";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  if (init.body) headers["Content-Type"] = "application/json";
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  let res: Response;
  try {
    res = await fetch(`${BASE}/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "network", "Cannot reach the backend. Is it running?");
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail =
      body?.error ??
      (Array.isArray(body?.detail) ? { code: "validation", message: body.detail[0]?.msg } : null);
    throw new ApiError(
      res.status,
      detail?.code ?? "error",
      detail?.message ?? `Request failed (${res.status})`,
    );
  }
  return body as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  register: (email: string, password: string) =>
    post<{ access_token: string }>("/auth/register", { email, password }),
  login: (email: string, password: string) =>
    post<{ access_token: string }>("/auth/login", { email, password }),
  me: () => request<{ id: number; email: string }>("/auth/me"),
  status: () => request<SystemStatus>("/system/status"),
  projects: () => request<Project[]>("/projects"),
  createProject: (name: string, requirements: string) => post<Project>("/projects", { name, requirements }),
  project: (id: number) => request<Project>(`/projects/${id}`),
  deleteProject: (id: number) => request<void>(`/projects/${id}`, { method: "DELETE" }),
  files: (id: number) => request<string[]>(`/projects/${id}/files`),
  fileContent: (id: number, path: string) =>
    request<{ path: string; content: string }>(
      `/projects/${id}/files/content?path=${encodeURIComponent(path)}`,
    ),
  search: (id: number, q: string) =>
    request<SearchHit[]>(`/projects/${id}/search?q=${encodeURIComponent(q)}`),
  outline: (id: number) => request<OutlineEntry[]>(`/projects/${id}/outline`),
  runs: (id: number) => request<Run[]>(`/projects/${id}/runs`),
  startRun: (id: number) => post<Run>(`/projects/${id}/runs`),
  run: (id: number) => request<Run>(`/runs/${id}`),
  approvePlan: (id: number, confirmDependencies: boolean) =>
    post<Run>(`/runs/${id}/approve-plan`, { confirm_dependencies: confirmDependencies }),
  rejectPlan: (id: number) => post<Run>(`/runs/${id}/reject-plan`),
  changes: (id: number) => request<Change[]>(`/runs/${id}/changes`),
  approveChange: (id: number) => post<Change>(`/changes/${id}/approve`),
  rejectChange: (id: number) => post<Change>(`/changes/${id}/reject`),
  applyChanges: (id: number) => post<Run>(`/runs/${id}/apply-changes`),
  approveFinal: (id: number) => post<Run>(`/runs/${id}/approve-final`),
  rejectFinal: (id: number) => post<Run>(`/runs/${id}/reject-final`),
  retry: (id: number) => post<Run>(`/runs/${id}/retry`),
  downloadZip: async (id: number) => {
    const res = await fetch(`${BASE}/api/projects/${id}/download`, {
      headers: { Authorization: `Bearer ${tokenStore.get() ?? ""}` },
    });
    if (!res.ok) throw new ApiError(res.status, "error", "Download failed");
    return res.blob();
  },
};
