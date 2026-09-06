from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView, View

from apps.accidents.models import Incident
from apps.accounts.mixins import PermissionRequiredMixin
from apps.capa.forms import (
    CAPAAttachmentForm,
    CAPAActionCompletionForm,
    CAPAActionForm,
    CAPAActionVerificationForm,
    CAPAClosureForm,
    CAPACommentForm,
    CAPAEffectivenessReviewForm,
    CAPAFilterForm,
    CAPAForm,
    CAPAInvestigationForm,
    CAPAReopenForm,
)
from apps.capa.models import (
    CAPA,
    CAPAAttachment,
    CAPAAction,
    CAPAActionCompletion,
    CAPAActionVerification,
    CAPAEffectivenessReview,
    CAPAInvestigation,
)
from apps.capa.services import CAPAService
from apps.hazards.models import Hazard
from apps.organizations.models import Location, Plant, SubLocation, Zone


def _accessible_plants(user):
    if user.is_superuser:
        return Plant.objects.filter(is_active=True)
    if hasattr(user, "get_all_plants"):
        plants = user.get_all_plants()
        return Plant.objects.filter(id__in=[p.id for p in plants], is_active=True)
    if getattr(user, "plant_id", None):
        return Plant.objects.filter(id=user.plant_id, is_active=True)
    return Plant.objects.none()


def _capa_queryset_for_user(user):
    if user.is_superuser:
        return CAPA.objects.all()
    plant_ids = list(_accessible_plants(user).values_list("id", flat=True))
    if not plant_ids:
        return CAPA.objects.none()
    return CAPA.objects.filter(plant_id__in=plant_ids)

from apps.organizations.models import Location, Plant, SubLocation, Zone


class CAPAAjaxGetZonesView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        plant_id = request.GET.get("plant_id")
        zones = Zone.objects.filter(plant_id=plant_id).order_by("name") if plant_id else Zone.objects.none()
        return JsonResponse(list(zones.values("id", "name")), safe=False)


class CAPAAjaxGetLocationsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        zone_id = request.GET.get("zone_id")
        locations = Location.objects.filter(zone_id=zone_id).order_by("name") if zone_id else Location.objects.none()
        return JsonResponse(list(locations.values("id", "name")), safe=False)


class CAPAAjaxGetSublocationsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        location_id = request.GET.get("location_id")
        sublocations = SubLocation.objects.filter(location_id=location_id).order_by("name") if location_id else SubLocation.objects.none()
        return JsonResponse(list(sublocations.values("id", "name")), safe=False)

class CAPASourceReferenceView(LoginRequiredMixin, View):
    """Return searchable source records that the current user can access."""

    def get(self, request, *args, **kwargs):
        source_type = request.GET.get("source_type", "").upper()
        query = request.GET.get("q", "").strip()
        plants = _accessible_plants(request.user)
        results = []

        if source_type == CAPA.SourceType.INCIDENT:
            records = Incident.objects.filter(plant__in=plants).order_by("-pk")
            if query:
                records = records.filter(Q(report_number__icontains=query) | Q(description__icontains=query))
            results = [
                {"value": record.report_number, "label": f"{record.report_number} - {record.description[:90]}"}
                for record in records[:100]
            ]
        elif source_type == CAPA.SourceType.HAZARD:
            records = Hazard.objects.filter(plant__in=plants).order_by("-pk")
            if query:
                records = records.filter(Q(report_number__icontains=query) | Q(hazard_title__icontains=query) | Q(hazard_description__icontains=query))
            results = [
                {"value": record.report_number, "label": f"{record.report_number} - {record.hazard_title[:90]}"}
                for record in records[:100]
            ]

        return JsonResponse({"results": results})


class CAPAAccessMixin(PermissionRequiredMixin):
    permission_required = "CAPA_VIEW"

    def get_queryset(self):
        return _capa_queryset_for_user(self.request.user).select_related(
            "plant", "zone", "location", "sublocation", "department", "owner", "created_by"
        ).prefetch_related("actions", "attachments", "comments", "audit_logs")


STATUS_BADGE_MAP = {
    CAPA.Status.DRAFT: "secondary",
    CAPA.Status.OPEN: "info",
    CAPA.Status.INVESTIGATION_IN_PROGRESS: "warning",
    CAPA.Status.INVESTIGATION_SUBMITTED: "warning",
    CAPA.Status.INVESTIGATION_APPROVED: "info",
    CAPA.Status.INVESTIGATION_REJECTED: "danger",
    CAPA.Status.ACTION_PLAN_IN_PROGRESS: "info",
    CAPA.Status.ACTION_IMPLEMENTATION: "info",
    CAPA.Status.VERIFICATION: "warning",
    CAPA.Status.EFFECTIVENESS_REVIEW: "warning",
    CAPA.Status.CLOSED: "success",
    CAPA.Status.REOPENED: "danger",
    CAPA.Status.CANCELLED: "secondary",
}


class CAPADashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = "CAPA_VIEW"
    template_name = "capa/dashboard.html"

    def get(self, request, *args, **kwargs):
        self.filters = {
            "plant": request.GET.get("plant", ""),
            "zone": request.GET.get("zone", ""),
            "location": request.GET.get("location", ""),
            "sublocation": request.GET.get("sublocation", ""),
            "month": request.GET.get("month", ""),
        }
        return super().get(request, *args, **kwargs)

    def _filtered_queryset(self):
        qs = _capa_queryset_for_user(self.request.user)
        f = self.filters
        if f["plant"]:
            qs = qs.filter(plant_id=f["plant"])
        if f["zone"]:
            qs = qs.filter(zone_id=f["zone"])
        if f["location"]:
            qs = qs.filter(location_id=f["location"])
        if f["sublocation"]:
            qs = qs.filter(sublocation_id=f["sublocation"])
        if f["month"]:
            try:
                year, month = (int(part) for part in f["month"].split("-"))
                qs = qs.filter(created_at__year=year, created_at__month=month)
            except (ValueError, TypeError):
                pass
        return qs

    @staticmethod
    def _month_options():
        today = timezone.localdate()
        options = []
        year, month = today.year, today.month
        for _ in range(12):
            options.append({
                "value": f"{year:04d}-{month:02d}",
                "label": date(year, month, 1).strftime("%b %Y"),
            })
            month -= 1
            if month == 0:
                month, year = 12, year - 1
        return options

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        qs = self._filtered_queryset()

        # ---------------- KPI stats ----------------
        stats = {
            "total": qs.count(),
            "open": qs.exclude(status=CAPA.Status.CLOSED).count(),
            "pending_verification": qs.filter(actions__status=CAPAAction.Status.PENDING_VERIFICATION).distinct().count(),
            "overdue": qs.filter(target_date__lt=today).exclude(status__in=[CAPA.Status.CLOSED, CAPA.Status.CANCELLED]).count(),
            "closed": qs.filter(status=CAPA.Status.CLOSED).count(),
            "critical": qs.filter(severity=CAPA.Severity.CRITICAL).count(),
            "high": qs.filter(severity=CAPA.Severity.HIGH).count(),
        }
        context["stats"] = stats
        context["dashboard_cards"] = [
            (stats["total"], "Total CAPAs", "fas fa-layer-group", "teal"),
            (stats["open"], "Open CAPAs", "fas fa-folder-open", "blue"),
            (stats["pending_verification"], "Pending Verification", "fas fa-user-check", "gold"),
            (stats["overdue"], "Overdue", "fas fa-exclamation-triangle", "red"),
        ]

        # ---------------- Source type chart (doughnut) ----------------
        source_labels_map = dict(CAPA.SourceType.choices)
        source_rows = list(qs.values("source_type").annotate(count=Count("id")).order_by("-count"))
        context["type_chart_labels"] = [source_labels_map.get(r["source_type"], r["source_type"]) for r in source_rows]
        context["type_chart_data"] = [r["count"] for r in source_rows]

        # ---------------- Monthly trend (last 6 months) ----------------
        month_buckets = []
        year, month = today.year, today.month
        for _ in range(6):
            month_buckets.append((year, month))
            month -= 1
            if month == 0:
                month, year = 12, year - 1
        month_buckets.reverse()

        monthly_counts_qs = (
            qs.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
        )
        counts_by_month = {(m["month"].year, m["month"].month): m["count"] for m in monthly_counts_qs if m["month"]}
        context["monthly_labels"] = [date(y, m, 1).strftime("%b %Y") for y, m in month_buckets]
        context["monthly_data"] = [counts_by_month.get((y, m), 0) for y, m in month_buckets]

        # ---------------- Severity distribution ----------------
        severity_rows = {r["severity"]: r["count"] for r in qs.values("severity").annotate(count=Count("id"))}
        context["severity_labels"] = [label for _, label in CAPA.Severity.choices]
        context["severity_data"] = [severity_rows.get(code, 0) for code, _ in CAPA.Severity.choices]

        # ---------------- Status distribution (clickable) ----------------
        status_rows = {r["status"]: r["count"] for r in qs.values("status").annotate(count=Count("id"))}
        status_labels, status_data = [], []
        for code, label in CAPA.Status.choices:
            count = status_rows.get(code, 0)
            if not count:
                continue
            status_labels.append(label)
            status_data.append({"count": count, "url": f"{reverse('capa:list')}?status={code}"})
        context["status_labels"] = status_labels
        context["status_data"] = status_data

        # ---------------- Overdue alerts ----------------
        overdue_capas = list(
            qs.filter(target_date__lt=today)
            .exclude(status__in=[CAPA.Status.CLOSED, CAPA.Status.CANCELLED])
            .select_related("plant", "owner")
            .order_by("target_date")[:5]
        )
        for c in overdue_capas:
            c.status_badge_class = STATUS_BADGE_MAP.get(c.status, "secondary")
        context["overdue_capas"] = overdue_capas

        # ---------------- Recent CAPAs ----------------
        recent_capas = list(qs.select_related("plant", "owner").order_by("-created_at")[:8])
        for c in recent_capas:
            c.status_badge_class = STATUS_BADGE_MAP.get(c.status, "secondary")
        context["recent_capas"] = recent_capas

        # ---------------- Filter bar data ----------------
        f = self.filters
        context["plants"] = _accessible_plants(self.request.user)
        context["zones"] = Zone.objects.filter(plant_id=f["plant"]) if f["plant"] else Zone.objects.none()
        context["locations"] = Location.objects.filter(zone_id=f["zone"]) if f["zone"] else Location.objects.none()
        context["sublocations"] = SubLocation.objects.filter(location_id=f["location"]) if f["location"] else SubLocation.objects.none()
        context["month_options"] = self._month_options()
        context["selected_plant"] = f["plant"]
        context["selected_zone"] = f["zone"]
        context["selected_location"] = f["location"]
        context["selected_sublocation"] = f["sublocation"]
        context["selected_month"] = f["month"]
        context["selected_plant_name"] = context["plants"].filter(pk=f["plant"]).values_list("name", flat=True).first() if f["plant"] else ""
        context["selected_zone_name"] = context["zones"].filter(pk=f["zone"]).values_list("name", flat=True).first() if f["zone"] else ""
        context["selected_location_name"] = context["locations"].filter(pk=f["location"]).values_list("name", flat=True).first() if f["location"] else ""
        context["selected_sublocation_name"] = context["sublocations"].filter(pk=f["sublocation"]).values_list("name", flat=True).first() if f["sublocation"] else ""
        context["selected_month_label"] = next((option["label"] for option in context["month_options"] if option["value"] == f["month"]), "")
        context["has_active_filters"] = any(f.values())
        return context


