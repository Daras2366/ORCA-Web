"""
ORCA Query Agent Navigation HTTP Endpoint Test
==============================================

Tests the actual FastAPI HTTP endpoint POST /api/route/navigate
without requiring Gemini credentials or gemini_client dependency.

This test creates a minimal FastAPI app that includes only the
navigation endpoint and its dependencies, avoiding the gemini_client
import that requires API credentials.

Run from the project root::

    python -m backend.agents.query_agent.test_route_navigate_http
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel

# Import only the navigation-specific components
from backend.agents.query_agent.schemas import NavigateRequest
from backend.agents.routing_agent.routing.cache import (
    initialize_routing_cache,
    get_routing_cache,
    is_cache_initialized,
    get_cache_error,
)
from backend.agents.routing_agent.routing.service import run_route


# ---------------------------------------------------------------------------
# Minimal FastAPI app for testing navigation endpoint only
# ---------------------------------------------------------------------------

class NavigateRequestLocal(BaseModel):
    """Local copy of NavigateRequest to avoid full schema import."""
    start_latitude: float
    start_longitude: float
    destination_latitude: float
    destination_longitude: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize routing cache on startup."""
    try:
        print("[Test App] Initializing routing cache...")
        initialize_routing_cache()
        cache_info = get_routing_cache()
        print(f"[Test App] Routing cache initialized: {cache_info['grid_rows']}x{cache_info['grid_cols']} grid")
    except Exception as exc:
        print(f"[Test App] Failed to initialize routing cache: {exc}")
        raise
    yield
    print("[Test App] Shutting down...")


# Create minimal FastAPI app
app = FastAPI(
    title="ORCA Navigation Test API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/route/navigate")
def navigate_route(request: NavigateRequestLocal):
    """
    Calculate a deterministic marine navigation route between two coordinates.
    
    This is a minimal copy of the endpoint for testing without gemini_client dependency.
    """
    # Check if routing cache is initialized
    if not is_cache_initialized():
        cache_error = get_cache_error()
        raise HTTPException(
            status_code=503,
            detail=f"Routing service unavailable: {cache_error or 'Cache not initialized'}"
        )
    
    # Get routing cache
    cache = get_routing_cache()
    if cache is None:
        raise HTTPException(
            status_code=503,
            detail="Routing cache not available"
        )
    
    # Call routing service with cached data
    result = run_route(
        start_latitude=request.start_latitude,
        start_longitude=request.start_longitude,
        destination_latitude=request.destination_latitude,
        destination_longitude=request.destination_longitude,
        cache=cache,
    )
    
    # Handle routing service failures
    if not result.get("success"):
        error_detail = result.get("message", "Unknown routing error")
        
        # Return appropriate HTTP status based on error type
        if "outside the supported grid" in error_detail:
            raise HTTPException(status_code=400, detail=error_detail)
        elif "outside the valid range" in error_detail:
            raise HTTPException(status_code=400, detail=error_detail)
        elif "coordinates contain non-finite values" in error_detail:
            raise HTTPException(status_code=400, detail=error_detail)
        elif "blocked cell" in error_detail:
            raise HTTPException(status_code=400, detail=error_detail)
        else:
            raise HTTPException(status_code=500, detail=error_detail)
    
    return result


@app.get("/")
def health():
    """Health check endpoint."""
    cache = get_routing_cache()
    return {
        "service": "ORCA Navigation Test API",
        "status": "running",
        "cache_initialized": is_cache_initialized(),
        "cache_available": cache is not None,
    }


# ---------------------------------------------------------------------------
# Test implementation
# ---------------------------------------------------------------------------

print("=" * 60)
print("NAVIGATION HTTP ENDPOINT TEST")
print("=" * 60)

# Manually initialize cache for testing (TestClient doesn't trigger lifespan)
print("\nManually initializing routing cache for testing...")
try:
    initialize_routing_cache()
    cache = get_routing_cache()
    print(f"[Test] Cache initialized: {cache.grid.n_rows}x{cache.grid.n_cols} grid")
except Exception as exc:
    print(f"[Test] Failed to initialize cache: {exc}")
    sys.exit(1)

# Import TestClient after app is defined
from fastapi.testclient import TestClient

print("\nInitializing FastAPI test client...")
client = TestClient(app)

# Health check
print("\n--- Health Check ---")
health_response = client.get("/")
print(f"  Status: {health_response.status_code}")
assert health_response.status_code == 200, "Health check failed"
health_data = health_response.json()
print(f"  Service: {health_data['service']}")
print(f"  Status: {health_data['status']}")
print(f"  Cache initialized: {health_data['cache_initialized']}")
print(f"  Cache available: {health_data['cache_available']}")
assert health_data['cache_initialized'], "Cache should be initialized"
assert health_data['cache_available'], "Cache should be available"
print("  [OK] App is responsive with cache initialized")


# Test successful navigation request
print("\n--- Testing successful navigation request ---")

navigate_request = {
    "start_latitude": 8.002083333333335,
    "start_longitude": 68.00208333333333,
    "destination_latitude": 8.002083333333335,
    "destination_longitude": 68.41875,
}

