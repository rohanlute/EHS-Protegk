"""
OWAS — Ovako Working Posture Analysing System (Karhu et al., 1977).

The method scores a work posture across four dimensions:
    Back  (1-4)  1 straight, 2 bent, 3 bent+twisted, 4 straight+twisted
    Arms  (1-3)  1 both below shoulder, 2 one at/above, 3 both at/above
    Legs  (1-6)  1 sitting, 2 standing straight, 3 one leg straight,
                 4 both bent, 5 kneeling, 6 walking
    Load  (1-3)  1 <10 kg, 2 10-20 kg, 3 >20 kg

The 4-digit code maps to an Action Category (AC 1-4):
    1 = no action required
    2 = action in the near future
    3 = action as soon as possible
    4 = action immediately

The real OWAS table has 252 entries. Below is a fully functional subset
covering the most common industrial postures. Any missing combination
falls back to a heuristic that reads the same direction as the official
table (higher back twist / heavier load → higher AC).
"""
from .risk_service import recommended_action_for_level


# Key: (back, arms, legs, load) -> Action Category (1-4)
_OWAS_TABLE = {
    # ----- Straight back, arms below shoulder -----
    (1, 1, 1, 1): 1,   # sitting, light
    (1, 1, 1, 2): 1,
    (1, 1, 1, 3): 2,

    (1, 1, 2, 1): 1,   # standing straight, light
    (1, 1, 2, 2): 2,
    (1, 1, 2, 3): 3,

    (1, 1, 3, 1): 1,   # one leg
    (1, 1, 3, 2): 2,
    (1, 1, 3, 3): 3,

    (1, 1, 4, 1): 2,   # both bent
    (1, 1, 4, 2): 3,
    (1, 1, 4, 3): 3,

    (1, 1, 5, 1): 2,   # kneeling
    (1, 1, 5, 2): 3,
    (1, 1, 5, 3): 4,

    (1, 1, 6, 1): 1,   # walking
    (1, 1, 6, 2): 2,
    (1, 1, 6, 3): 3,

    # ----- Bent back -----
    (2, 1, 1, 1): 2,
    (2, 1, 1, 2): 2,
    (2, 1, 1, 3): 3,

    (2, 1, 2, 1): 2,   # most common: bent forward standing
    (2, 1, 2, 2): 3,
    (2, 1, 2, 3): 3,

    (2, 1, 3, 1): 3,
    (2, 1, 3, 2): 3,
    (2, 1, 3, 3): 4,

    (2, 1, 4, 1): 3,
    (2, 1, 4, 2): 4,
    (2, 1, 4, 3): 4,

    (2, 1, 5, 1): 3,
    (2, 1, 5, 2): 4,
    (2, 1, 5, 3): 4,

    (2, 1, 6, 1): 2,
    (2, 1, 6, 2): 3,
    (2, 1, 6, 3): 3,

    # ----- Bent + twisted back -----
    (3, 1, 1, 1): 3,
    (3, 1, 1, 2): 3,
    (3, 1, 1, 3): 4,

    (3, 1, 2, 1): 3,
    (3, 1, 2, 2): 3,
    (3, 1, 2, 3): 4,

    (3, 1, 3, 1): 4,
    (3, 1, 3, 2): 4,
    (3, 1, 3, 3): 4,

    (3, 1, 4, 1): 4,
    (3, 1, 4, 2): 4,
    (3, 1, 4, 3): 4,

    (3, 1, 5, 1): 4,
    (3, 1, 5, 2): 4,
    (3, 1, 5, 3): 4,

    (3, 1, 6, 1): 3,
    (3, 1, 6, 2): 3,
    (3, 1, 6, 3): 4,

    # ----- Straight + twisted back -----
    (4, 1, 1, 1): 3,
    (4, 1, 1, 2): 3,
    (4, 1, 1, 3): 4,

    (4, 1, 2, 1): 3,
    (4, 1, 2, 2): 4,
    (4, 1, 2, 3): 4,

    (4, 1, 3, 1): 3,
    (4, 1, 3, 2): 4,
    (4, 1, 3, 3): 4,

    (4, 1, 4, 1): 4,
    (4, 1, 4, 2): 4,
    (4, 1, 4, 3): 4,

    (4, 1, 5, 1): 4,
    (4, 1, 5, 2): 4,
    (4, 1, 5, 3): 4,

    (4, 1, 6, 1): 3,
    (4, 1, 6, 2): 4,
    (4, 1, 6, 3): 4,

    # ----- Arms at/above shoulder (arms=2) escalate AC by 1 -----
    (1, 2, 2, 1): 2,
    (1, 2, 2, 2): 3,
    (2, 2, 2, 1): 3,
    (2, 2, 2, 2): 3,
    (3, 2, 2, 1): 4,
    (3, 2, 2, 2): 4,

    # ----- Arms both above shoulder (arms=3) escalate AC by 1 more -----
    (1, 3, 2, 1): 3,
    (1, 3, 2, 2): 3,
    (2, 3, 2, 1): 3,
    (2, 3, 2, 2): 4,
    (3, 3, 2, 1): 4,
    (3, 3, 2, 2): 4,
}


_AC_ACTION = {
    1: "No action required",
    2: "Action in the near future",
    3: "Action as soon as possible",
    4: "Action immediately",
}

_AC_LEVEL = {
    1: "LOW",
    2: "MEDIUM",
    3: "HIGH",
    4: "VERY_HIGH",
}


def _fallback_category(back, arms, legs, load):
    """
    Heuristic used only if the exact (back, arms, legs, load) tuple is not
    in the table. Directionally correct: the worse the back/arms/load,
    the higher the action category.
    """
    score = 0
    if back >= 3:
        score += 2
    elif back == 2:
        score += 1

    if arms == 3:
        score += 2
    elif arms == 2:
        score += 1

    if legs in (4, 5):
        score += 1

    if load == 3:
        score += 2
    elif load == 2:
        score += 1

    if score <= 1:
        return 1
    if score <= 3:
        return 2
    if score <= 5:
        return 3
    return 4


def calculate_owas(data):
    """
    `data` is a dict-like (typically `model.__dict__`) with keys:
        back_score   1..4
        arms_score   1..3
        legs_score   1..6
        load_score   1..3
    """
    back = max(1, min(4, int(data.get("back_score") or 1)))
    arms = max(1, min(3, int(data.get("arms_score") or 1)))
    legs = max(1, min(6, int(data.get("legs_score") or 2)))
    load = max(1, min(3, int(data.get("load_score") or 1)))

    category = _OWAS_TABLE.get((back, arms, legs, load))
    if category is None:
        category = _fallback_category(back, arms, legs, load)

    level = _AC_LEVEL[category]

    return {
        "score": category,            # numeric AC 1..4 (stored in assessment.score)
        "action_level": _AC_ACTION[category],
        "risk_level": level,
        "recommended_action": recommended_action_for_level(level),
    }