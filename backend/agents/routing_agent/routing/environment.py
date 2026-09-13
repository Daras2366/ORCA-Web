from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np
import xarray as xr


@dataclass
class CurrentData:
    """
    Ocean-current state aligned to the ORCA routing grid.

    U and V are horizontal current components in m/s.
    """

    latitudes: np.ndarray
    longitudes: np.ndarray

    current_u_ms: np.ndarray
    current_v_ms: np.ndarray

    current_speed_ms: np.ndarray
    current_direction_deg: np.ndarray

    current_data_available: np.ndarray

    source: str = "INCOIS RSMC HYCOM"

    # Optional timestamp / metadata.
    timestamp: str | None = None

    def __post_init__(self):
        self.latitudes = np.asarray(
            self.latitudes
        )

        self.longitudes = np.asarray(
            self.longitudes
        )

        self.current_u_ms = np.asarray(
            self.current_u_ms,
            dtype=np.float32,
        )

        self.current_v_ms = np.asarray(
            self.current_v_ms,
            dtype=np.float32,
        )

        self.current_speed_ms = np.asarray(
            self.current_speed_ms,
            dtype=np.float32,
        )

        self.current_direction_deg = np.asarray(
            self.current_direction_deg,
            dtype=np.float32,
        )

        self.current_data_available = np.asarray(
            self.current_data_available,
            dtype=bool,
        )

        shape = self.current_u_ms.shape

        if len(shape) != 2:
            raise ValueError(
                "Current arrays must be 2-dimensional."
            )

        arrays = {
            "current_v_ms": self.current_v_ms,
            "current_speed_ms": self.current_speed_ms,
            "current_direction_deg": self.current_direction_deg,
            "current_data_available": (
                self.current_data_available
            ),
        }

        for name, array in arrays.items():
            if array.shape != shape:
                raise ValueError(
                    f"{name} has shape {array.shape}, "
                    f"expected {shape}."
                )

        if len(self.latitudes) != shape[0]:
            raise ValueError(
                "Latitude coordinate length does not "
                "match current grid rows."
            )

        if len(self.longitudes) != shape[1]:
            raise ValueError(
                "Longitude coordinate length does not "
                "match current grid columns."
            )

    @property
    def shape(self) -> Tuple[int, int]:
        return self.current_u_ms.shape

    @property
    def n_rows(self) -> int:
        return self.shape[0]

    @property
    def n_cols(self) -> int:
        return self.shape[1]

    @property
    def available_cells(self) -> int:
        return int(
            self.current_data_available.sum()
        )


def _find_variable(
    ds: xr.Dataset,
    candidates: list[str],
    required: bool = True,
):
    """
    Find the first matching variable in an xarray dataset.

    Allows us to tolerate small naming differences in the
    processed current file without changing the routing logic.
    """

    for name in candidates:
        if name in ds.data_vars:
            return ds[name]

    if required:
        raise ValueError(
            "Could not find any of the expected variables: "
            + ", ".join(candidates)
        )

    return None


