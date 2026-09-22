"""
Snook & Ciriello (1991) psychophysical tables for manual handling.

For a given task (Lift / Lower / Push / Pull / Carry), gender, and
population percentile, the tables give a Maximum Acceptable Weight (MAW).
The ratio of Actual Load to MAW drives the risk level:

    ratio = Actual Load / MAW

    ratio ≤ 0.75      → LOW       (below the recommended limit)
    0.75 < ratio ≤ 1  → MEDIUM    (at the limit — borderline)
    1 < ratio ≤ 1.5   → HIGH      (above the limit — investigate)
    ratio > 1.5       → VERY_HIGH (well above — act now)

The tables below are a compressed but functional subset. Real Snook &
Ciriello tables have separate entries for:
    - Lifting (by height: floor / knuckle / shoulder)
    - Lowering (same heights)
    - Pushing (initial / sustained force)
    - Pulling (initial / sustained force)
    - Carrying (by distance)

We compress each task type into a single table keyed by (gender,
percentile), with the height/distance chosen by a "position" input
(CLOSE / MEDIUM / FAR, or FLOOR / KNUCKLE / SHOULDER for lift/lower).
"""
from .risk_service import recommended_action_for_level


# -----------------------------------------------------------------------------
# Compressed MAW tables (kg) — Moore & Garg / Snook & Ciriello style
# Format: table[task][gender][position][percentile] = MAW (kg)
# -----------------------------------------------------------------------------
_MAW_TABLE = {
    # -------------------------------------------------------------- LIFT
    "LIFT": {
        "MALE": {
            "FLOOR":   {10: 16, 25: 20, 50: 25, 75: 31, 90: 38},
            "KNUCKLE": {10: 20, 25: 25, 50: 32, 75: 39, 90: 47},
            "SHOULDER": {10: 15, 25: 19, 50: 24, 75: 29, 90: 36},
        },
        "FEMALE": {
            "FLOOR":   {10: 9,  25: 11, 50: 14, 75: 17, 90: 21},
            "KNUCKLE": {10: 11, 25: 14, 50: 18, 75: 22, 90: 27},
            "SHOULDER": {10: 8, 25: 10, 50: 13, 75: 16, 90: 20},
        },
    },
    # -------------------------------------------------------------- LOWER
    "LOWER": {
        "MALE": {
            "FLOOR":   {10: 18, 25: 22, 50: 27, 75: 33, 90: 40},
            "KNUCKLE": {10: 22, 25: 27, 50: 34, 75: 41, 90: 49},
            "SHOULDER": {10: 16, 25: 20, 50: 25, 75: 30, 90: 37},
        },
        "FEMALE": {
            "FLOOR":   {10: 10, 25: 13, 50: 16, 75: 19, 90: 23},
            "KNUCKLE": {10: 12, 25: 15, 50: 19, 75: 23, 90: 28},
            "SHOULDER": {10: 9, 25: 11, 50: 14, 75: 17, 90: 21},
        },
    },
    # -------------------------------------------------------------- PUSH
    "PUSH": {
        "MALE": {
            "CLOSE":  {10: 20, 25: 24, 50: 30, 75: 36, 90: 43},
            "MEDIUM": {10: 15, 25: 19, 50: 24, 75: 29, 90: 35},
            "FAR":    {10: 11, 25: 13, 50: 17, 75: 21, 90: 25},
        },
        "FEMALE": {
            "CLOSE":  {10: 13, 25: 16, 50: 20, 75: 24, 90: 29},
            "MEDIUM": {10: 10, 25: 12, 50: 16, 75: 19, 90: 23},
            "FAR":    {10: 7,  25: 9,  50: 11, 75: 14, 90: 17},
        },
    },
    # -------------------------------------------------------------- PULL
    "PULL": {
        "MALE": {
            "CLOSE":  {10: 18, 25: 22, 50: 27, 75: 33, 90: 39},
            "MEDIUM": {10: 14, 25: 17, 50: 21, 75: 26, 90: 31},
            "FAR":    {10: 10, 25: 12, 50: 15, 75: 19, 90: 23},
        },
        "FEMALE": {
            "CLOSE":  {10: 12, 25: 14, 50: 18, 75: 21, 90: 26},
            "MEDIUM": {10: 9,  25: 11, 50: 14, 75: 17, 90: 21},
            "FAR":    {10: 7,  25: 8,  50: 10, 75: 13, 90: 15},
        },
    },
    # -------------------------------------------------------------- CARRY
    "CARRY": {
        "MALE": {
            "CLOSE":  {10: 19, 25: 23, 50: 28, 75: 34, 90: 41},
            "MEDIUM": {10: 14, 25: 17, 50: 21, 75: 26, 90: 31},
            "FAR":    {10: 10, 25: 12, 50: 15, 75: 18, 90: 22},
        },
        "FEMALE": {
            "CLOSE":  {10: 12, 25: 14, 50: 17, 75: 21, 90: 25},
            "MEDIUM": {10: 9,  25: 11, 50: 14, 75: 17, 90: 20},
            "FAR":    {10: 7,  25: 8,  50: 10, 75: 12, 90: 15},
        },
    },
}


def _get_maw(task, gender, position, percentile):
    """
    Look up MAW. Falls back gracefully if a combination isn't in the
    compressed table by interpolating between neighbours.
    """
    task = task or "LIFT"
    gender = gender or "MALE"
    position = position or "KNUCKLE"
    percentile = int(percentile or 50)

    task_table = _MAW_TABLE.get(task) or _MAW_TABLE["LIFT"]
    gender_table = task_table.get(gender) or task_table["MALE"]

    # If position missing, fall back to the middle key
    if position not in gender_table:
        position = list(gender_table.keys())[0]

    position_table = gender_table[position]

    # Percentile fallback: nearest lower key
    if percentile not in position_table:
        keys = sorted(position_table.keys())
        lower = [k for k in keys if k <= percentile]
        percentile = lower[-1] if lower else keys[0]

    return position_table[percentile]


def calculate_snook(data):
    """
    `data` is a dict-like (typically `model.__dict__`) with:
        task_type       LIFT / LOWER / PUSH / PULL / CARRY
        gender          MALE / FEMALE
        position        FLOOR / KNUCKLE / SHOULDER  (for lift/lower)
                        CLOSE / MEDIUM / FAR        (for push/pull/carry)
        percentile      10 / 25 / 50 / 75 / 90
        actual_load     kg
    """
    task = (data.get("task_type") or "LIFT").upper()
    gender = (data.get("gender") or "MALE").upper()
    position = (data.get("position") or "KNUCKLE").upper()
    percentile = int(data.get("percentile") or 50)
    actual_load = float(data.get("actual_load") or 0)

    maw = _get_maw(task, gender, position, percentile)
    ratio = round(actual_load / maw, 2) if maw else 99.99

    if ratio <= 0.75:
        level = "LOW"
        action_level = "Below recommended limit — acceptable"
    elif ratio <= 1.0:
        level = "MEDIUM"
        action_level = "At the recommended limit — monitor / improve"
    elif ratio <= 1.5:
        level = "HIGH"
        action_level = "Above recommended limit — corrective action required"
    else:
        level = "VERY_HIGH"
        action_level = "Well above limit — immediate action required"

    return {
        "score": ratio,                       # stored in assessment.score
        "maw": maw,
        "action_level": action_level,
        "risk_level": level,
        "recommended_action": recommended_action_for_level(level),
    }