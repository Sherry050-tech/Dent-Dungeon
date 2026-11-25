// components/ui/status-badge.tsx  (updated: no "pending", added "inactive")
import { cn } from "@/lib/utils";

// Colors come from the badge table in Part 7.2 (soft background + dark text).
const STYLES = {
  scheduled: { label: "Scheduled", cls: "bg-[#E0F2FE] text-[#0369A1]" },
  confirmed: { label: "Confirmed", cls: "bg-[#CCFBF1] text-[#0F766E]" },
  in_progress: { label: "In progress", cls: "bg-[#FEF3C7] text-[#B45309]" },
  completed: { label: "Completed", cls: "bg-[#DCFCE7] text-[#15803D]" },
  cancelled: { label: "Cancelled", cls: "bg-[#F1F5F9] text-[#475569]" },
  no_show: { label: "No show", cls: "bg-[#FFE4E6] text-[#BE123C]" },
  active: { label: "Active", cls: "bg-[#DCFCE7] text-[#15803D]" },
  inactive: { label: "Deactivated", cls: "bg-[#F1F5F9] text-[#475569]" },
  admin: { label: "Admin", cls: "bg-[#EDE9FE] text-[#6D28D9]" },
  doctor: { label: "Doctor", cls: "bg-[#CCFBF1] text-[#0F766E]" },
  receptionist: { label: "Receptionist", cls: "bg-[#E0F2FE] text-[#0369A1]" },
} as const;

export type BadgeStatus = keyof typeof STYLES;

export function StatusBadge({
  status,
  className,
}: {
  status: BadgeStatus;
  className?: string;
}) {
  const s = STYLES[status];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        s.cls,
        className
      )}
    >
      {s.label}
    </span>
  );
}