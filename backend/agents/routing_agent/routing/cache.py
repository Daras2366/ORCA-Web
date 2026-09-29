"""
ORCA Routing Cache
==================

Startup cache for routing data to avoid reloading large NetCDF files
on every request.

The cache loads once at application startup and provides:
- Bathymetry data
- Current data  
- MarineGrid
- Default vessel profile
- Constraint mask

Usage::

    from backend.agents.routing_agent.routing.cache import (
        initialize_routing_cache,
        get_routing_cache
    )

    # Call during FastAPI startup
    initialize_routing_cache()

    # Use in endpoint handlers
    cache = get_routing_cache()
    if cache is None:
        raise HTTPException(status_code=503, detail="Routing data not initialized")

    # Access cached components
    bathymetry = cache.bathymetry
    grid = cache.grid
    # etc.
"""

from __future__ import annotations

import gc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .bathymetry import load_bathymetry, BathymetryData
from .environment import load_currents, CurrentData, validate_alignment
from .grid import MarineGrid
from .constraints import build_constraint_mask, ConstraintMask
from .vessel import VesselProfile


# ---------------------------------------------------------------------------
# Cache dataclass
# ---------------------------------------------------------------------------

@dataclass
class RoutingCache:
    """
    Cached routing data loaded once at startup.
    
    All components are initialized from the same bathymetry and current
    datasets to ensure spatial alignment.
    """
    
    bathymetry: BathymetryData
    currents: CurrentData
    grid: MarineGrid
    vessel: VesselProfile
    constraints: ConstraintMask
    
    def validate(self) -> None:
        """
        Verify that all cached components are properly aligned.
        """
        # Validate spatial alignment between bathymetry and currents
        validate_alignment(
            self.bathymetry.latitudes,
            self.bathymetry.longitudes,
            self.currents
        )
        
        # Validate constraint mask
        if self.constraints.shape != self.bathymetry.navigable.shape:
            raise ValueError(
                "Constraint mask shape does not match bathymetry navigable mask"
            )


# ---------------------------------------------------------------------------
# Module-level cache storage
# ---------------------------------------------------------------------------

_routing_cache: RoutingCache | None = None
_cache_initialized: bool = False
_cache_error: str | None = None


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

# Resolve paths relative to the project root (four levels up from this file:
#   routing/cache.py
#   routing/
#   routing_agent/
#   agents/
#   backend/
#   project_root/
# )
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[4]

_DEFAULT_BATHYMETRY_FILE = (
    _PROJECT_ROOT
    / "backend"
    / "data"
    / "routing"
    / "grid"
    / "orca_west_coast_bathymetry_landmasked.nc"
)

