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

    Memory-optimised layout
    -----------------------
    elevation_m, depth_safe, and depth_blocked are no longer stored
    as full 2-D arrays — they are not accessed by any downstream
    routing component (A*, cost, metrics, constraints).

    Retained arrays
    ---------------
    latitudes        float32  1-D   negligible
    longitudes       float32  1-D   negligible
    depth_m          float32  2-D   ~31 MB
    is_land          bool     2-D   ~7.8 MB
    is_water         bool     2-D   ~7.8 MB
    navigable        bool     2-D   ~7.8 MB

    Total resident: ~54 MB (was ~102 MB — 47 MB saved by removing unused arrays)
    """

    latitudes: np.ndarray
    longitudes: np.ndarray

    depth_m: np.ndarray

    is_land: np.ndarray
    is_water: np.ndarray

    navigable: np.ndarray

    # ---------------------------------------------------------------------------
    # elevation_m, depth_safe, depth_blocked removed:
    #   - elevation_m  is never read by A*, cost, constraints, or metrics
    #   - depth_safe   is never read by A*, cost, constraints, or metrics
    #   - depth_blocked is never read by A*, cost, constraints, or metrics
    # Removing them saves 31.31 + 7.83 + 7.83 = 46.97 MB resident + the same
    # again as transient .astype() copies during load_bathymetry().
    # ---------------------------------------------------------------------------


def load_bathymetry(
    filepath: str | Path,
) -> BathymetryData:
    """
    Load the processed ORCA bathymetry dataset.

    Memory strategy
    ---------------
    Variables are extracted one at a time and immediately assigned.
    ``np.asarray(..., dtype=T)`` is used instead of ``.astype(T)``
    to avoid allocating a duplicate array when the on-disk dtype
    already matches the target dtype (both float32/bool in this file).
    np.asarray returns the original array unchanged when the dtype and
    memory layout already match; .astype always creates a fresh copy.

    Only the arrays actually needed by downstream routing code are
    loaded.  elevation_m, depth_safe, and depth_blocked are skipped
    entirely, saving ~47 MB of resident RAM and eliminating the
    corresponding transient copies.
    """

    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(
            f"Bathymetry file not found: {filepath}"
        )

    ds = xr.open_dataset(filepath)

    try:
        # ------------------------------------------------------------------
        # Coordinates — validate
        # ------------------------------------------------------------------
        if "lat" not in ds.coords:
            raise ValueError(
                "Bathymetry dataset is missing 'lat' coordinate."
            )
        if "lon" not in ds.coords:
            raise ValueError(
                "Bathymetry dataset is missing 'lon' coordinate."
            )

        # ------------------------------------------------------------------
        # Variables — validate only the ones we actually need
        # ------------------------------------------------------------------
        required_variables = {"depth_m", "is_land", "is_water", "navigable"}
        missing_variables = required_variables - set(ds.data_vars)

        if missing_variables:
            raise ValueError(
                "Invalid bathymetry dataset — missing variables: "
                + ", ".join(sorted(missing_variables))
            )

        # ------------------------------------------------------------------
        # Coordinates (1-D, negligible size)
        # np.asarray avoids a copy when dtype already matches.
        # ------------------------------------------------------------------
        latitudes = np.asarray(ds["lat"].values, dtype=np.float32)
        longitudes = np.asarray(ds["lon"].values, dtype=np.float32)

        # ------------------------------------------------------------------
        # depth_m — float32, ~31 MB
        # Extracted alone so only one large array is a transient at a time.
        # np.asarray avoids duplicate allocation when already float32.
        # ------------------------------------------------------------------
        depth_m = np.asarray(
            ds["depth_m"].values,
            dtype=np.float32,
        )

        # ------------------------------------------------------------------
        # Boolean masks — ~7.8 MB each
        # Extracted sequentially so only one raw array lives at a time.
        # ------------------------------------------------------------------
        is_land = np.asarray(
            ds["is_land"].values,
            dtype=bool,
        )

        is_water = np.asarray(
            ds["is_water"].values,
            dtype=bool,
        )

        navigable = np.asarray(
            ds["navigable"].values,
            dtype=bool,
        )

    finally:
        # Close the dataset before constructing the dataclass so the
        # xarray/netCDF4 internal buffers are released immediately.
        ds.close()

    # Construct the dataclass now that the dataset is closed and all
    # raw xarray objects have been freed.
    return BathymetryData(
        latitudes=latitudes,
        longitudes=longitudes,
        depth_m=depth_m,
        is_land=is_land,
        is_water=is_water,
        navigable=navigable,
    )


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