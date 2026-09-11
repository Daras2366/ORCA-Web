/**
 * FeedbackCard.tsx
 *
 * Standalone feedback submission form used on the Feedback page (/history).
 * NOT rendered on the Dashboard.
 *
 * Supports both fishing and safety observations in a single submission.
 *
 * Duplicate-submission logic:
 *   - Each unique prediction is identified by a prediction_id string.
 *   - If that prediction_id has already been submitted, localStorage
 *     records it so the form shows "Feedback already submitted for this
 *     prediction." instead of the empty form.
 *   - On reload: the form resets to idle UNLESS the same prediction_id
 *     is detected in localStorage.
 *   - When there is no active prediction (zone_id is null / undefined),
 *     the component shows a zone-picker instead of undefined values.
 *
 * Reload behaviour:
 *   - React state `submitState` always starts as "idle".
 *   - The ONLY reason a success message appears after reload is a
 *     matching prediction_id in localStorage — not the mere existence
 *     of any feedback in the JSONL file.
 */

import { useState } from "react";
import {
  ThumbsUp,
  ThumbsDown,
  CheckCircle,
  Loader2,
  AlertCircle,
  MessageSquare,
  Fish,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PredictionSnapshot, Rating } from "@/services/feedbackService";
import { submitFeedback, buildPredictionId } from "@/services/feedbackService";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FeedbackSnapshot {
  zone_id: string;
  fishing_score: number | null;
  safety_score: number | null;
  final_score: number | null;
  decision: string | null;
  model_version: string;
}

interface Props {
  /** Current ORCA prediction context. Pass null when no prediction is active. */
  snapshot: FeedbackSnapshot | null;
  /** Optional list of available zone IDs for the fallback picker. */
  availableZones?: string[];
  /** Called after successful submission so parent can refresh data. */
  onSuccess?: () => void;
}

type SubmitState = "idle" | "submitting" | "success" | "error";

// ---------------------------------------------------------------------------
// Outcome options
// ---------------------------------------------------------------------------

const FISHING_OPTIONS = [
  { value: "good", label: "Good" },
  { value: "moderate", label: "Moderate" },
  { value: "poor", label: "Poor" },
] as const;

const SAFETY_OPTIONS = [
  { value: "safe", label: "Safe" },
  { value: "moderate", label: "Moderate" },
  { value: "unsafe", label: "Unsafe" },
] as const;

// ---------------------------------------------------------------------------
// localStorage helpers — keyed to prediction_id, not just zone
// ---------------------------------------------------------------------------

const LS_PREFIX = "orca_fb_pred_";

function getPredId(snap: FeedbackSnapshot): string {
  return buildPredictionId(
    snap.zone_id,
    snap.fishing_score,
    snap.safety_score,
    snap.model_version,
  );
}

function isAlreadySubmitted(predId: string): boolean {
  try {
    return localStorage.getItem(LS_PREFIX + predId) === "1";
  } catch {
    return false;
  }
}

