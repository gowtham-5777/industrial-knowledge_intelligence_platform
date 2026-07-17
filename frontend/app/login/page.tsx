"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import {
  type AuthUser,
  clearSession,
  fetchMe,
  getStoredUser,
  loginRequest,
  saveSession,
} from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("ChangeMeAdmin!");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
  }, []);

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
      router.push("/");
    } catch (err) {
      clearSession();
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 px-6 text-zinc-100">
      <div className="w-full max-w-md">
        <p className="text-sm uppercase tracking-[0.2em] text-zinc-500">
          Industrial Brain AI
        </p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="mt-2 text-sm text-zinc-400">
          JWT seed auth for hackathon. Seeded admin and operator accounts are
          available after{" "}
          <code className="text-zinc-300">python -m app.db.seed_cli</code>.
        </p>

        {user ? (
          <p className="mt-6 rounded border border-zinc-800 bg-zinc-900/60 p-3 text-sm text-zinc-300">
            Already signed in as {user.email}.{" "}
            <button
              type="button"
              className="underline"
              onClick={() => {
                clearSession();
                setUser(null);
              }}
            >
              Sign out
            </button>
          </p>
        ) : null}

        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <label className="block text-sm">
            <span className="text-zinc-400">Email</span>
            <input
              className="mt-1 w-full rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-zinc-100 outline-none focus:border-zinc-500"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </label>
          <label className="block text-sm">
            <span className="text-zinc-400">Password</span>
            <input
              className="mt-1 w-full rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-zinc-100 outline-none focus:border-zinc-500"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          {error ? <p className="text-sm text-red-400">{error}</p> : null}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded bg-zinc-100 px-3 py-2 text-sm font-medium text-zinc-900 disabled:opacity-60"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </main>
  );
}
