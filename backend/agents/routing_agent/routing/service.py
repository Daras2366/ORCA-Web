"""
ORCA Marine Routing Service
============================

Production entry point for deterministic marine route calculation.

Usage::

    from backend.agents.routing_agent.routing.service import run_route

    result = run_route(
        start_latitude=10.5,
        start_longitude=76.0,
        destination_latitude=12.0,
        destination_longitude=77.5,
    )

The returned dict is fully JSON-serialisable (no NumPy, xarray, or
NetCDF objects).  All float values are plain Python floats.

Data files are resolved relative to the project root so the service
works correctly regardless of the working directory the caller uses.
"""

from __future__ import annotations

import math
import traceback
from pathlib import Path
from typing import Any

from .bathymetry import load_bathymetry
from .environment import load_currents
from .grid import MarineGrid
from .constraints import build_constraint_mask
from .vessel import VesselProfile
from .cost import CostWeights
from .astar import astar_search
from .metrics import calculate_route_metrics, path_to_geojson


# ---------------------------------------------------------------------------
# Data file resolution
# ---------------------------------------------------------------------------

# Resolve paths relative to the project root (four levels up from this file:
#   routing/service.py
#   routing/
#   routing_agent/
#   agents/
#   backend/
#   project_root/
# )
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[4]

_BATHYMETRY_FILE = (
    _PROJECT_ROOT
    / "backend"
    / "data"
    / "routing"
    / "grid"
    / "orca_west_coast_bathymetry_landmasked.nc"
)

_CURRENT_FILE = (
    _PROJECT_ROOT
    / "backend"
    / "data"
    / "routing"
    / "environmental"
    / "orca_west_coast_currents_departure.nc"
)


# ---------------------------------------------------------------------------
# Coordinate validation helpers
# ---------------------------------------------------------------------------

_VALID_LATITUDE_RANGE = (-90.0, 90.0)
_VALID_LONGITUDE_RANGE = (-180.0, 180.0)


def _validate_coordinates(
    latitude: float,
    longitude: float,
    label: str,
) -> str | None:
    """
    Return an error message string if the coordinates are invalid,
    or None if they are acceptable.
    """

    if not math.isfinite(latitude) or not math.isfinite(longitude):
        return (
            f"{label} coordinates contain non-finite values: "
            f"lat={latitude}, lon={longitude}"
        )

    lat_min, lat_max = _VALID_LATITUDE_RANGE
    lon_min, lon_max = _VALID_LONGITUDE_RANGE

    if not (lat_min <= latitude <= lat_max):
        return (
            f"{label} latitude {latitude} is outside the valid range "
            f"[{lat_min}, {lat_max}]."
        )

    if not (lon_min <= longitude <= lon_max):
        return (
            f"{label} longitude {longitude} is outside the valid range "
            f"[{lon_min}, {lon_max}]."
        )

    return None


def _coords_within_grid(
    latitude: float,
    longitude: float,
    grid: MarineGrid,
) -> bool:
    """
    Return True if the latitude/longitude fall within the grid extent.
    A small tolerance of one grid-cell width is allowed on each edge.
    """

    lat_min = float(grid.latitudes.min())
    lat_max = float(grid.latitudes.max())
    lon_min = float(grid.longitudes.min())
    lon_max = float(grid.longitudes.max())

    # One-cell tolerance in each direction.
    lat_step = float(grid.latitudes[1] - grid.latitudes[0]) if grid.n_rows > 1 else 0.0
    lon_step = float(grid.longitudes[1] - grid.longitudes[0]) if grid.n_cols > 1 else 0.0
    tol_lat = abs(lat_step)
    tol_lon = abs(lon_step)

    return (
        (lat_min - tol_lat) <= latitude <= (lat_max + tol_lat)
        and (lon_min - tol_lon) <= longitude <= (lon_max + tol_lon)
    )


# ---------------------------------------------------------------------------
# Safe float conversion
# ---------------------------------------------------------------------------

