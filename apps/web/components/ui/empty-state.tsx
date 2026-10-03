// components/ui/empty-state.tsx
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode; // e.g. <Button>Add patient</Button>
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-border bg-card px-6 py-16 text-center shadow-sm",
        className
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#CCFBF1] text-[#0F766E]">
        <Icon className="h-6 w-6" strokeWidth={1.75} aria-hidden="true" />
      </div>
      <h2 className="mt-4 text-base font-semibold">{title}</h2>
      {description && (
        <p className="mt-1 max-w-[360px] text-sm text-muted-foreground">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
