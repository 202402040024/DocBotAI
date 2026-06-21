"use client";
import { useEffect } from "react";
import { BASE_URL } from "@/services/api";

/**
 * Pings the backend every 10 minutes to prevent Render free tier cold starts.
 * Mount this in the root layout once the user is authenticated.
 */
export function KeepAlive() {
  useEffect(() => {
    const ping = () => {
      fetch(`${BASE_URL}/health`, { method: "GET" }).catch(() => {});
    };

    // Ping immediately on mount
    ping();

    // Then ping every 10 minutes
    const interval = setInterval(ping, 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return null;
}
