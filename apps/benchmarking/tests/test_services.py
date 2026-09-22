from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.benchmarking.services import refresh_live_results_for_all, refresh_live_results_for_plants
from apps.benchmarking.tasks import refresh_live_benchmark_results


class LiveRefreshTests(SimpleTestCase):
    @patch("apps.benchmarking.services.calculate_period")
    @patch("apps.benchmarking.services.Plant.objects.filter")
    @patch("apps.benchmarking.services.BenchmarkPeriod.objects.filter")
    def test_refresh_all_uses_active_plants(self, period_filter, plant_filter, calculate_period):
        plants = object()
        plant_filter.return_value = plants
        period_filter.return_value.exclude.return_value.select_related.return_value = []

        refresh_live_results_for_all()

        plant_filter.assert_called_once_with(is_active=True)
        calculate_period.assert_not_called()

    @patch("apps.benchmarking.tasks.refresh_live_results_for_all")
    def test_celery_task_refreshes_live_results(self, refresh):
        result = refresh_live_benchmark_results()

        refresh.assert_called_once_with()
        self.assertEqual(result, "Live benchmark results refreshed.")

    @patch("apps.benchmarking.services.calculate_period")
    @patch("apps.benchmarking.services.timezone.localdate", return_value=date(2026, 9, 21))
    def test_refresh_recalculates_current_unpublished_periods(self, localdate, calculate_period):
        period = type("Period", (), {"Status": type("Status", (), {"PUBLISHED": "PUBLISHED"})})()
        period_queryset = type("Periods", (), {
            "exclude": lambda self, **kwargs: self,
            "select_related": lambda self, *args: self,
            "__iter__": lambda self: iter([period]),
        })()
        plants = object()

        with patch("apps.benchmarking.services.BenchmarkPeriod.objects.filter", return_value=period_queryset):
            refresh_live_results_for_plants(plants)

        calculate_period.assert_called_once_with(period, plants=plants)
