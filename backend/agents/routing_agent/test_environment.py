import sys
from pathlib import Path

import numpy as np

from backend.agents.routing_agent.routing.bathymetry import (
    load_bathymetry,
)

from backend.agents.routing_agent.routing.environment import (
    load_currents,
    validate_alignment,
    current_along_direction,
    effective_speed_mps,
)

from backend.agents.routing_agent.routing.vessel import (
    VesselProfile,
    knots_to_mps,
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
    print("ENVIRONMENT / CURRENT TEST")
    print("=" * 60)

    # --------------------------------------------------------
    # Check files
    # --------------------------------------------------------

    if not bathymetry_file.exists():

        print(
            "\n❌ Bathymetry file not found:"
        )

        print(bathymetry_file)

        sys.exit(1)

    if not current_file.exists():

        print(
            "\n❌ Current file not found:"
        )

        print(current_file)

        sys.exit(1)

    # --------------------------------------------------------
    # Load bathymetry
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
    # Load currents
    # --------------------------------------------------------

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
    # Current information
    # --------------------------------------------------------

    print(
        "\nCurrent grid:"
    )

    print(
        "  Rows:",
        currents.n_rows
    )

    print(
        "  Columns:",
        currents.n_cols
    )

    print(
        "  Shape:",
        currents.shape
    )

    print(
        "  Cells with data:",
        currents.available_cells
    )

    print(
        "  Source:",
        currents.source
    )

    print(
        "  Timestamp:",
        currents.timestamp
    )

    # --------------------------------------------------------
    # Validate alignment
    # --------------------------------------------------------

    print(
        "\nChecking grid alignment..."
    )

    validate_alignment(
        bathymetry.latitudes,
        bathymetry.longitudes,
        currents,
    )

    print(
        "✓ Bathymetry/current grids aligned"
    )

    # --------------------------------------------------------
    # Check current values
    # --------------------------------------------------------

    valid = (
        currents.current_data_available
        & np.isfinite(
            currents.current_u_ms
        )
        & np.isfinite(
            currents.current_v_ms
        )
    )

    if not np.any(valid):

        print(
            "\n❌ No valid current cells found."
        )

        sys.exit(1)

    u_valid = currents.current_u_ms[valid]
    v_valid = currents.current_v_ms[valid]

    # current_speed_ms is no longer stored (saves 31 MB).
    # Derive speed from u/v for display purposes.
    speed_valid = np.sqrt(u_valid**2 + v_valid**2)

    print(
        "\nCurrent statistics:"
    )

    print(
        "  U min/max:",
        float(u_valid.min()),
        "/",
        float(u_valid.max()),
        "m/s",
    )

    print(
        "  V min/max:",
        float(v_valid.min()),
        "/",
        float(v_valid.max()),
        "m/s",
    )

    print(
        "  Speed min/max (derived):",
        float(speed_valid.min()),
        "/",
        float(speed_valid.max()),
        "m/s",
    )

    # --------------------------------------------------------
    # Test along-route current
    # --------------------------------------------------------

    print(
        "\nAlong-route current tests:"
    )

    # Eastward current + eastward vessel movement
    following = current_along_direction(
        u_ms=1.0,
        v_ms=0.0,
        direction_deg=90.0,
    )

    print(
        "  East current + East movement:",
        following,
        "m/s",
    )

    # Eastward current + westward vessel movement
    opposing = current_along_direction(
        u_ms=1.0,
        v_ms=0.0,
        direction_deg=270.0,
    )

    print(
        "  East current + West movement:",
        opposing,
        "m/s",
    )

    assert following > 0

    assert opposing < 0

    # --------------------------------------------------------
    # Test effective speed
    # --------------------------------------------------------

    vessel = VesselProfile()

    vessel_speed = knots_to_mps(
        vessel.cruising_speed_knots
    )

    faster = effective_speed_mps(
        vessel_speed,
        following,
    )

    slower = effective_speed_mps(
        vessel_speed,
        opposing,
    )

    print(
        "\nEffective-speed tests:"
    )

    print(
        "  Vessel speed:",
        vessel_speed,
        "m/s",
    )

    print(
        "  Following current:",
        faster,
        "m/s",
    )

    print(
        "  Opposing current:",
        slower,
        "m/s",
    )

    assert faster > vessel_speed

    assert slower < vessel_speed

    # --------------------------------------------------------
    # Final assertions
    # --------------------------------------------------------

    assert (
        currents.shape
        == bathymetry.navigable.shape
    )

    assert (
        currents.current_u_ms.shape
        == currents.current_v_ms.shape
    )

    # current_speed_ms and current_direction_deg are no longer stored
    # (they were unused by A* and have been removed to save 2 x 31 MB)
    assert (
        currents.current_data_available.shape
        == currents.current_u_ms.shape
    )

    print(
        "\n✓ ENVIRONMENT TEST PASSED"
    )


if __name__ == "__main__":
    main()