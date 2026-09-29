from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os
import time


from backend.agents.safety_agent.live_marine_adapter import get_live_conditions, get_live_conditions_bulk
from backend.agents.safety_agent.forecast_adapter import (
    get_tomorrow_forecast,
    calculate_forecast_safety,
    get_safest_time
)
from backend.agents.safety_agent.cyclone_adapter import get_cyclone_risk
from backend.agents.safety_agent.mosdac_lightning_adapter import get_mosdac_lightning_risk, get_mosdac_lightning_risk_bulk


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DATA_PATH = os.path.join(
    BASE_DIR,
    "data",
    "safety",
    "unified_safety.csv"
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")

app = FastAPI(
    title="ORCA Safety Agent API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:8080",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
df = pd.read_csv(DATA_PATH)
df.columns = df.columns.str.strip()
print(f"Safety dataset loaded: {len(df)} rows")


# ---------------------------------------------------------
# REQUEST SCHEMAS
# ---------------------------------------------------------
class SafetyRequest(BaseModel):
    zone_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    vessel: dict | None = None

class ForecastRequest(BaseModel):
    zone_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None


# ---------------------------------------------------------
# HELPER
# ---------------------------------------------------------
def get_value(row, *names):
    for name in names:
        if name in df.columns:
            x = row[name]

            if pd.notna(x):
                return float(x)

    return None


# ---------------------------------------------------------
# STATIC RISK CALCULATION
# ---------------------------------------------------------
def calculate_risk(row):
    risks = []

    wind = get_value(
        row,
        "wind_speed_ms"
    )

    wave = get_value(
        row,
        "wave_height_m"
    )

    cyclone_dist = get_value(
        row,
        "cyclone_distance_km"
    )

    cyclone_wind = get_value(
        row,
        "cyclone_wind_kt"
    )

    rainfall = get_value(
        row,
        "rainfall_mean"
    )

    if wind is not None:
        risks.append(
            np.clip(wind / 15, 0, 1) * 0.25
        )

    if wave is not None:
        risks.append(
            np.clip(wave / 4, 0, 1) * 0.25
        )

    if cyclone_dist is not None:
        cyclone_risk = (
            1 - np.clip(cyclone_dist / 500, 0, 1)
        )

        risks.append(
            cyclone_risk * 0.25
        )

    if cyclone_wind is not None:
        risks.append(
            np.clip(cyclone_wind / 80, 0, 1) * 0.15
        )

    if rainfall is not None:
        risks.append(
            np.clip(rainfall / 10, 0, 1) * 0.10
        )

    if not risks:
        return None

    return round(float(sum(risks)), 4)

def get_vessel_limits(vessel: dict | None) -> dict:
    """
    Return conservative operational weather limits for the vessel.

    These are ORCA prototype operating-envelope heuristics,
    not certified vessel limitations.
    """

    if not vessel:
        return {
            "wind_limit_ms": 15.0,
            "wave_limit_m": 4.0,
            "profile": "generic",
        }

    vessel_type = str(
        vessel.get("vessel_type", "other")
    ).lower()

    length = vessel.get("length_m")

    # Base limits by vessel class.
    limits = {
        "small_fishing_boat": {
            "wind_limit_ms": 10.0,
            "wave_limit_m": 1.5,
        },
        "gillnetter": {
            "wind_limit_ms": 11.0,
            "wave_limit_m": 1.8,
        },
        "longliner": {
            "wind_limit_ms": 13.0,
            "wave_limit_m": 2.5,
        },
        "trawler": {
            "wind_limit_ms": 15.0,
            "wave_limit_m": 3.0,
        },
        "purse_seiner": {
            "wind_limit_ms": 16.0,
            "wave_limit_m": 3.5,
        },
        "other": {
            "wind_limit_ms": 13.0,
            "wave_limit_m": 2.5,
        },
    }

    selected = limits.get(
        vessel_type,
        limits["other"],
    ).copy()

    # Length adjustment.
    # Larger vessels receive a modest increase in the
    # prototype operating envelope.
    if length is not None:
        try:
            length = float(length)

            if length >= 20:
                selected["wind_limit_ms"] += 2.0
                selected["wave_limit_m"] += 0.8

            elif length >= 12:
                selected["wind_limit_ms"] += 1.0
                selected["wave_limit_m"] += 0.4

        except (TypeError, ValueError):
            pass

    selected["profile"] = vessel_type

    return selected
    
def calculate_live_risk(
    data,
    vessel: dict | None = None,
):
    """
    Calculate vessel-aware live risk score (0–1).

    Lower vessel operating limits make the same environmental
    conditions produce a higher risk score.

    This is an ORCA prototype operational-risk heuristic,
    not a certified vessel safety limit.
    """

    limits = get_vessel_limits(vessel)

    wind_limit = limits["wind_limit_ms"]
    wave_limit = limits["wave_limit_m"]

    WEIGHTS = {
        "wind": 0.20,
        "waves": 0.20,
        "rainfall": 0.10,
        "current": 0.15,
        "cyclone": 0.20,
        "lightning": 0.15,
    }

    weighted_sum = 0.0
    total_weight = 0.0

    # --------------------------------------------------
    # WIND — vessel specific
    # --------------------------------------------------

    wind_kmh = data.get("wind_speed_kmh")

    if wind_kmh is not None:
        wind_ms = float(wind_kmh) / 3.6

        wind_risk = np.clip(
            wind_ms / wind_limit,
            0,
            1,
        )

        weighted_sum += (
            wind_risk * WEIGHTS["wind"]
        )

        total_weight += WEIGHTS["wind"]

    # --------------------------------------------------
    # WAVES — vessel specific
    # --------------------------------------------------

    wave = data.get("wave_height_m")

    if wave is not None:
        wave_risk = np.clip(
            float(wave) / wave_limit,
            0,
            1,
        )

        weighted_sum += (
            wave_risk * WEIGHTS["waves"]
        )

        total_weight += WEIGHTS["waves"]

    # --------------------------------------------------
    # RAINFALL
    # --------------------------------------------------

    rainfall = data.get("precipitation_mm")

    if rainfall is not None:

        rainfall_risk = np.clip(
            float(rainfall) / 10,
            0,
            1,
        )

        weighted_sum += (
            rainfall_risk *
            WEIGHTS["rainfall"]
        )

        total_weight += WEIGHTS["rainfall"]

    # --------------------------------------------------
    # CURRENT
    # --------------------------------------------------

    current = data.get("current_speed_ms")

    if current is not None:

        current_risk = np.clip(
            float(current) / 2,
            0,
            1,
        )

        weighted_sum += (
            current_risk *
            WEIGHTS["current"]
        )

        total_weight += WEIGHTS["current"]

    # --------------------------------------------------
    # CYCLONE
    # --------------------------------------------------

    cyclone = data.get("cyclone")

    if cyclone and cyclone.get("available"):

        weighted_sum += (
            float(cyclone.get("risk", 0))
            * WEIGHTS["cyclone"]
        )

        total_weight += WEIGHTS["cyclone"]

    # --------------------------------------------------
    # LIGHTNING
    # --------------------------------------------------

    lightning = data.get("lightning")

    if (
        lightning
        and lightning.get("available")
        and lightning.get("risk") is not None
    ):

        weighted_sum += (
            float(lightning["risk"])
            * WEIGHTS["lightning"]
        )

        total_weight += WEIGHTS["lightning"]

    if total_weight == 0:
        return None

    return round(
        float(weighted_sum / total_weight),
        4,
    )


# ---------------------------------------------------------
# RISK LEVEL
# ---------------------------------------------------------
def get_risk_level(risk_score):
    if risk_score is None:
        return "UNKNOWN"

    if risk_score <= 0.40:
        return "LOW"

    elif risk_score <= 0.70:
        return "MODERATE"

    else:
        return "HIGH"


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------
@app.get("/")
def home():
    return {
        "agent": "Safety Agent",
        "status": "running",
        "rows": len(df),

        "features": [
            "current_safety",
            "tomorrow_forecast",
            "safest_time",
            "wave_forecast",
            "wind_forecast",
            "rainfall_forecast"
        ]
    }


# ---------------------------------------------------------
# CURRENT / STATIC SAFETY
# ---------------------------------------------------------
@app.post("/safety/analyze")
def analyze_safety(request: SafetyRequest):
    latitude = request.latitude
    longitude = request.longitude

    zone_id = request.zone_id.strip() if request.zone_id else None

    # --------------------------------------------------
    # If coordinates were not supplied, get them from
    # the historical PFZ dataset.
    #
    # The coordinates are only being used to locate the
    # requested zone. The actual safety conditions below
    # come from the live API.
    # --------------------------------------------------

    if latitude is None or longitude is None:
        if not zone_id:
            raise HTTPException(
                status_code=400,
                detail="Provide zone_id or latitude and longitude"
            )

        rows = df[
            df["zone_id"]
            .astype(str)
            .str.upper()
            == zone_id.upper()
        ]

        if rows.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Zone {zone_id} not found"
            )

        row = rows.iloc[0]

        latitude = float(row["latitude"])
        longitude = float(row["longitude"])

    # --------------------------------------------------
    # LIVE DATA
    # --------------------------------------------------
    try:
        live = get_live_conditions(
            latitude,
            longitude
        )
        live["cyclone"] = get_cyclone_risk(
            latitude,
            longitude
        )
        live["lightning"] = get_mosdac_lightning_risk(
            latitude,
            longitude
        )

    except Exception as e:
        print(f"[Safety] Open-Meteo unavailable; using fallback: {str(e)}")
        # Provide a graceful fallback when Open-Meteo is unavailable
        # This allows the service to continue functioning with limited data
        live = {
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": None,
            "wave_height_m": None,
            "wave_period_s": None,
            "wave_direction_deg": None,
            "current_speed_ms": None,
            "current_direction_deg": None,
            "sst_c": None,
            "wind_speed_kmh": None,
            "wind_direction_deg": None,
            "precipitation_mm": None,
            "cyclone": get_cyclone_risk(latitude, longitude),
            "lightning": get_mosdac_lightning_risk(latitude, longitude),
            "source": "Fallback - Open-Meteo unavailable",
            "data_mode": "fallback"
        }

    # --------------------------------------------------
    # LIVE RISK
    # --------------------------------------------------
    risk_score = calculate_live_risk(
        live,
        request.vessel,
    )
    risk_level = get_risk_level(risk_score)

    # --------------------------------------------------
    # RESPONSE
    # --------------------------------------------------
    lightning = live.get("lightning", {})
    lightning_live = bool(lightning.get("available"))
    base_source = live.get("source", "Open-Meteo + GDACS")
    data_source = (
        base_source + " + MOSDAC Lightning Forecast"
        if lightning_live
        else base_source
    )

    return {
        "agent": "Safety Agent",
        "status": "success",
        "mode": live.get("data_mode", "live"),
        "data_source": data_source,
        "timestamp": live.get("timestamp"),

        "zone_id": zone_id,
        "location": {
            "latitude": latitude,
            "longitude": longitude
        },

        "risk_score": risk_score,
        "risk_level": risk_level,
        
        "vessel_specific": request.vessel is not None,
        "vessel_profile": (
            {
                "name": request.vessel.get("name"),
                "vessel_type": request.vessel.get("vessel_type"),
                "length_m": request.vessel.get("length_m"),
                "engine_power_hp": request.vessel.get("engine_power_hp"),
                "cruising_speed_kmh": request.vessel.get("cruising_speed_kmh"),
            }
            if request.vessel
            else None
        ),
        "operating_limits": get_vessel_limits(
            request.vessel
        ),

        "evidence": {
            "wind_speed_ms": (
                live["wind_speed_kmh"] / 3.6
                if live.get("wind_speed_kmh") is not None
                else None
            ),
            "wind_direction_deg": live.get("wind_direction_deg"),
            "wave_height_m": live.get("wave_height_m"),
            "wave_period_s": live.get("wave_period_s"),
            "wave_direction_deg": live.get("wave_direction_deg"),
            "rainfall_mean": live.get("precipitation_mm"),
            "current_speed_ms": live.get("current_speed_ms"),
            "current_direction_deg": live.get("current_direction_deg"),
            "sst_c": live.get("sst_c"),
            "cyclone": live.get("cyclone"),
            "lightning": lightning if lightning else {
                "available": False,
                "risk": None,
                "source": "not attempted",
                "timestamp": None,
            },
        }
    }

# ---------------------------------------------------------
# CURRENT SAFETY RANKING FOR ALL PFZ ZONES
# ---------------------------------------------------------
@app.get("/safety/ranking")
def safety_ranking():
    """
    Rank PFZ zones using LIVE marine/weather conditions.

    The static safety CSV is used only as a fallback if
    live retrieval fails.
    """

    # --------------------------------------------------
    # GET PFZ CANDIDATES
    # --------------------------------------------------
    zone_ids = df["zone_id"].astype(str).str.upper()
    rows = df[zone_ids.str.startswith("PFZ")].copy()

    if rows.empty:
        raise HTTPException(
            status_code=404,
            detail="No PFZ zones available"
        )

    # --------------------------------------------------
    # PREPARE LIVE REQUEST
    # --------------------------------------------------
    points = []

    for _, row in rows.iterrows():
        try:
            points.append({
                "zone_id": str(row["zone_id"]),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
            })

        except Exception:
            continue

    # --------------------------------------------------
    # TRY LIVE DATA
    # --------------------------------------------------
    live_data = {}
    live_error = None

    try:
        t0 = time.time()

        live_data = get_live_conditions_bulk(points)

        # Use the exact same lightning source used by
        # individual /safety/analyze requests.
        lightning_data = get_mosdac_lightning_risk_bulk(points)

    except Exception as e:
        live_error = str(e)

        print(
            "[SAFETY] Live ranking failed:",
            e
        )

        lightning_data = {}

    # --------------------------------------------------
    # BUILD RESULTS
    # --------------------------------------------------
    results = []

    for _, row in rows.iterrows():
        zone_id = str(
            row["zone_id"]
        ).upper()

        live = live_data.get(zone_id)

        # ==================================================
        # LIVE SCORE
        # ==================================================
        if live:
            live["lightning"] = (
                lightning_data.get(
                    zone_id,
                    {
                        "available": False,
                        "risk": None,
                        "raw_lpi": None,
                        "source": "MOSDAC Lightning Forecast -- unavailable",
                    }
                )
            )
            
            risk_score = calculate_live_risk(live)
            risk_level = get_risk_level(risk_score)
            
            safety_score = (
                round(1 - risk_score, 4)
                if risk_score is not None
                else None
            )

            results.append({
                "zone_id": zone_id,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "safety_score": safety_score,
                "data_mode": "live",
                "data_source": "Open-Meteo + GDACS",
                "timestamp": live.get("timestamp"),
                "evidence": {
                    "wind_speed_ms": (
                        live["wind_speed_kmh"] / 3.6
                        if live.get("wind_speed_kmh") is not None
                        else None
                    ),
                    "wave_height_m": live.get("wave_height_m"),
                    "wave_period_s": live.get("wave_period_s"),
                    "rainfall_mm": live.get("precipitation_mm"),
                    "current_speed_ms": live.get("current_speed_ms"),
                    "cyclone": live.get("cyclone"),
                    "lightning": live.get("lightning"),
                }
            })
            continue

        # ==================================================
        # STATIC FALLBACK
        # ==================================================
        fallback_risk = calculate_risk(row)
        fallback_level = get_risk_level(fallback_risk)

        results.append({
            "zone_id": zone_id,
            "risk_score": fallback_risk,
            "risk_level": fallback_level,

            "safety_score":
                (
                    round(1 - fallback_risk, 4)
                    
                    if fallback_risk is not None
                    else None
                ),
                
            "data_mode": "fallback",
            "data_source": "ORCA static safety dataset",
            "timestamp": None,
            "evidence": {},

            "fallback_reason":
                live_error
                or "Live data unavailable for this zone",
        })

    # --------------------------------------------------
    # SORT
    # --------------------------------------------------
    results.sort(
        key = lambda x: x["risk_score"]
        if x["risk_score"] is not None else 999
    )

    return {
        "agent": "Safety Agent",
        "status": "success",
        "mode": "live_first",
        "zones": results,

        "live_zone_count":
            sum(
                1
                for x in results
                if x["data_mode"] == "live"
            ),

        "fallback_zone_count":
            sum(
                1
                for x in results
                if x["data_mode"] == "fallback"
            )
    }

# ---------------------------------------------------------
# TOMORROW FORECAST
# ---------------------------------------------------------
@app.post("/safety/forecast")
def safety_forecast(request: ForecastRequest):
    latitude = request.latitude
    longitude = request.longitude
    zone_id = request.zone_id

    # ---------------------------------------------
    # If zone_id is supplied, get coordinates
    # from Safety dataset
    # ---------------------------------------------
    if zone_id:
        rows = df[
            df["zone_id"]
            .astype(str)
            .str.upper()
            == zone_id.strip().upper()
        ]

        if rows.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Zone {zone_id} not found"
            )

        row = rows.iloc[0]

        if latitude is None:
            latitude = float(
                row["latitude"]
            )

        if longitude is None:
            longitude = float(
                row["longitude"]
            )

    # ---------------------------------------------
    # Coordinates are mandatory
    # ---------------------------------------------
    if latitude is None or longitude is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide zone_id or "
                "latitude and longitude"
            )
        )

    # ---------------------------------------------
    # Get hourly forecast
    # ---------------------------------------------
    try:
        forecast = get_tomorrow_forecast(
            latitude,
            longitude
        )

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Forecast API error: {str(e)}"
        )

    if not forecast:
        raise HTTPException(
            status_code=404,
            detail="No forecast data available"
        )

    # ---------------------------------------------
    # Calculate hourly safety
    # ---------------------------------------------
    scored = calculate_forecast_safety(forecast)

    # ---------------------------------------------
    # Safest hour
    # ---------------------------------------------
    safest, _ = get_safest_time(forecast)

    return {
        "agent": "Safety Agent",
        "status": "success",
        "mode": "tomorrow_forecast",
        "zone_id": zone_id,

        "location": {
            "latitude": latitude,
            "longitude": longitude
        },

        "forecast_date": scored[0]["time"][:10],
        "safest_time": safest,
        "hourly_forecast": scored
    }


