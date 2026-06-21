"use client";
import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppLayout } from "@/components/layout/AppLayout";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { useChatStore } from "@/store/useChatStore";
import { useAuthStore } from "@/store/useAuthStore";
import { authService } from "@/services/auth.service";

function ChatPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionIdParam = searchParams.get("session");
  const { activeSessionId, setActiveSession } = useChatStore();
  const { setUser, isAuthenticated } = useAuthStore();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) { router.replace("/auth/login"); return; }
    if (!isAuthenticated) {
      authService.getMe().then(setUser).catch(() => router.replace("/auth/login"));
    }
  }, [router, isAuthenticated, setUser]);

  useEffect(() => {
    if (sessionIdParam && sessionIdParam !== activeSessionId) {
      setActiveSession(sessionIdParam);
    } else if (!sessionIdParam && activeSessionId) {
      setActiveSession(null);
    }
  }, [sessionIdParam, activeSessionId, setActiveSession]);

  const handleNewSession = (id: string) => {
    router.push(`/chat?session=${id}`, { scroll: false });
  };

  return (
    <AppLayout>
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <ChatWindow
          sessionId={activeSessionId}
          onNewSession={handleNewSession}
        />
      </div>
    </AppLayout>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="w-8 h-8 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" /></div>}>
      <ChatPageContent />
    </Suspense>
  );
}
