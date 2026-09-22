"""
Strain Index (Moore & Garg, 1995).

A multiplier-based assessment for distal upper-extremity MSD risk
(hand, wrist, forearm) in repetitive tasks.

    SI = IE × IW × ID × IP × IH × IF × DD × DR

Each factor maps to a lookup table:

    IE  Intensity of Exertion          (Borg CR-10 based)
    IW  Duration of Exertion per cycle (% of cycle)
    ID  Efforts per Minute              (frequency)
    IP  Hand/Wrist Posture              (deviation severity)
    IH  Speed of Work                   (pace)
    IF  Duration of Task per Day        (hours)
    DD  Daily Duration                  (hours total)
    DR  Efforts per Hour                (hand/wrist recovery)

Risk bands:
    SI ≤ 3      → LOW       (safe)
    3 < SI ≤ 7  → MEDIUM    (uncertain, investigate)
    SI > 7      → HIGH      (hazardous, take action)
"""
from .risk_service import recommended_action_for_level


# -----------------------------------------------------------------------------
# Lookup tables (values from Moore & Garg, 1995)
# -----------------------------------------------------------------------------
INTENSITY_OF_EXERTION = {
    "LIGHT":          1,    # Borg CR-10 ≈ 1-2
    "SOMEWHAT_HARD":  3,    # ≈ 3
    "HARD":           6,    # ≈ 4-5
    "VERY_HARD":      9,    # ≈ 6-7
    "NEAR_MAXIMAL":  13,    # ≈ 8-10
}

DURATION_OF_EXERTION = {
    "<10":  0.5,   # <10 % of cycle
    "10-29": 1.0,
    "30-49": 1.5,
    "50-79": 2.0,
    ">=80":  3.0,
}

EFFORTS_PER_MINUTE = {
    "<4":   0.5,
    "4-8":  1.0,
    "9-14": 1.5,
    "15-19": 2.0,
    ">=20": 3.0,
}

HAND_WRIST_POSTURE = {
    "VERY_GOOD": 1.0,   # perfect neutral
    "GOOD":      1.0,   # near neutral
    "FAIR":      1.5,   # slight deviation
    "BAD":       2.0,   # marked deviation
    "VERY_BAD":  3.0,   # extreme deviation
}

SPEED_OF_WORK = {
    "VERY_SLOW": 1.0,
    "SLOW":      1.0,
    "FAIR":      1.0,
    "FAST":      1.5,
    "VERY_FAST": 2.0,
}

DURATION_PER_DAY_HOURS = {
    "<1":   0.25,
    "1-2":  0.5,
    "2-4":  0.75,
    "4-8":  1.0,
    ">=8":  1.5,
}

DAILY_DURATION_HOURS = {
    "<1":   0.25,
    "1-2":  0.5,
    "2-4":  0.75,
    "4-8":  1.0,
    ">=8":  1.5,
}

EFFORTS_PER_HOUR = {
    "0-1":  0.5,
    "2-3":  1.0,
    "4-5":  1.5,
    "6-7":  2.0,
    ">=8":  3.0,
}


def calculate_strain_index(data):
    """
    `data` is a dict-like (typically `model.__dict__`) with:
        intensity_of_exertion   choice key from INTENSITY_OF_EXERTION
        duration_of_exertion    choice key from DURATION_OF_EXERTION
        efforts_per_minute      choice key from EFFORTS_PER_MINUTE
        hand_wrist_posture      choice key from HAND_WRIST_POSTURE
        speed_of_work           choice key from SPEED_OF_WORK
        duration_per_day_hours  choice key from DURATION_PER_DAY_HOURS
        daily_duration_hours    choice key from DAILY_DURATION_HOURS
        efforts_per_hour        choice key from EFFORTS_PER_HOUR
    """
    ie = INTENSITY_OF_EXERTION.get(data.get("intensity_of_exertion") or "LIGHT", 1)
    iw = DURATION_OF_EXERTION.get(data.get("duration_of_exertion") or "<10", 0.5)
    id_ = EFFORTS_PER_MINUTE.get(data.get("efforts_per_minute") or "<4", 0.5)
    ip = HAND_WRIST_POSTURE.get(data.get("hand_wrist_posture") or "FAIR", 1.5)
    ih = SPEED_OF_WORK.get(data.get("speed_of_work") or "FAIR", 1.0)
    if_ = DURATION_PER_DAY_HOURS.get(data.get("duration_per_day_hours") or "<1", 0.25)
    dd = DAILY_DURATION_HOURS.get(data.get("daily_duration_hours") or "<1", 0.25)
    dr = EFFORTS_PER_HOUR.get(data.get("efforts_per_hour") or "0-1", 0.5)

    si = round(ie * iw * id_ * ip * ih * if_ * dd * dr, 2)

    if si <= 3:
        level = "LOW"
        action_level = "Safe — no action required"
    elif si <= 7:
        level = "MEDIUM"
        action_level = "Uncertain — investigate and consider improvement"
    else:
        level = "HIGH"
        action_level = "Hazardous — job modification required"

    return {
        "score": si,
        "action_level": action_level,
        "risk_level": level,
        "recommended_action": recommended_action_for_level(level),
    }