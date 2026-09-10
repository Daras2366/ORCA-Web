/**
 * authService.ts — calls the ORCA Auth API (port 8005).
 *
 * VITE_AUTH_API_URL should be set in frontend/.env, e.g.:
 *   VITE_AUTH_API_URL=http://localhost:8005
 */

const AUTH_API_URL =
  (import.meta.env["VITE_AUTH_API_URL"] as string | undefined) ??
  "http://localhost:8005";

export { AUTH_API_URL };

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UserOut {
  id: string;
  name: string;
  email: string;
  user_type: string;
  preferred_language: string;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
  confirm_password: string;
  user_type: string;
  preferred_language?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function authPost<T>(path: string, body: unknown): Promise<T> {
  const token = localStorage.getItem("orca_token");
  const res = await fetch(AUTH_API_URL + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  const data = await res.json();
  if (!res.ok) {
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((e: { msg: string }) => e.msg).join("; ")
          : "Request failed";
    throw new Error(detail);
  }
  return data as T;
}

async function authGet<T>(path: string): Promise<T> {
  const token = localStorage.getItem("orca_token");
  const res = await fetch(AUTH_API_URL + path, {
    method: "GET",
    headers: {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  const data = await res.json();
  if (!res.ok) {
    const detail =
      typeof data.detail === "string" ? data.detail : "Request failed";
    throw new Error(detail);
  }
  return data as T;
}

// ---------------------------------------------------------------------------
// Auth API calls
// ---------------------------------------------------------------------------

export async function register(payload: RegisterPayload): Promise<TokenResponse> {
  return authPost<TokenResponse>("/auth/register", payload);
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  return authPost<TokenResponse>("/auth/login", payload);
}

export async function getMe(): Promise<UserOut> {
  return authGet<UserOut>("/auth/me");
}

export async function logout(): Promise<void> {
  try {
    await authPost("/auth/logout", {});
  } catch {
    // Ignore server errors on logout — token is deleted client-side regardless.
  }
}
