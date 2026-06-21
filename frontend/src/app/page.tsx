"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";
import { authService } from "@/services/auth.service";
import { Bot, AlertTriangle, RefreshCw } from "lucide-react";

export default function RootPage() {
  const router = useRouter();
  const { setUser } = useAuthStore();
  const [backendDown, setBackendDown] = useState(false);

  const tryConnect = () => {
    setBackendDown(false);
    const token = localStorage.getItem("access_token");
    if (!token) { router.replace("/auth/login"); return; }
    authService.getMe()
      .then((user) => { setUser(user); router.replace("/chat"); })
      .catch((err) => {
        // Network error = backend not running
        if (!err.response) { setBackendDown(true); }
        else { router.replace("/auth/login"); }
      });
  };

  useEffect(() => { tryConnect(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (backendDown) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--background)] p-4">
        <div className="max-w-sm w-full text-center flex flex-col items-center gap-5">
          <div className="w-14 h-14 rounded-2xl bg-[var(--primary)]/10 flex items-center justify-center">
            <Bot size={28} className="text-[var(--primary)]" />
          </div>
          <div>
            <div className="flex items-center justify-center gap-2 text-yellow-500 mb-2">
              <AlertTriangle size={16} />
              <span className="text-sm font-semibold">Backend not reachable</span>
            </div>
            <p className="text-sm text-[var(--muted-foreground)]">
              Cannot reach the API server at:<br />
              <code className="bg-[var(--secondary)] px-1 rounded text-xs break-all">
                {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
              </code>
            </p>
            <p className="text-xs text-[var(--muted-foreground)] mt-3 bg-[var(--secondary)] rounded-lg p-3 text-left">
              If you are on <strong>Vercel</strong>, make sure the{" "}
              <code className="bg-black/20 px-1 rounded">NEXT_PUBLIC_API_URL</code> environment variable
              is set to your Render backend URL in the Vercel dashboard, then redeploy.
            </p>
          </div>
          <button
            onClick={tryConnect}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--primary)] text-white text-sm hover:opacity-90 transition-opacity"
          >
            <RefreshCw size={14} /> Retry connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--background)]">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-[var(--primary)] flex items-center justify-center">
          <Bot size={20} className="text-white" />
        </div>
        <div className="w-6 h-6 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-[var(--muted-foreground)]">Connecting…</p>
      </div>
    </div>
  );
}
