// components/layout/full-page-skeleton.tsx
import { Skeleton } from "@/components/ui/skeleton";

// Shown while the session is being restored, so nobody sees a flash of the wrong page.
export function FullPageSkeleton() {
  return (
    <div className="flex min-h-screen bg-background" aria-busy="true" aria-label="Loading">
      <aside className="hidden w-64 shrink-0 border-r border-border bg-card p-4 lg:block">
        <Skeleton className="h-8 w-40" />
        <div className="mt-8 space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      </aside>
      <div className="flex-1">
        <div className="h-16 border-b border-border bg-card px-6">
          <Skeleton className="mt-4 h-8 w-56" />
        </div>
        <div className="space-y-6 p-4 sm:p-6">
          <Skeleton className="h-9 w-64" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    </div>
  );
}