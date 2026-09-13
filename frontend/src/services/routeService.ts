import type { RouteEstimate, UserLocation, NavigationRequest, NavigationResult } from "@/types/marine";
import { apiGet, apiPost } from "./apiClient";

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

// POST /api/route/navigate (deterministic A* routing)
export async function navigateRoute(
  startLatitude: number,
  startLongitude: number,
  destinationLatitude: number,
  destinationLongitude: number,
): Promise<NavigationResult> {
  try {
    const response = await apiPost<{
      success: boolean;
      message: string;
      start: { latitude: number; longitude: number };
      destination: { latitude: number; longitude: number };
      snapped_start: { latitude: number; longitude: number };
      snapped_destination: { latitude: number; longitude: number };
      metrics: {
        distance_km: number;
        travel_time_h: number;
        fuel_l: number;
        min_depth_m: number;
        max_depth_m: number;
        average_depth_m: number;
        average_current_ms: number | null;
        total_cost: number;
      };
      geojson: {
        type: "LineString";
        coordinates: [number, number][];
      };
    }>("/api/route/navigate", {
      start_latitude: startLatitude,
      start_longitude: startLongitude,
      destination_latitude: destinationLatitude,
      destination_longitude: destinationLongitude,
    });

    if (!response.success) {
      return {
        success: false,
        distance_km: 0,
        travel_time_h: 0,
        fuel_l: 0,
        min_depth_m: 0,
        max_depth_m: 0,
        average_depth_m: 0,
        average_current_ms: null,
        geojson: { type: "LineString", coordinates: [] },
        snapped_start: { latitude: 0, longitude: 0 },
        snapped_destination: { latitude: 0, longitude: 0 },
        error: response.message || "Navigation failed",
      };
    }

    return {
      success: true,
      distance_km: response.metrics.distance_km,
      travel_time_h: response.metrics.travel_time_h,
      fuel_l: response.metrics.fuel_l,
      min_depth_m: response.metrics.min_depth_m,
      max_depth_m: response.metrics.max_depth_m,
      average_depth_m: response.metrics.average_depth_m,
      average_current_ms: response.metrics.average_current_ms,
      geojson: response.geojson,
      snapped_start: response.snapped_start,
      snapped_destination: response.snapped_destination,
    };
  } catch (error) {
    // Handle HTTP errors (400, 500, etc.)
    const errorMessage = error instanceof Error ? error.message : "Navigation request failed";
    
    return {
      success: false,
      distance_km: 0,
      travel_time_h: 0,
      fuel_l: 0,
      min_depth_m: 0,
      max_depth_m: 0,
      average_depth_m: 0,
      average_current_ms: null,
      geojson: { type: "LineString", coordinates: [] },
      snapped_start: { latitude: 0, longitude: 0 },
      snapped_destination: { latitude: 0, longitude: 0 },
      error: errorMessage,
    };
  }
}