class CAPAListView(CAPAAccessMixin, ListView):
    template_name = "capa/list.html"
    context_object_name = "capas"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        form = CAPAFilterForm(self.request.GET or None)
        self.filter_form = form
        if form.is_valid():
            data = form.cleaned_data
            if data.get("plant"):
                qs = qs.filter(plant=data["plant"])
            if data.get("zone"):
                qs = qs.filter(zone=data["zone"])
            if data.get("location"):
                qs = qs.filter(location=data["location"])
            if data.get("sublocation"):
                qs = qs.filter(sublocation=data["sublocation"])
            if data.get("department"):
                qs = qs.filter(department=data["department"])
            if data.get("owner"):
                qs = qs.filter(owner=data["owner"])
            if data.get("source_type"):
                qs = qs.filter(source_type=data["source_type"])
            if data.get("severity"):
                qs = qs.filter(severity=data["severity"])
            if data.get("priority"):
                qs = qs.filter(priority=data["priority"])
            if data.get("status"):
                qs = qs.filter(status=data["status"])
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = getattr(self, "filter_form", CAPAFilterForm())
        return context


class CAPADetailView(CAPAAccessMixin, DetailView):
    template_name = "capa/detail.html"
    context_object_name = "capa"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comment_form"] = CAPACommentForm()
        context["attachment_form"] = CAPAAttachmentForm()
        try:
            context["investigation"] = self.object.investigation
        except CAPAInvestigation.DoesNotExist:
            context["investigation"] = None
        try:
            context["effectiveness_review"] = self.object.effectiveness_review
        except CAPAEffectivenessReview.DoesNotExist:
            context["effectiveness_review"] = None
        context["timeline"] = [
            "Created",
            "Investigation",
            "Investigation Approved",
            "Action Plan",
            "Implementation",
            "Verification",
            "Effectiveness",
            "Closed",
        ]
        status = self.object.status
        context.update({
            "can_start_investigation": status in {CAPA.Status.DRAFT, CAPA.Status.OPEN, CAPA.Status.INVESTIGATION_IN_PROGRESS, CAPA.Status.INVESTIGATION_REJECTED, CAPA.Status.REOPENED},
            "can_review_investigation": status == CAPA.Status.INVESTIGATION_SUBMITTED,
            "can_add_action": status in {CAPA.Status.INVESTIGATION_APPROVED, CAPA.Status.ACTION_PLAN_IN_PROGRESS, CAPA.Status.ACTION_IMPLEMENTATION, CAPA.Status.REOPENED},
            "can_start_effectiveness": status in {CAPA.Status.VERIFICATION, CAPA.Status.EFFECTIVENESS_REVIEW},
            "can_close": status == CAPA.Status.EFFECTIVENESS_REVIEW,
        })
        return context


