// app/(auth)/register/page.tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/features/auth/auth-provider";
import { registerSchema, type RegisterValues } from "@/features/auth/schemas";
import { handleAuthError } from "@/features/auth/errors";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/ui/password-input";
import { FieldError, FormBanner } from "@/components/ui/form-feedback";

const FIELD_NAMES = [
  "clinic_name",
  "first_name",
  "last_name",
  "email",
  "password",
  "is_practitioner",
] as const;

function passwordHint(p: string): { text: string; tone: string } {
  if (!p) return { text: "Use at least 8 characters.", tone: "text-muted-foreground" };
  if (p.length < 8) return { text: "Too short. Use at least 8 characters.", tone: "text-destructive" };
  const variety = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((r) => r.test(p)).length;
  if (p.length >= 12 && variety >= 3) return { text: "Strong password.", tone: "text-[#15803D]" };
  if (variety >= 3) return { text: "Good password.", tone: "text-[#15803D]" };
  return { text: "Okay. Add numbers or symbols to make it stronger.", tone: "text-[#B45309]" };
}

export default function RegisterPage() {
  const { register: registerClinic } = useAuth();
  const [banner, setBanner] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      clinic_name: "",
      first_name: "",
      last_name: "",
      email: "",
      password: "",
      confirm: "",
      is_practitioner: false,
    },
  });

  const hint = passwordHint(watch("password"));

  async function onSubmit(values: RegisterValues) {
    setBanner(null);
    const { confirm, ...input } = values;
    void confirm; // only used for the "passwords match" check
    try {
      await registerClinic(input); // already logged in; the provider goes to /dashboard
      toast.success("Welcome to Dent-Dungeon. Your clinic is ready.");
    } catch (err) {
      setBanner(handleAuthError(err, setError, FIELD_NAMES));
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight">Create your clinic</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Set up Dent-Dungeon for your practice in a minute.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4">
        {banner && <FormBanner message={banner} />}

        <div className="space-y-1.5">
          <Label htmlFor="clinic_name">Clinic name</Label>
          <Input
            id="clinic_name"
            autoFocus
            autoComplete="organization"
            placeholder="Bright Smile Dental"
            aria-invalid={!!errors.clinic_name}
            {...register("clinic_name")}
          />
          <FieldError message={errors.clinic_name?.message} />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="first_name">First name</Label>
            <Input
              id="first_name"
              autoComplete="given-name"
              aria-invalid={!!errors.first_name}
              {...register("first_name")}
            />
            <FieldError message={errors.first_name?.message} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="last_name">Last name</Label>
            <Input
              id="last_name"
              autoComplete="family-name"
              aria-invalid={!!errors.last_name}
              {...register("last_name")}
            />
            <FieldError message={errors.last_name?.message} />
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="sara@clinic.com"
            aria-invalid={!!errors.email}
            {...register("email")}
          />
          <FieldError message={errors.email?.message} />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <PasswordInput
            id="password"
            autoComplete="new-password"
            aria-invalid={!!errors.password}
            {...register("password")}
          />
          {errors.password ? (
            <FieldError message={errors.password.message} />
          ) : (
            <p className={`text-xs ${hint.tone}`}>{hint.text}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="confirm">Confirm password</Label>
          <PasswordInput
            id="confirm"
            autoComplete="new-password"
            aria-invalid={!!errors.confirm}
            {...register("confirm")}
          />
          <FieldError message={errors.confirm?.message} />
        </div>

        <div className="flex items-start gap-3 rounded-lg border border-border bg-card p-3">
          <Controller
            name="is_practitioner"
            control={control}
            render={({ field }) => (
              <Checkbox
                id="is_practitioner"
                checked={field.value}
                onCheckedChange={(v) => field.onChange(v === true)}
                className="mt-0.5"
              />
            )}
          />
          <div className="space-y-0.5">
            <Label htmlFor="is_practitioner" className="cursor-pointer">
              I also treat patients
            </Label>
            <p className="text-xs text-muted-foreground">
              Choose this if you are a dentist who sees patients yourself. You can
              change it later.
            </p>
          </div>
        </div>

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="animate-spin" aria-hidden="true" />}
          {isSubmitting ? "Creating your clinic..." : "Create my clinic"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}