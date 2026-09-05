
"""
ORCA Routing Agent API - M3_v2
route_api.py

Run from project root:
    python -m uvicorn backend.api.route_api:app --reload --port 8004

Endpoints:
    GET  /                 health / info
    POST /route/analyze    analyse a fishing zone
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import sys
import os

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so the package import below works
# whether the server is started from the root or from inside backend/.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Import the M3_v2 scoring engine
from backend.agents.routing_agent.predict import predict_route  # noqa: E402

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ORCA Routing Agent API",
    description="M3_v2 deterministic route scoring engine for ORCA",
    version="2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Dataset - loaded once at startup using a project-relative path.
# _BASE_DIR resolves to the backend/ directory regardless of launch location.
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_PATH = os.path.join(
    _BASE_DIR, "data", "routing", "M3_final_routing_dataset.csv"
)

_df = pd.read_csv(_DATA_PATH)
_df.columns = _df.columns.str.strip()

print(f"[route_api] Dataset loaded: {len(_df)} rows from {_DATA_PATH}")

# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------


class RouteRequest(BaseModel):
    zone_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
def home():
    """Health check / info endpoint."""
    return {
        "agent": "Routing Agent",
        "status": "running",
        "version": "M3_v2",
        "dataset": "M3_final_routing_dataset.csv",
        "rows": len(_df),
    }


@app.post("/route/analyze")
def analyze_route(request: RouteRequest):
    """
    Analyse a fishing zone and return M3_v2 route scores.

    Request body example: {"zone_id": "PFZ0001"}

    Returns JSON with route_score, route_metrics, evidence, dataset_scores.
    Raises HTTP 404 if the zone_id is not found.
    """
    zone_id = request.zone_id.strip()

    # Case-insensitive lookup
    mask = _df["zone_id"].astype(str).str.upper() == zone_id.upper()
    rows = _df[mask]

    if rows.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zone_id}' not found in routing dataset.",
        )

    row = rows.iloc[0].to_dict()

    # Delegate all scoring to the M3_v2 predict engine
    return predict_route(row)
