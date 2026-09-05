"""
ORCA Routing Agent - M3_v2 Deterministic Route Scoring Engine
predict.py

Loaded by route_api.py to score a dataset row using the
deterministic route_model.pkl artifact (not a trained ML model).

The artifact provides:
  - quantile references for safety scoring
  - component weights for efficiency and safety
  - metadata describing the scoring contract

This implementation follows the logic defined in Routing_Agent_v2.ipynb.
"""

import os
import math

import joblib
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Load the model artifact using a path relative to this file.
# Never use hardcoded absolute paths.
# ---------------------------------------------------------------------------
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "route_model.pkl")
model_artifact = joblib.load(_MODEL_PATH)

_refs = model_artifact["safety_references"]
_sw   = model_artifact["safety_weights"]
_rw   = model_artifact["route_score_weights"]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _safe_float(value, decimals: int = 4):
    """
    Convert a pandas / numpy scalar to a plain Python float,
    returning None for NaN / Inf values so JSON serialisation is safe.
    """
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, decimals)


def _safe_bool(value) -> bool:
    """Convert a pandas / numpy boolean-like scalar to a plain Python bool."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    return bool(value)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _interpolate_safety(value, q10, q50, q90,
                        low_is_safe: bool = False) -> float:
    """
    Linearly interpolate a safety score [0, 1] using three quantile anchors.

    If low_is_safe=True  (e.g. current speed):
        q10 -> score 1.0, q90 -> score 0.0
    If low_is_safe=False (e.g. depth, mpa_distance):
        q10 -> score 0.0, q90 -> score 1.0
    """
    if low_is_safe:
        if value <= q10:
            return 1.0
        if value >= q90:
            return 0.0
        return _clamp(1.0 - (value - q10) / (q90 - q10))
    else:
        if value <= q10:
            return 0.0
        if value >= q90:
            return 1.0
        return _clamp((value - q10) / (q90 - q10))


# ---------------------------------------------------------------------------
# Main prediction function
# ---------------------------------------------------------------------------

def predict_route(row: dict) -> dict:
    """
    Generate the final structured Route Agent output for a single data row.

    Parameters
    ----------
    row : dict
        A dictionary of feature values for one routing zone,
        typically obtained from a CSV row via .to_dict().

    Returns
    -------
    dict
        JSON-serialisable dictionary matching the route_agent output contract.
        On failure, returns a dict with status="error".

    Notes
    -----
    The route_score is computed live from raw components using the
    route_model.pkl artifact weights.  It should closely match (but may
    differ slightly from) the pre-computed final_route_score column because
    both use the same M3_v2 formula with the same weights.
    The API also exposes the dataset's own final_route_score,
    final_route_confidence, and adjusted_final_route_score for comparison.
    """

    # --- Efficiency score -------------------------------------------------
    efficiency = row.get("efficiency_score_v2")

    # --- Route safety score -----------------------------------------------
    # The CSV already contains the pre-computed route_safety_score.
    # Use it when present; recompute from components only as fallback.
    route_safety = row.get("route_safety_score")

    if route_safety is None or (isinstance(route_safety, float) and
                                 math.isnan(float(route_safety))):
        # Recompute safety from depth, constraints, and current
        depth_val   = row.get("water_depth_m")
        current_val = row.get("current_speed_ms")

        # Depth safety
        if depth_val is not None and not (isinstance(depth_val, float) and
                                           math.isnan(float(depth_val))):
            depth_score = _interpolate_safety(
                float(depth_val),
                _refs["depth_q10"], _refs["depth_q50"], _refs["depth_q90"],
                low_is_safe=False
            )
        else:
            depth_score = None

        # Constraint safety (MPA + EEZ)
        constraint_score = row.get("constraint_safety_score")
        if constraint_score is None or (isinstance(constraint_score, float) and
                                         math.isnan(float(constraint_score))):
            constraint_score = None
        else:
            constraint_score = float(constraint_score)

        # Current safety
        if current_val is not None and not (isinstance(current_val, float) and
                                             math.isnan(float(current_val))):
            current_score = _interpolate_safety(
                float(current_val),
                _refs["current_q10"], _refs["current_q50"],
                _refs["current_q90"],
                low_is_safe=True
            )
        else:
            current_score = None

        components = [
            (depth_score,      _sw["depth"]),
            (constraint_score, _sw["constraints"]),
            (current_score,    _sw["current"]),
        ]
        available_safety = [(s, w) for s, w in components if s is not None]

        if available_safety:
            total_w = sum(w for _, w in available_safety)
            route_safety = sum(s * w for s, w in available_safety) / total_w
        else:
            route_safety = None

    # --- Compute live route_score -----------------------------------------
    score_components = []

    eff_val = None
    if efficiency is not None:
        try:
            eff_val = float(efficiency)
            if math.isnan(eff_val) or math.isinf(eff_val):
                eff_val = None
        except (TypeError, ValueError):
            eff_val = None

    saf_val = None
    if route_safety is not None:
        try:
            saf_val = float(route_safety)
            if math.isnan(saf_val) or math.isinf(saf_val):
                saf_val = None
        except (TypeError, ValueError):
            saf_val = None

    if eff_val is not None:
        score_components.append((eff_val, _rw["efficiency"]))
    if saf_val is not None:
        score_components.append((saf_val, _rw["safety"]))

    if not score_components:
        return {
            "agent": "route_agent",
            "status": "error",
            "error": {
                "code": "insufficient_route_data",
                "message": "Insufficient routing information to compute score."
            }
        }

    total_weight = sum(w for _, w in score_components)
    route_score  = sum(s * w for s, w in score_components) / total_weight
    route_score  = _clamp(float(route_score))

    # --- Confidence: fraction of key features present ---------------------
    key_features = [
        "distance_km", "travel_time_hr", "fuel_l_proxy",
        "water_depth_m", "current_speed_ms"
    ]

    def _is_present(key):
        val = row.get(key)
        if val is None:
            return False
        try:
            f = float(val)
            return not (math.isnan(f) or math.isinf(f))
        except (TypeError, ValueError):
            return False

    available_count = sum(1 for f in key_features if _is_present(f))
    confidence = available_count / len(key_features)

    # --- Build output dict -----------------------------------------------
    return {
        "agent": "route_agent",
        "status": "success",

        "zone_id": str(row["zone_id"]),

        "location": {
            "latitude":  _safe_float(row.get("latitude")),
            "longitude": _safe_float(row.get("longitude"))
        },

        "route_metrics": {
            "distance_km":    _safe_float(row.get("distance_km")),
            "travel_time_hr": _safe_float(row.get("travel_time_hr")),
            "fuel_l":         _safe_float(row.get("fuel_l_proxy"))
        },

        # Live-computed score (from artifact weights + raw components)
        "route_score":  round(route_score, 4),
        "confidence":   round(confidence, 2),

        # Pre-computed values from the M3 dataset
        "adjusted_route_score": _safe_float(
            row.get("adjusted_final_route_score")
        ),
        "route_safety_score":   _safe_float(row.get("route_safety_score")),
        "geofence_caution":     _safe_bool(row.get("geofence_caution")),

        "evidence": {
            "water_depth_m":            _safe_float(row.get("water_depth_m")),
            "current_speed_ms":         _safe_float(row.get("current_speed_ms")),
            "mpa_distance_km":          _safe_float(row.get("mpa_distance_km")),
            "eez_boundary_distance_km": _safe_float(
                row.get("eez_boundary_distance_km")
            ),
            "inside_mpa":  _safe_bool(row.get("inside_mpa")),
            "mpa_caution": _safe_bool(row.get("mpa_caution"))
        },

        # Dataset pre-computed fields for transparency / verification
        "dataset_scores": {
            "final_route_score":          _safe_float(
                row.get("final_route_score")
            ),
            "final_route_confidence":     _safe_float(
                row.get("final_route_confidence")
            ),
            "adjusted_final_route_score": _safe_float(
                row.get("adjusted_final_route_score")
            ),
            "efficiency_score_v2":        _safe_float(
                row.get("efficiency_score_v2")
            )
        }
    }