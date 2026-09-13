import numpy as np

from backend.agents.routing_agent.routing.grid import MarineGrid
from backend.agents.routing_agent.routing.bathymetry import load_bathymetry
from backend.agents.routing_agent.routing.environment import load_currents
from backend.agents.routing_agent.routing.constraints import (
    build_constraint_mask,
)
from backend.agents.routing_agent.routing.vessel import (
    VesselProfile
)
from backend.agents.routing_agent.routing.astar import astar_search


BATHYMETRY_FILE = (
    "backend/data/routing/grid/"
    "orca_west_coast_bathymetry_landmasked.nc"
)

CURRENT_FILE = (
    "backend/data/routing/environmental/"
    "orca_west_coast_currents_departure.nc"
)


print("=" * 60)
print("A* ROUTING TEST")
print("=" * 60)


# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

print("\nLoading bathymetry...")

bathymetry = load_bathymetry(
    BATHYMETRY_FILE
)

print("✓ Bathymetry loaded")


print("\nLoading currents...")

currents = load_currents(
    CURRENT_FILE
)

print("✓ Currents loaded")


# ------------------------------------------------------------
# Build grid
# ------------------------------------------------------------

grid = MarineGrid(
    latitudes=bathymetry.latitudes,
    longitudes=bathymetry.longitudes,
    navigable=bathymetry.navigable,
    depth_m=bathymetry.depth_m,
)

print(
    f"\nGrid: {grid.n_rows} × {grid.n_cols}"
)


# ------------------------------------------------------------
# Vessel
# ------------------------------------------------------------

vessel = VesselProfile(
    cruising_speed_knots=12.0,
    draft_m=4.0,
    under_keel_clearance_m=1.0,
    fuel_capacity_litres=50000.0,
    fuel_burn_lph=120.0,
)

print(
    f"Vessel speed: "
    f"{vessel.cruising_speed_knots} knots"
)

print(
    f"Minimum safe depth: "
    f"{vessel.minimum_safe_depth_m} m"
)


# ------------------------------------------------------------
# Constraints
# ------------------------------------------------------------

constraints = build_constraint_mask(
    bathymetry,
    vessel,
)

print("✓ Constraints built")


# ------------------------------------------------------------
# Choose a small REAL test route
# ------------------------------------------------------------

# Find navigable cells away from the boundary.
navigable_indices = np.flatnonzero(
    ~constraints.blocked.ravel()
)

assert len(navigable_indices) > 0

start_node = int(
    navigable_indices[0]
)

# Select a destination several cells away.
start_row = start_node // grid.n_cols
start_col = start_node % grid.n_cols

goal_node = None

for offset in range(100, 2000):

    candidate = start_node + offset

    if candidate >= grid.n_nodes:
        break

    row = candidate // grid.n_cols
    col = candidate % grid.n_cols

    if not constraints.blocked[row, col]:

        # Keep the test reasonably local.
        if abs(row - start_row) < 100:
            goal_node = candidate
            break


assert goal_node is not None, (
    "Could not find a suitable real-grid goal node."
)


print("\nRoute request:")

print(
    "  Start node:",
    start_node
)

print(
    "  Goal node:",
    goal_node
)

print(
    "  Start:",
    grid.node_to_latlon(start_node)
)

print(
    "  Goal:",
    grid.node_to_latlon(goal_node)
)


# ------------------------------------------------------------
# Run A*
# ------------------------------------------------------------

print("\nRunning A*...")

result = astar_search(
    grid=grid,
    constraints=constraints,
    start_node=start_node,
    goal_node=goal_node,
    bathymetry=bathymetry,
    currents=currents,
    vessel=vessel,
)


# ------------------------------------------------------------
# Validate result
# ------------------------------------------------------------

print("\nA* result:")

print(
    "  Success:",
    result.success
)

print(
    "  Message:",
    result.message
)

print(
    "  Nodes expanded:",
    result.nodes_expanded
)

print(
    "  Path nodes:",
    result.path_length
)

print(
    "  Total cost:",
    result.total_cost
)


assert result.success, (
    f"A* failed: {result.message}"
)

assert len(result.path) >= 2

assert result.path[0] == start_node

assert result.path[-1] == goal_node

assert np.isfinite(result.total_cost)

assert result.total_cost > 0


# ------------------------------------------------------------
# Verify every path cell is navigable
# ------------------------------------------------------------

for node in result.path:

    row = node // grid.n_cols
    col = node % grid.n_cols

    assert not constraints.blocked[row, col], (
        f"Route entered blocked cell: {node}"
    )


print(
    "\n✓ Route contains no blocked cells"
)


# ------------------------------------------------------------
# Verify path connectivity
# ------------------------------------------------------------

for a, b in zip(
    result.path[:-1],
    result.path[1:],
):

    neighbors = grid.get_navigable_neighbors(a)

    neighbor_ids = {
        neighbor_node
        for neighbor_node, direction_deg in neighbors
    }

    assert b in neighbor_ids, (
        f"Invalid path jump: {a} -> {b}"
    )


print("\n" + "=" * 60)
print("✓ A* ROUTING TEST PASSED")
print("=" * 60)