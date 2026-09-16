from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from apps.organizations.models import Department, Plant

from .forms import (
    HIRAActionForm,
    HIRAForm,
    HIRAHazardFormSet,
    HIRAReportFilterForm,
    HIRASourceSelectForm,
    HazardRiskMasterForm,
    RiskMatrixForm,
    RiskMatrixLevelForm,
)
from .models import HIRA, HIRAAction, HIRAHazard, HIRAModule, HazardRiskMaster, RiskMatrix, RiskMatrixLevel
from .reports import filter_hira_queryset, filter_source_queryset, source_first_workbook_response, workbook_response
from .source_adapters import ADAPTERS, describe_source_object, get_adapter, get_source_object


class HIRAAccessMixin(LoginRequiredMixin):
    allowed_roles = ["ADMIN", "SAFETY OFFICER", "PLANT HEAD", "HOD"]

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        role_name = request.user.role.name if getattr(request.user, "role", None) else ""
        if not (
            request.user.is_superuser
            or getattr(request.user, "can_access_reports_module", False)
            or role_name in self.allowed_roles
        ):
            messages.error(request, "You don't have permission to access HIRA Management.")
            return redirect("dashboards:home")
        return super().dispatch(request, *args, **kwargs)

    def base_queryset(self):
        qs = HIRA.objects.select_related("plant", "department", "module", "prepared_by").prefetch_related("hazards")
        user = self.request.user
        is_admin = user.is_superuser or getattr(user, "is_admin_user", False)
        if not is_admin and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            return qs.filter(plant__in=plants) if plants else qs.none()
        return qs

    def can_approve_hira(self):
        user = self.request.user
        role_name = user.role.name if getattr(user, "role", None) else ""
        return user.is_superuser or role_name in ["ADMIN", "SAFETY OFFICER", "PLANT HEAD"]


class HIRAMasterAccessMixin(HIRAAccessMixin):
    master_roles = ["ADMIN", "SAFETY OFFICER"]

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        role_name = request.user.role.name if getattr(request.user, "role", None) else ""
        if not (request.user.is_superuser or getattr(request.user, "is_admin_user", False) or role_name in self.master_roles):
            messages.error(request, "You don't have permission to manage HIRA masters.")
            return redirect("hira:dashboard")
        return View.dispatch(self, request, *args, **kwargs)


def _master_suggestions_for_source(source_info):
    if not source_info:
        return HazardRiskMaster.objects.none()
    module = HIRAModule.objects.filter(name=source_info.module_name).first()
    qs = HazardRiskMaster.objects.filter(is_active=True).filter(Q(module__isnull=True) | Q(module=module))
    process = (source_info.process or "").strip()
    activity = (source_info.activity or "").strip()
    if process:
        qs = qs.filter(Q(process="") | Q(process__icontains=process) | Q(hazard__icontains=process))
    if activity:
        qs = qs.filter(Q(activity__icontains=activity) | Q(hazard__icontains=activity) | Q(hazard_category__icontains=activity))
    return qs.order_by("module__name", "activity", "hazard_category")[:10]


def _hazard_initial_from_master(rule, source_info):
    return {
        "master_rule": rule,
        "activity": rule.activity or source_info.activity,
        "hazard_category": rule.hazard_category,
        "hazard": rule.hazard,
        "unsafe_act": rule.unsafe_act or source_info.unsafe_act,
        "unsafe_condition": rule.unsafe_condition or source_info.unsafe_condition,
        "potential_consequence": rule.consequence,
        "existing_controls": rule.existing_controls or source_info.existing_action,
        "likelihood": rule.default_likelihood,
        "severity": rule.default_severity,
        "additional_controls": rule.suggested_additional_controls,
        "responsible_person": source_info.responsible_person,
        "target_date": source_info.target_date,
    }


def _risk_matrix_levels_context():
    levels = RiskMatrixLevel.objects.filter(
        risk_matrix__is_active=True,
        is_active=True,
    ).order_by("-risk_matrix__created_at", "display_order", "min_score")
    if levels.exists():
        return list(levels.values("min_score", "max_score", "risk_level"))
    return [
        {"min_score": 1, "max_score": 4, "risk_level": "Low"},
        {"min_score": 5, "max_score": 9, "risk_level": "Medium"},
        {"min_score": 10, "max_score": 16, "risk_level": "High"},
        {"min_score": 17, "max_score": 25, "risk_level": "Critical"},
    ]


