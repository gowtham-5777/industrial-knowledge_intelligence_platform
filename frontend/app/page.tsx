"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AuthUser, clearSession, getStoredUser } from "@/lib/auth";

export default function Home() {
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 px-6 text-zinc-100">
      <p className="text-sm uppercase tracking-[0.2em] text-zinc-500">
        Industrial Brain AI
      </p>
      <h1 className="mt-4 max-w-2xl text-center text-3xl font-semibold tracking-tight sm:text-4xl">
        Industrial Knowledge Intelligence Platform
      </h1>
      <p className="mt-4 max-w-xl text-center text-zinc-400">
        Auth session wiring is live (Milestone 1.4). Enterprise shell arrives in
        Milestone 1.8.
      </p>

      <div className="mt-8 flex flex-wrap items-center justify-center gap-4 text-sm">
        {user ? (
          <>
            <span className="text-zinc-300">
              Signed in as <strong>{user.display_name}</strong> ({user.email})
            </span>
            <button
              type="button"
              className="rounded border border-zinc-700 px-3 py-1.5 text-zinc-200 hover:border-zinc-500"
              onClick={() => {
                clearSession();
                setUser(null);
              }}
            >
              Sign out
            </button>
          </>
        ) : (
          <Link
            href="/login"
            className="rounded bg-zinc-100 px-3 py-1.5 font-medium text-zinc-900"
          >
            Sign in
          </Link>
        )}
      </div>
    </main>
  );
}
