"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AppHeader } from "@/components/layout/app-header";
import {
  fetchDashboardKpis,
  fetchHeroMotors,
  fetchIndexingStatus,
} from "@/lib/motors-api";

export default function DashboardPage() {
  const kpis = useQuery({
    queryKey: ["dashboard-kpis"],
    queryFn: fetchDashboardKpis,
  });
  const hero = useQuery({
    queryKey: ["hero-motors"],
    queryFn: fetchHeroMotors,
  });
  const indexing = useQuery({
    queryKey: ["indexing-status"],
    queryFn: fetchIndexingStatus,
    retry: false,
  });

  const d = kpis.data;

  const cards = [
    {
      label: "Documents discovered",
      value: d?.documents_discovered ?? d?.catalog_count ?? "—",
    },
    {
      label: "Documents ingested",
      value: d?.documents_ingested ?? d?.document_count ?? "—",
    },
    {
      label: "Fully indexed",
      value: d?.documents_indexed ?? d?.indexed_count ?? "—",
    },
    {
      label: "Motor models",
      value: d?.motor_models ?? d?.motor_count ?? "—",
    },
  ];

  return (
    <>
      <AppHeader
        title="Dashboard"
        description="Fleet KPIs, hero motor signal, and continuous indexing progress."
      />
      <main className="flex-1 overflow-y-auto p-5">
        <div className="mx-auto max-w-6xl space-y-5">
          <section className="overflow-hidden rounded-lg border border-border bg-gradient-to-br from-[#eef5f6] via-background to-[#f3efe6] p-5 dark:from-[#0f1a1c] dark:via-background dark:to-[#16120c]">
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
              Industrial Brain AI
            </p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight">
              Fleet operations pulse
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              Live counts from the system of record — no fabricated demo metrics.
            </p>
          </section>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {cards.map((c) => (
              <div
                key={c.label}
                className="rounded-lg border border-border bg-card px-4 py-3"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  {c.label}
                </p>
                <p className="mt-2 text-2xl font-semibold tabular-nums">
                  {kpis.isLoading ? "…" : c.value}
                </p>
              </div>
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <section className="rounded-lg border border-border bg-card p-4">
              <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Hero motor
              </h3>
              {hero.data ? (
                <div className="mt-3">
                  <p className="text-lg font-semibold">{hero.data.hero.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {hero.data.hero.code} · Health{" "}
                    {d?.hero_health
                      ? `${Math.round(d.hero_health.score)}/100 ${d.hero_health.risk_level}`
                      : d?.hero_health_score != null
                        ? `${Math.round(d.hero_health_score)}/100 ${d.hero_risk_level ?? ""}`
                        : "pending"}
                  </p>
                  <Link
                    href={`/motors/${hero.data.hero.id}`}
                    className="mt-3 inline-block text-sm font-medium text-accent hover:underline"
                  >
                    Open Motor 360 →
                  </Link>
                </div>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  Confirm the hero set from Motor Explorer to populate this panel.
                </p>
              )}
            </section>

            <section className="rounded-lg border border-border bg-card p-4">
              <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Continuous indexing
              </h3>
              {indexing.data || d?.indexing_status ? (
                <pre className="mt-3 max-h-48 overflow-auto rounded bg-muted/40 p-3 text-xs text-muted-foreground">
                  {JSON.stringify(indexing.data ?? d?.indexing_status, null, 2)}
                </pre>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  Indexing status API unavailable or empty — open Sync for detail.
                </p>
              )}
              <Link
                href="/sync"
                className="mt-3 inline-block text-sm font-medium text-accent hover:underline"
              >
                Open indexing status →
              </Link>
            </section>
          </div>
        </div>
      </main>
    </>
  );
}