class HIRADashboardView(HIRAAccessMixin, TemplateView):
    template_name = "hira/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.base_queryset()
        hazards = HIRAHazard.objects.filter(hira__in=qs)
        actions = HIRAAction.objects.filter(hazard__hira__in=qs)
        source_module_stats = []
        total_source_records = 0
        assessed_source_records = 0
        for adapter in ADAPTERS.values():
            source_qs = adapter.queryset(self.request.user)
            source_ids = set(source_qs.values_list("pk", flat=True))
            content_type = adapter.content_type()
            assessed_ids = set(
                qs.filter(
                    source_content_type=content_type,
                    source_object_id__in=source_ids,
                ).values_list("source_object_id", flat=True)
            )
            assessed_ids.update(
                HIRAHazard.objects.filter(
                    related_content_type=content_type,
                    related_object_id__in=source_ids,
                    hira__in=qs,
                ).values_list("related_object_id", flat=True)
            )
            assessed_count = len(assessed_ids)
            total_count = len(source_ids)
            total_source_records += total_count
            assessed_source_records += assessed_count
            source_module_stats.append({
                "module": adapter.module_name,
                "total": total_count,
                "assessed": assessed_count,
                "not_assessed": max(total_count - assessed_count, 0),
            })
        context.update(
            total_source_records=total_source_records,
            total_hiras=qs.count(),
            assessed_source_records=assessed_source_records,
            not_assessed_source_records=max(total_source_records - assessed_source_records, 0),
            approved_hiras=qs.filter(status="APPROVED").count(),
            critical_hazards=hazards.filter(initial_risk_level="Critical").count(),
            high_hazards=hazards.filter(initial_risk_level="High").count(),
            open_actions=actions.filter(status__in=["OPEN", "IN_PROGRESS", "OVERDUE"]).count(),
            overdue_actions=actions.filter(status="OVERDUE").count(),
            closed_actions=actions.filter(status__in=["COMPLETED", "VERIFIED", "CLOSED"]).count(),
            recent_hiras=qs[:8],
            risk_counts=hazards.values("initial_risk_level").annotate(total=Count("id")),
            source_module_stats=source_module_stats,
        )
        return context


class HIRAListView(HIRAAccessMixin, ListView):
    model = HIRA
    template_name = "hira/register.html"
    context_object_name = "hiras"
    paginate_by = 20

    def get_queryset(self):
        qs = self.base_queryset()
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(
                Q(hira_number__icontains=search)
                | Q(process__icontains=search)
                | Q(hazards__activity__icontains=search)
                | Q(hazards__hazard__icontains=search)
            )
        if self.request.GET.get("plant"):
            qs = qs.filter(plant_id=self.request.GET["plant"])
        if self.request.GET.get("department"):
            qs = qs.filter(department_id=self.request.GET["department"])
        if self.request.GET.get("module"):
            qs = qs.filter(module_id=self.request.GET["module"])
        if self.request.GET.get("risk_level"):
            qs = qs.filter(hazards__initial_risk_level=self.request.GET["risk_level"])
        if self.request.GET.get("status"):
            qs = qs.filter(status=self.request.GET["status"])
        if self.request.GET.get("source_module"):
            adapter = get_adapter(self.request.GET["source_module"])
            if adapter:
                qs = qs.filter(source_content_type=adapter.content_type())
        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            plants=Plant.objects.filter(is_active=True),
            departments=Department.objects.filter(is_active=True),
            modules=HIRAModule.objects.filter(is_active=True),
            status_choices=HIRA.STATUS_CHOICES,
            risk_levels=["Low", "Medium", "High", "Critical"],
            source_form=HIRAReportFilterForm(self.request.GET or None, user=self.request.user),
        )
        return context