# ---------------------------------------------------------
# SAFEST TIME ONLY
# ---------------------------------------------------------
@app.post("/safety/safest-time")
def safest_time(request: ForecastRequest):
    latitude = request.latitude
    longitude = request.longitude
    zone_id = request.zone_id

    # ---------------------------------------------
    # Resolve zone coordinates
    # ---------------------------------------------
    if zone_id:
        rows = df[
            df["zone_id"]
            .astype(str)
            .str.upper()
            == zone_id.strip().upper()
        ]

        if rows.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Zone {zone_id} not found"
            )

        row = rows.iloc[0]

        latitude = (
            float(row["latitude"])
            if latitude is None
            else latitude
        )

        longitude = (
            float(row["longitude"])
            if longitude is None
            else longitude
        )

    if latitude is None or longitude is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide zone_id or "
                "latitude and longitude"
            )
        )

    # ---------------------------------------------
    # Fetch forecast
    # ---------------------------------------------
    try:
        forecast = get_tomorrow_forecast(
            latitude,
            longitude
        )

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Forecast API error: {str(e)}"
        )

    if not forecast:
        raise HTTPException(
            status_code=404,
            detail="No forecast data available"
        )

    # ---------------------------------------------
    # Find safest time
    # ---------------------------------------------
    safest, scored = get_safest_time(forecast)

    if safest is None:
        raise HTTPException(
            status_code=404,
            detail="Unable to calculate safety"
        )

    return {
        "agent": "Safety Agent",
        "status": "success",
        "mode": "safest_time",
        "zone_id": zone_id,

        "location": {
            "latitude": latitude,
            "longitude": longitude
        },

        "date": safest["time"][:10],
        "safest_time": safest["time"],
        "forecast_safety_score": safest["forecast_safety_score"],
        "forecast_safety_level": safest["forecast_safety_level"],

        "conditions": {
            "wind_speed_ms": safest["wind_speed_ms"],
            "wave_height_m": safest["wave_height_m"],
            "wave_period_s": safest["wave_period_s"],
            "wave_direction_deg": safest["wave_direction_deg"],
            "precipitation_mm": safest["precipitation_mm"]
        },

        "hourly_options": scored
    }