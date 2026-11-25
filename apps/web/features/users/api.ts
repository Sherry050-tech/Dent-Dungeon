// features/users/api.ts
// No trailing slashes in API paths: "/users", never "/users/".
import { api } from "@/lib/api";
import * as mocks from "@/lib/mocks";
import type {
  CreateStaffInput,
  Paginated,
  StaffFilters,
  UpdateStaffInput,
  User,
} from "@/types/api";

const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

export function listStaff(filters: StaffFilters = {}): Promise<Paginated<User>> {
  if (USE_MOCKS) return mocks.mockListStaff(filters);
  const qs = new URLSearchParams();
  if (filters.role) qs.set("role", filters.role);
  if (filters.is_active !== undefined) qs.set("is_active", String(filters.is_active));
  if (filters.page) qs.set("page", String(filters.page));
  if (filters.limit) qs.set("limit", String(filters.limit));
  const query = qs.toString();
  return api<Paginated<User>>(`/users${query ? `?${query}` : ""}`);
}

export function createStaff(input: CreateStaffInput): Promise<User> {
  if (USE_MOCKS) return mocks.mockCreateStaff(input);
  return api<User>("/users", { method: "POST", body: JSON.stringify(input) });
}

export function updateStaff(id: string, patch: UpdateStaffInput): Promise<User> {
  if (USE_MOCKS) return mocks.mockUpdateStaff(id, patch);
  return api<User>(`/users/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
}

export function listDoctors(): Promise<Paginated<User>> {
  if (USE_MOCKS) return mocks.mockListDoctors();
  return api<Paginated<User>>("/users/doctors");
}