import type {
  FishingZone,
  OceanConditions,
  RouteEstimate,
  SafetyReport,
  UserLocation,
  ZoneFactor,
} from "@/types/marine";

/** DEMO VALUES ONLY — replaced by FastAPI responses later. */

export const defaultLocation: UserLocation = {
  latitude: 9.9312,
  longitude: 76.2673,
  city: "Kochi",
  state: "Kerala",
  country: "India",
};

export const mockZones: FishingZone[] = [
  {
    zone_id: "PFZ0319",
    latitude: 9.72,
    longitude: 75.62,
    hsi: 0.59,
    potential: "High",
    recommended: true,
    sst_c: 28.4,
    chlorophyll_mg_m3: 0.086,
    safety_score: 85,
    confidence: 0.98,
  },
  {
    zone_id: "PFZ0321",
    latitude: 10.35,
    longitude: 75.28,
    hsi: 0.42,
    potential: "Medium",
    recommended: false,
    sst_c: 28.1,
    chlorophyll_mg_m3: 0.071,
    safety_score: 78,
    confidence: 0.92,
  },
  {
    zone_id: "PFZ0324",
    latitude: 9.18,
    longitude: 75.05,
    hsi: 0.67,
    potential: "High",
    recommended: false,
    sst_c: 28.7,
    chlorophyll_mg_m3: 0.094,
    safety_score: 74,
    confidence: 0.9,
  },
  {
    zone_id: "PFZ0331",
    latitude: 8.62,
    longitude: 75.72,
    hsi: 0.51,
    potential: "Medium",
    recommended: false,
    sst_c: 28.9,
    chlorophyll_mg_m3: 0.066,
    safety_score: 81,
    confidence: 0.88,
  },
  {
    zone_id: "PFZ0332",
    latitude: 11.02,
    longitude: 74.86,
    hsi: 0.48,
    potential: "Medium",
    recommended: false,
    sst_c: 27.8,
    chlorophyll_mg_m3: 0.058,
    safety_score: 69,
    confidence: 0.85,
  },
  {
    zone_id: "PFZ0333",
    latitude: 10.05,
    longitude: 73.94,
    hsi: 0.28,
    potential: "Low",
    recommended: false,
    sst_c: 27.4,
    chlorophyll_mg_m3: 0.032,
    safety_score: 63,
    confidence: 0.8,
  },
];

export const mockOceanConditions: OceanConditions = {
  updated_at: "Demo snapshot",
  metrics: [
    { key: "sst", label: "SST", value: "28.4°C", status: "Optimal" },
    { key: "chlorophyll", label: "Chlorophyll", value: "0.086 mg/m³", status: "Low" },
    { key: "wind", label: "Wind", value: "12 km/h", status: "Moderate" },
    { key: "waves", label: "Waves", value: "0.8 m", status: "Calm" },
  ],
};

export const mockSafety: SafetyReport = {
  status: "All Clear",
  message: "No active alerts in your area",
  indicators: [
    { label: "Cyclone Risk", value: "Low", level: "low" },
    { label: "Storm Risk", value: "Low", level: "low" },
    { label: "Visibility", value: "Good", level: "low" },
  ],
};

export const mockRoute: RouteEstimate = {
  from_label: "Your Location",
  from_sub: "(Kochi)",
  to_label: "PFZ0319",
  to_sub: "Recommended Zone",
  distance_km: 45.2,
  duration_label: "2h 15m",
  fuel_litres: 18.6,
  note: "Estimated using available marine and routing data.",
};

export const mockZoneFactors: ZoneFactor[] = [
  { factor: "SST", score: 82 },
  { factor: "Chlorophyll", score: 46 },
  { factor: "Wave", score: 88 },
  { factor: "Safety", score: 85 },
  { factor: "Confidence", score: 98 },
];

export const suggestedQuestions = [
  "Where are the best fishing zones today?",
  "Is it safe to go fishing tomorrow?",
  "Which fishing zone is closest to me?",
  "Show ocean conditions near me.",
  "Is there any cyclone risk?",
];
