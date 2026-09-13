from dataclasses import dataclass


@dataclass
class VesselProfile:
    """
    Configuration for a vessel used by the ORCA navigation engine.
    """

    vessel_type: str = "demo_coastal_vessel"
    cruising_speed_knots: float = 12.0
    draft_m: float = 4.0
    under_keel_clearance_m: float = 1.0
    fuel_capacity_litres: float = 50000.0
    fuel_burn_lph: float = 120.0

    @property
    def minimum_safe_depth_m(self) -> float:
        """
        Minimum water depth required for this vessel.
        """
        return self.draft_m + self.under_keel_clearance_m


def knots_to_mps(knots: float) -> float:
    """
    Convert knots to metres per second.
    """
    return knots * 0.514444


def mps_to_knots(mps: float) -> float:
    """
    Convert metres per second to knots.
    """
    return mps / 0.514444