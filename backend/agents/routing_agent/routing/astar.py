from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Dict, List, Optional, Tuple

from backend.agents.routing_agent.routing import bathymetry, vessel

from .grid import MarineGrid
from .constraints import ConstraintMask
from .cost import (
    CostWeights,
    calculate_edge_cost,
    haversine_distance_km,
)

from .bathymetry import BathymetryData
from .environment import CurrentData
from .vessel import VesselProfile, knots_to_mps


@dataclass
class AStarResult:
    """
    Result returned by the A* routing engine.
    """

    success: bool
    path: List[int]
    total_cost: float
    nodes_expanded: int
    message: str = ""

    @property
    def path_length(self) -> int:
        return len(self.path)


def _heuristic(
    grid: MarineGrid,
    current_node: int,
    goal_node: int,
    vessel_speed_mps: float,
) -> float:
    """
    Optimistic straight-line travel-time heuristic.

    We assume:
        - straight-line distance
        - vessel's full cruising speed
        - no penalties

    This keeps the heuristic optimistic for the prototype.
    """

    current_lat, current_lon = grid.node_to_latlon(
        current_node
    )

    goal_lat, goal_lon = grid.node_to_latlon(
        goal_node
    )

    distance_km = haversine_distance_km(
        current_lat,
        current_lon,
        goal_lat,
        goal_lon,
    )

    speed_kmh = max(
        vessel_speed_mps * 3.6,
        0.1,
    )

    return distance_km / speed_kmh


def reconstruct_path(
    came_from: Dict[int, int],
    start_node: int,
    goal_node: int,
) -> List[int]:
    """
    Reconstruct path from goal back to start.
    """

    path = [goal_node]

    current = goal_node

    while current != start_node:

        if current not in came_from:
            return []

        current = came_from[current]

        path.append(current)

    path.reverse()

    return path


