from dataclasses import dataclass

import numpy as np

from .bathymetry import BathymetryData
from .vessel import VesselProfile


@dataclass
class ConstraintMask:
    """
    Hard navigation constraints for the ORCA routing grid.

    True  = cell is blocked
    False = cell may be considered by the router
    """

    blocked: np.ndarray

    @property
    def shape(self):
        return self.blocked.shape

    @property
    def blocked_cells(self) -> int:
        return int(self.blocked.sum())

    @property
    def navigable_cells(self) -> int:
        return int(
            self.blocked.size
            - self.blocked.sum()
        )

    def is_blocked(
        self,
        row: int,
        col: int,
    ) -> bool:
        return bool(
            self.blocked[row, col]
        )


def build_constraint_mask(
    bathymetry: BathymetryData,
    vessel: VesselProfile,
) -> ConstraintMask:
    """
    Build the hard navigation-block mask.

    A cell is blocked when:

        1. It is not part of the original navigable mask.
        2. It is land.
        3. It is not water.
        4. Its depth is below the vessel's minimum safe depth.

    This function intentionally does NOT treat MPA membership,
    current, wind, wave or fuel as hard blocks.
    """

    minimum_safe_depth = (
        vessel.minimum_safe_depth_m
    )

    unsafe_depth = (
        bathymetry.depth_m
        < minimum_safe_depth
    )

    blocked = (
        ~bathymetry.navigable
        | bathymetry.is_land
        | ~bathymetry.is_water
        | unsafe_depth
    )

    # The result of boolean arithmetic on bool arrays is already bool.
    # Using np.asarray avoids the extra 7.83 MB copy that
    # blocked.astype(bool) would produce needlessly.
    return ConstraintMask(
        blocked=np.asarray(blocked, dtype=bool)
    )


def apply_constraints_to_navigability(
    navigable: np.ndarray,
    constraints: ConstraintMask,
) -> np.ndarray:
    """
    Apply a hard-block mask to an existing navigability mask.

    Returns a new boolean array where:

        True  = navigable
        False = blocked
    """

    navigable = np.asarray(
        navigable,
        dtype=bool,
    )

    if navigable.shape != constraints.shape:
        raise ValueError(
            "Navigability mask and constraint mask "
            "must have identical shapes."
        )

    return (
        navigable
        & ~constraints.blocked
    )


def add_confirmed_restrictions(
    constraints: ConstraintMask,
    prohibited_mask: np.ndarray | None = None,
    restricted_mask: np.ndarray | None = None,
) -> ConstraintMask:
    """
    Add confirmed navigation restrictions.

    These masks represent only confirmed restrictions.

    MPA membership alone should NOT be passed here unless
    it corresponds to an actual confirmed navigation
    restriction.
    """

    blocked = constraints.blocked.copy()

    if prohibited_mask is not None:

        prohibited_mask = np.asarray(
            prohibited_mask,
            dtype=bool,
        )

        if prohibited_mask.shape != blocked.shape:
            raise ValueError(
                "Prohibited-area mask shape does not "
                "match routing grid."
            )

        blocked |= prohibited_mask

    if restricted_mask is not None:

        restricted_mask = np.asarray(
            restricted_mask,
            dtype=bool,
        )

        if restricted_mask.shape != blocked.shape:
            raise ValueError(
                "Restricted-area mask shape does not "
                "match routing grid."
            )

        blocked |= restricted_mask

    return ConstraintMask(
        blocked=blocked
    )


def validate_constraint_mask(
    constraints: ConstraintMask,
) -> None:
    """
    Basic integrity checks for the hard constraint mask.
    """

    if constraints.blocked.ndim != 2:
        raise ValueError(
            "Constraint mask must be 2-dimensional."
        )

    if constraints.blocked.dtype != bool:
        raise ValueError(
            "Constraint mask must contain boolean values."
        )

    if constraints.blocked.size == 0:
        raise ValueError(
            "Constraint mask is empty."
        )