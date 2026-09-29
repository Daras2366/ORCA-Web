from dataclasses import dataclass
from pathlib import Path

import numpy as np
import xarray as xr

from .vessel import VesselProfile


@dataclass
class BathymetryData:
    """
    Static bathymetry information used by the ORCA
    navigation engine.
    """

    latitudes: np.ndarray
    longitudes: np.ndarray

    elevation_m: np.ndarray
    depth_m: np.ndarray

    is_land: np.ndarray
    is_water: np.ndarray

    depth_safe: np.ndarray
    depth_blocked: np.ndarray

    navigable: np.ndarray


def load_bathymetry(
    filepath: str | Path,
) -> BathymetryData:
    """
    Load the processed ORCA bathymetry dataset.

    Expected variables:

        elevation_m
        depth_m
        is_land
        is_water
        depth_safe
        depth_blocked
        navigable
    """

    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(
            f"Bathymetry file not found: {filepath}"
        )

    ds = xr.open_dataset(filepath)

    required_coordinates = {
        "lat",
        "lon",
    }

    required_variables = {
        "elevation_m",
        "depth_m",
        "is_land",
        "is_water",
        "depth_safe",
        "depth_blocked",
        "navigable",
    }

    missing_coordinates = (
        required_coordinates
        - set(ds.coords)
    )

    missing_variables = (
        required_variables
        - set(ds.data_vars)
    )

    if missing_coordinates or missing_variables:
        ds.close()

        problems = []

        if missing_coordinates:
            problems.append(
                "missing coordinates: "
                + ", ".join(
                    sorted(missing_coordinates)
                )
            )

        if missing_variables:
            problems.append(
                "missing variables: "
                + ", ".join(
                    sorted(missing_variables)
                )
            )

        raise ValueError(
            "Invalid bathymetry dataset — "
            + "; ".join(problems)
        )

    data = BathymetryData(
        latitudes=ds["lat"].values.astype(np.float32),

        longitudes=ds["lon"].values.astype(np.float32),

        elevation_m=(
            ds["elevation_m"]
            .values
            .astype(np.float32)
        ),

        depth_m=(
            ds["depth_m"]
            .values
            .astype(np.float32)
        ),

        is_land=(
            ds["is_land"]
            .values
            .astype(bool)
        ),

        is_water=(
            ds["is_water"]
            .values
            .astype(bool)
        ),

        depth_safe=(
            ds["depth_safe"]
            .values
            .astype(bool)
        ),

        depth_blocked=(
            ds["depth_blocked"]
            .values
            .astype(bool)
        ),

        navigable=(
            ds["navigable"]
            .values
            .astype(bool)
        ),
    )

    ds.close()

    return data


def apply_vessel_depth_constraint(
    bathymetry: BathymetryData,
    vessel: VesselProfile,
) -> np.ndarray:
    """
    Determine which cells are safe for a particular vessel.

    A cell is depth-safe when:

        depth >= vessel minimum safe depth

    Land and existing non-navigable cells remain blocked.
    """

    minimum_depth = vessel.minimum_safe_depth_m

    vessel_depth_safe = (
        bathymetry.depth_m
        >= minimum_depth
    )

    return (
        bathymetry.navigable
        & bathymetry.is_water
        & vessel_depth_safe
    )


def bathymetry_summary(
    bathymetry: BathymetryData,
) -> dict:
    """
    Return useful summary information about
    the bathymetry dataset.
    """

    return {
        "rows": int(
            len(bathymetry.latitudes)
        ),

        "columns": int(
            len(bathymetry.longitudes)
        ),

        "total_cells": int(
            bathymetry.navigable.size
        ),

        "navigable_cells": int(
            bathymetry.navigable.sum()
        ),

        "land_cells": int(
            bathymetry.is_land.sum()
        ),

        "water_cells": int(
            bathymetry.is_water.sum()
        ),

        "depth_blocked_cells": int(
            bathymetry.depth_blocked.sum()
        ),

        "latitude_min": float(
            bathymetry.latitudes.min()
        ),

        "latitude_max": float(
            bathymetry.latitudes.max()
        ),

        "longitude_min": float(
            bathymetry.longitudes.min()
        ),

        "longitude_max": float(
            bathymetry.longitudes.max()
        ),

        "minimum_depth_m": float(
            np.nanmin(bathymetry.depth_m)
        ),

        "maximum_depth_m": float(
            np.nanmax(bathymetry.depth_m)
        ),
    }