"use client";

import { AppHeader } from "@/components/layout/app-header";
import { useSessionCheck } from "@/lib/hooks/use-session-check";

export default function DashboardPage() {
  const session = useSessionCheck();

  return (
    <>
      <AppHeader
        title="Dashboard"
        description="Fleet KPIs, indexing status, and operational alerts."
      />
      <main className="flex-1 overflow-y-auto p-5">
        <div className="mx-auto max-w-3xl space-y-4">
          <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Placeholder
            </p>
            <h2 className="mt-2 text-xl font-semibold tracking-tight">
              Dashboard
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Fleet dashboard KPIs will bind to catalog and indexing APIs in
              later milestones. No fabricated business metrics are shown here.
            </p>
          </div>

          <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              API session (TanStack Query)
            </p>
            {session.isLoading ? (
              <p className="mt-2 text-sm text-muted-foreground">
                Verifying authenticated session…
              </p>
            ) : null}
            {session.isError ? (
              <p className="mt-2 text-sm text-destructive">
                Session check failed — confirm the API is running at{" "}
                <code className="text-xs">NEXT_PUBLIC_API_BASE_URL</code>.
              </p>
            ) : null}
            {session.data ? (
              <p className="mt-2 text-sm text-muted-foreground">
                Authenticated as{" "}
                <span className="font-medium text-foreground">
                  {session.data.email}
                </span>{" "}
                (user {session.data.user_id}).
              </p>
            ) : null}
          </div>
        </div>
      </main>
    </>
  );
}
