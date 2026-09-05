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
