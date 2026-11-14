import { useEffect, useState } from "react";

/**
 * Returns a className ("recently-updated" or "") that is briefly applied
 * for ~2 seconds whenever `key` changes. Pair with `.recently-updated` from
 * `micro-animations.css` to trigger a glow pulse on value updates.
 */
export function useRecentlyUpdated(key: unknown, durationMs: number = 2000): string {
  const [cls, setCls] = useState("");
  useEffect(() => {
    if (key === null || key === undefined) return;
    setCls("recently-updated");
    const t = setTimeout(() => setCls(""), durationMs);
    return () => clearTimeout(t);
  }, [key, durationMs]);
  return cls;
}

export default useRecentlyUpdated;
