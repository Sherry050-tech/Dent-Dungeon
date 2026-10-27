// lib/mocks.ts
// In-memory fake server. Returns exactly the shapes in Part 5 of the plan.
// State resets when you reload the page (tokens in localStorage may then point at a
// user that no longer exists; the app logs you out, which is fine for mock mode).
import { ApiError } from "./api";
import { tokens } from "./tokens";
import type {
  AuthResponse,
  Clinic,
  ClinicSettings,
  ClinicSettingsPatch,
  CreateStaffInput,
  MeResponse,
  Paginated,
  Preferences,
  RegisterInput,
  StaffFilters,
  UpdateStaffInput,
  User,
  Weekday,
  WorkingHours,
} from "@/types/api";

const delay = (ms = 300) => new Promise<void>((r) => setTimeout(r, ms));

type MockUser = User & { password: string };

const DEMO_PASSWORD = "Demo-Pass-123";
const DAYS: Weekday[] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

function defaultPreferences(): Preferences {
  const working_hours = Object.fromEntries(
    DAYS.map((d) => [d, d === "sun" ? null : ["09:00", "17:00"]])
  ) as WorkingHours;
  return {
    currency: "PKR",
    timezone: "Asia/Karachi",
    default_slot_min: 30,
    working_hours,
  };
}

const clinics = new Map<string, Clinic>([
  ["clinic-1", { id: "clinic-1", name: "Bright Smile Dental (Demo)", address: null, phone: null }],
  ["clinic-2", { id: "clinic-2", name: "Smile Care Clinic (Demo)", address: null, phone: null }],
]);

const prefs = new Map<string, Preferences>([
  ["clinic-1", defaultPreferences()],
  ["clinic-2", defaultPreferences()],
]);

const users: MockUser[] = [
  { id: "u-1", clinic_id: "clinic-1", first_name: "Sara", last_name: "Ahmed", email: "demo.owner@example.com", role: "admin", is_practitioner: true, is_active: true, password: DEMO_PASSWORD },
  { id: "u-2", clinic_id: "clinic-1", first_name: "Imran", last_name: "Qureshi", email: "demo.doctor@example.com", role: "doctor", is_practitioner: true, is_active: true, password: DEMO_PASSWORD },
  { id: "u-3", clinic_id: "clinic-1", first_name: "Hina", last_name: "Shah", email: "demo.reception@example.com", role: "receptionist", is_practitioner: false, is_active: true, password: DEMO_PASSWORD },
  { id: "u-4", clinic_id: "clinic-2", first_name: "Bilal", last_name: "Khan", email: "demo.owner2@example.com", role: "admin", is_practitioner: false, is_active: true, password: DEMO_PASSWORD },
  { id: "u-5", clinic_id: "clinic-2", first_name: "Ayesha", last_name: "Malik", email: "demo.doctor2@example.com", role: "doctor", is_practitioner: true, is_active: true, password: DEMO_PASSWORD },
];

// ---------- helpers ----------

function toUser(u: MockUser): User {
  const { password, ...rest } = u;
  void password;
  return rest;
}

function authResponse(u: MockUser): AuthResponse {
  return {
    access_token: `mock-access:${u.id}`,
    refresh_token: `mock-refresh:${u.id}`,
    token_type: "bearer",
    expires_in: 3600,
    user: toUser(u),
    clinic: clinics.get(u.clinic_id)!,
  };
}

function fail(fields: Record<string, string>): never {
  throw new ApiError(422, "VALIDATION_ERROR", "Validation failed", fields);
}

function current(): MockUser {
  const access = tokens.get()?.access ?? "";
  const id = access.startsWith("mock-access:") ? access.slice("mock-access:".length) : "";
  const u = users.find((x) => x.id === id);
  if (!u || !u.is_active) {
    throw new ApiError(401, "NOT_AUTHENTICATED", "Login required");
  }
  return u;
}

function requireAdmin(u: MockUser) {
  if (u.role !== "admin") {
    throw new ApiError(403, "FORBIDDEN", "You do not have permission");
  }
}

function emailTaken(email: string) {
  return email === "taken@example.com" || users.some((u) => u.email === email);
}

// ---------- auth ----------

