import time
import requests
from math import radians, sin, cos, asin, sqrt

GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP"
CACHE_TTL = 600
_cache = {"time": 0, "data": []}

def _distance_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))

def get_active_cyclones():
    global _cache
    now = time.time()
    if now - _cache["time"] < CACHE_TTL:
        return _cache["data"]
    try:
        r = requests.get(GDACS_URL, timeout=30)
        r.raise_for_status()
        data = r.json()
        events = [
            e for e in data.get("features", [])
            if e.get("properties", {}).get("eventtype") == "TC"
        ]
        _cache = {"time": now, "data": events}
        return events
    except Exception as e:
        print(f"[GDACS] Cyclone fetch failed: {e}")
        return []

def get_cyclone_risk(latitude, longitude):
    cyclones = get_active_cyclones()
    if not cyclones:
        return {
            "available": False,
            "risk": 0.0,
            "status": "UNKNOWN",
            "source": "GDACS"
        }

    nearest = None
    nearest_distance = float("inf")

    for event in cyclones:
        coords = event.get("geometry", {}).get("coordinates")
        if not coords or len(coords) < 2:
            continue
        try:
            lon, lat = float(coords[0]), float(coords[1])
            distance = _distance_km(latitude, longitude, lat, lon)
        except (TypeError, ValueError):
            continue
        if distance < nearest_distance:
            nearest_distance = distance
            nearest = event

    if nearest is None:
        return {
            "available": False,
            "risk": 0.0,
            "status": "UNKNOWN",
            "source": "GDACS"
        }

    if nearest_distance <= 100:
        risk = 1.0
    elif nearest_distance <= 200:
        risk = 0.8
    elif nearest_distance <= 300:
        risk = 0.6
    elif nearest_distance <= 500:
        risk = 0.3
    else:
        risk = 0.0

    p = nearest.get("properties", {})

    return {
        "available": True,
        "risk": risk,
        "status": "ACTIVE" if risk > 0 else "CLEAR",
        "distance_km": round(nearest_distance, 1),
        "event_id": p.get("eventid"),
        "event_name": p.get("eventname") or p.get("name"),
        "alert_level": p.get("alertlevel"),
        "source": "GDACS"
    }