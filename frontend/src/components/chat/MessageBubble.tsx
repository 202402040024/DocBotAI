"use client";
import { memo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { ChatMessage } from "@/types";
import { CitationCard } from "./CitationCard";
import { Bot, User, Copy, Check, Volume2, Loader2 } from "lucide-react";
import { formatDate } from "@/lib/utils";
import { voiceService } from "@/services/voice.service";

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

export const MessageBubble = memo(({ message, isStreaming }: MessageBubbleProps) => {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const [ttsLoading, setTtsLoading] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTTS = async () => {
    if (ttsLoading) return;
    setTtsLoading(true);
    try {
      const blob = await voiceService.speak(message.content.slice(0, 2000));
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch {
      // TTS not available — silently fail
    } finally {
      setTtsLoading(false);
    }
  };

  return (
    <div className={`group flex gap-3 animate-fade-in ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center self-start mt-0.5 ${
        isUser
          ? "bg-[var(--primary)] text-white"
          : "bg-[var(--secondary)] text-[var(--foreground)] border border-[var(--border)]"
      }`}>
        {isUser ? <User size={14} /> : <Bot size={14} />}
      </div>

      {/* Content */}
      <div className={`flex flex-col max-w-[80%] min-w-0 ${isUser ? "items-end" : "items-start"}`}>
        <div className={`rounded-2xl px-4 py-2.5 ${
          isUser
            ? "bg-[var(--primary)] text-white rounded-tr-sm"
            : "bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] rounded-tl-sm"
        }`}>
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
          ) : (
            <div className={`prose text-sm ${isStreaming ? "typing-cursor" : ""}`}>
              <ReactMarkdown
                components={{
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  code({ inline, className, children, ...props }: any) {
                    const match = /language-(\w+)/.exec(className || "");
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={oneDark}
                        language={match[1]}
                        PreTag="div"
                        customStyle={{ margin: "0.5em 0", borderRadius: "6px", fontSize: "0.8em" }}
                        {...props}
                      >
                        {String(children).replace(/\n$/, "")}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={className} {...props}>{children}</code>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Citations */}
        {!isUser && message.citations?.length > 0 && (
          <div className="w-full mt-1">
            <CitationCard citations={message.citations} />
          </div>
        )}

        {/* Actions row */}
        <div className={`flex items-center gap-2 mt-1 px-1 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
          <span className="text-xs text-[var(--muted-foreground)]">{formatDate(message.timestamp)}</span>

          {/* Action buttons — shown on hover */}
          {!isStreaming && (
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={handleCopy}
                title="Copy"
                className="p-1 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)] transition-colors"
              >
                {copied ? <Check size={12} className="text-green-500" /> : <Copy size={12} />}
              </button>
              {!isUser && (
                <button
                  onClick={handleTTS}
                  title="Read aloud"
                  className="p-1 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)] transition-colors"
                >
                  {ttsLoading
                    ? <Loader2 size={12} className="animate-spin" />
                    : <Volume2 size={12} />}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});
MessageBubble.displayName = "MessageBubble";
