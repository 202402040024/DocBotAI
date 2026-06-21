"use client";
import { useState, useEffect } from "react";
import { AlertTriangle, X, Loader2 } from "lucide-react";
import { BASE_URL } from "@/services/api";

export function ColdStartBanner() {
  const [status, setStatus] = useState<"checking" | "ok" | "slow">("checking");

  useEffect(() => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    fetch(`${BASE_URL}/health`, { signal: controller.signal })
      .then((r) => setStatus(r.ok ? "ok" : "slow"))
      .catch(() => setStatus("slow"))
      .finally(() => clearTimeout(timeout));
  }, []);

  if (status === "ok" || status === "checking") return null;

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[90vw] max-w-md">
      <div className="flex items-start gap-3 bg-yellow-500/10 border border-yellow-500/40 rounded-xl px-4 py-3 shadow-xl backdrop-blur-sm">
        <AlertTriangle size={16} className="text-yellow-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-yellow-500">Backend is waking up…</p>
          <p className="text-xs text-[var(--muted-foreground)] mt-0.5 leading-relaxed">
            Render free tier sleeps after 15 min of inactivity. First request takes 30–60 seconds. Please wait then retry.
          </p>
        </div>
        <button
          onClick={() => setStatus("ok")}
          className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] flex-shrink-0"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
