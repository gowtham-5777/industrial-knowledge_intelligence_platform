"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { AppHeader } from "@/components/layout/app-header";
import { MiniGraph } from "@/components/motors/mini-graph";
import { fetchHeroMotors, fetchMotorSubgraph } from "@/lib/motors-api";

export default function GraphPage() {
  const hero = useQuery({
    queryKey: ["hero-motors"],
    queryFn: fetchHeroMotors,
  });
  const [motorId, setMotorId] = useState<string>("");

  const effectiveId = motorId || hero.data?.hero.id || "";

  const subgraph = useQuery({
    queryKey: ["subgraph", effectiveId],
    queryFn: () => fetchMotorSubgraph(effectiveId),
    enabled: Boolean(effectiveId),
  });

  return (
    <>
      <AppHeader
        title="Knowledge Graph"
        description="Motor-centered neighborhood visualization."
      />
      <main className="flex-1 overflow-y-auto p-5">
        <div className="mx-auto max-w-5xl space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs text-muted-foreground">
              Motor id / hero default
              <input
                value={motorId}
                onChange={(e) => setMotorId(e.target.value)}
                placeholder={hero.data?.hero.id ?? "Confirm hero first"}
                className="mt-1 block w-80 rounded-md border border-border bg-card px-3 py-2 text-sm"
              />
            </label>
          </div>
          {subgraph.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading subgraph…</p>
          ) : null}
          {subgraph.data ? (
            <MiniGraph
              nodes={subgraph.data.nodes}
              edges={subgraph.data.edges}
            />
          ) : (
            <p className="text-sm text-muted-foreground">
              No subgraph yet — seed the hero motor and index linked documents.
            </p>
          )}
        </div>
      </main>
    </>
  );
}
