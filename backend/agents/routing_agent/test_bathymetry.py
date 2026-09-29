import sys
from pathlib import Path
import numpy as np

from backend.agents.routing_agent.routing.bathymetry import (
    load_bathymetry,
    apply_vessel_depth_constraint,
    bathymetry_summary,
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
    print("BATHYMETRY TEST")
    print("=" * 60)

    if not bathymetry_file.exists():

        print(
            "\n❌ Bathymetry file not found:"
        )

        print(
            bathymetry_file
        )

        print(
            "\nPlace the friend's processed "
            "NetCDF file at that location."
        )

        sys.exit(1)

    bathymetry = load_bathymetry(
        bathymetry_file
    )

    summary = bathymetry_summary(
        bathymetry
    )

    print(
        "\nGrid:"
    )

    print(
        "  Rows:",
        summary["rows"]
    )

    print(
        "  Columns:",
        summary["columns"]
    )

    print(
        "  Total cells:",
        summary["total_cells"]
    )

    print(
        "  Navigable cells:",
        summary["navigable_cells"]
    )

    print(
        "\nGeographic coverage:"
    )

    print(
        "  Latitude:",
        summary["latitude_min"],
        "→",
        summary["latitude_max"],
    )

    print(
        "  Longitude:",
        summary["longitude_min"],
        "→",
        summary["longitude_max"],
    )

    print(
        "\nBathymetry:"
    )

    print(
        "  Land cells:",
        summary["land_cells"]
    )

    print(
        "  Water cells:",
        summary["water_cells"]
    )

    print(
        "  Depth-blocked: (computed from depth_m on demand)"
    )

    print(
        "  Min depth:",
        summary["minimum_depth_m"],
    )

    print(
        "  Max depth:",
        summary["maximum_depth_m"],
    )

    # --------------------------------------------------------
    # Vessel test
    # --------------------------------------------------------

    vessel = VesselProfile()

    vessel_safe = apply_vessel_depth_constraint(
        bathymetry,
        vessel,
    )

    print(
        "\nVessel:"
    )

    print(
        "  Type:",
        vessel.vessel_type
    )

    print(
        "  Draft:",
        vessel.draft_m,
        "m"
    )

    print(
        "  UKC:",
        vessel.under_keel_clearance_m,
        "m"
    )

    print(
        "  Minimum safe depth:",
        vessel.minimum_safe_depth_m,
        "m"
    )

    print(
        "  Vessel-safe cells:",
        int(vessel_safe.sum())
    )

    # --------------------------------------------------------
    # Basic assertions
    # --------------------------------------------------------

    assert bathymetry.navigable.ndim == 2

    assert (
        bathymetry.depth_m.shape
        == bathymetry.navigable.shape
    )

    assert (
        bathymetry.is_land.shape
        == bathymetry.navigable.shape
    )

    assert (
        bathymetry.is_water.shape
        == bathymetry.navigable.shape
    )

    # elevation_m, depth_safe, depth_blocked no longer stored in BathymetryData
    # (they were unused by routing and have been removed to save ~47 MB)
    assert (
        vessel_safe.shape
        == bathymetry.navigable.shape
    )

    # Vessel-safe cells must always be
    # a subset of the original navigable cells.

    assert np.all(
        vessel_safe
        <= bathymetry.navigable
    )
    
    print(
        "\n✓ BATHYMETRY TEST PASSED"
    )


if __name__ == "__main__":
    main()