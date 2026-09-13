"""
ORCA Routing Service Integration Test
======================================

Tests the public run_route() entry point against the real routing
grid.  The test is intentionally focused: it uses the same start/goal
pair that the validated test_metrics.py test uses (node 0 → node 100)
but exercises the complete service interface rather than the individual
routing components.

Run from the project root::

    python -m backend.agents.routing_agent.test_service
"""

from __future__ import annotations

import math
from pathlib import Path

from backend.agents.routing_agent.routing.bathymetry import load_bathymetry
from backend.agents.routing_agent.routing.grid import MarineGrid
from backend.agents.routing_agent.routing.service import run_route


# ---------------------------------------------------------------------------
# Data file paths (same convention as the other routing tests)
# ---------------------------------------------------------------------------

BATHYMETRY_FILE = (
    "backend/data/routing/grid/"
    "orca_west_coast_bathymetry_landmasked.nc"
)

CURRENT_FILE = (
    "backend/data/routing/environmental/"
    "orca_west_coast_currents_departure.nc"
)


print("=" * 60)
print("ROUTING SERVICE INTEGRATION TEST")
print("=" * 60)


# ---------------------------------------------------------------------------
# Step 0 — Resolve start/goal lat-lon from node IDs 0 and 100
# ---------------------------------------------------------------------------
# We use the same node pair as test_metrics.py so we can compare results.
# The service accepts lat/lon coordinates and snaps internally.

print("\nLoading bathymetry to resolve node coordinates...")

_bathy = load_bathymetry(BATHYMETRY_FILE)

_grid = MarineGrid(
    latitudes=_bathy.latitudes,
    longitudes=_bathy.longitudes,
    navigable=_bathy.navigable,
    depth_m=_bathy.depth_m,
)

START_NODE = 0
GOAL_NODE = 100

start_lat, start_lon = _grid.node_to_latlon(START_NODE)
goal_lat, goal_lon = _grid.node_to_latlon(GOAL_NODE)

print(f"  Start  node {START_NODE}: lat={start_lat:.6f}, lon={start_lon:.6f}")
print(f"  Goal   node {GOAL_NODE}: lat={goal_lat:.6f}, lon={goal_lon:.6f}")


# ---------------------------------------------------------------------------
# Step 1 — Call the service
# ---------------------------------------------------------------------------

print(f"\nCalling run_route({start_lat:.6f}, {start_lon:.6f}, "
      f"{goal_lat:.6f}, {goal_lon:.6f})...")

result = run_route(
    start_latitude=start_lat,
    start_longitude=start_lon,
    destination_latitude=goal_lat,
    destination_longitude=goal_lon,
)

print(f"\nService response keys: {list(result.keys())}")


# ---------------------------------------------------------------------------
# Step 2 — Success flag
# ---------------------------------------------------------------------------

print("\n--- Success ---")
print(f"  success: {result.get('success')}")
print(f"  message: {result.get('message')}")

assert result.get("success") is True, (
    f"Service returned failure: {result.get('message')}"
)


# ---------------------------------------------------------------------------
# Step 3 — Coordinate fields
# ---------------------------------------------------------------------------

print("\n--- Coordinate fields ---")

for field in ("start", "destination", "snapped_start", "snapped_destination"):
    assert field in result, f"Result missing '{field}' field."
    coords = result[field]
    assert "latitude" in coords and "longitude" in coords, (
        f"'{field}' missing latitude/longitude keys."
    )
    assert isinstance(coords["latitude"], float), (
        f"'{field}.latitude' must be a plain float."
    )
    assert isinstance(coords["longitude"], float), (
        f"'{field}.longitude' must be a plain float."
    )
    print(
        f"  {field}: lat={coords['latitude']:.6f}, "
        f"lon={coords['longitude']:.6f}"
    )


# ---------------------------------------------------------------------------
# Step 4 — Metrics
# ---------------------------------------------------------------------------

print("\n--- Metrics ---")

assert "metrics" in result, "Result missing 'metrics' field."
metrics = result["metrics"]

required_metric_keys = {
    "distance_km",
    "travel_time_h",
    "fuel_l",
    "min_depth_m",
    "max_depth_m",
    "average_depth_m",
    "average_current_ms",
    "total_cost",
}

for key in required_metric_keys:
    assert key in metrics, f"Metrics missing key '{key}'."

for key, value in metrics.items():
    print(f"  {key}: {value}")

# Numeric sanity checks.

assert metrics["distance_km"] is not None
assert metrics["distance_km"] > 0, (
    f"distance_km must be > 0, got {metrics['distance_km']}"
)

assert metrics["travel_time_h"] is not None
assert metrics["travel_time_h"] > 0, (
    f"travel_time_h must be > 0, got {metrics['travel_time_h']}"
)

assert metrics["fuel_l"] is not None
assert metrics["fuel_l"] > 0, (
    f"fuel_l must be > 0, got {metrics['fuel_l']}"
)

assert metrics["min_depth_m"] is not None
assert math.isfinite(metrics["min_depth_m"]), (
    "min_depth_m must be finite."
)

assert metrics["max_depth_m"] is not None
assert metrics["max_depth_m"] >= metrics["min_depth_m"], (
    "max_depth_m must be >= min_depth_m."
)

assert metrics["average_depth_m"] is not None
assert math.isfinite(metrics["average_depth_m"]), (
    "average_depth_m must be finite."
)

assert metrics["total_cost"] is not None
assert metrics["total_cost"] > 0, (
    f"total_cost must be > 0, got {metrics['total_cost']}"
)

# average_current_ms may legitimately be None when no current data
# covers the route.  If it is present it must be a finite float.
if metrics["average_current_ms"] is not None:
    assert math.isfinite(metrics["average_current_ms"]), (
        "average_current_ms must be finite when present."
    )

