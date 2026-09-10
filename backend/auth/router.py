"""
router.py — Auth API endpoints.

POST /auth/register  — create account, return JWT + user
POST /auth/login     — verify credentials, return JWT + user
GET  /auth/me        — return current authenticated user (requires JWT)
POST /auth/logout    — client-side logout (returns 200 OK)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.database import get_db
from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.auth.schemas import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from backend.auth.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Create a new user account.

    - Validates all fields (including password confirmation).
    - Hashes the password with bcrypt before storing.
    - Returns a JWT access token and the new user's public profile.
    - Returns HTTP 409 if the email is already registered.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        user_type=payload.user_type,
        preferred_language=payload.preferred_language,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate an existing user.

    - Returns HTTP 401 for unknown email or wrong password.
      (A generic message is returned to avoid email enumeration.)
    """
    user = db.query(User).filter(User.email == payload.email).first()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get the current authenticated user",
)
def me(current_user: User = Depends(get_current_user)):
    """
    Return the authenticated user's profile.

    Requires a valid Bearer token in the Authorization header.
    """
    return UserOut.model_validate(current_user)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (client-side token invalidation)",
)
def logout():
    """
    Logout endpoint.

    JWT tokens are stateless — the token is invalidated on the client side
    by deleting it from localStorage. This endpoint exists so the frontend
    can call a consistent /auth/logout URL and receive a clean 200 response.
    """
    return MessageResponse(message="Logged out successfully.")
