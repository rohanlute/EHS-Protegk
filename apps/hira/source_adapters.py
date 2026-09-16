from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.urls import NoReverseMatch
from django.urls import reverse


@dataclass
class SourceInfo:
    source_type: str
    module_name: str
    record_id: int
    record_label: str
    record_date: object = None
    plant: object = None
    department: object = None
    process: str = ""
    activity: str = ""
    unsafe_act: str = ""
    unsafe_condition: str = ""
    existing_action: str = ""
    responsible_person: object = None
    target_date: object = None
    status: str = ""
    url: str = ""


class BaseSourceAdapter:
    source_type = ""
    module_name = ""
    model = None

    def queryset(self, user=None):
        qs = self.model.objects.all()
        if user and not user.is_superuser and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            if plants and hasattr(self.model, "plant"):
                qs = qs.filter(plant__in=plants)
        return qs

    def get(self, pk, user=None):
        return self.queryset(user).get(pk=pk)

    def content_type(self):
        return ContentType.objects.get_for_model(self.model)

    def source_info(self, obj):
        raise NotImplementedError

    def choices(self, user=None, limit=100):
        return [(obj.pk, self.source_info(obj).record_label) for obj in self.queryset(user)[:limit]]

    def filtered_queryset(self, data, user=None):
        return self.queryset(user)

    def hira_module_code(self):
        return self.module_name.lower().replace(" ", "-")


def _value_id(value):
    return getattr(value, "pk", value) if value else None


def _financial_year_bounds(value):
    if not value:
        return None, None
    try:
        start_year = int(str(value)[:4])
    except (TypeError, ValueError):
        return None, None
    return f"{start_year}-04-01", f"{start_year + 1}-03-31"


def _safe_reverse(viewname, **kwargs):
    try:
        return reverse(viewname, kwargs=kwargs)
    except NoReverseMatch:
        return ""


def _display(obj, field):
    if not obj:
        return ""
    method = getattr(obj, f"get_{field}_display", None)
    return method() if method else getattr(obj, field, "")


class TrainingSessionAdapter(BaseSourceAdapter):
    source_type = "training"
    module_name = "Training Management"

    @property
    def model(self):
        from apps.training.models import TrainingSession

        return TrainingSession

    def queryset(self, user=None):
        qs = self.model.objects.select_related("topic", "plant", "location", "created_by").order_by("-scheduled_date")
        if user and not user.is_superuser and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            qs = qs.filter(plant__in=plants) if plants else qs.none()
        return qs

    def source_info(self, obj):
        return SourceInfo(
            source_type=self.source_type,
            module_name=self.module_name,
            record_id=obj.pk,
            record_label=obj.session_number,
            record_date=obj.actual_date or obj.scheduled_date,
            plant=obj.plant,
            department=getattr(obj.created_by, "department", None),
            process=obj.topic.name if obj.topic else "Safety Training",
            activity=obj.get_training_mode_display(),
            existing_action=f"Training status: {obj.get_status_display()}",
            responsible_person=obj.created_by,
            status=obj.get_status_display(),
            url=reverse("training:session_detail", kwargs={"pk": obj.pk}),
        )

    def filtered_queryset(self, data, user=None):
        qs = self.queryset(user)
        if _value_id(data.get("plant")):
            qs = qs.filter(plant_id=_value_id(data["plant"]))
        if _value_id(data.get("department")):
            qs = qs.filter(created_by__department_id=_value_id(data["department"]))
        if data.get("process"):
            qs = qs.filter(topic__name__icontains=data["process"])
        if data.get("activity"):
            qs = qs.filter(training_mode__icontains=data["activity"])
        if data.get("from_date"):
            qs = qs.filter(scheduled_date__gte=data["from_date"])
        if data.get("to_date"):
            qs = qs.filter(scheduled_date__lte=data["to_date"])
        start, end = _financial_year_bounds(data.get("financial_year"))
        if start and end:
            qs = qs.filter(scheduled_date__gte=start, scheduled_date__lte=end)
        return qs


