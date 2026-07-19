"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getAccessToken, getStoredUser } from "@/lib/auth";

/** Root entry — send authenticated users to Dashboard, else login. */
export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = getAccessToken();
    const user = getStoredUser();
    router.replace(token && user ? "/dashboard" : "/login");
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-background text-sm text-muted-foreground">
      Loading…
    </main>
  );
}
