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
    Download a small L4 CHL subset and return the nearest
    grid-cell value.

    Returns:
        (chlorophyll_value, observation_date)
    """

    start = date.strftime(
        "%Y-%m-%dT00:00:00"
    )

    min_lon = longitude - BOX_DEGREES
    max_lon = longitude + BOX_DEGREES
    min_lat = latitude - BOX_DEGREES
    max_lat = latitude + BOX_DEGREES

    # Create a date-specific temporary/cache directory.
    # This prevents one request from accidentally reading
    # a NetCDF file created by another request.
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
        exist_ok=True
    )

    try:

        copernicusmarine.subset(
            dataset_id=DATASET_ID,
            variables=["CHL"],
            start_datetime=start,
            end_datetime=start,
            minimum_longitude=min_lon,
            maximum_longitude=max_lon,
            minimum_latitude=min_lat,
            maximum_latitude=max_lat,
            output_directory=str(output_dir),
        )

        nc_files = list(
            output_dir.glob("*.nc")
        )

        if not nc_files:
            return None, None

        # There should normally be one file in this
        # date/coordinate-specific directory.
        file_path = nc_files[0]

        with xr.open_dataset(file_path) as ds:

            if "CHL" not in ds:
                return None, None

            if (
                "latitude" not in ds.coords
                or "longitude" not in ds.coords
            ):
                return None, None

            chl = ds["CHL"]

            values = np.asarray(
                chl.squeeze().values,
                dtype=float
            )

            if values.size == 0:
                return None, None

            lats = np.asarray(
                ds["latitude"].values,
                dtype=float
            )

            lons = np.asarray(
                ds["longitude"].values,
                dtype=float
            )

            lat_idx = int(
                np.abs(
                    lats - latitude
                ).argmin()
            )

            lon_idx = int(
                np.abs(
                    lons - longitude
                ).argmin()
            )

            value = float(
                values[lat_idx, lon_idx]
            )

            if not np.isfinite(value):
                return None, None

            return (
                value,
                date.strftime("%Y-%m-%d")
            )

    except Exception as exc:

        print(
            f"[CHL] Copernicus request failed "
            f"for {date.strftime('%Y-%m-%d')}: {exc}"
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
                "ORCA historical/satellite dataset",

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