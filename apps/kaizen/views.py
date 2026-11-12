from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import TemplateView, ListView, DeleteView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from apps.accounts.models import *
from .models import *
from django.db.models import Count, Q
from .forms import *
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.apps import apps as django_apps
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.http import FileResponse
from django.views import View
from datetime import datetime, date
from .related_records import RELATED_RECORD_MODELS
from .reporting import generate_kaizen_final_report


def _sync_kaizen_after_implementation_change(implementation, user):
    kaizen = implementation.kaizen
    if implementation.implementation_status == KaizenImplementation.ImplementationStatusChoices.COMPLETED:
        return

    new_status = (
        Kaizen.StatusChoices.ON_HOLD
        if implementation.implementation_status == KaizenImplementation.ImplementationStatusChoices.ON_HOLD
        else Kaizen.StatusChoices.IN_PROGRESS
    )
    if kaizen.status != new_status:
        old_status = kaizen.status
        kaizen.status = new_status
        kaizen.current_stage = 'IMPLEMENTATION'
        kaizen.save(update_fields=['status', 'current_stage', 'updated_at'])
        KaizenHistory.objects.create(
            kaizen=kaizen,
            previous_status=old_status,
            new_status=kaizen.status,
            action='Implementation Put On Hold' if new_status == Kaizen.StatusChoices.ON_HOLD else 'Implementation Resumed',
            comments=implementation.implementation_remarks,
            changed_by=user,
        )


class KaizenRelatedRecordSearchView(LoginRequiredMixin, View):
    """Search records from the selected, allowlisted EHS module."""

    def get(self, request, *args, **kwargs):
        module = request.GET.get('module', '').strip().lower()
        model_path = RELATED_RECORD_MODELS.get(module)
        if not model_path:
            return JsonResponse({'results': []})

        model = django_apps.get_model(*model_path)
        content_type = ContentType.objects.get_for_model(model)
        queryset = model.objects.all().order_by('-pk')
        selected = request.GET.get('selected', '').strip()
        query = request.GET.get('q', '').strip()

        if selected.isdigit():
            queryset = model.objects.filter(pk=selected)
        elif query:
            searchable_fields = [
                field.name for field in model._meta.fields
                if field.get_internal_type() in ('CharField', 'TextField')
            ]
            search = Q(pk=int(query)) if query.isdigit() else Q()
            for field_name in searchable_fields:
                search |= Q(**{f'{field_name}__icontains': query})
            queryset = queryset.filter(search).order_by('-pk')

        try:
            results = [
                {
                    'value': str(record.pk),
                    'label': str(record)[:180],
                    'content_type_id': content_type.pk,
                }
                for record in queryset[:100]
            ]
        except (OperationalError, ProgrammingError):
            results = []
        return JsonResponse({'results': results})

class KaizenCategoryListView(LoginRequiredMixin, ListView):
    model = KaizenCategory
    template_name = 'kaizen/category_list.html'
    context_object_name = 'kaizen_category'
    paginate_by = 20

    def get_queryset(self):
        queryset = KaizenCategory.objects.order_by('name')
        search_query = self.request.GET.get('search','')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context ['search_query'] = self.request.GET.get('search', '')
        category_counts = KaizenCategory.objects.aggregate(
            total_categories=Count('pk'),
            active_categories=Count('pk', filter=Q(is_active=True)),
            inactive_categories=Count('pk', filter=Q(is_active=False)),
        )
        context.update(category_counts)
        return context

class KaizenCategoryCreateView(LoginRequiredMixin, CreateView):
    model = KaizenCategory
    form_class = KaizenCategoryForm
    template_name = 'kaizen/category_form.html'
    success_url = reverse_lazy('kaizen:category_list')

    def form_valid(self, form):
        kaizen_category = form.save(commit=False)
        kaizen_category.created_by = self.request.user
        kaizen_category.save()

        messages.success(
            self.request, f'Kaizen Type "{kaizen_category.name}" created successfully!'
        )
        return super().form_valid(form)

class KaizenCategoryUpdateView(LoginRequiredMixin,UpdateView):
    model = KaizenCategory
    form_class = KaizenCategoryForm
    template_name = 'kaizen/category_form.html'
    success_url = reverse_lazy('kaizen:category_list')

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Kaizen Category "{self.object.name}" updated successfully!'
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        context['kaizen_category'] = self.get_object

        return context

class KaizenCategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = KaizenCategory
    template_name = 'kaizen/category_confirm_delete.html'
    success_url = reverse_lazy('kaizen:category_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['kaizen_category'] = self.object
        context['kaizen_count'] = 0
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        kaizen_category_name = self.object.name
        self.success_url = self.get_success_url()
        self.object.delete()
        messages.success(
            request, f'Kaizen Category "{kaizen_category_name}" deleted successfully!'
        )
        return redirect(self.success_url)   
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'kaizen/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        kaizens = Kaizen.objects.all()

        context['total_kaizens'] = kaizens.count()
        context['submitted_kaizens'] = kaizens.exclude(status=Kaizen.StatusChoices.DRAFT).count()
        context['draft_kaizens'] = kaizens.filter(
            status=Kaizen.StatusChoices.DRAFT
        ).count()
        review_statuses = [
            Kaizen.StatusChoices.SUBMITTED,
            Kaizen.StatusChoices.UNDER_INITIAL_REVIEW,
            Kaizen.StatusChoices.UNDER_TECHNICAL_EVALUATION,
            Kaizen.StatusChoices.PENDING_APPROVAL,
        ]
        context['under_review_kaizens'] = kaizens.filter(status__in=review_statuses).count()
        context['in_progress_kaizens'] = kaizens.filter(
            status__in=[
                Kaizen.StatusChoices.APPROVED_FOR_IMPLEMENTATION,
                Kaizen.StatusChoices.IN_PROGRESS,
                Kaizen.StatusChoices.ON_HOLD,
                Kaizen.StatusChoices.PENDING_VERIFICATION,
                Kaizen.StatusChoices.VERIFICATION_FAILED,
                Kaizen.StatusChoices.PENDING_CLOSURE,
            ]
        ).count()
        context['pending_verification'] = kaizens.filter(
            status=Kaizen.StatusChoices.PENDING_VERIFICATION
        ).count()
        context['closed_kaizens'] = kaizens.filter(
            status=Kaizen.StatusChoices.CLOSED
        ).count()

        context['recent_kaizens'] = kaizens.select_related(
            'category', 'submitted_by', 'department'
        ).order_by('-created_at')[:10]

        status_distribution = [
            {'label': label, 'value': kaizens.filter(status=value).count()}
            for value, label in Kaizen.StatusChoices.choices
        ]
        context['status_distribution'] = status_distribution

        # Six calendar months of submissions and closures for the trend chart.
        current_month = timezone.localdate().replace(day=1)
        months = []
        for offset in range(5, -1, -1):
            month_index = current_month.year * 12 + current_month.month - 1 - offset
            year, month_number = divmod(month_index, 12)
            months.append(date(year, month_number + 1, 1))
        trend_labels = [month.strftime('%b %y') for month in months]
        trend_submitted = []
        trend_closed = []
        for month_start in months:
            next_month_index = month_start.year * 12 + month_start.month
            next_year, next_month_number = divmod(next_month_index, 12)
            month_end = date(next_year, next_month_number + 1, 1)
            start_dt = timezone.make_aware(datetime.combine(month_start, datetime.min.time()))
            end_dt = timezone.make_aware(datetime.combine(month_end, datetime.min.time()))
            trend_submitted.append(kaizens.filter(
                submission_date__gte=start_dt, submission_date__lt=end_dt,
            ).count())
            trend_closed.append(kaizens.filter(
                status=Kaizen.StatusChoices.CLOSED,
                closure__closure_date__gte=start_dt,
                closure__closure_date__lt=end_dt,
            ).count())
        context['trend_labels'] = trend_labels
        context['trend_submitted'] = trend_submitted
        context['trend_closed'] = trend_closed

        context['department_performance'] = list(
            kaizens.exclude(department__isnull=True)
            .values('department__name')
            .annotate(
                submitted=Count('pk', filter=~Q(status=Kaizen.StatusChoices.DRAFT)),
                closed=Count('pk', filter=Q(status=Kaizen.StatusChoices.CLOSED)),
            )
            .order_by('-submitted', 'department__name')[:7]
        )

        overdue_implementations = KaizenImplementation.objects.filter(
            planned_end_date__lt=timezone.localdate(),
            implementation_status__in=[
                KaizenImplementation.ImplementationStatusChoices.NOT_STARTED,
                KaizenImplementation.ImplementationStatusChoices.IN_PROGRESS,
                KaizenImplementation.ImplementationStatusChoices.ON_HOLD,
            ],
            kaizen__status__in=[
                Kaizen.StatusChoices.IN_PROGRESS,
                Kaizen.StatusChoices.ON_HOLD,
                Kaizen.StatusChoices.VERIFICATION_FAILED,
            ],
        ).select_related('kaizen', 'implementation_owner').order_by('planned_end_date')
        today = timezone.localdate()
        overdue_rows = list(overdue_implementations[:5])
        for implementation in overdue_rows:
            implementation.overdue_days = (today - implementation.planned_end_date).days
        context['overdue_implementations'] = overdue_rows
        context['overdue_actions_count'] = overdue_implementations.count()

        context['my_kaizens_count'] = kaizens.filter(
            submitted_by=self.request.user
        ).count()

        owner_implementations = KaizenImplementation.objects.filter(
            implementation_owner=self.request.user,
        )
        active_implementation_statuses = [
            KaizenImplementation.ImplementationStatusChoices.NOT_STARTED,
            KaizenImplementation.ImplementationStatusChoices.IN_PROGRESS,
            KaizenImplementation.ImplementationStatusChoices.ON_HOLD,
        ]
        context['my_actions_count'] = owner_implementations.filter(
            Q(
                kaizen__status__in=[Kaizen.StatusChoices.IN_PROGRESS, Kaizen.StatusChoices.ON_HOLD],
                implementation_status__in=active_implementation_statuses,
            ) | Q(kaizen__status=Kaizen.StatusChoices.VERIFICATION_FAILED)
        ).count()

        context['overdue_actions_count'] = owner_implementations.filter(
            planned_end_date__lt=timezone.localdate(),
        ).filter(
            Q(
                kaizen__status__in=[Kaizen.StatusChoices.IN_PROGRESS, Kaizen.StatusChoices.ON_HOLD],
                implementation_status__in=active_implementation_statuses,
            ) | Q(kaizen__status=Kaizen.StatusChoices.VERIFICATION_FAILED)
        ).count()

        return context


# KAIZEN LIST
class KaizenListView(LoginRequiredMixin, ListView):
    model = Kaizen
    template_name = 'kaizen/kaizen_list.html'
    context_object_name = 'kaizens'
    paginate_by = 20

    def get_queryset(self):
        queryset = Kaizen.objects.select_related(
            'category',
            'submitted_by',
            'plant',
            'department',
            'assigned_to'
        ).order_by('-created_at')

        search_query = self.request.GET.get('search', '')
        status = self.request.GET.get('status', '')
        priority = self.request.GET.get('priority', '')

        if search_query:
            queryset = queryset.filter(
                Q(kaizen_id__icontains=search_query) |
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(submitted_by__username__icontains=search_query)
            )

        if status:
            queryset = queryset.filter(status=status)

        if priority:
            queryset = queryset.filter(priority=priority)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_priority'] = self.request.GET.get('priority', '')

        context['status_choices'] = Kaizen.StatusChoices.choices
        context['priority_choices'] = Kaizen.PriorityChoices.choices

        return context


# KAIZEN CREATE
class KaizenCreateView(LoginRequiredMixin, CreateView):
    model = Kaizen
    form_class = KaizenForm
    template_name = 'kaizen/kaizen_form.html'
    success_url = reverse_lazy('kaizen:my_kaizens')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_assigned_plants'] = self.request.user.assigned_plants.filter(is_active=True)
        return context

    def form_valid(self, form):
        with transaction.atomic():
            kaizen = form.save(commit=False)

            kaizen.submitted_by = self.request.user
            kaizen.created_by = self.request.user

            # The form has no draft action: every valid create is a submission.
            # Do not rely on the submit button's POST value because the frontend
            # disables that button during submission, which omits it from POST.
            kaizen.status = Kaizen.StatusChoices.SUBMITTED
            kaizen.submission_date = timezone.now()
            kaizen.current_stage = 'INITIAL_REVIEW'

            kaizen.save()

            KaizenHistory.objects.create(
                kaizen=kaizen,
                previous_status='',
                new_status=kaizen.status,
                action='Kaizen Created',
                comments='Kaizen idea created.',
                changed_by=self.request.user
            )

        messages.success(
            self.request,
            f'Kaizen "{kaizen.kaizen_id or kaizen.title}" saved successfully!'
        )

        return redirect(self.success_url)


class KaizenEditView(LoginRequiredMixin, UpdateView):
    model = Kaizen
    form_class = KaizenForm
    template_name = 'kaizen/kaizen_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return Kaizen.objects.filter(
            submitted_by=self.request.user,
            status__in=[
                Kaizen.StatusChoices.DRAFT,
                Kaizen.StatusChoices.RETURNED_FOR_CLARIFICATION,
                Kaizen.StatusChoices.RETURNED_FOR_REVISION,
            ]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_editing'] = True
        context['user_assigned_plants'] = self.request.user.assigned_plants.filter(is_active=True)
        return context

    def form_valid(self, form):
        with transaction.atomic():
            kaizen = form.save(commit=False)
            old_status = kaizen.status
            old_stage = kaizen.current_stage
            kaizen.submission_date = timezone.now()
            if (
                old_status == Kaizen.StatusChoices.RETURNED_FOR_REVISION
                or old_stage == 'TECHNICAL_EVALUATION'
            ):
                kaizen.status = Kaizen.StatusChoices.UNDER_TECHNICAL_EVALUATION
                kaizen.current_stage = 'TECHNICAL_EVALUATION'
            else:
                kaizen.status = Kaizen.StatusChoices.SUBMITTED
                kaizen.current_stage = 'INITIAL_REVIEW'
            kaizen.save()
            KaizenHistory.objects.create(
                kaizen=kaizen,
                previous_status=old_status,
                new_status=kaizen.status,
                action='Kaizen Resubmitted',
                comments='Kaizen idea updated by submitter.',
                changed_by=self.request.user,
            )
        messages.success(
            self.request,
            'Kaizen resubmitted for technical evaluation.'
            if kaizen.status == Kaizen.StatusChoices.UNDER_TECHNICAL_EVALUATION
            else 'Kaizen submitted for initial review.',
        )
        return redirect('kaizen:kaizen_detail', pk=kaizen.pk)


# KAIZEN DETAIL
class KaizenDetailView(LoginRequiredMixin, DetailView):
    model = Kaizen
    template_name = 'kaizen/kaizen_detail.html'
    context_object_name = 'kaizen'

    def get_queryset(self):
        return Kaizen.objects.select_related(
            'category',
            'submitted_by',
            'plant',
            'department',
            'zone',
            'location_record',
            'sublocation',
            'assigned_to',
            'related_content_type'
        ).prefetch_related(
            'initial_reviews',
            'technical_evaluations',
            'approvals',
            'verifications',
            'attachments',
            'history'
        )


# MY KAIZENS
class MyKaizenListView(LoginRequiredMixin, ListView):
    model = Kaizen
    template_name = 'kaizen/my_kaizens.html'
    context_object_name = 'kaizens'
    paginate_by = 20

    def get_queryset(self):
        return Kaizen.objects.filter(
            submitted_by=self.request.user
        ).select_related(
            'category', 'plant', 'department'
        ).order_by('-created_at')


# INITIAL REVIEW
class KaizenStageContextMixin:
    """Provide the parent Kaizen to the shared workflow form template."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = getattr(self, 'object', None)
        kaizen = getattr(self, 'kaizen', None)
        if kaizen is None and obj is not None:
            kaizen = getattr(obj, 'kaizen', None)
            if kaizen is None:
                implementation = getattr(obj, 'implementation', None)
                if implementation is not None:
                    kaizen = implementation.kaizen
        if kaizen is None:
            implementation = getattr(self, 'implementation', None)
            if implementation is not None:
                kaizen = implementation.kaizen
        context['stage_kaizen'] = kaizen
        return context


class KaizenInitialReviewCreateView(KaizenStageContextMixin, LoginRequiredMixin, CreateView):
    model = KaizenInitialReview
    form_class = KaizenInitialReviewForm
    template_name = 'kaizen/initial_review_form.html'
    extra_context = {
        'stage_key': 'initial_review',
        'stage_title': 'Stage 2 · Initial Review',
        'stage_description': 'Accept the idea for technical evaluation, request clarification, mark it duplicate, or reject it.',
    }

    def dispatch(self, request, *args, **kwargs):
        self.kaizen = get_object_or_404(
            Kaizen, pk=kwargs['kaizen_id']
        )
        if self.kaizen.status not in [
            Kaizen.StatusChoices.SUBMITTED,
            Kaizen.StatusChoices.UNDER_INITIAL_REVIEW,
        ]:
            messages.warning(request, 'This Kaizen is not awaiting initial review.')
            return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            review = form.save(commit=False)
            review.kaizen = self.kaizen
            review.reviewed_by = self.request.user
            review.save()

            old_status = self.kaizen.status

            decision_status = {
                KaizenInitialReview.DecisionChoices.ACCEPTED:
                    Kaizen.StatusChoices.UNDER_TECHNICAL_EVALUATION,

                KaizenInitialReview.DecisionChoices.CLARIFICATION:
                    Kaizen.StatusChoices.RETURNED_FOR_CLARIFICATION,

                KaizenInitialReview.DecisionChoices.DUPLICATE:
                    Kaizen.StatusChoices.DUPLICATE,

                KaizenInitialReview.DecisionChoices.REJECTED:
                    Kaizen.StatusChoices.REJECTED,
            }

            self.kaizen.status = decision_status[review.decision]

            if review.decision == KaizenInitialReview.DecisionChoices.ACCEPTED:
                self.kaizen.current_stage = 'TECHNICAL_EVALUATION'

            self.kaizen.save()

            KaizenHistory.objects.create(
                kaizen=self.kaizen,
                previous_status=old_status,
                new_status=self.kaizen.status,
                action='Initial Review',
                comments=review.review_comments,
                changed_by=self.request.user
            )

        messages.success(self.request, 'Initial review submitted successfully!')
        return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)


# TECHNICAL EVALUATION
class KaizenTechnicalEvaluationCreateView(KaizenStageContextMixin, LoginRequiredMixin, CreateView):
    model = KaizenTechnicalEvaluation
    form_class = KaizenTechnicalEvaluationForm
    template_name = 'kaizen/technical_evaluation_form.html'
    extra_context = {
        'stage_key': 'technical_evaluation',
        'stage_title': 'Stage 3 · Technical Evaluation',
        'stage_description': 'Assess feasibility and impacts, then recommend approval, request clarification, or recommend rejection.',
    }

    def dispatch(self, request, *args, **kwargs):
        self.kaizen = get_object_or_404(
            Kaizen, pk=kwargs['kaizen_id']
        )
        if self.kaizen.status != Kaizen.StatusChoices.UNDER_TECHNICAL_EVALUATION:
            messages.warning(request, 'This Kaizen is not awaiting technical evaluation.')
            return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            evaluation = form.save(commit=False)
            evaluation.kaizen = self.kaizen
            evaluation.evaluated_by = self.request.user
            evaluation.save()

            old_status = self.kaizen.status
            if (
                evaluation.decision == KaizenTechnicalEvaluation.DecisionChoices.CLARIFICATION
            ):
                self.kaizen.status = Kaizen.StatusChoices.RETURNED_FOR_REVISION
                self.kaizen.current_stage = 'TECHNICAL_EVALUATION'
            elif (
                evaluation.decision == KaizenTechnicalEvaluation.DecisionChoices.REJECTED
                or evaluation.feasibility == KaizenTechnicalEvaluation.FeasibilityChoices.NOT_FEASIBLE
            ):
                self.kaizen.status = Kaizen.StatusChoices.REJECTED
                self.kaizen.current_stage = 'TECHNICAL_EVALUATION'
            else:
                self.kaizen.status = Kaizen.StatusChoices.PENDING_APPROVAL
                self.kaizen.current_stage = 'APPROVAL'
            self.kaizen.save()

            KaizenHistory.objects.create(
                kaizen=self.kaizen,
                previous_status=old_status,
                new_status=self.kaizen.status,
                action='Technical Evaluation',
                comments=evaluation.technical_comments or evaluation.recommendation,
                changed_by=self.request.user
            )

        messages.success(
            self.request,
            'Technical evaluation submitted successfully!'
        )

        return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)


# APPROVAL
class KaizenApprovalCreateView(KaizenStageContextMixin, LoginRequiredMixin, CreateView):
    model = KaizenApproval
    form_class = KaizenApprovalForm
    template_name = 'kaizen/approval_form.html'
    extra_context = {
        'stage_key': 'approval',
        'stage_title': 'Stage 4 · Approval',
        'stage_description': 'Approve the recommended improvement, return it for revision, or reject it.',
    }

    def dispatch(self, request, *args, **kwargs):
        self.kaizen = get_object_or_404(
            Kaizen, pk=kwargs['kaizen_id']
        )
        if self.kaizen.status != Kaizen.StatusChoices.PENDING_APPROVAL:
            messages.warning(request, 'This Kaizen is not awaiting approval.')
            return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            approval = form.save(commit=False)
            approval.kaizen = self.kaizen
            approval.approved_by = self.request.user
            approval.save()

            old_status = self.kaizen.status

            decision_status = {
                KaizenApproval.DecisionChoices.APPROVED:
                    Kaizen.StatusChoices.APPROVED_FOR_IMPLEMENTATION,

                KaizenApproval.DecisionChoices.REJECTED:
                    Kaizen.StatusChoices.REJECTED,

                KaizenApproval.DecisionChoices.REVISION:
                    Kaizen.StatusChoices.RETURNED_FOR_REVISION,
            }

            self.kaizen.status = decision_status[approval.decision]

            if approval.decision == KaizenApproval.DecisionChoices.APPROVED:
                self.kaizen.current_stage = 'IMPLEMENTATION'
            elif approval.decision == KaizenApproval.DecisionChoices.REVISION:
                self.kaizen.current_stage = 'TECHNICAL_EVALUATION'

            self.kaizen.save()

            KaizenHistory.objects.create(
                kaizen=self.kaizen,
                previous_status=old_status,
                new_status=self.kaizen.status,
                action='Approval',
                comments=approval.approval_comments,
                changed_by=self.request.user
            )

        messages.success(self.request, 'Approval decision recorded successfully!')
        return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)


# IMPLEMENTATION
class KaizenImplementationCreateView(KaizenStageContextMixin, LoginRequiredMixin, CreateView):
    model = KaizenImplementation
    form_class = KaizenImplementationForm
    template_name = 'kaizen/implementation_form.html'
    extra_context = {
        'stage_key': 'implementation',
        'stage_title': 'Stage 5 · Implementation Plan',
        'stage_description': 'Assign the implementation owner, dates, plan, and required resources.',
    }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['plant'] = self.kaizen.plant
        kwargs['user'] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        self.kaizen = get_object_or_404(
            Kaizen, pk=kwargs['kaizen_id']
        )
        if (
            self.kaizen.status != Kaizen.StatusChoices.APPROVED_FOR_IMPLEMENTATION
            or self.kaizen.implementations.exists()
        ):
            messages.warning(request, 'Implementation can start only after approval and can be planned once.')
            return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            implementation = form.save(commit=False)
            implementation.kaizen = self.kaizen
            implementation.save()

            old_status = self.kaizen.status
            self.kaizen.status = (
                Kaizen.StatusChoices.ON_HOLD
                if implementation.implementation_status == KaizenImplementation.ImplementationStatusChoices.ON_HOLD
                else Kaizen.StatusChoices.IN_PROGRESS
            )
            self.kaizen.current_stage = 'IMPLEMENTATION'
            self.kaizen.save()

            KaizenHistory.objects.create(
                kaizen=self.kaizen,
                previous_status=old_status,
                new_status=self.kaizen.status,
                action='Implementation Started',
                comments=implementation.implementation_remarks,
                changed_by=self.request.user
            )

        messages.success(self.request, 'Implementation plan saved successfully!')
        return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)


class KaizenImplementationUpdateView(KaizenStageContextMixin, LoginRequiredMixin, UpdateView):
    model = KaizenImplementation
    form_class = KaizenImplementationForm
    template_name = 'kaizen/implementation_update_form.html'
    extra_context = {
        'stage_key': 'implementation_update',
        'stage_title': 'Stage 5 · Implementation Update',
        'stage_description': 'Update implementation progress and costs. The assigned owner submits completion for verification.',
    }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['plant'] = self.object.kaizen.plant
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return KaizenImplementation.objects.filter(
            kaizen__status__in=[
                Kaizen.StatusChoices.APPROVED_FOR_IMPLEMENTATION,
                Kaizen.StatusChoices.IN_PROGRESS,
                Kaizen.StatusChoices.ON_HOLD,
                Kaizen.StatusChoices.VERIFICATION_FAILED,
            ]
        )

    def get_success_url(self):
        return reverse(
            'kaizen:kaizen_detail',
            kwargs={'pk': self.object.kaizen.pk}
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        _sync_kaizen_after_implementation_change(self.object, self.request.user)

        messages.success(self.request, 'Implementation updated successfully!')
        return response


# MY ACTIONS
class MyKaizenActionsView(LoginRequiredMixin, ListView):
    model = KaizenImplementation
    template_name = 'kaizen/my_actions.html'
    context_object_name = 'implementations'
    paginate_by = 20

    def get_queryset(self):
        return KaizenImplementation.objects.filter(
            implementation_owner=self.request.user,
        ).filter(
            Q(
                kaizen__status__in=[Kaizen.StatusChoices.IN_PROGRESS, Kaizen.StatusChoices.ON_HOLD],
                implementation_status__in=[
                    KaizenImplementation.ImplementationStatusChoices.NOT_STARTED,
                    KaizenImplementation.ImplementationStatusChoices.IN_PROGRESS,
                    KaizenImplementation.ImplementationStatusChoices.ON_HOLD,
                ],
            ) | Q(kaizen__status=Kaizen.StatusChoices.VERIFICATION_FAILED)
        ).select_related('kaizen', 'kaizen__plant').order_by('planned_end_date', '-created_at')


class KaizenImplementationCompletionView(LoginRequiredMixin, View):
    """Let the assigned implementation owner submit completion and evidence."""

    template_name = 'kaizen/implementation_completion_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.implementation = get_object_or_404(
            KaizenImplementation.objects.select_related(
                'kaizen', 'kaizen__category', 'kaizen__plant',
                'implementation_owner',
            ).filter(implementation_owner=request.user).filter(
                Q(
                    kaizen__status__in=[Kaizen.StatusChoices.IN_PROGRESS, Kaizen.StatusChoices.ON_HOLD],
                    implementation_status__in=[
                        KaizenImplementation.ImplementationStatusChoices.NOT_STARTED,
                        KaizenImplementation.ImplementationStatusChoices.IN_PROGRESS,
                        KaizenImplementation.ImplementationStatusChoices.ON_HOLD,
                    ],
                ) | Q(kaizen__status=Kaizen.StatusChoices.VERIFICATION_FAILED)
            ),
            pk=kwargs['pk'],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, form):
        return {
            'implementation': self.implementation,
            'kaizen': self.implementation.kaizen,
            'form': form,
        }

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            self.get_context_data(KaizenImplementationCompletionForm()),
        )

    def post(self, request, *args, **kwargs):
        form = KaizenImplementationCompletionForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, self.get_context_data(form))

        with transaction.atomic():
            implementation = self.implementation
            kaizen = implementation.kaizen
            implementation.actual_end_date = form.cleaned_data['completion_date']
            implementation.implementation_status = KaizenImplementation.ImplementationStatusChoices.COMPLETED
            implementation.completed_at = timezone.now()
            completion_note = form.cleaned_data['completion_remarks'].strip()
            existing_notes = implementation.implementation_remarks.strip()
            implementation.implementation_remarks = (
                f'{existing_notes}\n\nCompletion: {completion_note}'
                if existing_notes else completion_note
            )
            implementation.save(update_fields=[
                'actual_end_date', 'implementation_status', 'completed_at',
                'implementation_remarks', 'updated_at',
            ])

            old_status = kaizen.status
            kaizen.status = Kaizen.StatusChoices.PENDING_VERIFICATION
            kaizen.current_stage = 'VERIFICATION'
            kaizen.save(update_fields=['status', 'current_stage', 'updated_at'])
            KaizenHistory.objects.create(
                kaizen=kaizen,
                previous_status=old_status,
                new_status=kaizen.status,
                action='Implementation Completed',
                comments=completion_note,
                changed_by=request.user,
            )

            evidence = form.cleaned_data.get('evidence')
            if evidence:
                KaizenAttachment.objects.create(
                    kaizen=kaizen,
                    file=evidence,
                    attachment_type=KaizenAttachment.AttachmentTypeChoices.IMPLEMENTATION,
                    description='Implementation completion evidence',
                    uploaded_by=request.user,
                )

        messages.success(request, 'Implementation marked complete. Kaizen is now awaiting verification.')
        return redirect('kaizen:kaizen_detail', pk=self.implementation.kaizen.pk)


# VERIFICATION
class KaizenVerificationCreateView(KaizenStageContextMixin, LoginRequiredMixin, CreateView):
    model = KaizenVerification
    form_class = KaizenVerificationForm
    template_name = 'kaizen/verification_form.html'
    extra_context = {
        'stage_key': 'verification',
        'stage_title': 'Stage 6 · Verification',
        'stage_description': 'Record before-and-after results and decide whether the improvement is effective or needs rework.',
    }

    def dispatch(self, request, *args, **kwargs):
        self.kaizen = get_object_or_404(
            Kaizen, pk=kwargs['kaizen_id']
        )
        if self.kaizen.status != Kaizen.StatusChoices.PENDING_VERIFICATION:
            messages.warning(request, 'Verification is available after implementation is completed.')
            return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            verification = form.save(commit=False)
            verification.kaizen = self.kaizen
            verification.verified_by = self.request.user
            verification.save()

            old_status = self.kaizen.status

            if verification.result == KaizenVerification.ResultChoices.SUCCESSFUL:
                self.kaizen.status = Kaizen.StatusChoices.PENDING_CLOSURE
                self.kaizen.current_stage = 'CLOSURE'

            elif (
                verification.result == KaizenVerification.ResultChoices.PARTIAL
                and verification.rework_required
            ) or verification.result == KaizenVerification.ResultChoices.FAILED:
                self.kaizen.status = Kaizen.StatusChoices.VERIFICATION_FAILED
                self.kaizen.current_stage = 'IMPLEMENTATION'

            else:
                self.kaizen.status = Kaizen.StatusChoices.PENDING_CLOSURE
                self.kaizen.current_stage = 'CLOSURE'

            self.kaizen.save()

            KaizenHistory.objects.create(
                kaizen=self.kaizen,
                previous_status=old_status,
                new_status=self.kaizen.status,
                action='Verification',
                comments=verification.verification_comments,
                changed_by=self.request.user
            )

        messages.success(self.request, 'Verification recorded successfully!')
        return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)


class KaizenAttachmentCreateView(KaizenStageContextMixin, LoginRequiredMixin, CreateView):
    model = KaizenAttachment
    form_class = KaizenAttachmentForm
    template_name = 'kaizen/attachment_form.html'
    extra_context = {
        'stage_key': 'attachment',
        'stage_title': 'Upload Supporting Evidence',
        'stage_description': 'Attach proposal, implementation, or verification evidence to this Kaizen.',
    }

    def dispatch(self, request, *args, **kwargs):
        self.kaizen = get_object_or_404(Kaizen, pk=kwargs['kaizen_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        attachment = form.save(commit=False)
        attachment.kaizen = self.kaizen
        attachment.uploaded_by = self.request.user
        attachment.save()
        messages.success(self.request, 'Evidence uploaded successfully!')
        return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)


# CLOSURE
class KaizenClosureCreateView(KaizenStageContextMixin, LoginRequiredMixin, CreateView):
    model = KaizenClosure
    form_class = KaizenClosureForm
    template_name = 'kaizen/closure_form.html'
    extra_context = {
        'stage_key': 'closure',
        'stage_title': 'Stage 7 · Closure',
        'stage_description': 'Summarize the final outcome, actual benefits, cost, and lessons learned. Closure requires successful verification.',
    }

    def dispatch(self, request, *args, **kwargs):
        self.kaizen = get_object_or_404(
            Kaizen, pk=kwargs['kaizen_id']
        )

        if self.kaizen.status != Kaizen.StatusChoices.PENDING_CLOSURE:
            messages.warning(request, 'Kaizen can be closed only after successful verification.')
            return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)

        if hasattr(self.kaizen, 'closure'):
            messages.warning(request, 'This Kaizen has already been closed.')
            return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            closure = form.save(commit=False)
            closure.kaizen = self.kaizen
            closure.closed_by = self.request.user

            try:
                closure.full_clean()
                closure.save()
            except ValidationError as error:
                form.add_error(None, error)
                return self.form_invalid(form)

            old_status = self.kaizen.status
            self.kaizen.status = Kaizen.StatusChoices.CLOSED
            self.kaizen.current_stage = 'CLOSED'
            self.kaizen.save()

            KaizenHistory.objects.create(
                kaizen=self.kaizen,
                previous_status=old_status,
                new_status=self.kaizen.status,
                action='Kaizen Closed',
                comments=closure.closure_comments,
                changed_by=self.request.user
            )

        messages.success(self.request, 'Kaizen closed successfully!')
        return redirect('kaizen:kaizen_detail', pk=self.kaizen.pk)


class KaizenFinalReportView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        kaizen = get_object_or_404(
            Kaizen.objects.select_related(
                'category', 'submitted_by', 'plant', 'department', 'zone',
                'location_record', 'sublocation', 'closure', 'closure__closed_by',
            )
            .prefetch_related(
                'initial_reviews__reviewed_by',
                'technical_evaluations__evaluated_by',
                'approvals__approved_by',
                'implementations__implementation_owner',
                'verifications__verified_by',
                'attachments__uploaded_by',
                'history__changed_by',
            ),
            pk=pk,
        )
        pdf_buffer = generate_kaizen_final_report(kaizen)
        report_name = (kaizen.kaizen_id or f'KZN-{kaizen.pk}').replace('/', '-')
        report_suffix = 'Final_Report' if kaizen.status == Kaizen.StatusChoices.CLOSED else 'Progress_Report'
        return FileResponse(
            pdf_buffer,
            as_attachment=True,
            filename=f'{report_name}_{report_suffix}.pdf',
            content_type='application/pdf',
        )


# WORKFLOW HISTORY
class KaizenHistoryListView(LoginRequiredMixin, ListView):
    model = KaizenHistory
    template_name = 'kaizen/kaizen_history.html'
    context_object_name = 'history'
    paginate_by = 30

    def get_queryset(self):
        self.kaizen = get_object_or_404(
            Kaizen, pk=self.kwargs['kaizen_id']
        )

        return KaizenHistory.objects.filter(
            kaizen=self.kaizen
        ).select_related('changed_by').order_by('-changed_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['kaizen'] = self.kaizen
        return context
