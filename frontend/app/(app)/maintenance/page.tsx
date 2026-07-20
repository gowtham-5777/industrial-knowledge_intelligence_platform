"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppHeader } from "@/components/layout/app-header";
import { fetchMaintenance, fetchRca } from "@/lib/industrial-api";
import { fetchHeroMotors, fetchMotors } from "@/lib/motors-api";

export default function MaintenancePage() {
  const [motorId, setMotorId] = useState<string>("");
  const [motors, setMotors] = useState<{ id: string; code: string; name: string }[]>(
    [],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [list, hero] = await Promise.all([
        fetchMotors({ limit: 50 }),
        fetchHeroMotors().catch(() => null),
      ]);
      if (cancelled) return;
      setMotors(list.items.map((m) => ({ id: m.id, code: m.code, name: m.name })));
      setMotorId(hero?.hero?.id || list.items[0]?.id || "");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const maintenance = useQuery({
    queryKey: ["maintenance", motorId],
    queryFn: () => fetchMaintenance(motorId),
    enabled: Boolean(motorId),
  });
  const rca = useQuery({
    queryKey: ["rca", motorId],
    queryFn: () => fetchRca(motorId),
    enabled: Boolean(motorId),
  });

  const m = maintenance.data;
  const r = rca.data;

  return (
    <>
      <AppHeader
        title="Maintenance Intelligence"
        description="IEC test metric trends, anomaly patterns, and test-anomaly RCA."
      />
      <main className="flex-1 overflow-y-auto p-5">
        <div className="mx-auto max-w-5xl space-y-5">
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex min-w-[240px] flex-col gap-1 text-xs">
              <span className="font-medium text-muted-foreground">Motor</span>
              <select
                className="rounded-md border border-border bg-card px-3 py-2 text-sm"
                value={motorId}
                onChange={(e) => setMotorId(e.target.value)}
              >
                {motors.map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.name} ({x.code})
                  </option>
                ))}
              </select>
            </label>
            {motorId ? (
              <Link
                href={`/copilot?motor_id=${motorId}`}
                className="rounded-md border border-border px-3 py-2 text-xs hover:border-accent"
              >
                Ask Copilot
              </Link>
            ) : null}
          </div>

          {maintenance.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading trends…</p>
          ) : null}

          {m ? (
            <section className="space-y-3">
              <div className="flex flex-wrap gap-4 text-sm">
                <span>
                  Reports: <strong>{m.report_count}</strong>
                </span>
                <span>
                  Measurements: <strong>{m.measurement_count}</strong>
                </span>
                <span>
                  Anomalies: <strong>{m.anomalies.length}</strong>
                </span>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                {m.trends.length === 0 ? (
                  <p className="text-sm text-muted-foreground md:col-span-2">
                    No structured test measurements indexed for this motor yet.
                  </p>
                ) : null}
                {m.trends.map((t) => {
                  const max = Math.max(...t.values, 1);
                  return (
                    <article
                      key={t.parameter}
                      className="rounded-lg border border-border bg-card p-4"
                    >
                      <h3 className="text-sm font-semibold">{t.parameter}</h3>
                      <p className="text-xs text-muted-foreground">
                        mean {t.mean ?? "—"}
                        {t.unit ? ` ${t.unit}` : ""} · latest {t.latest ?? "—"}
                      </p>
                      <div className="mt-3 flex h-16 items-end gap-1">
                        {t.values.map((v, i) => (
                          <div
                            key={i}
                            className="flex-1 rounded-t bg-accent/70"
                            style={{ height: `${Math.max(8, (v / max) * 100)}%` }}
                            title={String(v)}
                          />
                        ))}
                      </div>
                    </article>
                  );
                })}
              </div>

              {m.anomalies.length > 0 ? (
                <section className="rounded-lg border border-border bg-card p-4">
                  <h3 className="text-sm font-semibold">Anomaly patterns</h3>
                  <ul className="mt-2 space-y-2 text-sm">
                    {m.anomalies.map((a, i) => (
                      <li key={i} className="border-b border-border/60 pb-2 last:border-0">
                        <span className="font-medium">{a.parameter}</span>{" "}
                        <span className="text-xs uppercase text-muted-foreground">
                          {a.severity}
                        </span>
                        <p className="text-xs text-muted-foreground">{a.rationale}</p>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </section>
          ) : null}

          <section className="rounded-lg border border-border bg-gradient-to-br from-[#eef5f6] to-background p-4 dark:from-[#0f1a1c]">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-semibold">Test Anomaly RCA</h2>
              {r ? (
                <span className="text-xs text-muted-foreground">
                  confidence {(r.confidence * 100).toFixed(0)}%
                </span>
              ) : null}
            </div>
            {rca.isLoading ? (
              <p className="mt-2 text-sm text-muted-foreground">Building 5-Why…</p>
            ) : null}
            {r?.honesty_note ? (
              <p className="mt-2 text-xs text-muted-foreground">{r.honesty_note}</p>
            ) : null}
            {r?.anomaly ? (
              <p className="mt-2 text-sm">
                Focus:{" "}
                <strong>{String(r.anomaly.parameter || "performance")}</strong>
                {r.anomaly.rationale ? (
                  <span className="text-muted-foreground">
                    {" "}
                    — {String(r.anomaly.rationale)}
                  </span>
                ) : null}
              </p>
            ) : null}
            <ol className="mt-3 space-y-3">
              {(r?.five_why || []).map((step) => (
                <li key={step.level} className="text-sm">
                  <p className="font-medium">
                    {step.level}. {step.question}
                  </p>
                  <p className="text-muted-foreground">{step.answer}</p>
                </li>
              ))}
            </ol>
            {r?.recommended_actions?.length ? (
              <ul className="mt-4 list-disc space-y-1 pl-5 text-sm">
                {r.recommended_actions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            ) : null}
          </section>
        </div>
      </main>
    </>
  );
}
