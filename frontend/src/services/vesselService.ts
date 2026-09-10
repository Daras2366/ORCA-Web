/**
 * vesselService.ts — CRUD calls to the ORCA Auth API's /vessels endpoints.
 */

import { AUTH_API_URL } from "@/services/authService";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface VesselOut {
  id: string;
  user_id: string;
  name: string;
  vessel_type: string;
  length_m: number | null;
  engine_type: string | null;
  engine_power_hp: number | null;
  cruising_speed_kmh: number | null;
  fuel_capacity_l: number | null;
  created_at: string;
  updated_at: string;
}

export interface VesselCreate {
  name: string;
  vessel_type: string;
  length_m?: number | null;
  engine_type?: string | null;
  engine_power_hp?: number | null;
  cruising_speed_kmh?: number | null;
  fuel_capacity_l?: number | null;
}

export type VesselUpdate = Partial<VesselCreate>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getToken(): string | null {
  return localStorage.getItem("orca_token");
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(AUTH_API_URL + path, {
    method,
    headers,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

  if (res.status === 204) return undefined as unknown as T;

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

// ---------------------------------------------------------------------------
// Vessel API
// ---------------------------------------------------------------------------

export const listVessels = (): Promise<VesselOut[]> =>
  request<VesselOut[]>("GET", "/vessels");

export const createVessel = (payload: VesselCreate): Promise<VesselOut> =>
  request<VesselOut>("POST", "/vessels", payload);

export const getVessel = (id: string): Promise<VesselOut> =>
  request<VesselOut>("GET", `/vessels/${id}`);

export const updateVessel = (id: string, payload: VesselUpdate): Promise<VesselOut> =>
  request<VesselOut>("PUT", `/vessels/${id}`, payload);

export const deleteVessel = (id: string): Promise<void> =>
  request<void>("DELETE", `/vessels/${id}`);
