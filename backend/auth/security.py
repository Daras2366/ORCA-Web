"""
security.py — Password hashing and JWT utilities.

Environment variables (required):
    JWT_SECRET              — strong random secret
    JWT_ALGORITHM           — default: HS256
    JWT_EXPIRATION_MINUTES  — default: 1440 (24 h)

Dependency note:
    Uses the `bcrypt` package directly (not via passlib).
    passlib has not been maintained since 2020 and its bcrypt backend
    is incompatible with bcrypt >= 4.0, causing ValueError on hashing.
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JWT_SECRET: str = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "1440"))

if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET environment variable is not set. "
        "Add a strong random value to your .env file."
    )

# ---------------------------------------------------------------------------
# Password hashing — direct bcrypt (no passlib wrapper)
# ---------------------------------------------------------------------------

_BCRYPT_ROUNDS = 12  # industry-standard work factor


def hash_password(plain: str) -> str:
    """
    Return a bcrypt hash of the plaintext password.

    bcrypt.hashpw expects bytes; we encode the plain-text string to UTF-8.
    The resulting hash is stored as a UTF-8 string in the database.
    """
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    hashed_bytes = bcrypt.hashpw(plain.encode("utf-8"), salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Return True if the plaintext matches the bcrypt hash.

    Both arguments are decoded/encoded at the boundary so bcrypt always
    receives bytes, which is what the library requires.
    """
    return bcrypt.checkpw(
        plain.encode("utf-8"),
        hashed.encode("utf-8"),
    )


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_access_token(user_id: str) -> str:
    """Create a signed JWT that encodes the user's ID as the subject."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """
    Decode a JWT and return the subject (user ID).

    Raises jose.JWTError on invalid / expired tokens.
    """
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    sub: str | None = payload.get("sub")
    if sub is None:
        raise JWTError("Token payload is missing 'sub' claim.")
    return sub
