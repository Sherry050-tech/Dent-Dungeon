// types/api.ts  (from Part 6 of the updated plan, plus StaffFilters)
export type Role = "admin" | "doctor" | "receptionist";

export interface User {
  id: string;
  clinic_id: string;
  first_name: string;
  last_name: string;
  email: string;
  role: Role;
  is_practitioner: boolean;
  is_active: boolean;
}

export interface Clinic {
  id: string;
  name: string;
  address: string | null;
  phone: string | null;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
  clinic: Clinic;
}

export interface MeResponse {
  user: User;
  clinic: Clinic;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}

export interface RegisterInput {
  clinic_name: string;
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  is_practitioner: boolean;
}

export interface CreateStaffInput {
  first_name: string;
  last_name: string;
  email: string;
  temporary_password: string;
  role: Role;
  is_practitioner: boolean;
}

export interface UpdateStaffInput {
  first_name?: string;
  last_name?: string;
  role?: Role;
  is_practitioner?: boolean;
  is_active?: boolean;
}

export interface StaffFilters {
  role?: Role;
  is_active?: boolean;
  page?: number;
  limit?: number;
}

export type Weekday = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun";
export type DayHours = [string, string] | null; // ["09:00","17:00"] or null = closed
export type WorkingHours = Record<Weekday, DayHours>;

export interface Preferences {
  currency: string;
  timezone: string;
  default_slot_min: number;
  working_hours: WorkingHours;
}

export interface ClinicSettings {
  clinic: Clinic;
  preferences: Preferences;
}

export interface ClinicSettingsPatch {
  clinic?: { name?: string; address?: string | null; phone?: string | null };
  preferences?: {
    currency?: string;
    timezone?: string;
    default_slot_min?: number;
    working_hours?: Partial<WorkingHours>;
  };
}