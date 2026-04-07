import { useEffect } from "react";

type Handler = () => void;

export function useKeyboard(shortcuts: Record<string, Handler>) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      // Skip if user is typing
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        // Allow command palette shortcut even in inputs
        const meta = e.metaKey || e.ctrlKey;
        if (meta && e.key === "k") {
          e.preventDefault();
          shortcuts["cmd+k"]?.();
        }
        return;
      }

      const key = e.key.toLowerCase();
      const meta = e.metaKey || e.ctrlKey;
      const shift = e.shiftKey;

      const combo = [meta && "cmd", shift && "shift", key].filter(Boolean).join("+");
      if (shortcuts[combo]) {
        e.preventDefault();
        shortcuts[combo]();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [shortcuts]);
}
