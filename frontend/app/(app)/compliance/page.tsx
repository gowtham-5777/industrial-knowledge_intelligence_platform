"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppHeader } from "@/components/layout/app-header";
import { fetchCompliance } from "@/lib/industrial-api";
import { fetchHeroMotors, fetchMotors } from "@/lib/motors-api";
import { cn } from "@/lib/utils";

export default function CompliancePage() {
  const [motorId, setMotorId] = useState("");
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

  const query = useQuery({
    queryKey: ["compliance", motorId],
    queryFn: () => fetchCompliance(motorId),
    enabled: Boolean(motorId),
  });

  const data = query.data;

  return (
    <>
      <AppHeader
        title="Compliance Intelligence"
        description="Checklist requirements, evidence links, and gap detection."
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
                {motors.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.code})
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

          {query.isLoading ? (
            <p className="text-sm text-muted-foreground">Assessing compliance…</p>
          ) : null}

          {data ? (
            <>
              <section className="overflow-hidden rounded-lg border border-border bg-gradient-to-r from-[#0d3d40] to-[#1a3a4a] px-5 py-4 text-white">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-teal-100/80">
                  Coverage
                </p>
                <p className="mt-1 text-3xl font-semibold">
                  {(data.coverage * 100).toFixed(0)}%
                </p>
                <p className="text-sm text-teal-50/90">
                  {data.met} of {data.total} requirements evidenced for{" "}
                  {data.motor_code}
                </p>
              </section>

              <section className="space-y-2">
                <h2 className="text-sm font-semibold">Requirements</h2>
                {data.items.map((item) => (
                  <article
                    key={item.requirement_code}
                    className={cn(
                      "rounded-lg border px-4 py-3",
                      item.status === "met"
                        ? "border-accent/40 bg-accent/5"
                        : "border-border bg-card",
                    )}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="text-sm font-medium">{item.title}</h3>
                      <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                        {item.status} · {item.severity}
                      </span>
                    </div>
                    {item.description ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        {item.description}
                      </p>
                    ) : null}
                    {item.evidence ? (
                      <p className="mt-2 text-xs">
                        Evidence: {item.evidence.title || item.evidence.document_id}
                      </p>
                    ) : (
                      <p className="mt-2 text-xs text-destructive">
                        Gap — not available in indexed knowledge
                      </p>
                    )}
                  </article>
                ))}
              </section>

              {data.gaps.length > 0 ? (
                <section className="rounded-lg border border-border bg-card p-4">
                  <h2 className="text-sm font-semibold">Open gaps</h2>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                    {data.gaps.map((g) => (
                      <li key={g.requirement_code}>
                        {g.title} ({g.severity})
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </>
          ) : null}
        </div>
      </main>
    </>
  );
}
