# apps/five_s/views.py
import base64
from collections import defaultdict

from .utils import (
    action_is_locked,
    block_if_action_locked,
    block_if_locked,
    schedule_is_locked,
)

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Avg, Count, Exists, OuterRef, Q, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView, DetailView, ListView, TemplateView, UpdateView,
)
from django.contrib.messages import get_messages

from apps.accounts.models import User
from apps.organizations.models import Location, Plant, SubLocation, Zone

from .forms import (
    ActionApprovalForm,
    ActionCompleteForm,
    FiveSQuestionForm,
    FiveSScheduleForm,
    FiveSTemplateBulkAddForm,
    FiveSTemplateForm,
    FiveSTemplateQuestionForm,
    InspectionAnswerForm,
)
from .models import (
    PILLAR_CHOICES,
    AuditAnswer,
    CorrectiveAction,
    FiveSAudit,
    FiveSQuestion,
    FiveSSchedule,
    FiveSTemplate,
    FiveSTemplateQuestion,
)
from .pdf_generators import (
    generate_five_s_audit_pdf,
    generate_five_s_schedule_report_pdf,
)


# ===========================================================================
# CONSTANTS & SHARED HELPERS
# ===========================================================================

PENDING_AUDIT_STATUSES = ['SCHEDULED', 'IN_PROGRESS']
SUBMITTED_AUDIT_STATUSES = ['SUBMITTED', 'REVIEWED', 'CLOSED']


def flash_once(request, message, level=messages.SUCCESS):
    """Adds a message ONLY if it hasn't already been added."""
    existing = [m.message for m in get_messages(request)]
    if message not in existing:
        messages.add_message(request, level, message)


def reassign_pending_audits(schedule, old_user_ids, new_user):
    qs = schedule.audits.filter(status__in=PENDING_AUDIT_STATUSES)
    if old_user_ids is not None:
        qs = qs.filter(user_id__in=list(old_user_ids))
    return qs.exclude(user=new_user).update(user=new_user)


def get_capas_for_audit(audit, finding_answer_ids=None):
    """
    Returns {answer_id_str: CAPA} for every finding in this audit.

    Handles two linkage styles:
      * Per-finding CAPA: source_reference == AuditAnswer.id (as str)
      * Schedule-wide CAPA: source_reference == FiveSSchedule.pk (as str)
        -> fanned out to every finding that doesn't already have its own.

    Ordering is -id so the most recent CAPA wins when multiple exist
    for the same reference.
    """
    from apps.capa.models import CAPA

    if finding_answer_ids is None:
        finding_answer_ids = [
            str(aid) for aid in AuditAnswer.objects
            .filter(audit=audit, answer__in=['1', '2'])
            .values_list('id', flat=True)
        ]
    if not finding_answer_ids:
        return {}

    schedule_id_str = str(audit.schedule_id)

    capa_qs = (
        CAPA.objects
        .filter(source_type='FIVE_S')
        .filter(
            Q(source_reference__in=finding_answer_ids) |
            Q(source_reference=schedule_id_str)
        )
        .select_related('owner')
        .order_by('-id')
    )

    capas_by_finding = {}
    schedule_wide = None
    for capa in capa_qs:
        ref = str(capa.source_reference)
        if ref == schedule_id_str:
            if schedule_wide is None:
                schedule_wide = capa
        else:
            capas_by_finding.setdefault(ref, capa)

    if schedule_wide is not None:
        for aid in finding_answer_ids:
            capas_by_finding.setdefault(aid, schedule_wide)

    return capas_by_finding


def sync_audit_closure(audit):
    """
    Auto-close a 5S audit when every finding is resolved:
      - A CLOSED 5S CorrectiveAction exists for the finding, OR
      - A CAPA (any status) exists for the finding.
    """
    if audit.status not in SUBMITTED_AUDIT_STATUSES:
        return False

    findings = list(
        AuditAnswer.objects
        .filter(audit=audit, answer__in=['1', '2'])
        .values_list('id', 'question_id')
    )
    if not findings:
        return audit.status == 'CLOSED'

    finding_answer_ids = [str(f[0]) for f in findings]
    finding_question_ids = [f[1] for f in findings]

    # 5S Action statuses by question
    statuses_by_question = defaultdict(list)
    for q_id, status in (
        CorrectiveAction.objects
        .filter(audit=audit, question_id__in=finding_question_ids)
        .values_list('question_id', 'status')
    ):
        statuses_by_question[q_id].append(status)

    # CAPAs linked to any of these findings (or the schedule)
    capa_refs = set(
        get_capas_for_audit(audit, finding_answer_ids=finding_answer_ids).keys()
    )

    all_closed = True
    for answer_id, question_id in findings:
        statuses = statuses_by_question.get(question_id, [])
        action_closed = statuses and all(s == 'CLOSED' for s in statuses)
        capa_present = str(answer_id) in capa_refs

        if not (action_closed or capa_present):
            all_closed = False
            break

    if all_closed and audit.status != 'CLOSED':
        audit.status = 'CLOSED'
        audit.save(update_fields=['status'])
    elif not all_closed and audit.status == 'CLOSED':
        audit.status = 'SUBMITTED'
        audit.save(update_fields=['status'])

    return all_closed


def is_schedule_closed(schedule):
    audits = schedule.audits.all()
    return audits.exists() and not audits.exclude(status='CLOSED').exists()


def generate_audits_for_schedule(schedule, target_date=None, users=None):
    if schedule.status != 'ACTIVE':
        return 0

    if target_date is None:
        target_date = schedule.start_date

    if users is None:
        assignees = schedule.assignee.all()
    else:
        assignees = users

    if not assignees.exists():
        return 0

    created = 0
    date_str = target_date.strftime('%Y%m%d')

    for user in assignees:
        exists = FiveSAudit.objects.filter(
            schedule=schedule,
            user=user,
            scheduled_date=target_date,
        ).exists()
        if exists:
            continue

        FiveSAudit.objects.create(
            schedule=schedule,
            user=user,
            template_version=schedule.template.version,
            cycle_key=f"{schedule.pk}-{date_str}-{user.pk}",
            scheduled_date=target_date,
            due_date=target_date,
            status='SCHEDULED',
        )
        created += 1

    return created


# ===========================================================================
# MIXINS
# ===========================================================================

class FiveSContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pillar_choices'] = PILLAR_CHOICES
        return context


# ===========================================================================
# QUESTIONS
# ===========================================================================

class QuestionListView(LoginRequiredMixin, FiveSContextMixin, ListView):
    model = FiveSQuestion
    template_name = 'five_s/question_list.html'
    context_object_name = 'page_obj'
    paginate_by = 25

    def get_queryset(self):
        qs = FiveSQuestion.objects.select_related('created_by').all()
        pillar = self.request.GET.get('pillar', '').strip()
        active = self.request.GET.get('active', '').strip()
        search = self.request.GET.get('search', '').strip()

        if pillar:
            qs = qs.filter(pillar=pillar)
        if active in ('0', '1'):
            qs = qs.filter(is_active=(active == '1'))
        if search:
            qs = qs.filter(
                Q(question_code__icontains=search) |
                Q(question_text__icontains=search) |
                Q(reference_standard__icontains=search)
            )
        return qs.order_by('-created_at', '-question_code')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filters'] = {
            'pillar': self.request.GET.get('pillar', '').strip(),
            'active': self.request.GET.get('active', '').strip(),
            'search': self.request.GET.get('search', '').strip(),
        }
        context['total_questions'] = self.get_queryset().count()
        return context


