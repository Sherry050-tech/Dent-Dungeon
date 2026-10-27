// app/providers.tsx  (updated for F4: AuthProvider added)
"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/features/auth/auth-provider";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {/* AuthProvider must sit INSIDE QueryClientProvider: it clears the cache on logout */}
      <AuthProvider>{children}</AuthProvider>
      <Toaster position="bottom-right" duration={3000} />
    </QueryClientProvider>
  );
}