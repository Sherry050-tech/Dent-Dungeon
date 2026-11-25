// lib/tokens.ts
const KEY = "dd_tokens";

export type Tokens = { access: string; refresh: string };

// localStorage only exists in the browser. Never call these during server rendering.
export const tokens = {
  get(): Tokens | null {
    if (typeof window === "undefined") return null;
    try {
      return JSON.parse(localStorage.getItem(KEY) ?? "null");
    } catch {
      return null;
    }
  },
  set(t: Tokens) {
    localStorage.setItem(KEY, JSON.stringify(t));
  },
  clear() {
    localStorage.removeItem(KEY);
  },
};