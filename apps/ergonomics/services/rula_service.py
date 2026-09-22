"""
RULA (Rapid Upper Limb Assessment) — McAtamney & Corlett (1993).

This implements the real Table A / Table B / Table C lookups instead of an
additive approximation. Do not "simplify" this back to a sum — the whole
point of RULA is that the tables are non-linear.
"""
from .risk_service import recommended_action_for_level

# ---------------------------------------------------------------------------
# TABLE A — Posture Score A
# Keyed by (upper_arm 1-6, lower_arm 1-3) -> 8 values for:
#   wrist1+twist1, wrist1+twist2, wrist2+twist1, wrist2+twist2,
#   wrist3+twist1, wrist3+twist2, wrist4+twist1, wrist4+twist2
# ---------------------------------------------------------------------------
TABLE_A = {
    (1, 1): [1, 2, 2, 2, 2, 3, 3, 3],
    (1, 2): [2, 2, 2, 2, 3, 3, 3, 3],
    (1, 3): [2, 3, 3, 3, 3, 3, 4, 4],
    (2, 1): [2, 3, 3, 3, 3, 4, 4, 4],
    (2, 2): [3, 3, 3, 3, 3, 4, 4, 4],
    (2, 3): [3, 4, 4, 4, 4, 4, 5, 5],
    (3, 1): [3, 3, 4, 4, 4, 4, 5, 5],
    (3, 2): [3, 4, 4, 4, 4, 4, 5, 5],
    (3, 3): [4, 4, 4, 4, 4, 5, 5, 5],
    (4, 1): [4, 4, 4, 4, 4, 5, 5, 5],
    (4, 2): [4, 4, 4, 4, 4, 5, 5, 5],
    (4, 3): [4, 4, 4, 5, 5, 5, 6, 6],
    (5, 1): [5, 5, 5, 5, 5, 6, 6, 7],
    (5, 2): [5, 6, 6, 6, 6, 7, 7, 7],
    (5, 3): [6, 6, 6, 7, 7, 7, 7, 8],
    (6, 1): [7, 7, 7, 7, 7, 8, 8, 9],
    (6, 2): [8, 8, 8, 8, 8, 9, 9, 9],
    (6, 3): [9, 9, 9, 9, 9, 9, 9, 9],
}

# ---------------------------------------------------------------------------
# TABLE B — Posture Score B
# Keyed by neck (1-6) -> list of 6 (legs1, legs2) tuples for trunk 1-6
# ---------------------------------------------------------------------------
TABLE_B = {
    1: [(1, 3), (2, 3), (3, 4), (5, 5), (6, 6), (7, 7)],
    2: [(2, 3), (2, 3), (4, 5), (5, 5), (6, 7), (7, 7)],
    3: [(3, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 7)],
    4: [(5, 5), (5, 6), (6, 7), (7, 7), (7, 7), (8, 8)],
    5: [(7, 7), (7, 7), (7, 8), (8, 8), (8, 8), (8, 8)],
    6: [(8, 8), (8, 8), (8, 8), (8, 9), (9, 9), (9, 9)],
}

# ---------------------------------------------------------------------------
# TABLE C — Grand Score, rows = Score A (1-8, 8 = "8+"), cols = Score B (1-7, 7 = "7+")
# ---------------------------------------------------------------------------
TABLE_C = [
    [1, 2, 3, 3, 4, 5, 5],
    [2, 2, 3, 4, 4, 5, 5],
    [3, 3, 3, 4, 4, 5, 6],
    [3, 3, 3, 4, 5, 6, 6],
    [4, 4, 4, 5, 6, 7, 7],
    [4, 4, 5, 6, 6, 7, 7],
    [5, 5, 6, 6, 7, 7, 7],
    [5, 5, 6, 7, 7, 7, 7],
]


def _clamp(value, low, high):
    return max(low, min(high, int(value)))


def calculate_rula(data):
    upper_arm = _clamp(data.get("upper_arm_score") or 1, 1, 6)
    lower_arm = _clamp(data.get("lower_arm_score") or 1, 1, 3)
    wrist = _clamp(data.get("wrist_score") or 1, 1, 4)
    wrist_twist = _clamp(data.get("wrist_twist_score") or 1, 1, 2)
    neck = _clamp(data.get("neck_score") or 1, 1, 6)
    trunk = _clamp(data.get("trunk_score") or 1, 1, 6)
    leg = _clamp(data.get("leg_score") or 1, 1, 2)
    muscle_use = _clamp(data.get("muscle_use_score") or 0, 0, 1)
    force_load = _clamp(data.get("force_load_score") or 0, 0, 3)

    # --- Table A lookup ---
    col_index = (wrist - 1) * 2 + (wrist_twist - 1)  # 0..7
    score_a_posture = TABLE_A[(upper_arm, lower_arm)][col_index]
    score_a = min(score_a_posture + muscle_use + force_load, 8)  # 8 = "8+" row

    # --- Table B lookup ---
    legs_pair = TABLE_B[neck][trunk - 1]
    score_b_posture = legs_pair[leg - 1]
    score_b = min(score_b_posture + muscle_use + force_load, 7)  # 7 = "7+" column

    # --- Table C lookup (grand score) ---
    final_score = TABLE_C[score_a - 1][score_b - 1]

    if final_score <= 2:
        level, action_level = "LOW", "Action Level 1"
    elif final_score <= 4:
        level, action_level = "MEDIUM", "Action Level 2"
    elif final_score <= 6:
        level, action_level = "HIGH", "Action Level 3"
    else:
        level, action_level = "VERY_HIGH", "Action Level 4"

    return {
        "score": final_score,
        "score_a": score_a,
        "score_b": score_b,
        "risk_level": level,
        "action_level": action_level,
        "recommended_action": recommended_action_for_level(level),
    }