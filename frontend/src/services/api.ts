import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from "axios";

// IMPORTANT: Set NEXT_PUBLIC_API_URL in Vercel dashboard to your Render URL
// e.g. https://docbotai-idyn.onrender.com
const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://docbotai-idyn.onrender.com"; // ← hardcoded Render URL as fallback

const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30000, // 30s timeout (Render free tier can be slow on cold start)
});

// Attach JWT token to every request
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem("refresh_token");
        if (!refreshToken) throw new Error("No refresh token");
        const res = await axios.post(`${BASE_URL}/api/auth/refresh`, {
          refresh_token: refreshToken,
        });
        const { access_token, refresh_token } = res.data;
        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", refresh_token);
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        if (typeof window !== "undefined") window.location.href = "/auth/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
export { BASE_URL };
