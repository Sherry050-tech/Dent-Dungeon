// features/auth/schemas.ts
// Same rules as the server. The server is still the authority: its errors are mapped too.
import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});
export type LoginValues = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    clinic_name: z.string().trim().min(2, "Enter your clinic name").max(150),
    first_name: z.string().trim().min(1, "Enter your first name").max(80),
    last_name: z.string().trim().min(1, "Enter your last name").max(80),
    email: z.string().trim().email("Enter a valid email address"),
    password: z.string().min(8, "Use at least 8 characters").max(128),
    confirm: z.string(),
    is_practitioner: z.boolean(),
  })
  .refine((d) => d.password === d.confirm, {
    path: ["confirm"],
    message: "Passwords do not match",
  });
export type RegisterValues = z.infer<typeof registerSchema>;