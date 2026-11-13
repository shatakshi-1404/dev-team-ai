import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, tokenStore } from "./api";

interface AuthValue {
  email: string | null;
  loading: boolean;
  login: (email: string, password: string, register: boolean) => Promise<void>;
  logout: () => void;
}
const Ctx = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [email, setEmail] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(tokenStore.get()));

  useEffect(() => {
    if (!tokenStore.get()) return;
    api
      .me()
      .then((u) => setEmail(u.email))
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (e: string, p: string, register: boolean) => {
    const { access_token } = register ? await api.register(e, p) : await api.login(e, p);
    tokenStore.set(access_token);
    setEmail((await api.me()).email);
  }, []);
  const logout = useCallback(() => {
    tokenStore.clear();
    setEmail(null);
  }, []);

  return <Ctx.Provider value={{ email, loading, login, logout }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}