# No NumPy objects in metrics — every value must be a plain Python
# float or None.
for key, value in metrics.items():
    assert value is None or isinstance(value, float), (
        f"Metric '{key}' contains a non-float value: "
        f"{type(value).__name__}"
    )

print("\n[OK] All metric assertions passed")


# ---------------------------------------------------------------------------
# Step 5 — GeoJSON
# ---------------------------------------------------------------------------

print("\n--- GeoJSON ---")

assert "geojson" in result, "Result missing 'geojson' field."
geojson = result["geojson"]

assert geojson["type"] == "LineString", (
    f"GeoJSON type must be 'LineString', got '{geojson['type']}'"
)

coordinates = geojson["coordinates"]

assert isinstance(coordinates, list), "GeoJSON coordinates must be a list."

assert len(coordinates) > 0, "GeoJSON coordinates must not be empty."

print(f"  GeoJSON type:       {geojson['type']}")
print(f"  Coordinate count:   {len(coordinates)}")
print(f"  First coordinate:   {coordinates[0]}")
print(f"  Last coordinate:    {coordinates[-1]}")

# Validate coordinate order: GeoJSON is [longitude, latitude].
# Each coordinate must be a list of exactly 2 finite floats.
for i, coord in enumerate(coordinates):
    assert isinstance(coord, list), (
        f"coordinate[{i}] must be a list."
    )
    assert len(coord) == 2, (
        f"coordinate[{i}] must have exactly 2 elements."
    )
    lon_val, lat_val = coord
    assert isinstance(lon_val, float) and math.isfinite(lon_val), (
        f"coordinate[{i}][0] (longitude) must be a finite float."
    )
    assert isinstance(lat_val, float) and math.isfinite(lat_val), (
        f"coordinate[{i}][1] (latitude) must be a finite float."
    )
    # Sanity range checks.
    assert -180.0 <= lon_val <= 180.0, (
        f"coordinate[{i}][0] longitude={lon_val} out of range."
    )
    assert -90.0 <= lat_val <= 90.0, (
        f"coordinate[{i}][1] latitude={lat_val} out of range."
    )

# GeoJSON spec: coordinate order is [longitude, latitude].
# The first coordinate's longitude must match the snapped_start longitude.
snapped_start_lon = result["snapped_start"]["longitude"]
snapped_goal_lon = result["snapped_destination"]["longitude"]

assert coordinates[0][0] == snapped_start_lon, (
    f"First GeoJSON longitude ({coordinates[0][0]}) does not match "
    f"snapped_start longitude ({snapped_start_lon})."
)

assert coordinates[-1][0] == snapped_goal_lon, (
    f"Last GeoJSON longitude ({coordinates[-1][0]}) does not match "
    f"snapped_destination longitude ({snapped_goal_lon})."
)

print("  [OK] Coordinate order is [longitude, latitude]")
print(f"  [OK] Start/end coordinates match snapped waypoints")

# Coordinate count should match path length — we infer this by confirming
# the coordinate list is neither empty nor a single point.
assert len(coordinates) >= 2, (
    "GeoJSON must contain at least 2 coordinates (start and destination)."
)

print("\n[OK] GeoJSON assertions passed")


# ---------------------------------------------------------------------------
# Step 6 — No NumPy / xarray objects anywhere in the result
# ---------------------------------------------------------------------------

print("\n--- Serialisability check ---")


def _check_serialisable(obj: object, path: str = "result") -> None:
    """
    Recursively verify that `obj` contains only JSON-compatible Python
    types (dict, list, str, int, float, bool, NoneType).
    """
    import numpy as np  # available since the routing code uses it

    if isinstance(obj, dict):
        for k, v in obj.items():
            _check_serialisable(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _check_serialisable(item, f"{path}[{i}]")
    elif isinstance(obj, (bool, int, float, str, type(None))):
        pass  # all acceptable
    elif isinstance(obj, np.generic):
        raise TypeError(
            f"NumPy scalar found at {path}: {type(obj).__name__}"
        )
    else:
        raise TypeError(
            f"Non-serialisable type at {path}: {type(obj).__name__}"
        )


_check_serialisable(result)

print("  [OK] Result contains no NumPy or non-serialisable objects")


# ---------------------------------------------------------------------------
# Step 7 — Error-handling cases (lightweight smoke tests)
# ---------------------------------------------------------------------------

print("\n--- Error-handling smoke tests ---")

# Invalid coordinates.
bad = run_route(999.0, 76.0, 12.0, 77.5)
assert bad["success"] is False, "Should fail for out-of-range latitude."
assert "message" in bad
print("  [OK] Invalid latitude rejected correctly")

# NaN coordinates.
nan_result = run_route(float("nan"), 76.0, 12.0, 77.5)
assert nan_result["success"] is False, "Should fail for NaN latitude."
print("  [OK] NaN latitude rejected correctly")

# Coordinates far outside the grid extent.
out_result = run_route(0.0, 0.0, 1.0, 1.0)
assert out_result["success"] is False, (
    "Should fail for coordinates outside grid extent."
)
print("  [OK] Out-of-grid coordinates rejected correctly")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("[OK] ROUTING SERVICE INTEGRATION TEST PASSED")
print("=" * 60)

print(f"\nSummary:")
print(f"  Distance:      {result['metrics']['distance_km']:.3f} km")
print(f"  Travel time:   {result['metrics']['travel_time_h']:.4f} h")
print(f"  Fuel:          {result['metrics']['fuel_l']:.3f} L")
print(f"  Min depth:     {result['metrics']['min_depth_m']:.0f} m")
print(f"  GeoJSON nodes: {len(result['geojson']['coordinates'])}")
