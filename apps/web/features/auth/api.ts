// features/auth/api.ts
import { api } from "@/lib/api";
import * as mocks from "@/lib/mocks";
import type { AuthResponse, MeResponse, RegisterInput } from "@/types/api";

const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

export function login(email: string, password: string): Promise<AuthResponse> {
  if (USE_MOCKS) return mocks.mockLogin(email, password);
  return api<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function register(input: RegisterInput): Promise<AuthResponse> {
  if (USE_MOCKS) return mocks.mockRegister(input);
  return api<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function fetchMe(): Promise<MeResponse> {
  if (USE_MOCKS) return mocks.mockMe();
  return api<MeResponse>("/auth/me");
}

export function changePassword(
  current_password: string,
  new_password: string
): Promise<void> {
  if (USE_MOCKS) return mocks.mockChangePassword(current_password, new_password);
  return api<void>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password, new_password }),
  });
}