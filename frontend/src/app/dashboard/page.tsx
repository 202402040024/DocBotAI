"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { FileText, MessageSquare, HelpCircle, Database, TrendingUp, Clock } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { dashboardService } from "@/services/dashboard.service";
import { useAuthStore } from "@/store/useAuthStore";
import { authService } from "@/services/auth.service";
import { formatDate, fileIcon } from "@/lib/utils";

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, setUser, user } = useAuthStore();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) { router.replace("/auth/login"); return; }
    if (!isAuthenticated) authService.getMe().then(setUser).catch(() => router.replace("/auth/login"));
  }, [router, isAuthenticated, setUser]);

  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: dashboardService.getStats,
    refetchInterval: 30000,
  });

  const statCards = [
    { label: "Documents", value: stats?.total_documents ?? 0, icon: FileText, color: "text-blue-500", bg: "bg-blue-500/10" },
    { label: "Chat Sessions", value: stats?.total_chats ?? 0, icon: MessageSquare, color: "text-purple-500", bg: "bg-purple-500/10" },
    { label: "Questions Asked", value: stats?.total_questions ?? 0, icon: HelpCircle, color: "text-green-500", bg: "bg-green-500/10" },
    { label: "RAG Retrievals", value: stats?.retrieval_count ?? 0, icon: Database, color: "text-orange-500", bg: "bg-orange-500/10" },
    { label: "Searches", value: stats?.searches_performed ?? 0, icon: TrendingUp, color: "text-pink-500", bg: "bg-pink-500/10" },
  ];

  return (
    <AppLayout>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-6 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-[var(--foreground)]">Dashboard</h1>
            <p className="text-sm text-[var(--muted-foreground)] mt-1">
              Welcome back, {user?.name?.split(" ")[0]}! Here's your AI activity overview.
            </p>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-16">
              <div className="w-8 h-8 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <>
              {/* Stats grid */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
                {statCards.map(({ label, value, icon: Icon, color, bg }) => (
                  <div key={label} className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
                    <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center mb-3`}>
                      <Icon size={20} className={color} />
                    </div>
                    <p className="text-2xl font-bold text-[var(--foreground)]">{value.toLocaleString()}</p>
                    <p className="text-xs text-[var(--muted-foreground)] mt-0.5">{label}</p>
                  </div>
                ))}
              </div>

              {/* Recent activity */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Recent uploads */}
                <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
                  <h2 className="text-sm font-semibold text-[var(--foreground)] mb-4 flex items-center gap-2">
                    <Clock size={14} className="text-[var(--muted-foreground)]" />
                    Recent Uploads
                  </h2>
                  {stats?.recent_uploads.length === 0 ? (
                    <p className="text-xs text-[var(--muted-foreground)] text-center py-4">No uploads yet</p>
                  ) : (
                    <div className="flex flex-col gap-2">
                      {stats?.recent_uploads.map((doc) => (
                        <div key={doc.id || doc.original_filename} className="flex items-center gap-3 py-2 border-b border-[var(--border)] last:border-0">
                          <span className="text-lg">{fileIcon(doc.file_type)}</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-[var(--foreground)] truncate">{doc.original_filename}</p>
                            <p className="text-xs text-[var(--muted-foreground)]">{formatDate(doc.upload_time)}</p>
                          </div>
                          <span className="text-xs bg-[var(--secondary)] px-1.5 py-0.5 rounded uppercase text-[var(--muted-foreground)]">{doc.file_type}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Recent conversations */}
                <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
                  <h2 className="text-sm font-semibold text-[var(--foreground)] mb-4 flex items-center gap-2">
                    <MessageSquare size={14} className="text-[var(--muted-foreground)]" />
                    Recent Conversations
                  </h2>
                  {stats?.recent_conversations.length === 0 ? (
                    <p className="text-xs text-[var(--muted-foreground)] text-center py-4">No conversations yet</p>
                  ) : (
                    <div className="flex flex-col gap-2">
                      {stats?.recent_conversations.map((chat) => (
                        <div key={chat.id || (chat as unknown as Record<string,string>)._id} className="flex items-center gap-3 py-2 border-b border-[var(--border)] last:border-0">
                          <div className="w-7 h-7 rounded-lg bg-[var(--secondary)] flex items-center justify-center flex-shrink-0">
                            <MessageSquare size={12} className="text-[var(--muted-foreground)]" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-[var(--foreground)] truncate">{chat.title}</p>
                            <p className="text-xs text-[var(--muted-foreground)]">{formatDate(chat.updated_at)}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
