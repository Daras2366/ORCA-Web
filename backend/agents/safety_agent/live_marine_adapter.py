import requests


MARINE_API = "https://marine-api.open-meteo.com/v1/marine"
WEATHER_API = "https://api.open-meteo.com/v1/forecast"


def get_live_conditions(latitude: float, longitude: float):

    # --------------------------------------------------
    # MARINE
    # --------------------------------------------------

    marine_params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "wave_height,"
            "wave_period,"
            "wave_direction,"
            "ocean_current_velocity,"
            "ocean_current_direction,"
            "sea_surface_temperature"
        ),
        "timezone": "auto",
    }

    marine_response = requests.get(
        MARINE_API,
        params=marine_params,
        timeout=20,
    )

    marine_response.raise_for_status()

    marine = marine_response.json()

    # --------------------------------------------------
    # WEATHER
    # --------------------------------------------------

    weather_params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "wind_speed_10m,"
            "wind_direction_10m,"
            "precipitation"
        ),
        "timezone": "auto",
    }

    weather_response = requests.get(
        WEATHER_API,
        params=weather_params,
        timeout=20,
    )

    weather_response.raise_for_status()

    weather = weather_response.json()

    marine_current = marine.get("current", {})
    weather_current = weather.get("current", {})

    return {
        "latitude": latitude,
        "longitude": longitude,

        "timestamp": (
            marine_current.get("time")
            or weather_current.get("time")
        ),

        "wave_height_m":
            marine_current.get("wave_height"),

        "wave_period_s":
            marine_current.get("wave_period"),

        "wave_direction_deg":
            marine_current.get("wave_direction"),

        "current_speed_ms":
            marine_current.get("ocean_current_velocity"),

        "current_direction_deg":
            marine_current.get("ocean_current_direction"),

        "sst_c":
            marine_current.get("sea_surface_temperature"),

        "wind_speed_kmh":
            weather_current.get("wind_speed_10m"),

        "wind_direction_deg":
            weather_current.get("wind_direction_10m"),

        "precipitation_mm":
            weather_current.get("precipitation"),

        "source": "Open-Meteo",

        "data_mode": "live",
    }