class HIRACreateView(HIRAAccessMixin, CreateView):
    model = HIRA
    form_class = HIRAForm
    template_name = "hira/form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.GET.get("source_module") and request.GET.get("standalone") != "1":
            return redirect("hira:create_from_source")
        return super().dispatch(request, *args, **kwargs)

    def get_source_info(self):
        source_type = self.request.GET.get("source_module")
        source_id = self.request.GET.get("source_record")
        source = get_source_object(source_type, source_id, user=self.request.user)
        return describe_source_object(source)

    def get_initial(self):
        initial = super().get_initial()
        source_info = self.get_source_info()
        if not source_info:
            return initial
        module = HIRAModule.objects.filter(name=source_info.module_name).first()
        initial.update(
            plant=source_info.plant,
            department=source_info.department or getattr(self.request.user, "department", None),
            module=module,
            process=source_info.process,
            assessment_date=source_info.record_date,
            assessment_type="INCIDENT_REVIEW" if source_info.source_type == "incident" else "REVIEW",
        )
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        source_info = self.get_source_info()
        hazard_initial = []
        if source_info:
            master_suggestions = list(_master_suggestions_for_source(source_info))
            if master_suggestions:
                hazard_initial = [
                    _hazard_initial_from_master(rule, source_info)
                    for rule in master_suggestions
                ]
            else:
                hazard_initial = [{
                    "activity": source_info.activity,
                    "unsafe_act": source_info.unsafe_act,
                    "unsafe_condition": source_info.unsafe_condition,
                    "existing_controls": source_info.existing_action,
                    "responsible_person": source_info.responsible_person,
                    "target_date": source_info.target_date,
                }]
        if self.request.POST:
            context["hazard_formset"] = HIRAHazardFormSet(self.request.POST, user=self.request.user)
        else:
            context["hazard_formset"] = HIRAHazardFormSet(user=self.request.user, initial=hazard_initial)
        context["action"] = "Create"
        context["source_info"] = source_info
        context["master_suggestions"] = list(_master_suggestions_for_source(source_info)) if source_info else []
        context["risk_matrix_levels"] = _risk_matrix_levels_context()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        hazard_formset = context["hazard_formset"]
        if not hazard_formset.is_valid():
            return self.form_invalid(form)
        self.object = form.save(commit=False)
        self.object.created_by = self.request.user
        self.object.prepared_by = self.request.user
        source_info = self.get_source_info()
        if source_info:
            source = get_source_object(source_info.source_type, source_info.record_id, user=self.request.user)
            adapter = get_adapter(source_info.source_type)
            self.object.source_content_type = adapter.content_type()
            self.object.source_object_id = source.pk
        self.object.save()
        hazard_formset.instance = self.object
        hazards = hazard_formset.save(commit=False)
        for hazard in hazards:
            if source_info and not hazard.related_object_id:
                source = get_source_object(source_info.source_type, source_info.record_id, user=self.request.user)
                adapter = get_adapter(source_info.source_type)
                hazard.related_content_type = adapter.content_type()
                hazard.related_object_id = source.pk
            hazard.save()
        for deleted in hazard_formset.deleted_objects:
            deleted.delete()
        messages.success(self.request, f"HIRA {self.object.hira_number} created successfully.")
        return redirect("hira:detail", pk=self.object.pk)


class HIRACreateFromSourceView(HIRAAccessMixin, TemplateView):
    template_name = "hira/source_select.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = HIRASourceSelectForm(self.request.GET or None, user=self.request.user)
        return context

    def get(self, request, *args, **kwargs):
        form = HIRASourceSelectForm(request.GET or None, user=request.user)
        if form.is_valid():
            return redirect(
                f"{reverse_lazy('hira:create')}?source_module={form.cleaned_data['source_module']}"
                f"&source_record={form.cleaned_data['source_record']}"
            )
        return super().get(request, *args, **kwargs)


class HIRAUpdateView(HIRAAccessMixin, UpdateView):
    model = HIRA
    form_class = HIRAForm
    template_name = "hira/form.html"

    def get_queryset(self):
        return self.base_queryset()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["hazard_formset"] = HIRAHazardFormSet(self.request.POST, instance=self.object, user=self.request.user)
        else:
            context["hazard_formset"] = HIRAHazardFormSet(instance=self.object, user=self.request.user)
        context["action"] = "Update"
        context["risk_matrix_levels"] = _risk_matrix_levels_context()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        hazard_formset = context["hazard_formset"]
        if not hazard_formset.is_valid():
            return self.form_invalid(form)
        self.object = form.save()
        hazard_formset.instance = self.object
        hazard_formset.save()
        messages.success(self.request, f"HIRA {self.object.hira_number} updated successfully.")
        return redirect("hira:detail", pk=self.object.pk)


class HIRADetailView(HIRAAccessMixin, DetailView):
    model = HIRA
    template_name = "hira/detail.html"
    context_object_name = "hira"

    def get_queryset(self):
        return self.base_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_approve"] = self.can_approve_hira()
        context["actions"] = HIRAAction.objects.filter(hazard__hira=self.object).select_related("hazard", "responsible_person")
        context["source_info"] = describe_source_object(self.object.source_record)
        context["hazard_sources"] = {
            hazard.pk: describe_source_object(hazard.related_record)
            for hazard in self.object.hazards.all()
        }
        return context


