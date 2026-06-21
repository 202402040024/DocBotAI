"use client";
import { useState, useRef, useCallback, useEffect } from "react";
import { Send, Mic, MicOff, Square, Paperclip } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { voiceService } from "@/services/voice.service";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  isStreaming?: boolean;
  onStop?: () => void;
}

export function ChatInput({ onSend, disabled, isStreaming, onStop }: ChatInputProps) {
  const router = useRouter();
  const [input, setInput] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [recordingError, setRecordingError] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Auto-resize textarea
  const resizeTextarea = () => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
    }
  };

  useEffect(() => { resizeTextarea(); }, [input]);

  const handleSend = useCallback(() => {
    const msg = input.trim();
    if (!msg || disabled || isStreaming) return;
    onSend(msg);
    setInput("");
  }, [input, disabled, isStreaming, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const startRecording = async () => {
    setRecordingError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        const file = new File([blob], "recording.wav", { type: "audio/wav" });
        try {
          const { text } = await voiceService.transcribe(file);
          if (text) setInput((prev) => (prev ? prev + " " + text : text));
        } catch {
          setRecordingError("Transcription failed — try again");
          setTimeout(() => setRecordingError(""), 3000);
        }
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch {
      setRecordingError("Microphone access denied");
      setTimeout(() => setRecordingError(""), 3000);
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  const canSend = input.trim().length > 0 && !disabled && !isStreaming;

  return (
    <div className="border-t border-[var(--border)] bg-[var(--background)] px-4 py-3 flex-shrink-0">
      <div className="max-w-3xl mx-auto">
        {/* Error toast */}
        {recordingError && (
          <p className="text-xs text-[var(--destructive)] text-center mb-2">{recordingError}</p>
        )}

        {/* Input box */}
        <div className={cn(
          "flex items-end gap-2 rounded-2xl border bg-[var(--card)] px-3 py-2 transition-all duration-150",
          isFocused
            ? "border-[var(--primary)] shadow-[0_0_0_3px_rgba(59,130,246,0.12)]"
            : isRecording
              ? "border-red-400 shadow-[0_0_0_3px_rgba(239,68,68,0.12)]"
              : "border-[var(--border)]"
        )}>
          {/* Upload shortcut */}
          <button
            type="button"
            title="Upload documents"
            onClick={() => router.push("/documents")}
            className="flex-shrink-0 p-1.5 rounded-lg text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)] transition-colors self-end mb-0.5"
          >
            <Paperclip size={15} />
          </button>

          {/* Text area */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={isRecording ? "🎙 Recording… click stop when done" : "Ask anything…"}
            disabled={disabled && !isStreaming || isRecording}
            className="flex-1 resize-none bg-transparent text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] outline-none min-h-[36px] max-h-[160px] py-2 leading-relaxed"
          />

          {/* Right actions */}
          <div className="flex items-center gap-0.5 self-end pb-0.5 flex-shrink-0">
            {/* Voice */}
            <button
              type="button"
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isStreaming}
              title={isRecording ? "Stop recording" : "Voice input"}
              className={cn(
                "p-1.5 rounded-lg transition-colors",
                isRecording
                  ? "text-red-500 hover:bg-red-500/10 animate-pulse"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)]"
              )}
            >
              {isRecording ? <MicOff size={15} /> : <Mic size={15} />}
            </button>

            {/* Send / Stop */}
            {isStreaming ? (
              <button
                type="button"
                onClick={onStop}
                title="Stop generation"
                className="p-1.5 rounded-lg text-[var(--destructive)] hover:bg-red-500/10 transition-colors"
              >
                <Square size={14} fill="currentColor" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSend}
                disabled={!canSend}
                title="Send (Enter)"
                className={cn(
                  "p-1.5 rounded-lg transition-all",
                  canSend
                    ? "bg-[var(--primary)] text-white hover:opacity-90 active:scale-95"
                    : "text-[var(--muted-foreground)] opacity-40 cursor-not-allowed"
                )}
              >
                <Send size={14} />
              </button>
            )}
          </div>
        </div>

        {/* Footer hint */}
        <p className="text-center text-xs text-[var(--muted-foreground)] mt-1.5 opacity-60">
          Enter to send · Shift+Enter for newline · AI responses may be inaccurate
        </p>
      </div>
    </div>
  );
}
