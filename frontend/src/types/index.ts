// ─── Auth ────────────────────────────────────────────────────────────────────
export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserSettings {
  theme: string;
  model_preferences: {
    primary_model: string;
    temperature: number;
  };
}

// ─── Chat ─────────────────────────────────────────────────────────────────────
export interface Citation {
  document_name: string;
  page_number: number;
  paragraph_number: number;
  similarity_score: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  timestamp: string;
  isStreaming?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

// ─── Documents ───────────────────────────────────────────────────────────────
export interface Document {
  id: string;
  original_filename: string;
  file_type: string;
  upload_time: string;
  document_version: number;
  chunk_count?: number;
}

// ─── RAG ─────────────────────────────────────────────────────────────────────
export interface SearchResult {
  chunk_id: string;
  chunk_text: string;
  document_name: string;
  page_number: number;
  paragraph_number: number;
  similarity_score: number;
}

export interface SummaryResponse {
  document_id: string;
  document_name: string;
  summary_type: string;
  summary: string;
}

export interface QuizQuestion {
  id: number;
  type: string;
  question: string;
  options?: string[];
  answer: string;
  explanation?: string;
}

export interface QuizResponse {
  document_id: string;
  questions: QuizQuestion[];
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
export interface DashboardStats {
  total_documents: number;
  total_chats: number;
  total_questions: number;
  retrieval_count: number;
  searches_performed: number;
  recent_uploads: Document[];
  recent_conversations: ChatSession[];
}

// ─── SSE Streaming ───────────────────────────────────────────────────────────
export interface SSEChunk {
  type: "session" | "content" | "citations" | "error";
  session_id?: string;
  text?: string;
  citations?: Citation[];
  message?: string;
}
