def normalize_ocean_output(data):
    return {
        "zone_id": data["zone_id"],
        "fishing_score": float(data["fishing_score"])
    }


def normalize_safety_output(data):
    return {
        "zone_id": data["zone_id"],
        "risk_score": float(data["risk_score"])
    }


def normalize_route_output(data):
    return {
        "zone_id": data["zone_id"],
        "route_score": float(data["route_score"])
    }
