from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os

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
    zone_id: str


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


def calculate_hsi(row):
    chl = value(row, "chlorophyll_mean", "chlorophyll")
    sst = value(row, "sst_c", "sst", "sea_surface_temperature")
    current = value(row, "current_speed_ms", "current_speed")

    components = []
    weights = []

    # Chlorophyll HSI
    if chl is not None:
        chl_score = normalize(chl, 0.05, 0.50)
        components.append(chl_score)
        weights.append(0.40)
    else:
        chl_score = None

    # SST HSI
    if sst is not None:
        sst_score = float(
            np.clip(
                1 - abs(sst - 28.0) / 5.0,
                0,
                1
            )
        )
        components.append(sst_score)
        weights.append(0.30)
    else:
        sst_score = None

    # Current HSI
    if current is not None:
        current_score = float(
            np.clip(
                1 - abs(current - 0.5) / 0.5,
                0,
                1
            )
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

    fishing_score = float(np.sum(np.array(components) * weights))

    return round(fishing_score, 4), {
        "chlorophyll_hsi": None if chl_score is None else round(chl_score, 4),
        "sst_hsi": None if sst_score is None else round(sst_score, 4),
        "current_hsi": None if current_score is None else round(current_score, 4)
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

    zone_id = request.zone_id.strip()

    rows = df[
        df["zone_id"].astype(str).str.upper() == zone_id.upper()
    ]

    if rows.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Zone {zone_id} not found"
        )

    row = rows.iloc[0]

    fishing_score, hsi = calculate_hsi(row)

    return {
        "agent": "Ocean Agent",
        "status": "success",
        "zone_id": str(row["zone_id"]),

        "location": {
            "latitude": value(row, "latitude"),
            "longitude": value(row, "longitude")
        },

        "fishing_score": fishing_score,

        "hsi_components": hsi,

        "evidence": {
            "sst_c": value(row, "sst_c", "sst"),
            "chlorophyll_mean": value(
                row,
                "chlorophyll_mean",
                "chlorophyll"
            ),
            "current_speed_ms": value(
                row,
                "current_speed_ms",
                "current_speed"
            ),
            "pfz_distance_km": value(
                row,
                "pfz_distance_km",
                "distance_km"
            )
        }
    }
