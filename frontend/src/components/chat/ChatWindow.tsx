"use client";
import { useEffect, useRef, useCallback, useState } from "react";
import { Bot, Sparkles } from "lucide-react";
import { ChatMessage, Citation } from "@/types";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { ChatHeader } from "./ChatHeader";
import { chatService } from "@/services/chat.service";
import { useChatStore } from "@/store/useChatStore";

interface ChatWindowProps {
  sessionId: string | null;
  onNewSession: (id: string) => void;
}

const SUGGESTIONS = [
  "Summarize my uploaded document",
  "What are the key insights from my files?",
  "Generate 5 quiz questions from my document",
  "Explain the main concepts simply",
  "What does the document say about [topic]?",
  "Compare ideas across my uploaded files",
];

export function ChatWindow({ sessionId, onNewSession }: ChatWindowProps) {
  const {
    sessions,
    messages,
    isStreaming,
    streamingMessage,
    appendMessage,
    setMessages,
    updateStreamingMessage,
    setIsStreaming,
    setPendingCitations,
    finalizeStreamingMessage,
    setActiveSession,
    addSession,
  } = useChatStore();

  const bottomRef = useRef<HTMLDivElement>(null);
  const stopRef = useRef<(() => void) | null>(null);
  const [loadingMessages, setLoadingMessages] = useState(false);

  const currentMessages = sessionId ? (messages[sessionId] || []) : [];
  const activeSession = sessions.find((s) => s.id === sessionId) || null;

  // Load messages when session changes
  useEffect(() => {
    if (!sessionId) return;
    if (messages[sessionId] !== undefined) return; // already loaded
    setLoadingMessages(true);
    chatService.getMessages(sessionId)
      .then((msgs) => setMessages(sessionId, msgs))
      .catch(() => setMessages(sessionId, []))
      .finally(() => setLoadingMessages(false));
  }, [sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Reset streaming message when switching sessions
  useEffect(() => {
    useChatStore.setState({ streamingMessage: "" });
  }, [sessionId]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentMessages.length, streamingMessage]);

  const handleSend = useCallback((text: string) => {
    if (isStreaming) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      citations: [],
      timestamp: new Date().toISOString(),
    };

    const targetSessionId = sessionId;
    if (targetSessionId) appendMessage(targetSessionId, userMsg);

    setIsStreaming(true);
    useChatStore.setState({ streamingMessage: "" });

    let resolvedSessionId = targetSessionId;

    const stop = chatService.streamChat(
      text,
      targetSessionId,
      (chunk) => updateStreamingMessage(chunk),
      (citations) => setPendingCitations(citations as Citation[]),
      (newSessionId) => {
        resolvedSessionId = newSessionId;
        if (!targetSessionId) {
          onNewSession(newSessionId);
          setActiveSession(newSessionId);
          appendMessage(newSessionId, userMsg);
          addSession({
            id: newSessionId,
            title: text.slice(0, 45) + (text.length > 45 ? "…" : ""),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          });
        }
      },
      () => {
        const finalId = resolvedSessionId || "";
        const { pendingCitations } = useChatStore.getState();
        finalizeStreamingMessage(finalId, pendingCitations);
      },
      (err) => {
        console.error("Stream error:", err);
        setIsStreaming(false);
      }
    );

    stopRef.current = stop;
  }, [isStreaming, sessionId, appendMessage, setIsStreaming, updateStreamingMessage, setPendingCitations,
      finalizeStreamingMessage, setActiveSession, onNewSession, addSession]);

  const handleStop = () => {
    stopRef.current?.();
    stopRef.current = null;
    const { pendingCitations, activeSessionId } = useChatStore.getState();
    if (activeSessionId) finalizeStreamingMessage(activeSessionId, pendingCitations);
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header — only when a session is active */}
      <ChatHeader session={activeSession} messages={currentMessages} />

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        {loadingMessages ? (
          <div className="flex items-center justify-center h-full">
            <div className="w-6 h-6 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 flex flex-col gap-6">
            {currentMessages.length === 0 && !isStreaming ? (
              <EmptyState onSuggestion={handleSend} />
            ) : (
              <>
                {currentMessages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}

                {/* Streaming assistant message */}
                {isStreaming && streamingMessage && (
                  <MessageBubble
                    message={{
                      id: "streaming",
                      role: "assistant",
                      content: streamingMessage,
                      citations: [],
                      timestamp: new Date().toISOString(),
                    }}
                    isStreaming
                  />
                )}

                {/* Typing indicator — before first chunk arrives */}
                {isStreaming && !streamingMessage && (
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-[var(--secondary)] border border-[var(--border)] flex items-center justify-center flex-shrink-0">
                      <Bot size={14} />
                    </div>
                    <div className="flex gap-1 px-4 py-3 rounded-2xl rounded-tl-sm bg-[var(--card)] border border-[var(--border)]">
                      {[0, 1, 2].map((i) => (
                        <span
                          key={i}
                          className="w-2 h-2 rounded-full bg-[var(--muted-foreground)] animate-bounce"
                          style={{ animationDelay: `${i * 0.18}s` }}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <ChatInput
        onSend={handleSend}
        disabled={isStreaming || loadingMessages}
        isStreaming={isStreaming}
        onStop={handleStop}
      />
    </div>
  );
}

function EmptyState({ onSuggestion }: { onSuggestion: (text: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[55vh] gap-8 text-center py-8">
      <div className="flex flex-col items-center gap-4">
        <div className="w-16 h-16 rounded-2xl bg-[var(--primary)]/10 border border-[var(--primary)]/20 flex items-center justify-center">
          <Bot size={32} className="text-[var(--primary)]" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-[var(--foreground)] mb-2">How can I help you today?</h2>
          <p className="text-sm text-[var(--muted-foreground)] max-w-sm">
            Ask anything — I'll search your uploaded documents first, then fall back to general knowledge.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-xl">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            onClick={() => onSuggestion(suggestion)}
            className="group flex items-start gap-2.5 text-left p-3.5 rounded-xl border border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)]/50 hover:bg-[var(--primary)]/5 transition-all"
          >
            <Sparkles size={13} className="text-[var(--primary)] flex-shrink-0 mt-0.5 opacity-60 group-hover:opacity-100" />
            <span className="text-xs text-[var(--muted-foreground)] group-hover:text-[var(--foreground)] transition-colors leading-relaxed">
              {suggestion}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