class IncidentAdapter(BaseSourceAdapter):
    source_type = "injury"
    module_name = "Injury"

    @property
    def model(self):
        from apps.accidents.models import Incident

        return Incident

    def queryset(self, user=None):
        qs = self.model.objects.select_related(
            "incident_type",
            "plant",
            "affected_person_department",
            "action_plan_responsible_person",
            "reported_by",
        ).order_by("-incident_date")
        if user and not user.is_superuser and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            qs = qs.filter(plant__in=plants) if plants else qs.none()
        return qs

    def source_info(self, obj):
        unsafe_acts = ", ".join(obj.unsafe_acts or [])
        unsafe_conditions = ", ".join(obj.unsafe_conditions or [])
        if obj.unsafe_acts_other:
            unsafe_acts = f"{unsafe_acts}; {obj.unsafe_acts_other}".strip("; ")
        if obj.unsafe_conditions_other:
            unsafe_conditions = f"{unsafe_conditions}; {obj.unsafe_conditions_other}".strip("; ")
        existing_action = obj.action_plan or ""
        if hasattr(obj, "investigation_report"):
            report = obj.investigation_report
            existing_action = "\n".join(
                value
                for value in [
                    existing_action,
                    report.immediate_corrective_actions,
                    report.preventive_measures,
                ]
                if value
            )
        return SourceInfo(
            source_type=self.source_type,
            module_name=self.module_name,
            record_id=obj.pk,
            record_label=obj.report_number,
            record_date=obj.incident_date,
            plant=obj.plant,
            department=obj.affected_person_department,
            process=obj.incident_type.name if obj.incident_type else "Injury / Incident Review",
            activity=obj.additional_location_details or obj.description[:120],
            unsafe_act=unsafe_acts,
            unsafe_condition=unsafe_conditions,
            existing_action=existing_action,
            responsible_person=obj.action_plan_responsible_person or obj.assigned_to,
            target_date=obj.action_plan_deadline,
            status=obj.get_status_display(),
            url=_safe_reverse("accidents:incident_detail", pk=obj.pk),
        )

    def filtered_queryset(self, data, user=None):
        qs = self.queryset(user)
        if _value_id(data.get("plant")):
            qs = qs.filter(plant_id=_value_id(data["plant"]))
        if _value_id(data.get("department")):
            qs = qs.filter(affected_person_department_id=_value_id(data["department"]))
        if data.get("process"):
            qs = qs.filter(incident_type__name__icontains=data["process"])
        if data.get("activity"):
            qs = qs.filter(description__icontains=data["activity"])
        if data.get("from_date"):
            qs = qs.filter(incident_date__gte=data["from_date"])
        if data.get("to_date"):
            qs = qs.filter(incident_date__lte=data["to_date"])
        start, end = _financial_year_bounds(data.get("financial_year"))
        if start and end:
            qs = qs.filter(incident_date__gte=start, incident_date__lte=end)
        return qs


class HazardAdapter(BaseSourceAdapter):
    source_type = "hazard"
    module_name = "Hazard"

    @property
    def model(self):
        from apps.hazards.models import Hazard

        return Hazard

    def queryset(self, user=None):
        qs = self.model.objects.select_related(
            "plant",
            "location",
            "behalf_person_dept",
            "reported_by",
            "assigned_to",
        ).order_by("-incident_datetime", "-created_at")
        if user and not user.is_superuser and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            qs = qs.filter(plant__in=plants) if plants else qs.none()
        return qs

    def source_info(self, obj):
        unsafe_act = obj.hazard_description if obj.hazard_type == "UA" else ""
        unsafe_condition = obj.hazard_description if obj.hazard_type in ["UC", "NM"] else ""
        return SourceInfo(
            source_type=self.source_type,
            module_name=self.module_name,
            record_id=obj.pk,
            record_label=obj.report_number,
            record_date=obj.incident_datetime.date() if obj.incident_datetime else obj.reported_date.date(),
            plant=obj.plant,
            department=obj.behalf_person_dept,
            process=obj.get_hazard_category_display(),
            activity=obj.hazard_title,
            unsafe_act=unsafe_act,
            unsafe_condition=unsafe_condition,
            existing_action=obj.immediate_action or obj.corrective_action_plan,
            responsible_person=obj.assigned_to or obj.reported_by,
            target_date=obj.action_deadline,
            status=obj.effective_status_display,
            url=_safe_reverse("hazards:hazard_detail", pk=obj.pk),
        )

    def filtered_queryset(self, data, user=None):
        qs = self.queryset(user)
        if _value_id(data.get("plant")):
            qs = qs.filter(plant_id=_value_id(data["plant"]))
        if _value_id(data.get("department")):
            qs = qs.filter(behalf_person_dept_id=_value_id(data["department"]))
        if data.get("process"):
            qs = qs.filter(hazard_category__icontains=data["process"])
        if data.get("activity"):
            qs = qs.filter(Q(hazard_title__icontains=data["activity"]) | Q(hazard_description__icontains=data["activity"]))
        if data.get("from_date"):
            qs = qs.filter(incident_datetime__date__gte=data["from_date"])
        if data.get("to_date"):
            qs = qs.filter(incident_datetime__date__lte=data["to_date"])
        start, end = _financial_year_bounds(data.get("financial_year"))
        if start and end:
            qs = qs.filter(incident_datetime__date__gte=start, incident_datetime__date__lte=end)
        return qs


