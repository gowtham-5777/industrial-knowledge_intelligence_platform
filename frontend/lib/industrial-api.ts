/** Phase 4 Industrial AI API clients — Copilot, maintenance, RCA, compliance, analytics. */

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getApiBaseUrl } from "@/lib/session";

export type RouteResult = {
  intent: string;
  confidence: number;
  entities: {
    motor_id: string | null;
    motor_code: string | null;
    serial_number: string | null;
    drawing_number: string | null;
    aliases_matched: string[];
  };
  tools: string[];
  model_tier: string;
  rationale: string;
};

export type Citation = {
  citation?: string | null;
  document_id?: string | null;
  chunk_id?: string | null;
  text?: string | null;
  title?: string | null;
  score?: number | null;
};

export type ChatResponse = {
  session_id: string;
  message_id: string;
  answer: string;
  intent?: string | null;
  confidence?: number | null;
  citations: Citation[];
  reasoning?: string | null;
  verified?: boolean;
  degraded?: boolean;
  route?: RouteResult | Record<string, unknown> | null;
};

export type CopilotSession = {
  id: string;
  motor_id: string | null;
  title: string | null;
  status: string;
  messages: {
    id: string;
    role: string;
    content: string;
    intent?: string | null;
    confidence?: number | null;
    citations?: Citation[];
    reasoning?: string | null;
  }[];
};

export type MaintenanceOut = {
  motor_id: string;
  motor_code: string;
  trends: {
    parameter: string;
    unit: string | null;
    values: number[];
    mean: number | null;
    latest: number | null;
  }[];
  anomalies: {
    parameter: string;
    value: number;
    mean: number;
    deviation_pct: number;
    severity: string;
    rationale: string;
  }[];
  report_count: number;
  measurement_count: number;
};

export type RcaOut = {
  motor_id: string;
  motor_code: string;
  anomaly: Record<string, unknown> | null;
  five_why: {
    level: number;
    question: string;
    answer: string;
    evidence: Citation[];
  }[];
  similar_reports: Citation[];
  recommended_actions: string[];
  confidence: number;
  honesty_note?: string | null;
};

export type ComplianceOut = {
  motor_id: string;
  motor_code: string;
  coverage: number;
  met: number;
  total: number;
  gaps: { requirement_code: string; title: string; severity: string }[];
  items: {
    requirement_code: string;
    title: string;
    severity: string;
    status: string;
    evidence?: { document_id?: string; title?: string } | null;
    description?: string | null;
  }[];
};

export type AnalyticsOut = {
  catalog_total: number;
  documents_total: number;
  indexed_ready: number;
  motor_models: number;
  coverage_pct: number;
  domains: { domain: string; catalog_count: number; ingested_count: number }[];
  velocity: { day: string; jobs_completed: number; jobs_failed: number }[];
  jobs_by_status: Record<string, number>;
  generated_at: string;
};

export async function createCopilotSession(motorId?: string | null) {
  return apiClient<CopilotSession>("/api/v1/copilot/sessions", {
    method: "POST",
    body: JSON.stringify({ motor_id: motorId || null }),
  });
}

export async function routeQuery(query: string, motorId?: string | null) {
  return apiClient<RouteResult>("/api/v1/copilot/route", {
    method: "POST",
    body: JSON.stringify({ query, motor_id: motorId || null }),
  });
}

export async function chatCopilot(opts: {
  message: string;
  sessionId?: string | null;
  motorId?: string | null;
}) {
  return apiClient<ChatResponse>("/api/v1/copilot/chat", {
    method: "POST",
    body: JSON.stringify({
      message: opts.message,
      session_id: opts.sessionId || null,
      motor_id: opts.motorId || null,
      stream: false,
    }),
  });
}

export async function submitCopilotFeedback(opts: {
  rating: number;
  sessionId?: string | null;
  messageId?: string | null;
  comment?: string | null;
}) {
  return apiClient<{ id: string }>("/api/v1/copilot/feedback", {
    method: "POST",
    body: JSON.stringify({
      rating: opts.rating,
      session_id: opts.sessionId || null,
      message_id: opts.messageId || null,
      comment: opts.comment || null,
    }),
  });
}

/** SSE streaming chat — yields parsed events. */
export async function* streamCopilotChat(opts: {
  message: string;
  sessionId?: string | null;
  motorId?: string | null;
  signal?: AbortSignal;
}): AsyncGenerator<{ event: string; data: unknown }> {
  const token = getAccessToken();
  const response = await fetch(`${getApiBaseUrl()}/api/v1/copilot/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      message: opts.message,
      session_id: opts.sessionId || null,
      motor_id: opts.motorId || null,
      stream: true,
    }),
    signal: opts.signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`Copilot stream failed (${response.status})`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const lines = part.split("\n");
      let event = "message";
      let data = "";
      for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (!data) continue;
      try {
        yield { event, data: JSON.parse(data) };
      } catch {
        yield { event, data };
      }
    }
  }
}

export async function fetchMaintenance(motorId: string) {
  return apiClient<MaintenanceOut>(`/api/v1/maintenance/${motorId}`);
}

export async function fetchRca(motorId: string, parameter?: string) {
  const qs = parameter ? `?parameter=${encodeURIComponent(parameter)}` : "";
  return apiClient<RcaOut>(`/api/v1/rca/${motorId}${qs}`);
}

export async function fetchCompliance(motorId: string) {
  return apiClient<ComplianceOut>(`/api/v1/compliance/motors/${motorId}`);
}

export async function fetchAnalytics() {
  return apiClient<AnalyticsOut>("/api/v1/analytics");
}
