import requests
import numpy as np
from datetime import datetime, timedelta


MARINE_API = "https://marine-api.open-meteo.com/v1/marine"
WEATHER_API = "https://api.open-meteo.com/v1/forecast"


def get_tomorrow_forecast(latitude, longitude):
    tomorrow = (
        datetime.now() + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    # -----------------------------
    # MARINE FORECAST
    # -----------------------------
    marine_params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "wave_height,wave_period,wave_direction",
        "forecast_days": 2,
        "timezone": "auto"
    }

    marine_response = requests.get(
        MARINE_API,
        params=marine_params,
        timeout=20
    )

    marine_response.raise_for_status()
    marine = marine_response.json()

    # -----------------------------
    # WEATHER FORECAST
    # -----------------------------
    weather_params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "wind_speed_10m,precipitation",
        "forecast_days": 2,
        "timezone": "auto"
    }

    weather_response = requests.get(
        WEATHER_API,
        params=weather_params,
        timeout=20
    )

    weather_response.raise_for_status()
    weather = weather_response.json()

    marine_hourly = marine["hourly"]
    weather_hourly = weather["hourly"]

    # Match weather values using timestamp
    weather_map = {
        timestamp: {
            "wind_speed_kmh": wind,
            "precipitation_mm": rain
        }
        for timestamp, wind, rain in zip(
            weather_hourly["time"],
            weather_hourly["wind_speed_10m"],
            weather_hourly["precipitation"]
        )
    }

    forecast = []

    for i, timestamp in enumerate(marine_hourly["time"]):

        # Keep only tomorrow
        if not timestamp.startswith(tomorrow):
            continue

        weather_data = weather_map.get(timestamp, {})

        wind_kmh = weather_data.get("wind_speed_kmh")

        # Convert km/h → m/s
        wind_ms = (
            wind_kmh / 3.6
            if wind_kmh is not None
            else None
        )

        forecast.append({
            "time": timestamp,
            "wave_height_m": marine_hourly["wave_height"][i],
            "wave_period_s": marine_hourly["wave_period"][i],
            "wave_direction_deg": marine_hourly["wave_direction"][i],
            "wind_speed_ms": wind_ms,
            "precipitation_mm": weather_data.get(
                "precipitation_mm"
            )
        })

    return forecast


# =========================================================
# SAFETY SCORING FUNCTIONS
# Same thresholds as Safety Agent notebook
# =========================================================

def wind_safety_score(wind):
    if wind is None:
        return None

    return float(
        np.interp(
            wind,
            [0, 4, 6, 8, 10, 12, 15],
            [100, 100, 90, 65, 35, 10, 0]
        )
    )


def wave_safety_score(wave):
    if wave is None:
        return None

    return float(
        np.interp(
            wave,
            [0, 0.5, 1, 1.5, 2, 2.5, 3.5, 5, 8, 10],
            [100, 100, 95, 85, 70, 50, 25, 10, 0, 0]
        )
    )


def rainfall_safety_score(rainfall):
    if rainfall is None:
        return None

    return float(
        np.interp(
            rainfall,
            [0, 2, 4, 6, 8, 10, 15],
            [100, 95, 85, 65, 40, 20, 0]
        )
    )


# =========================================================
# FORECAST SAFETY SCORE
# =========================================================

def calculate_forecast_safety(forecast):

    results = []

    for row in forecast:

        wind_score = wind_safety_score(
            row["wind_speed_ms"]
        )

        wave_score = wave_safety_score(
            row["wave_height_m"]
        )

        rain_score = rainfall_safety_score(
            row["precipitation_mm"]
        )

        # Same weighting philosophy as Safety Agent:
        # wind 30%, wave 25%, rainfall 10%.
        #
        # Cyclone/current are not available as hourly
        # forecast values here, so available weights
        # are renormalized.

        components = []

        if wind_score is not None:
            components.append(
                (wind_score, 0.30)
            )

        if wave_score is not None:
            components.append(
                (wave_score, 0.25)
            )

        if rain_score is not None:
            components.append(
                (rain_score, 0.10)
            )

        if not components:
            forecast_score = None

        else:
            weighted_sum = sum(
                score * weight
                for score, weight in components
            )

            total_weight = sum(
                weight
                for _, weight in components
            )

            forecast_score = (
                weighted_sum / total_weight
            )

        # Safety level
        if forecast_score is None:
            level = "UNKNOWN"

        elif forecast_score >= 80:
            level = "SAFE"

        elif forecast_score >= 60:
            level = "MODERATE"

        elif forecast_score >= 40:
            level = "CAUTION"

        else:
            level = "UNSAFE"

        results.append({
            **row,

            "wind_safety": (
                round(wind_score, 2)
                if wind_score is not None
                else None
            ),

            "wave_safety": (
                round(wave_score, 2)
                if wave_score is not None
                else None
            ),

            "rainfall_safety": (
                round(rain_score, 2)
                if rain_score is not None
                else None
            ),

            "forecast_safety_score": (
                round(forecast_score, 2)
                if forecast_score is not None
                else None
            ),

            "forecast_safety_level": level
        })

    return results


# =========================================================
# FIND SAFEST TIME
# =========================================================

def get_safest_time(forecast):

    scored = calculate_forecast_safety(forecast)

    valid = [
        row for row in scored
        if row["forecast_safety_score"] is not None
    ]

    if not valid:
        return None, []

    safest = max(
        valid,
        key=lambda row: row["forecast_safety_score"]
    )

    return safest, scored


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    # Example location
    latitude = 10.0
    longitude = 76.0

    print("Fetching tomorrow forecast...")

    forecast = get_tomorrow_forecast(
        latitude,
        longitude
    )

    print(
        f"Tomorrow forecast: {len(forecast)} hours"
    )

    safest, scored = get_safest_time(
        forecast
    )

    print("\n==============================")
    print("SAFEST TIME TOMORROW")
    print("==============================")

    if safest:

        print(
            "Time:",
            safest["time"]
        )

        print(
            "Forecast Safety Score:",
            safest["forecast_safety_score"],
            "/100"
        )

        print(
            "Safety Level:",
            safest["forecast_safety_level"]
        )

        print(
            "Wind:",
            round(
                safest["wind_speed_ms"], 2
            ),
            "m/s"
        )

        print(
            "Wave Height:",
            safest["wave_height_m"],
            "m"
        )

        print(
            "Wave Period:",
            safest["wave_period_s"],
            "s"
        )

        print(
            "Rain:",
            safest["precipitation_mm"],
            "mm"
        )

    else:
        print(
            "No valid forecast data available."
        )
