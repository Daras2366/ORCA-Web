from backend.agents.decision_layer.config import SAFETY_MINIMUM


def apply_constraints(safety_score, final_score):
    if safety_score < SAFETY_MINIMUM:
        return "AVOID"

    if final_score >= 0.75:
        return "RECOMMENDED"

    if final_score >= 0.50:
        return "CAUTION"

    return "AVOID"
