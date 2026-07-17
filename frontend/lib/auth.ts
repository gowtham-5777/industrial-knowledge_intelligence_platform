/** Browser session helpers for JWT seed auth (Milestone 1.4). */

const ACCESS_KEY = "iba_access_token";
const REFRESH_KEY = "iba_refresh_token";
const USER_KEY = "iba_user";

export type AuthUser = {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  roles: { code: string; name: string }[];
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export function getApiBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
    "http://localhost:8000"
  );
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function saveSession(tokens: TokenPair, user: AuthUser): void {
  window.localStorage.setItem(ACCESS_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
  window.localStorage.removeItem(USER_KEY);
}

type Envelope<T> = {
  data: T | null;
  meta: Record<string, unknown>;
  errors: { code: string; message: string }[];
};

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers,
  });
  const body = (await response.json()) as Envelope<T>;
  if (!response.ok || body.errors?.length) {
    const message =
      body.errors?.[0]?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }
  if (body.data === null || body.data === undefined) {
    throw new Error("Empty response data");
  }
  return body.data;
}

export async function loginRequest(
  email: string,
  password: string,
): Promise<TokenPair> {
  return apiFetch<TokenPair>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function fetchMe(): Promise<AuthUser> {
  return apiFetch<AuthUser>("/api/v1/auth/me");
}
