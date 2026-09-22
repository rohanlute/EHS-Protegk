RISK_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "VERY_HIGH": 4}


def ergonomic_risk_level(score):
    score = float(score or 0)
    if score <= 0:
        return ""
    if score <= 3:
        return "LOW"
    if score <= 7:
        return "MEDIUM"
    if score <= 10:
        return "HIGH"
    return "VERY_HIGH"


def recommended_action_for_level(level):
    return {
        "LOW": "Acceptable; monitor and maintain controls.",
        "MEDIUM": "Investigate and improve controls where practicable.",
        "HIGH": "Prompt investigation and ergonomic changes required.",
        "VERY_HIGH": "Immediate action required; reduce exposure until controlled.",
    }.get(level, "")


def risk_reduction_percent(previous_score, new_score):
    previous_score = float(previous_score or 0)
    new_score = float(new_score or 0)
    if previous_score <= 0:
        return 0
    return round(((previous_score - new_score) / previous_score) * 100, 2)