class PermitAdapter(BaseSourceAdapter):
    source_type = "permit"
    module_name = "Permit to Work"

    @property
    def model(self):
        from apps.permit.models import Permit

        return Permit

    def queryset(self, user=None):
        qs = self.model.objects.select_related(
            "permit_type",
            "plant",
            "department",
            "requester_user",
            "approver",
        ).order_by("-created_at")
        if user and not user.is_superuser and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            qs = qs.filter(plant__in=plants) if plants else qs.none()
        return qs

    def source_info(self, obj):
        hazards = ", ".join(str(value) for value in (obj.hazards or []) if value)
        return SourceInfo(
            source_type=self.source_type,
            module_name=self.module_name,
            record_id=obj.pk,
            record_label=obj.permit_number or f"Permit #{obj.pk}",
            record_date=obj.start_date.date() if obj.start_date else obj.created_at.date(),
            plant=obj.plant,
            department=obj.department,
            process=obj.permit_type.name if obj.permit_type else "Permit to Work",
            activity=obj.job_description[:200],
            unsafe_condition=hazards,
            existing_action=obj.safety_measures or obj.close_out_notes or "",
            responsible_person=obj.approver or obj.requester_user,
            target_date=obj.end_date.date() if obj.end_date else None,
            status=obj.get_status_display(),
            url=_safe_reverse("permit:permit_detail", pk=obj.pk),
        )

    def filtered_queryset(self, data, user=None):
        qs = self.queryset(user)
        if _value_id(data.get("plant")):
            qs = qs.filter(plant_id=_value_id(data["plant"]))
        if _value_id(data.get("department")):
            qs = qs.filter(department_id=_value_id(data["department"]))
        if data.get("process"):
            qs = qs.filter(permit_type__name__icontains=data["process"])
        if data.get("activity"):
            qs = qs.filter(job_description__icontains=data["activity"])
        if data.get("from_date"):
            qs = qs.filter(start_date__date__gte=data["from_date"])
        if data.get("to_date"):
            qs = qs.filter(start_date__date__lte=data["to_date"])
        start, end = _financial_year_bounds(data.get("financial_year"))
        if start and end:
            qs = qs.filter(start_date__date__gte=start, start_date__date__lte=end)
        return qs


class InspectionFindingAdapter(BaseSourceAdapter):
    source_type = "inspection_finding"
    module_name = "Inspection"

    @property
    def model(self):
        from apps.inspections.models import InspectionFinding

        return InspectionFinding

    def queryset(self, user=None):
        qs = self.model.objects.select_related(
            "submission",
            "submission__schedule",
            "submission__schedule__template",
            "submission__schedule__department",
            "question",
            "question__category",
            "assigned_to",
        ).order_by("-created_at")
        if user and not user.is_superuser and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            if plants:
                qs = qs.filter(submission__schedule__plants__in=plants).distinct()
            else:
                qs = qs.none()
        return qs

    def source_info(self, obj):
        schedule = obj.submission.schedule
        plant = schedule.plants.first()
        return SourceInfo(
            source_type=self.source_type,
            module_name=self.module_name,
            record_id=obj.pk,
            record_label=obj.finding_code,
            record_date=obj.created_at.date() if obj.created_at else schedule.scheduled_date,
            plant=plant,
            department=schedule.department,
            process=schedule.template.template_name if schedule.template else "Inspection Finding",
            activity=obj.question.question_text if obj.question else obj.description,
            unsafe_condition=obj.description,
            existing_action=obj.resolution_notes or "",
            responsible_person=obj.assigned_to,
            target_date=obj.due_date,
            status=obj.get_status_display(),
            url=_safe_reverse("inspections:schedule_detail", pk=schedule.pk),
        )

    def filtered_queryset(self, data, user=None):
        qs = self.queryset(user)
        if _value_id(data.get("plant")):
            qs = qs.filter(submission__schedule__plants__id=_value_id(data["plant"]))
        if _value_id(data.get("department")):
            qs = qs.filter(submission__schedule__department_id=_value_id(data["department"]))
        if data.get("process"):
            qs = qs.filter(submission__schedule__template__template_name__icontains=data["process"])
        if data.get("activity"):
            qs = qs.filter(question__question_text__icontains=data["activity"])
        if data.get("from_date"):
            qs = qs.filter(created_at__date__gte=data["from_date"])
        if data.get("to_date"):
            qs = qs.filter(created_at__date__lte=data["to_date"])
        start, end = _financial_year_bounds(data.get("financial_year"))
        if start and end:
            qs = qs.filter(created_at__date__gte=start, created_at__date__lte=end)
        return qs.distinct()


