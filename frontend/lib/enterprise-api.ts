/** Phase 5 Enterprise API clients — admin, audit, ops. */

import { apiClient } from "@/lib/api-client";

export type AdminRole = {
  id: string;
  code: string;
  name: string;
  description?: string | null;
};

export type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  roles: AdminRole[];
};

export type AuditEvent = {
  id: string;
  action: string;
  resource_type?: string | null;
  resource_id?: string | null;
  actor_user_id?: string | null;
  ip_address?: string | null;
  details?: Record<string, unknown> | null;
  created_at?: string | null;
};

export type OpsHealth = {
  api: {
    request_count: number;
    error_count: number;
    avg_latency_ms: number;
    max_latency_ms: number;
  };
  workers: {
    queue_depth: number;
    dead_letter_open: number;
  };
  security: {
    environment: string;
    ok: boolean;
    issues: string[];
    warnings: string[];
    cors_origins: string[];
  };
  status: string;
};

export async function fetchAdminUsers(): Promise<AdminUser[]> {
  return apiClient<AdminUser[]>("/admin/users");
}

export async function fetchAdminRoles(): Promise<AdminRole[]> {
  return apiClient<AdminRole[]>("/admin/roles");
}

export async function createAdminUser(body: {
  email: string;
  display_name: string;
  password: string;
  role_codes: string[];
  is_active?: boolean;
}): Promise<AdminUser> {
  return apiClient<AdminUser>("/admin/users", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function setUserRoles(
  userId: string,
  role_codes: string[],
): Promise<AdminUser> {
  return apiClient<AdminUser>(`/admin/users/${userId}/roles`, {
    method: "PUT",
    body: JSON.stringify({ role_codes }),
  });
}

export async function setUserActive(
  userId: string,
  is_active: boolean,
): Promise<AdminUser> {
  return apiClient<AdminUser>(`/admin/users/${userId}/active`, {
    method: "PUT",
    body: JSON.stringify({ is_active }),
  });
}

export async function fetchAuditEvents(params?: {
  action?: string;
  limit?: number;
}): Promise<{ items: AuditEvent[]; total: number }> {
  const qs = new URLSearchParams();
  if (params?.action) qs.set("action", params.action);
  if (params?.limit) qs.set("limit", String(params.limit));
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiClient(`/admin/audit${suffix}`);
}

export async function exportAuditEvents(limit = 500): Promise<{
  events: AuditEvent[];
  count: number;
}> {
  return apiClient(`/admin/audit/export?limit=${limit}`);
}

export async function fetchOpsHealth(): Promise<OpsHealth> {
  return apiClient<OpsHealth>("/ops/health-dashboard");
}