class HIRAStatusView(HIRAAccessMixin, View):
    def post(self, request, pk, action):
        hira = get_object_or_404(self.base_queryset(), pk=pk)
        if action == "submit" and hira.status in ["DRAFT", "REJECTED"]:
            hira.status = "SUBMITTED"
            messages.success(request, f"{hira.hira_number} submitted for review.")
        elif action == "review" and hira.status == "SUBMITTED" and self.can_approve_hira():
            hira.status = "UNDER_REVIEW"
            hira.reviewed_by = request.user
            messages.success(request, f"{hira.hira_number} moved under review.")
        elif action == "approve" and hira.status in ["SUBMITTED", "UNDER_REVIEW"] and self.can_approve_hira():
            hira.status = "APPROVED"
            hira.approved_by = request.user
            hira.approval_date = timezone.now().date()
            if not hira.reviewed_by:
                hira.reviewed_by = request.user
            messages.success(request, f"{hira.hira_number} approved.")
        elif action == "reject" and hira.status in ["SUBMITTED", "UNDER_REVIEW"] and self.can_approve_hira():
            hira.status = "REJECTED"
            hira.reviewed_by = request.user
            messages.warning(request, f"{hira.hira_number} rejected for revision.")
        else:
            messages.error(request, "That HIRA workflow action is not available.")
            return redirect("hira:detail", pk=hira.pk)
        hira.save()
        return redirect("hira:detail", pk=hira.pk)


class HIRAActionListView(HIRAAccessMixin, ListView):
    model = HIRAAction
    template_name = "hira/actions.html"
    context_object_name = "actions"
    paginate_by = 25

    def get_queryset(self):
        qs = HIRAAction.objects.select_related("hazard", "hazard__hira", "responsible_person")
        qs = qs.filter(hazard__hira__in=self.base_queryset())
        if self.request.GET.get("status"):
            qs = qs.filter(status=self.request.GET["status"])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = HIRAAction.STATUS_CHOICES
        return context


class HIRAActionUpdateView(HIRAAccessMixin, UpdateView):
    model = HIRAAction
    form_class = HIRAActionForm
    template_name = "hira/action_form.html"

    def get_queryset(self):
        return HIRAAction.objects.filter(hazard__hira__in=self.base_queryset())

    def get_success_url(self):
        return reverse_lazy("hira:detail", kwargs={"pk": self.object.hazard.hira_id})


class HIRAHazardMasterListView(HIRAMasterAccessMixin, ListView):
    model = HazardRiskMaster
    template_name = "hira/masters/hazard_master_list.html"
    context_object_name = "rules"
    paginate_by = 25

    def get_queryset(self):
        qs = HazardRiskMaster.objects.select_related("module", "created_by")
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(
                Q(activity__icontains=search)
                | Q(process__icontains=search)
                | Q(hazard__icontains=search)
                | Q(consequence__icontains=search)
            )
        if self.request.GET.get("module"):
            if self.request.GET["module"] == "ALL":
                qs = qs.filter(module__isnull=True)
            else:
                qs = qs.filter(module_id=self.request.GET["module"])
        if self.request.GET.get("activity"):
            qs = qs.filter(activity__icontains=self.request.GET["activity"])
        if self.request.GET.get("hazard_category"):
            qs = qs.filter(hazard_category=self.request.GET["hazard_category"])
        if self.request.GET.get("active") in ["1", "0"]:
            qs = qs.filter(is_active=self.request.GET["active"] == "1")
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["modules"] = HIRAModule.objects.filter(is_active=True)
        context["hazard_categories"] = HIRAHazard.HAZARD_CATEGORY_CHOICES
        return context


class HIRAHazardMasterDetailView(HIRAMasterAccessMixin, DetailView):
    model = HazardRiskMaster
    template_name = "hira/masters/hazard_master_detail.html"
    context_object_name = "rule"


class HIRAHazardMasterCreateView(HIRAMasterAccessMixin, CreateView):
    model = HazardRiskMaster
    form_class = HazardRiskMasterForm
    template_name = "hira/masters/hazard_master_form.html"
    success_url = reverse_lazy("hira:hazard_master")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Hazard & Risk Master rule created.")
        return super().form_valid(form)


class HIRAHazardMasterUpdateView(HIRAMasterAccessMixin, UpdateView):
    model = HazardRiskMaster
    form_class = HazardRiskMasterForm
    template_name = "hira/masters/hazard_master_form.html"
    success_url = reverse_lazy("hira:hazard_master")

    def form_valid(self, form):
        messages.success(self.request, "Hazard & Risk Master rule updated.")
        return super().form_valid(form)


