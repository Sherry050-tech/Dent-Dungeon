// app/(app)/layout.tsx  (guard only; F6 replaces <>{children}</> with the sidebar + top bar shell)
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/auth-provider";
import { FullPageSkeleton } from "@/components/layout/full-page-skeleton";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);

  // loading, or anonymous and about to be redirected: never render private pages
  if (status !== "authenticated") return <FullPageSkeleton />;

  return <>{children}</>;
}