"""
main.py — ORCA Auth API (port 8005).

Run from project root:
    python -m uvicorn backend.auth.main:app --reload --port 8005

IMPORTANT: backend.auth._env must be the very first import so that
python-dotenv populates os.environ before security.py and database.py
read JWT_SECRET / DATABASE_URL at module-import time.
"""

# --- Load .env FIRST — do not move this import below any other auth import ---
import backend.auth._env  # noqa: F401

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth.router import router
from backend.auth.vessel_router import router as vessel_router

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")

app = FastAPI(
    title="ORCA Auth API",
    description="PostgreSQL-backed JWT authentication for ORCA",
    version="1.0.0",
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

app.include_router(router)
app.include_router(vessel_router)


@app.get("/", tags=["health"])
def health():
    return {
        "service": "ORCA Auth API",
        "status": "running",
        "version": "1.0.0",
    }
