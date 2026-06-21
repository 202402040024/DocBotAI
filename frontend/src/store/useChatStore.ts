import { create } from "zustand";
import { ChatSession, ChatMessage, Citation } from "@/types";

interface ChatState {
  sessions: ChatSession[];
  activeSessionId: string | null;
  messages: Record<string, ChatMessage[]>;
  streamingMessage: string;
  isStreaming: boolean;
  pendingCitations: Citation[];

  setSessions: (sessions: ChatSession[]) => void;
  addSession: (session: ChatSession) => void;
  removeSession: (id: string) => void;
  renameSession: (id: string, title: string) => void;
  setActiveSession: (id: string | null) => void;
  setMessages: (sessionId: string, messages: ChatMessage[]) => void;
  appendMessage: (sessionId: string, message: ChatMessage) => void;
  updateStreamingMessage: (text: string) => void;
  setIsStreaming: (val: boolean) => void;
  setPendingCitations: (citations: Citation[]) => void;
  finalizeStreamingMessage: (sessionId: string, citations: Citation[]) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: {},
  streamingMessage: "",
  isStreaming: false,
  pendingCitations: [],

  setSessions: (sessions) => set({ sessions }),
  addSession: (session) =>
    set((s) => ({ sessions: [session, ...s.sessions] })),
  removeSession: (id) =>
    set((s) => ({ sessions: s.sessions.filter((x) => x.id !== id) })),
  renameSession: (id, title) =>
    set((s) => ({
      sessions: s.sessions.map((x) => (x.id === id ? { ...x, title } : x)),
    })),
  setActiveSession: (id) => set({ activeSessionId: id, streamingMessage: "" }),
  setMessages: (sessionId, messages) =>
    set((s) => ({ messages: { ...s.messages, [sessionId]: messages } })),
  appendMessage: (sessionId, message) =>
    set((s) => ({
      messages: {
        ...s.messages,
        [sessionId]: [...(s.messages[sessionId] || []), message],
      },
    })),
  updateStreamingMessage: (text) =>
    set((s) => ({ streamingMessage: s.streamingMessage + text })),
  setIsStreaming: (val) => set({ isStreaming: val }),
  setPendingCitations: (citations) => set({ pendingCitations: citations }),
  finalizeStreamingMessage: (sessionId, citations) => {
    const { streamingMessage, appendMessage } = get();
    if (streamingMessage.trim()) {
      appendMessage(sessionId, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: streamingMessage,
        citations,
        timestamp: new Date().toISOString(),
      });
    }
    set({ streamingMessage: "", isStreaming: false, pendingCitations: [] });
  },
}));
