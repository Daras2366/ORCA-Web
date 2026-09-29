from __future__ import annotations

import math
from typing import Any

from .grid import MarineGrid
from .bathymetry import BathymetryData
from .environment import CurrentData
from .vessel import VesselProfile
from .cost import calculate_edge_cost, CostWeights


def calculate_route_metrics(
    path: list[int],
    grid: MarineGrid,
    bathymetry: BathymetryData,
    currents: CurrentData,
    constraints,
    vessel: VesselProfile,
    weights: CostWeights | None = None,
) -> dict[str, Any]:
    """
    Calculate physical and operational metrics for a completed route.

    The path is a sequence of grid node IDs.
    """

    if not path:
        return {
            "distance_km": 0.0,
            "travel_time_h": 0.0,
            "fuel_l": 0.0,
            "min_depth_m": None,
            "max_depth_m": None,
            "average_depth_m": None,
            "average_current_ms": None,
            "total_cost": 0.0,
        }

    if len(path) == 1:
        row, col = grid.row_col(path[0])
        depth = float(bathymetry.depth_m[row, col])

        return {
            "distance_km": 0.0,
            "travel_time_h": 0.0,
            "fuel_l": 0.0,
            "min_depth_m": depth,
            "max_depth_m": depth,
            "average_depth_m": depth,
            "average_current_ms": 0.0,
            "total_cost": 0.0,
        }

    total_distance_km = 0.0
    total_travel_time_h = 0.0
    total_fuel_l = 0.0
    total_cost = 0.0

    depths: list[float] = []
    current_speeds: list[float] = []

    # Collect depth/current information for every path node.
    for node_id in path:
        row, col = grid.row_col(node_id)

        depth = float(
            bathymetry.depth_m[row, col]
        )

        depths.append(depth)

        # current_speed_ms was removed from CurrentData to save ~31 MB.
        # Derive the scalar magnitude from the retained u/v components.
        if currents.current_data_available[row, col]:
            current_speed = math.hypot(
                float(currents.current_u_ms[row, col]),
                float(currents.current_v_ms[row, col]),
            )
            current_speeds.append(current_speed)

    # Calculate every route edge.
    for source_node, target_node in zip(
        path[:-1],
        path[1:],
    ):

        source_row, source_col = (
            grid.row_col(source_node)
        )

        target_row, target_col = (
            grid.row_col(target_node)
        )

        # Determine direction from grid neighbors.
        direction_deg = None

        for neighbor_node, candidate_direction in (
            grid.get_navigable_neighbors(
                source_node
            )
        ):
            if neighbor_node == target_node:
                direction_deg = candidate_direction
                break

        if direction_deg is None:
            raise ValueError(
                "Path contains a non-adjacent edge: "
                f"{source_node} -> {target_node}"
            )

        edge = calculate_edge_cost(
            source_node=source_node,
            target_node=target_node,
            route_direction_deg=direction_deg,
            grid=grid,
            bathymetry=bathymetry,
            currents=currents,
            constraints=constraints,
            vessel=vessel,
            weights=weights,
        )

        if not math.isfinite(edge.total_cost):
            raise ValueError(
                "Path contains an invalid/blocked edge: "
                f"{source_node} -> {target_node}"
            )

        total_distance_km += edge.distance_km
        total_travel_time_h += edge.travel_time_h
        total_fuel_l += edge.fuel_l
        total_cost += edge.total_cost

    return {
        "distance_km": total_distance_km,
        "travel_time_h": total_travel_time_h,
        "fuel_l": total_fuel_l,
        "min_depth_m": min(depths),
        "max_depth_m": max(depths),
        "average_depth_m": sum(depths) / len(depths),
        "average_current_ms": (
            sum(current_speeds)
            / len(current_speeds)
            if current_speeds
            else None
        ),
        "total_cost": total_cost,
    }


def path_to_geojson(
    path: list[int],
    grid: MarineGrid,
) -> dict[str, Any]:
    """
    Convert a grid-node path into a GeoJSON LineString.

    GeoJSON coordinate order is:
        [longitude, latitude]
    """

    if not path:
        return {
            "type": "LineString",
            "coordinates": [],
        }

    coordinates = []

    for node_id in path:

        latitude, longitude = (
            grid.node_to_latlon(node_id)
        )

        coordinates.append(
            [
                float(longitude),
                float(latitude),
            ]
        )

    return {
        "type": "LineString",
        "coordinates": coordinates,
    }


def route_to_geojson_feature(
    path: list[int],
    grid: MarineGrid,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Convert a route into a GeoJSON Feature.
    """

    return {
        "type": "Feature",
        "properties": properties or {},
        "geometry": path_to_geojson(
            path=path,
            grid=grid,
        ),
    }