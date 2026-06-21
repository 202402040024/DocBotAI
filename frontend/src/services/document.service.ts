import api from "./api";
import { Document, SearchResult, SummaryResponse, QuizResponse } from "@/types";

// Direct backend URL for file uploads — Next.js proxy drops multipart/form-data with ECONNRESET
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const documentService = {
  async upload(
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<{ message: string; document: Document }> {
    return new Promise((resolve, reject) => {
      const token =
        typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

      const formData = new FormData();
      formData.append("file", file);

      const xhr = new XMLHttpRequest();

      // Track upload progress
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      });

      xhr.addEventListener("load", () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch {
            reject(new Error("Invalid response from server"));
          }
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject({ response: { data: err, status: xhr.status } });
          } catch {
            reject(new Error(`Upload failed: HTTP ${xhr.status}`));
          }
        }
      });

      xhr.addEventListener("error", () => reject(new Error("Network error during upload")));
      xhr.addEventListener("abort", () => reject(new Error("Upload aborted")));

      // Go directly to backend — bypass Next.js proxy
      xhr.open("POST", `${BACKEND_URL}/api/documents/upload`);
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.send(formData);
    });
  },

  async list(): Promise<Document[]> {
    const res = await api.get<Document[]>("/api/documents");
    return res.data;
  },

  async getById(id: string): Promise<Document> {
    const res = await api.get<Document>(`/api/documents/${id}`);
    return res.data;
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/api/documents/${id}`);
  },

  async rename(id: string, newName: string): Promise<void> {
    await api.put(`/api/documents/${id}`, null, { params: { new_name: newName } });
  },

  async search(query: string): Promise<SearchResult[]> {
    const res = await api.post<SearchResult[]>("/api/rag/search", { query });
    return res.data;
  },

  async summarize(documentId: string, summaryType: string): Promise<SummaryResponse> {
    const res = await api.post<SummaryResponse>("/api/rag/summarize", {
      document_id: documentId,
      summary_type: summaryType,
    });
    return res.data;
  },

  async generateQuiz(
    documentId: string,
    numQuestions: number,
    quizType: string
  ): Promise<QuizResponse> {
    const res = await api.post<QuizResponse>("/api/rag/quiz", {
      document_id: documentId,
      num_questions: numQuestions,
      quiz_type: quizType,
    });
    return res.data;
  },
};
