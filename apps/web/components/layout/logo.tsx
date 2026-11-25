// components/layout/logo.tsx
import { cn } from "@/lib/utils";

export function Logo({
  className,
  light = false,
}: {
  className?: string;
  light?: boolean; // true on the teal brand panel (white text and chip)
}) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <div
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-lg",
          light ? "bg-white/20" : "bg-primary"
        )}
      >
        <svg
          viewBox="0 0 24 24"
          className="h-5 w-5 text-white"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.75}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M7 3.5C4.5 3.5 3.5 6 4.5 9c.6 1.8 1 3.5 1.2 5.5.2 2.5.7 6 2.3 6 1.4 0 1.2-3.5 4-3.5s2.6 3.5 4 3.5c1.6 0 2.1-3.5 2.3-6 .2-2 .6-3.7 1.2-5.5 1-3 0-5.5-2.5-5.5-1.8 0-2.5.8-5 .8S8.8 3.5 7 3.5z" />
        </svg>
      </div>
      <span
        className={cn(
          "text-lg font-semibold tracking-tight",
          light ? "text-white" : "text-foreground"
        )}
      >
        Dent-Dungeon
      </span>
    </div>
  );
}
