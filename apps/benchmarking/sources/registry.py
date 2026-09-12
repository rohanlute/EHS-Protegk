"""Plant-scoped, controlled KPI calculators using the project's real source models."""
from decimal import Decimal

from django.db.models import Avg, Count, Q


def _percentage(numerator, denominator):
    return (Decimal(numerator) * 100 / denominator if denominator else None), denominator


def _accident_closure_rate(plant, department, start, end):
    from apps.accidents.models import Incident
    qs = Incident.objects.filter(plant=plant, incident_date__range=(start, end))
    return _percentage(qs.filter(status="CLOSED").count(), qs.count())


def _audit_pass_rate(plant, department, start, end):
    from apps.audits.models import AuditResponse
    qs = AuditResponse.objects.filter(schedule__plants=plant, schedule__scheduled_date__range=(start, end), status__in=["PASS", "FAIL"]).distinct()
    return _percentage(qs.filter(status="PASS").count(), qs.count())


def _capa_closure_rate(plant, department, start, end):
    from apps.capa.models import CAPA
    qs = CAPA.objects.filter(plant=plant, created_at__date__range=(start, end))
    return _percentage(qs.filter(status=CAPA.Status.CLOSED).count(), qs.count())


def _chemical_inventory_compliance(plant, department, start, end):
    from apps.chemicals.models import Chemical
    qs = Chemical.objects.filter(plant=plant, receipt_date__range=(start, end))
    compliant = qs.filter(status__in=["in_stock", "low_stock"], expiration_date__gte=end).count()
    return _percentage(compliant, qs.count())


def _emergency_drill_completion(plant, department, start, end):
    from apps.emergency.models import EmergencySession
    qs = EmergencySession.objects.filter(plant=plant, scheduled_date__range=(start, end))
    return _percentage(qs.filter(status="COMPLETED").count(), qs.count())


def _hazard_closure_rate(plant, department, start, end):
    from apps.hazards.models import Hazard
    qs = Hazard.objects.filter(plant=plant, incident_datetime__date__range=(start, end))
    return _percentage(qs.filter(status="CLOSED").count(), qs.count())


def _inspection_score(plant, department, start, end):
    from apps.inspections.models import InspectionSubmission
    qs = InspectionSubmission.objects.filter(schedule__plants=plant, submitted_at__date__range=(start, end)).distinct()
    value = qs.aggregate(value=Avg("compliance_score"))["value"]
    return (Decimal(str(value)) if value is not None else None), qs.count()


def _permit_closure_rate(plant, department, start, end):
    from apps.permit.models import Permit
    qs = Permit.objects.filter(plant=plant, start_date__date__range=(start, end))
    return _percentage(qs.filter(status="closed").count(), qs.count())


def _ppe_inspection_completion(plant, department, start, end):
    from apps.PPE.models import PPEInspectionSchedule
    qs = PPEInspectionSchedule.objects.filter(plant=plant, scheduled_date__range=(start, end))
    return _percentage(qs.filter(status="COMPLETED").count(), qs.count())


def _toolbox_talk_completion(plant, department, start, end):
    from apps.toolbox_talk.models import ToolboxTalkSessionPlan
    qs = ToolboxTalkSessionPlan.objects.filter(plants=plant, planned_date__range=(start, end)).distinct()
    return _percentage(qs.filter(status="COMPLETED").count(), qs.count())


def _training_completion(plant, department, start, end):
    from apps.training.models import TrainingSession
    qs = TrainingSession.objects.filter(plant=plant, scheduled_date__range=(start, end))
    return _percentage(qs.filter(status="COMPLETED").count(), qs.count())


registered_calculators = {
    "ACCIDENT_CLOSURE_RATE": _accident_closure_rate,
    "AUDIT_PASS_RATE": _audit_pass_rate,
    "CAPA_CLOSURE_RATE": _capa_closure_rate,
    "CHEMICAL_INVENTORY_COMPLIANCE": _chemical_inventory_compliance,
    "EMERGENCY_DRILL_COMPLETION": _emergency_drill_completion,
    "HAZARD_CLOSURE_RATE": _hazard_closure_rate,
    "INSPECTION_SCORE": _inspection_score,
    "PERMIT_CLOSURE_RATE": _permit_closure_rate,
    "PPE_INSPECTION_COMPLETION": _ppe_inspection_completion,
    "TOOLBOX_TALK_COMPLETION": _toolbox_talk_completion,
    "TRAINING_COMPLETION_RATE": _training_completion,
}


def calculate_kpi_value(code, plant, department, start, end, source_module=None):
    """Calculate a registered KPI. source_module is accepted for service compatibility."""
    calculator = registered_calculators.get(code)
    return calculator(plant, department, start, end) if calculator else (None, 0)
