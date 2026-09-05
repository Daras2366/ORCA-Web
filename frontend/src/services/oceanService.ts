import type { FishingZone, OceanConditions, UserLocation } from "@/types/marine";
import { apiGet } from "./apiClient";

interface OceanApiResponse {
  status: string;
  zone_id?: string;
  fishing_score?: number;
  evidence?: Record<string, number | null>;
}

/** Raw numeric evidence values returned alongside the formatted metrics. */
export interface OceanRawEvidence {
  zone_id: string | null;
  sst_c: number | null;
  chlorophyll_mean: number | null;
  current_speed_ms: number | null;
  pfz_distance_km: number | null;
  fishing_score: number | null;
}

export interface OceanConditionsResult {
  conditions: OceanConditions;
  raw: OceanRawEvidence;
}

// GET /api/ocean (via Query Agent → Ocean Agent)
export async function getOceanConditions(location: UserLocation): Promise<OceanConditionsResult> {
  const response = await apiGet<OceanApiResponse>("/api/ocean", {
    latitude: location.latitude,
    longitude: location.longitude,
  });

  const evidence = response.evidence ?? {};

  const raw = (k: string): number | null => {
    const v = evidence[k];
    return v != null ? Number(v) : null;
  };

  const fmt = (v: number | null | undefined, decimals: number, unit: string) =>
    v != null ? `${v.toFixed(decimals)}${unit}` : "N/A";

  const sst       = raw("sst_c");
  const chl       = raw("chlorophyll_mean");
  const cur       = raw("current_speed_ms");
  const dist      = raw("pfz_distance_km");
  const fscore    = response.fishing_score ?? null;
  const zoneId    = response.zone_id ?? null;

  const metrics = [
    { key: "sst",         label: "Sea Surface Temp",  value: fmt(sst,  2, "°C"),    status: "Live" },
    { key: "chlorophyll", label: "Chlorophyll",        value: fmt(chl,  3, " mg/m³"), status: "Live" },
    { key: "current",     label: "Current Speed",      value: fmt(cur,  2, " m/s"),   status: "Live" },
  ];

  if (dist != null) {
    metrics.push({ key: "distance", label: "Dist. to Zone",  value: fmt(dist, 1, " km"),  status: "Live" });
  }

  const conditions: OceanConditions = {
    updated_at: new Date().toLocaleString(),
    metrics,
  };

  const rawEvidence: OceanRawEvidence = {
    zone_id: zoneId,
    sst_c: sst,
    chlorophyll_mean: chl,
    current_speed_ms: cur,
    pfz_distance_km: dist,
    fishing_score: fscore,
  };

  return { conditions, raw: rawEvidence };
}

// GET /api/fishing-zones (via Query Agent)
export async function getFishingZones(location: UserLocation): Promise<FishingZone[]> {
  const response = await apiGet<{ status: string; zones: FishingZone[] }>("/api/fishing-zones", {
    latitude: location.latitude,
    longitude: location.longitude,
  });
  return response.zones ?? [];
}

