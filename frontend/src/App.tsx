import { useEffect, useState } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api";
import { useAuth } from "./auth";
import { StatusBanner } from "./components/StatusBanner";
import { AuthPage } from "./pages/AuthPage";
import { Dashboard } from "./pages/Dashboard";
import { NewProject } from "./pages/NewProject";
import { ProjectPage } from "./pages/ProjectPage";
import type { SystemStatus } from "./types";

export default function App() {
  const { email, loading, logout } = useAuth();
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    api
      .status()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, [email]);

  if (loading) return <p className="p-8">Loading…</p>;
  return (
    <BrowserRouter>
      <StatusBanner status={status} />
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-bold">
            DevTeam AI
          </Link>
          {email && (
            <span className="flex items-center gap-3 text-sm">
              <span className="hidden text-slate-500 sm:inline">{email}</span>
              <button onClick={logout} className="underline">
                Sign out
              </button>
            </span>
          )}
        </div>
      </header>
      <div className="mx-auto max-w-6xl px-4 py-6">
        <Routes>
          <Route path="/login" element={email ? <Navigate to="/" /> : <AuthPage mode="login" />} />
          <Route path="/register" element={email ? <Navigate to="/" /> : <AuthPage mode="register" />} />
          <Route path="/" element={email ? <Dashboard /> : <Navigate to="/login" />} />
          <Route path="/projects/new" element={email ? <NewProject /> : <Navigate to="/login" />} />
          <Route
            path="/projects/:id"
            element={email ? <ProjectPage status={status} /> : <Navigate to="/login" />}
          />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
