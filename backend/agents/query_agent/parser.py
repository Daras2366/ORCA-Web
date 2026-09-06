import re
from datetime import datetime, timedelta


def parse_query(query: str):

    text = query.lower()

    # -----------------------------
    # INTENT DETECTION
    # -----------------------------

    intents = []

    fishing_words = [
        # English
        "fish", "fishing", "pfz", "fishing zone",
        "fishing potential", "chlorophyll", "sst",
        "productivity",

        # Hindi
        "मछली", "मछली पकड़ना", "मछली पकड़ने",
        "मछली पकड़ने का क्षेत्र", "क्लोरोफिल",
        "जोखिम", "समुद्र",

        # Tamil
        "மீன்", "மீன்பிடி", "மீன்பிடிக்க",
        "மீன்பிடி பகுதி", "குளோரோபில்",
        "கடல்",

        # Punjabi
        "ਮੱਛੀ", "ਮੱਛੀ ਫੜਨ", "ਮੱਛੀ ਫੜਨ ਲਈ",
        "ਮੱਛੀ ਫੜਨ ਵਾਲਾ ਇਲਾਕਾ", "ਕਲੋਰੋਫਿਲ",
        "ਸਮੁੰਦਰ",

        # Hinglish
        "machhli", "machhli pakadna",
        "fishing zone", "samundar", "sea"
    ]
    
    ocean_words = [
        # English
        "ocean", "sea", "ocean condition",
        "ocean conditions", "sea condition",
        "sea conditions", "sst", "chlorophyll",
        "current", "wave", "temperature",

        # Hindi
        "समुद्र", "समुद्र की स्थिति",
        "समुद्री स्थिति", "समुद्र की हालत",
        "तापमान", "क्लोरोफिल", "लहर",
        "लहरें", "धारा",

        # Tamil
        "கடல்", "கடல் நிலைமை",
        "கடல் நிலை", "வெப்பநிலை",
        "குளோரோபில்", "அலை", "நீரோட்டம்",

        # Punjabi
        "ਸਮੁੰਦਰ", "ਸਮੁੰਦਰ ਦੀ ਸਥਿਤੀ",
        "ਸਮੁੰਦਰ ਦੀ ਹਾਲਤ", "ਤਾਪਮਾਨ",
        "ਕਲੋਰੋਫਿਲ", "ਲਹਿਰ", "ਲਹਿਰਾਂ",
        "ਧਾਰਾ",

        # Hinglish
        "samundar", "samundar ki condition",
        "sea condition", "lehar", "lehrein",
        "temperature"
    ]

    safety_words = [
        # English
        "safe", "safety", "risk", "danger",
        "dangerous", "cyclone", "storm",
        "wind", "wave", "avoid", "warning",
        "boat",

        # Hindi
        "सुरक्षित", "सुरक्षा", "जोखिम", "खतरा",
        "खतरनाक", "चक्रवात", "तूफान",
        "हवा", "लहर", "बचें", "चेतावनी",

        # Tamil
        "பாதுகாப்பு", "பாதுகாப்பான", "ஆபத்து",
        "அபாயம்", "சூறாவளி", "புயல்",
        "காற்று", "அலை",

        # Punjabi
        "ਸੁਰੱਖਿਅਤ", "ਸੁਰੱਖਿਆ", "ਖਤਰਾ",
        "ਖ਼ਤਰਾ", "ਚੱਕਰਵਾਤ", "ਤੂਫ਼ਾਨ",
        "ਹਵਾ", "ਲਹਿਰ",

        # Hinglish
        "safe", "safety", "risk", "danger",
        "cyclone", "hawa", "lehar",
        "surakshit", "khatra", "toofan"
    ]

    route_words = [
        # English
        "route", "distance", "travel", "fuel",
        "reach", "harbour", "harbor",
        "shortest", "closest", "nearest",
        "litres", "liters", "km",

        # Hindi
        "दूरी", "रास्ता", "मार्ग", "ईंधन",
        "कितनी दूर", "कितना समय",

        # Tamil
        "தூரம்", "வழி", "எரிபொருள்",
        "எவ்வளவு தூரம்", "எவ்வளவு நேரம்",

        # Punjabi
        "ਦੂਰੀ", "ਰਸਤਾ", "ਈਂਧਨ",
        "ਕਿੰਨੀ ਦੂਰ", "ਕਿੰਨਾ ਸਮਾਂ"
    ]

    if any(word in text for word in fishing_words):
        intents.append("fishing")
        
    if any(word in text for word in ocean_words):
        intents.append("ocean")

    if any(word in text for word in safety_words):
        intents.append("safety")

    if any(word in text for word in route_words):
        intents.append("route")

    if not intents:
        intents.append("general")

    # -----------------------------
    # TIME DETECTION
    # -----------------------------

    datetime_value = None

    if "tomorrow" in text:
        tomorrow = datetime.now() + timedelta(days=1)
        datetime_value = tomorrow.strftime("%Y-%m-%d")

    elif "today" in text:
        datetime_value = datetime.now().strftime("%Y-%m-%d")

    # Time such as:
    # 9 AM
    # 9:30 AM
    # 09:00
    time_match = re.search(
        r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
        text
    )

    requested_time = None

    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        meridian = time_match.group(3)

        if meridian == "pm" and hour != 12:
            hour += 12
        elif meridian == "am" and hour == 12:
            hour = 0

        requested_time = f"{hour:02d}:{minute:02d}"

    # -----------------------------
    # COORDINATE DETECTION
    # -----------------------------

    coordinates = re.findall(
        r"(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)",
        query
    )

    latitude = None
    longitude = None

    if coordinates:
        latitude = float(coordinates[0][0])
        longitude = float(coordinates[0][1])

    # -----------------------------
    # ZONE DETECTION
    # -----------------------------

    zones = re.findall(
        r"\b(PFZ\d+|Z\d+)\b",
        query.upper()
    )

    zone_id = zones[0] if zones else None
    comparison_zone = zones[1] if len(zones) > 1 else None

    # -----------------------------
    # DISTANCE DETECTION
    # -----------------------------

    distance_km = None

    distance_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:km|kilometers|kilometres)",
        text
    )

    if distance_match:
        distance_km = float(distance_match.group(1))

    # -----------------------------
    # FUEL DETECTION
    # -----------------------------

    fuel_litres = None

    fuel_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:l|litre|litres|liter|liters)",
        text
    )

    if fuel_match:
        fuel_litres = float(fuel_match.group(1))

    # -----------------------------
    # ORIGIN / HARBOUR DETECTION
    # -----------------------------

    origin = None

    origin_match = re.search(
        r"(?:from|starting from)\s+(.+?)(?=\s+to\s+|\s*$)",
        query,
        re.IGNORECASE
    )

    if origin_match:
        origin = origin_match.group(1).strip()

    # Explicit harbour mention
    if "harbour" in text or "harbor" in text:
        if origin is None:
            origin = "harbour"

    # -----------------------------
    # QUERY TYPE / CONSTRAINTS
    # -----------------------------

    query_type = "general"

    if "safest time" in text or (
        "what time" in text and "safe" in text
    ):
        query_type = "safest_time"

    elif any(x in text for x in [
        "highest fishing",
        "highest fishing potential",
        "best fishing",
        "best fishing zone"
    ]):
        query_type = "highest_fishing"

    elif any(x in text for x in [
        "safest",
        "safest fishing zone",
        "which fishing zone is safest"
    ]):
        query_type = "safest"

    elif "within" in text and distance_km is not None:
        query_type = "nearby"

    elif any(x in text for x in [
        "nearby", "closest", "nearest"
    ]):
        query_type = "nearby"

    elif "least fuel" in text:
        query_type = "least_fuel"

    elif "shortest route" in text:
        query_type = "shortest_route"

    elif "lowest travel time" in text:
        query_type = "lowest_travel_time"

    elif "how far" in text or "distance" in text:
        query_type = "distance"

    elif "how long" in text or "travel time" in text:
        query_type = "travel_time"

    elif "how much fuel" in text or "fuel" in text:
        query_type = "fuel"

    elif "can i reach" in text:
        query_type = "fuel_feasibility"

    elif "tomorrow" in text:
        query_type = "tomorrow_forecast"

    elif "cyclone" in text or "storm" in text:
        query_type = "cyclone_risk"

    elif "wave" in text:
        query_type = "wave_safety"

    elif "wind" in text:
        query_type = "wind_safety"

    elif "avoid" in text:
        query_type = "avoid_zones"

    elif "compare" in text or (
        zone_id and comparison_zone
    ):
        query_type = "comparison"

    elif "why" in text:
        query_type = "explanation"

    # -----------------------------
    # REQUIRED AGENTS
    # -----------------------------

    required_agents = []

    if "fishing" in intents:
        required_agents.append("ocean")

    if "safety" in intents:
        required_agents.append("safety")

    if "route" in intents:
        required_agents.append("route")

    if "general" in intents:
        required_agents = ["ocean", "safety", "route"]

    # Tomorrow safety needs safety + potentially ocean
    if query_type in [
        "safest_time",
        "tomorrow_forecast",
        "cyclone_risk",
        "wave_safety",
        "wind_safety",
        "avoid_zones"
    ]:
        if "safety" not in required_agents:
            required_agents.append("safety")

    return {
        "query": query,
        "intents": intents,
        "query_type": query_type,

        "latitude": latitude,
        "longitude": longitude,

        "zone_id": zone_id,
        "comparison_zone": comparison_zone,

        "datetime": datetime_value,
        "requested_time": requested_time,

        "origin": origin,

        "distance_km": distance_km,
        "fuel_litres": fuel_litres,

        "required_agents": required_agents
    }
