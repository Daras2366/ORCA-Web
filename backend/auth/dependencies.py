"""
dependencies.py — FastAPI dependency injection for authentication.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from backend.auth.database import get_db
from backend.auth.models import User
from backend.auth.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Require a valid Bearer JWT.
    Raises HTTP 401 if the token is missing, expired, or invalid.
    The user ID is read from the token — never trusted from the request body.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Return the authenticated user if a valid token is supplied,
    otherwise return None (guest mode).
    """
    if credentials is None:
        return None
    try:
        user_id = decode_access_token(credentials.credentials)
        return db.query(User).filter(User.id == user_id).first()
    except JWTError:
        return None