class CAPAInvestigationDetailView(CAPAAccessMixin, DetailView):
    template_name = "capa/investigation_detail.html"
    context_object_name = "capa"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["investigation"] = self.object.investigation
        except CAPAInvestigation.DoesNotExist:
            context["investigation"] = None
        return context


class CAPACreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "CAPA_CREATE"
    template_name = "capa/form.html"
    form_class = CAPAForm

    def get_initial(self):
        initial = super().get_initial()
        source_type = self.request.GET.get("source_type")
        source_id = self.request.GET.get("source_id")
        if source_type == "INCIDENT" and source_id:
            incident = Incident.objects.filter(pk=source_id).select_related("plant", "zone", "location", "sublocation", "affected_person_department").first()
            if incident:
                initial.update({
                    "title": f"CAPA for {incident.report_number}",
                    "description": incident.description,
                    "source_type": CAPA.SourceType.INCIDENT,
                    "source_reference": incident.report_number,
                    "plant": incident.plant,
                    "zone": incident.zone,
                    "location": incident.location,
                    "sublocation": incident.sublocation,
                    "department": incident.affected_person_department,
                })
        elif source_type == "HAZARD" and source_id:
            hazard = Hazard.objects.filter(pk=source_id).select_related("plant", "zone", "location", "sublocation", "behalf_person_dept").first()
            if hazard:
                initial.update({
                    "title": f"CAPA for {hazard.report_number}",
                    "description": hazard.hazard_description,
                    "source_type": CAPA.SourceType.HAZARD,
                    "source_reference": hazard.report_number,
                    "plant": hazard.plant,
                    "zone": hazard.zone,
                    "location": hazard.location,
                    "sublocation": hazard.sublocation,
                    "department": hazard.behalf_person_dept,
                })
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_draft_button"] = True
        context["cancel_url"] = reverse("capa:list")
        return context

    def form_valid(self, form):
        if self.request.POST.get("action") == "cancel":
            return redirect("capa:list")

        source_type = form.cleaned_data.get("source_type")
        source_reference = form.cleaned_data.get("source_reference")
        source_obj = None
        if source_type == CAPA.SourceType.INCIDENT:
            source_obj = Incident.objects.filter(report_number=source_reference).first()
        elif source_type == CAPA.SourceType.HAZARD:
            source_obj = Hazard.objects.filter(report_number=source_reference).first()

        capa = CAPAService.create_capa(
            user=self.request.user,
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
            plant=form.cleaned_data["plant"],
            zone=form.cleaned_data.get("zone"),
            location=form.cleaned_data.get("location"),
            sublocation=form.cleaned_data.get("sublocation"),
            department=form.cleaned_data.get("department"),
            category=form.cleaned_data.get("category", ""),
            severity=form.cleaned_data.get("severity", CAPA.Severity.MEDIUM),
            priority=form.cleaned_data.get("priority", CAPA.Priority.MEDIUM),
            owner=form.cleaned_data.get("owner"),
            target_date=form.cleaned_data.get("target_date"),
            reason_required=form.cleaned_data.get("reason_required", ""),
            capa_recommended=form.cleaned_data.get("capa_recommended", False),
            capa_reason=form.cleaned_data.get("capa_reason", ""),
            source_type=source_type,
            source_reference=source_reference,
            source_obj=source_obj,
            status=CAPA.Status.DRAFT if self.request.POST.get("save_draft") else CAPA.Status.OPEN,
        )
        messages.success(self.request, f"CAPA {capa.capa_number} created successfully.")
        return redirect(reverse("capa:list"))


class CAPAUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "CAPA_EDIT"
    model = CAPA
    form_class = CAPAForm
    template_name = "capa/form.html"

    def get_queryset(self):
        return _capa_queryset_for_user(self.request.user)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        source_type = form.cleaned_data.get("source_type")
        source_reference = form.cleaned_data.get("source_reference", "")
        source_obj = None
        if source_type == CAPA.SourceType.INCIDENT:
            source_obj = Incident.objects.filter(report_number=source_reference).first()
        elif source_type == CAPA.SourceType.HAZARD:
            source_obj = Hazard.objects.filter(report_number=source_reference).first()
        if source_obj:
            form.instance.source_content_type = ContentType.objects.get_for_model(source_obj)
            form.instance.source_object_id = source_obj.pk
        else:
            form.instance.source_content_type = None
            form.instance.source_object_id = None
        messages.success(self.request, "CAPA updated successfully.")
        return redirect(reverse("capa:detail", kwargs={"pk": self.object.pk}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.object.get_absolute_url()
        return context


class CAPAInvestigationView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "CAPA_INVESTIGATE"
    template_name = "capa/investigation_form.html"
    form_class = CAPAInvestigationForm

    def dispatch(self, request, *args, **kwargs):
        self.capa = get_object_or_404(_capa_queryset_for_user(request.user), pk=kwargs["pk"])
        try:
            if self.capa.investigation.completed_date and self.capa.status != CAPA.Status.INVESTIGATION_REJECTED:
                messages.info(request, "This investigation has already been submitted and cannot be resubmitted.")
                return redirect(reverse("capa:investigation_detail", kwargs={"pk": self.capa.pk}))
        except CAPAInvestigation.DoesNotExist:
            pass
        if self.capa.status not in {CAPA.Status.DRAFT, CAPA.Status.OPEN, CAPA.Status.INVESTIGATION_IN_PROGRESS, CAPA.Status.INVESTIGATION_REJECTED, CAPA.Status.REOPENED}:
            messages.info(request, "This investigation has already been submitted. You are viewing the read-only investigation record.")
            return redirect(reverse("capa:investigation_detail", kwargs={"pk": self.capa.pk}))
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if hasattr(self.capa, "investigation"):
            m2m_fields = {"affected_plants", "affected_departments", "affected_locations"}
            for field in self.form_class.Meta.fields:
                if field != "capa":
                    value = getattr(self.capa.investigation, field, None)
                    if field in m2m_fields and value is not None:
                        initial[field] = list(value.values_list("pk", flat=True))
                    else:
                        initial[field] = value
        return initial

    def get_form_kwargs(self):
        """Bind the form to the investigation before Django validates it."""
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = CAPAInvestigation.objects.filter(capa=self.capa).first() or CAPAInvestigation(capa=self.capa)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["capa"] = self.capa
        try:
            context["investigation"] = self.capa.investigation
        except CAPAInvestigation.DoesNotExist:
            context["investigation"] = None
        try:
            context["effectiveness_review"] = self.capa.effectiveness_review
        except CAPAEffectivenessReview.DoesNotExist:
            context["effectiveness_review"] = None
        context["cancel_url"] = self.capa.get_absolute_url()
        return context

    def form_valid(self, form):
        if self.request.POST.get("submit_investigation"):
            try:
                if self.capa.investigation.completed_date and self.capa.status != CAPA.Status.INVESTIGATION_REJECTED:
                    messages.info(self.request, "This investigation has already been submitted and cannot be resubmitted.")
                    return redirect(reverse("capa:investigation_detail", kwargs={"pk": self.capa.pk}))
            except CAPAInvestigation.DoesNotExist:
                pass
        investigation = form.save(commit=False)
        investigation.capa = self.capa
        investigation.save()
        form.save_m2m()
        if self.request.POST.get("submit_investigation"):
            CAPAService.submit_investigation(user=self.request.user, capa=self.capa, investigation=investigation)
            messages.success(self.request, "Investigation submitted.")
            return redirect(reverse("capa:detail", kwargs={"pk": self.capa.pk}))
        if self.capa.status in {CAPA.Status.DRAFT, CAPA.Status.OPEN}:
            CAPAService._set_status(self.capa, CAPA.Status.INVESTIGATION_IN_PROGRESS, self.request.user, "INVESTIGATION_STARTED")
        messages.success(self.request, "Investigation saved.")
        return redirect(reverse("capa:investigation", kwargs={"pk": self.capa.pk}))


class CAPAInvestigationReviewView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = "CAPA_APPROVE_INVESTIGATION"
    template_name = "capa/investigation_review.html"

    def dispatch(self, request, *args, **kwargs):
        self.capa = get_object_or_404(_capa_queryset_for_user(request.user), pk=kwargs["pk"])
        if self.capa.status != CAPA.Status.INVESTIGATION_SUBMITTED:
            messages.info(request, "Investigation review is available only after submission.")
            return redirect(reverse("capa:detail", kwargs={"pk": self.capa.pk}))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        remarks = request.POST.get("remarks", "").strip()
        if "approve" in request.POST:
            CAPAService.approve_investigation(user=request.user, capa=self.capa, remarks=remarks)
            messages.success(request, "Investigation approved.")
        elif "reject" in request.POST:
            if not remarks:
                messages.error(request, "Rejection reason is required.")
                return redirect(reverse("capa:investigation_review", kwargs={"pk": self.capa.pk}))
            CAPAService.reject_investigation(user=request.user, capa=self.capa, remarks=remarks)
            messages.warning(request, "Investigation rejected.")
        else:
            messages.error(request, "Select Approve or Reject before submitting the review.")
            return redirect(reverse("capa:investigation_review", kwargs={"pk": self.capa.pk}))
        return redirect(reverse("capa:detail", kwargs={"pk": self.capa.pk}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["capa"] = self.capa
        context["cancel_url"] = self.capa.get_absolute_url()
        return context


class CAPAActionCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "CAPA_MANAGE_ACTIONS"
    template_name = "capa/action_form.html"
    form_class = CAPAActionForm

    def dispatch(self, request, *args, **kwargs):
        self.capa = get_object_or_404(_capa_queryset_for_user(request.user), pk=kwargs["pk"])
        if self.capa.status not in {CAPA.Status.INVESTIGATION_APPROVED, CAPA.Status.ACTION_PLAN_IN_PROGRESS, CAPA.Status.ACTION_IMPLEMENTATION, CAPA.Status.REOPENED}:
            messages.info(request, "Complete and approve the investigation before adding actions.")
            return redirect(reverse("capa:detail", kwargs={"pk": self.capa.pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        action = CAPAService.create_action(user=self.request.user, capa=self.capa, **form.cleaned_data)
        messages.success(self.request, "Action added.")
        return redirect(reverse("capa:detail", kwargs={"pk": self.capa.pk}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.capa.get_absolute_url()
        return context


class CAPAActionCompletionView(LoginRequiredMixin, FormView):
    template_name = "capa/action_completion_form.html"
    form_class = CAPAActionCompletionForm

    def dispatch(self, request, *args, **kwargs):
        self.action = get_object_or_404(CAPAAction.objects.select_related("capa"), pk=kwargs["pk"])
        if not _capa_queryset_for_user(request.user).filter(pk=self.action.capa_id).exists():
            raise Http404
        if self.action.assigned_to_id != request.user.pk:
            messages.error(request, "You are not assigned to this action.")
            return redirect(reverse("capa:my_action_items"))
        if self.action.status not in {CAPAAction.Status.PENDING, CAPAAction.Status.IN_PROGRESS, CAPAAction.Status.REJECTED}:
            messages.info(request, "This action has already been submitted for verification.")
            return redirect(reverse("capa:action_detail", kwargs={"pk": self.action.pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        CAPAService.complete_action(
            user=self.request.user,
            action=self.action,
            completion_remarks=form.cleaned_data.get("completion_remarks", ""),
            evidence=form.cleaned_data.get("evidence"),
        )
        messages.success(self.request, "Action marked as completed.")
        return redirect(reverse("capa:my_action_items"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = self.action
        context["cancel_url"] = self.action.capa.get_absolute_url()
        return context


class CAPAMyActionItemsView(LoginRequiredMixin, ListView):
    model = CAPAAction
    template_name = "capa/my_action_items.html"
    context_object_name = "action_items"
    paginate_by = 15

    def get_queryset(self):
        queryset = CAPAAction.objects.filter(
            assigned_to=self.request.user,
            capa__in=_capa_queryset_for_user(self.request.user),
        ).select_related("capa", "capa__plant", "created_by", "assigned_to").order_by("target_date", "-created_at")
        status_filter = self.request.GET.get("status", "")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assigned = CAPAAction.objects.filter(
            assigned_to=self.request.user,
            capa__in=_capa_queryset_for_user(self.request.user),
        )
        context["total_assigned"] = assigned.count()
        context["pending_count"] = assigned.filter(status__in=[CAPAAction.Status.PENDING, CAPAAction.Status.REJECTED]).count()
        context["in_progress_count"] = assigned.filter(status=CAPAAction.Status.IN_PROGRESS).count()
        context["pending_verification_count"] = assigned.filter(status=CAPAAction.Status.PENDING_VERIFICATION).count()
        context["overdue_count"] = sum(1 for item in assigned if item.is_overdue)
        context["status_choices"] = CAPAAction.Status.choices
        context["selected_status"] = self.request.GET.get("status", "")
        return context


class CAPAActionVerificationView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "CAPA_VERIFY_ACTION"
    template_name = "capa/action_verification_form.html"
    form_class = CAPAActionVerificationForm

    def dispatch(self, request, *args, **kwargs):
        self.action = get_object_or_404(CAPAAction.objects.select_related("capa"), pk=kwargs["pk"])
        if not _capa_queryset_for_user(request.user).filter(pk=self.action.capa_id).exists():
            raise Http404
        if self.action.capa.status not in {CAPA.Status.ACTION_IMPLEMENTATION, CAPA.Status.REOPENED} or self.action.status != CAPAAction.Status.PENDING_VERIFICATION:
            messages.info(request, "Verification is available only after the action has been completed.")
            return redirect(reverse("capa:action_detail", kwargs={"pk": self.action.pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        cleaned = dict(form.cleaned_data)
        result = cleaned.pop("result")
        CAPAService.verify_action(user=self.request.user, action=self.action, result=result, **cleaned)
        messages.success(self.request, "Action verification saved.")
        return redirect(reverse("capa:detail", kwargs={"pk": self.action.capa.pk}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = self.action  # ADD THIS
        try:
            context["completion"] = self.action.completion  # ADD THIS
        except CAPAActionCompletion.DoesNotExist:
            context["completion"] = None
        context["cancel_url"] = self.action.capa.get_absolute_url()
        return context


class CAPAEffectivenessReviewView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "CAPA_EFFECTIVENESS"
    template_name = "capa/effectiveness_form.html"
    form_class = CAPAEffectivenessReviewForm

    def dispatch(self, request, *args, **kwargs):
        self.capa = get_object_or_404(_capa_queryset_for_user(request.user), pk=kwargs["pk"])
        if self.capa.status not in {CAPA.Status.VERIFICATION, CAPA.Status.EFFECTIVENESS_REVIEW}:
            messages.info(request, "Complete verification for all actions before starting effectiveness review.")
            return redirect(reverse("capa:detail", kwargs={"pk": self.capa.pk}))
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        try:
            review = self.capa.effectiveness_review
            if review:
                # Populate initial data from existing review
                fields = [
                    'review_date', 'corrective_working_as_intended', 'preventive_working_as_intended',
                    'risk_reduced_as_expected', 'controls_adequate', 'systemic_cause_addressed',
                    'effectiveness_evidence', 'evidence_description', 'review_findings',
                    'observed_improvement', 'remaining_risk_gap', 'result', 'remarks'
                ]
                for field in fields:
                    value = getattr(review, field, None)
                    if value is not None:
                        initial[field] = value
        except CAPAEffectivenessReview.DoesNotExist:
            pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["capa"] = self.capa
        try:
            context["effectiveness_review"] = self.capa.effectiveness_review
        except CAPAEffectivenessReview.DoesNotExist:
            context["effectiveness_review"] = None
        context["cancel_url"] = self.capa.get_absolute_url()
        return context

    def form_valid(self, form):
        review, created = CAPAEffectivenessReview.objects.get_or_create(capa=self.capa)
        for field, value in form.cleaned_data.items():
            setattr(review, field, value)
        review.reviewed_by = self.request.user
        review.save()
        
        if self.capa.status == CAPA.Status.VERIFICATION:
            CAPAService.start_effectiveness_review(user=self.request.user, capa=self.capa)
        
        messages.success(self.request, "Effectiveness review saved successfully.")
        return redirect(reverse("capa:detail", kwargs={"pk": self.capa.pk}))


class CAPAClosureView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "CAPA_CLOSE"
    template_name = "capa/closure_form.html"
    form_class = CAPAClosureForm

    def dispatch(self, request, *args, **kwargs):
        self.capa = get_object_or_404(_capa_queryset_for_user(request.user), pk=kwargs["pk"])
        if self.capa.status != CAPA.Status.EFFECTIVENESS_REVIEW:
            messages.info(request, "CAPA closure is available only after an effective review.")
            return redirect(reverse("capa:detail", kwargs={"pk": self.capa.pk}))
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        # Populate initial data from existing CAPA
        initial["closure_remarks"] = self.capa.closure_remarks
        initial["lessons_learned"] = self.capa.lessons_learned
        initial["final_recommendations"] = self.capa.final_recommendations
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["capa"] = self.capa
        try:
            context["effectiveness_review"] = self.capa.effectiveness_review
        except CAPAEffectivenessReview.DoesNotExist:
            context["effectiveness_review"] = None
        # Get all actions for summary
        context["total_actions"] = self.capa.actions.count()
        context["verified_actions"] = self.capa.actions.filter(status=CAPAAction.Status.VERIFIED).count()
        context["cancel_url"] = self.capa.get_absolute_url()
        return context

    def form_valid(self, form):
        CAPAService.close_capa(
            user=self.request.user,
            capa=self.capa,
            closure_remarks=form.cleaned_data.get("closure_remarks", ""),
            lessons_learned=form.cleaned_data.get("lessons_learned", ""),
            final_recommendations=form.cleaned_data.get("final_recommendations", ""),
        )
        messages.success(self.request, f"CAPA {self.capa.capa_number} closed successfully.")
        return redirect(reverse("capa:list"))


class CAPAReopenView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "CAPA_REOPEN"
    template_name = "capa/reopen_form.html"
    form_class = CAPAReopenForm

    def dispatch(self, request, *args, **kwargs):
        self.capa = get_object_or_404(_capa_queryset_for_user(request.user), pk=kwargs["pk"])
        if self.capa.status != CAPA.Status.CLOSED:
            messages.info(request, "Only closed CAPAs can be reopened.")
            return redirect("capa:detail", pk=self.capa.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["capa"] = self.capa
        context["cancel_url"] = self.capa.get_absolute_url()
        return context

    def form_valid(self, form):
        CAPAService.reopen_capa(user=self.request.user, capa=self.capa, reason=form.cleaned_data["reason"])
        messages.warning(self.request, "CAPA reopened.")
        return redirect(self.capa.get_absolute_url())


class CAPAActionDetailView(LoginRequiredMixin, CAPAAccessMixin, DetailView):
    model = CAPAAction
    template_name = "capa/action_detail.html"
    context_object_name = "action"

    def get_queryset(self):
        return CAPAAction.objects.select_related("capa", "assigned_to", "department").filter(capa__in=_capa_queryset_for_user(self.request.user))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["completion"] = self.object.completion
        except CAPAActionCompletion.DoesNotExist:
            context["completion"] = None
        try:
            context["verification"] = self.object.verification
        except CAPAActionVerification.DoesNotExist:
            context["verification"] = None
        return context


class CAPAAttachmentCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "CAPA_EDIT"
    template_name = "capa/attachment_form.html"
    form_class = CAPAAttachmentForm

    def dispatch(self, request, *args, **kwargs):
        self.capa = get_object_or_404(_capa_queryset_for_user(request.user), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        attachment = form.save(commit=False)
        attachment.capa = self.capa
        attachment.uploaded_by = self.request.user
        attachment.save()
        messages.success(self.request, "Attachment uploaded.")
        return redirect(reverse("capa:detail", kwargs={"pk": self.capa.pk}))


class CAPACommentCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "CAPA_EDIT"
    form_class = CAPACommentForm
    template_name = "capa/comment_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.capa = get_object_or_404(_capa_queryset_for_user(request.user), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        comment = form.save(commit=False)
        comment.capa = self.capa
        comment.author = self.request.user
        comment.save()
        messages.success(self.request, "Comment added.")
        return redirect(reverse("capa:detail", kwargs={"pk": self.capa.pk}))


class CAPASourceCreateFromIncidentView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "CAPA_CREATE"

    def post(self, request, incident_id):
        incident = get_object_or_404(Incident, pk=incident_id)
        capa = CAPAService.create_from_incident(user=request.user, incident=incident, status=CAPA.Status.OPEN)
        messages.success(request, "CAPA created from incident.")
        return redirect(reverse("capa:detail", kwargs={"pk": capa.pk}))


class CAPASourceCreateFromHazardView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "CAPA_CREATE"

    def post(self, request, hazard_id):
        hazard = get_object_or_404(Hazard, pk=hazard_id)
        capa = CAPAService.create_from_hazard(user=request.user, hazard=hazard, status=CAPA.Status.OPEN)
        messages.success(request, "CAPA created from hazard.")
        return redirect(reverse("capa:detail", kwargs={"pk": capa.pk}))