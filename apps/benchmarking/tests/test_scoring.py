from decimal import Decimal
from django.test import SimpleTestCase
from apps.benchmarking.engine.scoring import calculate_kpi_score, calculate_overall_score


class ScoringTests(SimpleTestCase):
    def test_higher_is_better_is_capped(self): self.assertEqual(calculate_kpi_score(Decimal("95"), Decimal("90"), "HIGHER_IS_BETTER"), Decimal("100.00"))
    def test_lower_is_better(self): self.assertEqual(calculate_kpi_score(Decimal("0.6"), Decimal("1"), "LOWER_IS_BETTER"), Decimal("100.00"))
    def test_weighted_score(self): self.assertEqual(calculate_overall_score([(Decimal("80"), Decimal("60")), (Decimal("50"), Decimal("40"))]), Decimal("68.00"))
