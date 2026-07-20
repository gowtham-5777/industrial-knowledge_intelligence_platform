"use client";

import { useQuery } from "@tanstack/react-query";
import { AppHeader } from "@/components/layout/app-header";
import { fetchAnalytics } from "@/lib/industrial-api";

export default function AnalyticsPage() {
  const query = useQuery({
    queryKey: ["analytics"],
    queryFn: fetchAnalytics,
  });
  const d = query.data;
  const maxVelocity = Math.max(
    1,
    ...(d?.velocity.map((v) => v.jobs_completed + v.jobs_failed) || [1]),
  );

  return (
    <>
      <AppHeader
        title="Analytics"
        description="Fleet coverage and continuous indexing velocity."
      />
      <main className="flex-1 overflow-y-auto p-5">
        <div className="mx-auto max-w-5xl space-y-5">
          {query.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading analytics…</p>
          ) : null}
          {query.isError ? (
            <p className="text-sm text-destructive">Failed to load analytics.</p>
          ) : null}

          {d ? (
            <>
              <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  { label: "Catalog", value: d.catalog_total },
                  { label: "Ingested", value: d.documents_total },
                  { label: "Indexed ready", value: d.indexed_ready },
                  { label: "Coverage", value: `${d.coverage_pct}%` },
                ].map((card) => (
                  <article
                    key={card.label}
                    className="rounded-lg border border-border bg-card px-4 py-3"
                  >
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                      {card.label}
                    </p>
                    <p className="mt-1 text-2xl font-semibold tabular-nums">
                      {card.value}
                    </p>
                  </article>
                ))}
              </section>

              <section className="rounded-lg border border-border bg-card p-4">
                <h2 className="text-sm font-semibold">Indexing velocity (7 days)</h2>
                <div className="mt-4 flex h-36 items-end gap-2">
                  {d.velocity.map((v) => (
                    <div key={v.day} className="flex flex-1 flex-col items-center gap-1">
                      <div className="flex h-28 w-full items-end gap-0.5">
                        <div
                          className="w-full rounded-t bg-accent/80"
                          style={{
                            height: `${(v.jobs_completed / maxVelocity) * 100}%`,
                          }}
                          title={`${v.jobs_completed} completed`}
                        />
                        <div
                          className="w-full rounded-t bg-destructive/50"
                          style={{
                            height: `${(v.jobs_failed / maxVelocity) * 100}%`,
                          }}
                          title={`${v.jobs_failed} failed`}
                        />
                      </div>
                      <span className="text-[10px] text-muted-foreground">
                        {v.day.slice(5)}
                      </span>
                    </div>
                  ))}
                </div>
              </section>

              <section className="rounded-lg border border-border bg-card p-4">
                <h2 className="text-sm font-semibold">Domain coverage</h2>
                <div className="mt-3 space-y-2">
                  {d.domains.map((domain) => {
                    const pct =
                      domain.catalog_count > 0
                        ? Math.round(
                            (100 * domain.ingested_count) / domain.catalog_count,
                          )
                        : 0;
                    return (
                      <div key={domain.domain}>
                        <div className="flex justify-between text-xs">
                          <span>{domain.domain}</span>
                          <span className="text-muted-foreground">
                            {domain.ingested_count}/{domain.catalog_count} ({pct}%)
                          </span>
                        </div>
                        <div className="mt-1 h-2 overflow-hidden rounded bg-muted">
                          <div
                            className="h-full bg-accent"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                  {d.domains.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No catalog domains discovered yet.
                    </p>
                  ) : null}
                </div>
              </section>
            </>
          ) : null}
        </div>
      </main>
    </>
  );
}
