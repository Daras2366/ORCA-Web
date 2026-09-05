import type { RouteEstimate, UserLocation } from "@/types/marine";
import { apiGet } from "./apiClient";

/** Shape returned by GET /api/route (Query Agent proxies to Routing Agent). */
interface RouteApiResponse {
  status: string;
  agent?: string;
  zone_id?: string;
  route_metrics?: {
    distance_km: number | null;
    travel_time_hr: number | null;
    fuel_l: number | null;
  };
  route_score?: number | null;
  confidence?: number | null;
  adjusted_route_score?: number | null;
  route_safety_score?: number | null;
  geofence_caution?: boolean;
  evidence?: Record<string, unknown>;
  dataset_scores?: Record<string, number | null>;
  // Legacy flat fields (fallback)
  distance_km?: number | null;
  travel_time_hr?: number | null;
  fuel_l?: number | null;
}

// GET /api/route (via Query Agent → Routing Agent)
export async function getRouteEstimate(
  location: UserLocation,
  zoneId: string,
): Promise<RouteEstimate> {
  // Always call real API — throws on failure so React Query shows error state
  const response = await apiGet<RouteApiResponse>("/api/route", {
    zone_id: zoneId,
  });

  // The Routing Agent returns metrics under route_metrics; fall back to flat
  // fields in case the Query Agent ever reshapes the response.
  const distanceKm =
    response.route_metrics?.distance_km ?? response.distance_km ?? 0;
  const travelTimeHr =
    response.route_metrics?.travel_time_hr ?? response.travel_time_hr ?? 0;
  const fuelL =
    response.route_metrics?.fuel_l ?? response.fuel_l ?? 0;
  const routeScore = response.route_score ?? null;
  const confidence = response.confidence ?? null;
  const routeSafety = response.route_safety_score ?? null;
  const geofenceCaution = response.geofence_caution ?? false;

  const hours = Math.floor(travelTimeHr);
  const minutes = Math.round((travelTimeHr - hours) * 60);
  const durationLabel = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

  // Build the note from real backend values
  const noteParts: string[] = [];
  if (routeScore !== null) {
    noteParts.push(`Route score: ${(routeScore * 100).toFixed(0)}/100`);
  }
  if (confidence !== null) {
    noteParts.push(`Confidence: ${(confidence * 100).toFixed(0)}%`);
  }
  if (routeSafety !== null) {
    noteParts.push(`Route safety: ${(routeSafety * 100).toFixed(0)}/100`);
  }
  if (geofenceCaution) {
    noteParts.push("⚠ Geofence caution");
  }
  const note = noteParts.join(" · ") || "Straight-line distance estimate.";

  return {
    from_label: "Your Location",
    from_sub: location.city ? `(${location.city})` : "",
    to_label: zoneId,
    to_sub: "Fishing Zone",
    distance_km: distanceKm,
    duration_label: durationLabel,
    fuel_litres: fuelL,
    note,
  };
}
