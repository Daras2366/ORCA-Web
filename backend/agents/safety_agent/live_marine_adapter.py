import os
import time
import math
import requests
from backend.agents.safety_agent.cyclone_adapter import get_cyclone_risk

MARINE_API = "https://marine-api.open-meteo.com/v1/marine"
WEATHER_API = "https://api.open-meteo.com/v1/forecast"

CACHE_TTL = 900
CHUNK_SIZE = 25

_single_cache = {}
_bulk_cache = {"time": 0, "data": {}}


def _get_json(url, params=None, headers=None):
    r = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=30
    )
    r.raise_for_status()
    return r.json()


def _to_ms(value):
    if value is None:
        return None
    return float(value) / 3.6


def _distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1 = math.radians(float(lat1))
    p2 = math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    return 2 * r * math.asin(math.sqrt(a))


def get_live_conditions(latitude, longitude):
    key = (
        round(float(latitude), 4),
        round(float(longitude), 4)
    )

    now = time.time()
    cached = _single_cache.get(key)

    if cached and now - cached["time"] < CACHE_TTL:
        return cached["data"]

    marine = _get_json(MARINE_API, {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "wave_height,wave_period,wave_direction,"
            "ocean_current_velocity,ocean_current_direction,"
            "sea_surface_temperature"
        ),
        "timezone": "UTC",
        "cell_selection": "sea"
    })

    weather = _get_json(WEATHER_API, {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "wind_speed_10m,wind_direction_10m,precipitation"
        ),
        "wind_speed_unit": "kmh",
        "timezone": "UTC"
    })

    cyclone = get_cyclone_risk(
        latitude,
        longitude
    )

    mc = marine.get("current", {})
    wc = weather.get("current", {})

    data = {
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": mc.get("time") or wc.get("time"),
        "wave_height_m": mc.get("wave_height"),
        "wave_period_s": mc.get("wave_period"),
        "wave_direction_deg": mc.get("wave_direction"),
        "current_speed_ms": _to_ms(mc.get("ocean_current_velocity")),
        "current_direction_deg": mc.get("ocean_current_direction"),
        "sst_c": mc.get("sea_surface_temperature"),
        "wind_speed_kmh": wc.get("wind_speed_10m"),
        "wind_direction_deg": wc.get("wind_direction_10m"),
        "precipitation_mm": wc.get("precipitation"),
        "cyclone": cyclone,
        "source": "Open-Meteo + GDACS",
        "data_mode": "live"
    }

    _single_cache[key] = {
        "time": now,
        "data": data
    }

    return data


def get_live_conditions_bulk(
    points,
    chunk_size=CHUNK_SIZE
):
    global _bulk_cache

    now = time.time()

    if (
        now - _bulk_cache["time"] < CACHE_TTL
        and _bulk_cache["data"]
    ):
        return _bulk_cache["data"]

    results = {}

    for start in range(
        0,
        len(points),
        chunk_size
    ):
        chunk = points[
            start:start + chunk_size
        ]

        if not chunk:
            continue

        latitudes = ",".join(
            str(float(p["latitude"]))
            for p in chunk
        )

        longitudes = ",".join(
            str(float(p["longitude"]))
            for p in chunk
        )

        try:
            marine = _get_json(MARINE_API, {
                "latitude": latitudes,
                "longitude": longitudes,
                "current": (
                    "wave_height,wave_period,wave_direction,"
                    "ocean_current_velocity,"
                    "ocean_current_direction,"
                    "sea_surface_temperature"
                ),
                "timezone": "UTC",
                "cell_selection": "sea"
            })

            weather = _get_json(WEATHER_API, {
                "latitude": latitudes,
                "longitude": longitudes,
                "current": (
                    "wind_speed_10m,"
                    "wind_direction_10m,"
                    "precipitation"
                ),
                "wind_speed_unit": "kmh",
                "timezone": "UTC"
            })

            marine_rows = (
                marine
                if isinstance(marine, list)
                else [marine]
            )

            weather_rows = (
                weather
                if isinstance(weather, list)
                else [weather]
            )

            for i, point in enumerate(chunk):
                if (
                    i >= len(marine_rows)
                    or i >= len(weather_rows)
                ):
                    continue

                mc = marine_rows[i].get(
                    "current",
                    {}
                )

                wc = weather_rows[i].get(
                    "current",
                    {}
                )

                zone_id = str(
                    point["zone_id"]
                ).upper()

                cyclone = get_cyclone_risk(
                    point["latitude"],
                    point["longitude"]
                )

                results[zone_id] = {
                    "latitude": float(
                        point["latitude"]
                    ),
                    "longitude": float(
                        point["longitude"]
                    ),
                    "timestamp": (
                        mc.get("time")
                        or wc.get("time")
                    ),

                    "wave_height_m":
                        mc.get("wave_height"),

                    "wave_period_s":
                        mc.get("wave_period"),

                    "wave_direction_deg":
                        mc.get("wave_direction"),

                    "current_speed_ms":
                        _to_ms(
                            mc.get(
                                "ocean_current_velocity"
                            )
                        ),

                    "current_direction_deg":
                        mc.get(
                            "ocean_current_direction"
                        ),

                    "sst_c":
                        mc.get(
                            "sea_surface_temperature"
                        ),

                    "wind_speed_kmh":
                        wc.get(
                            "wind_speed_10m"
                        ),

                    "wind_direction_deg":
                        wc.get(
                            "wind_direction_10m"
                        ),

                    "precipitation_mm":
                        wc.get(
                            "precipitation"
                        ),

                    "cyclone": cyclone,

                    "source": "Open-Meteo + GDACS",
                    "data_mode": "live"
                }

        except requests.HTTPError as e:
            print(
                f"[LIVE] Batch "
                f"{start}:{start + len(chunk)} "
                f"failed: {e}"
            )

        except Exception as e:
            print(
                f"[LIVE] Batch "
                f"{start}:{start + len(chunk)} "
                f"failed: {e}"
            )

    if results:
        _bulk_cache = {
            "time": now,
            "data": results
        }

    return results