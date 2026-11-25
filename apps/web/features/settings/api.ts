// features/settings/api.ts
import { api } from "@/lib/api";
import * as mocks from "@/lib/mocks";
import type { ClinicSettings, ClinicSettingsPatch } from "@/types/api";

const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

export function getClinicSettings(): Promise<ClinicSettings> {
  if (USE_MOCKS) return mocks.mockGetSettings();
  return api<ClinicSettings>("/settings/clinic");
}

// Send only what changed. For working_hours send all 7 days (the server replaces the schedule).
export function updateClinicSettings(
  patch: ClinicSettingsPatch
): Promise<ClinicSettings> {
  if (USE_MOCKS) return mocks.mockUpdateSettings(patch);
  return api<ClinicSettings>("/settings/clinic", {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}