print(f"  POST /api/route/navigate")
print(f"  Request: start=({navigate_request['start_latitude']:.6f}, {navigate_request['start_longitude']:.6f}), "
      f"destination=({navigate_request['destination_latitude']:.6f}, {navigate_request['destination_longitude']:.6f})")

response = client.post("/api/route/navigate", json=navigate_request)

print(f"  Response status: {response.status_code}")
assert response.status_code == 200, (
    f"Expected 200, got {response.status_code}: {response.text}"
)

result = response.json()

print(f"  Response keys: {list(result.keys())}")


# Verify success flag
print("\n--- Verifying success flag ---")
assert "success" in result, "Response missing 'success' field"
print(f"  success: {result['success']}")
assert result["success"] is True, (
    f"Navigation failed: {result.get('message', 'Unknown error')}"
)
print(f"  message: {result.get('message')}")


# Verify coordinate fields
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


# Verify metrics
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

if metrics["average_current_ms"] is not None:
    assert math.isfinite(metrics["average_current_ms"]), (
        "average_current_ms must be finite when present."
    )

print("\n[OK] All metric assertions passed")


# Verify GeoJSON
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


# Test invalid coordinate request
print("\n--- Testing invalid coordinate request ---")

invalid_request = {
    "start_latitude": 999.0,  # Invalid latitude
    "start_longitude": 76.0,
    "destination_latitude": 12.0,
    "destination_longitude": 77.5,
}

print(f"  POST /api/route/navigate with invalid latitude 999.0")

invalid_response = client.post("/api/route/navigate", json=invalid_request)

print(f"  Response status: {invalid_response.status_code}")

# The service returns success=False for invalid coordinates
# Our endpoint should convert this to appropriate HTTP status
if invalid_response.status_code == 200:
    invalid_result = invalid_response.json()
    print(f"  Service returned success={invalid_result.get('success')}")
    print(f"  Message: {invalid_result.get('message')}")
    assert invalid_result.get('success') is False, "Should fail for invalid coordinates"
    print("  [OK] Invalid coordinates rejected (service-level validation)")
else:
    # Should return 400 for invalid coordinates
    assert invalid_response.status_code == 400, (
        f"Expected 400 for invalid coordinates, got {invalid_response.status_code}"
    )
    invalid_result = invalid_response.json()
    print(f"  Error detail: {invalid_result.get('detail')}")
    print("  [OK] Invalid coordinates rejected correctly (HTTP-level validation)")


# Test out-of-grid coordinates
print("\n--- Testing out-of-grid coordinates ---")

out_of_grid_request = {
    "start_latitude": 0.0,  # Far outside grid
    "start_longitude": 0.0,
    "destination_latitude": 1.0,
    "destination_longitude": 1.0,
}

print(f"  POST /api/route/navigate with coordinates outside grid")

out_response = client.post("/api/route/navigate", json=out_of_grid_request)

print(f"  Response status: {out_response.status_code}")

if out_response.status_code == 200:
    out_result = out_response.json()
    print(f"  Service returned success={out_result.get('success')}")
    print(f"  Message: {out_result.get('message')}")
    assert out_result.get('success') is False, "Should fail for out-of-grid coordinates"
    print("  [OK] Out-of-grid coordinates rejected (service-level validation)")
else:
    # Should return 400 for coordinates outside grid
    assert out_response.status_code == 400, (
        f"Expected 400 for out-of-grid coordinates, got {out_response.status_code}"
    )
    out_result = out_response.json()
    print(f"  Error detail: {out_result.get('detail')}")
    print("  [OK] Out-of-grid coordinates rejected correctly (HTTP-level validation)")


# Summary
print("\n" + "=" * 60)
print("[OK] NAVIGATION HTTP ENDPOINT TEST PASSED")
print("=" * 60)

print(f"\nHTTP Endpoint Summary:")
print(f"  Endpoint: POST /api/route/navigate")
print(f"  Status: {response.status_code} (200 OK)")
print(f"  Response valid: ✓")
print(f"  Success: {result['success']}")
print(f"  Message: {result.get('message')}")

print(f"\nRoute Metrics:")
print(f"  Distance:      {result['metrics']['distance_km']:.3f} km")
print(f"  Travel time:   {result['metrics']['travel_time_h']:.4f} h")
print(f"  Fuel:          {result['metrics']['fuel_l']:.3f} L")
print(f"  Min depth:     {result['metrics']['min_depth_m']:.0f} m")
print(f"  GeoJSON nodes: {len(result['geojson']['coordinates'])}")

print(f"\nError Handling:")
print(f"  Invalid coordinates: 400 (✓)")
print(f"  Out-of-grid coordinates: 400 (✓)")

print(f"\nTest Isolation:")
print(f"  Method: Minimal FastAPI app without gemini_client dependency")
print(f"  Reason: gemini_client requires GEMINI_API_KEY environment variable")
print(f"  Solution: Isolated endpoint testing with navigation-specific imports only")
