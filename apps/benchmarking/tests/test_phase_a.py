from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase

from apps.accounts.models import User
from apps.benchmarking.models import (
    BenchmarkCategory,
    BenchmarkFramework,
    BenchmarkInsight,
    BenchmarkKPI,
    BenchmarkPeriod,
    BenchmarkPerformanceLevel,
    BenchmarkResult,
    BenchmarkTarget,
)
from apps.benchmarking.services import calculate_period
from apps.organizations.models import Plant


class PhaseACalculationTests(TestCase):
    def setUp(self):
        self.plant = Plant.objects.create(name="Phase A Plant", code="PHA", address="Address", city="City", state="State", pincode="000000")
        self.framework = BenchmarkFramework.objects.create(name="Phase A", code="PHASE-A", effective_from=date(2026, 1, 1))
        self.period = BenchmarkPeriod.objects.create(framework=self.framework, period_type="MONTH", start_date=date(2026, 9, 1), end_date=date(2026, 9, 30))
        BenchmarkPerformanceLevel.objects.create(framework=self.framework, name="Below", minimum_score=0, maximum_score=100)

    def add_kpi(self, category_code, category_weight, kpi_code, target):
        category = BenchmarkCategory.objects.create(framework=self.framework, name=category_code, code=category_code, weightage=category_weight)
        kpi = BenchmarkKPI.objects.create(category=category, name=kpi_code, code=kpi_code, direction="HIGHER_IS_BETTER", weightage=100, calculator_code=kpi_code)
        BenchmarkTarget.objects.create(framework=self.framework, kpi=kpi, target_type="PLANT", plant=self.plant, target_value=target, effective_from=date(2026, 1, 1))
        return kpi

    @patch("apps.benchmarking.services.calculate_kpi_value", return_value=(Decimal("0"), 1))
    def test_target_gap_uses_weighted_configured_targets(self, calculate_value):
        self.add_kpi("SAFETY", Decimal("60"), "KPI_ONE", Decimal("80"))
        self.add_kpi("RISK", Decimal("40"), "KPI_TWO", Decimal("50"))

        calculate_period(self.period, plants=[self.plant])

        result = BenchmarkResult.objects.get(period=self.period, plant=self.plant)
        self.assertEqual(result.target_score, Decimal("68.00"))
        self.assertEqual(result.target_gap, Decimal("-68.00"))

    @patch("apps.benchmarking.services.calculate_kpi_value", return_value=(Decimal("0"), 1))
    def test_missing_targets_persist_no_target_gap(self, calculate_value):
        category = BenchmarkCategory.objects.create(framework=self.framework, name="SAFETY", code="SAFETY", weightage=100)
        BenchmarkKPI.objects.create(category=category, name="Untargeted", code="UNTARGETED", direction="HIGHER_IS_BETTER", weightage=100, calculator_code="UNTARGETED")

        calculate_period(self.period, plants=[self.plant])

        result = BenchmarkResult.objects.get(period=self.period, plant=self.plant)
        self.assertIsNone(result.target_score)
        self.assertIsNone(result.target_gap)

    @patch("apps.benchmarking.services.calculate_kpi_value", return_value=(Decimal("0"), 1))
    def test_recalculation_is_idempotent_and_preserves_insight_status(self, calculate_value):
        self.add_kpi("SAFETY", Decimal("100"), "KPI_ONE", Decimal("80"))
        calculate_period(self.period, plants=[self.plant])
        result = BenchmarkResult.objects.get(period=self.period, plant=self.plant)
        insight = BenchmarkInsight.objects.get(benchmark_result=result)
        insight.status = "ACKNOWLEDGED"
        insight.save(update_fields=["status"])

        calculate_period(self.period, plants=[self.plant])

        self.assertEqual(BenchmarkResult.objects.filter(period=self.period, plant=self.plant).count(), 1)
        self.assertEqual(BenchmarkInsight.objects.filter(benchmark_result=result).count(), 1)
        self.assertEqual(BenchmarkInsight.objects.get(benchmark_result=result).status, "ACKNOWLEDGED")


class PhaseAViewTests(TestCase):
    def test_dashboard_get_never_refreshes_results(self):
        user = User.objects.create_superuser(username="phase-a-admin", email="phase-a@example.com", password="pass")
        client = Client()
        client.force_login(user)
        with patch("apps.benchmarking.views.refresh_live_results") as refresh:
            response = client.get("/benchmarking/")
        self.assertEqual(response.status_code, 200)
        refresh.assert_not_called()

    def test_refresh_endpoint_is_post_only_and_uses_current_user_scope(self):
        user = User.objects.create_superuser(username="phase-a-refresh", email="refresh@example.com", password="pass")
        client = Client()
        client.force_login(user)
        self.assertEqual(client.get("/benchmarking/refresh/").status_code, 405)
        with patch("apps.benchmarking.views.refresh_live_results") as refresh:
            response = client.post("/benchmarking/refresh/")
        self.assertEqual(response.status_code, 302)
        refresh.assert_called_once_with(user)
