"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import {
  createAdminUser,
  exportAuditEvents,
  fetchAdminRoles,
  fetchAdminUsers,
  fetchAuditEvents,
  fetchOpsHealth,
  setUserActive,
  type AdminUser,
  type AuditEvent,
} from "@/lib/enterprise-api";

export default function AdminPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"users" | "audit" | "ops">("users");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [roleCode, setRoleCode] = useState("PlantOperator");
  const [error, setError] = useState<string | null>(null);

  const usersQuery = useQuery({
    queryKey: ["admin-users"],
    queryFn: fetchAdminUsers,
    enabled: tab === "users",
    retry: false,
  });
  const rolesQuery = useQuery({
    queryKey: ["admin-roles"],
    queryFn: fetchAdminRoles,
    enabled: tab === "users",
    retry: false,
  });
  const auditQuery = useQuery({
    queryKey: ["admin-audit"],
    queryFn: () => fetchAuditEvents({ limit: 50 }),
    enabled: tab === "audit",
    retry: false,
  });
  const opsQuery = useQuery({
    queryKey: ["ops-health"],
    queryFn: fetchOpsHealth,
    enabled: tab === "ops",
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: createAdminUser,
    onSuccess: () => {
      setEmail("");
      setDisplayName("");
      setPassword("");
      setError(null);
      void qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      setUserActive(id, active),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin-users"] }),
    onError: (err: Error) => setError(err.message),
  });

  const exportMutation = useMutation({
    mutationFn: () => exportAuditEvents(500),
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data.events, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "audit-export.json";
      a.click();
      URL.revokeObjectURL(url);
    },
    onError: (err: Error) => setError(err.message),
  });

  const roleOptions = useMemo(
    () => rolesQuery.data?.map((r) => r.code) ?? ["PlantOperator", "SystemAdmin"],
    [rolesQuery.data],
  );

  return (
    <main className="flex flex-1 flex-col gap-6 p-6">
      <header className="space-y-1">
        <h1 className="font-display text-3xl tracking-tight text-foreground">
          Administration
        </h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Users, roles, immutable audit events, and ops health for enterprise
          control.
        </p>
      </header>

      <div className="flex gap-2 border-b border-border pb-2">
        {(
          [
            ["users", "Users & roles"],
            ["audit", "Audit log"],
            ["ops", "Ops health"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => {
              setTab(id);
              setError(null);
            }}
            className={
              tab === id
                ? "border-b-2 border-foreground px-3 py-1.5 text-sm font-medium"
                : "px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
            }
          >
            {label}
          </button>
        ))}
      </div>

      {error ? (
        <p className="rounded border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      ) : null}

      {tab === "users" ? (
        <section className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <div className="overflow-x-auto">
            {usersQuery.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading users…</p>
            ) : usersQuery.isError ? (
              <p className="text-sm text-destructive">
                {(usersQuery.error as Error).message}
              </p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-muted-foreground">
                  <tr>
                    <th className="py-2 pr-3 font-medium">Email</th>
                    <th className="py-2 pr-3 font-medium">Name</th>
                    <th className="py-2 pr-3 font-medium">Roles</th>
                    <th className="py-2 pr-3 font-medium">Active</th>
                    <th className="py-2 font-medium" />
                  </tr>
                </thead>
                <tbody>
                  {(usersQuery.data ?? []).map((u: AdminUser) => (
                    <tr key={u.id} className="border-b border-border/60">
                      <td className="py-2 pr-3">{u.email}</td>
                      <td className="py-2 pr-3">{u.display_name}</td>
                      <td className="py-2 pr-3">
                        {u.roles.map((r) => r.code).join(", ") || "—"}
                      </td>
                      <td className="py-2 pr-3">
                        {u.is_active ? "yes" : "no"}
                      </td>
                      <td className="py-2">
                        <button
                          type="button"
                          className="text-xs underline"
                          onClick={() =>
                            toggleActive.mutate({
                              id: u.id,
                              active: !u.is_active,
                            })
                          }
                        >
                          {u.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <form
            className="flex flex-col gap-3 border-l border-border pl-6"
            onSubmit={(e) => {
              e.preventDefault();
              createMutation.mutate({
                email,
                display_name: displayName,
                password,
                role_codes: [roleCode],
              });
            }}
          >
            <h2 className="text-sm font-semibold">Create user</h2>
            <label className="text-xs text-muted-foreground">
              Email
              <input
                className="mt-1 w-full border border-border bg-background px-2 py-1.5 text-sm"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                type="email"
              />
            </label>
            <label className="text-xs text-muted-foreground">
              Display name
              <input
                className="mt-1 w-full border border-border bg-background px-2 py-1.5 text-sm"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
              />
            </label>
            <label className="text-xs text-muted-foreground">
              Password
              <input
                className="mt-1 w-full border border-border bg-background px-2 py-1.5 text-sm"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                type="password"
                minLength={8}
              />
            </label>
            <label className="text-xs text-muted-foreground">
              Role
              <select
                className="mt-1 w-full border border-border bg-background px-2 py-1.5 text-sm"
                value={roleCode}
                onChange={(e) => setRoleCode(e.target.value)}
              >
                {roleOptions.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="submit"
              className="mt-2 bg-foreground px-3 py-2 text-sm text-background disabled:opacity-50"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? "Creating…" : "Create user"}
            </button>
          </form>
        </section>
      ) : null}

      {tab === "audit" ? (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Recent immutable audit events (login, upload, view, copilot,
              export, admin).
            </p>
            <button
              type="button"
              className="border border-border px-3 py-1.5 text-sm"
              onClick={() => exportMutation.mutate()}
              disabled={exportMutation.isPending}
            >
              Export JSON
            </button>
          </div>
          {auditQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading audit…</p>
          ) : auditQuery.isError ? (
            <p className="text-sm text-destructive">
              {(auditQuery.error as Error).message}
            </p>
          ) : (
            <ul className="divide-y divide-border border border-border">
              {(auditQuery.data?.items ?? []).map((ev: AuditEvent) => (
                <li key={ev.id} className="px-3 py-2 text-sm">
                  <div className="flex flex-wrap gap-x-3 gap-y-1">
                    <span className="font-medium">{ev.action}</span>
                    <span className="text-muted-foreground">
                      {ev.resource_type}
                      {ev.resource_id ? `:${ev.resource_id.slice(0, 8)}` : ""}
                    </span>
                    <span className="text-muted-foreground">
                      {ev.created_at ?? ""}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {tab === "ops" ? (
        <section className="space-y-4">
          {opsQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading ops…</p>
          ) : opsQuery.isError ? (
            <p className="text-sm text-destructive">
              {(opsQuery.error as Error).message}
            </p>
          ) : opsQuery.data ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <OpsStat
                label="Status"
                value={opsQuery.data.status}
              />
              <OpsStat
                label="API requests"
                value={String(opsQuery.data.api.request_count)}
              />
              <OpsStat
                label="Avg latency ms"
                value={String(opsQuery.data.api.avg_latency_ms)}
              />
              <OpsStat
                label="Queue depth"
                value={String(opsQuery.data.workers.queue_depth)}
              />
              <OpsStat
                label="Dead letters"
                value={String(opsQuery.data.workers.dead_letter_open)}
              />
              <OpsStat
                label="Secrets hygiene"
                value={opsQuery.data.security.ok ? "ok" : "issues"}
              />
            </div>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}

function OpsStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-border px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-xl font-medium tabular-nums">{value}</p>
    </div>
  );
}