export async function mockLogin(email: string, password: string): Promise<AuthResponse> {
  await delay();
  const u = users.find((x) => x.email === email.trim().toLowerCase());
  if (!u || u.password !== password) {
    throw new ApiError(401, "INVALID_CREDENTIALS", "Email or password is incorrect");
  }
  if (!u.is_active) {
    throw new ApiError(403, "ACCOUNT_INACTIVE", "This account has been deactivated");
  }
  return authResponse(u);
}

export async function mockRegister(input: RegisterInput): Promise<AuthResponse> {
  await delay();
  const email = input.email.trim().toLowerCase();
  const fields: Record<string, string> = {};
  if (input.clinic_name.trim().length < 2) fields.clinic_name = "Clinic name must be at least 2 characters";
  if (!input.first_name.trim()) fields.first_name = "First name is required";
  if (!input.last_name.trim()) fields.last_name = "Last name is required";
  if (input.password.length < 8) fields.password = "Password must be at least 8 characters";
  if (Object.keys(fields).length) fail(fields);

  if (emailTaken(email)) {
    throw new ApiError(409, "EMAIL_TAKEN", "That email is already registered", {
      email: "This email is already registered.",
    });
  }

  const clinicId = crypto.randomUUID();
  clinics.set(clinicId, { id: clinicId, name: input.clinic_name.trim(), address: null, phone: null });
  prefs.set(clinicId, defaultPreferences());

  const u: MockUser = {
    id: crypto.randomUUID(),
    clinic_id: clinicId,
    first_name: input.first_name.trim(),
    last_name: input.last_name.trim(),
    email,
    role: "admin",
    is_practitioner: input.is_practitioner,
    is_active: true,
    password: input.password,
  };
  users.push(u);
  return authResponse(u);
}

export async function mockMe(): Promise<MeResponse> {
  await delay(150);
  const u = current();
  return { user: toUser(u), clinic: clinics.get(u.clinic_id)! };
}

export async function mockChangePassword(currentPassword: string, newPassword: string): Promise<void> {
  await delay();
  const u = current();
  if (u.password !== currentPassword) {
    throw new ApiError(400, "WRONG_PASSWORD", "Current password is incorrect", {
      current_password: "Current password is incorrect",
    });
  }
  if (newPassword.length < 8) fail({ new_password: "Password must be at least 8 characters" });
  if (newPassword === currentPassword) {
    fail({ new_password: "New password must be different from the current one" });
  }
  u.password = newPassword;
}

// ---------- staff ----------

export async function mockListStaff(f: StaffFilters = {}): Promise<Paginated<User>> {
  await delay();
  const me = current();
  requireAdmin(me);
  let items = users.filter((u) => u.clinic_id === me.clinic_id);
  if (f.role) items = items.filter((u) => u.role === f.role);
  if (f.is_active !== undefined) items = items.filter((u) => u.is_active === f.is_active);
  items.sort((a, b) => a.first_name.localeCompare(b.first_name));
  const page = f.page ?? 1;
  const limit = f.limit ?? 20;
  return {
    items: items.slice((page - 1) * limit, page * limit).map(toUser),
    total: items.length,
    page,
    limit,
  };
}

export async function mockCreateStaff(input: CreateStaffInput): Promise<User> {
  await delay();
  const me = current();
  requireAdmin(me);
  const email = input.email.trim().toLowerCase();
  const fields: Record<string, string> = {};
  if (!input.first_name.trim()) fields.first_name = "First name is required";
  if (!input.last_name.trim()) fields.last_name = "Last name is required";
  if (input.temporary_password.length < 8) {
    fields.temporary_password = "Password must be at least 8 characters";
  }
  if (Object.keys(fields).length) fail(fields);
  if (emailTaken(email)) {
    throw new ApiError(409, "EMAIL_TAKEN", "That email is already registered", {
      email: "This email is already registered.",
    });
  }
  const u: MockUser = {
    id: crypto.randomUUID(),
    clinic_id: me.clinic_id,
    first_name: input.first_name.trim(),
    last_name: input.last_name.trim(),
    email,
    role: input.role,
    is_practitioner: input.is_practitioner,
    is_active: true,
    password: input.temporary_password,
  };
  users.push(u);
  return toUser(u);
}

