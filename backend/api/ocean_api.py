from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os
from math import radians, sin, cos, asin, sqrt

from backend.agents.ocean_agent.live_ocean_adapter import get_live_ocean
from backend.agents.ocean_agent.chlorophyll_adapter import get_chlorophyll


app = FastAPI(title="ORCA Ocean Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DATA_PATH = os.path.join(
    BASE_DIR,
    "data",
    "ocean",
    "unified_ocean_current.csv"
)

df = pd.read_csv(DATA_PATH)
df.columns = df.columns.str.strip()

print(f"Ocean dataset loaded: {len(df)} rows")


class OceanRequest(BaseModel):
    zone_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None


def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:

    lat1, lon1, lat2, lon2 = map(
        radians,
        [
            lat1,
            lon1,
            lat2,
            lon2
        ]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    return 6371.0088 * 2 * asin(
        sqrt(a)
    )


def value(row, *names):
    for name in names:
        if name in df.columns:
            x = row[name]
            if pd.notna(x):
                return float(x)
    return None


def normalize(x, low, high):
    if x is None:
        return None
    return float(np.clip((x - low) / (high - low), 0, 1))


def calculate_hsi(
    chlorophyll,
    sst,
    current
):
    components = []
    weights = []

    if chlorophyll is not None:
        chl_score = normalize(chlorophyll, 0.05, 0.50)
        
        components.append(chl_score)
        weights.append(0.40)

    else:
        chl_score = None

    if sst is not None:
        sst_score = float(
            np.clip(1 - abs(sst - 28.0) / 5.0, 0, 1)
        )

        components.append(sst_score)
        weights.append(0.30)

    else:
        sst_score = None


    if current is not None:
        current_score = float(
            np.clip(1 - abs(current - 0.5) / 0.5, 0, 1)
        )

        components.append(current_score)
        weights.append(0.30)

    else:
        current_score = None

    if not components:
        return None, {
            "chlorophyll_hsi": None,
            "sst_hsi": None,
            "current_hsi": None
        }

    weights = np.array(weights)
    weights = weights / weights.sum()

    fishing_score = float(
        np.sum(
            np.array(components) * weights
        )
    )

    return round(fishing_score, 4), {
        "chlorophyll_hsi":
            None
            if chl_score is None
            else round(chl_score, 4),

        "sst_hsi":
            None
            if sst_score is None
            else round(sst_score, 4),

        "current_hsi":
            None
            if current_score is None
            else round(current_score, 4)
    }


@app.get("/")
def home():
    return {
        "agent": "Ocean Agent",
        "status": "running",
        "rows": len(df)
    }


@app.post("/ocean/analyze")
def analyze_ocean(request: OceanRequest):

    latitude = request.latitude
    longitude = request.longitude
    zone_id = request.zone_id   

    # --------------------------------------------------
    # RESOLVE HISTORICAL/PFZ ROW
    # --------------------------------------------------
    row = None

    if zone_id:
        rows = df[
            df["zone_id"]
            .astype(str)
            .str.upper()
            == zone_id.upper()
        ]

        if not rows.empty:
            row = rows.iloc[0]

    # --------------------------------------------------
    # RESOLVE COORDINATES
    # --------------------------------------------------
    if latitude is None or longitude is None:
        if row is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Provide a valid zone_id or "
                    "latitude and longitude"
                )
            )

        latitude = float(row["latitude"])
        longitude = float(row["longitude"])

    # --------------------------------------------------
    # LIVE OCEAN DATA
    # --------------------------------------------------
    try:
        live = get_live_ocean(
            latitude,
            longitude
        )

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=(
                "Live ocean data unavailable: "
                f"{str(e)}"
            )
        )

    # --------------------------------------------------
    # NEAR-REAL-TIME CHLOROPHYLL
    # --------------------------------------------------
    try:
        chlorophyll_data = get_chlorophyll(
            latitude,
            longitude
        )

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=(
                "Chlorophyll data unavailable: "
                f"{str(e)}"
            )
        )

    chlorophyll = chlorophyll_data.get(
        "chlorophyll_mean"
    )

    # --------------------------------------------------
    # LIVE SST
    # --------------------------------------------------
    sst = live.get(
        "sst_c"
    )

    # --------------------------------------------------
    # LIVE OCEAN CURRENT
    # --------------------------------------------------
    current = live.get(
        "current_speed_ms"
    )

    # --------------------------------------------------
    # CALCULATE HSI
    # --------------------------------------------------
    fishing_score, hsi = calculate_hsi(
        chlorophyll=chlorophyll,
        sst=sst,
        current=current
    )

    # --------------------------------------------------
    # ACTUAL VESSEL → PFZ DISTANCE
    # --------------------------------------------------
    pfz_distance = None

    if (
        row is not None
        and request.latitude is not None
        and request.longitude is not None
    ):

        pfz_distance = haversine_km(
            float(request.latitude),
            float(request.longitude),
            float(row["latitude"]),
            float(row["longitude"])
        )

    # --------------------------------------------------
    # RESPONSE
    # --------------------------------------------------

    return {
        "agent": "Ocean Agent",
        "status": "success",
        "data_mode": "mixed",
        "timestamp": live.get("timestamp"),

        "data_sources": {
            "sst": "Open-Meteo",
            "ocean_current": "Open-Meteo",
            "wave": "Open-Meteo",
            "chlorophyll": chlorophyll_data.get("source")
        },

        "data_modes": {
            "sst": "live",
            "ocean_current": "live",
            "wave": "live",
            "chlorophyll": chlorophyll_data.get("data_mode")

        },

        "zone_id": zone_id,

        "location": {
            "latitude": latitude,
            "longitude": longitude
        },

        "fishing_score": fishing_score,
        "hsi_components": hsi,

        "evidence": {
            # ------------------------------------------
            # LIVE
            # -----------------------------------------
            "sst_c": live.get("sst_c"),
            "current_speed_ms": live.get("current_speed_ms"),
            "current_direction_deg": live.get("current_direction_deg"),
            "wave_height_m": live.get("wave_height_m"),
            "wave_period_s": live.get("wave_period_s"),
            "wave_direction_deg": live.get("wave_direction_deg"),

            # ------------------------------------------
            # CHLOROPHYLL
            # ------------------------------------------
            "chlorophyll_mean": chlorophyll,
            "chlorophyll_timestamp": chlorophyll_data.get("timestamp"),
            "chlorophyll_source": chlorophyll_data.get("source"),
            "chlorophyll_data_mode": chlorophyll_data.get("data_mode"),
            "pfz_distance_km": pfz_distance
        }
    }
    
