"use client";
import { useState } from "react";
import { Download, MoreHorizontal, Trash2, Edit2, Check, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { ChatSession, ChatMessage } from "@/types";
import { Button } from "@/components/ui/Button";
import { chatService } from "@/services/chat.service";
import { useChatStore } from "@/store/useChatStore";
import { useRouter } from "next/navigation";

interface ChatHeaderProps {
  session: ChatSession | null;
  messages: ChatMessage[];
}

export function ChatHeader({ session, messages }: ChatHeaderProps) {
  const router = useRouter();
  const { renameSession, removeSession, setActiveSession } = useChatStore();
  const [menuOpen, setMenuOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(session?.title || "");

  if (!session) return null;

  const handleRename = async () => {
    if (!title.trim() || title === session.title) { setEditing(false); return; }
    await chatService.renameSession(session.id, title.trim());
    renameSession(session.id, title.trim());
    setEditing(false);
  };

  const handleDelete = async () => {
    await chatService.deleteSession(session.id);
    removeSession(session.id);
    setActiveSession(null);
    router.push("/chat");
  };

  const exportAsTxt = () => {
    const lines = messages.map((m) =>
      `[${new Date(m.timestamp).toLocaleString()}] ${m.role.toUpperCase()}\n${m.content}\n`
    );
    const blob = new Blob([lines.join("\n---\n\n")], { type: "text/plain" });
    download(blob, `${session.title}.txt`);
  };

  const exportAsJson = () => {
    const data = { session, messages };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    download(blob, `${session.title}.json`);
  };

  const download = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] bg-[var(--background)] flex-shrink-0">
      <div className="flex items-center gap-2 flex-1 min-w-0">
        {editing ? (
          <div className="flex items-center gap-2 flex-1">
            <input
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleRename(); if (e.key === "Escape") setEditing(false); }}
              className="flex-1 text-sm bg-[var(--secondary)] border border-[var(--primary)] rounded-lg px-3 py-1.5 text-[var(--foreground)] outline-none"
            />
            <button onClick={handleRename} className="text-green-500 hover:text-green-400"><Check size={15} /></button>
            <button onClick={() => setEditing(false)} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]"><X size={15} /></button>
          </div>
        ) : (
          <h1 className="text-sm font-medium text-[var(--foreground)] truncate max-w-xs">{session.title}</h1>
        )}
      </div>

      <div className="flex items-center gap-1">
        {/* Export dropdown */}
        <div className="relative">
          <Button variant="ghost" size="icon" onClick={() => setMenuOpen(!menuOpen)} title="Options">
            <MoreHorizontal size={16} />
          </Button>
          <AnimatePresence>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: -4 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="absolute right-0 top-10 z-20 w-48 rounded-xl border border-[var(--border)] bg-[var(--card)] shadow-xl py-1"
                >
                  <p className="px-3 py-1 text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wide">Export</p>
                  <button onClick={() => { exportAsTxt(); setMenuOpen(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[var(--foreground)] hover:bg-[var(--accent)]">
                    <Download size={13} /> Export as TXT
                  </button>
                  <button onClick={() => { exportAsJson(); setMenuOpen(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[var(--foreground)] hover:bg-[var(--accent)]">
                    <Download size={13} /> Export as JSON
                  </button>
                  <div className="border-t border-[var(--border)] my-1" />
                  <button onClick={() => { setEditing(true); setTitle(session.title); setMenuOpen(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[var(--foreground)] hover:bg-[var(--accent)]">
                    <Edit2 size={13} /> Rename chat
                  </button>
                  <button onClick={() => { handleDelete(); setMenuOpen(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[var(--destructive)] hover:bg-red-500/10">
                    <Trash2 size={13} /> Delete chat
                  </button>
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