def load_currents(
    filepath: str | Path,
) -> CurrentData:
    """
    Load the processed ORCA current dataset.

    The expected current information is:

        U component
        V component
        current speed
        current direction
        data availability
    """

    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(
            f"Current dataset not found: {filepath}"
        )

    ds = xr.open_dataset(filepath)

    try:
        # ----------------------------------------------------
        # Coordinates
        # ----------------------------------------------------

        if "lat" not in ds.coords:
            raise ValueError(
                "Current dataset is missing 'lat' coordinate."
            )

        if "lon" not in ds.coords:
            raise ValueError(
                "Current dataset is missing 'lon' coordinate."
            )

        latitudes = ds["lat"].values
        longitudes = ds["lon"].values

        # ----------------------------------------------------
        # Current variables
        # ----------------------------------------------------

        u = _find_variable(
            ds,
            [
                "current_u_ms",
                "u_current_ms",
                "u_ms",
                "current_u",
            ],
        )

        v = _find_variable(
            ds,
            [
                "current_v_ms",
                "v_current_ms",
                "v_ms",
                "current_v",
            ],
        )

        speed = _find_variable(
            ds,
            [
                "current_speed_ms",
                "current_speed",
                "speed_ms",
            ],
            required=False,
        )

        direction = _find_variable(
            ds,
            [
                "current_direction_deg",
                "current_direction",
                "direction_deg",
            ],
            required=False,
        )

        availability = _find_variable(
            ds,
            [
                "current_data_available",
                "data_available",
            ],
            required=False,
        )

        # ----------------------------------------------------
        # Convert to NumPy
        # ----------------------------------------------------

        u_values = u.values.astype(
            np.float32
        )

        v_values = v.values.astype(
            np.float32
        )

        # ----------------------------------------------------
        # Derive speed if not stored
        # ----------------------------------------------------

        if speed is None:
            speed_values = np.sqrt(
                u_values ** 2
                + v_values ** 2
            ).astype(np.float32)

        else:
            speed_values = speed.values.astype(
                np.float32
            )

        # ----------------------------------------------------
        # Derive direction if not stored
        # ----------------------------------------------------

        if direction is None:
            direction_values = (
                np.degrees(
                    np.arctan2(
                        u_values,
                        v_values,
                    )
                )
                + 360.0
            ) % 360.0

            direction_values = (
                direction_values.astype(np.float32)
            )

        else:
            direction_values = (
                direction.values.astype(np.float32)
            )

        # ----------------------------------------------------
        # Derive availability if not stored
        # ----------------------------------------------------

        if availability is None:
            availability_values = (
                np.isfinite(u_values)
                & np.isfinite(v_values)
            )

        else:
            availability_values = (
                availability.values.astype(bool)
            )

        # ----------------------------------------------------
        # Timestamp
        # ----------------------------------------------------

        timestamp = None

        for key in [
            "time",
            "valid_time",
            "forecast_time",
            "datetime",
        ]:
            if key in ds.coords:
                values = ds[key].values

                if np.size(values) > 0:
                    timestamp = str(
                        np.ravel(values)[0]
                    )

                    break

        return CurrentData(
            latitudes=latitudes,
            longitudes=longitudes,

            current_u_ms=u_values,
            current_v_ms=v_values,

            current_speed_ms=speed_values,
            current_direction_deg=direction_values,

            current_data_available=(
                availability_values
            ),

            timestamp=timestamp,
        )

    finally:
        ds.close()


def validate_alignment(
    bathymetry_latitudes: np.ndarray,
    bathymetry_longitudes: np.ndarray,
    currents: CurrentData,
) -> None:
    """
    Verify that the current grid is spatially aligned
    with the bathymetry grid.

    Routing must not combine arrays from different
    spatial grids.
    """

    if (
        len(bathymetry_latitudes)
        != len(currents.latitudes)
    ):
        raise ValueError(
            "Bathymetry and current grids have "
            "different numbers of latitude cells."
        )

    if (
        len(bathymetry_longitudes)
        != len(currents.longitudes)
    ):
        raise ValueError(
            "Bathymetry and current grids have "
            "different numbers of longitude cells."
        )

    if not np.allclose(
        bathymetry_latitudes,
        currents.latitudes,
        rtol=0.0,
        atol=1e-10,
    ):
        raise ValueError(
            "Bathymetry and current latitude grids "
            "are not aligned."
        )

    if not np.allclose(
        bathymetry_longitudes,
        currents.longitudes,
        rtol=0.0,
        atol=1e-10,
    ):
        raise ValueError(
            "Bathymetry and current longitude grids "
            "are not aligned."
        )


def current_along_direction(
    u_ms: float,
    v_ms: float,
    direction_deg: float,
) -> float:
    """
    Calculate current velocity along a route direction.

    Positive:
        following / assisting current

    Negative:
        opposing current

    Direction convention:
        0°   = North
        90°  = East
        180° = South
        270° = West
    """

    direction_rad = np.radians(
        direction_deg
    )

    direction_x = np.sin(
        direction_rad
    )

    direction_y = np.cos(
        direction_rad
    )

    return float(
        u_ms * direction_x
        + v_ms * direction_y
    )


def effective_speed_mps(
    vessel_speed_mps: float,
    along_current_ms: float,
) -> float:
    """
    Calculate vessel speed relative to the ground.

    This is the initial prototype formulation:

        effective speed =
            vessel speed + along-route current

    A minimum positive value is enforced so that a strong
    opposing current does not produce zero/negative travel
    speed.
    """

    return max(
        0.1,
        vessel_speed_mps + along_current_ms,
    )