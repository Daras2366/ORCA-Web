import requests


MARINE_API = "https://marine-api.open-meteo.com/v1/marine"


def get_live_ocean(latitude, longitude):

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "sea_surface_temperature,"
            "ocean_current_velocity,"
            "ocean_current_direction,"
            "wave_height,"
            "wave_period,"
            "wave_direction"
        ),
        "timezone": "auto",
    }

    response = requests.get(
        MARINE_API,
        params=params,
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    current = data.get(
        "current",
        {}
    )

    return {
        "timestamp":
            current.get("time"),

        "sst_c":
            current.get(
                "sea_surface_temperature"
            ),

        "current_speed_ms":
            current.get(
                "ocean_current_velocity"
            ),

        "current_direction_deg":
            current.get(
                "ocean_current_direction"
            ),

        "wave_height_m":
            current.get(
                "wave_height"
            ),

        "wave_period_s":
            current.get(
                "wave_period"
            ),

        "wave_direction_deg":
            current.get(
                "wave_direction"
            ),

        "source":
            "Open-Meteo",

        "data_mode":
            "live"
    }