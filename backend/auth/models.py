"""
models.py — SQLAlchemy ORM models for users and vessels.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.auth.database import Base

# Allowed user types — enforced at the application layer via Pydantic.
ALLOWED_USER_TYPES = [
    "fisherman",
    "coast_guard",
    "researcher",
    "maritime_operator",
    "coastal_authority",
    "other",
]

ALLOWED_VESSEL_TYPES = [
    "small_fishing_boat",
    "gillnetter",
    "trawler",
    "longliner",
    "purse_seiner",
    "other",
]

ALLOWED_ENGINE_TYPES = [
    "outboard",
    "inboard",
    "diesel",
    "petrol",
    "other",
]


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Never store plaintext — always bcrypt-hashed.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    user_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="other",
    )

    preferred_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="en",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship — cascade deletes vessels when user is deleted.
    vessels: Mapped[List["Vessel"]] = relationship(
        "Vessel",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r} type={self.user_type!r}>"


class Vessel(Base):
    __tablename__ = "vessels"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    vessel_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="other",
    )

    length_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    engine_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )

    engine_power_hp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    cruising_speed_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    fuel_capacity_l: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship back to owner.
    owner: Mapped["User"] = relationship("User", back_populates="vessels")

    def __repr__(self) -> str:
        return f"<Vessel id={self.id!r} name={self.name!r} user_id={self.user_id!r}>"
