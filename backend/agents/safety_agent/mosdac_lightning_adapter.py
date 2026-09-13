import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

MOSDAC_WMS = "https://mosdac.gov.in/geoserver_2/weather_forecast/wms"
MOSDAC_LPI_LAYER = os.getenv("MOSDAC_LPI_LAYER", "weather_forecast:GEO_LPI_03")
WIDTH = 256
HEIGHT = 256
RESOLUTION = 152.8740575
CACHE_TTL = 600
TIMEOUT = 5
MAX_WORKERS = 12
_cache = {}

def latlon_to_webmercator(lat, lon):
    x = lon * 20037508.34 / 180
    y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
    y *= 20037508.34 / 180
    return x, y

def _get_lpi(lat, lon, layer):
    x, y = latlon_to_webmercator(lat, lon)
    half = RESOLUTION * WIDTH / 2
    bbox = f"{x-half},{y-half},{x+half},{y+half}"
    params = {
        "REQUEST": "GetFeatureInfo",
        "QUERY_LAYERS": layer,
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "FORMAT": "image/png",
        "STYLES": "",
        "TRANSPARENT": "TRUE",
        "LAYERS": layer,
        "INFO_FORMAT": "application/json",
        "FEATURE_COUNT": 1,
        "X": 128,
        "Y": 128,
        "WIDTH": WIDTH,
        "HEIGHT": HEIGHT,
        "SRS": "EPSG:3857",
        "BBOX": bbox,
    }
    r = requests.get(MOSDAC_WMS, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    features = r.json().get("features", [])
    if not features:
        return None
    value = features[0].get("properties", {}).get("GRAY_INDEX")
    return float(value) if value is not None else None

def _lpi_to_risk(lpi):
    if lpi is None:
        return None
    if lpi <= 1:
        return min(lpi, 0.2)
    if lpi <= 5:
        return 0.2 + (lpi - 1) * 0.075
    if lpi <= 10:
        return 0.5 + (lpi - 5) * 0.08
    return min(0.9 + (lpi - 10) * 0.01, 1.0)

def get_mosdac_lightning_risk(lat, lon, layer=None):
    layer = layer or MOSDAC_LPI_LAYER
    key = (round(float(lat), 4), round(float(lon), 4), layer)
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached[0] < CACHE_TTL:
        return cached[1]
    try:
        lpi = _get_lpi(float(lat), float(lon), layer)
        result = {
            "available": lpi is not None,
            "risk": _lpi_to_risk(lpi),
            "raw_lpi": lpi,
            "source": "MOSDAC Lightning Forecast" if lpi is not None else "MOSDAC Lightning Forecast -- no value",
            "layer": layer,
        }
    except Exception as e:
        result = {
            "available": False,
            "risk": None,
            "raw_lpi": None,
            "source": f"MOSDAC Lightning Forecast -- unavailable: {type(e).__name__}",
            "layer": layer,
        }
    _cache[key] = (now, result)
    return result

def get_mosdac_lightning_risk_bulk(points, layer=None):
    layer = layer or MOSDAC_LPI_LAYER
    results = {}
    tasks = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for point in points:
            zone_id = str(point["zone_id"]).upper()
            lat = float(point["latitude"])
            lon = float(point["longitude"])
            tasks[executor.submit(get_mosdac_lightning_risk, lat, lon, layer)] = zone_id

        for future in as_completed(tasks):
            zone_id = tasks[future]
            try:
                results[zone_id] = future.result()
            except Exception as e:
                results[zone_id] = {
                    "available": False,
                    "risk": None,
                    "raw_lpi": None,
                    "source": f"MOSDAC Lightning Forecast -- unavailable: {type(e).__name__}",
                    "layer": layer,
                }

    return results

if __name__ == "__main__":
    points = [
        {"zone_id": "TEST1", "latitude": 17.36, "longitude": 78.47},
        {"zone_id": "TEST2", "latitude": 9.9312, "longitude": 76.2673},
        {"zone_id": "TEST3", "latitude": 10.0, "longitude": 70.0},
    ]
    print(get_mosdac_lightning_risk_bulk(points))