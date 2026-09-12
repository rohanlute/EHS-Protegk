"""Safely initialize a usable plant-scoped benchmark configuration from real EHS data."""
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.benchmarking.models import (BenchmarkCategory, BenchmarkFramework, BenchmarkKPI, BenchmarkPerformanceLevel, BenchmarkPeriod, BenchmarkTarget,)
from apps.benchmarking.services import calculate_period
from apps.organizations.models import Plant


class Command(BaseCommand):
    help = "Initialize plant-only KPIs for all supported source modules and calculate real source data."

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
        definitions = [
            ("ACCIDENT", "Accident Management", "ACCIDENT_CLOSURE_RATE", "Incident Closure Rate", "accidents", 9.09),
            ("AUDIT", "Audit Performance", "AUDIT_PASS_RATE", "Audit Pass Rate", "audits", 9.09),
            ("CAPA", "Corrective Action Performance", "CAPA_CLOSURE_RATE", "CAPA Closure Rate", "capa", 9.09),
            ("CHEMICAL", "Chemical Management", "CHEMICAL_INVENTORY_COMPLIANCE", "Chemical Inventory Compliance", "chemicals", 9.09),
            ("EMERGENCY", "Emergency Preparedness", "EMERGENCY_DRILL_COMPLETION", "Emergency Drill Completion", "emergency", 9.09),
            ("HAZARD", "Hazard Management", "HAZARD_CLOSURE_RATE", "Hazard Closure Rate", "hazards", 9.09),
            ("INSPECTION", "Inspection Performance", "INSPECTION_SCORE", "Inspection Compliance Score", "inspections", 9.09),
            ("PERMIT", "Permit-to-Work", "PERMIT_CLOSURE_RATE", "Permit Closure Rate", "permit", 9.09),
            ("PPE", "PPE Inspection", "PPE_INSPECTION_COMPLETION", "PPE Inspection Completion", "PPE", 9.09),
            ("TOOLBOX", "Toolbox Talk", "TOOLBOX_TALK_COMPLETION", "Toolbox Talk Completion", "toolbox_talk", 9.09),
            ("TRAINING", "Training Competency", "TRAINING_COMPLETION_RATE", "Training Completion Rate", "training", 9.10),
        ]
        kpis = []
        for order, (code, category_name, calculator_code, kpi_name, source_module, weightage) in enumerate(definitions, 1):
            category, _ = BenchmarkCategory.objects.update_or_create(
                framework=framework, code=code,
                defaults={"name": category_name, "description": f"Plant-level {category_name.lower()} measure.", "weightage": weightage, "display_order": order, "is_active": True},
            )
            kpi, _ = BenchmarkKPI.objects.update_or_create(
                category=category, code=calculator_code,
                defaults={"name": kpi_name, "description": f"Plant-scoped {kpi_name.lower()} from the {source_module} module.", "unit": "%", "calculation_type": "PERCENTAGE", "direction": "HIGHER_IS_BETTER", "weightage": 100, "frequency": "MONTH", "calculator_code": calculator_code, "source_module": source_module, "is_active": True},
            )
            kpis.append(kpi)
        for name, minimum, maximum, order in [("Excellent", 90, 100, 1), ("Good", 75, 89.99, 2), ("Average", 60, 74.99, 3), ("Below Average", 0, 59.99, 4)]:
            BenchmarkPerformanceLevel.objects.get_or_create(framework=framework, name=name, defaults={"minimum_score": minimum, "maximum_score": maximum, "display_order": order, "is_active": True})
        for plant in Plant.objects.filter(is_active=True):
            for kpi in kpis:
                BenchmarkTarget.objects.get_or_create(framework=framework, kpi=kpi, plant=plant, target_type="PLANT", effective_from=start, defaults={"target_value": 80})
        period, _ = BenchmarkPeriod.objects.get_or_create(framework=framework, period_type="MONTH", start_date=start, end_date=end)
        calculate_period(period)
        results = period.results.filter(scope_type="PLANT").count()
        self.stdout.write(self.style.SUCCESS(f"Initialized {framework.name}; calculated {results} plant result(s) from real source modules."))
