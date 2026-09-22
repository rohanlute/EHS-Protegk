from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncMonth
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.organizations.models import Department, Plant

from .audit import get_ergonomic_audit_logs, log_ergonomic_action
from .forms import (
    ErgonomicAssessmentForm,
    ErgonomicAssessmentMethodForm,
    ErgonomicAssessmentScheduleForm,
    ErgonomicControlForm,
    CorrectiveActionRejectForm,
    ErgonomicCorrectiveActionCreateForm,
    ErgonomicCorrectiveActionDefinitionEditForm,
    ErgonomicCorrectiveActionForm,
    ErgonomicJobMappingForm,
    ErgonomicObservationForm,
    ErgonomicReassessmentForm,
    ErgonomicRiskFactorForm,
    MSDDiscomfortForm,
    MyActionUpdateForm,
    NIOSHForm,
    SnookCirielloForm,
    REBAForm,
    StrainIndexForm,
    OWASForm,
    OCRAForm,
    RULAForm,
)
from .models import (
    ErgonomicAssessment,
    ErgonomicAssessmentMethod,
    ErgonomicAssessmentSchedule,
    ErgonomicControl,
    ErgonomicCorrectiveAction,
    ErgonomicJobMapping,
    ErgonomicObservation,
    ErgonomicReassessment,
    ErgonomicAuditLog,
    ErgonomicRiskFactor,
    MSDDiscomfort,
    SnookCirielloAssessment,
    OWASAssessment,
    StrainIndexAssessment,
    OCRAAssessment,
    NIOSHLiftingAssessment,
    REBAAssessment,
    RULAAssessment,
)
from .reports import (
    filter_assessments,
    workbook_response,
    department_report_response,
    management_report_response,
)

User = get_user_model()


# =============================================================================
# ACCESS MIXIN
# =============================================================================
class ErgonomicsAccessMixin(LoginRequiredMixin):
    allowed_roles = [
        "ADMIN",
        "SAFETY MANAGER",
        "EHS MANAGER",
        "EHS OFFICER",
        "PLANT HEAD",
        "HOD",
    ]

    # Only Plant Heads may approve/reject corrective actions
    verify_roles = {"PLANT HEAD"}

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        role_name = request.user.role.name if getattr(request.user, "role", None) else ""
        if not (
            request.user.is_superuser
            or getattr(request.user, "can_access_reports_module", False)
            or role_name in self.allowed_roles
        ):
            messages.error(request, "You don't have permission to access Ergonomics.")
            return redirect("dashboards:home")
        return super().dispatch(request, *args, **kwargs)

    def base_queryset(self):
        qs = ErgonomicAssessment.objects.select_related(
            "plant", "department", "assessment_method", "worker", "assessor"
        )
        user = self.request.user
        if not user.is_superuser and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            return qs.filter(plant__in=plants) if plants else qs.none()
        return qs

    def can_verify(self, user, action):
        """
        True if `user` may approve/reject `action`.

        Only Plant Heads (scoped to their accessible plants) and superusers.
        """
        if user.is_superuser:
            return True

        role_name = user.role.name if getattr(user, "role", None) else ""
        if role_name not in self.verify_roles:
            return False

        if hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            if plants is not None:
                plant_ids = {p.pk for p in plants}
                assessment_plant_id = (
                    action.assessment.plant_id if action.assessment else None
                )
                if assessment_plant_id not in plant_ids:
                    return False

        return True


