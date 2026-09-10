"""
vessel_router.py — Authenticated CRUD endpoints for vessels.

All endpoints require a valid Bearer JWT.
Ownership is enforced: users can only see/modify their own vessels.

Routes (prefix /vessels):
    GET    /vessels              — list current user's vessels
    POST   /vessels              — create a vessel for current user
    GET    /vessels/{vessel_id}  — get one vessel (ownership enforced)
    PUT    /vessels/{vessel_id}  — update a vessel (ownership enforced)
    DELETE /vessels/{vessel_id}  — delete a vessel (ownership enforced)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.database import get_db
from backend.auth.dependencies import get_current_user
from backend.auth.models import User, Vessel
from backend.auth.vessel_schemas import VesselCreate, VesselOut, VesselUpdate

router = APIRouter(prefix="/vessels", tags=["vessels"])


def _get_owned_vessel(vessel_id: str, user: User, db: Session) -> Vessel:
    """
    Fetch a vessel by ID and verify it belongs to the current user.
    Raises 404 for not found OR for ownership mismatch (avoids enumeration).
    """
    vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if vessel is None or vessel.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vessel not found.",
        )
    return vessel


@router.get(
    "",
    response_model=list[VesselOut],
    summary="List the current user's vessels",
)
def list_vessels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all vessels owned by the authenticated user."""
    return (
        db.query(Vessel)
        .filter(Vessel.user_id == current_user.id)
        .order_by(Vessel.created_at.asc())
        .all()
    )


@router.post(
    "",
    response_model=VesselOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new vessel",
)
def create_vessel(
    payload: VesselCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a vessel owned by the authenticated user."""
    vessel = Vessel(
        user_id=current_user.id,
        name=payload.name,
        vessel_type=payload.vessel_type,
        length_m=payload.length_m,
        engine_type=payload.engine_type,
        engine_power_hp=payload.engine_power_hp,
        cruising_speed_kmh=payload.cruising_speed_kmh,
        fuel_capacity_l=payload.fuel_capacity_l,
    )
    db.add(vessel)
    db.commit()
    db.refresh(vessel)
    return vessel


@router.get(
    "/{vessel_id}",
    response_model=VesselOut,
    summary="Get a single vessel",
)
def get_vessel(
    vessel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a vessel. Returns 404 if the vessel does not belong to the user."""
    return _get_owned_vessel(vessel_id, current_user, db)


@router.put(
    "/{vessel_id}",
    response_model=VesselOut,
    summary="Update a vessel",
)
def update_vessel(
    vessel_id: str,
    payload: VesselUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Partial update — only fields explicitly supplied are changed.
    Returns 404 if the vessel does not belong to the user.
    """
    vessel = _get_owned_vessel(vessel_id, current_user, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vessel, field, value)

    db.commit()
    db.refresh(vessel)
    return vessel


@router.delete(
    "/{vessel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a vessel",
)
def delete_vessel(
    vessel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete a vessel.
    Returns 404 if the vessel does not belong to the user.
    """
    vessel = _get_owned_vessel(vessel_id, current_user, db)
    db.delete(vessel)
    db.commit()
