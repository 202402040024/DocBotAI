import api from "./api";

export const voiceService = {
  async transcribe(audioFile: File): Promise<{ text: string; warning?: string }> {
    const formData = new FormData();
    formData.append("file", audioFile);
    const res = await api.post("/api/voice/transcribe", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data;
  },

  async speak(text: string): Promise<Blob> {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    // Use relative URL — goes through Next.js proxy
    const response = await fetch("/api/voice/speak", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) throw new Error("TTS failed");
    return response.blob();
  },
};
