import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isRegister = mode === "register";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password, isRegister);
      nav("/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto mt-16 max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="mb-4 text-xl font-semibold">
        {isRegister ? "Create your account" : "Sign in to DevTeam AI"}
      </h1>
      <form onSubmit={submit} className="space-y-3">
        <label className="block text-sm">
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          Password
          <input
            type="password"
            required
            minLength={8}
            maxLength={72}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
        )}
        <button disabled={busy} className="w-full rounded bg-slate-900 py-2 text-white disabled:opacity-50">
          {isRegister ? "Register" : "Sign in"}
        </button>
      </form>
      <p className="mt-4 text-sm text-slate-600">
        {isRegister ? (
          <a className="underline" href="/login">
            Already have an account?
          </a>
        ) : (
          <a className="underline" href="/register">
            Create an account
          </a>
        )}
      </p>
    </main>
  );
}
