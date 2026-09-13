import sys
from pathlib import Path

import numpy as np

from backend.agents.routing_agent.routing.bathymetry import (
    load_bathymetry,
)

from backend.agents.routing_agent.routing.constraints import (
    build_constraint_mask,
    add_confirmed_restrictions,
    validate_constraint_mask,
)

from backend.agents.routing_agent.routing.vessel import (
    VesselProfile,
)


def main():

    bathymetry_file = Path(
        "backend/data/routing/grid/"
        "orca_west_coast_bathymetry_landmasked.nc"
    )

    print("=" * 60)
    print("CONSTRAINT TEST")
    print("=" * 60)

    if not bathymetry_file.exists():

        print(
            "\n❌ Bathymetry file not found:"
        )

        print(bathymetry_file)

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

    # --------------------------------------------------------
    # Build constraints
    # --------------------------------------------------------

    vessel = VesselProfile()

    print(
        "\nBuilding hard constraint mask..."
    )

    constraints = build_constraint_mask(
        bathymetry,
        vessel,
    )

    print(
        "✓ Constraint mask created"
    )

    print(
        "\nConstraint statistics:"
    )

    print(
        "  Grid shape:",
        constraints.shape
    )

    print(
        "  Blocked cells:",
        constraints.blocked_cells
    )

    print(
        "  Navigable cells:",
        constraints.navigable_cells
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    validate_constraint_mask(
        constraints
    )

    # --------------------------------------------------------
    # Test individual rules
    # --------------------------------------------------------

    print(
        "\nTesting hard-block rules..."
    )

    # Every original land cell must be blocked.

    land_cells = bathymetry.is_land

    assert np.all(
        constraints.blocked[land_cells]
    )

    print(
        "  ✓ Land cells blocked"
    )

    # Every non-water cell must be blocked.

    non_water = ~bathymetry.is_water

    assert np.all(
        constraints.blocked[non_water]
    )

    print(
        "  ✓ Non-water cells blocked"
    )

    # Every cell below the vessel's minimum depth
    # must be blocked.

    unsafe_depth = (
        bathymetry.depth_m
        < vessel.minimum_safe_depth_m
    )

    assert np.all(
        constraints.blocked[unsafe_depth]
    )

    print(
        "  ✓ Unsafe-depth cells blocked"
    )

    # Every original non-navigable cell must remain blocked.

    non_navigable = ~bathymetry.navigable

    assert np.all(
        constraints.blocked[non_navigable]
    )

    print(
        "  ✓ Original non-navigable cells blocked"
    )

    # --------------------------------------------------------
    # Test confirmed restriction layer
    # --------------------------------------------------------

    print(
        "\nTesting confirmed restrictions..."
    )

    prohibited = np.zeros(
        constraints.shape,
        dtype=bool,
    )

    restricted = np.zeros(
        constraints.shape,
        dtype=bool,
    )

    # Pick a cell that is currently navigable.
    # This lets us verify that adding a confirmed
    # restriction actually blocks it.

    navigable_positions = np.argwhere(
        ~constraints.blocked
    )

    if len(navigable_positions) == 0:

        print(
            "\n❌ No navigable cells available "
            "for restriction test."
        )

        sys.exit(1)

    test_row = int(
        navigable_positions[0, 0]
    )

    test_col = int(
        navigable_positions[0, 1]
    )

    prohibited[
        test_row,
        test_col
    ] = True

    updated = add_confirmed_restrictions(
        constraints,
        prohibited_mask=prohibited,
        restricted_mask=restricted,
    )

    assert updated.is_blocked(
        test_row,
        test_col
    )

    print(
        "  ✓ Confirmed prohibited cell blocked"
    )

    # --------------------------------------------------------
    # Verify original constraint object wasn't mutated
    # --------------------------------------------------------

    assert not constraints.is_blocked(
        test_row,
        test_col
    )

    print(
        "  ✓ Original constraint mask unchanged"
    )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print(
        "\n✓ CONSTRAINT TEST PASSED"
    )


if __name__ == "__main__":
    main()