"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { AppHeader } from "@/components/layout/app-header";
import { fetchSearch } from "@/lib/motors-api";

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");

  const results = useQuery({
    queryKey: ["search", submitted],
    queryFn: () => fetchSearch(submitted),
    enabled: submitted.length > 0,
  });

  return (
    <>
      <AppHeader
        title="AI Search"
        description="Unified search across motors, documents, and drawing numbers."
      />
      <main className="flex-1 overflow-y-auto p-5">
        <div className="mx-auto max-w-3xl">
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setSubmitted(q.trim());
            }}
          >
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Motor code, drawing number, document title…"
              className="flex-1 rounded-md border border-border bg-card px-3 py-2 text-sm outline-none ring-accent focus:ring-2"
            />
            <button
              type="submit"
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground"
            >
              Search
            </button>
          </form>

          {results.data ? (
            <div className="mt-6 space-y-6">
              <ResultBlock title="Motors">
                {results.data.motors.map((m) => (
                  <Link
                    key={m.id}
                    href={`/motors/${m.id}`}
                    className="block border-b border-border py-2 text-sm hover:text-accent"
                  >
                    {m.name}{" "}
                    <span className="text-muted-foreground">({m.code})</span>
                  </Link>
                ))}
                {!results.data.motors.length ? (
                  <p className="text-sm text-muted-foreground">No motor hits.</p>
                ) : null}
              </ResultBlock>
              <ResultBlock title="Documents">
                {results.data.documents.map((d) => (
                  <div key={d.id} className="border-b border-border py-2 text-sm">
                    {d.title}
                    <span className="ml-2 text-xs text-muted-foreground">
                      {d.category ?? d.doc_type ?? d.status}
                    </span>
                  </div>
                ))}
                {!results.data.documents.length ? (
                  <p className="text-sm text-muted-foreground">No document hits.</p>
                ) : null}
              </ResultBlock>
              <ResultBlock title="Drawings">
                {results.data.drawings.map((d) => (
                  <Link
                    key={d.id}
                    href={`/drawings?q=${encodeURIComponent(d.drawing_number)}`}
                    className="block border-b border-border py-2 text-sm hover:text-accent"
                  >
                    {d.drawing_number}
                  </Link>
                ))}
                {!results.data.drawings.length ? (
                  <p className="text-sm text-muted-foreground">No drawing hits.</p>
                ) : null}
              </ResultBlock>
            </div>
          ) : null}
        </div>
      </main>
    </>
  );
}

function ResultBlock({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {title}
      </h2>
      <div className="mt-2 rounded-lg border border-border bg-card px-3">
        {children}
      </div>
    </section>
  );
}
