from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr
import copernicusmarine


DATASET_ID = (
    "cmems_obs-oc_glo_bgc-plankton_nrt_l4-gapfree-multi-4km_P1D"
)

# L4 resolution is approximately 4 km.
BOX_DEGREES = 0.08

# Maximum age of an acceptable Copernicus observation.
MAX_DATA_AGE_DAYS = 5

# The NRT product can lag the current date.
# Starting two days back avoids predictable "date exceeds dataset"
# requests while still allowing recent data to be used.
INITIAL_LOOKBACK_DAYS = 2

# Temporary fallback to the ORCA CSV.
CSV_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "ocean"
    / "unified_ocean_current.csv"
)


def _get_latest_copernicus_date() -> datetime:
    """
    Return a recent UTC date from which to begin searching.

    Copernicus NRT ocean-colour data can lag the current date,
    so we intentionally start slightly behind today.
    """

    now = datetime.now(timezone.utc)

    today = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    return today - timedelta(
        days=INITIAL_LOOKBACK_DAYS
    )


def _download_chlorophyll(
    latitude: float,
    longitude: float,
    date: datetime,
) -> tuple[float | None, str | None]:
    """
    Download a small Copernicus Marine L4 CHL subset and
    return the nearest valid ocean grid-cell value.
    """

    start = date.strftime("%Y-%m-%dT00:00:00")
    end = (
        date + timedelta(days=1)
    ).strftime("%Y-%m-%dT00:00:00")

    min_lon = longitude - BOX_DEGREES
    max_lon = longitude + BOX_DEGREES
    min_lat = latitude - BOX_DEGREES
    max_lat = latitude + BOX_DEGREES

    cache_root = (
        Path(__file__).resolve().parents[3]
        / "copernicus_cache"
    )

    output_dir = (
        cache_root
        / date.strftime("%Y-%m-%d")
        / f"{latitude:.4f}_{longitude:.4f}"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        print(
            f"[CHL] Requesting Copernicus "
            f"{date.strftime('%Y-%m-%d')} "
            f"at ({latitude:.4f}, {longitude:.4f})"
        )

        copernicusmarine.subset(
            dataset_id=DATASET_ID,
            variables=["CHL"],
            start_datetime=start,
            end_datetime=end,
            minimum_longitude=min_lon,
            maximum_longitude=max_lon,
            minimum_latitude=min_lat,
            maximum_latitude=max_lat,
            output_directory=str(output_dir),
        )

        nc_files = list(output_dir.glob("*.nc"))

        if not nc_files:
            print("[CHL] Copernicus returned no NetCDF file.")
            return None, None

        file_path = nc_files[0]

        print(f"[CHL] Reading {file_path.name}")

        with xr.open_dataset(file_path) as ds:

            print(
                f"[CHL] Dimensions: {dict(ds.sizes)}"
            )
            print(
                f"[CHL] Variables: {list(ds.data_vars)}"
            )
            print(
                f"[CHL] Coordinates: {list(ds.coords)}"
            )

            if "CHL" not in ds:
                print("[CHL] CHL variable not found.")
                return None, None

            if (
                "latitude" not in ds.coords
                or "longitude" not in ds.coords
            ):
                print(
                    "[CHL] Latitude/longitude coordinates "
                    "not found."
                )
                return None, None

            chl = ds["CHL"]

            # -------------------------------------------------
            # Select the requested day first.
            # This fixes the 3D (time, latitude, longitude)
            # indexing problem seen in the previous code.
            # -------------------------------------------------
            if "time" in chl.dims:
                time_values = np.asarray(
                    ds["time"].values
                )

                # Convert both sides to timezone-free day precision.
                target_time = np.datetime64(
                    date.strftime("%Y-%m-%d"),
                    "D",
                )

                dataset_times = time_values.astype(
                    "datetime64[D]"
                )

                time_idx = int(
                    np.abs(dataset_times - target_time).argmin()
                )

                print(
                    f"[CHL] Selected time index {time_idx}: "
                    f"{dataset_times[time_idx]}"
                )

                chl = chl.isel(time=time_idx)

            chl = chl.squeeze(drop=True)

            lats = np.asarray(
                ds["latitude"].values,
                dtype=float,
            )

            lons = np.asarray(
                ds["longitude"].values,
                dtype=float,
            )

            values = np.asarray(
                chl.values,
                dtype=float,
            )

            print(
                f"[CHL] Spatial array shape: {values.shape}"
            )

            # -------------------------------------------------
            # Make sure we have a 2D latitude x longitude array.
            # -------------------------------------------------
            if values.ndim != 2:
                print(
                    f"[CHL] Unexpected CHL dimensions: "
                    f"{values.shape}"
                )
                return None, None

            # -------------------------------------------------
            # Find the closest grid cell.
            # -------------------------------------------------
            lat_idx = int(
                np.abs(lats - latitude).argmin()
            )

            lon_idx = int(
                np.abs(lons - longitude).argmin()
            )

            nearest_value = float(
                values[lat_idx, lon_idx]
            )

            # -------------------------------------------------
            # If the closest pixel is NaN (common near coastlines),
            # search the downloaded area for the closest VALID
            # chlorophyll pixel.
            # -------------------------------------------------
            if not np.isfinite(nearest_value):

                print(
                    "[CHL] Nearest Copernicus cell is NaN. "
                    "Searching nearby valid ocean cells..."
                )

                valid_mask = np.isfinite(values)

                if not valid_mask.any():
                    print(
                        "[CHL] No valid CHL pixels found "
                        "in the requested area."
                    )
                    return None, None

                valid_indices = np.argwhere(
                    valid_mask
                )

                # Calculate geographic distance for every
                # valid pixel and select the closest one.
                lat_values = lats[
                    valid_indices[:, 0]
                ]

                lon_values = lons[
                    valid_indices[:, 1]
                ]

                distances = (
                    (lat_values - latitude) ** 2
                    + (lon_values - longitude) ** 2
                )

                closest_valid_idx = int(
                    np.argmin(distances)
                )

                valid_lat_idx = int(
                    valid_indices[
                        closest_valid_idx, 0
                    ]
                )

                valid_lon_idx = int(
                    valid_indices[
                        closest_valid_idx, 1
                    ]
                )

                nearest_value = float(
                    values[
                        valid_lat_idx,
                        valid_lon_idx,
                    ]
                )

                print(
                    f"[CHL] Using nearby valid ocean pixel "
                    f"at ({lats[valid_lat_idx]:.4f}, "
                    f"{lons[valid_lon_idx]:.4f})"
                )

            # -------------------------------------------------
            # Final validation
            # -------------------------------------------------
            if not np.isfinite(nearest_value):
                print(
                    "[CHL] No valid Copernicus CHL value."
                )
                return None, None

            print(
                f"[CHL] Copernicus SUCCESS: "
                f"{nearest_value:.4f} mg/m3 "
                f"({date.strftime('%Y-%m-%d')})"
            )

            return (
                nearest_value,
                date.strftime("%Y-%m-%d"),
            )

    except Exception as exc:
        print(
            f"[CHL] Copernicus FAILED "
            f"for {date.strftime('%Y-%m-%d')}"
        )
        print(
            f"[CHL] Error type: {type(exc).__name__}"
        )
        print(
            f"[CHL] Error: {exc}"
        )

        return None, None


def _get_csv_fallback(
    latitude: float,
    longitude: float
) -> dict[str, Any] | None:
    """
    Find the nearest ORCA CSV chlorophyll value.
    """

    if not CSV_PATH.exists():
        return None

    try:

        df = pd.read_csv(
            CSV_PATH
        )

        required = {
            "latitude",
            "longitude",
            "chlorophyll_mean",
        }

        if not required.issubset(
            df.columns
        ):
            return None

        valid = df.dropna(
            subset=[
                "latitude",
                "longitude",
                "chlorophyll_mean",
            ]
        )

        if valid.empty:
            return None

        distance = (
            (valid["latitude"] - latitude) ** 2
            + (valid["longitude"] - longitude) ** 2
        )

        idx = distance.idxmin()

        row = valid.loc[idx]

        return {
            "chlorophyll_mean":
                float(row["chlorophyll_mean"]),

            "timestamp":
                None,

            "source":
                "MOSDAC",

            "data_mode":
                "fallback",
        }

    except Exception as exc:

        print(
            f"[CHL] CSV fallback failed: {exc}"
        )

        return None


def get_chlorophyll(
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """
    Get near-real-time chlorophyll for a geographic point.

    Priority:

        1. Copernicus Marine L4 NRT gap-free
        2. ORCA CSV fallback
    """

    latest_date = (
        _get_latest_copernicus_date()
    )

    for days_back in range(
        MAX_DATA_AGE_DAYS + 1
    ):

        target_date = (
            latest_date
            - timedelta(days=days_back)
        )

        value, timestamp = (
            _download_chlorophyll(
                latitude,
                longitude,
                target_date,
            )
        )

        if value is not None:

            return {
                "chlorophyll_mean":
                    value,

                "timestamp":
                    timestamp,

                "source":
                    "Copernicus Marine",

                "data_mode":
                    "near_real_time",

                "dataset_id":
                    DATASET_ID,
            }

    fallback = _get_csv_fallback(
        latitude,
        longitude
    )

    if fallback is not None:
        return fallback

    return {
        "chlorophyll_mean":
            None,

        "timestamp":
            None,

        "source":
            None,

        "data_mode":
            "unavailable",
    }