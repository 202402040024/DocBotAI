import api from "./api";
import { ChatSession, ChatMessage } from "@/types";

// Direct backend URL only for SSE streaming (Next.js proxy buffers SSE and breaks it)
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const chatService = {
  async createSession(title: string): Promise<ChatSession> {
    const res = await api.post<ChatSession>("/api/chat/new", { title });
    return res.data;
  },

  async getSessions(query?: string): Promise<ChatSession[]> {
    const params = query ? { query } : {};
    const res = await api.get<ChatSession[]>("/api/chat/history", { params });
    return res.data;
  },

  async getMessages(sessionId: string): Promise<ChatMessage[]> {
    const res = await api.get<ChatMessage[]>(`/api/chat/${sessionId}/messages`);
    return res.data;
  },

  async deleteSession(id: string): Promise<void> {
    await api.delete(`/api/chat/${id}`);
  },

  async renameSession(id: string, title: string): Promise<void> {
    await api.put(`/api/chat/${id}`, null, { params: { title } });
  },

  // SSE streaming goes directly to backend — Next.js proxy buffers responses and breaks streaming
  streamChat(
    query: string,
    sessionId: string | null,
    onChunk: (text: string) => void,
    onCitations: (citations: unknown[]) => void,
    onSession: (id: string) => void,
    onDone: () => void,
    onError: (msg: string) => void
  ): () => void {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const params = new URLSearchParams({ stream: "true" });
    if (sessionId) params.set("session_id", sessionId);

    const controller = new AbortController();

    fetch(`${BACKEND_URL}/api/chat?${params.toString()}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ query }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const errText = await response.text().catch(() => "Unknown error");
          throw new Error(`HTTP ${response.status}: ${errText}`);
        }
        const reader = response.body?.getReader();
        if (!reader) throw new Error("No readable stream");
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const payload = line.slice(6).trim();
            if (payload === "[DONE]") { onDone(); continue; }
            try {
              const data = JSON.parse(payload);
              if (data.type === "content") onChunk(data.text || "");
              else if (data.type === "session") onSession(data.session_id || "");
              else if (data.type === "citations") onCitations(data.citations || []);
              else if (data.type === "error") onError(data.message || "Unknown error");
            } catch {
              // ignore malformed SSE lines
            }
          }
        }
        onDone();
      })
      .catch((err) => {
        if (err.name !== "AbortError") onError(err.message || "Stream error");
      });

    return () => controller.abort();
  },
};
