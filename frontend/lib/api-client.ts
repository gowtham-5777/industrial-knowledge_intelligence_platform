/** Authenticated API client for the Industrial Brain backend (Milestone 1.8). */

import { getAccessToken, getApiBaseUrl } from "@/lib/session";

export type ApiEnvelope<T> = {
  data: T | null;
  meta: Record<string, unknown>;
  errors: { code: string; message: string; details?: unknown }[];
};

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(
    message: string,
    opts: { status: number; code: string; details?: unknown },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = opts.status;
    this.code = opts.code;
    this.details = opts.details;
  }
}

export type ApiClientOptions = {
  /** Override access token (tests / SSR). */
  token?: string | null;
  /** Skip JSON Content-Type (multipart uploads). */
  rawBody?: boolean;
};

export async function apiClient<T>(
  path: string,
  init: RequestInit = {},
  options: ApiClientOptions = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!options.rawBody && !headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }

  const token =
    options.token === undefined ? getAccessToken() : options.token;
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers,
  });

  let body: ApiEnvelope<T>;
  try {
    body = (await response.json()) as ApiEnvelope<T>;
  } catch {
    throw new ApiError("Invalid JSON response from API", {
      status: response.status,
      code: "INVALID_RESPONSE",
    });
  }

  if (!response.ok || (body.errors && body.errors.length > 0)) {
    const first = body.errors?.[0];
    throw new ApiError(
      first?.message || `Request failed (${response.status})`,
      {
        status: response.status,
        code: first?.code || "REQUEST_FAILED",
        details: first?.details,
      },
    );
  }

  if (body.data === null || body.data === undefined) {
    throw new ApiError("Empty response data", {
      status: response.status,
      code: "EMPTY_DATA",
    });
  }

  return body.data;
}
