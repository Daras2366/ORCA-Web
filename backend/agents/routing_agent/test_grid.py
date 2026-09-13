import numpy as np

from backend.agents.routing_agent.routing.grid import MarineGrid


def main():

    # Small synthetic grid for testing.
    #
    # 5 x 5 cells
    # Everything navigable initially.

    latitudes = np.array([
        10.0,
        10.01,
        10.02,
        10.03,
        10.04,
    ])

    longitudes = np.array([
        70.0,
        70.01,
        70.02,
        70.03,
        70.04,
    ])

    navigable = np.ones(
        (5, 5),
        dtype=bool,
    )

    depth_m = np.full(
        (5, 5),
        20.0,
        dtype=np.float32,
    )

    grid = MarineGrid(
        latitudes=latitudes,
        longitudes=longitudes,
        navigable=navigable,
        depth_m=depth_m,
    )

    print("=" * 60)
    print("GRID TEST")
    print("=" * 60)

    print("Rows:", grid.n_rows)
    print("Columns:", grid.n_cols)
    print("Total nodes:", grid.n_nodes)
    print("Navigable nodes:", grid.navigable_nodes)

    # Test indexing

    node = grid.flat_index(2, 2)

    print("\nCenter node:", node)
    print("Row/Col:", grid.row_col(node))
    print("Lat/Lon:", grid.node_to_latlon(node))

    # Test neighbors

    neighbors = grid.get_navigable_neighbors(node)

    print("\nNeighbors:", len(neighbors))

    for neighbor_id, direction in neighbors:
        print(
            f"  {neighbor_id} -> {direction}°"
        )

    # Test nearest-node lookup

    nearest = grid.nearest_node(
        latitude=10.021,
        longitude=70.021,
    )

    print("\nNearest node:", nearest)
    print("Nearest coordinates:", grid.node_to_latlon(nearest))

    # Assertions

    assert grid.n_rows == 5
    assert grid.n_cols == 5
    assert grid.n_nodes == 25
    assert grid.navigable_nodes == 25

    assert grid.is_valid_node(node)

    assert len(neighbors) == 8

    assert nearest == grid.flat_index(2, 2)

    print("\n✓ GRID TEST PASSED")


if __name__ == "__main__":
    main()