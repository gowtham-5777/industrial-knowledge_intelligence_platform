"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { AppHeader } from "@/components/layout/app-header";
import {
  confirmHeroMotors,
  enrichFromCatalog,
  fetchMotors,
  type MotorModel,
} from "@/lib/motors-api";

function MotorRow({ motor }: { motor: MotorModel }) {
  return (
    <Link
      href={`/motors/${motor.id}`}
      className="grid grid-cols-[1.4fr_0.7fr_0.6fr_0.5fr_0.5fr] gap-3 border-b border-border px-4 py-3 text-sm transition-colors hover:bg-muted/50"
    >
      <div className="min-w-0">
        <p className="truncate font-medium text-foreground">{motor.name}</p>
        <p className="truncate text-xs text-muted-foreground">{motor.code}</p>
      </div>
      <span className="self-center text-muted-foreground">
        {motor.frame_size ?? "—"}
      </span>
      <span className="self-center text-muted-foreground">
        {motor.power_kw != null ? `${motor.power_kw} kW` : "—"}
      </span>
      <span className="self-center text-muted-foreground">
        {motor.ie_class ?? "—"}
      </span>
      <span className="self-center">
        {motor.is_hero ? (
          <span className="text-xs font-semibold text-accent">Hero</span>
        ) : motor.is_supporting ? (
          <span className="text-xs text-muted-foreground">Support</span>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </span>
    </Link>
  );
}

export default function MotorsPage() {
  const [q, setQ] = useState("");
  const [frame, setFrame] = useState("");
  const [ie, setIe] = useState("");
  const [busy, setBusy] = useState(false);

  const query = useQuery({
    queryKey: ["motors", q, frame, ie],
    queryFn: () =>
      fetchMotors({
        q: q || undefined,
        frame_size: frame || undefined,
        ie_class: ie || undefined,
        limit: 100,
      }),
  });

  const frames = useMemo(() => {
    const set = new Set<string>();
    for (const m of query.data?.items ?? []) {
      if (m.frame_size) set.add(m.frame_size);
    }
    return Array.from(set).sort();
  }, [query.data]);

  async function bootstrap() {
    setBusy(true);
    try {
      await enrichFromCatalog();
      await confirmHeroMotors();
      await query.refetch();
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <AppHeader
        title="Motor Explorer"
        description="Browse, search, and open Motor 360 for any registered model."
      />
      <main className="flex-1 overflow-y-auto">
        <div className="border-b border-border bg-gradient-to-br from-[#eef5f6] via-background to-[#f7f3ea] px-5 py-4 dark:from-[#0f1a1c] dark:via-background dark:to-[#16120c]">
          <div className="mx-auto flex max-w-6xl flex-wrap items-end gap-3">
            <label className="min-w-[200px] flex-1 text-xs text-muted-foreground">
              Search
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Code, name, frame…"
                className="mt-1 w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground outline-none ring-accent focus:ring-2"
              />
            </label>
            <label className="w-32 text-xs text-muted-foreground">
              Frame
              <select
                value={frame}
                onChange={(e) => setFrame(e.target.value)}
                className="mt-1 w-full rounded-md border border-border bg-card px-2 py-2 text-sm"
              >
                <option value="">All</option>
                {frames.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </label>
            <label className="w-28 text-xs text-muted-foreground">
              IE class
              <select
                value={ie}
                onChange={(e) => setIe(e.target.value)}
                className="mt-1 w-full rounded-md border border-border bg-card px-2 py-2 text-sm"
              >
                <option value="">All</option>
                {["IE2", "IE3", "IE4"].map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              disabled={busy}
              onClick={() => void bootstrap()}
              className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-accent-foreground disabled:opacity-60"
            >
              {busy ? "Seeding…" : "Seed hero set"}
            </button>
          </div>
        </div>

        <div className="mx-auto max-w-6xl px-5 py-4">
          <div className="overflow-hidden rounded-lg border border-border bg-card">
            <div className="grid grid-cols-[1.4fr_0.7fr_0.6fr_0.5fr_0.5fr] gap-3 border-b border-border bg-muted/40 px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              <span>Motor</span>
              <span>Frame</span>
              <span>Power</span>
              <span>IE</span>
              <span>Role</span>
            </div>
            {query.isLoading ? (
              <p className="px-4 py-8 text-sm text-muted-foreground">
                Loading motors…
              </p>
            ) : null}
            {query.isError ? (
              <p className="px-4 py-8 text-sm text-destructive">
                Could not load motors. Confirm API auth and Phase 3 routes.
              </p>
            ) : null}
            {(query.data?.items ?? []).map((m) => (
              <MotorRow key={m.id} motor={m} />
            ))}
            {query.data && query.data.items.length === 0 ? (
              <p className="px-4 py-8 text-sm text-muted-foreground">
                No motors yet. Use “Seed hero set” or run catalog enrichment.
              </p>
            ) : null}
          </div>
          {query.data ? (
            <p className="mt-3 text-xs text-muted-foreground">
              Showing {query.data.items.length} of {query.data.total}
            </p>
          ) : null}
        </div>
      </main>
    </>
  );
}
