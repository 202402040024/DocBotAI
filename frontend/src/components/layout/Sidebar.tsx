"use client";
import { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import {
  Plus, Search, MessageSquare, FileText, LayoutDashboard,
  Settings, LogOut, Trash2, Edit2, Check, X, Bot,
  ChevronLeft, ChevronRight, PanelLeftClose, PanelLeft
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { chatService } from "@/services/chat.service";
import { authService } from "@/services/auth.service";
import { useChatStore } from "@/store/useChatStore";
import { useAuthStore } from "@/store/useAuthStore";
import { Button } from "@/components/ui/Button";
import { cn, truncate } from "@/lib/utils";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { sessions, setSessions, activeSessionId, setActiveSession, removeSession, renameSession } = useChatStore();
  const { user, logout } = useAuthStore();
  const [searchQuery, setSearchQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    chatService.getSessions(searchQuery || undefined).then(setSessions).catch(() => {});
  }, [searchQuery, setSessions]);

  const handleNewChat = () => {
    setActiveSession(null);
    router.push("/chat");
  };

  const handleSelectSession = (id: string) => {
    setActiveSession(id);
    router.push(`/chat?session=${id}`);
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    await chatService.deleteSession(id);
    removeSession(id);
    if (activeSessionId === id) { setActiveSession(null); router.push("/chat"); }
  };

  const handleStartEdit = (e: React.MouseEvent, id: string, title: string) => {
    e.stopPropagation();
    setEditingId(id);
    setEditTitle(title);
  };

  const handleSaveEdit = async (id: string) => {
    if (!editTitle.trim()) { setEditingId(null); return; }
    await chatService.renameSession(id, editTitle.trim());
    renameSession(id, editTitle.trim());
    setEditingId(null);
  };

  const handleLogout = async () => {
    await authService.logout();
    logout();
    router.push("/auth/login");
  };

  const navItems = [
    { href: "/chat", icon: MessageSquare, label: "Chat" },
    { href: "/documents", icon: FileText, label: "Documents" },
    { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { href: "/settings", icon: Settings, label: "Settings" },
  ];

  // Group sessions by date
  const today = new Date(); today.setHours(0,0,0,0);
  const yesterday = new Date(today); yesterday.setDate(yesterday.getDate()-1);
  const week = new Date(today); week.setDate(week.getDate()-7);

  const groupLabel = (dateStr: string) => {
    const d = new Date(dateStr);
    if (d >= today) return "Today";
    if (d >= yesterday) return "Yesterday";
    if (d >= week) return "This week";
    return "Older";
  };

  const grouped = sessions.reduce<Record<string, typeof sessions>>((acc, s) => {
    const label = groupLabel(s.updated_at);
    if (!acc[label]) acc[label] = [];
    acc[label].push(s);
    return acc;
  }, {});

  const GROUP_ORDER = ["Today", "Yesterday", "This week", "Older"];

  return (
    <motion.aside
      animate={{ width: collapsed ? 56 : 260 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="flex flex-col h-full bg-[var(--sidebar-bg)] border-r border-[var(--sidebar-border)] overflow-hidden flex-shrink-0"
    >
      {/* ── Brand header ── */}
      <div className="flex items-center h-12 px-3 border-b border-[var(--border)] flex-shrink-0">
        {!collapsed && (
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-[var(--primary)] flex items-center justify-center flex-shrink-0">
              <Bot size={14} className="text-white" />
            </div>
            <span className="text-sm font-semibold text-[var(--foreground)] truncate">DocBot AI</span>
          </div>
        )}
        <button
          onClick={onToggle}
          className={cn(
            "text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors p-1.5 rounded-md hover:bg-[var(--accent)]",
            collapsed && "mx-auto"
          )}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
        </button>
      </div>

      {/* ── Navigation ── */}
      <div className="px-2 py-2 border-b border-[var(--border)] flex-shrink-0">
        {navItems.map(({ href, icon: Icon, label }) => {
          const active = pathname === href || (href !== "/chat" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              className={cn(
                "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors mb-0.5",
                active
                  ? "bg-[var(--primary)] text-white"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)]",
                collapsed && "justify-center px-0"
              )}
            >
              <Icon size={16} className="flex-shrink-0" />
              {!collapsed && <span>{label}</span>}
            </Link>
          );
        })}
      </div>

      {/* ── New chat + search ── */}
      {!collapsed && (
        <div className="px-2 pt-3 pb-1 flex-shrink-0">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-dashed border-[var(--border)] text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:border-[var(--primary)]/50 hover:bg-[var(--primary)]/5 transition-all"
          >
            <Plus size={13} className="flex-shrink-0" />
            <span>New conversation</span>
          </button>

          {/* Search toggle */}
          <div className="mt-2">
            {searchOpen ? (
              <div className="relative">
                <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" />
                <input
                  autoFocus
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onBlur={() => { if (!searchQuery) setSearchOpen(false); }}
                  placeholder="Search chats…"
                  className="w-full h-7 rounded-lg bg-[var(--secondary)] border border-[var(--border)] pl-7 pr-7 text-xs text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] outline-none focus:border-[var(--primary)]"
                />
                {searchQuery && (
                  <button onClick={() => { setSearchQuery(""); setSearchOpen(false); }} className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]">
                    <X size={11} />
                  </button>
                )}
              </div>
            ) : (
              <button
                onClick={() => setSearchOpen(true)}
                className="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)] px-1 py-1 transition-colors"
              >
                <Search size={12} /> Search chats
              </button>
            )}
          </div>
        </div>
      )}

      {/* Collapsed: new chat icon */}
      {collapsed && (
        <div className="px-2 py-2 flex-shrink-0">
          <button
            onClick={handleNewChat}
            title="New chat"
            className="w-full flex justify-center p-2 rounded-lg text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)] transition-colors"
          >
            <Plus size={16} />
          </button>
        </div>
      )}

      {/* ── Sessions list ── */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto px-2 pb-2 mt-1">
          <AnimatePresence>
            {sessions.length === 0 ? (
              <p className="text-xs text-[var(--muted-foreground)] text-center mt-10 px-4">
                No conversations yet
              </p>
            ) : (
              GROUP_ORDER.filter(g => grouped[g]?.length).map((groupName) => (
                <div key={groupName}>
                  <p className="text-xs font-medium text-[var(--muted-foreground)] px-2 py-1.5 mt-1 uppercase tracking-wide opacity-60">
                    {groupName}
                  </p>
                  {grouped[groupName].map((session) => (
                    <motion.div
                      key={session.id}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -6 }}
                      className={cn(
                        "group flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer transition-colors mb-0.5",
                        activeSessionId === session.id
                          ? "bg-[var(--accent)] text-[var(--foreground)]"
                          : "text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
                      )}
                      onClick={() => handleSelectSession(session.id)}
                    >
                      <MessageSquare size={13} className="flex-shrink-0 opacity-70" />

                      {editingId === session.id ? (
                        <input
                          autoFocus
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleSaveEdit(session.id);
                            if (e.key === "Escape") setEditingId(null);
                          }}
                          className="flex-1 text-xs bg-[var(--background)] border border-[var(--border)] rounded px-1.5 py-0.5 outline-none text-[var(--foreground)] min-w-0"
                        />
                      ) : (
                        <span className="flex-1 text-xs truncate">{session.title}</span>
                      )}

                      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                        {editingId === session.id ? (
                          <>
                            <button onClick={(e) => { e.stopPropagation(); handleSaveEdit(session.id); }} className="p-0.5 text-green-500 hover:text-green-400">
                              <Check size={11} />
                            </button>
                            <button onClick={(e) => { e.stopPropagation(); setEditingId(null); }} className="p-0.5 hover:text-[var(--destructive)]">
                              <X size={11} />
                            </button>
                          </>
                        ) : (
                          <>
                            <button onClick={(e) => handleStartEdit(e, session.id, session.title)} className="p-0.5 hover:text-[var(--foreground)]" title="Rename">
                              <Edit2 size={11} />
                            </button>
                            <button onClick={(e) => handleDelete(e, session.id)} className="p-0.5 hover:text-[var(--destructive)]" title="Delete">
                              <Trash2 size={11} />
                            </button>
                          </>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              ))
            )}
          </AnimatePresence>
        </div>
      )}

      {collapsed && <div className="flex-1" />}

      {/* ── User footer ── */}
      <div className="border-t border-[var(--border)] p-2 flex-shrink-0">
        {!collapsed ? (
          <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[var(--accent)] transition-colors">
            <div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              {user?.name?.[0]?.toUpperCase() || "?"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-[var(--foreground)] truncate">{user?.name}</p>
              <p className="text-xs text-[var(--muted-foreground)] truncate">{truncate(user?.email || "", 24)}</p>
            </div>
            <Button variant="ghost" size="icon" onClick={handleLogout} className="h-7 w-7 flex-shrink-0 ml-1" title="Logout">
              <LogOut size={13} />
            </Button>
          </div>
        ) : (
          <Button variant="ghost" size="icon" onClick={handleLogout} className="w-full h-9" title="Logout">
            <LogOut size={14} />
          </Button>
        )}
      </div>
    </motion.aside>
  );
}
