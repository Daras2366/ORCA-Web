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

    Memory-optimised layout
    -----------------------
    current_speed_ms and current_direction_deg are not stored as
    resident 2-D arrays.  The A* cost function only reads:
      - current_u_ms          (for current_along_direction)
      - current_v_ms          (for current_along_direction)
      - current_data_available (availability mask)

    Removing the two derived scalar-field arrays saves 2 x 31.31 MB
    = 62.62 MB of resident RAM (plus the same again as transient
    allocation during load_currents).
    """

    latitudes: np.ndarray
    longitudes: np.ndarray

    current_u_ms: np.ndarray
    current_v_ms: np.ndarray

    current_data_available: np.ndarray

    source: str = "INCOIS RSMC HYCOM"

    # Optional timestamp / metadata.
    timestamp: str | None = None

    def __post_init__(self):
        # np.asarray with matching dtype returns the same array object
        # (no copy) when the input is already a C-contiguous numpy array.
        if not isinstance(self.latitudes, np.ndarray):
            self.latitudes = np.asarray(self.latitudes, dtype=np.float32)
        if not isinstance(self.longitudes, np.ndarray):
            self.longitudes = np.asarray(self.longitudes, dtype=np.float32)

        self.current_u_ms = np.asarray(
            self.current_u_ms,
            dtype=np.float32,
        )

        self.current_v_ms = np.asarray(
            self.current_v_ms,
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

        for name, array in {
            "current_v_ms": self.current_v_ms,
            "current_data_available": self.current_data_available,
        }.items():
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
    latitudes: np.ndarray | None = None,
    longitudes: np.ndarray | None = None,
) -> CurrentData:
    """
    Load the processed ORCA current dataset.

    Only the variables needed by A* are loaded:
        - U component   (current_u_ms)
        - V component   (current_v_ms)
        - availability  (current_data_available)

    current_speed_ms and current_direction_deg are skipped entirely
    — the cost function derives the along-route component directly
    from U/V, so the stored speed/direction arrays are redundant.
    Skipping them saves 2 x 31.31 MB = 62.62 MB resident RAM.

    Memory strategy
    ---------------
    Variables are extracted sequentially so that at any moment
    only one (raw xarray array + one numpy conversion) is live,
    rather than all variables simultaneously.

    ``np.asarray(..., dtype=T)`` is used instead of ``.astype(T)``
    to avoid allocating a duplicate array when the on-disk dtype
    already matches the target (float32/bool here).  np.asarray
    returns the original array unchanged when dtype/layout match;
    .astype always creates a fresh copy.

    Parameters
    ----------
    filepath:
        Path to the current NetCDF file.
    latitudes:
        Optional pre-loaded latitude array to avoid duplication.
        If provided, will be used instead of loading from file.
    longitudes:
        Optional pre-loaded longitude array to avoid duplication.
        If provided, will be used instead of loading from file.
    """

    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(
            f"Current dataset not found: {filepath}"
        )

    ds = xr.open_dataset(filepath)

    try:
        # ------------------------------------------------------------------
        # Coordinates
        # ------------------------------------------------------------------

        if latitudes is None or longitudes is None:
            if "lat" not in ds.coords:
                raise ValueError(
                    "Current dataset is missing 'lat' coordinate."
                )

            if "lon" not in ds.coords:
                raise ValueError(
                    "Current dataset is missing 'lon' coordinate."
                )

            latitudes = np.asarray(
                ds["lat"].values, dtype=np.float32
            )
            longitudes = np.asarray(
                ds["lon"].values, dtype=np.float32
            )
        else:
            # Ensure passed coordinates are float32 (no copy when already f32)
            latitudes = np.asarray(latitudes, dtype=np.float32)
            longitudes = np.asarray(longitudes, dtype=np.float32)

        # ------------------------------------------------------------------
        # U component — required
        # ------------------------------------------------------------------

        u_var = _find_variable(
            ds,
            [
                "current_u_ms",
                "u_current_ms",
                "u_ms",
                "current_u",
            ],
        )

        # np.asarray avoids a duplicate allocation when dtype already matches
        u_values = np.asarray(u_var.values, dtype=np.float32)
        del u_var  # free xarray reference immediately

        # ------------------------------------------------------------------
        # V component — required
        # ------------------------------------------------------------------

        v_var = _find_variable(
            ds,
            [
                "current_v_ms",
                "v_current_ms",
                "v_ms",
                "current_v",
            ],
        )

        v_values = np.asarray(v_var.values, dtype=np.float32)
        del v_var

        # ------------------------------------------------------------------
        # Data availability — optional (derived from u/v if absent)
        # ------------------------------------------------------------------

        availability_var = _find_variable(
            ds,
            [
                "current_data_available",
                "data_available",
            ],
            required=False,
        )

        if availability_var is not None:
            availability_values = np.asarray(
                availability_var.values, dtype=bool
            )
            del availability_var
        else:
            # Derive: a cell has data where both u and v are finite.
            availability_values = (
                np.isfinite(u_values)
                & np.isfinite(v_values)
            )

        # ------------------------------------------------------------------
        # Timestamp (metadata only, negligible cost)
        # ------------------------------------------------------------------

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

        # NOTE: current_speed_ms and current_direction_deg are NOT loaded.
        # cost.py computes the along-route current directly from u/v:
        #   along = u * sin(dir_rad) + v * cos(dir_rad)
        # Storing speed/direction as resident arrays wastes 2 x 31 MB.

    finally:
        ds.close()

    return CurrentData(
        latitudes=latitudes,
        longitudes=longitudes,

        current_u_ms=u_values,
        current_v_ms=v_values,

        current_data_available=availability_values,

        timestamp=timestamp,
    )


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
        0   = North
        90  = East
        180 = South
        270 = West
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