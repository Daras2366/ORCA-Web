from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os

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
    # PFZ DISTANCE
    # --------------------------------------------------
    pfz_distance = None

    if row is not None:
        pfz_distance = value(
            row,
            "pfz_distance_km",
            "distance_km"
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