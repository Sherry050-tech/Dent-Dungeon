// components/ui/form-feedback.tsx
import { AlertCircle } from "lucide-react";

// Error for the whole form (wrong password, server down...).
export function FormBanner({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-lg border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

// Error under one input.
export function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return (
    <p role="alert" className="text-xs text-destructive">
      {message}
    </p>
  );
}