def astar_search(
    grid: MarineGrid,
    constraints: ConstraintMask,
    start_node: int,
    goal_node: int,
    bathymetry: BathymetryData,
    currents: CurrentData,
    vessel: VesselProfile,
    weights: Optional[CostWeights] = None,
) -> AStarResult:
    """
    Run deterministic A* over the marine routing grid.

    The grid supplies flat node IDs and movement directions.
    The constraint mask supplies hard blocks.
    The cost engine determines edge cost.
    """

    if weights is None:
        weights = CostWeights()

    # ========================================================
    # Validate start
    # ========================================================

    if not grid.is_valid_node(start_node):
        return AStarResult(
            success=False,
            path=[],
            total_cost=math.inf,
            nodes_expanded=0,
            message="Start node is invalid or not navigable.",
        )

    # ========================================================
    # Validate goal
    # ========================================================

    if not grid.is_valid_node(goal_node):
        return AStarResult(
            success=False,
            path=[],
            total_cost=math.inf,
            nodes_expanded=0,
            message="Goal node is invalid or not navigable.",
        )

    start_row, start_col = grid.row_col(
        start_node
    )

    goal_row, goal_col = grid.row_col(
        goal_node
    )

    if constraints.blocked[
        start_row,
        start_col,
    ]:
        return AStarResult(
            success=False,
            path=[],
            total_cost=math.inf,
            nodes_expanded=0,
            message="Start node is blocked.",
        )

    if constraints.blocked[
        goal_row,
        goal_col,
    ]:
        return AStarResult(
            success=False,
            path=[],
            total_cost=math.inf,
            nodes_expanded=0,
            message="Goal node is blocked.",
        )

    # ========================================================
    # Same-node case
    # ========================================================

    if start_node == goal_node:

        return AStarResult(
            success=True,
            path=[start_node],
            total_cost=0.0,
            nodes_expanded=0,
            message="Start and goal are the same node.",
        )

    # ========================================================
    # A* structures
    # ========================================================

    # Heap entries:
    #
    #     (f_score, node_id)
    #
    # Using node_id as the second value gives deterministic
    # tie-breaking.

    open_heap: List[
        Tuple[float, int]
    ] = []

    came_from: Dict[int, int] = {}

    g_score: Dict[int, float] = {
        start_node: 0.0
    }

    start_h = _heuristic(
        grid,
        start_node,
        goal_node,
        knots_to_mps(
            vessel.cruising_speed_knots
        ),
    )

    heapq.heappush(
        open_heap,
        (
            start_h,
            start_node,
        ),
    )

    nodes_expanded = 0

    # ========================================================
    # Main A* loop
    # ========================================================

    while open_heap:

        current_f, current_node = heapq.heappop(
            open_heap
        )

        current_g = g_score.get(
            current_node,
            math.inf,
        )

        current_h = _heuristic(
            grid,
            current_node,
            goal_node,
            knots_to_mps(
                vessel.cruising_speed_knots
            ),
        )

        expected_f = current_g + current_h

        # Ignore stale heap entries.
        if current_f > expected_f + 1e-12:
            continue

        nodes_expanded += 1

        # ====================================================
        # Goal reached
        # ====================================================

        if current_node == goal_node:

            path = reconstruct_path(
                came_from,
                start_node,
                goal_node,
            )

            if not path:

                return AStarResult(
                    success=False,
                    path=[],
                    total_cost=math.inf,
                    nodes_expanded=nodes_expanded,
                    message="Path reconstruction failed.",
                )

            return AStarResult(
                success=True,
                path=path,
                total_cost=g_score[
                    goal_node
                ],
                nodes_expanded=nodes_expanded,
                message="A* route found.",
            )

        # ====================================================
        # Explore neighbors
        # ====================================================

        neighbors = grid.get_navigable_neighbors(
            current_node
        )

        for neighbor_node, direction_deg in neighbors:

            # ------------------------------------------------
            # Convert neighbor node ID to row/column
            # ------------------------------------------------

            neighbor_row, neighbor_col = grid.row_col(
                neighbor_node
            )

            # ------------------------------------------------
            # Hard constraint check
            # ------------------------------------------------

            if constraints.blocked[
                neighbor_row,
                neighbor_col,
            ]:
                continue

            # ------------------------------------------------
            # Current/source coordinates
            # ------------------------------------------------

            source_lat, source_lon = (
                grid.node_to_latlon(
                    current_node
                )
            )

            target_lat, target_lon = (
                grid.node_to_latlon(
                    neighbor_node
                )
            )

            # ------------------------------------------------
            # Edge cost
            # ------------------------------------------------

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

            # ------------------------------------------------
            # Skip impossible edge
            # ------------------------------------------------

            if not math.isfinite(
                edge.total_cost
            ):
                continue

            # ------------------------------------------------
            # Tentative g score
            # ------------------------------------------------

            tentative_g = (
                current_g
                + edge.total_cost
            )

            previous_g = g_score.get(
                neighbor_node,
                math.inf,
            )

            if tentative_g >= previous_g:
                continue

            # ------------------------------------------------
            # Better route to neighbor found
            # ------------------------------------------------

            came_from[
                neighbor_node
            ] = current_node

            g_score[
                neighbor_node
            ] = tentative_g

            # ------------------------------------------------
            # Calculate f = g + h
            # ------------------------------------------------

            heuristic = _heuristic(
                grid,
                neighbor_node,
                goal_node,
                knots_to_mps(
                    vessel.cruising_speed_knots
                ),
            )

            f_score = (
                tentative_g
                + heuristic
            )

            heapq.heappush(
                open_heap,
                (
                    f_score,
                    neighbor_node,
                ),
            )

    # ========================================================
    # No route
    # ========================================================

    return AStarResult(
        success=False,
        path=[],
        total_cost=math.inf,
        nodes_expanded=nodes_expanded,
        message=(
            "No route exists between "
            "the selected nodes."
        ),
    )