"""Controlled KPI calculators. Unsupported codes deliberately return unavailable."""
from decimal import Decimal
from django.db.models import Avg


def _capa_closure_rate(plant, department, start, end):
    from apps.capa.models import CAPA
    qs = CAPA.objects.filter(created_at__date__range=(start, end))
    if plant: qs = qs.filter(plant=plant)
    if department: qs = qs.filter(department=department)
    total = qs.count()
    closed = qs.filter(status=CAPA.Status.CLOSED).count()
    return (Decimal(closed) * 100 / total if total else None), total


def _hazard_closure_rate(plant, department, start, end):
    from apps.hazards.models import Hazard
    qs = Hazard.objects.filter(incident_datetime__date__range=(start, end))
    if plant: qs = qs.filter(plant=plant)
    # Hazard has no department relation: plant-only calculation is intentional.
    total = qs.count(); closed = qs.filter(status="CLOSED").count()
    return (Decimal(closed) * 100 / total if total else None), total


def _inspection_score(plant, department, start, end):
    from apps.inspections.models import InspectionSubmission
    qs = InspectionSubmission.objects.filter(submitted_at__date__range=(start, end))
    if plant: qs = qs.filter(schedule__plants=plant)
    if department: qs = qs.filter(schedule__department=department)
    count = qs.count(); value = qs.aggregate(value=Avg("compliance_score"))["value"]
    return (Decimal(str(value)) if value is not None else None), count


registered_calculators = {
    "CAPA_CLOSURE_RATE": _capa_closure_rate,
    "HAZARD_CLOSURE_RATE": _hazard_closure_rate,
    "INSPECTION_SCORE": _inspection_score,
}


def calculate_kpi_value(code, plant, department, start, end):
    calculator = registered_calculators.get(code)
    return calculator(plant, department, start, end) if calculator else (None, 0)
