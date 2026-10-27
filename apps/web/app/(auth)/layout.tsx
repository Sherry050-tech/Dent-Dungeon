// app/(auth)/layout.tsx  (guard only; F5 adds the split-screen brand panel around {children})
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/auth-provider";
import { FullPageSkeleton } from "@/components/layout/full-page-skeleton";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") router.replace("/dashboard");
  }, [status, router]);

  // Only show login / register to people who are logged out.
  if (status !== "anonymous") return <FullPageSkeleton />;

  return <>{children}</>;
}