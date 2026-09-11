from decimal import Decimal, ROUND_HALF_UP


def score(value, target, direction):
    """Target attainment normalized to 0–100; lower-is-better uses target/value."""
    if value is None or target is None or target <= 0: return None
    ratio = value / target if direction == "HIGHER_IS_BETTER" else target / value if value > 0 else Decimal("1")
    return min(Decimal("100"), max(Decimal("0"), ratio * 100)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)


calculate_kpi_score = score


def calculate_overall_score(category_scores):
    """category_scores is iterable of (score, configured category weight)."""
    valid = [(Decimal(str(s)), Decimal(str(w))) for s, w in category_scores if s is not None]
    if not valid: return Decimal("0.00")
    weight_total = sum(w for _, w in valid)
    return min(Decimal("100"), sum(s * w for s, w in valid) / weight_total).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