class QuestionCreateView(LoginRequiredMixin, FiveSContextMixin, CreateView):
    model = FiveSQuestion
    form_class = FiveSQuestionForm
    template_name = 'five_s/question_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Question {self.object.question_code} created successfully.')

        if self.request.POST.get('action_type') == 'save_and_add':
            return redirect('five_s:question_create')

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('five_s:question_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        context['title'] = 'Create 5S Question'
        return context


class QuestionUpdateView(LoginRequiredMixin, FiveSContextMixin, UpdateView):
    model = FiveSQuestion
    form_class = FiveSQuestionForm
    template_name = 'five_s/question_form.html'
    context_object_name = 'question'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Question {self.object.question_code} updated.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Edit'
        context['title'] = f'Edit Question: {self.object.question_code}'
        return context

    def get_success_url(self):
        return reverse('five_s:question_detail', kwargs={'pk': self.object.pk})


class QuestionDetailView(LoginRequiredMixin, DetailView):
    model = FiveSQuestion
    template_name = 'five_s/question_detail.html'
    context_object_name = 'question'

    def get_queryset(self):
        return FiveSQuestion.objects.select_related('created_by')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['templates'] = (
            FiveSTemplate.objects
            .filter(template_questions__question=self.object, is_active=True)
            .distinct()
            .order_by('template_name')
        )
        return context


class QuestionDeactivateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        obj = get_object_or_404(FiveSQuestion, pk=pk)
        return render(request, 'five_s/question_confirm_deactivate.html', {'question': obj})

    def post(self, request, pk):
        obj = get_object_or_404(FiveSQuestion, pk=pk)
        obj.is_active = False
        obj.save(update_fields=['is_active', 'updated_at'])
        messages.success(request, f'Question {obj.question_code} deactivated.')
        return redirect('five_s:question_list')


class QuestionReactivateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        obj = get_object_or_404(FiveSQuestion, pk=pk)
        return render(request, 'five_s/question_confirm_reactivate.html', {'question': obj})

    def post(self, request, pk):
        obj = get_object_or_404(FiveSQuestion, pk=pk)
        obj.is_active = True
        obj.save(update_fields=['is_active', 'updated_at'])
        messages.success(request, f'Question {obj.question_code} reactivated.')
        return redirect('five_s:question_detail', pk=obj.pk)


# ===========================================================================
# TEMPLATES
# ===========================================================================

class TemplateListView(LoginRequiredMixin, ListView):
    model = FiveSTemplate
    template_name = 'five_s/template_list.html'
    context_object_name = 'page_obj'
    paginate_by = 15

    def get_queryset(self):
        qs = FiveSTemplate.objects.select_related('created_by').all()
        active = self.request.GET.get('active', '').strip()
        search = self.request.GET.get('search', '').strip()

        if active in ('0', '1'):
            qs = qs.filter(is_active=(active == '1'))
        if search:
            qs = qs.filter(
                Q(template_name__icontains=search) |
                Q(template_code__icontains=search) |
                Q(description__icontains=search)
            )
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filters'] = {
            'active': self.request.GET.get('active', '').strip(),
            'search': self.request.GET.get('search', '').strip(),
        }
        return context


class TemplateCreateView(LoginRequiredMixin, FiveSContextMixin, CreateView):
    model = FiveSTemplate
    form_class = FiveSTemplateForm
    template_name = 'five_s/template_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        code = form.cleaned_data.get('template_code')
        existing_versions = FiveSTemplate.objects.filter(template_code=code).values_list('version', flat=True)
        form.instance.version = max(existing_versions) + 1 if existing_versions else 1

        self.object = form.save()

        bulk_ids = self.request.POST.getlist('bulk_questions')
        if bulk_ids:
            start_order = self.object.template_questions.count()
            added = 0
            for qid in bulk_ids:
                q = FiveSQuestion.objects.filter(pk=qid).first()
                if q:
                    start_order += 1
                    FiveSTemplateQuestion.objects.create(template=self.object, question=q, display_order=start_order)
                    added += 1
            if added:
                messages.success(self.request, f'{added} question(s) added.')

        messages.success(self.request, f'Template "{self.object.template_name}" created successfully.')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        context['title'] = 'Create 5S Template'

        available_qs = FiveSQuestion.objects.filter(is_active=True).order_by('pillar', 'question_code')
        grouped = defaultdict(list)
        for q in available_qs:
            grouped[q.pillar].append(q)

        pillar_dict = dict(PILLAR_CHOICES)
        context['available_by_pillar'] = {
            code: {'name': pillar_dict.get(code, code), 'questions': qs}
            for code, qs in grouped.items()
        }
        return context

    def get_success_url(self):
        return reverse('five_s:template_detail', kwargs={'pk': self.object.pk})


class TemplateUpdateView(LoginRequiredMixin, FiveSContextMixin, UpdateView):
    model = FiveSTemplate
    form_class = FiveSTemplateForm
    template_name = 'five_s/template_form.html'
    context_object_name = 'template'

    def form_valid(self, form):
        if not form.instance.version:
            form.instance.version = self.object.version
        self.object = form.save()
        submitted_qids = set(int(qid) for qid in self.request.POST.getlist('bulk_questions') if qid.isdigit())
        current_mappings = self.object.template_questions.all()
        for mapping in current_mappings:
            if mapping.question_id not in submitted_qids:
                mapping.delete()
        existing_qids = set(self.object.template_questions.values_list('question_id', flat=True))
        new_qids = submitted_qids - existing_qids
        start_order = self.object.template_questions.count()
        added = 0
        for qid in new_qids:
            q = FiveSQuestion.objects.filter(pk=qid).first()
            if q:
                start_order += 1
                FiveSTemplateQuestion.objects.create(template=self.object, question=q, display_order=start_order)
                added += 1
        if added:
            messages.success(self.request, f'{added} question(s) added.')
        messages.success(self.request, f'Template "{self.object.template_name}" updated successfully.')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Edit'
        context['title'] = f'Edit Template: {self.object.template_name}'
        taken = self.object.template_questions.values_list('question_id', flat=True)
        available_qs = FiveSQuestion.objects.filter(is_active=True).exclude(id__in=taken).order_by('pillar', 'question_code')
        grouped = defaultdict(list)
        for q in available_qs:
            grouped[q.pillar].append(q)
        pillar_dict = dict(PILLAR_CHOICES)
        context['available_by_pillar'] = {
            code: {'name': pillar_dict.get(code, code), 'questions': qs}
            for code, qs in grouped.items()
        }
        context['current_questions'] = self.object.template_questions.select_related('question').order_by('display_order')
        return context

    def get_success_url(self):
        return reverse('five_s:template_detail', kwargs={'pk': self.object.pk})


class TemplateDetailView(LoginRequiredMixin, FiveSContextMixin, DetailView):
    model = FiveSTemplate
    template_name = 'five_s/template_detail.html'
    context_object_name = 'template'

    def get_queryset(self):
        return FiveSTemplate.objects.select_related('created_by')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        template = self.object
        tqs = FiveSTemplateQuestion.objects.filter(template=template).select_related('question').order_by('question__pillar', 'display_order', 'question__question_code')
        by_pillar = defaultdict(list)
        for tq in tqs:
            by_pillar[tq.question.pillar].append(tq)
        context.update({'by_pillar': dict(by_pillar), 'total_questions': tqs.count()})
        return context


class TemplateDeactivateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        obj = get_object_or_404(FiveSTemplate, pk=pk)
        return render(request, 'five_s/template_confirm_deactivate.html', {'template': obj})

    def post(self, request, pk):
        obj = get_object_or_404(FiveSTemplate, pk=pk)
        obj.is_active = False
        obj.save(update_fields=['is_active', 'updated_at'])
        messages.success(request, f'Template "{obj.template_name}" deactivated.')
        return redirect('five_s:template_list')


