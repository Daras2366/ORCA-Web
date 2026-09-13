import sys
from pathlib import Path

import numpy as np

from backend.agents.routing_agent.routing.bathymetry import (
    load_bathymetry,
)

from backend.agents.routing_agent.routing.environment import (
    load_currents,
)

from backend.agents.routing_agent.routing.grid import (
    MarineGrid,
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
    haversine_distance_km,
)


def main():

    bathymetry_file = Path(
        "backend/data/routing/grid/"
        "orca_west_coast_bathymetry_landmasked.nc"
    )

    current_file = Path(
        "backend/data/routing/environmental/"
        "orca_west_coast_currents_departure.nc"
    )

    print("=" * 60)
    print("COST ENGINE TEST")
    print("=" * 60)

    if not bathymetry_file.exists():
        print(
            "\n❌ Bathymetry file not found."
        )
        sys.exit(1)

    if not current_file.exists():
        print(
            "\n❌ Current file not found."
        )
        sys.exit(1)

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    print(
        "\nLoading bathymetry..."
    )

    bathymetry = load_bathymetry(
        bathymetry_file
    )

    print(
        "✓ Bathymetry loaded"
    )

    print(
        "\nLoading currents..."
    )

    currents = load_currents(
        current_file
    )

    print(
        "✓ Currents loaded"
    )

    # --------------------------------------------------------
    # Build grid
    # --------------------------------------------------------

    grid = MarineGrid(
        latitudes=bathymetry.latitudes,
        longitudes=bathymetry.longitudes,
        navigable=bathymetry.navigable,
        depth_m=bathymetry.depth_m,
    )

    print(
        "\nGrid:",
        grid.n_rows,
        "×",
        grid.n_cols,
    )

    # --------------------------------------------------------
    # Constraints
    # --------------------------------------------------------

    vessel = VesselProfile()

    constraints = build_constraint_mask(
        bathymetry,
        vessel,
    )

    print(
        "✓ Constraints built"
    )

    # --------------------------------------------------------
    # Find two nearby navigable cells
    # --------------------------------------------------------

    navigable_positions = np.argwhere(
        ~constraints.blocked
    )

    if len(navigable_positions) < 2:

        print(
            "\n❌ Not enough navigable cells."
        )

        sys.exit(1)

    source_row = int(
        navigable_positions[0, 0]
    )

    source_col = int(
        navigable_positions[0, 1]
    )

    source_node = grid.flat_index(
        source_row,
        source_col,
    )

    # Search for a nearby navigable target.

    target_node = None

    for row, col in navigable_positions[1:]:
        row = int(row)
        col = int(col)

        distance_cells = (
            abs(row - source_row)
            + abs(col - source_col)
        )

        if distance_cells <= 3:
            target_node = grid.flat_index(
                row,
                col,
            )
            break

    if target_node is None:
        row = int(
            navigable_positions[1, 0]
        )

        col = int(
            navigable_positions[1, 1]
        )

        target_node = grid.flat_index(
            row,
            col,
        )

    print(
        "\nTest edge:"
    )

    print(
        "  Source node:",
        source_node,
    )

    print(
        "  Target node:",
        target_node,
    )

    print(
        "  Source:",
        grid.node_to_latlon(
            source_node
        ),
    )

    print(
        "  Target:",
        grid.node_to_latlon(
            target_node
        ),
    )

    # --------------------------------------------------------
    # Cost
    # --------------------------------------------------------

    weights = CostWeights()

    print(
        "\nCost weights:"
    )

    print(
        "  Distance:",
        weights.distance,
    )

    print(
        "  Travel time:",
        weights.travel_time,
    )

    print(
        "  Fuel:",
        weights.fuel,
    )

    print(
        "  Detour:",
        weights.detour,
    )

    print(
        "  Depth:",
        weights.depth,
    )

    print(
        "  Current:",
        weights.current,
    )

    # --------------------------------------------------------
    # Determine direction
    # --------------------------------------------------------

    source_lat, source_lon = (
        grid.node_to_latlon(source_node)
    )

    target_lat, target_lon = (
        grid.node_to_latlon(target_node)
    )

    delta_lon = (
        target_lon - source_lon
    )

    delta_lat = (
        target_lat - source_lat
    )

    direction_deg = (
        np.degrees(
            np.arctan2(
                delta_lon,
                delta_lat,
            )
        )
        + 360.0
    ) % 360.0

    edge = calculate_edge_cost(
        source_node=source_node,
        target_node=target_node,
        route_direction_deg=float(
            direction_deg
        ),
        grid=grid,
        bathymetry=bathymetry,
        currents=currents,
        constraints=constraints,
        vessel=vessel,
        weights=weights,
    )

    print(
        "\nEdge result:"
    )

    print(
        "  Distance:",
        edge.distance_km,
        "km",
    )

    print(
        "  Travel time:",
        edge.travel_time_h,
        "hours",
    )

    print(
        "  Fuel:",
        edge.fuel_l,
        "L",
    )

    print(
        "  Depth penalty:",
        edge.depth_penalty,
    )

    print(
        "  Current penalty:",
        edge.current_penalty,
    )

    print(
        "  Along current:",
        edge.along_current_ms,
        "m/s",
    )

    print(
        "  Effective speed:",
        edge.effective_speed_mps,
        "m/s",
    )

    print(
        "  Total cost:",
        edge.total_cost,
    )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    assert np.isfinite(
        edge.distance_km
    )

    assert edge.distance_km > 0

    assert np.isfinite(
        edge.travel_time_h
    )

    assert edge.travel_time_h > 0

    assert np.isfinite(
        edge.fuel_l
    )

    assert edge.fuel_l > 0

    assert np.isfinite(
        edge.total_cost
    )

    assert edge.total_cost >= 0

    # --------------------------------------------------------
    # Test haversine independently
    # --------------------------------------------------------

    distance = haversine_distance_km(
        0.0,
        0.0,
        0.0,
        1.0,
    )

    print(
        "\nHaversine test:"
    )

    print(
        "  1° longitude at equator:",
        distance,
        "km",
    )

    assert 110.0 < distance < 112.0

    print(
        "\n✓ COST ENGINE TEST PASSED"
    )


if __name__ == "__main__":
    main()