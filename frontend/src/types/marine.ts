export interface UserLocation {
  latitude: number;
  longitude: number;
  city: string;
  state: string;
  country: string;
}

export type PotentialLevel = "High" | "Medium" | "Low";

export interface FishingZone {
  zone_id: string;
  latitude: number;
  longitude: number;
  hsi: number;
  potential: PotentialLevel;
  recommended: boolean;
  sst_c?: number | null;
  chlorophyll_mg_m3?: number | null;
  safety_score?: number | null;
  confidence: number;
    distance_km?: number | null;
}

export interface OceanMetric {
  key: string;
  label: string;
  value: string;
  status: string;
}

export interface OceanConditions {
  updated_at: string;
  metrics: OceanMetric[];
}

export type SafetyStatus = "All Clear" | "Warning" | "Unsafe";

export interface SafetyReport {
  status: SafetyStatus;
  message: string;
  indicators: { label: string; value: string; level: "low" | "moderate" | "high" }[];
}

export interface RouteEstimate {
  from_label: string;
  from_sub: string;
  to_label: string;
  to_sub: string;
  distance_km: number;
  duration_label: string;
  fuel_litres: number;
  note: string;
}

export interface NavigationRequest {
  start_latitude: number;
  start_longitude: number;
  destination_latitude: number;
  destination_longitude: number;
}

export interface NavigationResponse {
  success: boolean;
  message: string;
  start: {
    latitude: number;
    longitude: number;
  };
  destination: {
    latitude: number;
    longitude: number;
  };
  snapped_start: {
    latitude: number;
    longitude: number;
  };
  snapped_destination: {
    latitude: number;
    longitude: number;
  };
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
}

export interface NavigationResult {
  success: boolean;
  distance_km: number;
  travel_time_h: number;
  fuel_l: number;
  min_depth_m: number;
  max_depth_m: number;
  average_depth_m: number;
  average_current_ms: number | null;
  geojson: {
    type: "LineString";
    coordinates: [number, number][];
  };
  snapped_start: {
    latitude: number;
    longitude: number;
  };
  snapped_destination: {
    latitude: number;
    longitude: number;
  };
  error?: string;
}

export interface ZoneFactor {
  factor: string;
  score: number;
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: number;
}

export interface AssistantResponse {
  conversation_id: string;
  reply: string;
}