export async function mockUpdateStaff(id: string, patch: UpdateStaffInput): Promise<User> {
  await delay();
  const me = current();
  requireAdmin(me);
  const target = users.find((u) => u.id === id && u.clinic_id === me.clinic_id);
  if (!target) throw new ApiError(404, "NOT_FOUND", "User not found");

  const losesAdmin =
    target.role === "admin" &&
    target.is_active &&
    ((patch.role !== undefined && patch.role !== "admin") || patch.is_active === false);
  if (losesAdmin) {
    const activeAdmins = users.filter(
      (u) => u.clinic_id === me.clinic_id && u.role === "admin" && u.is_active
    ).length;
    if (activeAdmins <= 1) {
      throw new ApiError(400, "LAST_ADMIN", "You cannot remove the clinic's only active admin");
    }
  }

  if (patch.first_name !== undefined) target.first_name = patch.first_name.trim();
  if (patch.last_name !== undefined) target.last_name = patch.last_name.trim();
  if (patch.role !== undefined) target.role = patch.role;
  if (patch.is_practitioner !== undefined) target.is_practitioner = patch.is_practitioner;
  if (patch.is_active !== undefined) target.is_active = patch.is_active;
  return toUser(target);
}

export async function mockListDoctors(): Promise<Paginated<User>> {
  await delay();
  const me = current();
  const items = users
    .filter(
      (u) =>
        u.clinic_id === me.clinic_id &&
        u.is_active &&
        (u.role === "doctor" || u.is_practitioner)
    )
    .sort((a, b) => a.first_name.localeCompare(b.first_name))
    .map(toUser);
  return { items, total: items.length, page: 1, limit: items.length || 20 };
}

// ---------- settings ----------

function settingsFor(clinicId: string): ClinicSettings {
  return { clinic: clinics.get(clinicId)!, preferences: prefs.get(clinicId)! };
}

export async function mockGetSettings(): Promise<ClinicSettings> {
  await delay();
  const me = current();
  return structuredClone(settingsFor(me.clinic_id));
}

export async function mockUpdateSettings(patch: ClinicSettingsPatch): Promise<ClinicSettings> {
  await delay();
  const me = current();
  requireAdmin(me);
  const clinic = clinics.get(me.clinic_id)!;
  const p = prefs.get(me.clinic_id)!;
  const fields: Record<string, string> = {};

  if (patch.clinic?.name !== undefined && patch.clinic.name.trim().length < 2) {
    fields["clinic.name"] = "Clinic name must be at least 2 characters";
  }
  const pp = patch.preferences;
  if (pp?.timezone !== undefined) {
    try {
      new Intl.DateTimeFormat("en", { timeZone: pp.timezone });
    } catch {
      fields["preferences.timezone"] = "Enter a valid time zone";
    }
  }
  if (pp?.default_slot_min !== undefined && (pp.default_slot_min < 5 || pp.default_slot_min > 240)) {
    fields["preferences.default_slot_min"] = "Slot length must be between 5 and 240 minutes";
  }
  if (pp?.working_hours) {
    for (const [day, hours] of Object.entries(pp.working_hours)) {
      if (hours && hours[1] <= hours[0]) {
        fields["preferences.working_hours"] = `Closing time must be after opening time (${day})`;
      }
    }
  }
  if (Object.keys(fields).length) fail(fields);

  if (patch.clinic) {
    if (patch.clinic.name !== undefined) clinic.name = patch.clinic.name.trim();
    if (patch.clinic.address !== undefined) clinic.address = patch.clinic.address?.trim() || null;
    if (patch.clinic.phone !== undefined) clinic.phone = patch.clinic.phone?.trim() || null;
  }
  if (pp) {
    if (pp.currency !== undefined) p.currency = pp.currency.toUpperCase();
    if (pp.timezone !== undefined) p.timezone = pp.timezone;
    if (pp.default_slot_min !== undefined) p.default_slot_min = pp.default_slot_min;
    if (pp.working_hours) {
      // Like the server: the schedule is replaced; days left out are saved as closed.
      p.working_hours = Object.fromEntries(
        DAYS.map((d) => [d, pp.working_hours![d] ?? null])
      ) as WorkingHours;
    }
  }
  return structuredClone(settingsFor(me.clinic_id));
}