"""
NIOSH Revised Lifting Equation (Waters et al., 1994).
Uses the real Table 5 (frequency multiplier) and Table 7 (coupling
multiplier), not a linear approximation.
"""
from .risk_service import recommended_action_for_level

LC = 23.0  # load constant (kg)

# Table 5 — Frequency Multiplier.
# Breakpoints are the *upper* bound of each frequency band; for an actual
# frequency <= breakpoint, use that row. Frequencies above the last
# breakpoint for a given duration/V category get FM = 0 (not recommended
# for manual lifting at that rate).
# Columns: (duration_hours upper bound, V>=75cm?) -> ((freq_breakpoint, fm), ...)
_FM_TABLE = {
    ("short", False): [(0.2, 1.00), (0.5, 0.97), (1, 0.94), (2, 0.91), (3, 0.88), (4, 0.84), (5, 0.80),
                        (6, 0.75), (7, 0.70), (8, 0.60), (9, 0.52), (10, 0.45), (11, 0.41), (12, 0.37)],
    ("short", True):  [(0.2, 1.00), (0.5, 0.97), (1, 0.94), (2, 0.91), (3, 0.88), (4, 0.84), (5, 0.80),
                        (6, 0.75), (7, 0.70), (8, 0.60), (9, 0.52), (10, 0.45), (11, 0.41), (12, 0.37),
                        (13, 0.34), (14, 0.31), (15, 0.28)],
    ("moderate", False): [(0.2, 0.95), (0.5, 0.92), (1, 0.88), (2, 0.84), (3, 0.79), (4, 0.72), (5, 0.60),
                           (6, 0.50), (7, 0.42), (8, 0.35), (9, 0.30), (10, 0.26)],
    ("moderate", True): [(0.2, 0.95), (0.5, 0.92), (1, 0.88), (2, 0.84), (3, 0.79), (4, 0.72), (5, 0.60),
                          (6, 0.50), (7, 0.42), (8, 0.35), (9, 0.30), (10, 0.26), (11, 0.23), (12, 0.21)],
    ("long", False): [(0.2, 0.85), (0.5, 0.81), (1, 0.75), (2, 0.65), (3, 0.55), (4, 0.45), (5, 0.35),
                       (6, 0.27), (7, 0.22), (8, 0.18)],
    ("long", True): [(0.2, 0.85), (0.5, 0.81), (1, 0.75), (2, 0.65), (3, 0.55), (4, 0.45), (5, 0.35),
                      (6, 0.27), (7, 0.22), (8, 0.18), (9, 0.15), (10, 0.13)],
}


def _duration_bucket(duration_hours):
    if duration_hours <= 1:
        return "short"
    if duration_hours <= 2:
        return "moderate"
    return "long"  # up to 8 hours; beyond 8h NIOSH equation is not applicable


def _frequency_multiplier(frequency, duration_hours, vertical_location):
    bucket = _duration_bucket(duration_hours)
    v_ge_75 = vertical_location >= 75
    table = _FM_TABLE[(bucket, v_ge_75)]
    for breakpoint, fm in table:
        if frequency <= breakpoint:
            return fm
    return 0.0  # frequency exceeds table range - not recommended manually


# Table 7 — Coupling Multiplier
def _coupling_multiplier(coupling, vertical_location):
    v_ge_75 = vertical_location >= 75
    return {
        "GOOD": 1.00,
        "FAIR": 1.00 if v_ge_75 else 0.95,
        "POOR": 0.90,
    }.get(coupling, 0.95)


def calculate_niosh(data):
    load_weight = float(data.get("load_weight") or 0)
    horizontal = max(float(data.get("horizontal_location") or 25), 25)
    vertical = min(max(float(data.get("vertical_location") or 75), 0), 175)
    distance = max(float(data.get("vertical_travel_distance") or 25), 25)
    asymmetry = min(max(float(data.get("asymmetry_angle") or 0), 0), 135)
    frequency = float(data.get("frequency_lifts_per_minute") or 0.2)
    duration_hours = float(data.get("duration_hours") or 1)
    coupling = data.get("coupling") or "FAIR"

    hm = min(25.0 / horizontal, 1.0) if horizontal else 0
    vm = max(1 - (0.003 * abs(vertical - 75)), 0)
    dm = max(0.82 + (4.5 / distance), 0) if distance else 0
    am = max(1 - (0.0032 * asymmetry), 0)
    fm = _frequency_multiplier(frequency, duration_hours, vertical)
    cm = _coupling_multiplier(coupling, vertical)

    rwl = round(LC * hm * vm * dm * am * fm * cm, 2)
    lifting_index = round(load_weight / rwl, 2) if rwl else 99.99

    if lifting_index <= 1:
        level = "LOW"
    elif lifting_index <= 2:
        level = "MEDIUM"
    elif lifting_index <= 3:
        level = "HIGH"
    else:
        level = "VERY_HIGH"

    return {
        "recommended_weight_limit": rwl,
        "lifting_index": lifting_index,
        "hm": round(hm, 2),
        "vm": round(vm, 2),
        "dm": round(dm, 2),
        "am": round(am, 2),
        "fm": round(fm, 2),
        "cm": round(cm, 2),
        "risk_level": level,
        "recommended_action": recommended_action_for_level(level),
    }