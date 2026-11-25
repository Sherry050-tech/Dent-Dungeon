// components/ui/stat-card.tsx
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  note,
  noteTone = "muted",
  icon: Icon,
  className,
}: {
  label: string;
  value: string | number;
  note?: string;
  noteTone?: "muted" | "success";
  icon: LucideIcon;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card p-5 shadow-sm",
        className
      )}
    >
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#CCFBF1] text-[#0F766E]">
          <Icon className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
        </div>
        <span className="text-[13px] font-medium text-muted-foreground">
          {label}
        </span>
      </div>
      <div className="mt-4 text-[28px] font-bold leading-none tracking-tight tabular-nums">
        {value}
      </div>
      {note && (
        <p
          className={cn(
            "mt-2 text-xs",
            noteTone === "success" ? "text-[#16A34A]" : "text-muted-foreground"
          )}
        >
          {note}
        </p>
      )}
    </div>
  );
}
