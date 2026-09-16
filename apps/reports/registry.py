# apps/reports/registry.py
"""
Central registry: maps module_slug → spec builder.

A module registers itself by calling register(slug, label)(builder_fn).
The builder_fn receives the Django `request` and returns a ReportSpec.
"""
REGISTRY = {}


def register(slug, label):
    """Decorator: @register('hira', 'HIRA')"""
    def wrapper(fn):
        REGISTRY[slug] = {"spec_builder": fn, "label": label}
        return fn
    return wrapper


# ══════════════════════════════════════════════════════════════
# 1. ACCIDENTS / INJURY
# ══════════════════════════════════════════════════════════════
@register("accidents", "Injury / Incident")
def build_accidents_for_request(request):
    from apps.accidents.models import Incident
    from apps.accidents.report_spec import build_accidents_spec

    qs = Incident.objects.select_related("plant", "zone", "location", "reported_by")
    is_admin = request.user.is_superuser or getattr(request.user, "is_admin_user", False)
    if not is_admin and hasattr(request.user, "get_all_plants"):
        qs = qs.filter(plant__in=request.user.get_all_plants())

    if request.GET.get("plant"):
        qs = qs.filter(plant_id=request.GET["plant"])
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])

    return build_accidents_spec(qs)


# ══════════════════════════════════════════════════════════════
# 2. HAZARDS
# ══════════════════════════════════════════════════════════════
@register("hazards", "Hazards")
def build_hazards_for_request(request):
    from apps.hazards.models import Hazard
    from apps.hazards.report_spec import build_hazards_spec

    qs = Hazard.objects.select_related(
        "plant", "zone", "location", "reported_by", "assigned_to"
    )
    is_admin = request.user.is_superuser or getattr(request.user, "is_admin_user", False)
    if not is_admin and hasattr(request.user, "get_all_plants"):
        qs = qs.filter(plant__in=request.user.get_all_plants())

    if request.GET.get("plant"):
        qs = qs.filter(plant_id=request.GET["plant"])
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    if request.GET.get("severity"):
        qs = qs.filter(severity=request.GET["severity"])
    if request.GET.get("category"):
        qs = qs.filter(hazard_category=request.GET["category"])

    return build_hazards_spec(qs)


# ══════════════════════════════════════════════════════════════
# 3. PERMIT-TO-WORK
# ══════════════════════════════════════════════════════════════
@register("permit", "Permit-to-Work")
def build_permit_for_request(request):
    from apps.permit.models import Permit
    from apps.permit.report_spec import build_permit_spec

    qs = Permit.objects.select_related(
        "plant", "zone", "location", "permit_type", "approver", "requester_user"
    )
    is_admin = request.user.is_superuser or getattr(request.user, "is_admin_user", False)
    if not is_admin and hasattr(request.user, "get_all_plants"):
        qs = qs.filter(plant__in=request.user.get_all_plants())

    if request.GET.get("plant"):
        qs = qs.filter(plant_id=request.GET["plant"])
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    if request.GET.get("type"):
        qs = qs.filter(permit_type_id=request.GET["type"])

    return build_permit_spec(qs)


# ══════════════════════════════════════════════════════════════
# 4. INSPECTIONS
# ══════════════════════════════════════════════════════════════
@register("inspections", "Inspections")
def build_inspections_for_request(request):
    from apps.inspections.models import InspectionResponse, InspectionSchedule
    from apps.inspections.report_spec import build_inspection_spec

    is_admin = request.user.is_superuser or getattr(request.user, "is_admin_user", False)

    schedules_qs = InspectionSchedule.objects.select_related("template", "assigned_to")
    if not is_admin and hasattr(request.user, "get_all_plants"):
        schedules_qs = schedules_qs.filter(
            plants__in=request.user.get_all_plants()
        ).distinct()

    if request.GET.get("plant"):
        schedules_qs = schedules_qs.filter(plants__id=request.GET["plant"])

    responses_qs = InspectionResponse.objects.filter(
        submission__schedule__in=schedules_qs
    )
    if request.GET.get("answer"):
        responses_qs = responses_qs.filter(answer=request.GET["answer"])

    return build_inspection_spec(responses_qs, schedules_qs)


# ══════════════════════════════════════════════════════════════
# 5. AUDITS
# ══════════════════════════════════════════════════════════════
@register("audits", "Audits")
def build_audits_for_request(request):
    from apps.audits.models import AuditFinding
    from apps.audits.report_spec import build_audits_spec

    qs = AuditFinding.objects.select_related(
        "parent_audit", "origin_question", "reviewed_by",
    ).prefetch_related("capas")

    is_admin = request.user.is_superuser or getattr(request.user, "is_admin_user", False)
    if not is_admin and hasattr(request.user, "get_all_plants"):
        qs = qs.filter(
            parent_audit__plants__in=request.user.get_all_plants()
        ).distinct()

    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    if request.GET.get("risk"):
        qs = qs.filter(risk_score=request.GET["risk"])

    return build_audits_spec(qs)