class TemplateCloneView(LoginRequiredMixin, View):
    def get(self, request, pk):
        template = get_object_or_404(FiveSTemplate, pk=pk)
        return render(request, 'five_s/template_clone.html', {'template': template})

    def post(self, request, pk):
        original = get_object_or_404(FiveSTemplate, pk=pk)
        with transaction.atomic():
            used = set(FiveSTemplate.objects.filter(template_code=original.template_code).values_list('version', flat=True))
            next_version = max(used, default=0) + 1
            new = FiveSTemplate.objects.create(
                template_name=f"{original.template_name} (Copy)",
                template_code=original.template_code,
                version=next_version,
                description=original.description,
                min_compliance_score=original.min_compliance_score,
                is_active=True,
                created_by=request.user,
            )
            for tq in original.template_questions.all():
                FiveSTemplateQuestion.objects.create(
                    template=new, question=tq.question, is_mandatory=tq.is_mandatory,
                    display_order=tq.display_order, section_name=tq.section_name,
                )
        messages.success(request, f'Cloned as {new.template_code} v{new.version}.')
        return redirect('five_s:template_detail', pk=new.pk)


class TemplateAddQuestionView(LoginRequiredMixin, CreateView):
    model = FiveSTemplateQuestion
    form_class = FiveSTemplateQuestionForm
    template_name = 'five_s/template_add_question.html'

    def get_template(self):
        return get_object_or_404(FiveSTemplate, pk=self.kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['template'] = self.get_template()
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial['display_order'] = self.get_template().template_questions.count() + 1
        return initial

    def form_valid(self, form):
        form.instance.template = self.get_template()
        response = super().form_valid(form)
        messages.success(self.request, f'Question {self.object.question.question_code} added.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template'] = self.get_template()
        return context

    def get_success_url(self):
        return reverse('five_s:template_detail', kwargs={'pk': self.kwargs['pk']})


class TemplateBulkAddQuestionsView(LoginRequiredMixin, FiveSContextMixin, View):
    def get_template(self):
        return get_object_or_404(FiveSTemplate, pk=self.kwargs['pk'])

    def get(self, request, pk):
        template = self.get_template()
        form = FiveSTemplateBulkAddForm(template=template)
        available = form.fields['questions'].queryset
        by_pillar = defaultdict(list)
        for q in available:
            by_pillar[q.pillar].append(q)
        return render(request, 'five_s/template_bulk_add_questions.html', {
            'template': template, 'form': form, 'by_pillar': dict(by_pillar),
            'available_count': available.count(), 'pillar_choices': dict(PILLAR_CHOICES),
        })

    def post(self, request, pk):
        template = self.get_template()
        form = FiveSTemplateBulkAddForm(request.POST, template=template)
        if form.is_valid():
            questions = form.cleaned_data['questions']
            section_name = (form.cleaned_data['section_name'] or '').strip()
            start_order = template.template_questions.count()
            added = 0
            with transaction.atomic():
                for q in questions:
                    start_order += 1
                    FiveSTemplateQuestion.objects.create(
                        template=template, question=q, is_mandatory=True,
                        display_order=start_order, section_name=section_name or None,
                    )
                    added += 1
            messages.success(request, f'{added} question(s) added to the template.')
            return redirect('five_s:template_detail', pk=template.pk)
        available = form.fields['questions'].queryset
        by_pillar = defaultdict(list)
        for q in available:
            by_pillar[q.pillar].append(q)
        return render(request, 'five_s/template_bulk_add_questions.html', {
            'template': template, 'form': form, 'by_pillar': dict(by_pillar),
            'available_count': available.count(), 'pillar_choices': dict(PILLAR_CHOICES),
        })


class TemplateRemoveQuestionView(LoginRequiredMixin, View):
    def get(self, request, pk, question_pk):
        template = get_object_or_404(FiveSTemplate, pk=pk)
        tq = get_object_or_404(FiveSTemplateQuestion, template=template, question_id=question_pk)
        return render(request, 'five_s/template_remove_question.html', {'template': template, 'tq': tq})

    def post(self, request, pk, question_pk):
        template = get_object_or_404(FiveSTemplate, pk=pk)
        tq = get_object_or_404(FiveSTemplateQuestion, template=template, question_id=question_pk)
        code = tq.question.question_code
        tq.delete()
        messages.success(request, f'Question {code} removed from template.')
        return redirect('five_s:template_detail', pk=template.pk)


class TemplateEditQuestionWeightView(LoginRequiredMixin, UpdateView):
    model = FiveSTemplateQuestion
    form_class = FiveSTemplateQuestionForm
    template_name = 'five_s/template_edit_question_weight.html'
    context_object_name = 'tq'

    def get_queryset(self):
        return FiveSTemplateQuestion.objects.filter(template_id=self.kwargs['pk'], question_id=self.kwargs['question_pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['template'] = get_object_or_404(FiveSTemplate, pk=self.kwargs['pk'])
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Question {self.object.question.question_code} updated.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template'] = get_object_or_404(FiveSTemplate, pk=self.kwargs['pk'])
        return context

    def get_success_url(self):
        return reverse('five_s:template_detail', kwargs={'pk': self.kwargs['pk']})


# ===========================================================================
# STAGE 2: SCHEDULES
# ===========================================================================

class ScheduleListView(LoginRequiredMixin, ListView):
    model = FiveSSchedule
    template_name = 'five_s/schedule_list.html'
    context_object_name = 'page_obj'
    paginate_by = 15

    def get_queryset(self):
        latest_audit = FiveSAudit.objects.filter(schedule=OuterRef('pk')).order_by('-id')

        qs = (
            FiveSSchedule.objects
            .select_related('template')
            .prefetch_related('plant', 'assignee')
            .annotate(
                has_audits=Exists(FiveSAudit.objects.filter(schedule=OuterRef('pk'))),
                has_open_audits=Exists(
                    FiveSAudit.objects.filter(schedule=OuterRef('pk')).exclude(status='CLOSED')
                ),
                latest_audit_status=Subquery(latest_audit.values('status')[:1]),
            )
        )

        search = self.request.GET.get('search', '').strip()
        status = self.request.GET.get('status', '').strip()

        if search:
            qs = qs.filter(
                Q(schedule_name__icontains=search) |
                Q(template__template_name__icontains=search) |
                Q(assignee__first_name__icontains=search) |
                Q(assignee__last_name__icontains=search)
            )

        if status == 'CLOSED':
            qs = qs.filter(latest_audit_status='CLOSED')
        elif status:
            qs = qs.filter(status=status)

        return qs.distinct().order_by('-created_at')


class ScheduleCreateView(LoginRequiredMixin, CreateView):
    model = FiveSSchedule
    form_class = FiveSScheduleForm
    template_name = 'five_s/schedule_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        self.object = form.save()

        plant_ids = self.request.POST.getlist('plants')
        zone_ids = self.request.POST.getlist('zones')
        loc_ids = self.request.POST.getlist('locations')
        sub_ids = self.request.POST.getlist('sublocations')
        user_ids = self.request.POST.getlist('assignees')

        if plant_ids: self.object.plant.set(plant_ids)
        if zone_ids: self.object.zone.set(zone_ids)
        if loc_ids: self.object.location.set(loc_ids)
        if sub_ids: self.object.sublocation.set(sub_ids)
        if user_ids: self.object.assignee.set(user_ids)

        created = generate_audits_for_schedule(self.object)

        if created:
            messages.success(
                self.request,
                f'Schedule "{self.object.schedule_name}" created and '
                f'{created} initial audit(s) assigned to users.'
            )
        else:
            messages.success(
                self.request,
                f'Schedule "{self.object.schedule_name}" created. '
                f'No audits generated (check if assignees are set).'
            )
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        context['title'] = 'Create 5S Schedule'
        context['all_plants'] = Plant.objects.filter(is_active=True)
        context['templates'] = FiveSTemplate.objects.filter(is_active=True)
        return context

    def get_success_url(self):
        return reverse('five_s:schedule_list')


class ScheduleUpdateView(LoginRequiredMixin, UpdateView):
    model = FiveSSchedule
    form_class = FiveSScheduleForm
    template_name = 'five_s/schedule_form.html'
    context_object_name = 'schedule'

    # ── LOCK: block opening the edit form for a paused/ended schedule ──
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        blocked = block_if_locked(
            request, self.object,
            redirect_to='five_s:schedule_detail',
            redirect_kwargs={'pk': self.object.pk},
            verb='Editing this schedule',
        )
        if blocked:
            return blocked
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        # ── LOCK: block saving edits to a paused/ended schedule ──
        blocked = block_if_locked(
            self.request, self.object,
            redirect_to='five_s:schedule_detail',
            redirect_kwargs={'pk': self.object.pk},
            verb='Editing this schedule',
        )
        if blocked:
            return blocked

        old_assignee_ids = set(self.object.assignee.values_list('id', flat=True))
        self.object = form.save()

        plant_ids = self.request.POST.getlist('plants')
        zone_ids = self.request.POST.getlist('zones')
        loc_ids = self.request.POST.getlist('locations')
        sub_ids = self.request.POST.getlist('sublocations')
        user_ids = [int(u) for u in self.request.POST.getlist('assignees') if u.isdigit()]

        moved = 0
        generated = 0
        with transaction.atomic():
            self.object.plant.set(plant_ids)
            self.object.zone.set(zone_ids)
            self.object.location.set(loc_ids)
            self.object.sublocation.set(sub_ids)
            self.object.assignee.set(user_ids)

            removed = old_assignee_ids - set(user_ids)
            added = [u for u in user_ids if u not in old_assignee_ids]
            if removed and added:
                new_user = User.objects.get(pk=added[0])
                moved = reassign_pending_audits(self.object, removed, new_user)

            if added:
                new_users = User.objects.filter(pk__in=added)
                generated = generate_audits_for_schedule(self.object, users=new_users)

        msg = f'Schedule "{self.object.schedule_name}" updated.'
        if moved:
            msg += f' {moved} pending audit(s) moved to the new assignee.'
        if generated:
            msg += f' {generated} new audit(s) created for added users.'
        messages.success(self.request, msg)
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Edit'
        context['title'] = f'Edit Schedule: {self.object.schedule_name}'
        context['all_plants'] = Plant.objects.filter(is_active=True)
        context['selected_plants'] = list(self.object.plant.values_list('id', flat=True))
        context['selected_zones'] = list(self.object.zone.values_list('id', flat=True))
        context['selected_locations'] = list(self.object.location.values_list('id', flat=True))
        context['selected_sublocations'] = list(self.object.sublocation.values_list('id', flat=True))
        context['selected_assignees'] = list(self.object.assignee.values_list('id', flat=True))
        return context

    def get_success_url(self):
        return reverse('five_s:schedule_list')


class ScheduleDetailView(LoginRequiredMixin, DetailView):
    model = FiveSSchedule
    template_name = 'five_s/schedule_detail.html'
    context_object_name = 'schedule'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        schedule = self.object
        context['audits'] = schedule.audits.select_related('user').order_by('-scheduled_date')

        tqs = (
            FiveSTemplateQuestion.objects
            .filter(template=schedule.template)
            .select_related('question')
        )

        raw_by_pillar = defaultdict(list)
        for tq in tqs:
            raw_by_pillar[tq.question.pillar].append(tq)

        by_pillar = {}
        for code, name in PILLAR_CHOICES:
            if code in raw_by_pillar:
                by_pillar[code] = raw_by_pillar[code]

        context['by_pillar'] = by_pillar
        context['all_users'] = User.objects.filter(is_active=True, is_active_employee=True)
        return context


class ScheduleTransferView(LoginRequiredMixin, View):
    def post(self, request, pk):
        schedule = get_object_or_404(FiveSSchedule, pk=pk)

        # ── LOCK: block transfers on paused/ended schedules ──
        blocked = block_if_locked(
            request, schedule,
            redirect_to='five_s:schedule_detail',
            redirect_kwargs={'pk': schedule.pk},
            verb='Transferring this schedule',
        )
        if blocked:
            return blocked

        new_id = request.POST.get('new_assignee')
        from_id = request.POST.get('from_assignee')

        if not new_id:
            messages.error(request, 'Please select a valid user.')
            return redirect('five_s:schedule_detail', pk=pk)

        new_user = get_object_or_404(User, pk=new_id, is_active=True)
        current_ids = list(schedule.assignee.values_list('id', flat=True))

        if current_ids == [new_user.pk]:
            messages.info(request, f'{new_user.get_full_name() or new_user.username} is already the assignee.')
            return redirect('five_s:schedule_detail', pk=pk)

        with transaction.atomic():
            if from_id and from_id.isdigit() and int(from_id) in current_ids:
                old_ids = [int(from_id)]
                schedule.assignee.remove(*old_ids)
                schedule.assignee.add(new_user)
            else:
                old_ids = current_ids
                schedule.assignee.set([new_user])

            moved = reassign_pending_audits(schedule, old_ids, new_user)

        messages.success(
            request,
            f'Schedule transferred to {new_user.get_full_name() or new_user.username}. '
            f'{moved} pending audit(s) moved to their My Inspections and removed from the previous user.'
        )
        return redirect('five_s:schedule_detail', pk=pk)


class ScheduleToggleStatusView(LoginRequiredMixin, View):
    def post(self, request, pk):
        schedule = get_object_or_404(FiveSSchedule, pk=pk)

        if schedule.status == 'ACTIVE':
            schedule.status = 'PAUSED'
            schedule.save(update_fields=['status'])
            messages.success(
                request,
                f'Schedule "{schedule.schedule_name}" paused. '
                f'Existing audits are untouched; no new audits will be '
                f'created until it is resumed.'
            )

        elif schedule.status == 'PAUSED':
            schedule.status = 'ACTIVE'
            schedule.save(update_fields=['status'])

            generated = generate_audits_for_schedule(schedule)

            msg = f'Schedule "{schedule.schedule_name}" resumed.'
            if generated:
                msg += f' {generated} audit(s) generated.'
            messages.success(request, msg)

        else:  # ENDED
            messages.error(request, 'This schedule has ended and cannot be resumed.')

        return redirect('five_s:schedule_detail', pk=pk)


# ===========================================================================
# STAGE 3: MY INSPECTIONS
# ===========================================================================

class MyInspectionsListView(LoginRequiredMixin, ListView):
    model = FiveSAudit
    template_name = 'five_s/my_inspections.html'
    context_object_name = 'page_obj'
    paginate_by = 15

    def get_queryset(self):
        qs = FiveSAudit.objects.filter(user=self.request.user).select_related('schedule', 'schedule__template').prefetch_related('schedule__plant').order_by('-scheduled_date')
        status = self.request.GET.get('status', '').strip()
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filters'] = {'status': self.request.GET.get('status', '').strip()}
        context['status_choices'] = FiveSAudit.STATUS_CHOICES
        user_audits = FiveSAudit.objects.filter(user=self.request.user)
        context['stats'] = {
            'pending': user_audits.filter(status__in=PENDING_AUDIT_STATUSES).count(),
            'submitted': user_audits.filter(status__in=SUBMITTED_AUDIT_STATUSES).count(),
            'overdue': user_audits.filter(status__in=PENDING_AUDIT_STATUSES, due_date__lt=timezone.now().date()).count(),
        }
        context['today'] = timezone.now().date()
        return context


class InspectionFormView(LoginRequiredMixin, View):
    template_name = 'five_s/inspection_form.html'

    def get_audit(self, pk):
        return get_object_or_404(
            FiveSAudit.objects.select_related('schedule', 'schedule__template'),
            pk=pk, user=self.request.user,
        )

    def get(self, request, pk):
        audit = self.get_audit(pk)

        # ── LOCK: block *starting* a new inspection when the schedule is paused/ended.
        # IN_PROGRESS audits are allowed to continue so users can finish what
        # they already started. If you want a hard freeze, remove the
        # `audit.status == 'SCHEDULED'` check below.
        if audit.status == 'SCHEDULED' and schedule_is_locked(audit.schedule):
            messages.error(
                request,
                f'Schedule "{audit.schedule.schedule_name}" is '
                f'{audit.schedule.get_status_display().lower()}. '
                f'Cannot start a new inspection until it is resumed.',
            )
            return redirect('five_s:my_inspections')

        if audit.status == 'SCHEDULED':
            audit.status = 'IN_PROGRESS'
            audit.started_at = timezone.now()
            audit.save()

        template = audit.schedule.template
        questions = FiveSTemplateQuestion.objects.filter(template=template).select_related('question').order_by('question__pillar', 'display_order')

        raw_by_pillar = defaultdict(list)
        for tq in questions:
            raw_by_pillar[tq.question.pillar].append(tq)

        by_pillar = {}
        for code, name in PILLAR_CHOICES:
            if code in raw_by_pillar:
                by_pillar[code] = raw_by_pillar[code]

        previous_audit = FiveSAudit.objects.filter(
            schedule=audit.schedule,
            status__in=['SUBMITTED', 'CLOSED', 'REVIEWED']
        ).exclude(pk=audit.pk).order_by('-created_at').first()

        repeat_findings = {}
        if previous_audit:
            prev_answers = AuditAnswer.objects.filter(audit=previous_audit, answer__in=['1', '2']).values_list('question_id', flat=True)
            for q_id in prev_answers:
                repeat_findings[q_id] = True

        return render(request, self.template_name, {
            'audit': audit,
            'by_pillar': by_pillar,
            'pillar_choices': dict(PILLAR_CHOICES),
            'repeat_findings': repeat_findings,
        })

    def post(self, request, pk):
        audit = self.get_audit(pk)

        # ── LOCK: block submitting when the schedule is paused/ended.
        # If you chose to allow finishing IN_PROGRESS audits, change this
        # to:  if audit.status == 'SCHEDULED' and schedule_is_locked(...)
        blocked = block_if_locked(
            request, audit.schedule,
            redirect_to='five_s:my_inspections',
            verb='Submitting this inspection',
        )
        if blocked:
            return blocked

        template = audit.schedule.template
        questions = (
            FiveSTemplateQuestion.objects
            .filter(template=template)
            .select_related('question')
        )

        SCORE_POINTS = {'1': 1, '2': 3, '3': 5, '4': 5, '5': 5, 'NA': 5}
        total_score_points = 0
        max_possible_points = 0

        errors = []
        validated_answers = []

        for tq in questions:
            q_id = tq.question.id
            raw_answer = request.POST.get(f'question_{q_id}')

            if not raw_answer:
                continue

            remarks = (request.POST.get(f'remarks_{q_id}') or '').strip()
            evidence = request.FILES.get(f'evidence_{q_id}')

            form = InspectionAnswerForm(
                data={'answer': raw_answer, 'remarks': remarks},
                files={'evidence': evidence},
                question=tq.question,
            )

            if not form.is_valid():
                for field, field_errors in form.errors.items():
                    for error in field_errors:
                        errors.append({
                            'question': tq.question,
                            'field': field,
                            'message': error,
                        })
            else:
                validated_answers.append({
                    'question': tq.question,
                    'answer': raw_answer,
                    'remarks': remarks,
                    'evidence': evidence,
                })

        if errors:
            for err in errors:
                messages.error(
                    request,
                    f"{err['question'].question_code}: {err['message']}"
                )

            submitted_data = {}
            for tq in questions:
                q_id = tq.question.id
                submitted_data[q_id] = {
                    'answer': request.POST.get(f'question_{q_id}', ''),
                    'remarks': request.POST.get(f'remarks_{q_id}', ''),
                }

            by_pillar = defaultdict(list)
            for tq in questions:
                by_pillar[tq.question.pillar].append(tq)

            previous_audit = FiveSAudit.objects.filter(
                schedule=audit.schedule,
                status__in=['SUBMITTED', 'CLOSED', 'REVIEWED']
            ).exclude(pk=audit.pk).order_by('-created_at').first()

            repeat_findings = {}
            if previous_audit:
                prev_answers = AuditAnswer.objects.filter(
                    audit=previous_audit, answer__in=['1', '2']
                ).values_list('question_id', flat=True)
                for q_id in prev_answers:
                    repeat_findings[q_id] = True

            return render(request, self.template_name, {
                'audit': audit,
                'by_pillar': dict(by_pillar),
                'pillar_choices': dict(PILLAR_CHOICES),
                'repeat_findings': repeat_findings,
                'submitted_data': submitted_data,
                'has_errors': True,
            })

        for item in validated_answers:
            defaults = {
                'answer': item['answer'],
                'remarks': item['remarks'] or None,
            }
            if item['evidence']:
                defaults['evidence'] = item['evidence']

            AuditAnswer.objects.update_or_create(
                audit=audit,
                question=item['question'],
                defaults=defaults,
            )

            total_score_points += SCORE_POINTS.get(item['answer'], 0)
            max_possible_points += 5

        if max_possible_points > 0:
            audit.overall_score = round(
                (total_score_points / max_possible_points) * 100, 2
            )

        signature_data = request.POST.get('signature_data')
        if signature_data:
            try:
                format_, imgstr = signature_data.split(';base64,')
                ext = format_.split('/')[-1]
                data = ContentFile(
                    base64.b64decode(imgstr),
                    name=f'sig_{audit.pk}.{ext}',
                )
                audit.inspector_signature = data
            except Exception:
                messages.warning(
                    request,
                    "Audit submitted, but the signature could not be saved."
                )

        audit.status = 'SUBMITTED'
        audit.submitted_at = timezone.now()
        audit.submitted_by = request.user
        audit.save()

        has_answers = AuditAnswer.objects.filter(audit=audit).exists()
        has_findings = AuditAnswer.objects.filter(audit=audit, answer__in=['1', '2']).exists()
        if has_answers and not has_findings:
            audit.status = 'CLOSED'
            audit.save(update_fields=['status'])

        messages.success(request, 'Audit submitted successfully!')
        return redirect('five_s:my_inspections')


# ===========================================================================
# AJAX ENDPOINTS
# ===========================================================================

class GetZonesView(LoginRequiredMixin, View):
    def get(self, request):
        plant_id = request.GET.get('plant_id')
        if not plant_id: return JsonResponse({'zones': []})
        zones = Zone.objects.filter(plant_id=plant_id, is_active=True).values('id', 'name')
        return JsonResponse({'zones': list(zones)})


class GetLocationsView(LoginRequiredMixin, View):
    def get(self, request):
        zone_id = request.GET.get('zone_id')
        if not zone_id: return JsonResponse({'locations': []})
        locations = Location.objects.filter(zone_id=zone_id, is_active=True).values('id', 'name')
        return JsonResponse({'locations': list(locations)})


class GetSublocationsView(LoginRequiredMixin, View):
    def get(self, request):
        location_id = request.GET.get('location_id')
        if not location_id: return JsonResponse({'sublocations': []})
        sublocations = SubLocation.objects.filter(location_id=location_id, is_active=True).values('id', 'name')
        return JsonResponse({'sublocations': list(sublocations)})


class GetUsersByPlantView(LoginRequiredMixin, View):
    def get(self, request):
        plant_id = request.GET.get('plant_id')
        if not plant_id: return JsonResponse({'users': []})
        users = User.objects.filter(plant_id=plant_id, is_active=True, is_active_employee=True).values('id', 'first_name', 'last_name', 'username')
        user_list = []
        for u in users:
            name = f"{u['first_name']} {u['last_name']}".strip()
            user_list.append({'id': u['id'], 'name': name or u['username']})
        return JsonResponse({'users': user_list})


# ===========================================================================
# STAGE 4: AUDIT DETAIL & CORRECTIVE ACTIONS
# ===========================================================================

class AuditDetailPageView(LoginRequiredMixin, DetailView):
    model = FiveSAudit
    template_name = 'five_s/audit_detail.html'
    context_object_name = 'audit'

    def get_queryset(self):
        return (
            FiveSAudit.objects
            .select_related('schedule', 'schedule__template', 'user', 'submitted_by')
            .prefetch_related(
                'schedule__plant', 'schedule__zone',
                'schedule__location', 'schedule__sublocation',
            )
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        audit = self.object

        # ── LOCK: block creating corrective actions when paused/ended ──
        blocked = block_if_locked(
            request, audit.schedule,
            redirect_to='five_s:audit_page',
            redirect_kwargs={'pk': audit.pk},
            verb='Creating a corrective action',
        )
        if blocked:
            return blocked

        question_id = request.POST.get('question_id')
        assigned_to_id = request.POST.get('assigned_to')
        remarks = request.POST.get('remarks')
        due_date = request.POST.get('due_date') or None

        if not question_id or not assigned_to_id or not remarks:
            messages.error(request, "Please fill all required fields.")
            return redirect('five_s:audit_page', pk=audit.pk)

        CorrectiveAction.objects.create(
            audit=audit,
            question_id=question_id,
            assigned_to_id=assigned_to_id,
            verifier=request.user,
            remarks=remarks,
            due_date=due_date,
            status='ASSIGNED',
            created_by=request.user
        )

        sync_audit_closure(audit)

        messages.success(request, "Corrective action created and assigned successfully.")
        return redirect('five_s:audit_page', pk=audit.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        audit = self.object

        plant = audit.schedule.plant.first()
        if plant:
            plant_users = User.objects.filter(plant=plant, is_active=True, is_active_employee=True)
        else:
            plant_users = User.objects.filter(is_active=True, is_active_employee=True)

        answers = list(
            audit.answers
            .select_related('question')
            .order_by('question__pillar', 'question__question_code')
        )

        for ans in answers:
            if ans.answer in ['1', '2', '3', '4', '5']:
                ans.selected_num = int(ans.answer)
            else:
                ans.selected_num = 0
            ans.score_value = {'1': 1, '2': 3, '3': 5, '4': 5, '5': 5, 'NA': 5}.get(ans.answer, 5)

        findings = [a for a in answers if a.selected_num in [1, 2]]

        pillar_scores = {}
        for code, name in PILLAR_CHOICES:
            pillar_scores[code] = {
                'name': name, 'earned': 0, 'max': 0, 'percentage': 0, 'has_questions': False
            }

        for ans in answers:
            pillar_code = ans.question.pillar
            if pillar_code in pillar_scores:
                pillar_scores[pillar_code]['earned'] += ans.score_value
                pillar_scores[pillar_code]['max'] += 5
                pillar_scores[pillar_code]['has_questions'] = True

        for code, data in pillar_scores.items():
            if data['max'] > 0:
                data['percentage'] = round((data['earned'] / data['max']) * 100, 1)

        # --- Existing 5S CorrectiveActions ---
        existing_actions = CorrectiveAction.objects.filter(audit=audit)
        actions_dict = {action.question_id: action for action in existing_actions}

        # --- CAPAs linked to findings (or schedule-wide) ---
        finding_ids = [str(a.id) for a in findings]
        capas_by_finding = get_capas_for_audit(audit, finding_answer_ids=finding_ids)

        # --- Attach action, capa, and images to each answer ---
        for ans in answers:
            ans.action = actions_dict.get(ans.question.id)
            ans.capa = capas_by_finding.get(str(ans.id))
            ans.before_image = ans.evidence if ans.evidence else None
            ans.after_image = (
                ans.action.completion_evidence
                if ans.action and ans.action.completion_evidence
                else None
            )
            ans.has_before_after = bool(ans.before_image and ans.after_image)

        # --- Repeat Finding Detection ---
        for ans in answers:
            if ans.selected_num in (1, 2):
                previous = (
                    AuditAnswer.objects
                    .filter(
                        question=ans.question,
                        answer__in=['1', '2'],
                        audit__id__lt=audit.id,
                    )
                    .select_related('audit', 'audit__schedule')
                    .order_by('-audit__id')
                    .first()
                )
                if previous:
                    ans.is_repeat = True
                    ans.repeat_info = {
                        'prev_audit_cycle': previous.audit.cycle_key,
                        'prev_audit_date': previous.audit.scheduled_date,
                        'prev_schedule_name': previous.audit.schedule.schedule_name,
                    }
                else:
                    ans.is_repeat = False
                    ans.repeat_info = None
            else:
                ans.is_repeat = False
                ans.repeat_info = None

        has_any_photos = any(a.before_image or a.after_image for a in findings)

        context.update({
            'answers': answers,
            'findings': findings,
            'total_questions': len(answers),
            'findings_count': len(findings),
            'pillar_scores': pillar_scores,
            'plant_users': plant_users,
            'actions_dict': actions_dict,
            'capas_by_finding': capas_by_finding,
            'has_any_photos': has_any_photos,
            'back_url': reverse('five_s:schedule_detail', kwargs={'pk': audit.schedule.pk}),
        })
        return context


class ActionDetailView(LoginRequiredMixin, DetailView):
    model = CorrectiveAction
    template_name = 'five_s/action_detail.html'
    context_object_name = 'action'

    def get_queryset(self):
        return CorrectiveAction.objects.select_related(
            'audit',
            'audit__schedule',
            'question',
            'assigned_to',
            'created_by',
            'approved_by'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        action = self.object

        try:
            audit_answer = AuditAnswer.objects.get(
                audit=action.audit,
                question=action.question
            )
        except AuditAnswer.DoesNotExist:
            audit_answer = None

        context['audit_answer'] = audit_answer
        context['before_image'] = audit_answer.evidence if audit_answer and audit_answer.evidence else None
        context['after_image'] = action.completion_evidence if action.completion_evidence else None
        context['has_before_after'] = bool(context['before_image'] and context['after_image'])

        return context


class MyActionsListView(LoginRequiredMixin, ListView):
    model = CorrectiveAction
    template_name = 'five_s/my_actions.html'
    context_object_name = 'actions'
    paginate_by = 15

    def get_queryset(self):
        return CorrectiveAction.objects.filter(assigned_to=self.request.user) \
            .select_related('audit', 'audit__schedule', 'question') \
            .order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Only the current page of rows matters for the banner check.
        context['has_locked_actions'] = any(
            action_is_locked(a) for a in context['actions']
        )
        return context


class ActionCompleteView(LoginRequiredMixin, View):
    template_name = 'five_s/action_complete.html'

    def get(self, request, pk):
        action = get_object_or_404(CorrectiveAction, pk=pk, assigned_to=request.user)

        # ── LOCK: block opening the completion form when paused/ended ──
        blocked = block_if_action_locked(
            request, action,
            redirect_to='five_s:my_actions',
            verb='Completing this action',
        )
        if blocked:
            return blocked

        audit_answer = AuditAnswer.objects.filter(audit=action.audit, question=action.question).first()
        return render(request, self.template_name, {
            'action': action,
            'audit_answer': audit_answer,
        })

    def post(self, request, pk):
        action = get_object_or_404(CorrectiveAction, pk=pk, assigned_to=request.user)

        # ── LOCK: block submitting completion when paused/ended ──
        blocked = block_if_action_locked(
            request, action,
            redirect_to='five_s:my_actions',
            verb='Completing this action',
        )
        if blocked:
            return blocked

        completion_date = request.POST.get('completion_date')
        completion_remarks = request.POST.get('completion_remarks')
        completion_evidence = request.FILES.get('completion_evidence')

        audit_answer = AuditAnswer.objects.filter(audit=action.audit, question=action.question).first()

        if not completion_remarks:
            messages.error(request, "Remarks are required.")
            return render(request, self.template_name, {
                'action': action,
                'audit_answer': audit_answer,
            })

        if audit_answer and audit_answer.evidence and not completion_evidence:
            messages.error(
                request,
                "Photo evidence is required to close this action "
                "(the inspector uploaded a 'before' photo)."
            )
            return render(request, self.template_name, {
                'action': action,
                'audit_answer': audit_answer,
            })

        action.completion_date = completion_date
        action.completion_remarks = completion_remarks
        if completion_evidence:
            action.completion_evidence = completion_evidence

        action.status = 'SUBMITTED'
        action.save()

        messages.success(request, "Action completed and sent for approval.")
        return redirect('five_s:my_actions')


class ActionApprovalView(LoginRequiredMixin, View):
    template_name = 'five_s/action_approval.html'

    def get(self, request, pk):
        action = get_object_or_404(CorrectiveAction, pk=pk)

        # ── LOCK: block opening the approval page when paused/ended ──
        blocked = block_if_action_locked(
            request, action,
            redirect_to='five_s:audit_page',
            redirect_kwargs={'pk': action.audit.pk},
            verb='Approving this action',
        )
        if blocked:
            return blocked

        form = ActionApprovalForm(instance=action)
        audit_answer = AuditAnswer.objects.filter(audit=action.audit, question=action.question).first()
        return render(request, self.template_name, {
            'action': action,
            'form': form,
            'audit_answer': audit_answer,
        })

    def post(self, request, pk):
        action = get_object_or_404(CorrectiveAction, pk=pk)

        # ── LOCK: block approving/rejecting when paused/ended ──
        blocked = block_if_action_locked(
            request, action,
            redirect_to='five_s:audit_page',
            redirect_kwargs={'pk': action.audit.pk},
            verb='Approving this action',
        )
        if blocked:
            return blocked

        form = ActionApprovalForm(request.POST, instance=action)

        if form.is_valid():
            decision = form.cleaned_data.get('decision')
            audit_closed = False

            with transaction.atomic():
                action = form.save(commit=False)

                if decision == 'approve':
                    action.status = 'CLOSED'
                    action.approved_by = request.user
                    action.approved_at = timezone.now()
                elif decision == 'reject':
                    action.status = 'REJECTED'
                action.save()
                audit_closed = sync_audit_closure(action.audit)

            if decision == 'approve':
                if audit_closed:
                    flash_once(
                        request,
                        "Action approved and closed. All findings are resolved, "
                        "so the audit has been closed."
                    )
                else:
                    flash_once(request, "Action approved and closed.")
            elif decision == 'reject':
                flash_once(request, "Action rejected. Assignee must rework.", messages.WARNING)

            return redirect('five_s:audit_page', pk=action.audit.pk)

        messages.error(request, "Please correct the errors below.")

        audit_answer = AuditAnswer.objects.filter(audit=action.audit, question=action.question).first()

        return render(request, self.template_name, {
            'action': action,
            'form': form,
            'audit_answer': audit_answer,
        })


class ActionSubmissionDetailView(LoginRequiredMixin, DetailView):
    model = CorrectiveAction
    template_name = 'five_s/action_submission_detail.html'
    context_object_name = 'action'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        action = self.object

        try:
            audit_answer = AuditAnswer.objects.get(
                audit=action.audit,
                question=action.question
            )
        except AuditAnswer.DoesNotExist:
            audit_answer = None

        context['audit_answer'] = audit_answer
        context['before_image'] = audit_answer.evidence if audit_answer else None
        context['after_image'] = action.completion_evidence
        context['has_before_after'] = bool(
            context['before_image'] and context['after_image']
        )
        return context


# ===========================================================================
# ANALYTICAL DASHBOARD
# ===========================================================================

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'five_s/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        plant_id = self.request.GET.get('plant')
        zone_id = self.request.GET.get('zone')
        days = int(self.request.GET.get('days', 90))
        cutoff_date = timezone.now().date() - timezone.timedelta(days=days)

        audits = FiveSAudit.objects.all()
        if plant_id:
            audits = audits.filter(schedule__plant__id=plant_id)
        if zone_id:
            audits = audits.filter(schedule__zone__id=zone_id)
        audits = audits.filter(created_at__date__gte=cutoff_date)

        actions = CorrectiveAction.objects.filter(audit__in=audits)

        total_audits = audits.count()
        avg_score = audits.filter(overall_score__isnull=False).aggregate(Avg('overall_score'))['overall_score__avg'] or 0
        total_actions = actions.count()
        pending_actions = actions.filter(status__in=['ASSIGNED', 'REJECTED', 'SUBMITTED']).count()

        closed_actions = actions.filter(status='CLOSED').count()
        completion_rate = round((closed_actions / total_actions) * 100, 1) if total_actions > 0 else 0

        trend_labels = []
        trend_data = []
        for i in range(5, -1, -1):
            month_date = timezone.now().date() - relativedelta(months=i)
            trend_labels.append(month_date.strftime('%b %Y'))
            month_audits = audits.filter(
                created_at__year=month_date.year,
                created_at__month=month_date.month,
                overall_score__isnull=False
            )
            avg = month_audits.aggregate(Avg('overall_score'))['overall_score__avg']
            trend_data.append(round(avg, 1) if avg else 0)

        findings_qs = AuditAnswer.objects.filter(audit__in=audits, answer__in=['1', '2'])
        loc_counts = {}
        for ans in findings_qs:
            for loc in ans.audit.schedule.location.all():
                loc_counts[loc.name] = loc_counts.get(loc.name, 0) + 1
        heatmap_data = [{'name': k, 'count': v} for k, v in sorted(loc_counts.items(), key=lambda item: item[1], reverse=True)[:6]]

        audit_status_data = [
            audits.filter(status='SCHEDULED').count(),
            audits.filter(status='IN_PROGRESS').count(),
            audits.filter(status='SUBMITTED').count(),
            audits.filter(status='CLOSED').count(),
        ]

        zone_audits = audits.values('schedule__zone__name').annotate(total=Count('id')).exclude(schedule__zone__name__isnull=True).order_by('-total')[:5]
        zone_labels = [z['schedule__zone__name'] for z in zone_audits]
        zone_data = [z['total'] for z in zone_audits]

        action_counts = {
            'assigned': actions.filter(status='ASSIGNED').count(),
            'submitted': actions.filter(status='SUBMITTED').count(),
            'closed': actions.filter(status='CLOSED').count(),
            'rejected': actions.filter(status='REJECTED').count(),
        }

        ANSWER_TO_SCORE = {'1': 1, '2': 3, '3': 5, '4': 5, '5': 5, 'NA': 5}
        pillar_data = []
        colors = {'SEIRI': '#ef4444', 'SEITON': '#3b82f6', 'SEISO': '#22c55e', 'SEIKETSU': '#f59e0b', 'SHITSUKE': '#8b5cf6'}

        for code, name in PILLAR_CHOICES:
            ans_qs = AuditAnswer.objects.filter(audit__in=audits, question__pillar=code)
            total_pts = sum([ANSWER_TO_SCORE.get(a.answer, 0) for a in ans_qs])
            max_pts = ans_qs.count() * 5
            score = round((total_pts / max_pts) * 100, 1) if max_pts > 0 else 0
            pillar_data.append({'name': name, 'score': score, 'color': colors.get(code, '#64748b')})

        context.update({
            'plants': Plant.objects.filter(is_active=True),
            'zones': Zone.objects.filter(is_active=True),
            'selected_plant': plant_id,
            'selected_zone': zone_id,
            'selected_days': days,

            'total_audits': total_audits,
            'avg_score': round(avg_score, 1),
            'total_actions': total_actions,
            'pending_actions': pending_actions,
            'completion_rate': completion_rate,

            'trend_labels': trend_labels,
            'trend_data': trend_data,
            'heatmap_data': heatmap_data,
            'audit_status_data': audit_status_data,
            'zone_labels': zone_labels,
            'zone_data': zone_data,
            'action_counts': action_counts,
            'pillar_data': pillar_data,
        })
        return context


# ===========================================================================
# ALL FINDINGS / ALL ACTIONS
# ===========================================================================

class AllFindingsListView(LoginRequiredMixin, ListView):
    model = AuditAnswer
    template_name = 'five_s/all_findings.html'
    context_object_name = 'findings'
    paginate_by = 15

    def get_queryset(self):
        qs = AuditAnswer.objects.filter(answer__in=['1', '2']).select_related(
            'audit__schedule',
            'question',
            'audit__schedule__template'
        ).prefetch_related('audit__schedule__plant', 'audit__schedule__zone')

        assigned_actions = CorrectiveAction.objects.filter(
            audit_id=OuterRef('audit_id'),
            question_id=OuterRef('question_id')
        )

        qs = qs.exclude(
            Q(id__in=Subquery(assigned_actions.values('id')))
        )

        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(question__question_text__icontains=search) |
                Q(question__question_code__icontains=search) |
                Q(audit__schedule__schedule_name__icontains=search)
            )

        plant_id = self.request.GET.get('plant', '').strip()
        if plant_id:
            qs = qs.filter(audit__schedule__plant__id=plant_id)

        zone_id = self.request.GET.get('zone', '').strip()
        if zone_id:
            qs = qs.filter(audit__schedule__zone__id=zone_id)

        return qs.order_by('-audit__created_at')


class AllActionsListView(LoginRequiredMixin, ListView):
    model = CorrectiveAction
    template_name = 'five_s/all_actions.html'
    context_object_name = 'actions'
    paginate_by = 15

    def get_queryset(self):
        qs = CorrectiveAction.objects.select_related(
            'audit',
            'audit__schedule',
            'question',
            'assigned_to'
        ).prefetch_related('audit__schedule__plant').order_by('-created_at')

        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(question__question_text__icontains=search) |
                Q(question__question_code__icontains=search) |
                Q(audit__schedule__schedule_name__icontains=search)
            )

        status = self.request.GET.get('status', '').strip()
        if status:
            qs = qs.filter(status=status)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filters'] = {
            'search': self.request.GET.get('search', '').strip(),
            'status': self.request.GET.get('status', '').strip(),
        }
        context['status_choices'] = CorrectiveAction.STATUS_CHOICES
        context['total_actions'] = self.get_queryset().count()
        return context


# ===========================================================================
# AREA SCORECARDS (Grouped by Actual Location)
# ===========================================================================

PILLAR_COLORS = {
    'SEIRI':    {'color': '#ef4444', 'label': 'Sort'},
    'SEITON':   {'color': '#3b82f6', 'label': 'Set in Order'},
    'SEISO':    {'color': '#22c55e', 'label': 'Shine'},
    'SEIKETSU': {'color': '#f59e0b', 'label': 'Standardize'},
    'SHITSUKE': {'color': '#8b5cf6', 'label': 'Sustain'},
}

ANSWER_TO_SCORE = {'1': 1, '2': 3, '3': 5, '4': 5, '5': 5, 'NA': 5}


def _color_for_score(score):
    if score is None: return 'score-muted'
    if score >= 80: return 'score-green'
    if score >= 60: return 'score-amber'
    return 'score-red'


class AreaScorecardView(LoginRequiredMixin, TemplateView):
    template_name = 'five_s/area_scorecards.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        days = int(self.request.GET.get('days', 90))
        area_filter = self.request.GET.get('area', '').strip()
        cutoff = timezone.now().date() - relativedelta(days=days)

        answers = (
            AuditAnswer.objects
            .filter(
                audit__status__in=['SUBMITTED', 'REVIEWED', 'CLOSED'],
                audit__scheduled_date__gte=cutoff
            )
            .select_related('audit', 'question', 'audit__schedule')
            .prefetch_related(
                'audit__schedule__location',
                'audit__schedule__location__zone',
                'audit__schedule__location__zone__plant'
            )
        )

        location_map = {}

        for ans in answers:
            schedule = ans.audit.schedule
            points = ANSWER_TO_SCORE.get(ans.answer, 0)
            pillar = ans.question.pillar

            for loc in schedule.location.all():
                if loc.id not in location_map:
                    zone_name = loc.zone.name if loc.zone else 'Unassigned'
                    plant_name = loc.zone.plant.name if (loc.zone and loc.zone.plant) else '—'

                    location_map[loc.id] = {
                        'id': loc.id,
                        'name': loc.name,
                        'type': zone_name,
                        'plant': plant_name,
                        'pillar_scores': {code: {'earned': 0, 'max': 0} for code in PILLAR_COLORS},
                        'audit_ids': set(),
                    }

                entry = location_map[loc.id]
                if pillar in entry['pillar_scores']:
                    entry['pillar_scores'][pillar]['earned'] += points
                    entry['pillar_scores'][pillar]['max'] += 5
                entry['audit_ids'].add(ans.audit_id)

        scorecards = []
        for loc_id, entry in location_map.items():
            pillar_pct = {}
            total_earned = 0
            total_max = 0

            for code in PILLAR_COLORS:
                p = entry['pillar_scores'][code]
                if p['max'] > 0:
                    pct = round((p['earned'] / p['max']) * 100, 0)
                    if pct == 0:
                        pillar_pct[code] = {'value': None, 'color_class': 'score-muted'}
                    else:
                        pillar_pct[code] = {'value': pct, 'color_class': _color_for_score(pct)}
                    total_earned += p['earned']
                    total_max += p['max']
                else:
                    pillar_pct[code] = {'value': None, 'color_class': 'score-muted'}

            overall = round((total_earned / total_max) * 100, 0) if total_max > 0 else None
            if overall == 0:
                overall = None

            scorecards.append({
                'name': entry['name'],
                'type': entry['type'],
                'plant': entry['plant'],
                'audit_count': len(entry['audit_ids']),
                'pillar_scores': pillar_pct,
                'overall': {'value': overall, 'color_class': _color_for_score(overall)},
            })

        if area_filter:
            q = area_filter.lower()
            scorecards = [
                s for s in scorecards
                if q in s['name'].lower() or q in s['plant'].lower() or q in s['type'].lower()
            ]

        scorecards.sort(
            key=lambda s: s['overall']['value'] if s['overall']['value'] is not None else -1,
            reverse=True
        )

        unique_areas = sorted(list(set(s['type'] for s in scorecards if s['type'])))

        total_audits = sum(s['audit_count'] for s in scorecards)
        scored_overall = [s['overall']['value'] for s in scorecards if s['overall']['value'] is not None]
        avg_overall = round(sum(scored_overall) / len(scored_overall), 0) if scored_overall else 0

        context.update({
            'scorecards': scorecards,
            'unique_areas': unique_areas,
            'pillar_meta': PILLAR_COLORS,
            'pillar_order': ['SEIRI', 'SEITON', 'SEISO', 'SEIKETSU', 'SHITSUKE'],
            'days': days,
            'area_filter': area_filter,
            'total_areas': len(scorecards),
            'total_audits': total_audits,
            'avg_overall': avg_overall,
        })

        return context


# ===========================================================================
# PDF REPORTS
# ===========================================================================

class ScheduleReportView(LoginRequiredMixin, View):
    def get(self, request, pk):
        schedule = get_object_or_404(
            FiveSSchedule.objects
            .select_related('template', 'created_by')
            .prefetch_related('plant', 'zone', 'location', 'sublocation', 'assignee'),
            pk=pk,
        )

        if not is_schedule_closed(schedule):
            messages.warning(
                request,
                'The report is available only after all audits of this schedule are closed.'
            )
            return redirect('five_s:schedule_list')

        return generate_five_s_schedule_report_pdf(schedule)


class AuditPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        audit = get_object_or_404(
            FiveSAudit.objects
            .select_related('schedule', 'schedule__template', 'user', 'submitted_by')
            .prefetch_related('schedule__plant', 'schedule__zone',
                              'schedule__location', 'schedule__sublocation'),
            pk=pk,
        )
        capas_by_finding = get_capas_for_audit(audit)
        return generate_five_s_audit_pdf(audit, capas_by_finding=capas_by_finding)