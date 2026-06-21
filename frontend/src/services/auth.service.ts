import api from "./api";
import { User, AuthTokens, UserSettings } from "@/types";

export const authService = {
  async register(name: string, email: string, password: string): Promise<User> {
    const res = await api.post<User>("/api/auth/register", { name, email, password });
    return res.data;
  },

  async login(email: string, password: string): Promise<AuthTokens> {
    const res = await api.post<AuthTokens>("/api/auth/login", { email, password });
    const { access_token, refresh_token } = res.data;
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    return res.data;
  },

  async logout(): Promise<void> {
    try { await api.post("/api/auth/logout"); } catch {}
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },

  async getMe(): Promise<User> {
    const res = await api.get<User>("/api/auth/me");
    return res.data;
  },

  async getSettings(): Promise<UserSettings> {
    const res = await api.get<UserSettings>("/api/auth/settings");
    return res.data;
  },

  async updateSettings(settings: UserSettings): Promise<void> {
    await api.put("/api/auth/settings", settings);
  },
};
