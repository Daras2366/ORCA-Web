from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os

# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DATA_PATH = os.path.join(
    BASE_DIR,
    "data",
    "safety",
    "unified_safety.csv"
)

from backend.agents.safety_agent.forecast_adapter import (
    get_tomorrow_forecast,
    calculate_forecast_safety,
    get_safest_time
)


# ---------------------------------------------------------
# APP
# ---------------------------------------------------------

app = FastAPI(
    title="ORCA Safety Agent API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

df = pd.read_csv(DATA_PATH)

df.columns = df.columns.str.strip()

print(
    f"Safety dataset loaded: {len(df)} rows"
)


# ---------------------------------------------------------
# REQUEST SCHEMAS
# ---------------------------------------------------------

class SafetyRequest(BaseModel):
    zone_id: str
    latitude: float | None = None
    longitude: float | None = None


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
            np.clip(
                wind / 15,
                0,
                1
            ) * 0.25
        )

    if wave is not None:

        risks.append(
            np.clip(
                wave / 4,
                0,
                1
            ) * 0.25
        )

    if cyclone_dist is not None:

        cyclone_risk = (
            1 -
            np.clip(
                cyclone_dist / 500,
                0,
                1
            )
        )

        risks.append(
            cyclone_risk * 0.25
        )

    if cyclone_wind is not None:

        risks.append(
            np.clip(
                cyclone_wind / 80,
                0,
                1
            ) * 0.15
        )

    if rainfall is not None:

        risks.append(
            np.clip(
                rainfall / 10,
                0,
                1
            ) * 0.10
        )

    if not risks:

        return None

    return round(
        float(sum(risks)),
        4
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

    zone_id = request.zone_id.strip()

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

    risk_score = calculate_risk(row)

    risk_level = get_risk_level(
        risk_score
    )

    return {

        "agent": "Safety Agent",

        "status": "success",

        "mode": "current",

        "zone_id": str(
            row["zone_id"]
        ),

        "risk_score": risk_score,

        "risk_level": risk_level,

        "evidence": {

            "wind_speed_ms":
                get_value(
                    row,
                    "wind_speed_ms"
                ),

            "wave_height_m":
                get_value(
                    row,
                    "wave_height_m"
                ),

            "wave_period_s":
                get_value(
                    row,
                    "wave_period_s"
                ),

            "wave_direction_deg":
                get_value(
                    row,
                    "wave_direction_deg"
                ),

            "cyclone_distance_km":
                get_value(
                    row,
                    "cyclone_distance_km"
                ),

            "cyclone_wind_kt":
                get_value(
                    row,
                    "cyclone_wind_kt"
                ),

            "rainfall_mean":
                get_value(
                    row,
                    "rainfall_mean"
                ),

            "current_speed_ms":
                get_value(
                    row,
                    "current_speed_ms"
                )

        }

    }

# ---------------------------------------------------------
# CURRENT SAFETY RANKING FOR ALL PFZ ZONES
# ---------------------------------------------------------

@app.get("/safety/ranking")
def safety_ranking():

    # Prefer actual PFZ observations
    if "pfz_label" in df.columns:
        rows = df[df["pfz_label"] == 1].copy()
    else:
        rows = df.copy()

    if rows.empty:
        raise HTTPException(
            status_code=404,
            detail="No PFZ zones available"
        )

    results = []

    for _, row in rows.iterrows():

        risk_score = calculate_risk(row)
        risk_level = get_risk_level(risk_score)

        results.append({
            "zone_id": str(row["zone_id"]),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "safety_score": (
                round(1 - risk_score, 4)
                if risk_score is not None
                else None
            )
        })

    # Highest risk first
    results.sort(
        key=lambda x: (
            x["risk_score"]
            if x["risk_score"] is not None
            else -1
        ),
        reverse=True
    )

    return {
        "agent": "Safety Agent",
        "status": "success",
        "mode": "current_ranking",
        "zones": results
    }

# ---------------------------------------------------------
# TOMORROW FORECAST
# ---------------------------------------------------------

@app.post("/safety/forecast")
def safety_forecast(
    request: ForecastRequest
):

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

    scored = calculate_forecast_safety(
        forecast
    )

    # ---------------------------------------------
    # Safest hour
    # ---------------------------------------------

    safest, _ = get_safest_time(
        forecast
    )

    return {

        "agent": "Safety Agent",

        "status": "success",

        "mode": "tomorrow_forecast",

        "zone_id": zone_id,

        "location": {

            "latitude": latitude,

            "longitude": longitude

        },

        "forecast_date":
            scored[0]["time"][:10],

        "safest_time": safest,

        "hourly_forecast": scored

    }


# ---------------------------------------------------------
# SAFEST TIME ONLY
# ---------------------------------------------------------

@app.post("/safety/safest-time")
def safest_time(
    request: ForecastRequest
):

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

    safest, scored = get_safest_time(
        forecast
    )

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

        "date":
            safest["time"][:10],

        "safest_time":
            safest["time"],

        "forecast_safety_score":
            safest["forecast_safety_score"],

        "forecast_safety_level":
            safest["forecast_safety_level"],

        "conditions": {

            "wind_speed_ms":
                safest["wind_speed_ms"],

            "wave_height_m":
                safest["wave_height_m"],

            "wave_period_s":
                safest["wave_period_s"],

            "wave_direction_deg":
                safest["wave_direction_deg"],

            "precipitation_mm":
                safest["precipitation_mm"]

        },

        "hourly_options": scored

    }
