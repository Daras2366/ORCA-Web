"""
ORCA Feedback API — feedback_api.py

Endpoints (mounted under /api/feedback in query_agent/main.py):
    POST /feedback               — submit a field observation
    GET  /feedback/metrics       — accuracy statistics
    GET  /feedback/learning-status — readiness for calibration
    POST /feedback/retrain       — evaluate & conditionally deploy calibration

Persistent storage (JSONL, no database required):
    backend/feedback_data/feedback.jsonl
    backend/feedback_data/learned_model.json

Threshold system (documented):
    Fishing (HSI 0–1):
        good     >= 0.65
        moderate  0.35–0.65
        poor     < 0.35

    Safety (risk_score 0–1):
        safe     risk_score < 0.40  (safety_score > 60)
        moderate 0.40–0.70
        unsafe   > 0.70
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator
from typing import Optional, Literal
import json
import os
import uuid
from datetime import datetime, timezone
import copy

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FEEDBACK_DIR = os.path.join(_BASE_DIR, "feedback_data")
FEEDBACK_FILE = os.path.join(FEEDBACK_DIR, "feedback.jsonl")
MODEL_FILE = os.path.join(FEEDBACK_DIR, "learned_model.json")

os.makedirs(FEEDBACK_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Default calibration thresholds
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLDS = {
    "fishing": {
        "good_min": 0.65,
        "moderate_min": 0.35,
    },
    "safety": {
        "safe_max_risk": 0.40,
        "moderate_max_risk": 0.70,
    },
}

MINIMUM_SAMPLES = 20

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class PredictionSnapshot(BaseModel):
    fishing_score: Optional[float] = None
    safety_score: Optional[float] = None
    final_score: Optional[float] = None
    decision: Optional[str] = None
    model_version: Optional[str] = "calibrated_v1"


class FeedbackRequest(BaseModel):
    zone_id: str
    feedback_type: Literal["fishing", "safety"]
    prediction: PredictionSnapshot
    observed_outcome: str  # good/moderate/poor (fishing) or safe/moderate/unsafe (safety)
    rating: Optional[Literal["positive", "negative"]] = None
    comment: Optional[str] = None
    # Stable identifier for this prediction instance; used by the frontend
    # for duplicate-submission protection. Optional for backwards compatibility.
    prediction_id: Optional[str] = None

    @validator("zone_id")
    def zone_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("zone_id must not be empty")
        return v.strip().upper()

    @validator("observed_outcome")
    def valid_outcome(cls, v, values):
        ftype = values.get("feedback_type")
        fishing_outcomes = {"good", "moderate", "poor"}
        safety_outcomes = {"safe", "moderate", "unsafe"}
        v = v.strip().lower()
        if ftype == "fishing" and v not in fishing_outcomes:
            raise ValueError(f"fishing observed_outcome must be one of {fishing_outcomes}")
        if ftype == "safety" and v not in safety_outcomes:
            raise ValueError(f"safety observed_outcome must be one of {safety_outcomes}")
        return v


# ---------------------------------------------------------------------------
# Helpers — I/O
# ---------------------------------------------------------------------------


def _load_all_feedback() -> list[dict]:
    if not os.path.exists(FEEDBACK_FILE):
        return []
    records = []
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def _append_feedback(record: dict) -> None:
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _load_model() -> dict:
    if not os.path.exists(MODEL_FILE):
        return {
            "model_version": "calibrated_v1",
            "thresholds": copy.deepcopy(DEFAULT_THRESHOLDS),
            "sample_count": 0,
            "old_accuracy": None,
            "new_accuracy": None,
            "improvement": None,
            "timestamp": None,
        }
    with open(MODEL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_model(data: dict) -> None:
    with open(MODEL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _version_model(current: dict) -> None:
    """Copy the current model file to a versioned backup."""
    version = current.get("model_version", "calibrated_v1")
    # Extract version number
    try:
        num = int(version.split("_v")[-1])
    except (ValueError, IndexError):
        num = 1
    backup_name = f"learned_model_v{num}.json"
    backup_path = os.path.join(FEEDBACK_DIR, backup_name)
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)


# ---------------------------------------------------------------------------
# Helpers — prediction validation
# ---------------------------------------------------------------------------


def _fishing_label_from_score(hsi: float, thresholds: dict) -> str:
    """Convert an HSI score to a fishing outcome label using thresholds."""
    good_min = thresholds["fishing"]["good_min"]
    moderate_min = thresholds["fishing"]["moderate_min"]
    if hsi >= good_min:
        return "good"
    elif hsi >= moderate_min:
        return "moderate"
    else:
        return "poor"


def _safety_label_from_risk(risk_score: float, thresholds: dict) -> str:
    """Convert a risk_score (0–1) to a safety outcome label using thresholds."""
    safe_max = thresholds["safety"]["safe_max_risk"]
    moderate_max = thresholds["safety"]["moderate_max_risk"]
    if risk_score <= safe_max:
        return "safe"
    elif risk_score <= moderate_max:
        return "moderate"
    else:
        return "unsafe"


def _compute_prediction_match(
    feedback_type: str,
    prediction: PredictionSnapshot,
    observed_outcome: str,
    thresholds: dict,
) -> bool:
    """Return True if the ORCA prediction matches the observed outcome."""
    if feedback_type == "fishing":
        hsi = prediction.fishing_score
        if hsi is None:
            return False
        predicted_label = _fishing_label_from_score(hsi, thresholds)
        return predicted_label == observed_outcome

    elif feedback_type == "safety":
        # safety_score is 0–100 (1 - risk_score)*100
        # Convert back to risk_score for threshold comparison
        safety_score = prediction.safety_score
        if safety_score is None:
            return False
        risk_score = 1.0 - (safety_score / 100.0)
        predicted_label = _safety_label_from_risk(risk_score, thresholds)
        return predicted_label == observed_outcome

    return False


# ---------------------------------------------------------------------------
# Helpers — metrics
# ---------------------------------------------------------------------------


def _compute_metrics(records: list[dict]) -> dict:
    total = len(records)
    validated = [r for r in records if r.get("prediction_match") is not None]

    matches = sum(1 for r in validated if r.get("prediction_match") is True)
    mismatches = sum(1 for r in validated if r.get("prediction_match") is False)

    overall_accuracy = round(matches / len(validated), 4) if validated else None

    fishing_records = [r for r in validated if r.get("feedback_type") == "fishing"]
    safety_records = [r for r in validated if r.get("feedback_type") == "safety"]

    fishing_matches = sum(1 for r in fishing_records if r.get("prediction_match") is True)
    safety_matches = sum(1 for r in safety_records if r.get("prediction_match") is True)

    fishing_accuracy = (
        round(fishing_matches / len(fishing_records), 4) if fishing_records else None
    )
    safety_accuracy = (
        round(safety_matches / len(safety_records), 4) if safety_records else None
    )

    return {
        "total_feedback": total,
        "validated_feedback": len(validated),
        "overall_accuracy": overall_accuracy,
        "fishing_accuracy": fishing_accuracy,
        "safety_accuracy": safety_accuracy,
        "matches": matches,
        "mismatches": mismatches,
        "validated_samples_available": len(validated),
    }


# ---------------------------------------------------------------------------
# Helpers — calibration evaluation
# ---------------------------------------------------------------------------


def _evaluate_thresholds(validated: list[dict], thresholds: dict) -> float:
    """Compute accuracy of a given threshold set against validated observations."""
    if not validated:
        return 0.0
    correct = 0
    for r in validated:
        ftype = r.get("feedback_type")
        observed = r.get("observed_outcome")
        pred = r.get("original_prediction", {})

        if ftype == "fishing":
            hsi = pred.get("fishing_score")
            if hsi is None:
                continue
            snap = PredictionSnapshot(fishing_score=hsi)
            if _fishing_label_from_score(hsi, thresholds) == observed:
                correct += 1

        elif ftype == "safety":
            safety_score = pred.get("safety_score")
            if safety_score is None:
                continue
            risk_score = 1.0 - (safety_score / 100.0)
            if _safety_label_from_risk(risk_score, thresholds) == observed:
                correct += 1

    return round(correct / len(validated), 4)


def _find_best_thresholds(validated: list[dict]) -> dict:
    """
    Grid-search over a small set of candidate thresholds.
    Returns the threshold set with the highest accuracy.
    """
    candidates = []

    # Candidate fishing thresholds
    for good_min in [0.55, 0.60, 0.65, 0.70, 0.75]:
        for moderate_min in [0.25, 0.30, 0.35, 0.40, 0.45]:
            if moderate_min >= good_min:
                continue
            candidates.append({
                "fishing": {"good_min": good_min, "moderate_min": moderate_min},
                "safety": DEFAULT_THRESHOLDS["safety"].copy(),
            })

    # Candidate safety thresholds
    for safe_max in [0.30, 0.35, 0.40, 0.45]:
        for moderate_max in [0.60, 0.65, 0.70, 0.75, 0.80]:
            if safe_max >= moderate_max:
                continue
            candidates.append({
                "fishing": DEFAULT_THRESHOLDS["fishing"].copy(),
                "safety": {"safe_max_risk": safe_max, "moderate_max_risk": moderate_max},
            })

    if not candidates:
        return copy.deepcopy(DEFAULT_THRESHOLDS)

    best = max(candidates, key=lambda t: _evaluate_thresholds(validated, t))
    return best


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("")
def submit_feedback(request: FeedbackRequest):
    """
    Submit a field observation for a completed ORCA prediction.

    The 'observed_outcome' is the learning signal.
    'rating' (thumbs up/down) is a usefulness metric only.
    """
    model = _load_model()
    thresholds = model.get("thresholds", DEFAULT_THRESHOLDS)

    prediction_match = _compute_prediction_match(
        request.feedback_type,
        request.prediction,
        request.observed_outcome,
        thresholds,
    )

    feedback_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    record = {
        "feedback_id": feedback_id,
        "timestamp": timestamp,
        "zone_id": request.zone_id,
        "feedback_type": request.feedback_type,
        "original_prediction": request.prediction.dict(),
        "observed_outcome": request.observed_outcome,
        "rating": request.rating,
        "comment": request.comment,
        "model_version": request.prediction.model_version or "calibrated_v1",
        "prediction_match": prediction_match,
        # prediction_id is optional; stored if provided by frontend
        "prediction_id": request.prediction_id,
    }

    _append_feedback(record)

    return {
        "success": True,
        "feedback_id": feedback_id,
        "prediction_match": prediction_match,
    }


@router.get("/metrics")
def get_metrics():
    """Return overall and per-type accuracy metrics."""
    records = _load_all_feedback()
    metrics = _compute_metrics(records)
    return {"status": "success", **metrics}


@router.get("/recent")
def get_recent_feedback(limit: int = 20):
    """Return the most recent feedback records (newest first)."""
    records = _load_all_feedback()
    # Sort by timestamp descending, newest first
    records_sorted = sorted(
        records,
        key=lambda r: r.get("timestamp", ""),
        reverse=True,
    )
    recent = records_sorted[:limit]
    # Return only fields safe to expose in the UI
    public = [
        {
            "feedback_id": r.get("feedback_id", ""),
            "timestamp": r.get("timestamp", ""),
            "zone_id": r.get("zone_id", ""),
            "feedback_type": r.get("feedback_type", ""),
            "observed_outcome": r.get("observed_outcome", ""),
            "rating": r.get("rating"),
            "prediction_match": r.get("prediction_match"),
            "model_version": r.get("model_version", ""),
        }
        for r in recent
    ]
    return {"status": "success", "records": public, "total": len(records)}


@router.get("/learning-status")
def get_learning_status():
    """Return whether sufficient validated samples exist for calibration."""
    records = _load_all_feedback()
    validated = [r for r in records if r.get("prediction_match") is not None]
    model = _load_model()

    ready = len(validated) >= MINIMUM_SAMPLES
    status_label = "ready_for_learning" if ready else "collecting_feedback"

    return {
        "model_version": model.get("model_version", "calibrated_v1"),
        "validated_samples": len(validated),
        "minimum_samples": MINIMUM_SAMPLES,
        "ready": ready,
        "status": status_label,
        "last_evaluation": model.get("timestamp"),
        "last_accuracy": model.get("new_accuracy"),
    }


@router.post("/retrain")
def retrain_model():
    """
    Evaluate alternative calibration thresholds against validated feedback.
    Deploy ONLY if new accuracy exceeds current accuracy.
    Never retrains the underlying ML models.
    """
    records = _load_all_feedback()
    validated = [r for r in records if r.get("prediction_match") is not None]

    if len(validated) < MINIMUM_SAMPLES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient validated observations: {len(validated)}/{MINIMUM_SAMPLES}. "
                "Collect more field data before evaluating calibration."
            ),
        )

    # Load current model
    current_model = _load_model()
    current_thresholds = current_model.get("thresholds", DEFAULT_THRESHOLDS)

    # Evaluate current accuracy
    old_accuracy = _evaluate_thresholds(validated, current_thresholds)

    # Find the best alternative thresholds
    best_thresholds = _find_best_thresholds(validated)
    new_accuracy = _evaluate_thresholds(validated, best_thresholds)

    improvement = round(new_accuracy - old_accuracy, 4)
    timestamp = datetime.now(timezone.utc).isoformat()

    if new_accuracy > old_accuracy:
        # Backup the current model before overwriting
        _version_model(current_model)

        # Determine next version number
        try:
            old_num = int(
                current_model.get("model_version", "calibrated_v1").split("_v")[-1]
            )
        except (ValueError, IndexError):
            old_num = 1
        new_version = f"calibrated_v{old_num + 1}"

        new_model = {
            "model_version": new_version,
            "thresholds": best_thresholds,
            "sample_count": len(validated),
            "old_accuracy": old_accuracy,
            "new_accuracy": new_accuracy,
            "improvement": improvement,
            "timestamp": timestamp,
        }
        _save_model(new_model)

        return {
            "status": "deployed",
            "message": f"Calibration updated to {new_version}.",
            "model_version": new_version,
            "old_accuracy": old_accuracy,
            "new_accuracy": new_accuracy,
            "improvement": improvement,
            "sample_count": len(validated),
            "timestamp": timestamp,
        }
    else:
        return {
            "status": "retained",
            "message": "Previous calibration retained — no improvement.",
            "model_version": current_model.get("model_version", "calibrated_v1"),
            "old_accuracy": old_accuracy,
            "new_accuracy": new_accuracy,
            "improvement": improvement,
            "sample_count": len(validated),
            "timestamp": timestamp,
        }
