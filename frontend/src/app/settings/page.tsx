"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Moon, Sun, Save, User, Cpu } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";

export default function SettingsPage() {
  const router = useRouter();
  const { user, isAuthenticated, setUser, theme, setTheme } = useAuthStore();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [primaryModel, setPrimaryModel] = useState("gemini");
  const [temperature, setTemperature] = useState(0.7);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) { router.replace("/auth/login"); return; }
    if (!isAuthenticated) authService.getMe().then(setUser).catch(() => router.replace("/auth/login"));
  }, [router, isAuthenticated, setUser]);

  useEffect(() => {
    authService.getSettings().then((s) => {
      setPrimaryModel(s.model_preferences?.primary_model || "gemini");
      setTemperature(s.model_preferences?.temperature ?? 0.7);
      if (s.theme) setTheme(s.theme as "light" | "dark");
    }).catch(() => {});
  }, [setTheme]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await authService.updateSettings({
        theme,
        model_preferences: { primary_model: primaryModel, temperature },
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
    setSaving(false);
  };

  return (
    <AppLayout>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-6 py-8">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-[var(--foreground)]">Settings</h1>
            <p className="text-sm text-[var(--muted-foreground)] mt-1">Manage your account and preferences</p>
          </div>

          <div className="flex flex-col gap-6">
            {/* Profile */}
            <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
              <h2 className="text-sm font-semibold text-[var(--foreground)] mb-4 flex items-center gap-2">
                <User size={14} /> Profile
              </h2>
              <div className="flex flex-col gap-3">
                <Input label="Name" value={user?.name || ""} disabled />
                <Input label="Email" value={user?.email || ""} disabled />
                <Input label="Role" value={user?.role || ""} disabled />
              </div>
            </section>

            {/* Appearance */}
            <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
              <h2 className="text-sm font-semibold text-[var(--foreground)] mb-4">Appearance</h2>
              <div className="flex gap-3">
                <button
                  onClick={() => setTheme("light")}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm transition-all ${
                    theme === "light"
                      ? "bg-[var(--primary)] text-white border-[var(--primary)]"
                      : "border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                  }`}
                >
                  <Sun size={15} /> Light
                </button>
                <button
                  onClick={() => setTheme("dark")}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm transition-all ${
                    theme === "dark"
                      ? "bg-[var(--primary)] text-white border-[var(--primary)]"
                      : "border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                  }`}
                >
                  <Moon size={15} /> Dark
                </button>
              </div>
            </section>

            {/* AI Model Preferences */}
            <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
              <h2 className="text-sm font-semibold text-[var(--foreground)] mb-4 flex items-center gap-2">
                <Cpu size={14} /> AI Model Preferences
              </h2>
              <div className="flex flex-col gap-4">
                <div>
                  <label className="text-sm font-medium text-[var(--foreground)] block mb-2">Primary Model</label>
                  <div className="flex gap-2 flex-wrap">
                    {["gemini", "ollama"].map((m) => (
                      <button
                        key={m}
                        onClick={() => setPrimaryModel(m)}
                        className={`px-4 py-2 rounded-lg border text-sm transition-all capitalize ${
                          primaryModel === m
                            ? "bg-[var(--primary)] text-white border-[var(--primary)]"
                            : "border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                        }`}
                      >
                        {m === "gemini" ? "Gemini 2.5 Flash" : "Llama 3 (Ollama)"}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-[var(--foreground)] block mb-2">
                    Temperature: <span className="text-[var(--primary)]">{temperature}</span>
                  </label>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.1}
                    value={temperature}
                    onChange={(e) => setTemperature(Number(e.target.value))}
                    className="w-full accent-[var(--primary)]"
                  />
                  <div className="flex justify-between text-xs text-[var(--muted-foreground)] mt-1">
                    <span>Precise (0)</span>
                    <span>Creative (1)</span>
                  </div>
                </div>
              </div>
            </section>

            <Button onClick={handleSave} loading={saving} className="self-start">
              {saved ? "✓ Saved!" : <><Save size={14} /> Save Settings</>}
            </Button>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
