from backend.agents.decision_layer.config import FISHING_WEIGHT, SAFETY_WEIGHT, ROUTE_WEIGHT


def calculate_final_score(
    fishing_score: float,
    risk_score: float,
    route_score: float
) -> float:

    safety_score = 1 - risk_score

    final_score = (
        FISHING_WEIGHT * fishing_score
        + SAFETY_WEIGHT * safety_score
        + ROUTE_WEIGHT * route_score
    )

    return round(final_score, 4)