# =========================================================
# CANONICAL PFZ ZONE ANALYSIS
# =========================================================
#
# This endpoint is used when ORCA needs to talk about a
# specific PFZ zone shown on the fishing-zone map.
#
# The fishing metrics MUST come from the same unified PFZ
# dataset used by /api/fishing-zones.
#
# Live wave conditions are included as supplementary data.
# They do NOT replace the canonical SST/chlorophyll/current
# values and do NOT change the fishing HSI.
# =========================================================

@app.post("/ocean/zone")
def analyze_canonical_zone(request: OceanRequest):
    zone_id = request.zone_id.strip() if request.zone_id else None

    row = None

    # -----------------------------------------------------
    # Resolve zone
    # -----------------------------------------------------
    if zone_id:
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

    elif request.latitude is not None and request.longitude is not None:
        distances = (
            (df["latitude"] - request.latitude) ** 2
            + (df["longitude"] - request.longitude) ** 2
        )

        idx = distances.idxmin()
        row = df.loc[idx]
        zone_id = str(row["zone_id"])

    else:
        raise HTTPException(
            status_code=400,
            detail="Provide zone_id or latitude and longitude"
        )

    # -----------------------------------------------------
    # CANONICAL PFZ VALUES
    # These are exactly the values used by the map.
    # -----------------------------------------------------
    sst = value(row, "sst_c")
    chlorophyll = value(row, "chlorophyll_mean")
    current = value(row, "current_speed_ms")
    pfz_distance = value(row, "pfz_distance_km", "distance_km")

    # -----------------------------------------------------
    # CANONICAL FISHING HSI
    # -----------------------------------------------------
    fishing_score, hsi = calculate_hsi(
        chlorophyll=chlorophyll,
        sst=sst,
        current=current
    )

    # -----------------------------------------------------
    # LIVE WAVE CONDITIONS
    #
    # These are supplementary only.
    # They do NOT affect fishing_score.
    # -----------------------------------------------------
    live = {}

    try:
        latitude = float(row["latitude"])
        longitude = float(row["longitude"])

        live = get_live_ocean(
            latitude,
            longitude
        )

    except Exception as exc:

        print(
            f"[Ocean Zone] Live wave data unavailable "
            f"for {zone_id}: {exc}"
        )

    return {
        "agent": "Ocean Agent",
        "status": "success",
        "mode": "canonical_zone",
        "data_mode": "canonical_pfz_plus_live_waves",
        "zone_id": str(row["zone_id"]),
        "location": {
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"])
        },

        # -------------------------------------------------
        # THIS IS THE AUTHORITATIVE FISHING SCORE
        # -------------------------------------------------

        "fishing_score": fishing_score,
        "hsi_components": hsi,

        "data_sources": {
            "sst": "ORCA unified PFZ ocean dataset",
            "chlorophyll": "ORCA unified PFZ ocean dataset",
            "ocean_current": "ORCA unified PFZ ocean dataset",
            "wave": "Open-Meteo"
        },

        "data_modes": {
            "sst": "canonical",
            "chlorophyll": "canonical",
            "ocean_current": "canonical",
            "wave": "live"
        },

        "evidence": {

            # ---------------------------------------------
            # CANONICAL MAP VALUES
            # ---------------------------------------------
            "sst_c": sst,
            "chlorophyll_mean": chlorophyll,
            "current_speed_ms": current,
            "pfz_distance_km": pfz_distance,

            # ---------------------------------------------
            # LIVE SUPPLEMENTARY WAVE VALUES
            # ---------------------------------------------
            "wave_height_m": live.get("wave_height_m"),
            "wave_period_s": live.get("wave_period_s"),
            "wave_direction_deg": live.get("wave_direction_deg"),

            # ---------------------------------------------
            # Metadata
            # ---------------------------------------------
            "canonical_source": "backend/data/ocean/unified_ocean_current.csv",
            "canonical_timestamp": None,
            "live_wave_timestamp": live.get("timestamp")
        }
    }