# =============================================================================
# DASHBOARD
# =============================================================================
class ErgonomicsDashboardView(ErgonomicsAccessMixin, TemplateView):
    template_name = "ergonomics/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ErgonomicCorrectiveAction.objects.refresh_overdue()

        assessments = filter_assessments(self.request)
        actions = ErgonomicCorrectiveAction.objects.filter(assessment__in=assessments)
        msd = MSDDiscomfort.objects.filter(
            Q(related_assessment__in=assessments) | Q(related_assessment__isnull=True)
        )
        scores = assessments.exclude(score__isnull=True)

        context.update(
            assessments=assessments[:8],
            total_assessments=assessments.count(),
            high_risk=assessments.filter(risk_level="HIGH").count(),
            very_high_risk=assessments.filter(risk_level="VERY_HIGH").count(),
            open_actions=actions.exclude(status__in=["COMPLETED", "CLOSED"]).count(),
            overdue_actions=actions.filter(status="OVERDUE").count(),
            completed_actions=actions.filter(status__in=["COMPLETED", "CLOSED"]).count(),
            msd_cases=msd.count(),
            assessments_due=ErgonomicAssessmentSchedule.objects.filter(
                status__in=["DUE", "OVERDUE"]
            ).count(),
            average_score=round(scores.aggregate(avg=Avg("score"))["avg"] or 0, 2),
            risk_reduction=round(
                ErgonomicReassessment.objects.filter(assessment__in=assessments).aggregate(
                    avg=Avg("risk_reduction_percent")
                )["avg"]
                or 0,
                2,
            ),
        )

        context.update(
            plants=Plant.objects.filter(is_active=True),
            departments=Department.objects.filter(is_active=True),
            methods=ErgonomicAssessmentMethod.objects.filter(is_active=True),
            statuses=ErgonomicAssessment.STATUS_CHOICES,
            areas=assessments.exclude(area="").values_list("area", flat=True).distinct()[:50],
            assessors=User.objects.filter(ergonomic_assessments_done__isnull=False)
            .distinct()
            .order_by("first_name", "last_name"),
        )

        context["risk_distribution"] = assessments.values("risk_level").annotate(total=Count("id"))
        context["department_distribution"] = (
            assessments.values("department__name")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )
        context["risk_trend"] = (
            assessments.exclude(score__isnull=True)
            .annotate(month=TruncMonth("assessment_date"))
            .values("month")
            .annotate(avg_score=Avg("score"), total=Count("id"))
            .order_by("month")
        )
        context["risk_by_site"] = (
            assessments.values("plant__name").annotate(total=Count("id")).order_by("-total")
        )
        context["high_risk_tasks"] = (
            assessments.filter(risk_level__in=["HIGH", "VERY_HIGH"])
            .values("task")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )
        context["body_parts"] = msd.values("body_part").annotate(total=Count("id")).order_by("-total")
        context["action_status"] = actions.values("status").annotate(total=Count("id"))
        context["before_after"] = ErgonomicReassessment.objects.filter(
            assessment__in=assessments
        ).values("assessment__assessment_id", "previous_score", "new_score")[:10]
        context["method_usage"] = (
            assessments.values("assessment_method__name")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        context["overdue_list"] = actions.filter(status="OVERDUE")[:5]

        context["risk_by_job"] = (
            assessments.values("job_role")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )
        context["risk_by_task"] = (
            assessments.values("task")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )
        context["risk_by_shift"] = (
            assessments.exclude(shift="")
            .values("shift")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        context["risk_by_month"] = (
            assessments.annotate(month=TruncMonth("assessment_date"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )

        return context


# =============================================================================
# ASSESSMENT LIST / CREATE / UPDATE / DETAIL / DELETE
# =============================================================================
class ErgonomicAssessmentListView(ErgonomicsAccessMixin, ListView):
    model = ErgonomicAssessment
    template_name = "ergonomics/assessment_list.html"
    context_object_name = "assessments"
    paginate_by = 25

    def get_queryset(self):
        qs = filter_assessments(self.request)
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(
                Q(assessment_id__icontains=search)
                | Q(job_role__icontains=search)
                | Q(task__icontains=search)
                | Q(worker__first_name__icontains=search)
                | Q(worker__last_name__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            plants=Plant.objects.filter(is_active=True),
            departments=Department.objects.filter(is_active=True),
            methods=ErgonomicAssessmentMethod.objects.filter(is_active=True),
            risk_levels=ErgonomicAssessment.RISK_LEVEL_CHOICES,
            status_choices=ErgonomicAssessment.STATUS_CHOICES,
        )
        return context


class ErgonomicAssessmentCreateView(ErgonomicsAccessMixin, CreateView):
    model = ErgonomicAssessment
    form_class = ErgonomicAssessmentForm
    template_name = "ergonomics/assessment_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        if not form.instance.assessor:
            form.instance.assessor = self.request.user

        # Every new assessment starts as SUBMITTED
        form.instance.status = "SUBMITTED"

        response = super().form_valid(form)

        log_ergonomic_action(
            user=self.request.user,
            action=ErgonomicAuditLog.ACTION_CREATE,
            instance=self.object,
            changes={"status": ["", "SUBMITTED"]},
            message=f"Assessment created for task '{self.object.task}'.",
            request=self.request,
        )

        messages.success(
            self.request,
            "Ergonomic assessment created. Add method-specific scoring next.",
        )
        return response

    def get_success_url(self):
        return reverse_lazy("ergonomics:detail", kwargs={"pk": self.object.pk})


class ErgonomicAssessmentUpdateView(ErgonomicsAccessMixin, UpdateView):
    model = ErgonomicAssessment
    form_class = ErgonomicAssessmentForm
    template_name = "ergonomics/assessment_form.html"

    def get_queryset(self):
        return self.base_queryset()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)

        log_ergonomic_action(
            user=self.request.user,
            action=ErgonomicAuditLog.ACTION_UPDATE,
            instance=self.object,
            changes={
                f: [
                    str(form.initial.get(f, "")),
                    str(form.cleaned_data.get(f, "")),
                ]
                for f in form.changed_data
            } or {},
            message="Assessment details updated.",
            request=self.request,
        )

        messages.success(self.request, "Ergonomic assessment updated.")
        return response

    def get_success_url(self):
        return reverse_lazy("ergonomics:detail", kwargs={"pk": self.object.pk})


class ErgonomicAssessmentDetailView(ErgonomicsAccessMixin, DetailView):
    model = ErgonomicAssessment
    template_name = "ergonomics/assessment_detail.html"
    context_object_name = "assessment"

    def get_queryset(self):
        return self.base_queryset()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["actions"] = (
            ErgonomicCorrectiveAction.objects
            .filter(assessment=self.object)
            .select_related("responsible_person", "department")
            .order_by("-created_at")
        )

        ctx["reassessments"] = (
            ErgonomicReassessment.objects
            .filter(assessment=self.object)
            .select_related("corrective_action", "assessor")
            .order_by("-reassessment_date")
        )

        ctx["audit_logs"] = get_ergonomic_audit_logs(self.object, limit=30)

        ctx["reviews"] = []
        return ctx


class ErgonomicAssessmentDeleteView(ErgonomicsAccessMixin, DeleteView):
    model = ErgonomicAssessment
    template_name = "ergonomics/confirm_delete.html"
    success_url = reverse_lazy("ergonomics:assessments")

    def get_queryset(self):
        return self.base_queryset()

    def form_valid(self, form):
        # Log BEFORE deletion so we still have the object reference
        obj = self.get_object()
        log_ergonomic_action(
            user=self.request.user,
            action=ErgonomicAuditLog.ACTION_DELETE,
            instance=obj,
            message=f"Assessment {obj.assessment_id} deleted.",
            request=self.request,
        )
        return super().form_valid(form)


# =============================================================================
# GENERIC HELPERS
# =============================================================================
class RelatedCreateView(ErgonomicsAccessMixin, CreateView):
    template_name = "ergonomics/simple_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if hasattr(form.instance, "created_by_id") and not form.instance.created_by_id:
            form.instance.created_by = self.request.user
        if hasattr(form.instance, "observer_id") and not form.instance.observer_id:
            form.instance.observer = self.request.user
        if hasattr(form.instance, "assessor_id") and not form.instance.assessor_id:
            form.instance.assessor = self.request.user
        messages.success(self.request, "Record saved.")
        return super().form_valid(form)


# =============================================================================
# RISK FACTORS
# =============================================================================
class RiskFactorUpdateView(ErgonomicsAccessMixin, UpdateView):
    model = ErgonomicRiskFactor
    form_class = ErgonomicRiskFactorForm
    template_name = "ergonomics/risk_factor_form.html"

    def get_object(self):
        self.assessment = get_object_or_404(
            self.base_queryset(), pk=self.kwargs["assessment_pk"]
        )
        obj, _ = ErgonomicRiskFactor.objects.get_or_create(assessment=self.assessment)
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["assessment"] = self.assessment
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)

        log_ergonomic_action(
            user=self.request.user,
            action=ErgonomicAuditLog.ACTION_UPDATE,
            instance=self.assessment,
            message="Risk factors updated.",
            request=self.request,
        )

        messages.success(self.request, "Risk factors saved.")
        return response

    def get_success_url(self):
        return reverse_lazy("ergonomics:detail", kwargs={"pk": self.assessment.pk})


# =============================================================================
# METHOD-SPECIFIC SCORING
# =============================================================================
class MethodScoreUpdateView(ErgonomicsAccessMixin, UpdateView):
    template_name = "ergonomics/simple_form.html"

    method_map = {
        "rula": (RULAAssessment, RULAForm),
        "reba": (REBAAssessment, REBAForm),
        "niosh": (NIOSHLiftingAssessment, NIOSHForm),
        "owas": (OWASAssessment, OWASForm),
        "ocra": (OCRAAssessment, OCRAForm),
        "strain_index": (StrainIndexAssessment, StrainIndexForm),
        "snook_ciriello": (SnookCirielloAssessment, SnookCirielloForm),
    }

    def dispatch(self, request, *args, **kwargs):
        if kwargs.get("method") not in self.method_map:
            raise Http404("Unknown ergonomic assessment method.")
        self.model, self.form_class = self.method_map[kwargs["method"]]
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        assessment = get_object_or_404(
            self.base_queryset(), pk=self.kwargs["assessment_pk"]
        )
        defaults = {"assessment": assessment}
        method = self.kwargs["method"]

        if method == "niosh":
            defaults.update(
                load_weight=1,
                horizontal_location=25,
                vertical_location=75,
                vertical_travel_distance=25,
                frequency_lifts_per_minute=0.2,
                duration_hours=1,
            )

        elif method == "snook_ciriello":
            defaults.update(
                actual_load=1,
                task_type="LIFT",
                gender="MALE",
                position="KNUCKLE",
                percentile=50,
            )

        obj, _ = self.model.objects.get_or_create(
            assessment=assessment, defaults=defaults
        )
        return obj

    def form_valid(self, form):
        response = super().form_valid(form)

        log_ergonomic_action(
            user=self.request.user,
            action=ErgonomicAuditLog.ACTION_UPDATE,
            instance=self.object.assessment,
            message=f"Method scoring ({self.kwargs['method'].upper()}) updated.",
            request=self.request,
        )
        return response

    def get_success_url(self):
        return reverse_lazy("ergonomics:detail", kwargs={"pk": self.object.assessment_id})


# =============================================================================
# QUICK OBSERVATIONS
# =============================================================================
class ErgonomicObservationListView(ErgonomicsAccessMixin, ListView):
    model = ErgonomicObservation
    template_name = "ergonomics/observation_list.html"
    context_object_name = "observations"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            ErgonomicObservation.objects
            .select_related("plant", "department", "worker", "observer", "assessment")
            .order_by("-observation_date", "-id")
        )
        user = self.request.user
        if not user.is_superuser and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            qs = qs.filter(plant__in=plants) if plants else qs.none()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base_qs = self.get_queryset()

        ctx["total_count"] = base_qs.count()
        ctx["high_risk_count"] = base_qs.filter(
            risk_level__in=["HIGH", "VERY_HIGH"]
        ).count()
        ctx["converted_count"] = base_qs.filter(assessment__isnull=False).count()
        ctx["pending_count"] = base_qs.filter(assessment__isnull=True).count()
        return ctx


class ErgonomicObservationCreateView(RelatedCreateView):
    model = ErgonomicObservation
    form_class = ErgonomicObservationForm
    template_name = "ergonomics/observation_form.html"
    success_url = reverse_lazy("ergonomics:observations")

    def form_valid(self, form):
        response = super().form_valid(form)

        log_ergonomic_action(
            user=self.request.user,
            action=ErgonomicAuditLog.ACTION_CREATE,
            instance=self.object,
            message=f"Quick observation recorded: {self.object.task}.",
            request=self.request,
        )
        return response


class ConvertObservationView(ErgonomicsAccessMixin, View):
    def post(self, request, pk):
        observation = get_object_or_404(
            ErgonomicObservation.objects.filter(plant__in=self._accessible_plants(request.user)),
            pk=pk,
        )
        method = ErgonomicAssessmentMethod.objects.filter(is_active=True).first()
        if method is None:
            messages.error(
                request,
                "No active assessment method is configured. Add one under Assessment Methods before converting observations.",
            )
            return redirect("ergonomics:observations")

        assessment = ErgonomicAssessment.objects.create(
            plant=observation.plant,
            department=observation.department,
            area=observation.area,
            job_role=getattr(observation.worker, "job_title", "") or "Observed Job",
            task=observation.task,
            worker=observation.worker,
            assessment_date=observation.observation_date,
            assessor=request.user,
            assessment_method=method,
            task_description=observation.observation,
            created_by=request.user,
            status="SUBMITTED",
        )
        observation.assessment = assessment
        observation.save(update_fields=["assessment"])

        log_ergonomic_action(
            user=request.user,
            action=ErgonomicAuditLog.ACTION_CREATE,
            instance=assessment,
            message=f"Created from observation #{observation.pk}.",
            request=request,
        )

        messages.success(request, "Observation converted to ergonomic assessment.")
        return redirect("ergonomics:detail", pk=assessment.pk)

    def _accessible_plants(self, user):
        if user.is_superuser or not hasattr(user, "get_all_plants"):
            return Plant.objects.all()
        return user.get_all_plants()


class ConvertObservationConfirmView(ErgonomicsAccessMixin, View):
    def get(self, request, pk):
        observation = get_object_or_404(
            ErgonomicObservation.objects.filter(plant__in=self._accessible_plants(request.user)),
            pk=pk,
        )

        if observation.assessment_id:
            messages.info(request, "This observation has already been converted.")
            return redirect("ergonomics:detail", pk=observation.assessment_id)

        methods = ErgonomicAssessmentMethod.objects.filter(is_active=True)
        workers = (
            User.objects
            .filter(is_active=True)
            .order_by("first_name", "last_name")
        )

        return render(
            request,
            "ergonomics/observation_convert_confirm.html",
            {
                "observation": observation,
                "methods": methods,
                "workers": workers,
                "selected_worker_id": observation.worker_id,
            },
        )

    def post(self, request, pk):
        observation = get_object_or_404(
            ErgonomicObservation.objects.filter(plant__in=self._accessible_plants(request.user)),
            pk=pk,
        )

        if observation.assessment_id:
            messages.info(request, "This observation has already been converted.")
            return redirect("ergonomics:detail", pk=observation.assessment_id)

        method_id = request.POST.get("assessment_method")
        if not method_id:
            messages.error(request, "Please choose an assessment method.")
            return redirect("ergonomics:observation_convert_confirm", pk=pk)

        method = get_object_or_404(
            ErgonomicAssessmentMethod,
            pk=method_id,
            is_active=True,
        )

        # ---- WORKER (from the dropdown) ----
        worker_id = request.POST.get("worker") or None
        if worker_id:
            worker = get_object_or_404(User, pk=worker_id, is_active=True)
        else:
            worker = observation.worker

        # ---- JOB ROLE (derived, not user-typed) ----
        job_role = (getattr(worker, "job_title", "") or "").strip()
        if not job_role:
            job_role = (getattr(observation.worker, "job_title", "") or "").strip()
        if not job_role:
            job_role = "Observed Job"

        assessment = ErgonomicAssessment.objects.create(
            plant=observation.plant,
            department=observation.department,
            area=observation.area,
            job_role=job_role,
            task=observation.task,
            worker=worker,
            assessment_date=observation.observation_date,
            assessor=request.user,
            assessment_method=method,
            task_description=observation.observation,
            created_by=request.user,
            status="SUBMITTED",
        )

        observation.assessment = assessment
        observation.save(update_fields=["assessment"])

        log_ergonomic_action(
            user=request.user,
            action=ErgonomicAuditLog.ACTION_CREATE,
            instance=assessment,
            message=f"Created from observation #{observation.pk} using {method.name}.",
            request=request,
        )

        messages.success(
            request,
            f"Observation converted to ergonomic assessment using {method.name}.",
        )
        return redirect("ergonomics:detail", pk=assessment.pk)

    def _accessible_plants(self, user):
        if user.is_superuser or not hasattr(user, "get_all_plants"):
            return Plant.objects.all()
        return user.get_all_plants()


# =============================================================================
# CORRECTIVE ACTIONS
# =============================================================================
class CorrectiveActionListView(ErgonomicsAccessMixin, ListView):
    model = ErgonomicCorrectiveAction
    template_name = "ergonomics/action_list.html"
    context_object_name = "actions"
    paginate_by = 25

    def get_queryset(self):
        ErgonomicCorrectiveAction.objects.refresh_overdue()

        qs = (
            ErgonomicCorrectiveAction.objects
            .select_related("assessment", "responsible_person", "department")
            .order_by("-created_at", "-id")           # ← ADD THIS
        )
        if self.request.GET.get("status"):
            qs = qs.filter(status=self.request.GET["status"])
        return qs


class CorrectiveActionCreateView(RelatedCreateView):
    model = ErgonomicCorrectiveAction
    form_class = ErgonomicCorrectiveActionCreateForm
    success_url = reverse_lazy("ergonomics:actions")

    def get_initial(self):
        initial = super().get_initial()
        assessment_id = self.request.GET.get("assessment")
        if assessment_id:
            initial["assessment"] = assessment_id
        return initial

    def form_valid(self, form):
        # Inherit department from the assessment
        if form.instance.assessment_id and not form.instance.department_id:
            form.instance.department = form.instance.assessment.department

        form.instance.status = "ASSIGNED"
        response = super().form_valid(form)

        log_ergonomic_action(
            user=self.request.user,
            action=ErgonomicAuditLog.ACTION_CREATE,
            instance=self.object,
            changes={"status": ["", "ASSIGNED"]},
            message="Corrective action created and assigned.",
            request=self.request,
        )

        if self.object.assessment_id:
            self.object.assessment.refresh_status()

        return response

    def get_success_url(self):
        assessment_id = self.request.POST.get("assessment") or self.request.GET.get("assessment")
        if assessment_id:
            return reverse_lazy("ergonomics:detail", kwargs={"pk": assessment_id})
        return reverse_lazy("ergonomics:actions")

class CorrectiveActionDetailView(ErgonomicsAccessMixin, DetailView):
    model = ErgonomicCorrectiveAction
    template_name = "ergonomics/action_detail.html"
    context_object_name = "action"

    def get_queryset(self):
        return (
            ErgonomicCorrectiveAction.objects
            .select_related(
                "assessment",
                "assessment__plant",
                "assessment__department",
                "responsible_person",
                "department",
                "created_by",
                "verified_by",
                "rejected_by",
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["audit_logs"] = get_ergonomic_audit_logs(self.object, limit=50)
        return ctx


class CorrectiveActionUpdateView(ErgonomicsAccessMixin, UpdateView):
    model = ErgonomicCorrectiveAction
    form_class = ErgonomicCorrectiveActionDefinitionEditForm
    template_name = "ergonomics/simple_form.html"
    success_url = reverse_lazy("ergonomics:actions")

    def form_valid(self, form):
        response = super().form_valid(form)

        log_ergonomic_action(
            user=self.request.user,
            action=ErgonomicAuditLog.ACTION_UPDATE,
            instance=self.object,
            changes={
                f: [
                    str(form.initial.get(f, "")),
                    str(form.cleaned_data.get(f, "")),
                ]
                for f in form.changed_data
            } or {},
            message="Action definition updated.",
            request=self.request,
        )

        if self.object.assessment_id:
            self.object.assessment.refresh_status()

        return response


# =============================================================================
# VERIFICATION QUEUE — APPROVE / REJECT
# =============================================================================
class VerificationListView(ErgonomicsAccessMixin, ListView):
    model = ErgonomicCorrectiveAction
    template_name = "ergonomics/verification_list.html"
    context_object_name = "actions"
    paginate_by = 25

    def get_queryset(self):
        ErgonomicCorrectiveAction.objects.refresh_overdue()

        qs = (
            ErgonomicCorrectiveAction.objects
            .select_related(
                "assessment",
                "assessment__plant",
                "assessment__department",
                "responsible_person",
                "department",
            )
            .filter(status="PENDING_VERIFICATION")
            .order_by("target_date")
        )

        user = self.request.user
        if user.is_superuser:
            return qs

        role_name = user.role.name if getattr(user, "role", None) else ""
        if role_name not in self.verify_roles:
            return qs.none()

        if hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            if plants is not None:
                qs = qs.filter(assessment__plant__in=plants)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = self.get_queryset()
        ctx["pending_count"] = base.count()
        ctx["overdue_count"] = base.filter(
            target_date__lt=timezone.now().date()
        ).count()
        return ctx


class VerificationDetailView(ErgonomicsAccessMixin, DetailView):
    model = ErgonomicCorrectiveAction
    template_name = "ergonomics/verification_detail.html"
    context_object_name = "action"

    def get_queryset(self):
        qs = ErgonomicCorrectiveAction.objects.select_related(
            "assessment",
            "assessment__plant",
            "assessment__department",
            "responsible_person",
            "department",
            "created_by",
        )

        user = self.request.user
        if user.is_superuser:
            return qs

        role_name = user.role.name if getattr(user, "role", None) else ""
        if role_name not in self.verify_roles:
            return qs.none()

        if hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            if plants is not None:
                qs = qs.filter(assessment__plant__in=plants)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["reject_form"] = CorrectiveActionRejectForm()
        ctx["can_verify"] = self.can_verify(self.request.user, self.object)
        return ctx


class ApproveActionView(ErgonomicsAccessMixin, View):
    def post(self, request, pk):
        action = get_object_or_404(
            ErgonomicCorrectiveAction,
            pk=pk,
            status="PENDING_VERIFICATION",
        )

        if not self.can_verify(request.user, action):
            messages.error(request, "You don't have permission to verify this action.")
            return redirect("ergonomics:verifications")

        old_status = action.status
        action.status = "CLOSED"
        action.verified_by = request.user
        action.verification_date = timezone.now().date()
        if not action.verification:
            action.verification = "Verified via the verification queue."
        action.save()

        log_ergonomic_action(
            user=request.user,
            action=ErgonomicAuditLog.ACTION_VERIFY,
            instance=action,
            changes={"status": [old_status, "CLOSED"]},
            message="Action approved and verified.",
            request=request,
        )

        if action.assessment_id:
            action.assessment.refresh_status()

        messages.success(
            request,
            f"Action {action.action_id} has been approved and marked as verified.",
        )
        return redirect("ergonomics:verifications")


class RejectActionView(ErgonomicsAccessMixin, View):
    def post(self, request, pk):
        action = get_object_or_404(
            ErgonomicCorrectiveAction,
            pk=pk,
            status="PENDING_VERIFICATION",
        )

        if not self.can_verify(request.user, action):
            messages.error(request, "You don't have permission to reject this action.")
            return redirect("ergonomics:verifications")

        form = CorrectiveActionRejectForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please provide a valid rejection reason.")
            return redirect("ergonomics:verification_detail", pk=pk)

        old_status = action.status
        action.status = "REJECTED"
        action.rejection_remark = form.cleaned_data["rejection_remark"]
        action.rejected_by = request.user
        action.rejected_at = timezone.now()
        action.save()

        log_ergonomic_action(
            user=request.user,
            action=ErgonomicAuditLog.ACTION_REJECT,
            instance=action,
            changes={"status": [old_status, "REJECTED"]},
            message=form.cleaned_data["rejection_remark"],
            request=request,
        )

        if action.assessment_id:
            action.assessment.refresh_status()

        messages.warning(
            request,
            f"Action {action.action_id} has been rejected. "
            f"The responsible person has been asked to revise and resubmit.",
        )
        return redirect("ergonomics:verifications")


# =============================================================================
# MY ACTIONS — RESPONSIBLE PERSON FLOW
# =============================================================================
class MyErgonomicActionsView(LoginRequiredMixin, ListView):
    model = ErgonomicCorrectiveAction
    template_name = "ergonomics/my_actions.html"
    context_object_name = "actions"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            ErgonomicCorrectiveAction.objects
            .select_related("assessment", "assessment__plant", "assessment__department", "department")
            .filter(responsible_person=self.request.user)
            .order_by("-created_at")
        )
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = [
            ("ASSIGNED", "Assigned"),
            ("IN_PROGRESS", "In Progress"),
            ("PENDING_VERIFICATION", "Pending Verification"),
            ("COMPLETED", "Completed"),
            ("CLOSED", "Closed"),
        ]
        base = ErgonomicCorrectiveAction.objects.filter(responsible_person=self.request.user)
        ctx["open_count"] = base.filter(status__in=["OPEN", "ASSIGNED", "IN_PROGRESS"]).count()
        ctx["overdue_count"] = base.filter(status="OVERDUE").count()
        ctx["completed_count"] = base.filter(status__in=["COMPLETED", "CLOSED"]).count()
        return ctx


class MyActionUpdateView(LoginRequiredMixin, UpdateView):
    model = ErgonomicCorrectiveAction
    form_class = MyActionUpdateForm
    template_name = "ergonomics/my_action_form.html"
    context_object_name = "action"

    READONLY_STATUSES = {"PENDING_VERIFICATION", "COMPLETED", "CLOSED"}

    def get_queryset(self):
        return ErgonomicCorrectiveAction.objects.filter(
            responsible_person=self.request.user
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["readonly"] = self.object.status in self.READONLY_STATUSES
        return ctx

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.object.status in self.READONLY_STATUSES:
            for field in form.fields.values():
                field.disabled = True
        return form

    def get_success_url(self):
        messages.success(self.request, "Action updated.")
        return reverse_lazy("ergonomics:my_actions")

    def form_valid(self, form):
        if self.object.status in self.READONLY_STATUSES:
            messages.info(
                self.request,
                "This action is already submitted and cannot be edited.",
            )
            return redirect("ergonomics:my_actions")

        old_status = self.object.status
        form.instance.status = "PENDING_VERIFICATION"
        response = super().form_valid(form)

        log_ergonomic_action(
            user=self.request.user,
            action=ErgonomicAuditLog.ACTION_STATUS_CHANGE,
            instance=self.object,
            changes={"status": [old_status, "PENDING_VERIFICATION"]},
            message="Evidence uploaded and submitted for verification.",
            request=self.request,
        )

        if self.object.assessment_id:
            self.object.assessment.refresh_status()

        return response


# =============================================================================
# REASSESSMENT + CONTROL
# =============================================================================
class ErgonomicReassessmentCreateView(RelatedCreateView):
    model = ErgonomicReassessment
    form_class = ErgonomicReassessmentForm
    template_name = "ergonomics/simple_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.assessment = None
        assessment_pk = self.kwargs.get("assessment_pk") or request.GET.get("assessment")
        if assessment_pk:
            self.assessment = get_object_or_404(
                self.base_queryset(), pk=assessment_pk
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if not kwargs.get("instance") and self.assessment:
            kwargs["instance"] = ErgonomicReassessment(assessment=self.assessment)
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.assessment and "corrective_action" in form.fields:
            form.fields["corrective_action"].queryset = (
                ErgonomicCorrectiveAction.objects
                .filter(assessment=self.assessment)
                .order_by("-created_at")
            )
        return form

    def get_initial(self):
        initial = super().get_initial()
        if self.assessment:
            initial.update(
                previous_score=self.assessment.score or 0,
                previous_risk=self.assessment.risk_level or "LOW",
                assessor=self.request.user,
            )
        return initial

    def form_valid(self, form):
        if self.assessment and not form.instance.assessment_id:
            form.instance.assessment = self.assessment

        if not form.instance.assessor:
            form.instance.assessor = self.request.user

        response = super().form_valid(form)

        log_ergonomic_action(
            user=self.request.user,
            action=ErgonomicAuditLog.ACTION_CREATE,
            instance=self.object.assessment,
            changes={
                "score": [
                    str(self.object.previous_score),
                    str(self.object.new_score),
                ],
                "risk_level": [
                    self.object.previous_risk or "",
                    self.object.new_risk or "",
                ],
            },
            message=(
                f"Reassessment recorded — "
                f"{self.object.get_control_effectiveness_display()}, "
                f"{self.object.risk_reduction_percent}% reduction."
            ),
            request=self.request,
        )

        messages.success(self.request, "Reassessment recorded.")
        return response

    def get_success_url(self):
        return reverse_lazy(
            "ergonomics:detail",
            kwargs={"pk": self.object.assessment_id},
        )


class ErgonomicControlCreateView(RelatedCreateView):
    model = ErgonomicControl
    form_class = ErgonomicControlForm
    template_name = "ergonomics/simple_form.html"

    def get_initial(self):
        initial = super().get_initial()
        assessment_pk = self.kwargs.get("assessment_pk")
        if assessment_pk:
            assessment = get_object_or_404(self.base_queryset(), pk=assessment_pk)
            initial["assessment"] = assessment
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)

        log_ergonomic_action(
            user=self.request.user,
            action=ErgonomicAuditLog.ACTION_CREATE,
            instance=self.object.assessment,
            message=f"Control added: {self.object.get_control_type_display()}.",
            request=self.request,
        )
        return response

    def get_success_url(self):
        messages.success(self.request, "Control recorded.")
        return reverse_lazy("ergonomics:detail", kwargs={"pk": self.object.assessment_id})


# =============================================================================
# GENERIC LIST / CREATE (MSD, Job Mapping, Schedule, Methods)
# =============================================================================
class GenericErgonomicsListView(ErgonomicsAccessMixin, ListView):
    template_name = "ergonomics/generic_list.html"
    paginate_by = 25
    context_object_name = "objects"


class GenericErgonomicsCreateView(RelatedCreateView):
    template_name = "ergonomics/simple_form.html"

    def form_valid(self, form):
        assessment_pk = self.kwargs.get("assessment_pk")
        if assessment_pk and hasattr(form.instance, "assessment_id"):
            assessment = get_object_or_404(self.base_queryset(), pk=assessment_pk)
            form.instance.assessment = assessment
        return super().form_valid(form)

    def get_success_url(self):
        assessment_id = getattr(self.object, "assessment_id", None)
        if assessment_id:
            return reverse_lazy("ergonomics:detail", kwargs={"pk": assessment_id})
        return reverse_lazy("ergonomics:dashboard")


# =============================================================================
# MSD / DISCOMFORT TRACKING
# =============================================================================
class MSDDiscomfortListView(GenericErgonomicsListView):
    model = MSDDiscomfort
    template_name = "ergonomics/msd_list.html"


class MSDDiscomfortCreateView(GenericErgonomicsCreateView):
    model = MSDDiscomfort
    form_class = MSDDiscomfortForm
    template_name = "ergonomics/msd_form.html"
    success_url = reverse_lazy("ergonomics:msd_list")


# =============================================================================
# EMPLOYEE / JOB MAPPING
# =============================================================================
class ErgonomicJobMappingListView(GenericErgonomicsListView):
    model = ErgonomicJobMapping
    template_name = "ergonomics/job_mapping_list.html"


class ErgonomicJobMappingCreateView(GenericErgonomicsCreateView):
    model = ErgonomicJobMapping
    form_class = ErgonomicJobMappingForm
    template_name = "ergonomics/job_mapping_form.html"
    success_url = reverse_lazy("ergonomics:job_mapping")


class ErgonomicJobMappingUpdateView(ErgonomicsAccessMixin, UpdateView):
    model = ErgonomicJobMapping
    form_class = ErgonomicJobMappingForm
    template_name = "ergonomics/job_mapping_form.html"
    context_object_name = "object"

    def get_success_url(self):
        messages.success(self.request, "Job mapping updated.")
        return reverse_lazy("ergonomics:job_mapping")


# =============================================================================
# ASSESSMENT SCHEDULE
# =============================================================================
class ErgonomicAssessmentScheduleListView(GenericErgonomicsListView):
    model = ErgonomicAssessmentSchedule
    template_name = "ergonomics/schedule_list.html"


class ErgonomicAssessmentScheduleCreateView(GenericErgonomicsCreateView):
    model = ErgonomicAssessmentSchedule
    form_class = ErgonomicAssessmentScheduleForm
    success_url = reverse_lazy("ergonomics:schedule")


# =============================================================================
# ASSESSMENT METHOD MASTER
# =============================================================================
class ErgonomicAssessmentMethodListView(GenericErgonomicsListView):
    model = ErgonomicAssessmentMethod
    template_name = "ergonomics/method_list.html"


class ErgonomicAssessmentMethodCreateView(GenericErgonomicsCreateView):
    model = ErgonomicAssessmentMethod
    form_class = ErgonomicAssessmentMethodForm
    template_name = "ergonomics/method_form.html"
    success_url = reverse_lazy("ergonomics:method_list")


# =============================================================================
# REPORTS / ANALYTICS
# =============================================================================
class ErgonomicsReportExportView(ErgonomicsAccessMixin, View):
    def get(self, request):
        return workbook_response(filter_assessments(request))


class ErgonomicsAnalyticsView(ErgonomicsAccessMixin, TemplateView):
    template_name = "ergonomics/analytics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assessments = filter_assessments(self.request)

        context.update(
            plants=Plant.objects.filter(is_active=True),
            departments=Department.objects.filter(is_active=True),
            methods=ErgonomicAssessmentMethod.objects.filter(is_active=True),
        )

        context.update(
            by_risk=assessments.values("risk_level").annotate(total=Count("id")),
            by_department=assessments.values("department__name").annotate(total=Count("id")).order_by("-total"),
            by_method=assessments.values("assessment_method__name").annotate(total=Count("id")).order_by("-total"),
            by_body_part=MSDDiscomfort.objects.values("body_part").annotate(total=Count("id")).order_by("-total"),
        )

        context["by_site"] = (
            assessments.values("plant__name")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        context["by_job"] = (
            assessments.values("job_role")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )
        context["by_task"] = (
            assessments.values("task")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )
        context["by_shift"] = (
            assessments.exclude(shift="")
            .values("shift")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        context["by_month"] = (
            assessments.annotate(month=TruncMonth("assessment_date"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )
        context["high_risk_trend"] = (
            assessments.filter(risk_level__in=["HIGH", "VERY_HIGH"])
            .annotate(month=TruncMonth("assessment_date"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )
        context["msd_trend"] = (
            MSDDiscomfort.objects.annotate(month=TruncMonth("date_reported"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )
        context["action_trend"] = (
            ErgonomicCorrectiveAction.objects.filter(assessment__in=assessments)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )
        context["reduction_trend"] = (
            ErgonomicReassessment.objects.filter(assessment__in=assessments)
            .annotate(month=TruncMonth("reassessment_date"))
            .values("month")
            .annotate(avg_reduction=Avg("risk_reduction_percent"))
            .order_by("month")
        )

        return context


class DepartmentReportExportView(ErgonomicsAccessMixin, View):
    def get(self, request):
        assessments = filter_assessments(request)

        dept_id = request.GET.get("department")
        if dept_id:
            dept = get_object_or_404(Department, pk=dept_id, is_active=True)
            departments = [dept]
        else:
            dept_ids = assessments.values_list("department_id", flat=True).distinct()
            departments = list(
                Department.objects.filter(id__in=dept_ids, is_active=True).order_by("name")
            )
            if not departments:
                messages.warning(request, "No departments have any assessments yet.")
                return redirect("ergonomics:dashboard")

        return department_report_response(assessments, departments)


class ManagementReportExportView(ErgonomicsAccessMixin, View):
    def get(self, request):
        assessments = filter_assessments(request)
        return management_report_response(assessments)


class SiteBenchmarksAPIView(ErgonomicsAccessMixin, View):
    def get(self, request):
        from django.utils import timezone
        from .services.benchmarking_service import ergonomics_site_benchmarks

        user = request.user
        try:
            if user.is_superuser or not hasattr(user, "get_all_plants"):
                plants = Plant.objects.filter(is_active=True)
            else:
                plants = user.get_all_plants()
                if plants is None:
                    plants = Plant.objects.none()
                elif not hasattr(plants, "filter"):
                    plant_ids = [p.pk for p in plants if getattr(p, "pk", None)]
                    plants = (
                        Plant.objects.filter(pk__in=plant_ids, is_active=True)
                        if plant_ids
                        else Plant.objects.none()
                    )
        except Exception as exc:
            return JsonResponse(
                {
                    "generated_at": timezone.now().isoformat(),
                    "error": f"Could not resolve accessible plants: {exc}",
                    "sites": [],
                },
                status=500,
            )

        try:
            sites = ergonomics_site_benchmarks(plants=plants)
        except Exception as exc:
            return JsonResponse(
                {
                    "generated_at": timezone.now().isoformat(),
                    "error": f"Failed to compute site benchmarks: {exc}",
                    "sites": [],
                },
                status=500,
            )

        return JsonResponse({
            "generated_at": timezone.now().isoformat(),
            "count": len(sites),
            "sites": sites,
        })


class SiteBenchmarksView(ErgonomicsAccessMixin, TemplateView):
    """
    HTML rendering of the site benchmarking data.

    Reuses the same service as the JSON API, but renders the results as a
    styled table so they can be reviewed in the browser.
    """
    template_name = "ergonomics/benchmarks.html"

    def get_context_data(self, **kwargs):
        from .services.benchmarking_service import ergonomics_site_benchmarks

        context = super().get_context_data(**kwargs)
        user = self.request.user

        try:
            if user.is_superuser or not hasattr(user, "get_all_plants"):
                plants = Plant.objects.filter(is_active=True)
            else:
                plants = user.get_all_plants()
                if plants is None:
                    plants = Plant.objects.none()
                elif not hasattr(plants, "filter"):
                    plant_ids = [p.pk for p in plants if getattr(p, "pk", None)]
                    plants = (
                        Plant.objects.filter(pk__in=plant_ids, is_active=True)
                        if plant_ids
                        else Plant.objects.none()
                    )
        except Exception:
            plants = Plant.objects.none()

        try:
            rows = ergonomics_site_benchmarks(plants=plants)
        except Exception as exc:
            messages.error(self.request, f"Could not compute site benchmarks: {exc}")
            rows = []

        rows = sorted(
            rows,
            key=lambda r: (
                r.get("average_risk_score", 0) or 0,
                r.get("high_risk_tasks", 0) or 0,
            ),
            reverse=True,
        )

        total_assessments = sum(r.get("total_assessments", 0) or 0 for r in rows)
        total_high_risk = sum(r.get("high_risk_tasks", 0) or 0 for r in rows)
        total_msd = sum(r.get("msd_cases", 0) or 0 for r in rows)
        avg_scores = [r.get("average_risk_score", 0) or 0 for r in rows if r.get("total_assessments")]
        avg_reduction = 0
        if rows:
            reds = [r.get("action_closure", 0) or 0 for r in rows]
            avg_reduction = round(sum(reds) / len(reds), 2) if reds else 0

        context.update({
            "rows": rows,
            "sites_count": len(rows),
            "total_assessments": total_assessments,
            "total_high_risk": total_high_risk,
            "total_msd": total_msd,
            "overall_avg_score": round(sum(avg_scores) / len(avg_scores), 2) if avg_scores else 0,
            "overall_action_closure": avg_reduction,
        })
        return context