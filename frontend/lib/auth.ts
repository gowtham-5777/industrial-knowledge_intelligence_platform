/** Auth API helpers — login / me / session probe. */

import { apiClient } from "@/lib/api-client";
import type { AuthUser, TokenPair } from "@/lib/session";

export type { AuthUser, TokenPair } from "@/lib/session";
export {
  clearSession,
  getAccessToken,
  getApiBaseUrl,
  getStoredUser,
  saveSession,
} from "@/lib/session";

export async function loginRequest(
  email: string,
  password: string,
): Promise<TokenPair> {
  return apiClient<TokenPair>(
    "/api/v1/auth/login",
    {
      method: "POST",
      body: JSON.stringify({ email, password }),
    },
    { token: null },
  );
}

export async function fetchMe(): Promise<AuthUser> {
  return apiClient<AuthUser>("/api/v1/auth/me");
}

/** Session probe used by TanStack Query (auth-gated shell). */
export async function fetchSessionCheck(): Promise<{
  authenticated: boolean;
  user_id: string;
  email: string;
}> {
  return apiClient("/api/v1/session/check");
}
