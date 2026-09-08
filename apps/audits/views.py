import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from .forms import *
from .models import *
from apps.organizations.models import Plant
from apps.alert_engine.services import NotificationService


def _is_auditor_or_admin(user):
    role_name = (getattr(user, "role_name", "") or "").upper()
    return user.is_superuser or role_name in {"AUDITOR", "ADMIN"} or user.has_permission("ACCESS_AUDIT_MODULE")


def _is_manager_or_admin(user):
    role_name = (getattr(user, "role_name", "") or "").upper()
    return user.is_superuser or role_name in {"ADMIN", "EHS MANAGER", "EHS_MANAGER"} or user.has_permission("APPROVE_FINDING")


def _build_execution_initial(schedule):
    responses_by_question = {
        response.question_id: response
        for response in schedule.responses.select_related("question")
    }
    initial = []
    for question in schedule.template.questions.all():
        response = responses_by_question.get(question.id)
        initial.append(
            {
                "response_id": response.id if response else "",
                "question_id": question.id,
                "previous_status": response.status if response else "",
                "status": response.status if response else "",
                "comment": response.comment if response else "",
                "observation_detail": (
                    schedule.findings.filter(origin_question=question, is_archived=False)
                    .values_list("observation_detail", flat=True)
                    .first()
                    or ""
                ),
                "risk_score": (
                    schedule.findings.filter(origin_question=question, is_archived=False)
                    .values_list("risk_score", flat=True)
                    .first()
                    or AuditFinding.RISK_MAJOR
                ),
            }
        )
    return initial


class AuditorOrAdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not _is_auditor_or_admin(request.user):
            messages.error(request, "You don't have permission can start an audit.")
            return redirect("audits:schedule_list")
        return super().dispatch(request, *args, **kwargs)


class ManagerOrAdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not _is_manager_or_admin(request.user):
            messages.error(request, "You don't have permission to approve the finding")
            return redirect("audits:finding_dashboard")
        return super().dispatch(request, *args, **kwargs)


class AuditCategoryListView(LoginRequiredMixin, ListView):
    model = AuditCategory
    template_name = "audits/category_list.html"
    context_object_name = "categories"
    paginate_by = 10

    def get_queryset(self):
        queryset = AuditCategory.objects.annotate(template_count=Count("templates")).order_by("category_name")
        search = self.request.GET.get("search", "").strip()
        status = self.request.GET.get("status", "").strip()

        if search:
            queryset = queryset.filter(
                Q(category_name__icontains=search)
                | Q(category_code__icontains=search)
                | Q(description__icontains=search)
            )
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search"] = self.request.GET.get("search", "").strip()
        context["selected_status"] = self.request.GET.get("status", "").strip()
        return context


class AuditCategoryCreateView(LoginRequiredMixin, CreateView):
    model = AuditCategory
    form_class = AuditCategoryForm
    template_name = "audits/category_form.html"
    success_url = reverse_lazy("audits:category_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Audit category created successfully.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Audit Category"
        return context


class AuditCategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = AuditCategory
    form_class = AuditCategoryForm
    template_name = "audits/category_form.html"
    success_url = reverse_lazy("audits:category_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Audit category updated successfully.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Audit Category"
        return context


class AuditCategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = AuditCategory
    template_name = "audits/category_confirm_delete.html"
    success_url = reverse_lazy("audits:category_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Audit category deleted successfully.")
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["template_count"] = self.object.templates.count()
        return context


class AuditTemplateListView(LoginRequiredMixin, ListView):
    model = AuditTemplate
    template_name = "audits/template_list.html"
    context_object_name = "templates"
    paginate_by = 10

    def get_queryset(self):
        queryset = (
            AuditTemplate.objects.select_related("category")
            .annotate(question_count=Count("questions"))
            .order_by("title", "version")
        )
        search = self.request.GET.get("search", "").strip()
        category_id = self.request.GET.get("category", "").strip()

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(version__icontains=search)
                | Q(standard_reference__icontains=search)
            )
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = AuditCategory.objects.filter(is_active=True).order_by("category_name")
        context["search"] = self.request.GET.get("search", "").strip()
        context["selected_category"] = self.request.GET.get("category", "").strip()
        return context


class AuditTemplateCreateView(LoginRequiredMixin, CreateView):
    model = AuditTemplate
    form_class = AuditTemplateForm
    template_name = "audits/template_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Audit template created successfully.")
        return response

    def get_success_url(self):
        return reverse("audits:template_detail", kwargs={"pk": self.object.pk})


