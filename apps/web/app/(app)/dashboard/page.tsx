// app/(app)/dashboard/page.tsx  --  TEMPORARY, only to test F4. F6 replaces this file.
"use client";

import { useAuth } from "@/features/auth/auth-provider";
import { fullName } from "@/lib/permissions";
import { Button } from "@/components/ui/button";

export default function TempDashboard() {
  const { user, clinic, logout } = useAuth();
  if (!user || !clinic) return null;

  return (
    <main className="mx-auto max-w-2xl space-y-3 p-6">
      <h1 className="text-2xl font-semibold">Logged in</h1>
      <p className="text-sm text-muted-foreground">
        {fullName(user)} ({user.role}) at {clinic.name}
      </p>
      <Button variant="outline" onClick={logout}>
        Log out
      </Button>
    </main>
  );
}