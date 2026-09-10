"""
models.py — SQLAlchemy ORM model for the users table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

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

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r} type={self.user_type!r}>"
