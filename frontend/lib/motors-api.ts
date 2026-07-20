/** Phase 3 motor / asset API types & helpers — aligned to Motor360Out. */

import { apiClient } from "@/lib/api-client";

export type MotorModel = {
  id: string;
  code: string;
  name: string;
  frame_size: string | null;
  power_kw: number | null;
  voltage: string | null;
  ie_class: string | null;
  poles: number | null;
  mounting: string | null;
  cooling: string | null;
  asset_id: string | null;
  family_id: string;
  family_code: string | null;
  product_line_code: string | null;
  aliases: { alias: string; alias_type: string }[];
  is_hero: boolean;
  is_supporting: boolean;
  metadata?: Record<string, unknown> | null;
};

export type MotorList = {
  items: MotorModel[];
  total: number;
  limit: number;
  offset: number;
};

export type HeroMotors = {
  hero: MotorModel;
  supporting: MotorModel[];
  confirmed_at: string | null;
};

export type HealthScore = {
  score: number;
  risk_level: string;
  evidence?: { text?: string; factor?: string; passed?: boolean }[];
  reasoning?: { bullet: string; evidence?: string }[];
  computed_at: string;
};

export type AiSummary = {
  overview?: string;
  summary_text?: string;
  honesty_note?: string | null;
  generated_at: string;
  source_doc_ids?: string[] | null;
};

export type RecommendationCard = {
  title: string;
  category: string;
  rationale: string;
  confidence: number;
  citations: { doc_id: string; chunk_id?: string | null }[];
};

export type TimelineEvent = {
  id: string;
  event_type: string;
  title: string;
  description: string | null;
  event_at: string;
  is_estimated: boolean;
  document_id: string | null;
};

export type DocPanelItem = {
  id: string;
  title: string;
  status: string;
  doc_category?: string | null;
  category?: string | null;
  doc_type?: string | null;
  drawing_number?: string | null;
};

export type GraphNode = {
  id: string;
  label: string;
  type: string;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  label?: string;
};

export type Motor360Bundle = {
  motor: MotorModel;
  summary: AiSummary;
  health: HealthScore;
  recommendations: { items: RecommendationCard[] } | RecommendationCard[];
  timeline: { items: TimelineEvent[] } | TimelineEvent[];
  documents?: { category: string; items: DocPanelItem[] }[];
  documents_by_category?: Record<string, DocPanelItem[]>;
  related_assets: {
    id: string;
    code?: string;
    name: string;
    relation?: string;
  }[];
  drawings?: { drawing_number: string; normalized: string }[];
  drawing_numbers?: string[];
  subgraph: { nodes: GraphNode[]; edges: GraphEdge[] };
};

export type DashboardKpis = {
  documents_discovered?: number;
  documents_ingested?: number;
  documents_indexed?: number;
  motor_models?: number;
  catalog_count?: number;
  document_count?: number;
  indexed_count?: number;
  motor_count?: number;
  hero_health_score?: number | null;
  hero_risk_level?: string | null;
  hero_health?: { score: number; risk_level: string } | null;
  indexing?: Record<string, unknown> | null;
  indexing_status?: Record<string, unknown> | null;
};

export type SearchResults = {
  query: string;
  motors: MotorModel[];
  documents: DocPanelItem[];
  drawings: { drawing_number: string; normalized: string; id: string }[];
};

export type DrawingBundle = {
  drawing_number: string;
  normalized: string;
  documents: DocPanelItem[];
  motors: MotorModel[];
};

function qs(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export function asRecCards(
  recs: Motor360Bundle["recommendations"],
): RecommendationCard[] {
  if (Array.isArray(recs)) return recs;
  return recs?.items ?? [];
}

export function asTimeline(
  timeline: Motor360Bundle["timeline"],
): TimelineEvent[] {
  if (Array.isArray(timeline)) return timeline;
  return timeline?.items ?? [];
}

export function asDocMap(
  bundle: Motor360Bundle,
): Record<string, DocPanelItem[]> {
  if (bundle.documents_by_category) return bundle.documents_by_category;
  const map: Record<string, DocPanelItem[]> = {};
  for (const panel of bundle.documents ?? []) {
    map[panel.category] = panel.items;
  }
  return map;
}

export function asDrawings(bundle: Motor360Bundle): string[] {
  if (bundle.drawing_numbers?.length) return bundle.drawing_numbers;
  return (bundle.drawings ?? []).map((d) => d.drawing_number);
}

export function healthBullets(health: HealthScore | null | undefined): string[] {
  if (!health) return [];
  if (health.reasoning?.length) return health.reasoning.map((r) => r.bullet);
  return (health.evidence ?? []).map((e) => e.text || e.factor || "");
}

export function fetchMotors(params: {
  q?: string;
  frame_size?: string;
  ie_class?: string;
  power_kw_min?: number;
  power_kw_max?: number;
  limit?: number;
  offset?: number;
}) {
  return apiClient<MotorList>(`/api/v1/motors${qs(params)}`);
}

export function fetchMotor(id: string) {
  return apiClient<MotorModel>(`/api/v1/motors/${encodeURIComponent(id)}`);
}

export function fetchHeroMotors() {
  return apiClient<HeroMotors>("/api/v1/motors/hero");
}

export function confirmHeroMotors() {
  return apiClient<HeroMotors>("/api/v1/motors/hero/confirm", { method: "POST" });
}

export function enrichFromCatalog() {
  return apiClient<{ codes_seen: number; created: number; updated: number }>(
    "/api/v1/motors/enrich-from-catalog",
    { method: "POST" },
  );
}

export function fetchMotor360(id: string) {
  return apiClient<Motor360Bundle>(
    `/api/v1/motor360/${encodeURIComponent(id)}`,
  );
}

export function fetchDashboardKpis() {
  return apiClient<DashboardKpis>("/api/v1/dashboard/kpis");
}

export function fetchSearch(q: string) {
  return apiClient<SearchResults>(`/api/v1/search${qs({ q })}`);
}

export function fetchDrawings(q?: string) {
  return apiClient<{
    items: { id: string; drawing_number: string; normalized: string }[];
  }>(`/api/v1/drawings${qs({ q })}`);
}

export function fetchDrawingBundle(drawingNumber: string) {
  return apiClient<DrawingBundle>(
    `/api/v1/drawings/${encodeURIComponent(drawingNumber)}`,
  );
}

export function fetchMotorSubgraph(id: string) {
  return apiClient<{ nodes: GraphNode[]; edges: GraphEdge[] }>(
    `/api/v1/graph/motors/${encodeURIComponent(id)}/subgraph`,
  );
}

export function fetchIndexingStatus() {
  return apiClient<Record<string, unknown>>("/api/v1/indexing/status");
}
