/**
 * feedbackService.ts
 *
 * All feedback-loop API calls go through this single service.
 * Uses the same apiClient pattern as the rest of the dashboard.
 */

import { apiGet, apiPost } from "./apiClient";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PredictionSnapshot {
  fishing_score: number | null;
  safety_score: number | null;
  final_score: number | null;
  decision: string | null;
  model_version: string;
}

export type FeedbackType = "fishing" | "safety";
export type FishingOutcome = "good" | "moderate" | "poor";
export type SafetyOutcome = "safe" | "moderate" | "unsafe";
export type Rating = "positive" | "negative";

export interface FeedbackPayload {
  zone_id: string;
  feedback_type: FeedbackType;
  prediction: PredictionSnapshot;
  observed_outcome: string;
  rating?: Rating | null;
  comment?: string | null;
  /** Stable identifier for this specific prediction instance.
   *  Used to prevent duplicate submissions for the same prediction.
   *  Format: "{zone_id}_{fishing_score}_{safety_score}_{model_version}" */
  prediction_id?: string | null;
}

export interface FeedbackResponse {
  success: boolean;
  feedback_id: string;
  prediction_match: boolean;
}

export interface FeedbackMetrics {
  status: string;
  total_feedback: number;
  validated_feedback: number;
  overall_accuracy: number | null;
  fishing_accuracy: number | null;
  safety_accuracy: number | null;
  matches: number;
  mismatches: number;
  validated_samples_available: number;
}

export interface LearningStatus {
  model_version: string;
  validated_samples: number;
  minimum_samples: number;
  ready: boolean;
  status: "collecting_feedback" | "ready_for_learning";
  last_evaluation: string | null;
  last_accuracy: number | null;
}

export interface RetrainResult {
  status: "deployed" | "retained";
  message: string;
  model_version: string;
  old_accuracy: number;
  new_accuracy: number;
  improvement: number;
  sample_count: number;
  timestamp: string;
}

/** Shape of a single record returned from the backend JSONL store. */
export interface FeedbackRecord {
  feedback_id: string;
  timestamp: string;
  zone_id: string;
  feedback_type: FeedbackType;
  observed_outcome: string;
  rating: Rating | null;
  prediction_match: boolean | null;
  model_version: string;
}

export interface FeedbackListResponse {
  status: string;
  records: FeedbackRecord[];
  total: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a stable prediction_id string from the snapshot fields. */
export function buildPredictionId(
  zoneId: string,
  fishingScore: number | null,
  safetyScore: number | null,
  modelVersion: string,
): string {
  return `${zoneId}_fs${fishingScore ?? "null"}_ss${safetyScore ?? "null"}_${modelVersion}`;
}

// ---------------------------------------------------------------------------
// Service functions
// ---------------------------------------------------------------------------

export async function submitFeedback(payload: FeedbackPayload): Promise<FeedbackResponse> {
  return apiPost<FeedbackResponse>("/api/feedback", payload);
}

export async function getFeedbackMetrics(): Promise<FeedbackMetrics> {
  return apiGet<FeedbackMetrics>("/api/feedback/metrics");
}

export async function getLearningStatus(): Promise<LearningStatus> {
  return apiGet<LearningStatus>("/api/feedback/learning-status");
}

export async function retrainFeedbackModel(): Promise<RetrainResult> {
  return apiPost<RetrainResult>("/api/feedback/retrain", {});
}

export async function getRecentFeedback(limit = 20): Promise<FeedbackListResponse> {
  return apiGet<FeedbackListResponse>("/api/feedback/recent", { limit });
}
