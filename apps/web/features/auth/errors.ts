// features/auth/errors.ts
// Turns an API error into field errors (shown under inputs) and an optional banner message.
import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { ApiError } from "@/lib/api";

const GENERIC = "Something went wrong. Please try again.";

/**
 * Sets field errors on the form and returns a banner message,
 * or null when everything was shown under a field.
 * `fieldNames` = the form's own field names; server keys not in it go to the banner.
 */
export function handleAuthError<T extends FieldValues>(
  err: unknown,
  setError: UseFormSetError<T>,
  fieldNames: readonly string[]
): string | null {
  if (!(err instanceof ApiError)) return GENERIC;

  if (err.status === 0) return "Cannot reach the server. Check your connection.";

  switch (err.code) {
    case "INVALID_CREDENTIALS":
      return "Email or password is incorrect.";
    case "ACCOUNT_INACTIVE":
      return "This account has been deactivated. Contact your clinic administrator.";
    case "EMAIL_TAKEN":
      setError("email" as Path<T>, { message: "This email is already registered." });
      return null;
    case "VALIDATION_ERROR": {
      const leftovers: string[] = [];
      for (const [key, message] of Object.entries(err.fields)) {
        if (fieldNames.includes(key)) {
          setError(key as Path<T>, { message });
        } else {
          leftovers.push(message);
        }
      }
      return leftovers.length ? leftovers.join(" ") : null;
    }
    default:
      return err.status >= 500 ? GENERIC : err.message;
  }
}