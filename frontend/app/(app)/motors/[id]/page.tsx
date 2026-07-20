"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { AppHeader } from "@/components/layout/app-header";
import { MiniGraph } from "@/components/motors/mini-graph";
import {
  asDocMap,
  asDrawings,
  asRecCards,
  asTimeline,
  fetchMotor360,
  healthBullets,
} from "@/lib/motors-api";
import { cn } from "@/lib/utils";

const TABS = [
  "Timeline",
  "Documents",
  "Tests",
  "Drawings",
  "Compliance",
  "Graph",
] as const;

type Tab = (typeof TABS)[number];

export default function Motor360Page() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [tab, setTab] = useState<Tab>("Timeline");

  const query = useQuery({
    queryKey: ["motor360", id],
    queryFn: () => fetchMotor360(id),
    enabled: Boolean(id),
  });

  const bundle = query.data;
  const motor = bundle?.motor;
  const docs = bundle ? asDocMap(bundle) : {};
  const timeline = bundle ? asTimeline(bundle.timeline) : [];
  const recs = bundle ? asRecCards(bundle.recommendations) : [];
  const drawings = bundle ? asDrawings(bundle) : [];
  const bullets = healthBullets(bundle?.health);
  const summaryText =
    bundle?.summary?.overview ||
    bundle?.summary?.summary_text ||
    "Not available in indexed knowledge.";

  return (
    <>
      <AppHeader
        title="Motor 360"
        description="Flagship asset command center — specs, evidence, and intelligence."
      />
      <main className="flex-1 overflow-y-auto">
        {query.isLoading ? (
          <p className="p-6 text-sm text-muted-foreground">Loading Motor 360…</p>
        ) : null}
        {query.isError ? (
          <p className="p-6 text-sm text-destructive">
            Failed to load Motor 360 bundle for this motor.
          </p>
        ) : null}

        {motor ? (
          <div className="mx-auto max-w-6xl space-y-4 px-5 py-4">
            <section className="relative overflow-hidden rounded-lg border border-border bg-gradient-to-r from-[#0d3d40] via-[#134e52] to-[#1a3a4a] px-5 py-5 text-white shadow-sm">
              <div className="pointer-events-none absolute inset-0 opacity-30 [background-image:radial-gradient(circle_at_20%_20%,#2dd4bf55,transparent_40%),radial-gradient(circle_at_80%_0%,#f59e0b33,transparent_35%)]" />
              <div className="relative flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-teal-100/80">
                    Industrial Brain AI · Motor 360
                  </p>
                  <h1 className="mt-1 text-2xl font-semibold tracking-tight">
                    {motor.name}
                  </h1>
                  <p className="mt-2 text-sm text-teal-50/90">
                    Frame {motor.frame_size ?? "—"} ·{" "}
                    {motor.power_kw != null ? `${motor.power_kw} kW` : "—"} ·{" "}
                    {motor.voltage ?? "—"} · {motor.ie_class ?? "—"}
                    {drawings[0] ? ` · Drawing ${drawings[0]}` : ""}
                  </p>
                  <p className="mt-1 text-xs text-teal-100/70">{motor.code}</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="rounded-md bg-white/10 px-3 py-2 text-right backdrop-blur">
                    <p className="text-[10px] uppercase tracking-wide text-teal-100/80">
                      Health
                    </p>
                    <p className="text-lg font-semibold">
                      {bundle?.health
                        ? `${Math.round(bundle.health.score)}/100`
                        : "—"}
                    </p>
                    <p className="text-xs uppercase text-teal-50/90">
                      {bundle?.health?.risk_level ?? "unknown"}
                    </p>
                  </div>
                  <Link
                    href={`/copilot?motor_id=${motor.id}`}
                    className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-accent-foreground"
                  >
                    Copilot
                  </Link>
                </div>
              </div>
            </section>

            <div className="grid gap-4 md:grid-cols-2">
              <section className="rounded-lg border border-border bg-card p-4">
                <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  AI knowledge summary
                </h2>
                <p className="mt-3 text-sm leading-relaxed text-foreground">
                  {summaryText}
                </p>
                {bundle?.summary?.honesty_note ? (
                  <p className="mt-2 text-xs text-muted-foreground">
                    {bundle.summary.honesty_note}
                  </p>
                ) : null}
              </section>
              <section className="rounded-lg border border-border bg-card p-4">
                <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Health & risk
                </h2>
                <div className="mt-3 h-2 overflow-hidden rounded bg-muted">
                  <div
                    className="h-full bg-accent transition-all duration-700"
                    style={{
                      width: `${Math.min(100, Math.max(0, bundle?.health?.score ?? 0))}%`,
                    }}
                  />
                </div>
                <ul className="mt-3 space-y-2">
                  {bullets.slice(0, 5).map((b, i) => (
                    <li key={i} className="text-sm text-muted-foreground">
                      <span className="text-foreground">•</span> {b}
                    </li>
                  ))}
                  {!bullets.length ? (
                    <li className="text-sm text-muted-foreground">
                      No evidence bullets yet.
                    </li>
                  ) : null}
                </ul>
              </section>
            </div>

            <section className="rounded-lg border border-border bg-card p-4">
              <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                AI recommendations
              </h2>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                {recs.map((rec, i) => (
                  <div key={i} className="border-l-2 border-accent pl-3">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-accent">
                      {rec.category}
                    </p>
                    <p className="mt-1 text-sm font-medium">{rec.title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                      {rec.rationale}
                    </p>
                  </div>
                ))}
                {!recs.length ? (
                  <p className="text-sm text-muted-foreground">
                    No recommendations generated yet.
                  </p>
                ) : null}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-card">
              <div className="flex flex-wrap gap-1 border-b border-border px-2 py-2">
                {TABS.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTab(t)}
                    className={cn(
                      "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                      tab === t
                        ? "bg-accent text-accent-foreground"
                        : "text-muted-foreground hover:bg-muted",
                    )}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <div className="p-4">
                {tab === "Timeline" ? (
                  <ul className="space-y-3">
                    {timeline.map((ev) => (
                      <li key={ev.id} className="flex gap-3 text-sm">
                        <span className="w-28 shrink-0 text-xs text-muted-foreground">
                          {String(ev.event_at).slice(0, 10)}
                          {ev.is_estimated ? " ≈" : ""}
                        </span>
                        <div>
                          <p className="font-medium">{ev.title}</p>
                          <p className="text-xs text-muted-foreground">
                            {ev.event_type}
                            {ev.is_estimated ? " · estimated date" : ""}
                          </p>
                        </div>
                      </li>
                    ))}
                    {!timeline.length ? (
                      <p className="text-sm text-muted-foreground">
                        No timeline events yet.
                      </p>
                    ) : null}
                  </ul>
                ) : null}

                {tab === "Documents" ? <DocGroups docs={docs} /> : null}
                {tab === "Tests" ? (
                  <DocGroups
                    docs={{
                      test_report: docs.test_report ?? docs.tests ?? [],
                    }}
                  />
                ) : null}
                {tab === "Drawings" ? (
                  <ul className="space-y-2">
                    {drawings.map((d) => (
                      <li key={d}>
                        <Link
                          href={`/drawings?q=${encodeURIComponent(d)}`}
                          className="text-sm text-accent hover:underline"
                        >
                          {d}
                        </Link>
                      </li>
                    ))}
                    {!drawings.length ? (
                      <p className="text-sm text-muted-foreground">
                        No drawing numbers linked.
                      </p>
                    ) : null}
                  </ul>
                ) : null}
                {tab === "Compliance" ? (
                  <DocGroups
                    docs={{
                      compliance:
                        docs.compliance ??
                        docs.certification ??
                        docs.certificate ??
                        docs.regulation ??
                        [],
                    }}
                  />
                ) : null}
                {tab === "Graph" ? (
                  <MiniGraph
                    nodes={bundle?.subgraph?.nodes ?? []}
                    edges={bundle?.subgraph?.edges ?? []}
                  />
                ) : null}
              </div>
            </section>

            {bundle?.related_assets?.length ? (
              <section>
                <h2 className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Related assets
                </h2>
                <div className="flex flex-wrap gap-2">
                  {bundle.related_assets.map((a) => (
                    <Link
                      key={a.id}
                      href={`/motors/${a.id}`}
                      className="rounded-md border border-border bg-card px-3 py-1.5 text-sm hover:border-accent"
                    >
                      {a.name}
                    </Link>
                  ))}
                </div>
              </section>
            ) : null}
          </div>
        ) : null}
      </main>
    </>
  );
}

function DocGroups({
  docs,
}: {
  docs: Record<string, { id: string; title: string; status: string }[]>;
}) {
  const entries = Object.entries(docs).filter(([, v]) => v.length > 0);
  if (!entries.length) {
    return (
      <p className="text-sm text-muted-foreground">No documents in this panel.</p>
    );
  }
  return (
    <div className="space-y-4">
      {entries.map(([cat, items]) => (
        <div key={cat}>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            {cat.replaceAll("_", " ")}
          </p>
          <ul className="mt-2 space-y-1">
            {items.map((d) => (
              <li key={d.id} className="text-sm">
                <Link
                  href={`/documents?q=${encodeURIComponent(d.title)}`}
                  className="hover:text-accent"
                >
                  {d.title}
                </Link>
                <span className="ml-2 text-xs text-muted-foreground">
                  {d.status}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
