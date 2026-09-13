from __future__ import annotations

import heapq
import math
import time

import numpy as np

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
    calculate_edge_cost,
)
from backend.agents.routing_agent.routing.astar import (
    astar_search,
)


BATHYMETRY_FILE = (
    "backend/data/routing/grid/"
    "orca_west_coast_bathymetry_landmasked.nc"
)

CURRENT_FILE = (
    "backend/data/routing/environmental/"
    "orca_west_coast_currents_departure.nc"
)


# ============================================================
# Dijkstra validation implementation
# ============================================================

def dijkstra_search(
    grid: MarineGrid,
    constraints,
    start_node: int,
    goal_node: int,
    bathymetry,
    currents,
    vessel: VesselProfile,
    weights: CostWeights,
    max_expansions: int = 10000,
):
    """
    Independent Dijkstra implementation.

    This is deliberately separate from A* so it can serve as
    an optimality baseline.

    Dijkstra uses:
        h(n) = 0
    """

    if not grid.is_valid_node(start_node):
        raise ValueError(
            f"Start node {start_node} is not navigable."
        )

    if not grid.is_valid_node(goal_node):
        raise ValueError(
            f"Goal node {goal_node} is not navigable."
        )

    start_row, start_col = grid.row_col(start_node)
    goal_row, goal_col = grid.row_col(goal_node)

    if constraints.blocked[start_row, start_col]:
        raise ValueError(
            f"Start node {start_node} is blocked."
        )

    if constraints.blocked[goal_row, goal_col]:
        raise ValueError(
            f"Goal node {goal_node} is blocked."
        )

    heap = [
        (0.0, start_node)
    ]

    distance = {
        start_node: 0.0
    }

    expanded = 0

    while heap:

        current_cost, current_node = heapq.heappop(
            heap
        )

        # Ignore stale entries.
        if current_cost > distance.get(
            current_node,
            math.inf,
        ):
            continue

        expanded += 1

        if expanded > max_expansions:
            raise RuntimeError(
                f"Dijkstra exceeded "
                f"{max_expansions} expansions."
            )

        # Goal reached.
        if current_node == goal_node:

            return {
                "cost": current_cost,
                "expanded": expanded,
                "reached": True,
            }

        # Explore neighbors.
        for neighbor_node, direction_deg in (
            grid.get_navigable_neighbors(
                current_node
            )
        ):

            neighbor_row, neighbor_col = (
                grid.row_col(neighbor_node)
            )

            if constraints.blocked[
                neighbor_row,
                neighbor_col,
            ]:
                continue

            edge = calculate_edge_cost(
                source_node=current_node,
                target_node=neighbor_node,
                route_direction_deg=direction_deg,
                grid=grid,
                bathymetry=bathymetry,
                currents=currents,
                constraints=constraints,
                vessel=vessel,
                weights=weights,
            )

            if not math.isfinite(
                edge.total_cost
            ):
                continue

            new_cost = (
                current_cost
                + edge.total_cost
            )

            if new_cost < distance.get(
                neighbor_node,
                math.inf,
            ):

                distance[neighbor_node] = new_cost

                heapq.heappush(
                    heap,
                    (
                        new_cost,
                        neighbor_node,
                    ),
                )

    return {
        "cost": math.inf,
        "expanded": expanded,
        "reached": False,
    }


# ============================================================
# Test setup
# ============================================================

print("=" * 60)
print("A* vs DIJKSTRA VALIDATION")
print("=" * 60)


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


grid = MarineGrid(
    latitudes=bathymetry.latitudes,
    longitudes=bathymetry.longitudes,
    navigable=bathymetry.navigable,
    depth_m=bathymetry.depth_m,
)

