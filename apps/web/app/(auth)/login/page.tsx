// app/(auth)/login/page.tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/features/auth/auth-provider";
import { loginSchema, type LoginValues } from "@/features/auth/schemas";
import { handleAuthError } from "@/features/auth/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/ui/password-input";
import { FieldError, FormBanner } from "@/components/ui/form-feedback";

export default function LoginPage() {
  const { login } = useAuth();
  const [banner, setBanner] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    resetField,
    setFocus,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: LoginValues) {
    setBanner(null);
    try {
      await login(values.email, values.password); // on success the provider goes to /dashboard
    } catch (err) {
      setBanner(handleAuthError(err, setError, ["email", "password"]));
      if (err instanceof ApiError && err.code === "INVALID_CREDENTIALS") {
        resetField("password"); // keep the email, clear the password
        setFocus("password");
      }
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Sign in to your clinic account
      </p>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4">
        {banner && <FormBanner message={banner} />}

        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            autoFocus
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
            autoComplete="current-password"
            placeholder="Your password"
            aria-invalid={!!errors.password}
            {...register("password")}
          />
          <FieldError message={errors.password?.message} />
        </div>

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="animate-spin" aria-hidden="true" />}
          {isSubmitting ? "Signing in..." : "Sign in"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        New to Dent-Dungeon?{" "}
        <Link href="/register" className="font-medium text-primary hover:underline">
          Create your clinic
        </Link>
      </p>
    </div>
  );
}