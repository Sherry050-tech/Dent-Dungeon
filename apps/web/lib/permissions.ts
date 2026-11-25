// lib/permissions.ts
import type { User } from "@/types/api";

export type Action = "staff.manage" | "settings.edit";

// Mirrors the backend. The server enforces it too; this only decides what the UI shows.
export function can(user: User | null | undefined, action: Action): boolean {
  if (!user) return false;
  switch (action) {
    case "staff.manage":
    case "settings.edit":
      return user.role === "admin";
  }
}

// "Can treat patients" = a doctor, or anyone flagged is_practitioner (for example a solo owner).
export const treatsPatients = (u: User) =>
  u.role === "doctor" || u.is_practitioner;

export const fullName = (u: Pick<User, "first_name" | "last_name">) =>
  `${u.first_name} ${u.last_name}`;