_DEFAULT_CURRENT_FILE = (
    _PROJECT_ROOT
    / "backend"
    / "data"
    / "routing"
    / "environmental"
    / "orca_west_coast_currents_departure.nc"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def initialize_routing_cache(
    bathymetry_file: str | Path | None = None,
    current_file: str | Path | None = None,
) -> RoutingCache:
    """
    Initialize the routing cache by loading all required data.
    
    This function should be called once during FastAPI startup.
    If called multiple times, it will reload the cache.
    
    Parameters
    ----------
    bathymetry_file:
        Path to bathymetry NetCDF file. Defaults to the standard
        ORCA west coast bathymetry file.
    current_file:
        Path to currents NetCDF file. Defaults to the standard
        ORCA west coast currents file.
    
    Returns
    -------
    RoutingCache
        The initialized cache object.
    
    Raises
    ------
    FileNotFoundError
        If data files are not found.
    ValueError
        If data validation fails.
    Exception
        For other initialization errors.
    """
    global _routing_cache, _cache_initialized, _cache_error
    
    # Resolve file paths
    bathy_path = Path(bathymetry_file) if bathymetry_file else _DEFAULT_BATHYMETRY_FILE
    curr_path = Path(current_file) if current_file else _DEFAULT_CURRENT_FILE
    
    # Load bathymetry
    if not bathy_path.exists():
        error_msg = f"Bathymetry file not found: {bathy_path}"
        _cache_error = error_msg
        _cache_initialized = False
        raise FileNotFoundError(error_msg)
    
    try:
        bathymetry = load_bathymetry(bathy_path)
    except Exception as exc:
        error_msg = f"Failed to load bathymetry data: {exc}"
        _cache_error = error_msg
        _cache_initialized = False
        raise RuntimeError(error_msg) from exc

    # Explicitly collect transient xarray/numpy temporaries from bathymetry
    # loading before allocating the next large dataset.
    gc.collect()

    # Load currents (pass bathymetry coordinates to avoid duplication)
    if not curr_path.exists():
        error_msg = f"Current dataset not found: {curr_path}"
        _cache_error = error_msg
        _cache_initialized = False
        raise FileNotFoundError(error_msg)

    try:
        currents = load_currents(
            curr_path,
            latitudes=bathymetry.latitudes,
            longitudes=bathymetry.longitudes
        )
    except Exception as exc:
        error_msg = f"Failed to load current data: {exc}"
        _cache_error = error_msg
        _cache_initialized = False
        raise RuntimeError(error_msg) from exc

    # Collect transient current loading temporaries before grid construction.
    gc.collect()
    
    # Build MarineGrid from bathymetry (reusing arrays to save memory)
    try:
        grid = MarineGrid(
            latitudes=bathymetry.latitudes,  # Reuse reference
            longitudes=bathymetry.longitudes,  # Reuse reference
            navigable=bathymetry.navigable,  # Reuse reference
            depth_m=bathymetry.depth_m,  # Reuse reference
        )
    except Exception as exc:
        error_msg = f"Failed to construct routing grid: {exc}"
        _cache_error = error_msg
        _cache_initialized = False
        raise RuntimeError(error_msg) from exc
    
    # Create default vessel profile
    vessel = VesselProfile()
    
    # Build constraint mask
    try:
        constraints = build_constraint_mask(bathymetry, vessel)
    except Exception as exc:
        error_msg = f"Failed to build navigation constraints: {exc}"
        _cache_error = error_msg
        _cache_initialized = False
        raise RuntimeError(error_msg) from exc
    
    # Create cache object
    cache = RoutingCache(
        bathymetry=bathymetry,
        currents=currents,
        grid=grid,
        vessel=vessel,
        constraints=constraints,
    )
    
    # Validate cache consistency
    try:
        cache.validate()
    except Exception as exc:
        error_msg = f"Cache validation failed: {exc}"
        _cache_error = error_msg
        _cache_initialized = False
        raise RuntimeError(error_msg) from exc
    
    # Store cache globally
    _routing_cache = cache
    _cache_initialized = True
    _cache_error = None
    
    return cache


def get_routing_cache() -> RoutingCache | None:
    """
    Get the current routing cache.
    
    Returns None if the cache has not been initialized.
    
    Returns
    -------
    RoutingCache | None
        The cached routing data, or None if not initialized.
    """
    return _routing_cache


def is_cache_initialized() -> bool:
    """
    Check if the routing cache has been successfully initialized.
    
    Returns
    -------
    bool
        True if cache is initialized and available.
    """
    return _cache_initialized and _routing_cache is not None


def get_cache_error() -> str | None:
    """
    Get the error message from the last failed cache initialization.
    
    Returns
    -------
    str | None
        The error message, or None if no error occurred.
    """
    return _cache_error


def clear_cache() -> None:
    """
    Clear the routing cache.
    
    This is primarily useful for testing or when reinitializing
    the cache with different data files.
    """
    global _routing_cache, _cache_initialized, _cache_error
    _routing_cache = None
    _cache_initialized = False
    _cache_error = None


def get_cache_info() -> dict[str, Any]:
    """
    Get information about the current cache state.
    
    Returns
    -------
    dict
        Cache information including initialization status,
        grid dimensions, and file paths.
    """
    info: dict[str, Any] = {
        "initialized": _cache_initialized,
        "has_error": _cache_error is not None,
        "error": _cache_error,
    }
    
    if _routing_cache is not None:
        info.update({
            "grid_rows": _routing_cache.grid.n_rows,
            "grid_cols": _routing_cache.grid.n_cols,
            "navigable_cells": _routing_cache.grid.navigable_nodes,
            "bathymetry_file": str(_DEFAULT_BATHYMETRY_FILE),
            "current_file": str(_DEFAULT_CURRENT_FILE),
            "vessel_type": _routing_cache.vessel.vessel_type,
        })
    
    return info
