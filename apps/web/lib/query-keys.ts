// lib/query-keys.ts
// All TanStack Query keys live here. After a mutation, invalidate the matching key.
import type { StaffFilters } from "@/types/api";

export const queryKeys = {
  me: ["me"] as const,
  staff: (filters: StaffFilters = {}) => ["staff", filters] as const,
  staffAll: ["staff"] as const, // invalidate this to refresh every filtered staff list
  doctors: ["doctors"] as const,
  settings: ["settings"] as const,
};