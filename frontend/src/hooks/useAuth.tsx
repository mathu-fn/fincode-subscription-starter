import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { apiFetch } from "../lib/apiClient";
import { clearToken, getToken, getUser, setToken, setUser, type User } from "../lib/auth";

type AuthResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: User;
};

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (name: string, email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(() => getUser());
  const [loading, setLoading] = useState<boolean>(() => Boolean(getToken() && !getUser()));

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUserState(null);
      return;
    }
    try {
      const me = await apiFetch<User>("/api/user");
      setUser(me);
      setUserState(me);
    } catch {
      clearToken();
      setUserState(null);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (getToken()) {
      if (!getUser()) setLoading(true);
      refresh().finally(() => {
        if (!cancelled) setLoading(false);
      });
    }
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  useEffect(() => {
    const onAuthCleared = () => {
      setUserState(null);
    };
    window.addEventListener("fincode:auth-cleared", onAuthCleared);
    return () => {
      window.removeEventListener("fincode:auth-cleared", onAuthCleared);
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await apiFetch<AuthResponse>("/api/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    setToken(response.access_token);
    setUser(response.user);
    setUserState(response.user);
    return response.user;
  }, []);

  const register = useCallback(async (name: string, email: string, password: string) => {
    const response = await apiFetch<AuthResponse>("/api/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password })
    });
    setToken(response.access_token);
    setUser(response.user);
    setUserState(response.user);
    return response.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiFetch("/api/logout", { method: "POST" });
    } catch {
      // 無視する — ローカル状態は問わずクリアする
    }
    clearToken();
    setUserState(null);
  }, []);

  const value = useMemo<AuthContextValue>(() => ({ user, loading, login, register, logout, refresh }), [user, loading, login, register, logout, refresh]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return ctx;
}
