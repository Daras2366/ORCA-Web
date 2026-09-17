import type { SafetyReport, UserLocation } from "@/types/marine";
import { apiGet } from "./apiClient";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SafetyApiResponse {
  status: string;
  zone_id?: string | null;

  location?: {
    latitude: number;
    longitude: number;
  } | null;

  risk_score?: number | null;
  risk_level?: string | null;
  evidence?: Record<string, any>;
}

/** Raw numeric evidence values as returned by the Safety Agent. */
export interface SafetyRawEvidence {
  zone_id: string | null;

  latitude: number | null;
  longitude: number | null;

  risk_score: number | null;
  risk_level: string | null;
  safety_score: number | null;
  wind_speed_ms: number | null;
  wave_height_m: number | null;
  wave_period_s: number | null;
  wave_direction_deg: number | null;
  cyclone_distance_km: number | null;
  cyclone_wind_kt: number | null;
  rainfall_mean: number | null;
  current_speed_ms: number | null;
  lightning: {
    available: boolean;
    risk: number | null;
    raw_jkg: number | null;
    source: string;
    timestamp: string | null;
  } | null;
}

export interface SafetyResult {
  report: SafetyReport;
  raw: SafetyRawEvidence;
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

// GET /api/safety (via Query Agent → Safety Agent)
export async function getSafetyReport(location: UserLocation): Promise<SafetyResult> {
  const response = await apiGet<SafetyApiResponse>("/api/safety", {
    latitude: location.latitude,
    longitude: location.longitude,
  });

  const riskScore = response.risk_score ?? null;
  const riskLevel = response.risk_level ?? "UNKNOWN";
  const evidence = response.evidence ?? {};

  // Map to SafetyReport (used by Dashboard's SafetyAlerts widget)
  const numericRisk = riskScore ?? 0.5;

  let status: SafetyReport["status"] = "All Clear";
  if (riskLevel === "HIGH" || numericRisk > 0.7) {
    status = "Unsafe";
  } else if (riskLevel === "MODERATE" || numericRisk > 0.4) {
    status = "Warning";
  }

  const overallLevel: "low" | "moderate" | "high" =
    numericRisk > 0.7 ? "high" : numericRisk > 0.4 ? "moderate" : "low";

  const fmtEv = (key: string, decimals: number, unit: string): string => {
    const v = evidence[key];
    return v != null ? `${Number(v).toFixed(decimals)}${unit}` : "N/A";
  };

  const report: SafetyReport = {
    status,
    message: `Risk level: ${riskLevel} (score: ${(numericRisk * 100).toFixed(0)}/100)`,
    indicators: [
      {
        label: "Wind",
        value: fmtEv("wind_speed_ms", 1, " m/s"),
        level: overallLevel,
      },
      {
        label: "Waves",
        value: fmtEv("wave_height_m", 1, " m"),
        level: overallLevel,
      },
      {
        label: "Cyclone Risk",
        value:
          evidence.cyclone?.available && evidence.cyclone.distance_km != null
            ? `${Number(evidence.cyclone.distance_km).toFixed(0)} km`
            : "Clear",
        level: overallLevel,
      },
    ],
  };

  // Raw evidence (used by Safety & Alerts page)
  const rawNum = (key: string): number | null => {
    const v = evidence[key];
    return v != null ? Number(v) : null;
  };

  const safetyScore =
    riskScore != null ? round((1 - riskScore) * 100, 1) : null;

  const raw: SafetyRawEvidence = {
    zone_id: response.zone_id ?? null,

    latitude: response.location?.latitude ?? location.latitude,
    longitude: response.location?.longitude ?? location.longitude,

    risk_score:
      riskScore != null
        ? round(riskScore, 4)
        : null,

    risk_level: riskLevel,

    safety_score: safetyScore,

    wind_speed_ms: rawNum("wind_speed_ms"),
    wave_height_m: rawNum("wave_height_m"),
    wave_period_s: rawNum("wave_period_s"),
    wave_direction_deg: rawNum("wave_direction_deg"),
    cyclone_distance_km: rawNum("cyclone_distance_km"),
    cyclone_wind_kt: rawNum("cyclone_wind_kt"),
    rainfall_mean: rawNum("rainfall_mean"),
    current_speed_ms: rawNum("current_speed_ms"),

    lightning: (() => {
      const l = (evidence as Record<string, unknown>)["lightning"];

      if (!l || typeof l !== "object") {
        return null;
      }

      const lo = l as Record<string, unknown>;

      return {
        available: Boolean(lo["available"]),
        risk:
          lo["risk"] != null
            ? Number(lo["risk"])
            : null,
        raw_jkg:
          lo["raw_jkg"] != null
            ? Number(lo["raw_jkg"])
            : null,
        source: String(lo["source"] ?? ""),
        timestamp:
          lo["timestamp"] != null
            ? String(lo["timestamp"])
            : null,
      };
    })(),
  };

  return { report, raw };
}

// GET /api/safety?zone_id=PFZxxxx
// Used when the user opens a specific PFZ on the map.
export async function getZoneSafetyScore(
  zoneId: string,
): Promise<number | null> {
  const response = await apiGet<SafetyApiResponse>("/api/safety", {
    zone_id: zoneId,
  });

  const riskScore = response.risk_score ?? null;

  if (riskScore == null) {
    return null;
  }

  return round((1 - Number(riskScore)) * 100, 1);
}

function round(n: number, decimals: number): number {
  const factor = Math.pow(10, decimals);
  return Math.round(n * factor) / factor;
}
