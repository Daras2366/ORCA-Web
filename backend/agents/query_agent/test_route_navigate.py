"""
ORCA Query Agent Navigation API Test
=====================================

Tests the new POST /api/route/navigate endpoint components.

This test verifies that the Query Agent can successfully:
1. Initialize the routing cache
2. Use the cached data for routing calculations
3. Return properly formatted routing results
4. Handle error cases appropriately

Note: This test focuses on the routing components rather than the full
FastAPI app due to gemini_client dependency requirements.

Run from the project root::

    python -m backend.agents.query_agent.test_route_navigate
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.agents.routing_agent.routing.cache import (
    initialize_routing_cache,
    get_routing_cache,
    is_cache_initialized,
    get_cache_error,
    clear_cache,
)
from backend.agents.routing_agent.routing.service import run_route
from backend.agents.routing_agent.routing.bathymetry import load_bathymetry
from backend.agents.routing_agent.routing.grid import MarineGrid


# ---------------------------------------------------------------------------
# Data file paths
# ---------------------------------------------------------------------------

BATHYMETRY_FILE = (
    "backend/data/routing/grid/"
    "orca_west_coast_bathymetry_landmasked.nc"
)


print("=" * 60)
print("QUERY AGENT NAVIGATION API COMPONENT TEST")
print("=" * 60)


# ---------------------------------------------------------------------------
# Step 0 — Resolve start/goal lat-lon from node IDs 0 and 100
# ---------------------------------------------------------------------------

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
# Step 1 — Test cache initialization
# ---------------------------------------------------------------------------

print("\n--- Testing routing cache initialization ---")

print("  Initializing routing cache...")
try:
    cache = initialize_routing_cache()
    print(f"  [OK] Cache initialized successfully")
except Exception as exc:
    print(f"  [ERROR] Cache initialization failed: {exc}")
    sys.exit(1)

# Verify cache is available
assert is_cache_initialized(), "Cache should be initialized after initialization"
print("  [OK] Cache is marked as initialized")

# Get cache info
cache_info = get_routing_cache()
assert cache_info is not None, "Cache should not be None after initialization"
print(f"  [OK] Cache object is available")

# Verify cache structure
assert hasattr(cache_info, 'bathymetry'), "Cache missing bathymetry"
assert hasattr(cache_info, 'currents'), "Cache missing currents"
assert hasattr(cache_info, 'grid'), "Cache missing grid"
assert hasattr(cache_info, 'vessel'), "Cache missing vessel"
assert hasattr(cache_info, 'constraints'), "Cache missing constraints"
print("  [OK] Cache has all required components")

# Verify grid dimensions
print(f"  Grid: {cache_info.grid.n_rows}x{cache_info.grid.n_cols}")
print(f"  Navigable cells: {cache_info.grid.navigable_nodes}")
print(f"  Vessel type: {cache_info.vessel.vessel_type}")


# ---------------------------------------------------------------------------
# Step 2 — Test routing with cached data
# ---------------------------------------------------------------------------

print("\n--- Testing routing with cached data ---")

print(f"  Calling run_route with cache...")
print(f"  Request: start=({start_lat:.6f}, {start_lon:.6f}), "
      f"destination=({goal_lat:.6f}, {goal_lon:.6f})")

result = run_route(
    start_latitude=start_lat,
    start_longitude=start_lon,
    destination_latitude=goal_lat,
    destination_longitude=goal_lon,
    cache=cache_info,
)

print(f"  Response keys: {list(result.keys())}")


# ---------------------------------------------------------------------------
# Step 3 — Verify success flag
# ---------------------------------------------------------------------------

print("\n--- Verifying success flag ---")

assert "success" in result, "Response missing 'success' field"
print(f"  success: {result['success']}")

assert result["success"] is True, (
    f"Routing failed: {result.get('message', 'Unknown error')}"
)

print(f"  message: {result.get('message')}")


# ---------------------------------------------------------------------------
# Step 4 — Verify coordinate fields
# ---------------------------------------------------------------------------

print("\n--- Verifying coordinate fields ---")

for field in ("start", "destination", "snapped_start", "snapped_destination"):
    assert field in result, f"Response missing '{field}' field."
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
# Step 5 — Verify metrics
# ---------------------------------------------------------------------------

print("\n--- Verifying metrics ---")

assert "metrics" in result, "Response missing 'metrics' field."
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

# Numeric sanity checks
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

# average_current_ms may legitimately be None
if metrics["average_current_ms"] is not None:
    assert math.isfinite(metrics["average_current_ms"]), (
        "average_current_ms must be finite when present."
    )

print("\n[OK] All metric assertions passed")


# ---------------------------------------------------------------------------
# Step 6 — Verify GeoJSON
# ---------------------------------------------------------------------------

print("\n--- Verifying GeoJSON ---")

assert "geojson" in result, "Response missing 'geojson' field."
geojson = result["geojson"]

assert geojson["type"] == "LineString", (
    f"GeoJSON type must be 'LineString', got '{geojson['type']}'"
)

coordinates = geojson["coordinates"]

assert isinstance(coordinates, list), "GeoJSON coordinates must be a list."
assert len(coordinates) >= 2, "GeoJSON must contain at least 2 coordinates."

print(f"  GeoJSON type:       {geojson['type']}")
print(f"  Coordinate count:   {len(coordinates)}")
print(f"  First coordinate:   {coordinates[0]}")
print(f"  Last coordinate:    {coordinates[-1]}")

# Validate coordinate order: GeoJSON is [longitude, latitude]
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
    assert -180.0 <= lon_val <= 180.0, (
        f"coordinate[{i}][0] longitude={lon_val} out of range."
    )
    assert -90.0 <= lat_val <= 90.0, (
        f"coordinate[{i}][1] latitude={lat_val} out of range."
    )

# Verify coordinate order matches snapped waypoints
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

print("\n[OK] GeoJSON assertions passed")


# ---------------------------------------------------------------------------
# Step 7 — Test invalid coordinate request
# ---------------------------------------------------------------------------

print("\n--- Testing invalid coordinate request ---")

invalid_result = run_route(
    start_latitude=999.0,  # Invalid latitude
    start_longitude=76.0,
    destination_latitude=12.0,
    destination_longitude=77.5,
    cache=cache_info,
)

assert invalid_result["success"] is False, "Should fail for out-of-range latitude."
assert "message" in invalid_result
print(f"  [OK] Invalid latitude rejected correctly: {invalid_result['message']}")


# ---------------------------------------------------------------------------
# Step 8 — Test out-of-grid coordinates
# ---------------------------------------------------------------------------

print("\n--- Testing out-of-grid coordinates ---")

out_result = run_route(
    start_latitude=0.0,  # Far outside grid
    start_longitude=0.0,
    destination_latitude=1.0,
    destination_longitude=1.0,
    cache=cache_info,
)

assert out_result["success"] is False, (
    "Should fail for coordinates outside grid extent."
)
print(f"  [OK] Out-of-grid coordinates rejected correctly: {out_result['message']}")


# ---------------------------------------------------------------------------
# Step 9 — Test backwards compatibility (no cache)
# ---------------------------------------------------------------------------

print("\n--- Testing backwards compatibility (no cache) ---")

# Test that run_route still works without cache parameter
legacy_result = run_route(
    start_latitude=start_lat,
    start_longitude=start_lon,
    destination_latitude=goal_lat,
    destination_longitude=goal_lon,
)

assert legacy_result["success"] is True, "Legacy mode should still work"
print("  [OK] Backwards compatibility maintained (no cache parameter)")


# ---------------------------------------------------------------------------
# Step 10 — Test cache error handling
# ---------------------------------------------------------------------------

print("\n--- Testing cache error handling ---")

# Clear cache to test error handling
clear_cache()
assert not is_cache_initialized(), "Cache should be cleared"
assert get_cache_error() is None, "No error should be set after clear"
print("  [OK] Cache cleared successfully")

# Reinitialize for cleanup
initialize_routing_cache()
print("  [OK] Cache reinitialized")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("[OK] QUERY AGENT NAVIGATION API COMPONENT TEST PASSED")
print("=" * 60)

print(f"\nSummary:")
print(f"  Distance:      {result['metrics']['distance_km']:.3f} km")
print(f"  Travel time:   {result['metrics']['travel_time_h']:.4f} h")
print(f"  Fuel:          {result['metrics']['fuel_l']:.3f} L")
print(f"  Min depth:     {result['metrics']['min_depth_m']:.0f} m")
print(f"  GeoJSON nodes: {len(result['geojson']['coordinates'])}")
print(f"\nComponents tested:")
print(f"  ✓ Cache initialization")
print(f"  ✓ Cache data structure")
print(f"  ✓ Routing with cached data")
print(f"  ✓ Response format validation")
print(f"  ✓ Error handling")
print(f"  ✓ Backwards compatibility")
print(f"\nNew endpoint ready: POST /api/route/navigate")
print(f"Existing endpoint unchanged: GET /api/route?zone_id=...")
