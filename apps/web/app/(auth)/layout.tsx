// app/(auth)/layout.tsx  (updated for F5: guard + split-screen)
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/auth-provider";
import { FullPageSkeleton } from "@/components/layout/full-page-skeleton";
import { Logo } from "@/components/layout/logo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") router.replace("/dashboard");
  }, [status, router]);

  // Only show login / register to people who are logged out.
  if (status !== "anonymous") return <FullPageSkeleton />;

  return (
    <div className="flex min-h-screen bg-background">
      {/* Brand panel: hidden below 1024px */}
      <aside className="relative hidden w-[45%] flex-col justify-between overflow-hidden bg-linear-to-br from-[#0F766E] to-primary p-12 text-white lg:flex">
        <div
          aria-hidden="true"
          className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-white/10"
        />
        <div
          aria-hidden="true"
          className="absolute -bottom-32 -left-20 h-[28rem] w-[28rem] rounded-full bg-white/10"
        />
        <Logo light className="relative" />
        <div className="relative">
          <h2 className="text-4xl font-semibold leading-tight tracking-tight">
            Smart care.
            <br />
            Simple clinic.
          </h2>
          <p className="mt-4 max-w-sm text-base text-white/80">
            Patients, appointments, charts and billing in one calm place.
          </p>
        </div>
        <p className="relative text-sm text-white/60">Dent-Dungeon</p>
      </aside>

      {/* Form side */}
      <main className="flex min-h-screen flex-1 items-center justify-center px-4 py-10 sm:px-6">
        <div className="w-full max-w-[400px]">
          <Logo className="mb-8 lg:hidden" />
          {children}
        </div>
      </main>
    </div>
  );
}