def _safe_float(value: Any) -> float | None:
    """
    Convert a value to a plain Python float, returning None if the
    value is None, NaN, or non-finite.
    """

    if value is None:
        return None

    try:
        f = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(f):
        return None

    return f


def _safe_float_or_none(value: Any) -> float | None:
    """
    Like _safe_float but preserves None explicitly (used for optional
    metrics like average_current_ms that are legitimately absent when
    no current data exists).
    """

    if value is None:
        return None

    return _safe_float(value)


# ---------------------------------------------------------------------------
# Public service entry point
# ---------------------------------------------------------------------------

def run_route(
    start_latitude: float,
    start_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
    vessel: VesselProfile | None = None,
    weights: CostWeights | None = None,
    bathymetry_file: str | Path | None = None,
    current_file: str | Path | None = None,
    cache: Any = None,
) -> dict[str, Any]:
    """
    Calculate a marine navigation route from start to destination.

    Parameters
    ----------
    start_latitude:
        Latitude of the departure point (decimal degrees, WGS-84).
    start_longitude:
        Longitude of the departure point (decimal degrees, WGS-84).
    destination_latitude:
        Latitude of the destination (decimal degrees, WGS-84).
    destination_longitude:
        Longitude of the destination (decimal degrees, WGS-84).
    vessel:
        Optional VesselProfile.  Defaults to the demo coastal vessel.
    weights:
        Optional CostWeights.  Defaults to the standard routing weights.
    bathymetry_file:
        Override path to the bathymetry NetCDF file.
    current_file:
        Override path to the currents NetCDF file.
    cache:
        Optional RoutingCache object. If provided, uses cached data
        instead of loading NetCDF files. If cache is provided,
        bathymetry_file and current_file parameters are ignored.

    Returns
    -------
    dict
        A fully JSON-serialisable result dict.  Keys:

        success           bool
        message           str
        start             {latitude, longitude}
        destination       {latitude, longitude}
        snapped_start     {latitude, longitude}
        snapped_destination {latitude, longitude}
        metrics           {distance_km, travel_time_h, fuel_l,
                           min_depth_m, max_depth_m, average_depth_m,
                           average_current_ms, total_cost}
        geojson           {type: "LineString", coordinates: [...]}

    On failure, success=False and the other keys are omitted or set
    to None, with message describing the reason.
    """

    # ------------------------------------------------------------------
    # Step 1 — Input validation
    # ------------------------------------------------------------------

    error = _validate_coordinates(
        start_latitude,
        start_longitude,
        "Start",
    )
    if error:
        return _failure(error)

    error = _validate_coordinates(
        destination_latitude,
        destination_longitude,
        "Destination",
    )
    if error:
        return _failure(error)

    # ------------------------------------------------------------------
    # Step 2 — Load routing data (use cache if provided)
    # ------------------------------------------------------------------

    if cache is not None:
        # Use cached data
        try:
            bathymetry = cache.bathymetry
            currents = cache.currents
            grid = cache.grid
            
            # Use cached vessel if not overridden
            if vessel is None:
                vessel = cache.vessel
                constraints = cache.constraints
            else:
                # Rebuild constraints for custom vessel
                try:
                    constraints = build_constraint_mask(bathymetry, vessel)
                except Exception as exc:
                    return _failure(
                        f"Failed to build navigation constraints: {exc}",
                        exc=exc,
                    )
            
            if weights is None:
                weights = CostWeights()
                
        except AttributeError as exc:
            return _failure(
                f"Invalid cache object: {exc}",
                exc=exc,
            )
    else:
        # Load from files (legacy behavior)
        bathy_path = Path(bathymetry_file) if bathymetry_file else _BATHYMETRY_FILE
        curr_path = Path(current_file) if current_file else _CURRENT_FILE

        if not bathy_path.exists():
            return _failure(
                f"Bathymetry file not found: {bathy_path}"
            )

        if not curr_path.exists():
            return _failure(
                f"Current dataset not found: {curr_path}"
            )

        try:
            bathymetry = load_bathymetry(bathy_path)
        except Exception as exc:
            return _failure(
                f"Failed to load bathymetry data: {exc}",
                exc=exc,
            )

        try:
            currents = load_currents(curr_path)
        except Exception as exc:
            return _failure(
                f"Failed to load current data: {exc}",
                exc=exc,
            )

        try:
            grid = MarineGrid(
                latitudes=bathymetry.latitudes,
                longitudes=bathymetry.longitudes,
                navigable=bathymetry.navigable,
                depth_m=bathymetry.depth_m,
            )
        except Exception as exc:
            return _failure(
                f"Failed to construct routing grid: {exc}",
                exc=exc,
            )

        if vessel is None:
            vessel = VesselProfile()

        if weights is None:
            weights = CostWeights()

        try:
            constraints = build_constraint_mask(bathymetry, vessel)
        except Exception as exc:
            return _failure(
                f"Failed to build navigation constraints: {exc}",
                exc=exc,
            )

    # ------------------------------------------------------------------
    # Step 4 — Validate coordinates against grid extent
    # ------------------------------------------------------------------

    if not _coords_within_grid(start_latitude, start_longitude, grid):
        return _failure(
            f"Start coordinates ({start_latitude}, {start_longitude}) "
            f"are outside the supported grid area."
        )

    if not _coords_within_grid(destination_latitude, destination_longitude, grid):
        return _failure(
            f"Destination coordinates "
            f"({destination_latitude}, {destination_longitude}) "
            f"are outside the supported grid area."
        )

    # ------------------------------------------------------------------
    # Step 5 — Snap to nearest navigable grid nodes
    # ------------------------------------------------------------------

    try:
        start_node = grid.nearest_node(
            start_latitude,
            start_longitude,
            navigable_only=True,
        )
    except ValueError as exc:
        return _failure(
            f"Could not snap start to a navigable cell: {exc}"
        )

    try:
        goal_node = grid.nearest_node(
            destination_latitude,
            destination_longitude,
            navigable_only=True,
        )
    except ValueError as exc:
        return _failure(
            f"Could not snap destination to a navigable cell: {exc}"
        )

    # Verify snapped nodes pass the constraint mask.
    start_row, start_col = grid.row_col(start_node)
    goal_row, goal_col = grid.row_col(goal_node)

    if constraints.is_blocked(start_row, start_col):
        return _failure(
            "Start location snapped to a blocked cell. "
            "The area may be land or too shallow for this vessel."
        )

    if constraints.is_blocked(goal_row, goal_col):
        return _failure(
            "Destination location snapped to a blocked cell. "
            "The area may be land or too shallow for this vessel."
        )

    # Capture snapped coordinates as plain Python floats.
    snapped_start_lat, snapped_start_lon = grid.node_to_latlon(start_node)
    snapped_goal_lat, snapped_goal_lon = grid.node_to_latlon(goal_node)

    # ------------------------------------------------------------------
    # Step 6 — Run A*
    # ------------------------------------------------------------------

    try:
        astar_result = astar_search(
            grid=grid,
            constraints=constraints,
            start_node=start_node,
            goal_node=goal_node,
            bathymetry=bathymetry,
            currents=currents,
            vessel=vessel,
            weights=weights,
        )
    except Exception as exc:
        return _failure(
            f"A* search raised an unexpected error: {exc}",
            exc=exc,
        )

    if not astar_result.success:
        return _failure(
            f"No route found: {astar_result.message}",
            start_latitude=start_latitude,
            start_longitude=start_longitude,
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
            snapped_start_lat=snapped_start_lat,
            snapped_start_lon=snapped_start_lon,
            snapped_goal_lat=snapped_goal_lat,
            snapped_goal_lon=snapped_goal_lon,
        )

    path = astar_result.path

    # ------------------------------------------------------------------
    # Step 7 — Calculate route metrics
    # ------------------------------------------------------------------

    try:
        raw_metrics = calculate_route_metrics(
            path=path,
            grid=grid,
            bathymetry=bathymetry,
            currents=currents,
            constraints=constraints,
            vessel=vessel,
            weights=weights,
        )
    except Exception as exc:
        return _failure(
            f"Failed to calculate route metrics: {exc}",
            exc=exc,
        )

    # ------------------------------------------------------------------
    # Step 8 — Convert path to GeoJSON
    # ------------------------------------------------------------------

    try:
        geojson = path_to_geojson(path=path, grid=grid)
    except Exception as exc:
        return _failure(
            f"Failed to generate GeoJSON: {exc}",
            exc=exc,
        )

    # ------------------------------------------------------------------
    # Step 9 — Assemble clean, serialisable result
    # ------------------------------------------------------------------

    # All numeric values are cast to plain Python floats so that the
    # result can be passed directly to json.dumps or FastAPI response
    # serialisation without any NumPy-specific handling.

    metrics_out: dict[str, Any] = {
        "distance_km": _safe_float(raw_metrics.get("distance_km")),
        "travel_time_h": _safe_float(raw_metrics.get("travel_time_h")),
        "fuel_l": _safe_float(raw_metrics.get("fuel_l")),
        "min_depth_m": _safe_float(raw_metrics.get("min_depth_m")),
        "max_depth_m": _safe_float(raw_metrics.get("max_depth_m")),
        "average_depth_m": _safe_float(raw_metrics.get("average_depth_m")),
        "average_current_ms": _safe_float_or_none(
            raw_metrics.get("average_current_ms")
        ),
        "total_cost": _safe_float(raw_metrics.get("total_cost")),
    }

    # GeoJSON coordinates are already plain Python lists of [float, float]
    # produced by path_to_geojson; no further conversion needed.
    geojson_out: dict[str, Any] = {
        "type": geojson["type"],
        "coordinates": geojson["coordinates"],
    }

    return {
        "success": True,
        "message": "Route calculated successfully.",
        "start": {
            "latitude": float(start_latitude),
            "longitude": float(start_longitude),
        },
        "destination": {
            "latitude": float(destination_latitude),
            "longitude": float(destination_longitude),
        },
        "snapped_start": {
            "latitude": float(snapped_start_lat),
            "longitude": float(snapped_start_lon),
        },
        "snapped_destination": {
            "latitude": float(snapped_goal_lat),
            "longitude": float(snapped_goal_lon),
        },
        "metrics": metrics_out,
        "geojson": geojson_out,
    }


