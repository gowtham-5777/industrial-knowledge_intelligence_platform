"use client";

import type { GraphEdge, GraphNode } from "@/lib/motors-api";

/** Lightweight SVG mini-graph for Asset 360 (no heavy graph lib required). */
export function MiniGraph({
  nodes,
  edges,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
}) {
  if (!nodes.length) {
    return (
      <p className="text-sm text-muted-foreground">
        No graph neighborhood available for this motor yet.
      </p>
    );
  }

  const width = 640;
  const height = 280;
  const cx = width / 2;
  const cy = height / 2;
  const ring = Math.min(width, height) * 0.32;

  const center =
    nodes.find((n) => n.type === "MotorModel" || n.type === "motor") ?? nodes[0];
  const others = nodes.filter((n) => n.id !== center.id);

  const positions = new Map<string, { x: number; y: number }>();
  positions.set(center.id, { x: cx, y: cy });
  others.forEach((n, i) => {
    const angle = (i / Math.max(others.length, 1)) * Math.PI * 2 - Math.PI / 2;
    positions.set(n.id, {
      x: cx + Math.cos(angle) * ring,
      y: cy + Math.sin(angle) * ring,
    });
  });

  return (
    <div className="overflow-hidden rounded-md border border-border bg-muted/20">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full">
        {edges.map((e) => {
          const s = positions.get(e.source);
          const t = positions.get(e.target);
          if (!s || !t) return null;
          return (
            <line
              key={e.id}
              x1={s.x}
              y1={s.y}
              x2={t.x}
              y2={t.y}
              stroke="currentColor"
              className="text-border"
              strokeWidth={1.5}
            />
          );
        })}
        {nodes.map((n) => {
          const p = positions.get(n.id);
          if (!p) return null;
          const isCenter = n.id === center.id;
          return (
            <g key={n.id}>
              <circle
                cx={p.x}
                cy={p.y}
                r={isCenter ? 22 : 14}
                className={isCenter ? "fill-accent" : "fill-card stroke-border"}
                strokeWidth={1.5}
              />
              <text
                x={p.x}
                y={p.y + (isCenter ? 36 : 28)}
                textAnchor="middle"
                className="fill-foreground text-[10px]"
              >
                {n.label.length > 22 ? `${n.label.slice(0, 20)}…` : n.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
