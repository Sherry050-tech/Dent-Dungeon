// lib/api.ts
import { tokens } from "./tokens";

const BASE = process.env.NEXT_PUBLIC_API_URL!;

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public fields: Record<string, string> = {}
  ) {
    super(message);
  }
}

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn;
}

// One refresh at a time, even if 5 requests expire together
let refreshing: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const current = tokens.get();
  if (!current) return false;
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: current.refresh }),
  });
  if (!res.ok) {
    tokens.clear();
    return false;
  }
  tokens.set({
    access: (await res.json()).access_token,
    refresh: current.refresh,
  });
  return true;
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
  retried = false
): Promise<T> {
  const t = tokens.get();
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(t ? { Authorization: `Bearer ${t.access}` } : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError(
      0,
      "NETWORK_ERROR",
      "Cannot reach the server. Check your connection."
    );
  }

  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    if (res.status === 401 && data.code === "TOKEN_EXPIRED" && !retried) {
      refreshing ??= refreshTokens().finally(() => {
        refreshing = null;
      });
      if (await refreshing) return api<T>(path, init, true);
    }
    if (res.status === 401 && data.code !== "INVALID_CREDENTIALS") {
      onUnauthorized?.();
    }
    throw new ApiError(
      res.status,
      data.code ?? "UNKNOWN",
      data.detail ?? "Something went wrong",
      data.fields ?? {}
    );
  }
  return data as T;
}