function markAsSubmitted(predId: string): void {
  try {
    localStorage.setItem(LS_PREFIX + predId, "1");
  } catch {
    // Ignore storage errors
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function FeedbackCard({ snapshot, availableZones = [], onSuccess }: Props) {
  // -------------------------------------------------------------------------
  // State — all starts as idle on every render/reload.
  // The only way success state persists across reload is via localStorage
  // (checked below after state is initialised).
  // -------------------------------------------------------------------------
  const [fishingOutcome, setFishingOutcome] = useState<string | null>(null);
  const [safetyOutcome, setSafetyOutcome] = useState<string | null>(null);
  const [rating, setRating] = useState<Rating | null>(null);
  const [comment, setComment] = useState("");
  const [showNote, setShowNote] = useState(false);
  const [submitState, setSubmitState] = useState<SubmitState>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  // When no snapshot, the user can pick a zone ID manually.
  const [manualZone, setManualZone] = useState("");

  // -------------------------------------------------------------------------
  // Resolve which zone we're operating on
  // -------------------------------------------------------------------------
  const activeZone = snapshot?.zone_id ?? (manualZone.trim().toUpperCase() || null);

  // -------------------------------------------------------------------------
  // Duplicate detection: checked at render time, based on prediction_id.
  // State starts as "idle" on every page load — localStorage is the only
  // persistence mechanism here.
  // -------------------------------------------------------------------------
  const predId = snapshot ? getPredId(snapshot) : null;
  const alreadyDone = predId ? isAlreadySubmitted(predId) : false;

  // -------------------------------------------------------------------------
  // Submit handler
  // -------------------------------------------------------------------------
  async function handleSubmit() {
    if (!activeZone) return;
    if (!fishingOutcome && !safetyOutcome) return;

    setSubmitState("submitting");
    setErrorMsg("");

    const snap: PredictionSnapshot = {
      fishing_score: snapshot?.fishing_score ?? null,
      safety_score: snapshot?.safety_score ?? null,
      final_score: snapshot?.final_score ?? null,
      decision: snapshot?.decision ?? null,
      model_version: snapshot?.model_version ?? "calibrated_v1",
    };

    try {
      // Submit fishing observation if selected
      if (fishingOutcome) {
        await submitFeedback({
          zone_id: activeZone,
          feedback_type: "fishing",
          prediction: snap,
          observed_outcome: fishingOutcome,
          rating: rating ?? null,
          comment: comment.trim() || null,
          prediction_id: predId,
        });
      }

      // Submit safety observation if selected
      if (safetyOutcome) {
        await submitFeedback({
          zone_id: activeZone,
          feedback_type: "safety",
          prediction: snap,
          observed_outcome: safetyOutcome,
          rating: rating ?? null,
          comment: comment.trim() || null,
          prediction_id: predId ? predId + "_safety" : null,
        });
      }

      // Mark this prediction as submitted in localStorage
      if (predId) markAsSubmitted(predId);

      setSubmitState("success");
      onSuccess?.();
    } catch (err) {
      console.error("Feedback submission failed:", err);
      setErrorMsg("Could not submit feedback. Please check the backend is running.");
      setSubmitState("error");
    }
  }

  // -------------------------------------------------------------------------
  // Render: already submitted for THIS prediction (persists across reload)
  // -------------------------------------------------------------------------
  if (alreadyDone && submitState === "idle") {
    return <AlreadySubmittedBanner />;
  }

  // -------------------------------------------------------------------------
  // Render: just submitted in this session
  // -------------------------------------------------------------------------
  if (submitState === "success") {
    return <SuccessBanner />;
  }

  const canSubmit =
    activeZone !== null &&
    (fishingOutcome !== null || safetyOutcome !== null) &&
    submitState === "idle";

  // -------------------------------------------------------------------------
  // Render: form
  // -------------------------------------------------------------------------
  return (
    <div className="space-y-5">
      {/* Zone context */}
      {snapshot ? (
        <div className="rounded-lg border border-border bg-deep px-4 py-3">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wider mb-1">
            Current ORCA prediction
          </p>
          <p className="text-sm font-semibold text-shell">{snapshot.zone_id}</p>
          <div className="flex gap-4 mt-1.5 text-xs text-muted-foreground">
            {snapshot.fishing_score != null && (
              <span>Fishing HSI: <span className="text-shell">{snapshot.fishing_score.toFixed(2)}</span></span>
            )}
            {snapshot.safety_score != null && (
              <span>Safety: <span className="text-shell">{snapshot.safety_score.toFixed(1)}/100</span></span>
            )}
            <span className="font-mono">{snapshot.model_version}</span>
          </div>
        </div>
      ) : (
        /* No active prediction — let user identify the zone manually */
        <div>
          <label htmlFor="fb-manual-zone" className="block text-xs text-muted-foreground mb-1.5">
            Zone ID (e.g. PFZ001)
          </label>
          {availableZones.length > 0 ? (
            <select
              id="fb-manual-zone"
              value={manualZone}
              onChange={(e) => setManualZone(e.target.value)}
              className="w-full rounded-lg border border-border bg-deep px-3 py-2 text-sm text-shell focus:border-rose/50 focus:outline-none"
            >
              <option value="">Select a zone…</option>
              {availableZones.map((z) => (
                <option key={z} value={z}>{z}</option>
              ))}
            </select>
          ) : (
            <input
              id="fb-manual-zone"
              type="text"
              value={manualZone}
              onChange={(e) => setManualZone(e.target.value.toUpperCase())}
              placeholder="Enter zone ID…"
              className="w-full rounded-lg border border-border bg-deep px-3 py-2 text-sm text-shell placeholder:text-muted-foreground/60 focus:border-rose/50 focus:outline-none"
            />
          )}
        </div>
      )}

      {/* A. Fishing potential observed */}
      <div>
        <div className="flex items-center gap-1.5 mb-2">
          <Fish className="size-3.5 text-muted-foreground" />
          <p className="text-xs font-medium text-muted-foreground">Fishing potential observed</p>
        </div>
        <div className="flex gap-2" role="group" aria-label="Observed fishing outcome">
          {FISHING_OPTIONS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              id={`fb-fishing-${value}`}
              onClick={() => setFishingOutcome(fishingOutcome === value ? null : value)}
              className={`flex-1 rounded-lg border px-3 py-2 text-xs font-medium transition-all ${
                fishingOutcome === value
                  ? "border-rose bg-rose/20 text-rose"
                  : "border-border bg-deep text-muted-foreground hover:border-rose/40 hover:text-shell"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* B. Safety conditions observed */}
      <div>
        <div className="flex items-center gap-1.5 mb-2">
          <ShieldCheck className="size-3.5 text-muted-foreground" />
          <p className="text-xs font-medium text-muted-foreground">Safety conditions observed</p>
        </div>
        <div className="flex gap-2" role="group" aria-label="Observed safety outcome">
          {SAFETY_OPTIONS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              id={`fb-safety-${value}`}
              onClick={() => setSafetyOutcome(safetyOutcome === value ? null : value)}
              className={`flex-1 rounded-lg border px-3 py-2 text-xs font-medium transition-all ${
                safetyOutcome === value
                  ? "border-rose bg-rose/20 text-rose"
                  : "border-border bg-deep text-muted-foreground hover:border-rose/40 hover:text-shell"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* C. Usefulness rating */}
      <div>
        <p className="text-xs font-medium text-muted-foreground mb-2">
          Was ORCA's recommendation useful?
        </p>
        <div className="flex gap-2" role="group" aria-label="Usefulness rating">
          <button
            type="button"
            id="fb-rating-positive"
            onClick={() => setRating(rating === "positive" ? null : "positive")}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium transition-all ${
              rating === "positive"
                ? "border-safe bg-safe/20 text-safe"
                : "border-border bg-deep text-muted-foreground hover:border-safe/40 hover:text-shell"
            }`}
          >
            <ThumbsUp className="size-3.5" />
            Yes
          </button>
          <button
            type="button"
            id="fb-rating-negative"
            onClick={() => setRating(rating === "negative" ? null : "negative")}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium transition-all ${
              rating === "negative"
                ? "border-danger bg-danger/20 text-danger"
                : "border-border bg-deep text-muted-foreground hover:border-danger/40 hover:text-shell"
            }`}
          >
            <ThumbsDown className="size-3.5" />
            No
          </button>
        </div>
      </div>

      {/* D. Optional field note */}
      {showNote ? (
        <textarea
          id="fb-comment"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Add a field note… (optional)"
          rows={2}
          className="w-full resize-none rounded-lg border border-border bg-deep px-3 py-2 text-xs text-shell placeholder:text-muted-foreground/60 focus:border-rose/50 focus:outline-none"
        />
      ) : (
        <button
          type="button"
          id="fb-add-note-toggle"
          onClick={() => setShowNote(true)}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-shell transition-colors"
        >
          <MessageSquare className="size-3.5" />
          Add field note…
        </button>
      )}

      {/* Validation hint */}
      {!canSubmit && (fishingOutcome === null && safetyOutcome === null) && activeZone && (
        <p className="text-[11px] text-muted-foreground">
          Select at least one fishing or safety observation to submit.
        </p>
      )}

      {/* Error */}
      {submitState === "error" && (
        <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">
          <AlertCircle className="size-3.5 shrink-0" />
          {errorMsg}
        </div>
      )}

      {/* Submit */}
      <Button
        id="fb-submit"
        type="button"
        className="w-full"
        disabled={!canSubmit}
        onClick={handleSubmit}
      >
        {submitState === "submitting" ? (
          <span className="flex items-center gap-2">
            <Loader2 className="size-3.5 animate-spin" />
            Submitting…
          </span>
        ) : (
          "Submit Field Observation"
        )}
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Banner: just-submitted (in-session only, resets on reload)
// ---------------------------------------------------------------------------

export function SuccessBanner() {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-safe/30 bg-safe/10 px-4 py-4">
      <CheckCircle className="size-5 shrink-0 text-safe" />
      <div>
        <p className="text-sm font-medium text-shell">Field observation recorded</p>
        <p className="text-[11px] text-muted-foreground mt-0.5">
          Thank you — your data helps calibrate future ORCA predictions.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Banner: already submitted for this specific prediction (localStorage-based)
// ---------------------------------------------------------------------------

export function AlreadySubmittedBanner() {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-deep px-4 py-4">
      <CheckCircle className="size-5 shrink-0 text-muted-foreground" />
      <div>
        <p className="text-sm font-medium text-shell">Feedback already submitted for this prediction</p>
        <p className="text-[11px] text-muted-foreground mt-0.5">
          A new form will appear when ORCA generates a different prediction.
        </p>
      </div>
    </div>
  );
}
