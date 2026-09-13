from backend.agents.routing_agent.routing.grid import MarineGrid
from backend.agents.routing_agent.routing.bathymetry import (
    load_bathymetry,
)
from backend.agents.routing_agent.routing.environment import (
    load_currents,
)
from backend.agents.routing_agent.routing.constraints import (
    build_constraint_mask,
)
from backend.agents.routing_agent.routing.vessel import (
    VesselProfile,
)
from backend.agents.routing_agent.routing.cost import (
    CostWeights,
)
from backend.agents.routing_agent.routing.astar import (
    astar_search,
)
from backend.agents.routing_agent.routing.metrics import (
    calculate_route_metrics,
    path_to_geojson,
)


BATHYMETRY_FILE = (
    "backend/data/routing/grid/"
    "orca_west_coast_bathymetry_landmasked.nc"
)

CURRENT_FILE = (
    "backend/data/routing/environmental/"
    "orca_west_coast_currents_departure.nc"
)


print("=" * 60)
print("ROUTE METRICS + GEOJSON TEST")
print("=" * 60)


# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

bathymetry = load_bathymetry(
    BATHYMETRY_FILE
)

currents = load_currents(
    CURRENT_FILE
)

grid = MarineGrid(
    latitudes=bathymetry.latitudes,
    longitudes=bathymetry.longitudes,
    navigable=bathymetry.navigable,
    depth_m=bathymetry.depth_m,
)

vessel = VesselProfile(
    cruising_speed_knots=12.0,
    draft_m=4.0,
    under_keel_clearance_m=1.0,
    fuel_capacity_litres=50000.0,
    fuel_burn_lph=120.0,
)

weights = CostWeights()

constraints = build_constraint_mask(
    bathymetry,
    vessel,
)


# ------------------------------------------------------------
# Route
# ------------------------------------------------------------

start_node = 0
goal_node = 100

print(
    f"\nRouting {start_node} -> {goal_node}"
)


result = astar_search(
    grid=grid,
    constraints=constraints,
    start_node=start_node,
    goal_node=goal_node,
    bathymetry=bathymetry,
    currents=currents,
    vessel=vessel,
    weights=weights,
)


assert result.success, (
    f"A* failed: {result.message}"
)

path = result.path

print(
    "✓ Route found"
)

print(
    "Path nodes:",
    len(path),
)


# ------------------------------------------------------------
# Metrics
# ------------------------------------------------------------

metrics = calculate_route_metrics(
    path=path,
    grid=grid,
    bathymetry=bathymetry,
    currents=currents,
    constraints=constraints,
    vessel=vessel,
    weights=weights,
)


print("\nRoute metrics:")

for key, value in metrics.items():
    print(
        f"  {key}: {value}"
    )


# ------------------------------------------------------------
# Basic metric validation
# ------------------------------------------------------------

assert metrics["distance_km"] > 0

assert metrics["travel_time_h"] > 0

assert metrics["fuel_l"] > 0

assert metrics["min_depth_m"] >= (
    vessel.minimum_safe_depth_m
)

assert metrics["max_depth_m"] >= (
    metrics["min_depth_m"]
)

assert metrics["total_cost"] >= 0


print(
    "\n✓ Physical metrics are valid"
)


# ------------------------------------------------------------
# GeoJSON
# ------------------------------------------------------------

geojson = path_to_geojson(
    path=path,
    grid=grid,
)


print("\nGeoJSON:")

print(
    "  Type:",
    geojson["type"],
)

print(
    "  Coordinate count:",
    len(geojson["coordinates"]),
)

print(
    "  First coordinate:",
    geojson["coordinates"][0],
)

print(
    "  Last coordinate:",
    geojson["coordinates"][-1],
)


# ------------------------------------------------------------
# GeoJSON validation
# ------------------------------------------------------------

assert geojson["type"] == "LineString"

assert len(
    geojson["coordinates"]
) == len(path)

assert (
    geojson["coordinates"][0][0]
    == grid.node_to_latlon(path[0])[1]
)

assert (
    geojson["coordinates"][0][1]
    == grid.node_to_latlon(path[0])[0]
)

assert (
    geojson["coordinates"][-1][0]
    == grid.node_to_latlon(path[-1])[1]
)

assert (
    geojson["coordinates"][-1][1]
    == grid.node_to_latlon(path[-1])[0]
)


print(
    "✓ GeoJSON coordinate order is "
    "[longitude, latitude]"
)


print("\n" + "=" * 60)
print("✓ ROUTE METRICS + GEOJSON TEST PASSED")
print("=" * 60)