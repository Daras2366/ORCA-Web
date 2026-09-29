from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np
import xarray as xr


# ------------------------------------------------------------
# 8-neighbor movement model
# ------------------------------------------------------------

MOVEMENTS = [
    (-1, 0, 180.0),   # South
    (1, 0, 0.0),      # North
    (0, 1, 90.0),     # East
    (0, -1, 270.0),   # West
    (-1, 1, 135.0),   # Southeast
    (-1, -1, 225.0),  # Southwest
    (1, 1, 45.0),     # Northeast
    (1, -1, 315.0),   # Northwest
]


@dataclass
class MarineGrid:
    """
    Static spatial grid used by the ORCA navigation engine.

    The grid contains:
        - latitude coordinates
        - longitude coordinates
        - navigability mask
        - water depth

    Dynamic environmental information such as currents is
    handled separately by environment.py.
    """

    latitudes: np.ndarray
    longitudes: np.ndarray
    navigable: np.ndarray
    depth_m: np.ndarray

    def __post_init__(self):
        # Store references instead of copying to save memory
        # The arrays are already properly typed from BathymetryData
        if not isinstance(self.latitudes, np.ndarray):
            self.latitudes = np.asarray(self.latitudes, dtype=np.float32)
        if not isinstance(self.longitudes, np.ndarray):
            self.longitudes = np.asarray(self.longitudes, dtype=np.float32)
        if not isinstance(self.navigable, np.ndarray):
            self.navigable = np.asarray(self.navigable, dtype=bool)
        if not isinstance(self.depth_m, np.ndarray):
            self.depth_m = np.asarray(self.depth_m, dtype=np.float32)

        if self.navigable.ndim != 2:
            raise ValueError("navigable must be a 2D array")

        if self.depth_m.shape != self.navigable.shape:
            raise ValueError(
                "depth_m and navigable must have identical shapes"
            )

        if len(self.latitudes) != self.navigable.shape[0]:
            raise ValueError(
                "Latitude coordinate length does not match grid rows"
            )

        if len(self.longitudes) != self.navigable.shape[1]:
            raise ValueError(
                "Longitude coordinate length does not match grid columns"
            )

    # --------------------------------------------------------
    # Grid dimensions
    # --------------------------------------------------------

    @property
    def n_rows(self) -> int:
        return self.navigable.shape[0]

    @property
    def n_cols(self) -> int:
        return self.navigable.shape[1]

    @property
    def n_nodes(self) -> int:
        return self.n_rows * self.n_cols

    @property
    def navigable_nodes(self) -> int:
        return int(self.navigable.sum())

    # --------------------------------------------------------
    # Node indexing
    # --------------------------------------------------------

    def flat_index(self, row: int, col: int) -> int:
        """
        Convert 2D grid coordinates to a flat node ID.
        """
        if not (0 <= row < self.n_rows):
            raise IndexError("row outside grid")

        if not (0 <= col < self.n_cols):
            raise IndexError("column outside grid")

        return row * self.n_cols + col

    def row_col(self, node_id: int) -> Tuple[int, int]:
        """
        Convert flat node ID to 2D grid coordinates.
        """
        if node_id < 0 or node_id >= self.n_nodes:
            raise IndexError("node_id outside grid")

        return divmod(node_id, self.n_cols)

    # --------------------------------------------------------
    # Node validity
    # --------------------------------------------------------

    def is_valid_node(self, node_id: int) -> bool:
        """
        Return True if the node exists and is navigable.
        """
        if node_id < 0 or node_id >= self.n_nodes:
            return False

        row, col = self.row_col(node_id)

        return bool(self.navigable[row, col])

    # --------------------------------------------------------
    # Neighbor engine
    # --------------------------------------------------------

    def get_navigable_neighbors(
        self,
        node_id: int,
    ) -> List[Tuple[int, float]]:
        """
        Return navigable 8-connected neighbors.

        Returns:
            List of:
                (neighbor_node_id, direction_degrees)
        """

        if not self.is_valid_node(node_id):
            return []

        row, col = self.row_col(node_id)

        neighbors = []

        for dr, dc, direction in MOVEMENTS:

            nr = row + dr
            nc = col + dc

            if nr < 0 or nr >= self.n_rows:
                continue

            if nc < 0 or nc >= self.n_cols:
                continue

            if not self.navigable[nr, nc]:
                continue

            neighbor_id = self.flat_index(nr, nc)

            neighbors.append(
                (neighbor_id, direction)
            )

        return neighbors

    # --------------------------------------------------------
    # Geographic coordinate lookup
    # --------------------------------------------------------

    def node_to_latlon(
        self,
        node_id: int,
    ) -> Tuple[float, float]:
        """
        Convert node ID to (latitude, longitude).
        """

        row, col = self.row_col(node_id)

        return (
            float(self.latitudes[row]),
            float(self.longitudes[col]),
        )

    # --------------------------------------------------------
    # Nearest grid cell
    # --------------------------------------------------------

    def nearest_node(
        self,
        latitude: float,
        longitude: float,
        navigable_only: bool = True,
    ) -> int:
        """
        Find the nearest grid node to a latitude/longitude.

        For routing, navigable_only should normally remain True.
        """

        row = int(
            np.abs(self.latitudes - latitude).argmin()
        )

        col = int(
            np.abs(self.longitudes - longitude).argmin()
        )

        candidate = self.flat_index(row, col)

        if not navigable_only:
            return candidate

        if self.is_valid_node(candidate):
            return candidate

        # If the nearest coordinate happens to be land or
        # otherwise blocked, search outward for the nearest
        # navigable cell.

        navigable_indices = np.argwhere(self.navigable)

        if len(navigable_indices) == 0:
            raise ValueError(
                "Grid contains no navigable cells"
            )

        lat_values = self.latitudes[navigable_indices[:, 0]]
        lon_values = self.longitudes[navigable_indices[:, 1]]

        distance_sq = (
            (lat_values - latitude) ** 2
            + (lon_values - longitude) ** 2
        )

        nearest_idx = int(np.argmin(distance_sq))

        nearest_row = int(
            navigable_indices[nearest_idx, 0]
        )

        nearest_col = int(
            navigable_indices[nearest_idx, 1]
        )

        return self.flat_index(
            nearest_row,
            nearest_col,
        )

    # --------------------------------------------------------
    # Load from NetCDF
    # --------------------------------------------------------

    @classmethod
    def from_netcdf(
        cls,
        bathymetry_file: str | Path,
    ) -> "MarineGrid":
        """
        Load the static routing grid from the friend's
        processed bathymetry NetCDF dataset.
        """

        bathymetry_file = Path(bathymetry_file)

        if not bathymetry_file.exists():
            raise FileNotFoundError(
                f"Bathymetry file not found: {bathymetry_file}"
            )

        ds = xr.open_dataset(bathymetry_file)

        required_variables = {
            "navigable",
            "depth_m",
        }

        missing = required_variables - set(ds.data_vars)

        if missing:
            ds.close()

            raise ValueError(
                "Bathymetry dataset is missing variables: "
                + ", ".join(sorted(missing))
            )

        latitudes = ds["lat"].values
        longitudes = ds["lon"].values

        navigable = (
            ds["navigable"]
            .values
            .astype(bool)
        )

        depth_m = (
            ds["depth_m"]
            .values
            .astype(np.float32)
        )

        ds.close()

        return cls(
            latitudes=latitudes,
            longitudes=longitudes,
            navigable=navigable,
            depth_m=depth_m,
        )