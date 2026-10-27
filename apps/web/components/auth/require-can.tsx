// components/auth/require-can.tsx
"use client";

import { ShieldAlert } from "lucide-react";
import { useAuth } from "@/features/auth/auth-provider";
import { can, type Action } from "@/lib/permissions";
import { EmptyState } from "@/components/ui/empty-state";

export function RequireCan({
  action,
  children,
  description = "Only clinic admins can manage staff.",
}: {
  action: Action;
  children: React.ReactNode;
  description?: string;
}) {
  const { user } = useAuth();

  if (!can(user, action)) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title="You do not have access to this page"
        description={description}
      />
    );
  }
  return <>{children}</>;
}