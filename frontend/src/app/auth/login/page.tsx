"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Mail, Lock, Eye, EyeOff, Bot } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";

export default function LoginPage() {
  const router = useRouter();
  const setUser = useAuthStore((s) => s.setUser);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await authService.login(email, password);
      const me = await authService.getMe();
      setUser(me);
      router.push("/chat");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; code?: string; message?: string };
      if (!axiosErr.response) {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        setError(`Cannot reach the server at ${apiUrl}. Check that the backend is running.`);
      } else {
        setError(axiosErr.response?.data?.detail || "Invalid credentials");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--background)] p-4">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-sm"
      >
        {/* Logo */}
        <div className="flex flex-col items-center mb-8 gap-3">
          <div className="w-12 h-12 rounded-2xl bg-[var(--primary)] flex items-center justify-center">
            <Bot size={26} className="text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold text-[var(--foreground)]">Welcome back</h1>
            <p className="text-sm text-[var(--muted-foreground)] mt-1">Sign in to your AI assistant</p>
          </div>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-xl">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label="Email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              leftIcon={<Mail size={15} />}
              required
              autoFocus
            />
            <Input
              label="Password"
              type={showPwd ? "text" : "password"}
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              leftIcon={<Lock size={15} />}
              rightIcon={
                <button type="button" onClick={() => setShowPwd(!showPwd)} className="cursor-pointer">
                  {showPwd ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              }
              required
            />
            {error && (
              <p className="text-xs text-[var(--destructive)] bg-red-500/10 rounded-lg px-3 py-2">{error}</p>
            )}
            <Button type="submit" loading={loading} className="w-full mt-1">
              Sign in
            </Button>
          </form>
        </div>

        <p className="text-center text-sm text-[var(--muted-foreground)] mt-4">
          No account?{" "}
          <Link href="/auth/register" className="text-[var(--primary)] hover:underline font-medium">
            Create one
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
