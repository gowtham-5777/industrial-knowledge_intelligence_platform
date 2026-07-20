"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { AppHeader } from "@/components/layout/app-header";
import { fetchDrawingBundle, fetchDrawings } from "@/lib/motors-api";

function DrawingsInner() {
  const sp = useSearchParams();
  const initial = sp.get("q") ?? "";
  const [q, setQ] = useState(initial);
  const [selected, setSelected] = useState(initial);

  const list = useQuery({
    queryKey: ["drawings", q],
    queryFn: () => fetchDrawings(q || undefined),
  });

  const bundle = useQuery({
    queryKey: ["drawing-bundle", selected],
    queryFn: () => fetchDrawingBundle(selected),
    enabled: Boolean(selected),
  });

  return (
    <main className="flex-1 overflow-y-auto p-5">
      <div className="mx-auto grid max-w-6xl gap-4 lg:grid-cols-[280px_1fr]">
        <aside className="rounded-lg border border-border bg-card p-3">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Filter drawings…"
            className="mb-3 w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
          />
          <ul className="max-h-[70vh] space-y-1 overflow-y-auto">
            {(list.data?.items ?? []).map((d) => (
              <li key={d.id}>
                <button
                  type="button"
                  onClick={() => setSelected(d.drawing_number)}
                  className={`w-full rounded px-2 py-1.5 text-left text-sm ${
                    selected === d.drawing_number
                      ? "bg-accent text-accent-foreground"
                      : "hover:bg-muted"
                  }`}
                >
                  {d.drawing_number}
                </button>
              </li>
            ))}
          </ul>
        </aside>
        <section className="rounded-lg border border-border bg-card p-4">
          {!selected ? (
            <p className="text-sm text-muted-foreground">
              Select a drawing number to inspect cross-references.
            </p>
          ) : bundle.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading bundle…</p>
          ) : bundle.data ? (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold">
                  {bundle.data.drawing_number}
                </h2>
                <p className="text-xs text-muted-foreground">
                  Normalized: {bundle.data.normalized}
                </p>
              </div>
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Linked motors
                </h3>
                <ul className="mt-2 space-y-1">
                  {bundle.data.motors.map((m) => (
                    <li key={m.id}>
                      <Link
                        href={`/motors/${m.id}`}
                        className="text-sm text-accent hover:underline"
                      >
                        {m.name}
                      </Link>
                    </li>
                  ))}
                  {!bundle.data.motors.length ? (
                    <li className="text-sm text-muted-foreground">None</li>
                  ) : null}
                </ul>
              </div>
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Documents
                </h3>
                <ul className="mt-2 space-y-1">
                  {bundle.data.documents.map((d) => (
                    <li key={d.id} className="text-sm">
                      {d.title}
                    </li>
                  ))}
                  {!bundle.data.documents.length ? (
                    <li className="text-sm text-muted-foreground">None</li>
                  ) : null}
                </ul>
              </div>
            </div>
          ) : (
            <p className="text-sm text-destructive">Drawing not found.</p>
          )}
        </section>
      </div>
    </main>
  );
}

export default function DrawingsPage() {
  return (
    <>
      <AppHeader
        title="Drawing Explorer"
        description="Drawing-number cross-reference across documents and motors."
      />
      <Suspense
        fallback={
          <p className="p-5 text-sm text-muted-foreground">Loading…</p>
        }
      >
        <DrawingsInner />
      </Suspense>
    </>
  );
}
