"use client";

import { useQuery } from "@tanstack/react-query";
import { AppHeader } from "@/components/layout/app-header";
import { fetchIndexingStatus } from "@/lib/motors-api";

export default function SyncPage() {
  const indexing = useQuery({
    queryKey: ["indexing-status-page"],
    queryFn: fetchIndexingStatus,
    refetchInterval: 15_000,
  });

  return (
    <>
      <AppHeader
        title="Google Drive Sync"
        description="Continuous Intelligent Indexing progress and corpus sync status."
      />
      <main className="flex-1 overflow-y-auto p-5">
        <div className="mx-auto max-w-4xl space-y-4">
          <section className="rounded-lg border border-border bg-card p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Indexing status
            </h2>
            {indexing.isLoading ? (
              <p className="mt-3 text-sm text-muted-foreground">Loading…</p>
            ) : null}
            {indexing.isError ? (
              <p className="mt-3 text-sm text-destructive">
                Indexing status API failed — is the backend running?
              </p>
            ) : null}
            {indexing.data ? (
              <pre className="mt-3 overflow-auto rounded bg-muted/40 p-3 text-xs leading-relaxed text-muted-foreground">
                {JSON.stringify(indexing.data, null, 2)}
              </pre>
            ) : null}
          </section>
        </div>
      </main>
    </>
  );
}
