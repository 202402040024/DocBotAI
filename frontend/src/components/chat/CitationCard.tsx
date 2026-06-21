"use client";
import { Citation } from "@/types";
import { FileText, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface CitationCardProps {
  citations: Citation[];
}

export function CitationCard({ citations }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);

  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-3 rounded-lg border border-[var(--border)] bg-[var(--secondary)] overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <FileText size={12} />
          {citations.length} source{citations.length > 1 ? "s" : ""}
        </span>
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {expanded && (
        <div className="border-t border-[var(--border)] divide-y divide-[var(--border)]">
          {citations.map((c, i) => (
            <div key={i} className="px-3 py-2">
              <p className="text-xs font-medium text-[var(--foreground)] truncate">{c.document_name}</p>
              <div className="flex gap-3 mt-0.5">
                <span className="text-xs text-[var(--muted-foreground)]">Page {c.page_number}</span>
                <span className="text-xs text-[var(--muted-foreground)]">¶{c.paragraph_number}</span>
                <span className="text-xs text-[var(--primary)] font-medium ml-auto">
                  {(c.similarity_score * 100).toFixed(0)}% match
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
