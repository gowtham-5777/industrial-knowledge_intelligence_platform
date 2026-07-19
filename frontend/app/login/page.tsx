"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import {
  type AuthUser,
  clearSession,
  fetchMe,
  getAccessToken,
  getStoredUser,
  loginRequest,
  saveSession,
} from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/layout/theme-toggle";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("ChangeMeAdmin!");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    const stored = getStoredUser();
    if (token && stored) {
      router.replace("/dashboard");
      return;
    }
    setUser(stored);
  }, [router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const tokens = await loginRequest(email, password);
      saveSession(tokens, {
        id: "pending",
        email,
        display_name: email,
        is_active: true,
        roles: [],
      });
      const me = await fetchMe();
      saveSession(tokens, me);
      setUser(me);
      router.push("/dashboard");
    } catch (err) {
      clearSession();
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center bg-background px-6 text-foreground">
      <div
        className="pointer-events-none absolute inset-0 opacity-60"
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 50% -20%, color-mix(in oklab, var(--accent) 22%, transparent), transparent)",
        }}
      />
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>
      <div className="relative w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-sm">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
          Industrial Brain AI
        </p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          JWT seed auth for the hackathon. Seeded admin and operator accounts
          are available after backend seed.
        </p>

        {user ? (
          <p className="mt-6 rounded-md border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
            Session remnant for {user.email}.{" "}
            <button
              type="button"
              className="underline"
              onClick={() => {
                clearSession();
                setUser(null);
              }}
            >
              Clear
            </button>
          </p>
        ) : null}

        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <label className="block text-sm">
            <span className="text-muted-foreground">Email</span>
            <input
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-foreground outline-none ring-ring focus:ring-2"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </label>
          <label className="block text-sm">
            <span className="text-muted-foreground">Password</span>
            <input
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-foreground outline-none ring-ring focus:ring-2"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </div>
    </main>
  );
}