print(
    f"\nGrid: "
    f"{grid.n_rows} × {grid.n_cols}"
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

print("✓ Constraints built")


# ============================================================
# Choose a small real-grid validation route
# ============================================================

# We deliberately keep this route local.
#
# The previous A* test used:
#
#     start = 0
#     goal  = 100
#
# Reuse exactly the same pair so that the comparison is
# directly tied to the already-passing A* test.

start_node = 0
goal_node = 100


assert grid.is_valid_node(start_node), (
    f"Start node {start_node} is not navigable."
)

assert grid.is_valid_node(goal_node), (
    f"Goal node {goal_node} is not navigable."
)


print("\nValidation route:")

print(
    "  Start node:",
    start_node,
)

print(
    "  Goal node:",
    goal_node,
)

print(
    "  Start:",
    grid.node_to_latlon(start_node),
)

print(
    "  Goal:",
    grid.node_to_latlon(goal_node),
)


# ============================================================
# Run A*
# ============================================================

print("\n" + "-" * 60)
print("RUNNING A*")
print("-" * 60)


t0 = time.perf_counter()

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

astar_runtime = (
    time.perf_counter() - t0
)


print(
    "Reached:",
    astar_result.success,
)

print(
    "Cost:",
    astar_result.total_cost,
)

print(
    "Expanded:",
    astar_result.nodes_expanded,
)

print(
    "Path nodes:",
    astar_result.path_length,
)

print(
    "Runtime:",
    round(astar_runtime, 6),
    "seconds",
)


# ============================================================
# Validate A*
# ============================================================

assert astar_result.success, (
    f"A* failed: {astar_result.message}"
)

assert (
    astar_result.path[0]
    == start_node
)

assert (
    astar_result.path[-1]
    == goal_node
)

assert np.isfinite(
    astar_result.total_cost
)


# ============================================================
# Run Dijkstra
# ============================================================

print("\n" + "-" * 60)
print("RUNNING DIJKSTRA")
print("-" * 60)


t0 = time.perf_counter()

dijkstra_result = dijkstra_search(
    grid=grid,
    constraints=constraints,
    start_node=start_node,
    goal_node=goal_node,
    bathymetry=bathymetry,
    currents=currents,
    vessel=vessel,
    weights=weights,
    max_expansions=10000,
)

dijkstra_runtime = (
    time.perf_counter() - t0
)


print(
    "Reached:",
    dijkstra_result["reached"],
)

print(
    "Cost:",
    dijkstra_result["cost"],
)

print(
    "Expanded:",
    dijkstra_result["expanded"],
)

print(
    "Runtime:",
    round(dijkstra_runtime, 6),
    "seconds",
)


# ============================================================
# Optimality comparison
# ============================================================

print("\n" + "-" * 60)
print("OPTIMALITY CHECK")
print("-" * 60)


assert dijkstra_result["reached"], (
    "Dijkstra failed to reach the goal."
)


assert np.isfinite(
    dijkstra_result["cost"]
)


cost_difference = abs(
    astar_result.total_cost
    - dijkstra_result["cost"]
)


relative_difference = (
    cost_difference
    / max(
        abs(dijkstra_result["cost"]),
        1e-12,
    )
)


print(
    "A* cost:",
    astar_result.total_cost,
)

print(
    "Dijkstra cost:",
    dijkstra_result["cost"],
)

print(
    "Absolute difference:",
    cost_difference,
)

print(
    "Relative difference:",
    relative_difference,
)


# Floating-point calculations may produce tiny
# numerical differences. We allow a very small tolerance.

assert math.isclose(
    astar_result.total_cost,
    dijkstra_result["cost"],
    rel_tol=1e-9,
    abs_tol=1e-9,
), (
    "A* and Dijkstra produced different "
    "optimal costs."
)


print(
    "✓ A* and Dijkstra have the same optimal cost"
)


# ============================================================
# Efficiency comparison
# ============================================================

print("\n" + "-" * 60)
print("EFFICIENCY CHECK")
print("-" * 60)


print(
    "A* expanded:",
    astar_result.nodes_expanded,
)

print(
    "Dijkstra expanded:",
    dijkstra_result["expanded"],
)


if astar_result.nodes_expanded <= dijkstra_result[
    "expanded"
]:
    print(
        "✓ A* expanded no more nodes than Dijkstra"
    )
else:
    print(
        "⚠ A* expanded more nodes than Dijkstra"
    )


if dijkstra_runtime > 0:

    speedup = (
        dijkstra_runtime
        / max(astar_runtime, 1e-12)
    )

    print(
        "Runtime speedup:",
        round(speedup, 3),
        "x",
    )


# ============================================================
# Final result
# ============================================================

print("\n" + "=" * 60)
print("✓ A* vs DIJKSTRA VALIDATION PASSED")
print("=" * 60)