"""
REBA (Rapid Entire Body Assessment) — Hignett & McAtamney (2000).
Real Table A / Table B / Table C lookups; activity score added at the end.
"""
from .risk_service import recommended_action_for_level

# TABLE A — keyed by neck(1-3) -> list of 5 (legs1,legs2,legs3,legs4) tuples for trunk 1-5
TABLE_A = {
    1: [(1, 2, 3, 4), (2, 3, 4, 5), (2, 4, 5, 6), (3, 5, 6, 7), (4, 6, 7, 8)],
    2: [(1, 3, 4, 5), (2, 4, 5, 6), (3, 5, 6, 7), (4, 6, 7, 8), (5, 7, 8, 9)],
    3: [(3, 4, 5, 6), (3, 5, 6, 7), (5, 6, 7, 8), (6, 7, 8, 9), (7, 8, 9, 9)],
}

# TABLE B — keyed by upper_arm(1-6) -> list of 2 (wrist1,wrist2,wrist3) tuples for lower_arm 1-2
TABLE_B = {
    1: [(1, 2, 2), (1, 2, 3)],
    2: [(1, 2, 3), (2, 3, 4)],
    3: [(3, 4, 5), (4, 5, 5)],
    4: [(4, 5, 5), (5, 6, 7)],
    5: [(6, 7, 8), (7, 8, 8)],
    6: [(7, 8, 9), (8, 9, 9)],
}

# TABLE C — rows Score A (1-12), cols Score B (1-12)
TABLE_C = [
    [1, 1, 1, 2, 3, 3, 4, 5, 6, 7, 7, 7],
    [1, 2, 2, 3, 4, 4, 5, 6, 6, 7, 7, 8],
    [2, 3, 3, 3, 4, 5, 6, 7, 7, 8, 8, 8],
    [3, 4, 4, 4, 5, 6, 7, 8, 8, 9, 9, 9],
    [4, 4, 4, 5, 6, 7, 8, 8, 9, 9, 9, 9],
    [6, 6, 6, 7, 8, 8, 9, 9, 10, 10, 10, 10],
    [7, 7, 7, 8, 9, 9, 9, 10, 10, 11, 11, 11],
    [8, 8, 8, 9, 10, 10, 10, 10, 10, 11, 11, 11],
    [9, 9, 9, 10, 10, 10, 11, 11, 11, 12, 12, 12],
    [10, 10, 10, 11, 11, 11, 11, 12, 12, 12, 12, 12],
    [11, 11, 11, 11, 12, 12, 12, 12, 12, 12, 12, 12],
    [12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12],
]


def _clamp(value, low, high):
    return max(low, min(high, int(value)))


def calculate_reba(data):
    trunk = _clamp(data.get("trunk_score") or 1, 1, 5)
    neck = _clamp(data.get("neck_score") or 1, 1, 3)
    legs = _clamp(data.get("legs_score") or 1, 1, 4)
    upper_arm = _clamp(data.get("upper_arm_score") or 1, 1, 6)
    lower_arm = _clamp(data.get("lower_arm_score") or 1, 1, 2)
    wrist = _clamp(data.get("wrist_score") or 1, 1, 3)
    load_force = _clamp(data.get("load_force_score") or 0, 0, 3)
    coupling = _clamp(data.get("coupling_score") or 0, 0, 3)
    activity = _clamp(data.get("activity_score") or 0, 0, 3)

    score_a_posture = TABLE_A[neck][trunk - 1][legs - 1]
    score_a = min(score_a_posture + load_force, 12)

    score_b_posture = TABLE_B[upper_arm][lower_arm - 1][wrist - 1]
    score_b = min(score_b_posture + coupling, 12)

    score_c = TABLE_C[score_a - 1][score_b - 1]
    final_score = min(score_c + activity, 15)

    if final_score == 1:
        level, action_level = "LOW", "Negligible risk"
    elif final_score <= 3:
        level, action_level = "LOW", "Low risk, action may be needed"
    elif final_score <= 7:
        level, action_level = "MEDIUM", "Medium risk, further investigation, change soon"
    elif final_score <= 10:
        level, action_level = "HIGH", "High risk, investigate and implement change soon"
    else:
        level, action_level = "VERY_HIGH", "Very high risk, implement change immediately"

    return {
        "score": final_score,
        "score_a": score_a,
        "score_b": score_b,
        "risk_level": level,
        "action_level": action_level,
        "recommended_action": recommended_action_for_level(level),
    }