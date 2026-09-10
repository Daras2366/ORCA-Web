"""
vessel_schemas.py — Pydantic v2 request/response schemas for vessel CRUD.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator

from backend.auth.models import ALLOWED_VESSEL_TYPES, ALLOWED_ENGINE_TYPES

VesselTypeEnum = Literal[
    "small_fishing_boat",
    "gillnetter",
    "trawler",
    "longliner",
    "purse_seiner",
    "other",
]

EngineTypeEnum = Literal[
    "outboard",
    "inboard",
    "diesel",
    "petrol",
    "other",
]


class VesselCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    vessel_type: VesselTypeEnum = "other"
    length_m: Optional[float] = Field(None, gt=0, le=200)
    engine_type: Optional[EngineTypeEnum] = None
    engine_power_hp: Optional[float] = Field(None, gt=0, le=100000)
    cruising_speed_kmh: Optional[float] = Field(None, gt=0, le=200)
    fuel_capacity_l: Optional[float] = Field(None, gt=0, le=1000000)

    @field_validator("vessel_type")
    @classmethod
    def valid_vessel_type(cls, v: str) -> str:
        if v not in ALLOWED_VESSEL_TYPES:
            raise ValueError(
                f"vessel_type must be one of: {', '.join(ALLOWED_VESSEL_TYPES)}"
            )
        return v


class VesselUpdate(BaseModel):
    """All fields optional — only supplied fields are updated."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    vessel_type: Optional[VesselTypeEnum] = None
    length_m: Optional[float] = Field(None, gt=0, le=200)
    engine_type: Optional[EngineTypeEnum] = None
    engine_power_hp: Optional[float] = Field(None, gt=0, le=100000)
    cruising_speed_kmh: Optional[float] = Field(None, gt=0, le=200)
    fuel_capacity_l: Optional[float] = Field(None, gt=0, le=1000000)


class VesselOut(BaseModel):
    """Public vessel representation — safe to return in API responses."""
    id: str
    user_id: str
    name: str
    vessel_type: str
    length_m: Optional[float]
    engine_type: Optional[str]
    engine_power_hp: Optional[float]
    cruising_speed_kmh: Optional[float]
    fuel_capacity_l: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
