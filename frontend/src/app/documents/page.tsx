"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Upload, Trash2, Edit2, FileText, Search, BookOpen, Brain,
  Check, X, ChevronDown, RefreshCw
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { AppLayout } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { documentService } from "@/services/document.service";
import { useAuthStore } from "@/store/useAuthStore";
import { authService } from "@/services/auth.service";
import { Document, QuizQuestion } from "@/types";
import { formatDate, fileIcon } from "@/lib/utils";

export default function DocumentsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, setUser } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [summaryModal, setSummaryModal] = useState<{ open: boolean; doc: Document | null }>({ open: false, doc: null });
  const [summaryType, setSummaryType] = useState("short");
  const [summaryResult, setSummaryResult] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [quizModal, setQuizModal] = useState<{ open: boolean; doc: Document | null }>({ open: false, doc: null });
  const [quizType, setQuizType] = useState("mcq");
  const [numQuestions, setNumQuestions] = useState(5);
  const [quizResult, setQuizResult] = useState<QuizQuestion[]>([]);
  const [quizLoading, setQuizLoading] = useState(false);
  const [searchModal, setSearchModal] = useState(false);
  const [semanticQuery, setSemanticQuery] = useState("");
  const [searchResults, setSearchResults] = useState<unknown[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) { router.replace("/auth/login"); return; }
    if (!isAuthenticated) authService.getMe().then(setUser).catch(() => router.replace("/auth/login"));
  }, [router, isAuthenticated, setUser]);

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: documentService.list,
  });

  const deleteMutation = useMutation({
    mutationFn: documentService.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => documentService.rename(id, name),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["documents"] }); setEditingId(null); },
  });

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true);
    for (const file of files) {
      setUploadProgress(`Uploading ${file.name}… 0%`);
      try {
        await documentService.upload(file, (pct) => {
          setUploadProgress(`Uploading ${file.name}… ${pct}%`);
        });
        setUploadProgress(`✅ ${file.name} uploaded! Indexing in background…`);
        await new Promise(r => setTimeout(r, 1500));
      } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Upload failed";
        setUploadProgress(`❌ Error: ${msg}`);
        await new Promise(r => setTimeout(r, 2500));
      }
    }
    setUploadProgress("");
    setUploading(false);
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSummarize = async () => {
    if (!summaryModal.doc) return;
    setSummaryLoading(true);
    setSummaryResult("");
    try {
      const res = await documentService.summarize(summaryModal.doc.id, summaryType);
      setSummaryResult(res.summary);
    } catch { setSummaryResult("Failed to generate summary. Please try again."); }
    setSummaryLoading(false);
  };

  const handleQuiz = async () => {
    if (!quizModal.doc) return;
    setQuizLoading(true);
    setQuizResult([]);
    try {
      const res = await documentService.generateQuiz(quizModal.doc.id, numQuestions, quizType);
      setQuizResult(res.questions);
    } catch { setQuizResult([]); }
    setQuizLoading(false);
  };

  const handleSemanticSearch = async () => {
    if (!semanticQuery.trim()) return;
    setSearchLoading(true);
    try {
      const results = await documentService.search(semanticQuery);
      setSearchResults(results);
    } catch { setSearchResults([]); }
    setSearchLoading(false);
  };

  const filtered = docs.filter((d) =>
    d.original_filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <AppLayout>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-6 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-2xl font-bold text-[var(--foreground)]">Documents</h1>
              <p className="text-sm text-[var(--muted-foreground)] mt-1">{docs.length} document{docs.length !== 1 ? "s" : ""} indexed</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setSearchModal(true)}>
                <Search size={14} /> Semantic Search
              </Button>
              <input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.csv,.xml" className="hidden" onChange={handleFileUpload} />
              <Button size="sm" onClick={() => fileInputRef.current?.click()} loading={uploading}>
                <Upload size={14} /> Upload
              </Button>
            </div>
          </div>

          {/* Upload status */}
          {uploadProgress && (
            <div className="mb-4 flex items-center gap-2 text-sm text-[var(--muted-foreground)] bg-[var(--secondary)] rounded-lg px-4 py-2">
              <RefreshCw size={14} className="animate-spin" />
              {uploadProgress}
            </div>
          )}

          {/* Search */}
          <div className="mb-6">
            <Input
              placeholder="Filter by filename…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              leftIcon={<Search size={14} />}
            />
          </div>

          {/* Documents grid */}
          {isLoading ? (
            <div className="flex justify-center py-16">
              <div className="w-8 h-8 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <FileText size={40} className="text-[var(--muted-foreground)] mb-4" />
              <p className="text-[var(--foreground)] font-medium mb-1">No documents yet</p>
              <p className="text-sm text-[var(--muted-foreground)]">Upload PDF, DOCX, CSV, or XML files to get started.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AnimatePresence>
                {filtered.map((doc) => (
                  <DocumentCard
                    key={doc.id}
                    doc={doc}
                    editingId={editingId}
                    editName={editName}
                    onEditStart={(id, name) => { setEditingId(id); setEditName(name); }}
                    onEditSave={(id) => renameMutation.mutate({ id, name: editName })}
                    onEditCancel={() => setEditingId(null)}
                    onEditNameChange={setEditName}
                    onDelete={(id) => deleteMutation.mutate(id)}
                    onSummarize={(doc) => { setSummaryModal({ open: true, doc }); setSummaryResult(""); }}
                    onQuiz={(doc) => { setQuizModal({ open: true, doc }); setQuizResult([]); }}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>

      {/* Summary Modal */}
      <Modal open={summaryModal.open} onClose={() => setSummaryModal({ open: false, doc: null })} title="Document Summary" size="lg">
        <div className="flex flex-col gap-4">
          <p className="text-sm text-[var(--muted-foreground)]">{summaryModal.doc?.original_filename}</p>
          <div className="flex gap-2">
            {["short", "detailed", "key_insights"].map((t) => (
              <button
                key={t}
                onClick={() => setSummaryType(t)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${summaryType === t ? "bg-[var(--primary)] text-white border-[var(--primary)]" : "border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"}`}
              >
                {t === "key_insights" ? "Key Insights" : t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>
          <Button onClick={handleSummarize} loading={summaryLoading} size="sm">Generate Summary</Button>
          {summaryResult && (
            <div className="prose text-sm max-h-80 overflow-y-auto rounded-lg border border-[var(--border)] p-4 bg-[var(--secondary)]">
              <pre className="whitespace-pre-wrap text-[var(--foreground)] font-sans text-sm">{summaryResult}</pre>
            </div>
          )}
        </div>
      </Modal>

      {/* Quiz Modal */}
      <Modal open={quizModal.open} onClose={() => setQuizModal({ open: false, doc: null })} title="Quiz Generator" size="xl">
        <div className="flex flex-col gap-4">
          <p className="text-sm text-[var(--muted-foreground)]">{quizModal.doc?.original_filename}</p>
          <div className="flex items-center gap-4">
            <div className="flex gap-2">
              {["mcq", "true_false", "interview"].map((t) => (
                <button
                  key={t}
                  onClick={() => setQuizType(t)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${quizType === t ? "bg-[var(--primary)] text-white border-[var(--primary)]" : "border-[var(--border)] text-[var(--muted-foreground)]"}`}
                >
                  {t === "true_false" ? "True/False" : t === "mcq" ? "MCQ" : "Interview"}
                </button>
              ))}
            </div>
            <select
              value={numQuestions}
              onChange={(e) => setNumQuestions(Number(e.target.value))}
              className="text-xs border border-[var(--border)] rounded-lg px-2 py-1.5 bg-[var(--background)] text-[var(--foreground)] outline-none"
            >
              {[3, 5, 10, 15].map(n => <option key={n} value={n}>{n} questions</option>)}
            </select>
          </div>
          <Button onClick={handleQuiz} loading={quizLoading} size="sm">Generate Quiz</Button>
          {quizResult.length > 0 && (
            <div className="max-h-96 overflow-y-auto flex flex-col gap-4">
              {quizResult.map((q, i) => (
                <div key={q.id} className="rounded-lg border border-[var(--border)] p-4 bg-[var(--secondary)]">
                  <p className="text-sm font-medium text-[var(--foreground)] mb-2">Q{i+1}. {q.question}</p>
                  {q.options && q.options.length > 0 && (
                    <ul className="mb-2 space-y-1">
                      {q.options.map((opt, j) => (
                        <li key={j} className="text-xs text-[var(--muted-foreground)] flex items-start gap-1.5">
                          <span className="font-medium">{String.fromCharCode(65+j)}.</span> {opt}
                        </li>
                      ))}
                    </ul>
                  )}
                  <p className="text-xs text-green-600 dark:text-green-400 font-medium">Answer: {q.answer}</p>
                  {q.explanation && <p className="text-xs text-[var(--muted-foreground)] mt-1">{q.explanation}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>

      {/* Semantic Search Modal */}
      <Modal open={searchModal} onClose={() => setSearchModal(false)} title="Semantic Search" size="lg">
        <div className="flex flex-col gap-4">
          <div className="flex gap-2">
            <Input
              placeholder="Search document content by meaning…"
              value={semanticQuery}
              onChange={(e) => setSemanticQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleSemanticSearch(); }}
            />
            <Button onClick={handleSemanticSearch} loading={searchLoading} size="md">Search</Button>
          </div>
          {(searchResults as Array<{chunk_id: string; document_name: string; similarity_score: number; chunk_text: string; page_number: number}>).length > 0 && (
            <div className="max-h-80 overflow-y-auto flex flex-col gap-3">
              {(searchResults as Array<{chunk_id: string; document_name: string; similarity_score: number; chunk_text: string; page_number: number}>).map((r) => (
                <div key={r.chunk_id} className="rounded-lg border border-[var(--border)] p-3 bg-[var(--secondary)]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-[var(--foreground)]">{r.document_name}</span>
                    <span className="text-xs text-[var(--primary)]">{(r.similarity_score*100).toFixed(0)}% match</span>
                  </div>
                  <p className="text-xs text-[var(--muted-foreground)] line-clamp-3">{r.chunk_text}</p>
                  <p className="text-xs text-[var(--muted-foreground)] mt-1">Page {r.page_number}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>
    </AppLayout>
  );
}

// ─── Document Card ─────────────────────────────────────────────────────────
interface DocCardProps {
  doc: Document;
  editingId: string | null;
  editName: string;
  onEditStart: (id: string, name: string) => void;
  onEditSave: (id: string) => void;
  onEditCancel: () => void;
  onEditNameChange: (name: string) => void;
  onDelete: (id: string) => void;
  onSummarize: (doc: Document) => void;
  onQuiz: (doc: Document) => void;
}

function DocumentCard({ doc, editingId, editName, onEditStart, onEditSave, onEditCancel, onEditNameChange, onDelete, onSummarize, onQuiz }: DocCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 hover:border-[var(--primary)]/50 transition-all"
    >
      <div className="flex items-start gap-3">
        <span className="text-2xl leading-none mt-0.5">{fileIcon(doc.file_type)}</span>
        <div className="flex-1 min-w-0">
          {editingId === doc.id ? (
            <div className="flex items-center gap-1">
              <input
                autoFocus
                value={editName}
                onChange={(e) => onEditNameChange(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") onEditSave(doc.id); if (e.key === "Escape") onEditCancel(); }}
                className="flex-1 text-sm bg-[var(--background)] border border-[var(--border)] rounded px-2 py-0.5 outline-none text-[var(--foreground)]"
              />
              <button onClick={() => onEditSave(doc.id)} className="p-1 text-green-500"><Check size={13} /></button>
              <button onClick={onEditCancel} className="p-1 text-[var(--destructive)]"><X size={13} /></button>
            </div>
          ) : (
            <p className="text-sm font-medium text-[var(--foreground)] truncate">{doc.original_filename}</p>
          )}
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs bg-[var(--secondary)] text-[var(--muted-foreground)] px-1.5 py-0.5 rounded uppercase font-medium">{doc.file_type}</span>
            <span className="text-xs text-[var(--muted-foreground)]">{formatDate(doc.upload_time)}</span>
          </div>
        </div>

        {/* Actions dropdown */}
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="p-1 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)] transition-colors"
          >
            <ChevronDown size={14} />
          </button>
          <AnimatePresence>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="absolute right-0 top-8 z-20 w-44 rounded-lg border border-[var(--border)] bg-[var(--card)] shadow-xl py-1"
                >
                  <button onClick={() => { onEditStart(doc.id, doc.original_filename); setMenuOpen(false); }} className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--foreground)] hover:bg-[var(--accent)]">
                    <Edit2 size={12} /> Rename
                  </button>
                  <button onClick={() => { onSummarize(doc); setMenuOpen(false); }} className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--foreground)] hover:bg-[var(--accent)]">
                    <BookOpen size={12} /> Summarize
                  </button>
                  <button onClick={() => { onQuiz(doc); setMenuOpen(false); }} className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--foreground)] hover:bg-[var(--accent)]">
                    <Brain size={12} /> Generate Quiz
                  </button>
                  <div className="border-t border-[var(--border)] my-1" />
                  <button onClick={() => { onDelete(doc.id); setMenuOpen(false); }} className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--destructive)] hover:bg-red-500/10">
                    <Trash2 size={12} /> Delete
                  </button>
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}