class AuditFindingAdapter(BaseSourceAdapter):
    source_type = "audit"
    module_name = "Audit"

    @property
    def model(self):
        from apps.audits.models import AuditFinding

        return AuditFinding

    def queryset(self, user=None):
        qs = self.model.objects.select_related(
            "parent_audit",
            "parent_audit__template",
            "origin_question",
            "reviewed_by",
        ).prefetch_related("parent_audit__plants").filter(is_archived=False).order_by("-created_at")
        if user and not user.is_superuser and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            qs = qs.filter(parent_audit__plants__in=plants).distinct() if plants else qs.none()
        return qs

    def source_info(self, obj):
        audit = obj.parent_audit
        plant = audit.plants.first()
        capa = obj.capas.order_by("due_date").first()
        return SourceInfo(
            source_type=self.source_type,
            module_name=self.module_name,
            record_id=obj.pk,
            record_label=obj.finding_id,
            record_date=obj.created_at.date() if obj.created_at else audit.scheduled_date,
            plant=plant,
            department=None,
            process=audit.template.title if audit.template else "Audit Finding",
            activity=obj.origin_question.question_text if obj.origin_question else obj.observation_detail[:200],
            unsafe_condition=obj.observation_detail,
            existing_action=capa.action_required if capa else "",
            responsible_person=capa.assigned_to if capa else obj.reviewed_by,
            target_date=capa.due_date if capa else None,
            status=obj.get_status_display(),
            url=_safe_reverse("audits:finding_detail", pk=obj.pk),
        )

    def filtered_queryset(self, data, user=None):
        qs = self.queryset(user)
        if _value_id(data.get("plant")):
            qs = qs.filter(parent_audit__plants__id=_value_id(data["plant"]))
        if data.get("process"):
            qs = qs.filter(parent_audit__template__title__icontains=data["process"])
        if data.get("activity"):
            qs = qs.filter(Q(origin_question__question_text__icontains=data["activity"]) | Q(observation_detail__icontains=data["activity"]))
        if data.get("from_date"):
            qs = qs.filter(created_at__date__gte=data["from_date"])
        if data.get("to_date"):
            qs = qs.filter(created_at__date__lte=data["to_date"])
        start, end = _financial_year_bounds(data.get("financial_year"))
        if start and end:
            qs = qs.filter(created_at__date__gte=start, created_at__date__lte=end)
        return qs.distinct()


class LegalComplianceAdapter(BaseSourceAdapter):
    source_type = "legal_compliance"
    module_name = "Legal Compliance"

    @property
    def model(self):
        from apps.legal_compliance.models import ComplianceRequirement

        return ComplianceRequirement

    def queryset(self, user=None):
        qs = self.model.objects.select_related(
            "legal_act",
            "created_by",
        ).prefetch_related(
            "applicable_plants",
            "applicable_departments",
            "responsible_person",
        ).filter(is_active=True).order_by("due_date", "title")
        if user and not user.is_superuser and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            qs = qs.filter(applicable_plants__in=plants).distinct() if plants else qs.none()
        return qs

    def source_info(self, obj):
        return SourceInfo(
            source_type=self.source_type,
            module_name=self.module_name,
            record_id=obj.pk,
            record_label=obj.requirement_code,
            record_date=obj.scheduled_date or obj.due_date,
            plant=obj.applicable_plants.first(),
            department=obj.applicable_departments.first(),
            process=obj.legal_act.act_name if obj.legal_act else "Legal Compliance",
            activity=obj.title,
            unsafe_condition=obj.description or "",
            existing_action=f"Criticality: {obj.get_criticality_display()}",
            responsible_person=obj.responsible_person.first() or obj.created_by,
            target_date=obj.due_date,
            status=obj.get_status_display(),
            url=_safe_reverse("legal_compliance:compliance_detail", pk=obj.pk),
        )

    def filtered_queryset(self, data, user=None):
        qs = self.queryset(user)
        if _value_id(data.get("plant")):
            qs = qs.filter(applicable_plants__id=_value_id(data["plant"]))
        if _value_id(data.get("department")):
            qs = qs.filter(applicable_departments__id=_value_id(data["department"]))
        if data.get("process"):
            qs = qs.filter(legal_act__act_name__icontains=data["process"])
        if data.get("activity"):
            qs = qs.filter(Q(title__icontains=data["activity"]) | Q(description__icontains=data["activity"]))
        if data.get("from_date"):
            qs = qs.filter(Q(scheduled_date__gte=data["from_date"]) | Q(due_date__gte=data["from_date"]))
        if data.get("to_date"):
            qs = qs.filter(Q(scheduled_date__lte=data["to_date"]) | Q(due_date__lte=data["to_date"]))
        start, end = _financial_year_bounds(data.get("financial_year"))
        if start and end:
            qs = qs.filter(Q(scheduled_date__gte=start, scheduled_date__lte=end) | Q(due_date__gte=start, due_date__lte=end))
        return qs.distinct()