# ══════════════════════════════════════════════════════════════
# 6. TRAINING
# ══════════════════════════════════════════════════════════════
@register("training", "Training")
def build_training_for_request(request):
    from apps.training.models import TrainingRecord
    from apps.training.report_spec import build_training_spec

    qs = TrainingRecord.objects.select_related(
        "employee", "employee__department", "topic", "session", "created_by",
    )

    is_admin = request.user.is_superuser or getattr(request.user, "is_admin_user", False)
    if not is_admin and hasattr(request.user, "get_all_plants"):
        qs = qs.filter(employee__plant__in=request.user.get_all_plants()).distinct()

    # ── Existing filters ────────────────────────────────────
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    if request.GET.get("topic"):
        qs = qs.filter(topic_id=request.GET["topic"])

    # ── NEW: department filter ──────────────────────────────
    if request.GET.get("department"):
        qs = qs.filter(employee__department_id=request.GET["department"])

    # ── NEW: employee filter ────────────────────────────────
    if request.GET.get("employee"):
        qs = qs.filter(employee_id=request.GET["employee"])

    # ── NEW: date range (completed_date) ────────────────────
    if request.GET.get("date_from"):
        qs = qs.filter(completed_date__gte=request.GET["date_from"])
    if request.GET.get("date_to"):
        qs = qs.filter(completed_date__lte=request.GET["date_to"])

    # ── NEW: expiring soon only ─────────────────────────────
    if request.GET.get("expiring") == "1":
        from datetime import date, timedelta
        today = date.today()
        qs = qs.filter(
            valid_until__gte=today,
            valid_until__lte=today + timedelta(days=30),
        )

    # ── NEW: expired only ──────────────────────────────────
    if request.GET.get("expired") == "1":
        from datetime import date
        qs = qs.filter(valid_until__lt=date.today())

    # ── NEW: HIRA queryset (if you add a TrainingHIRA model) ─
    hira_qs = None
    try:
        from apps.training.models import TrainingHIRA
        hira_qs = TrainingHIRA.objects.select_related(
            "linked_record", "linked_record__employee",
        )
        if not is_admin and hasattr(request.user, "get_all_plants"):
            hira_qs = hira_qs.filter(
                linked_record__employee__plant__in=request.user.get_all_plants()
            ).distinct()
        if request.GET.get("risk_level"):
            # Filter by computed risk level band
            rl = request.GET["risk_level"]
            bands = {
                "Low":      (1, 4),
                "Medium":   (5, 9),
                "High":     (10, 16),
                "Critical": (17, 25),
            }
            if rl in bands:
                lo, hi = bands[rl]
                from django.db.models import F
                hira_qs = hira_qs.annotate(
                    risk_score=F("likelihood") * F("severity")
                ).filter(risk_score__gte=lo, risk_score__lte=hi)
        if request.GET.get("hazard_category"):
            hira_qs = hira_qs.filter(hazard_category=request.GET["hazard_category"])
    except ImportError:
        # TrainingHIRA model does not exist yet — HIRA sheet will be empty
        hira_qs = None

    return build_training_spec(qs, hira_qs=hira_qs, request=request)


# ════════════════════════════════════════════════════════════════════════
# 6A. HIRA MANAGEMENT
# ════════════════════════════════════════════════════════════════════════
@register("hira", "HIRA Management")
def build_hira_for_request(request):
    from apps.hira.forms import HIRAReportFilterForm
    from apps.hira.reports import filter_hira_queryset, filter_source_queryset, source_first_workbook_response, workbook_response

    form = HIRAReportFilterForm(request.GET or None, user=request.user)
    adapter, source_records = filter_source_queryset(request, form)
    if adapter:
        data = form.cleaned_data if form.is_valid() else request.GET
        return source_first_workbook_response(adapter, source_records, data=data)
    qs = filter_hira_queryset(request, form)
    return workbook_response(qs)


# ══════════════════════════════════════════════════════════════
# 7. LEGAL COMPLIANCE
# ══════════════════════════════════════════════════════════════
@register("legal_compliance", "Legal Compliance")
def build_legal_compliance_for_request(request):
    from apps.legal_compliance.models import ComplianceRequirement
    from apps.legal_compliance.report_spec import build_legal_compliance_spec

    qs = ComplianceRequirement.objects.select_related(
        "legal_act", "responsible_person", "reviewer",
    ).prefetch_related("applicable_plants")

    is_admin = request.user.is_superuser or getattr(request.user, "is_admin_user", False)
    if not is_admin and hasattr(request.user, "get_all_plants"):
        qs = qs.filter(
            applicable_plants__in=request.user.get_all_plants()
        ).distinct()

    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    if request.GET.get("criticality"):
        qs = qs.filter(criticality=request.GET["criticality"])

    return build_legal_compliance_spec(qs)


# ══════════════════════════════════════════════════════════════
# 8. TOOLBOX TALK
# ══════════════════════════════════════════════════════════════
@register("toolbox_talk", "Toolbox Talk")
def build_toolbox_talk_for_request(request):
    from apps.toolbox_talk.models import ToolboxTalkConduct
    from apps.toolbox_talk.report_spec import build_toolbox_talk_spec

    qs = ToolboxTalkConduct.objects.select_related(
        "session", "session__topic", "session__topic__category",
        "assignment", "assignment__assigned_to",
    ).prefetch_related("attendance_records")

    return build_toolbox_talk_spec(qs)
