import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { apiFetch } from "../../lib/apiClient";
import { clearToken, getToken, getUser, setToken, setUser, type User } from "../../lib/auth";
import { AuthContext } from "./AuthContext";
import type { AuthContextValue, AuthResponse } from "./types";

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

  const loginWithGoogle = useCallback(async (credential: string) => {
    const response = await apiFetch<AuthResponse>("/api/auth/google", {
      method: "POST",
      body: JSON.stringify({ credential })
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

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, loginWithGoogle, logout, refresh }),
    [user, loading, loginWithGoogle, logout, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