class ToolboxTalkAdapter(BaseSourceAdapter):
    source_type = "toolbox_talk"
    module_name = "Toolbox Talk"

    @property
    def model(self):
        from apps.toolbox_talk.models import ToolboxTalkSessionPlan

        return ToolboxTalkSessionPlan

    def queryset(self, user=None):
        qs = self.model.objects.select_related(
            "category",
            "topic",
            "department",
            "created_by",
        ).prefetch_related("plants", "trainers", "incharges").order_by("-planned_date", "-planned_time")
        if user and not user.is_superuser and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            qs = qs.filter(plants__in=plants).distinct() if plants else qs.none()
        return qs

    def source_info(self, obj):
        return SourceInfo(
            source_type=self.source_type,
            module_name=self.module_name,
            record_id=obj.pk,
            record_label=obj.session_no,
            record_date=obj.planned_date,
            plant=obj.plants.first(),
            department=obj.department,
            process=obj.category.category_name if obj.category else "Toolbox Talk",
            activity=obj.topic.topic_title if obj.topic else "",
            existing_action=obj.remarks or "",
            responsible_person=obj.trainers.first() or obj.incharges.first() or obj.created_by,
            status=obj.get_status_display(),
            url=_safe_reverse("toolbox_talk:session_view", pk=obj.pk),
        )

    def filtered_queryset(self, data, user=None):
        qs = self.queryset(user)
        if _value_id(data.get("plant")):
            qs = qs.filter(plants__id=_value_id(data["plant"]))
        if _value_id(data.get("department")):
            qs = qs.filter(department_id=_value_id(data["department"]))
        if data.get("process"):
            qs = qs.filter(category__category_name__icontains=data["process"])
        if data.get("activity"):
            qs = qs.filter(topic__topic_title__icontains=data["activity"])
        if data.get("from_date"):
            qs = qs.filter(planned_date__gte=data["from_date"])
        if data.get("to_date"):
            qs = qs.filter(planned_date__lte=data["to_date"])
        start, end = _financial_year_bounds(data.get("financial_year"))
        if start and end:
            qs = qs.filter(planned_date__gte=start, planned_date__lte=end)
        return qs.distinct()


ADAPTERS = {
    "injury": IncidentAdapter(),
    "hazard": HazardAdapter(),
    "permit": PermitAdapter(),
    "inspection_finding": InspectionFindingAdapter(),
    "audit": AuditFindingAdapter(),
    "training": TrainingSessionAdapter(),
    "legal_compliance": LegalComplianceAdapter(),
    "toolbox_talk": ToolboxTalkAdapter(),
}


def adapter_choices():
    return [(key, adapter.module_name) for key, adapter in ADAPTERS.items()]


def get_adapter(source_type):
    if source_type == "incident":
        source_type = "injury"
    return ADAPTERS.get(source_type)


def get_source_object(source_type, source_id, user=None):
    adapter = get_adapter(source_type)
    if not adapter or not source_id:
        return None
    try:
        return adapter.get(source_id, user=user)
    except adapter.model.DoesNotExist:
        return None


def describe_source_object(obj):
    if not obj:
        return None
    for adapter in ADAPTERS.values():
        if isinstance(obj, adapter.model):
            return adapter.source_info(obj)
    return SourceInfo(
        source_type=obj._meta.model_name,
        module_name=obj._meta.verbose_name.title(),
        record_id=obj.pk,
        record_label=str(obj),
        status="",
    )