class HIRAHazardMasterDeleteView(HIRAMasterAccessMixin, DeleteView):
    model = HazardRiskMaster
    template_name = "hira/masters/confirm_delete.html"
    success_url = reverse_lazy("hira:hazard_master")

    def form_valid(self, form):
        messages.success(self.request, "Hazard & Risk Master rule deleted.")
        return super().form_valid(form)


class HIRAHazardMasterToggleView(HIRAMasterAccessMixin, View):
    def post(self, request, pk):
        rule = get_object_or_404(HazardRiskMaster, pk=pk)
        rule.is_active = not rule.is_active
        rule.save(update_fields=["is_active", "updated_at"])
        messages.success(request, f"Rule {'activated' if rule.is_active else 'deactivated'}.")
        return redirect("hira:hazard_master")


class HIRARiskMatrixListView(HIRAMasterAccessMixin, ListView):
    model = RiskMatrix
    template_name = "hira/masters/risk_matrix_list.html"
    context_object_name = "matrices"

    def get_queryset(self):
        return RiskMatrix.objects.prefetch_related("levels").order_by("-is_active", "name")


class HIRARiskMatrixCreateView(HIRAMasterAccessMixin, CreateView):
    model = RiskMatrix
    form_class = RiskMatrixForm
    template_name = "hira/masters/risk_matrix_form.html"
    success_url = reverse_lazy("hira:risk_matrix_master")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Risk Matrix created.")
        return super().form_valid(form)


class HIRARiskMatrixUpdateView(HIRAMasterAccessMixin, UpdateView):
    model = RiskMatrix
    form_class = RiskMatrixForm
    template_name = "hira/masters/risk_matrix_form.html"
    success_url = reverse_lazy("hira:risk_matrix_master")

    def form_valid(self, form):
        messages.success(self.request, "Risk Matrix updated.")
        return super().form_valid(form)


class HIRARiskMatrixLevelCreateView(HIRAMasterAccessMixin, CreateView):
    model = RiskMatrixLevel
    form_class = RiskMatrixLevelForm
    template_name = "hira/masters/risk_matrix_level_form.html"
    success_url = reverse_lazy("hira:risk_matrix_master")

    def get_initial(self):
        initial = super().get_initial()
        matrix_id = self.request.GET.get("matrix")
        if matrix_id:
            initial["risk_matrix"] = matrix_id
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Risk Matrix level created.")
        return super().form_valid(form)


class HIRARiskMatrixLevelUpdateView(HIRAMasterAccessMixin, UpdateView):
    model = RiskMatrixLevel
    form_class = RiskMatrixLevelForm
    template_name = "hira/masters/risk_matrix_level_form.html"
    success_url = reverse_lazy("hira:risk_matrix_master")

    def form_valid(self, form):
        messages.success(self.request, "Risk Matrix level updated.")
        return super().form_valid(form)


class HIRARiskMatrixLevelDeleteView(HIRAMasterAccessMixin, DeleteView):
    model = RiskMatrixLevel
    template_name = "hira/masters/confirm_delete.html"
    success_url = reverse_lazy("hira:risk_matrix_master")

    def form_valid(self, form):
        messages.success(self.request, "Risk Matrix level deleted.")
        return super().form_valid(form)


class HIRAReportView(HIRAAccessMixin, TemplateView):
    template_name = "hira/report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = HIRAReportFilterForm(self.request.GET or None, user=self.request.user)
        context["form"] = form
        context["preview_count"] = filter_hira_queryset(self.request, form).count() if form.is_valid() else 0
        return context


class HIRAExcelExportView(HIRAAccessMixin, View):
    def get(self, request):
        form = HIRAReportFilterForm(request.GET or None, user=request.user)
        adapter, source_records = filter_source_queryset(request, form)
        if adapter:
            data = form.cleaned_data if form.is_valid() else request.GET
            return source_first_workbook_response(adapter, source_records, data=data)
        hiras = filter_hira_queryset(request, form)
        return workbook_response(hiras)


class HIRASourceRecordsAjaxView(HIRAAccessMixin, View):
    def get(self, request):
        adapter = get_adapter(request.GET.get("source_module"))
        if not adapter:
            return JsonResponse([], safe=False)
        data = [
            {"id": pk, "label": label}
            for pk, label in adapter.choices(user=request.user, limit=100)
        ]
        return JsonResponse(data, safe=False)
