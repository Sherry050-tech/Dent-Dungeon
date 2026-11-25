// components/ui/password-input.tsx
"use client";

import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

// Works with react-hook-form's register(): ref and handlers pass straight through props.
export function PasswordInput({
  className,
  ...props
}: React.ComponentProps<"input">) {
  const [show, setShow] = useState(false);

  return (
    <div className="relative">
      <Input
        {...props}
        type={show ? "text" : "password"}
        className={cn("pr-10", className)}
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        aria-label={show ? "Hide password" : "Show password"}
        className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md p-2 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {show ? (
          <EyeOff className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
        ) : (
          <Eye className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
        )}
      </button>
    </div>
  );
}