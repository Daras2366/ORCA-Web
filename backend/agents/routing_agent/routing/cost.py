from dataclasses import dataclass

import numpy as np

from .bathymetry import BathymetryData
from .constraints import ConstraintMask
from .environment import CurrentData, current_along_direction
from .grid import MarineGrid
from .vessel import VesselProfile, knots_to_mps


EARTH_RADIUS_KM = 6371.0088


@dataclass
class CostWeights:
    """
    Weights controlling the routing objective.

    These values are normalized internally before being
    combined into the final edge cost.
    """

    distance: float = 0.30
    travel_time: float = 0.25
    fuel: float = 0.20
    detour: float = 0.10
    depth: float = 0.10
    current: float = 0.05

    def __post_init__(self):

        values = [
            self.distance,
            self.travel_time,
            self.fuel,
            self.detour,
            self.depth,
            self.current,
        ]

        if any(value < 0 for value in values):
            raise ValueError(
                "Cost weights cannot be negative."
            )

        total = sum(values)

        if total <= 0:
            raise ValueError(
                "At least one cost weight must be positive."
            )

        # Normalize so the weights sum to 1.

        self.distance /= total
        self.travel_time /= total
        self.fuel /= total
        self.detour /= total
        self.depth /= total
        self.current /= total


@dataclass
class EdgeCost:
    """
    Detailed cost information for one movement between
    neighboring routing cells.
    """

    distance_km: float

    travel_time_h: float

    fuel_l: float

    depth_penalty: float

    current_penalty: float

    detour_penalty: float

    total_cost: float

    along_current_ms: float

    effective_speed_mps: float


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Great-circle distance between two geographic coordinates.

    The routing documentation uses the Earth radius:
        6371.0088 km
    """

    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)

    delta_lat = np.radians(
        lat2 - lat1
    )

    delta_lon = np.radians(
        lon2 - lon1
    )

    a = (
        np.sin(delta_lat / 2.0) ** 2
        + np.cos(lat1_rad)
        * np.cos(lat2_rad)
        * np.sin(delta_lon / 2.0) ** 2
    )

    a = min(
        1.0,
        max(0.0, float(a)),
    )

    return float(
        2.0
        * EARTH_RADIUS_KM
        * np.arcsin(np.sqrt(a))
    )


def depth_penalty(
    depth_m: float,
    vessel: VesselProfile,
) -> float:
    """
    Soft depth penalty.

    Hard depth violations should already be removed by
    constraints.py.

    Deeper water therefore receives a lower penalty,
    while water close to the minimum safe depth receives
    a larger penalty.

    The result is normalized to approximately [0, 1].
    """

    minimum_depth = (
        vessel.minimum_safe_depth_m
    )

    if depth_m < minimum_depth:
        return float("inf")

    # Give progressively safer/deeper water lower penalty.

    safety_margin = (
        depth_m - minimum_depth
    )

    reference_margin = max(
        10.0,
        minimum_depth,
    )

    penalty = 1.0 / (
        1.0
        + safety_margin / reference_margin
    )

    return float(
        np.clip(
            penalty,
            0.0,
            1.0,
        )
    )


def current_penalty(
    along_current_ms: float,
    reference_current_ms: float = 0.5,
) -> float:
    """
    Convert along-route current into a normalized penalty.

    Following current:
        negative / low penalty

    Opposing current:
        positive / higher penalty

    Cross-current:
        approximately neutral.
    """

    if not np.isfinite(
        along_current_ms
    ):
        return 0.5

    normalized = (
        -along_current_ms
        / max(
            reference_current_ms,
            1e-6,
        )
    )

    # Convert from roughly [-1, 1] to [0, 1].

    penalty = (
        normalized + 1.0
    ) / 2.0

    return float(
        np.clip(
            penalty,
            0.0,
            1.0,
        )
    )


def calculate_edge_cost(
    source_node: int,
    target_node: int,
    route_direction_deg: float,
    grid: MarineGrid,
    bathymetry: BathymetryData,
    currents: CurrentData,
    constraints: ConstraintMask,
    vessel: VesselProfile,
    weights: CostWeights | None = None,
    reference_distance_km: float = 10.0,
) -> EdgeCost:
    """
    Calculate the cost of moving from one grid node to
    a neighboring node.

    A hard-blocked source or target produces infinite cost.

    Valid edges receive a weighted soft cost.
    """

    if weights is None:
        weights = CostWeights()

    # --------------------------------------------------------
    # Validate nodes
    # --------------------------------------------------------

    source_row, source_col = grid.row_col(
        source_node
    )

    target_row, target_col = grid.row_col(
        target_node
    )

    if constraints.is_blocked(
        source_row,
        source_col,
    ):
        return EdgeCost(
            distance_km=float("inf"),
            travel_time_h=float("inf"),
            fuel_l=float("inf"),
            depth_penalty=float("inf"),
            current_penalty=float("inf"),
            detour_penalty=float("inf"),
            total_cost=float("inf"),
            along_current_ms=0.0,
            effective_speed_mps=0.0,
        )

    if constraints.is_blocked(
        target_row,
        target_col,
    ):
        return EdgeCost(
            distance_km=float("inf"),
            travel_time_h=float("inf"),
            fuel_l=float("inf"),
            depth_penalty=float("inf"),
            current_penalty=float("inf"),
            detour_penalty=float("inf"),
            total_cost=float("inf"),
            along_current_ms=0.0,
            effective_speed_mps=0.0,
        )

    # --------------------------------------------------------
    # Coordinates
    # --------------------------------------------------------

    source_lat, source_lon = (
        grid.node_to_latlon(source_node)
    )

    target_lat, target_lon = (
        grid.node_to_latlon(target_node)
    )

    # --------------------------------------------------------
    # Geographic distance
    # --------------------------------------------------------

    distance_km = haversine_distance_km(
        source_lat,
        source_lon,
        target_lat,
        target_lon,
    )

    # --------------------------------------------------------
    # Target-cell depth
    # --------------------------------------------------------

    depth_m = float(
        bathymetry.depth_m[
            target_row,
            target_col,
        ]
    )

    depth_cost = depth_penalty(
        depth_m,
        vessel,
    )

    if not np.isfinite(
        depth_cost
    ):
        return EdgeCost(
            distance_km=distance_km,
            travel_time_h=float("inf"),
            fuel_l=float("inf"),
            depth_penalty=float("inf"),
            current_penalty=float("inf"),
            detour_penalty=float("inf"),
            total_cost=float("inf"),
            along_current_ms=0.0,
            effective_speed_mps=0.0,
        )

    # --------------------------------------------------------
    # Current
    # --------------------------------------------------------

    if currents.current_data_available[
        target_row,
        target_col,
    ]:

        u_ms = float(
            currents.current_u_ms[
                target_row,
                target_col,
            ]
        )

        v_ms = float(
            currents.current_v_ms[
                target_row,
                target_col,
            ]
        )

        along_current = (
            current_along_direction(
                u_ms,
                v_ms,
                route_direction_deg,
            )
        )

    else:

        # Missing current data does not create a hard block.
        # It creates a neutral uncertainty/fallback value.

        along_current = 0.0

    # --------------------------------------------------------
    # Effective vessel speed
    # --------------------------------------------------------

    vessel_speed_mps = knots_to_mps(
        vessel.cruising_speed_knots
    )

    effective_speed = max(
        0.1,
        vessel_speed_mps
        + along_current,
    )

    # --------------------------------------------------------
    # Travel time
    # --------------------------------------------------------

    distance_m = (
        distance_km * 1000.0
    )

    travel_time_h = (
        distance_m
        / effective_speed
        / 3600.0
    )

    # --------------------------------------------------------
    # Fuel estimate
    # --------------------------------------------------------

    fuel_l = (
        travel_time_h
        * vessel.fuel_burn_lph
    )

    # --------------------------------------------------------
    # Soft current penalty
    # --------------------------------------------------------

    current_cost = current_penalty(
        along_current
    )

    # --------------------------------------------------------
    # Distance normalization
    # --------------------------------------------------------

    distance_cost = (
        distance_km
        / max(
            reference_distance_km,
            1e-6,
        )
    )

    distance_cost = float(
        np.clip(
            distance_cost,
            0.0,
            1.0,
        )
    )

    # --------------------------------------------------------
    # Time normalization
    # --------------------------------------------------------

    time_reference_h = (
        reference_distance_km
        * 1000.0
        / vessel_speed_mps
        / 3600.0
    )

    time_cost = (
        travel_time_h
        / max(
            time_reference_h,
            1e-6,
        )
    )

    time_cost = float(
        np.clip(
            time_cost,
            0.0,
            1.0,
        )
    )

    # --------------------------------------------------------
    # Fuel normalization
    # --------------------------------------------------------

    fuel_reference_l = (
        time_reference_h
        * vessel.fuel_burn_lph
    )

    fuel_cost = (
        fuel_l
        / max(
            fuel_reference_l,
            1e-6,
        )
    )

    fuel_cost = float(
        np.clip(
            fuel_cost,
            0.0,
            1.0,
        )
    )

    # --------------------------------------------------------
    # Detour
    # --------------------------------------------------------

    # For an individual edge there is no complete route
    # available yet, so detour is represented as neutral.
    #
    # The complete-route metric is calculated later in
    # metrics.py.

    detour_cost = 0.0

    # --------------------------------------------------------
    # Weighted total
    # --------------------------------------------------------

    total_cost = (
        weights.distance
        * distance_cost

        + weights.travel_time
        * time_cost

        + weights.fuel
        * fuel_cost

        + weights.detour
        * detour_cost

        + weights.depth
        * depth_cost

        + weights.current
        * current_cost
    )

    return EdgeCost(
        distance_km=distance_km,
        travel_time_h=travel_time_h,
        fuel_l=fuel_l,
        depth_penalty=depth_cost,
        current_penalty=current_cost,
        detour_penalty=detour_cost,
        total_cost=float(total_cost),
        along_current_ms=along_current,
        effective_speed_mps=effective_speed,
    )