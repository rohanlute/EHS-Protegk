"""Safely initialize a usable plant-scoped benchmark configuration from real EHS data."""
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.benchmarking.models import (BenchmarkCategory, BenchmarkFramework, BenchmarkKPI, BenchmarkPerformanceLevel, BenchmarkPeriod, BenchmarkTarget,)
from apps.benchmarking.services import calculate_period
from apps.organizations.models import Plant


class Command(BaseCommand):
    help = "Initialize a plant-only CAPA benchmark configuration and calculate it from actual source records."

    def add_arguments(self, parser):
        parser.add_argument("--start", default="2026-09-01", help="Calculation start date (YYYY-MM-DD).")
        parser.add_argument("--end", default="2026-09-30", help="Calculation end date (YYYY-MM-DD).")

    @transaction.atomic
    def handle(self, *args, **options):
        start = date.fromisoformat(options["start"])
        end = date.fromisoformat(options["end"])
        framework, _ = BenchmarkFramework.objects.get_or_create(
            code="PLANT-EHS-2026",
            defaults={"name": "Plant EHS Benchmark 2026", "description": "Plant-scoped benchmark calculated from real EHS source data.", "effective_from": start, "reporting_frequency": "MONTH", "status": "ACTIVE"},
        )
        category, _ = BenchmarkCategory.objects.get_or_create(
            framework=framework, code="CAPA", defaults={"name": "Corrective Action Performance", "description": "CAPA closure performance by plant.", "weightage": 100, "display_order": 1, "is_active": True},
        )
        kpi, _ = BenchmarkKPI.objects.get_or_create(
            category=category, code="CAPA_CLOSURE_RATE",
            defaults={"name": "CAPA Closure Rate", "description": "Closed CAPAs divided by total CAPAs created in the benchmark period.", "unit": "%", "calculation_type": "PERCENTAGE", "direction": "HIGHER_IS_BETTER", "weightage": 100, "frequency": "MONTH", "calculator_code": "CAPA_CLOSURE_RATE", "source_module": "capa", "is_active": True},
        )
        for name, minimum, maximum, order in [("Excellent", 90, 100, 1), ("Good", 75, 89.99, 2), ("Average", 60, 74.99, 3), ("Below Average", 0, 59.99, 4)]:
            BenchmarkPerformanceLevel.objects.get_or_create(framework=framework, name=name, defaults={"minimum_score": minimum, "maximum_score": maximum, "display_order": order, "is_active": True})
        for plant in Plant.objects.filter(is_active=True):
            BenchmarkTarget.objects.get_or_create(framework=framework, kpi=kpi, plant=plant, target_type="PLANT", effective_from=start, defaults={"target_value": 80})
        period, _ = BenchmarkPeriod.objects.get_or_create(framework=framework, period_type="MONTH", start_date=start, end_date=end)
        calculate_period(period)
        results = period.results.filter(scope_type="PLANT").count()
        self.stdout.write(self.style.SUCCESS(f"Initialized {framework.name}; calculated {results} plant result(s) from actual CAPA records."))
