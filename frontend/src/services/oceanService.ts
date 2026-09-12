import type { FishingZone, OceanConditions, UserLocation } from "@/types/marine";
import { apiGet } from "./apiClient";

interface OceanApiResponse {
  status: string;
  zone_id?: string;
  fishing_score?: number;

  data_mode?: string;

  data_sources?: {
    sst?: string;
    ocean_current?: string;
    wave?: string;
    chlorophyll?: string;
  };

  data_modes?: {
    sst?: string;
    ocean_current?: string;
    wave?: string;
    chlorophyll?: string;
  };

  timestamp?: string;

  evidence?: Record<
    string,
    number | string | null
  >;
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

  data_mode: string;

  data_sources: {
    sst: string;
    ocean_current: string;
    wave: string;
    chlorophyll: string;
  };

  data_modes: {
    sst: string;
    ocean_current: string;
    wave: string;
    chlorophyll: string;
  };

  timestamp: string | null;
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

  const dataModes = response.data_modes ?? {};

  const formatMode = (
    mode: string | undefined
  ): string => {

    if (!mode) {
      return "Unknown";
    }

    if (mode === "live") {
      return "Live";
    }

    if (mode === "near_real_time") {
      return "Near Real-Time";
    }

    if (mode === "fallback") {
      return "Fallback";
    }

    return mode;
  };

  const metrics = [
  {
    key: "sst",
    label: "Sea Surface Temp",
    value: fmt(sst, 2, "°C"),
    status: "",
  },

  {
    key: "chlorophyll",
    label: "Chlorophyll",
    value: fmt(chl, 3, " mg/m³"),
    status: "",
  },

  {
    key: "current",
    label: "Current Speed",
    value: fmt(cur, 2, " m/s"),
    status: "",
  },
];

  if (dist != null) {
    metrics.push({
      key: "distance",
      label: "Dist. to Zone",
      value: fmt(dist, 1, " km"),
      status: "",
    });
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

    return {
    conditions,
    raw: rawEvidence,

    data_mode:
      response.data_mode ?? "mixed",

    data_sources: {
      sst:
        response.data_sources?.sst
        ?? "Open-Meteo",

      ocean_current:
        response.data_sources?.ocean_current
        ?? "Open-Meteo",

      wave:
        response.data_sources?.wave
        ?? "Open-Meteo",

      chlorophyll:
        response.data_sources?.chlorophyll
        ?? "Unknown",
    },

    data_modes: {
      sst:
        response.data_modes?.sst
        ?? "live",

      ocean_current:
        response.data_modes?.ocean_current
        ?? "live",

      wave:
        response.data_modes?.wave
        ?? "live",

      chlorophyll:
        response.data_modes?.chlorophyll
        ?? "unknown",
    },

    timestamp:
      response.timestamp ?? null,
  };
}

// GET /api/fishing-zones (via Query Agent)
export async function getFishingZones(location: UserLocation): Promise<FishingZone[]> {
  const response = await apiGet<{ status: string; zones: FishingZone[] }>("/api/fishing-zones", {
    latitude: location.latitude,
    longitude: location.longitude,
  });
  return response.zones ?? [];
}

