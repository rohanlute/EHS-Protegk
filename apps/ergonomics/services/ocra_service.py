"""
OCRA Index — Occupational Repetitive Actions (Occhipinti & Colombini).

The OCRA Index compares the actual number of technical actions performed
in a shift against a "reference" number of actions for that task.

    OCRA Index = Actual Technical Actions / Reference Technical Actions

Reference Technical Actions for a shift:

    RTA = CF × Fp × Ff × Fr × Fa × Fc × Fd × 30

    CF = frequency constant (default 30 actions/min for the arm)
    Fp = posture multiplier
    Ff = force multiplier
    Fr = repetitiveness multiplier
    Fa = additional factors multiplier (vibration, precision, etc.)
    Fc = recovery period multiplier
    Fd = duration multiplier
    30 = multiplier that converts per-minute reference to per-shift

Interpretation (per Occhipinti & Colombini):
    Index ≤ 2.2       -> LOW       (acceptable)
    2.3 ≤ Index ≤ 3.5 -> MEDIUM    (borderline / improve)
    3.6 ≤ Index ≤ 4.5 -> HIGH      (risk present, act soon)
    Index > 4.5       -> VERY_HIGH (serious risk, act immediately)

All multipliers come in as decimals (0.1 – 1.0) with 1.0 meaning "best
case, no penalty". They are supplied by the assessor via the OCRA form.
"""
from .risk_service import recommended_action_for_level


def calculate_ocra(data):
    """
    `data` is a dict-like (typically `model.__dict__`) with:
        actual_actions             integer count per shift
        constant_frequency         float, typically 30
        posture_multiplier         float 0.1..1.0
        force_multiplier           float 0.1..1.0
        repetitiveness_multiplier  float 0.1..1.0
        additional_multiplier      float 0.1..1.0
        recovery_multiplier        float 0.1..1.0
        duration_multiplier        float 0.1..1.0
    """
    actual = float(data.get("actual_actions") or 0)
    cf = float(data.get("constant_frequency") or 30)

    # Clamp each multiplier to (0, 1]. Anything above 1 would imply "better
    # than ideal", which is not physically meaningful; anything <= 0 makes
    # the index undefined.
    def _clamp_multiplier(v, default=1.0):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return default
        if f <= 0:
            return 0.01  # avoid divide-by-zero; will yield a huge index
        return min(f, 1.0)

    fp = _clamp_multiplier(data.get("posture_multiplier"), 1.0)
    ff = _clamp_multiplier(data.get("force_multiplier"), 1.0)
    fr = _clamp_multiplier(data.get("repetitiveness_multiplier"), 1.0)
    fa = _clamp_multiplier(data.get("additional_multiplier"), 1.0)
    fc = _clamp_multiplier(data.get("recovery_multiplier"), 1.0)
    fd = _clamp_multiplier(data.get("duration_multiplier"), 1.0)

    reference_actions = cf * fp * ff * fr * fa * fc * fd * 30

    if reference_actions <= 0:
        index = 99.99
    else:
        index = round(actual / reference_actions, 2)

    if index <= 2.2:
        level = "LOW"
        action_level = "Acceptable — no action required"
    elif index <= 3.5:
        level = "MEDIUM"
        action_level = "Borderline — improve workstation / rotation"
    elif index <= 4.5:
        level = "HIGH"
        action_level = "Risk present — corrective action required"
    else:
        level = "VERY_HIGH"
        action_level = "Serious risk — immediate action required"

    return {
        "score": index,
        "reference_actions": round(reference_actions, 2),
        "action_level": action_level,
        "risk_level": level,
        "recommended_action": recommended_action_for_level(level),
    }