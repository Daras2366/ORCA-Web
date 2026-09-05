/**
 * Single place where the future FastAPI backend is configured.
 * Set VITE_API_BASE_URL to point the frontend at the real API.
 */
export const API_BASE_URL = import.meta.env["VITE_API_BASE_URL"] ?? "";

export const USE_MOCK_DATA = API_BASE_URL === "";

export const endpoints = {
  query: "/query",
  ocean: "/api/ocean",
  safety: "/api/safety",
  fishingZones: "/api/fishing-zones",
  route: "/api/route",
} as const;

export async function apiGet<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(API_BASE_URL + path);
  Object.entries(params ?? {}).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  const res = await fetch(url.toString(), { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return (await res.json()) as T;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(API_BASE_URL + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return (await res.json()) as T;
}

export function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
