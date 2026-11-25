// features/auth/auth-provider.tsx
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError, setUnauthorizedHandler } from "@/lib/api";
import { tokens } from "@/lib/tokens";
import { fetchMe, login as loginApi, register as registerApi } from "./api";
import type { AuthResponse, Clinic, RegisterInput, User } from "@/types/api";

type Status = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  status: Status;
  user: User | null;
  clinic: Clinic | null;
  login: (email: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  // "loading" on the server and on the first browser frame, so both render the same HTML.
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [clinic, setClinic] = useState<Clinic | null>(null);

  const clearSession = useCallback(() => {
    tokens.clear();
    queryClient.clear(); // one user's data must never show for the next user
    setUser(null);
    setClinic(null);
    setStatus("anonymous");
  }, [queryClient]);

  const startSession = useCallback((res: AuthResponse) => {
    tokens.set({ access: res.access_token, refresh: res.refresh_token });
    setUser(res.user);
    setClinic(res.clinic);
    setStatus("authenticated");
  }, []);

  // Restore the session on app start (only in the browser, inside an effect).
  useEffect(() => {
    async function restore() {
      if (!tokens.get()) {
        setStatus("anonymous");
        return;
      }
      try {
        const me = await fetchMe();
        setUser(me.user);
        setClinic(me.clinic);
        setStatus("authenticated");
      } catch (err) {
        // Bad or dead token: forget it. A plain network error keeps the tokens
        // so a temporary server problem does not log everybody out.
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          tokens.clear();
        }
        setUser(null);
        setClinic(null);
        setStatus("anonymous");
      }
    }
    void restore();
  }, []);

  // Any 401 from the API (except wrong login password) logs the user out.
  useEffect(() => {
    setUnauthorizedHandler(clearSession);
    return () => setUnauthorizedHandler(null);
  }, [clearSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await loginApi(email, password);
      startSession(res);
      router.replace("/dashboard");
    },
    [router, startSession]
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      const res = await registerApi(input);
      startSession(res); // registering already logs the person in
      router.replace("/dashboard");
    },
    [router, startSession]
  );

  const logout = useCallback(() => {
    clearSession();
    router.replace("/login");
  }, [clearSession, router]);

  const refreshMe = useCallback(async () => {
    const me = await fetchMe();
    setUser(me.user);
    setClinic(me.clinic);
  }, []);

  const value = useMemo(
    () => ({ status, user, clinic, login, register, logout, refreshMe }),
    [status, user, clinic, login, register, logout, refreshMe]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}