class AuditTemplateDetailView(LoginRequiredMixin, DetailView):
    model = AuditTemplate
    template_name = "audits/template_detail.html"
    context_object_name = "template"

    def get_queryset(self):
        return AuditTemplate.objects.select_related("category").prefetch_related("questions", "schedules")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        questions = self.object.questions.all().order_by("sequence", "id")
        context["questions"] = questions
        context["question_count"] = questions.count()
        context["schedule_count"] = self.object.schedules.count()
        return context


class AuditTemplateAddQuestionView(LoginRequiredMixin, CreateView):
    model = AuditQuestion
    form_class = AuditQuestionForm
    template_name = "audits/template_add_question.html"

    def dispatch(self, request, *args, **kwargs):
        self.template_obj = get_object_or_404(AuditTemplate, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        next_sequence = (
            self.template_obj.questions.order_by("-sequence").values_list("sequence", flat=True).first() or 0
        ) + 1
        initial["sequence"] = next_sequence
        return initial

    def form_valid(self, form):
        form.instance.template = self.template_obj
        response = super().form_valid(form)
        messages.success(self.request, "Audit question added to the template.")
        return response

    def get_success_url(self):
        return reverse("audits:template_detail", kwargs={"pk": self.template_obj.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["template"] = self.template_obj
        return context


class AuditTemplateAddQuestionsView(LoginRequiredMixin, TemplateView):
    template_name = "audits/template_add_questions.html"

    def dispatch(self, request, *args, **kwargs):
        self.template_obj = get_object_or_404(AuditTemplate, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def _get_next_sequence(self):
        return (self.template_obj.questions.order_by("-sequence").values_list("sequence", flat=True).first() or 0) + 1

    def get_formset(self):
        if self.request.method == "POST":
            return AuditQuestionFormSet(self.request.POST, queryset=AuditQuestion.objects.none())
        formset = AuditQuestionFormSet(queryset=AuditQuestion.objects.none())
        next_sequence = self._get_next_sequence()
        for index, form in enumerate(formset.forms):
            form.initial["sequence"] = next_sequence + index
        return formset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["template"] = self.template_obj
        context["formset"] = kwargs.get("formset", self.get_formset())
        return context

    def post(self, request, *args, **kwargs):
        formset = self.get_formset()
        if formset.is_valid():
            saved_count = 0
            next_sequence = self._get_next_sequence()
            for form in formset:
                if not form.cleaned_data or not form.cleaned_data.get("question_text"):
                    continue
                question = form.save(commit=False)
                question.template = self.template_obj
                if not question.sequence:
                    question.sequence = next_sequence + saved_count
                question.save()
                saved_count += 1

            if saved_count:
                messages.success(request, f"{saved_count} audit questions added to the template.")
                return redirect("audits:template_detail", pk=self.template_obj.pk)
            messages.error(request, "Add at least one question before saving.")

        return self.render_to_response(self.get_context_data(formset=formset))


class AuditTemplateRemoveQuestionView(LoginRequiredMixin, TemplateView):
    template_name = "audits/template_remove_question.html"

    def dispatch(self, request, *args, **kwargs):
        self.template_obj = get_object_or_404(AuditTemplate, pk=kwargs["template_pk"])
        self.question = get_object_or_404(AuditQuestion, pk=kwargs["question_pk"], template=self.template_obj)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["template"] = self.template_obj
        context["question"] = self.question
        return context

    def post(self, request, *args, **kwargs):
        self.question.delete()
        messages.success(request, "Audit question removed from the template.")
        return redirect("audits:template_detail", pk=self.template_obj.pk)


class AuditScheduleListView(LoginRequiredMixin, ListView):
    model = AuditSchedule
    template_name = "audits/schedule_list.html"
    context_object_name = "schedules"
    paginate_by = 10

    def get_base_queryset(self):
        return (
            AuditSchedule.objects.select_related(
                "template", "template__category", "auditor", "location", "location__zone", "location__zone__plant"
            )
            .prefetch_related("plants", "zones", "locations", "sublocations")
            .annotate(
                open_findings=Count(
                    "findings",
                    filter=Q(
                        findings__status__in=[
                            AuditFinding.STATUS_DRAFT,
                            AuditFinding.STATUS_OPEN,
                            AuditFinding.STATUS_IN_PROGRESS,
                        ],
                        findings__is_archived=False,
                    ),
                )
            )
            .order_by("-scheduled_date", "-created_at")
        )

    def get_available_status_choices(self):
        return AuditSchedule.STATUS_CHOICES

    def get_default_status(self):
        return ""

    def get_selected_status(self):
        available_statuses = {value for value, _ in self.get_available_status_choices()}
        requested_status = self.request.GET.get("status", "").strip()
        if requested_status in available_statuses:
            return requested_status
        return self.get_default_status()

    def show_auditor_filter(self):
        return True

    def get_page_config(self):
        return {
            "page_title": "Audit Schedules",
            "breadcrumb_title": "Audit Schedules",
            "hero_title": "Audit Management",
            "hero_description": "Monitor scheduled audits, assigned priorities, and open non-conformances from one place.",
            "hero_button_label": "Schedule Audit",
            "hero_button_url": reverse("audits:schedule_create"),
            "card_title": "Scheduled Audits",
            "reset_url": reverse("audits:schedule_list"),
            "empty_message": "No audits scheduled yet.",
            "search_placeholder": "Search code, template, auditor",
        }

    def get_queryset(self):
        queryset = self.get_base_queryset()
        search = self.request.GET.get("search", "").strip()
        status = self.get_selected_status()
        priority = self.request.GET.get("priority", "").strip()
        category_id = self.request.GET.get("category", "").strip()
        auditor_id = self.request.GET.get("auditor", "").strip()

        if search:
            queryset = queryset.filter(
                Q(schedule_code__icontains=search)
                | Q(template__title__icontains=search)
                | Q(auditor__first_name__icontains=search)
                | Q(auditor__last_name__icontains=search)
                | Q(location__name__icontains=search)
            )
        if status:
            queryset = queryset.filter(status=status)
        if priority:
            queryset = queryset.filter(priority=priority)
        if category_id:
            queryset = queryset.filter(template__category_id=category_id)
        if auditor_id and self.show_auditor_filter():
            queryset = queryset.filter(auditor_id=auditor_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        schedules = self.get_queryset()
        context["total_audits"] = schedules.count()
        context["in_progress_count"] = schedules.filter(status=AuditSchedule.STATUS_IN_PROGRESS).count()
        context["total_open_findings"] = sum(schedule.open_findings for schedule in schedules)
        context["search"] = self.request.GET.get("search", "").strip()
        context["selected_status"] = self.get_selected_status()
        context["selected_priority"] = self.request.GET.get("priority", "").strip()
        context["selected_category"] = self.request.GET.get("category", "").strip()
        context["selected_auditor"] = self.request.GET.get("auditor", "").strip()
        context["categories"] = AuditCategory.objects.filter(is_active=True).order_by("category_name")
        context["auditors"] = User.objects.filter(is_active=True).order_by("first_name", "last_name", "username")
        context["status_choices"] = self.get_available_status_choices()
        context["priority_choices"] = AuditSchedule.PRIORITY_CHOICES
        context["show_auditor_filter"] = self.show_auditor_filter()
        context.update(self.get_page_config())
        return context


class MyAuditListView(AuditScheduleListView):
    def get_base_queryset(self):
        return super().get_base_queryset().filter(auditor=self.request.user)

    def get_available_status_choices(self):
        return [
            (AuditSchedule.STATUS_SCHEDULED, "Scheduled"),
            (AuditSchedule.STATUS_COMPLETED, "Completed"),
            (AuditSchedule.STATUS_CLOSED, "Closed"),
        ]

    def get_default_status(self):
        return AuditSchedule.STATUS_SCHEDULED

    def show_auditor_filter(self):
        return False

    def get_page_config(self):
        return {
            "page_title": "My Audits",
            "breadcrumb_title": "My Audits",
            "hero_title": "My Audits",
            "hero_description": "Track the audits assigned to you, starting with your scheduled work and completed history.",
            "hero_button_label": "",
            "hero_button_url": "",
            "card_title": "Assigned Audits",
            "reset_url": reverse("audits:my_audits"),
            "empty_message": "No audits are assigned to you for the selected status.",
            "search_placeholder": "Search code, template, location",
        }


class AuditScheduleCreateView(LoginRequiredMixin, CreateView):
    model = AuditSchedule
    form_class = AuditScheduleForm
    template_name = "audits/schedule_form.html"

    def get_initial(self):
        initial = super().get_initial()
        template_id = self.request.GET.get("template")
        if template_id:
            initial["template"] = template_id
        return initial

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.status = AuditSchedule.STATUS_SCHEDULED
        self.object.save()
        form.save_related_locations(self.object)
        messages.success(self.request, f"Audit schedule {self.object.schedule_code} created successfully.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("audits:schedule_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Schedule Audit"
        context["action"] = "Create"
        return context


class AuditScheduleDetailView(LoginRequiredMixin, DetailView):
    model = AuditSchedule
    template_name = "audits/schedule_detail.html"
    context_object_name = "schedule"

    def get_queryset(self):
        return (
            AuditSchedule.objects.select_related(
                "template", "template__category", "auditor", "location", "location__zone", "location__zone__plant"
            )
            .prefetch_related(
                "plants",
                "zones",
                "locations",
                "sublocations",
                Prefetch("responses", queryset=AuditResponse.objects.select_related("question")),
                Prefetch("findings", queryset=AuditFinding.objects.filter(is_archived=False).prefetch_related("capas")),
            )
        )


class AuditExecuteView(AuditorOrAdminRequiredMixin, View):
    template_name = "audits/audit_execute.html"

    def get_schedule(self):
        return get_object_or_404(
            AuditSchedule.objects.select_related(
                "template", "template__category", "auditor", "location", "location__zone", "location__zone__plant"
            ).prefetch_related("template__questions", "findings", "plants", "zones", "locations", "sublocations"),
            pk=self.kwargs["pk"],
        )

    def dispatch(self, request, *args, **kwargs):
        self.schedule = self.get_schedule()
        if request.user != self.schedule.auditor and not _is_auditor_or_admin(request.user):
            messages.error(request, "Only the assigned Auditor or an Admin can start this audit.")
            return redirect("audits:schedule_detail", pk=self.schedule.pk)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if self.schedule.status in [AuditSchedule.STATUS_DRAFT, AuditSchedule.STATUS_SCHEDULED]:
            self.schedule.status = AuditSchedule.STATUS_IN_PROGRESS
            self.schedule.started_at = self.schedule.started_at or timezone.now()
            self.schedule.save(update_fields=["status", "started_at", "updated_at"])

        questions = list(self.schedule.template.questions.all())
        formset = AuditExecutionFormSet(initial=_build_execution_initial(self.schedule))
        return self.render_response(formset, questions)

    def post(self, request, *args, **kwargs):
        questions = list(self.schedule.template.questions.all())
        initial = _build_execution_initial(self.schedule)
        formset = AuditExecutionFormSet(request.POST, request.FILES, initial=initial)

        if formset.is_valid():
            archive_confirmation_missing = False
            for index, form in enumerate(formset.forms):
                question = questions[index]
                data = form.cleaned_data
                previous_status = data.get("previous_status")
                if previous_status == AuditResponse.STATUS_FAIL and data["status"] != AuditResponse.STATUS_FAIL:
                    existing_finding = AuditFinding.objects.filter(
                        parent_audit=self.schedule,
                        origin_question=question,
                        is_archived=False,
                    ).first()
                    if existing_finding and not data.get("archive_finding"):
                        archive_confirmation_missing = True
                        form.add_error(
                            "archive_finding",
                            "Tick this box to archive the linked finding before changing Fail to Pass/N/A.",
                        )

            if not archive_confirmation_missing:
                try:
                    with transaction.atomic():
                        for index, form in enumerate(formset.forms):
                            question = questions[index]
                            data = form.cleaned_data
                            response, _ = AuditResponse.objects.get_or_create(
                                schedule=self.schedule,
                                question=question,
                                defaults={"status": data["status"]},
                            )

                            previous_status = data.get("previous_status") or response.status
                            response.status = data["status"]
                            response.comment = data.get("comment", "")
                            if data.get("photo_evidence"):
                                response.photo_evidence = data["photo_evidence"]
                            response.save()

                            existing_finding = AuditFinding.objects.filter(
                                parent_audit=self.schedule,
                                origin_question=question,
                                is_archived=False,
                            ).first()

                            if previous_status == AuditResponse.STATUS_FAIL and data["status"] != AuditResponse.STATUS_FAIL:
                                if existing_finding and data.get("archive_finding"):
                                    existing_finding.archive(
                                        "Response updated from Fail to a compliant state during audit execution."
                                    )

                            if data["status"] == AuditResponse.STATUS_FAIL:
                                finding = AuditFinding.objects.get(parent_audit=self.schedule, origin_question=question)
                                finding.observation_detail = (
                                    data.get("observation_detail") or response.comment or question.question_text
                                )
                                finding.risk_score = data.get("risk_score") or finding.risk_score
                                if finding.manager_review_status == AuditFinding.REVIEW_REJECTED:
                                    finding.manager_review_status = AuditFinding.REVIEW_PENDING
                                    finding.status = AuditFinding.STATUS_DRAFT
                                finding.save()

                        action = request.POST.get("action")
                        self.schedule.status = (
                            AuditSchedule.STATUS_COMPLETED if action == "complete" else AuditSchedule.STATUS_IN_PROGRESS
                        )
                        self.schedule.completed_at = timezone.now() if action == "complete" else None
                        self.schedule.save()
                except Exception as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(
                        request,
                        "Audit saved successfully." if request.POST.get("action") != "complete" else "Audit completed successfully.",
                    )
                    return redirect("audits:schedule_detail", pk=self.schedule.pk)

        return self.render_response(formset, questions)

    def render_response(self, formset, questions):
        from django.shortcuts import render

        return render(
            self.request,
            self.template_name,
            {
                "schedule": self.schedule,
                "formset": formset,
                "question_forms": zip(questions, formset.forms),
            },
        )


class AuditFindingDashboardView(LoginRequiredMixin, ListView):
    model = AuditFinding
    template_name = "audits/finding_dashboard.html"
    context_object_name = "findings"
    paginate_by = 10

    def get_queryset(self):
        queryset = (
            AuditFinding.objects.filter(
                is_archived=False,
                status__in=[AuditFinding.STATUS_OPEN, AuditFinding.STATUS_IN_PROGRESS],
            )
            .select_related("parent_audit", "origin_question", "parent_audit__location", "parent_audit__auditor")
            .prefetch_related("capas")
            .order_by("-created_at")
        )
        search = self.request.GET.get("search", "").strip()
        status = self.request.GET.get("status", "").strip()
        risk = self.request.GET.get("risk", "").strip()
        priority = self.request.GET.get("priority", "").strip()

        if search:
            queryset = queryset.filter(
                Q(finding_id__icontains=search)
                | Q(parent_audit__schedule_code__icontains=search)
                | Q(origin_question__question_text__icontains=search)
                | Q(observation_detail__icontains=search)
            )
        if status:
            queryset = queryset.filter(status=status)
        if risk:
            queryset = queryset.filter(risk_score=risk)
        if priority:
            queryset = queryset.filter(parent_audit__priority=priority)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search"] = self.request.GET.get("search", "").strip()
        context["selected_status"] = self.request.GET.get("status", "").strip()
        context["selected_risk"] = self.request.GET.get("risk", "").strip()
        context["selected_priority"] = self.request.GET.get("priority", "").strip()
        context["status_choices"] = [
            (AuditFinding.STATUS_OPEN, "Open"),
            (AuditFinding.STATUS_IN_PROGRESS, "In-Progress"),
        ]
        context["risk_choices"] = AuditFinding.RISK_CHOICES
        context["priority_choices"] = AuditSchedule.PRIORITY_CHOICES
        return context


class AuditDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "audits/dashboard.html"

    def _parse_dates(self):
        today = timezone.now().date()
        date_range = self.request.GET.get("date_range", "90")
        start_date_str = self.request.GET.get("start_date", "").strip()
        end_date_str = self.request.GET.get("end_date", "").strip()

        if date_range == "custom" and start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                start_date = today - timedelta(days=90)
                end_date = today
        else:
            days = int(date_range) if date_range.isdigit() else 90
            start_date = today - timedelta(days=days)
            end_date = today

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        return date_range, start_date, end_date

    @staticmethod
    def _pct_change(current, previous):
        if previous == 0:
            return 100 if current else 0
        return round(((current - previous) / previous) * 100, 1)

    @staticmethod
    def _trend_class(delta):
        return "trend-up" if delta >= 0 else "trend-down"

    def _filtered_schedule_queryset(self, start_date, end_date, plant_id, category_id):
        queryset = (
            AuditSchedule.objects.select_related("template", "template__category", "auditor", "location", "location__zone", "location__zone__plant")
            .prefetch_related("plants", "zones", "locations", "sublocations")
            .filter(scheduled_date__range=[start_date, end_date])
            .distinct()
        )
        if plant_id:
            queryset = queryset.filter(Q(plants__id=plant_id) | Q(location__zone__plant__id=plant_id)).distinct()
        if category_id:
            queryset = queryset.filter(template__category_id=category_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date_range, start_date, end_date = self._parse_dates()
        plant_id = self.request.GET.get("plant", "").strip()
        category_id = self.request.GET.get("category", "").strip()

        schedules = self._filtered_schedule_queryset(start_date, end_date, plant_id, category_id)
        responses = AuditResponse.objects.filter(schedule__in=schedules).exclude(status=AuditResponse.STATUS_NA)
        findings = AuditFinding.objects.filter(parent_audit__in=schedules, is_archived=False)
        capas = CAPA.objects.filter(finding__parent_audit__in=schedules)

        period_days = max((end_date - start_date).days, 1)
        previous_end = start_date - timedelta(days=1)
        previous_start = previous_end - timedelta(days=period_days)
        previous_schedules = self._filtered_schedule_queryset(previous_start, previous_end, plant_id, category_id)
        previous_findings = AuditFinding.objects.filter(parent_audit__in=previous_schedules, is_archived=False)

        total_audits = schedules.count()
        completed_audits = schedules.filter(status__in=[AuditSchedule.STATUS_COMPLETED, AuditSchedule.STATUS_CLOSED]).count()
        total_findings = findings.count()
        critical_findings = findings.filter(risk_score=AuditFinding.RISK_CRITICAL).count()

        pass_count = responses.filter(status=AuditResponse.STATUS_PASS).count()
        fail_count = responses.filter(status=AuditResponse.STATUS_FAIL).count()
        total_scored = pass_count + fail_count
        compliance_score = round((pass_count / total_scored) * 100, 1) if total_scored else 0

        metrics = [
            {
                "label": "Total Audits",
                "value": total_audits,
                "delta": self._pct_change(total_audits, previous_schedules.count()),
                "class": self._trend_class(self._pct_change(total_audits, previous_schedules.count())),
            },
            {
                "label": "Completed Audits",
                "value": completed_audits,
                "delta": self._pct_change(
                    completed_audits,
                    previous_schedules.filter(status__in=[AuditSchedule.STATUS_COMPLETED, AuditSchedule.STATUS_CLOSED]).count(),
                ),
                "class": self._trend_class(
                    self._pct_change(
                        completed_audits,
                        previous_schedules.filter(status__in=[AuditSchedule.STATUS_COMPLETED, AuditSchedule.STATUS_CLOSED]).count(),
                    )
                ),
            },
            {
                "label": "Total Findings",
                "value": total_findings,
                "delta": self._pct_change(total_findings, previous_findings.count()),
                "class": self._trend_class(self._pct_change(total_findings, previous_findings.count())),
            },
            {
                "label": "Critical Findings",
                "value": critical_findings,
                "delta": self._pct_change(
                    critical_findings,
                    previous_findings.filter(risk_score=AuditFinding.RISK_CRITICAL).count(),
                ),
                "class": self._trend_class(
                    self._pct_change(
                        critical_findings,
                        previous_findings.filter(risk_score=AuditFinding.RISK_CRITICAL).count(),
                    )
                ),
            },
        ]

        month_labels = []
        scheduled_series = []
        completed_series = []
        month_anchor = end_date.replace(day=1)
        for offset in range(5, -1, -1):
            month_start = (month_anchor.replace(day=1) - timedelta(days=offset * 30)).replace(day=1)
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1, day=1)
            month_labels.append(month_start.strftime("%b %Y"))
            scheduled_series.append(schedules.filter(scheduled_date__gte=month_start, scheduled_date__lt=next_month).count())
            completed_series.append(
                schedules.filter(
                    completed_at__date__gte=month_start,
                    completed_at__date__lt=next_month,
                ).count()
            )

        severity_labels = [label for _, label in AuditFinding.RISK_CHOICES]
        severity_data = [findings.filter(risk_score=value).count() for value, _ in AuditFinding.RISK_CHOICES]

        category_labels = []
        category_data = []
        for category in AuditCategory.objects.filter(templates__schedules__in=schedules).distinct():
            category_labels.append(category.category_name)
            category_data.append(findings.filter(parent_audit__template__category=category).count())

        action_labels = [label for _, label in CAPA.VERIFICATION_CHOICES]
        action_data = [capas.filter(verification_status=value).count() for value, _ in CAPA.VERIFICATION_CHOICES]

        plant_rows = []
        plants = Plant.objects.filter(is_active=True)
        if plant_id:
            plants = plants.filter(pk=plant_id)
        for plant in plants:
            plant_schedules = schedules.filter(Q(plants=plant) | Q(location__zone__plant=plant)).distinct()
            if not plant_schedules.exists():
                continue
            plant_findings = findings.filter(parent_audit__in=plant_schedules)
            plant_responses = AuditResponse.objects.filter(schedule__in=plant_schedules).exclude(status=AuditResponse.STATUS_NA)
            plant_pass = plant_responses.filter(status=AuditResponse.STATUS_PASS).count()
            plant_fail = plant_responses.filter(status=AuditResponse.STATUS_FAIL).count()
            plant_total = plant_pass + plant_fail
            plant_compliance = round((plant_pass / plant_total) * 100, 1) if plant_total else 0
            resolved_capas = capas.filter(
                finding__parent_audit__in=plant_schedules,
                verification_status__in=[CAPA.STATUS_FIXED, CAPA.STATUS_VERIFIED],
            )
            resolution_days = [
                max((capa.updated_at.date() - capa.created_at.date()).days, 0)
                for capa in resolved_capas
            ]
            avg_resolution = round(sum(resolution_days) / len(resolution_days), 1) if resolution_days else 0
            if plant_compliance >= 90:
                performance = ("Excellent", "status-open")
            elif plant_compliance >= 75:
                performance = ("Good", "priority-medium")
            else:
                performance = ("Needs Improvement", "priority-critical")
            plant_rows.append(
                {
                    "name": plant.name,
                    "total_audits": plant_schedules.count(),
                    "completed": plant_schedules.filter(status__in=[AuditSchedule.STATUS_COMPLETED, AuditSchedule.STATUS_CLOSED]).count(),
                    "compliance_rate": plant_compliance,
                    "critical_findings": plant_findings.filter(risk_score=AuditFinding.RISK_CRITICAL).count(),
                    "avg_resolution": avg_resolution,
                    "performance_label": performance[0],
                    "performance_class": performance[1],
                }
            )

        plant_rows.sort(key=lambda row: row["compliance_rate"], reverse=True)

        context.update(
            {
                "metrics": metrics,
                "compliance_score": compliance_score,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "plant_rows": plant_rows,
                "plants": Plant.objects.filter(is_active=True).order_by("name"),
                "categories": AuditCategory.objects.filter(is_active=True).order_by("category_name"),
                "selected_date_range": date_range,
                "selected_plant": plant_id,
                "selected_category": category_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "trend_labels": json.dumps(month_labels),
                "scheduled_series": json.dumps(scheduled_series),
                "completed_series": json.dumps(completed_series),
                "severity_labels": json.dumps(severity_labels),
                "severity_data": json.dumps(severity_data),
                "category_labels": json.dumps(category_labels),
                "category_data": json.dumps(category_data),
                "action_labels": json.dumps(action_labels),
                "action_data": json.dumps(action_data),
            }
        )
        return context


class AuditFindingDetailView(LoginRequiredMixin, DetailView):
    model = AuditFinding
    template_name = "audits/finding_detail.html"
    context_object_name = "finding"

    def get_queryset(self):
        return AuditFinding.objects.select_related(
            "parent_audit",
            "parent_audit__template",
            "origin_question",
            "reviewed_by",
        ).prefetch_related("capas__assigned_to")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["response"] = AuditResponse.objects.filter(
            schedule=self.object.parent_audit,
            question=self.object.origin_question,
        ).first()
        context["capa_form"] = CAPACreateForm()
        return context


class AuditFindingReviewView(ManagerOrAdminRequiredMixin, UpdateView):
    model = AuditFinding
    form_class = AuditFindingReviewForm
    template_name = "audits/finding_review.html"
    context_object_name = "finding"

    def form_valid(self, form):
        finding = form.save(commit=False)
        finding.reviewed_by = self.request.user
        finding.reviewed_at = timezone.now()
        finding.manager_review_status = form.cleaned_data["decision"]
        finding.status = (
            AuditFinding.STATUS_OPEN
            if form.cleaned_data["decision"] == AuditFinding.REVIEW_APPROVED
            else AuditFinding.STATUS_DRAFT
        )
        finding.save()
        NotificationService.notify(finding, "AUDIT_FINDING_REVIEWED", module="AUDIT")
        messages.success(self.request, f"Finding {finding.finding_id} reviewed successfully.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("audits:finding_detail", kwargs={"pk": self.object.pk})


class CAPACreateView(ManagerOrAdminRequiredMixin, CreateView):
    model = CAPA
    form_class = CAPACreateForm
    template_name = "audits/capa_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.finding = get_object_or_404(AuditFinding, pk=kwargs["finding_pk"], is_archived=False)
        if self.finding.manager_review_status != AuditFinding.REVIEW_APPROVED:
            messages.error(request, "Approve the finding before opening a CAPA task.")
            return redirect("audits:finding_detail", pk=self.finding.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.finding = self.finding
        response = super().form_valid(form)
        self.finding.status = AuditFinding.STATUS_IN_PROGRESS
        self.finding.save(update_fields=["status", "updated_at"])
        messages.success(self.request, "CAPA task created successfully.")
        return response

    def get_success_url(self):
        return reverse("audits:finding_detail", kwargs={"pk": self.finding.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["finding"] = self.finding
        return context


class CAPAUpdateView(LoginRequiredMixin, UpdateView):
    model = CAPA
    form_class = CAPAUpdateForm
    template_name = "audits/capa_update.html"
    context_object_name = "capa"


    def get_queryset(self):
        return CAPA.objects.select_related("finding", "assigned_to", "finding__parent_audit")

    def form_valid(self, form):
        capa = form.save(commit=False)
        if form.cleaned_data.get("mark_as_fixed"):
            capa.verification_status = CAPA.STATUS_FIXED
        capa.save()

        if capa.verification_status == CAPA.STATUS_FIXED:
            capa.finding.status = AuditFinding.STATUS_RESOLVED
            capa.finding.save(update_fields=["status", "updated_at"])
        elif capa.verification_status == CAPA.STATUS_VERIFIED:
            capa.verified_by = self.request.user
            capa.verified_at = timezone.now()
            capa.save(update_fields=["verified_by", "verified_at", "updated_at"])
            capa.finding.status = AuditFinding.STATUS_CLOSED
            capa.finding.save(update_fields=["status", "updated_at"])

        NotificationService.notify(
            capa,
            "AUDIT_CAPA_UPDATED",
            module="AUDIT",
            extra_recipients=[capa.assigned_to],
        )

        messages.success(self.request, "CAPA updated successfully.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("audits:finding_detail", kwargs={"pk": self.object.finding.pk})