# ---------------------------------------------------------------------------
# Internal helper — build a failure result
# ---------------------------------------------------------------------------

def _failure(
    message: str,
    exc: Exception | None = None,
    start_latitude: float | None = None,
    start_longitude: float | None = None,
    destination_latitude: float | None = None,
    destination_longitude: float | None = None,
    snapped_start_lat: float | None = None,
    snapped_start_lon: float | None = None,
    snapped_goal_lat: float | None = None,
    snapped_goal_lon: float | None = None,
) -> dict[str, Any]:
    """
    Build a standardised failure response.

    The exception traceback is printed for diagnostics but is NOT
    included in the returned dict (it would be non-serialisable and
    could expose internal paths to clients).
    """

    if exc is not None:
        traceback.print_exc()

    result: dict[str, Any] = {
        "success": False,
        "message": message,
    }

    if start_latitude is not None:
        result["start"] = {
            "latitude": float(start_latitude),
            "longitude": float(start_longitude),  # type: ignore[arg-type]
        }

    if destination_latitude is not None:
        result["destination"] = {
            "latitude": float(destination_latitude),
            "longitude": float(destination_longitude),  # type: ignore[arg-type]
        }

    if snapped_start_lat is not None:
        result["snapped_start"] = {
            "latitude": float(snapped_start_lat),
            "longitude": float(snapped_start_lon),  # type: ignore[arg-type]
        }

    if snapped_goal_lat is not None:
        result["snapped_destination"] = {
            "latitude": float(snapped_goal_lat),
            "longitude": float(snapped_goal_lon),  # type: ignore[arg-type]
        }

    return result
