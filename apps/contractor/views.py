from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .pdf_generators import (
    generate_contractor_pdf,
    generate_work_order_pdf,
    generate_training_signoff_pdf,
    generate_inspection_pdf,
    generate_contractor_logbook_pdf,
    generate_performance_pdf,
    generate_onboarding_pdf,
)
from django.utils.html import strip_tags
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
)
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.contrib.auth import get_user_model

# Standard library imports
import secrets
import string
import json
import logging
from datetime import datetime, date, timedelta

# Apps imports
from apps.notifications.services import NotificationService
from apps.organizations.models import Plant, Zone, Location, SubLocation, Department
from apps.toolbox_talk.models import ToolboxTalkSessionPlan

# Local imports
from .models import (
    Contractor,
    OnboardingRequest,
    OnboardingDocumentRequirement,
    DocumentType,
    PreQualificationQuestion,
    ContractorPortalUser,
    ContractorAssignment,
    WorkOrder,
    TrainingSignOff,
    ContractorInspection,
    ContractorInspectionQuestion,
    ContractorInspectionResponse,
    ContractorPerformanceMetric,
    PerformanceWeightConfig,
    ContractorReport,
    ContractorDashboardSnapshot,
    ContractorPreQualification,
)
from .forms import (
    ContractorForm,
    WorkOrderForm,
    WorkOrderStatusForm,
    TrainingSignOffForm,
    ContractorInspectionForm,
    ContractorInspectionResponseForm,
)
from .services.performance_service import (
    ContractorPerformanceService,
    BulkPerformanceCalculator,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ==========================================================
# ADMIN REQUIRED MIXIN
# ==========================================================

class AdminRequiredMixin(UserPassesTestMixin):
    """
    Restricts view access to Admins only (superuser or Role.name == 'ADMIN').
    """
    def test_func(self):
        user = self.request.user
        return user.is_superuser or getattr(user, 'is_admin_user', False)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access this page. Admin access only.")
        return redirect('contractor:workorder_list')


# ==========================================================
# CONTRACTOR CRUD VIEWS
# ==========================================================

class ContractorListView(LoginRequiredMixin, ListView):
    """
    Display searchable and filterable contractor listing.
    """
    model = Contractor
    template_name = 'contractor/contractor_list.html'
    context_object_name = 'contractors'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')

        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(contractor_code__icontains=search_query) |
                Q(contractor_name__icontains=search_query) |
                Q(contact_person__icontains=search_query) |
                Q(mobile__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        if self.request.GET.get('contractor_type'):
            queryset = queryset.filter(
                contractor_type=self.request.GET.get('contractor_type')
            )

        if self.request.GET.get('work_category'):
            queryset = queryset.filter(
                work_category=self.request.GET.get('work_category')
            )

        if self.request.GET.get('status') == 'active':
            queryset = queryset.filter(is_active=True)
        elif self.request.GET.get('status') == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['contractor_type_choices'] = Contractor.CONTRACTOR_TYPE_CHOICES
        context['work_category_choices'] = Contractor.WORK_CATEGORY_CHOICES
        context['status_choices'] = [('active', 'Active'), ('inactive', 'Inactive')]

        context['search_query'] = self.request.GET.get('search', '')
        context['selected_type'] = self.request.GET.get('contractor_type', '')
        context['selected_work_category'] = self.request.GET.get('work_category', '')
        context['selected_status'] = self.request.GET.get('status', '')

        context['total_contractors'] = Contractor.objects.count()
        context['active_contractors'] = Contractor.objects.filter(is_active=True).count()
        context['inactive_contractors'] = Contractor.objects.filter(is_active=False).count()
        context['contractor_types_count'] = len(Contractor.CONTRACTOR_TYPE_CHOICES)

        return context


class ContractorCreateView(LoginRequiredMixin, CreateView):
    """
    Add new contractor with structured form.
    """
    model = Contractor
    form_class = ContractorForm
    template_name = 'contractor/contractor_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_mode'] = 'add'
        context['title'] = 'Add Contractor'
        return context

    def form_valid(self, form):
        contractor = form.save(commit=False)
        contractor.created_by = self.request.user
        contractor.save()
        messages.success(self.request, f'Contractor "{contractor.contractor_name}" added successfully!')

        if 'save_draft' in self.request.POST:
            messages.info(self.request, 'Contractor saved as draft.')
            return redirect('contractor:contractor_detail', pk=contractor.pk)
        elif 'submit_onboarding' in self.request.POST:
            messages.info(self.request, 'Contractor submitted for onboarding process.')
            return redirect('contractor:contractor_list')

        return redirect('contractor:contractor_list')

    def form_invalid(self, form):
        print("Form errors:", form.errors)
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class ContractorDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed contractor profile.
    """
    model = Contractor
    template_name = 'contractor/contractor_detail.html'
    context_object_name = 'contractor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contractor = self.get_object()

        context['can_edit'] = (
            self.request.user.has_perm('contractor.change_contractor') or
            self.request.user.is_superuser
        )
        context['can_delete'] = (
            self.request.user.has_perm('contractor.delete_contractor') or
            self.request.user.is_superuser
        )

        return context


class ContractorUpdateView(LoginRequiredMixin, UpdateView):
    """
    Edit contractor details.
    """
    model = Contractor
    form_class = ContractorForm
    template_name = 'contractor/contractor_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_mode'] = 'edit'
        context['title'] = 'Edit Contractor'
        context['contractor'] = self.get_object()
        return context

    def form_valid(self, form):
        contractor = form.save()
        messages.success(self.request, f'Contractor "{contractor.contractor_name}" updated successfully!')
        return redirect('contractor:contractor_detail', pk=contractor.pk)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class ContractorDeactivateView(LoginRequiredMixin, View):
    """
    Deactivate a contractor (set is_active=False).
    """
    def post(self, request, *args, **kwargs):
        contractor = get_object_or_404(Contractor, pk=kwargs.get('pk'))
        contractor.is_active = False
        contractor.save()
        messages.warning(request, f'Contractor "{contractor.contractor_name}" has been deactivated.')
        next_url = request.POST.get('next', reverse('contractor:contractor_list'))
        return redirect(next_url)


# ==========================================================
# GENERATE CONTRACTOR PASSWORD
# ==========================================================

def generate_contractor_password(length=10):
    """
    Generate a secure temporary password for Contractor Portal users.
    """
    characters = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(
        secrets.choice(characters)
        for _ in range(length)
    )


# ==========================================================
# ONBOARDING VIEWS
# ==========================================================

class ContractorOnboardingView(LoginRequiredMixin, View):
    """
    Contractor onboarding form with pre-qualification and document checklists.
    """
    template_name = 'contractor/contractor_onboarding_form.html'

    def get(self, request):
        contractors = Contractor.objects.filter(is_active=True).order_by('contractor_name')
        prequal_questions = PreQualificationQuestion.objects.filter(is_active=True).order_by('sequence')
        documents = DocumentType.objects.filter(is_active=True).order_by('name')

        context = {
            'contractors': contractors,
            'prequal_questions': prequal_questions,
            'documents': documents,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        contractor_id = request.POST.get('contractor')
        selected_questions = request.POST.getlist('prequal_questions')
        selected_documents = request.POST.getlist('documents')
        notes = request.POST.get('notes', '').strip()

        portal_credentials = []

        if not contractor_id:
            messages.error(request, "Please select a contractor.")
            return redirect('contractor:contractor_onboarding')

        contractor = get_object_or_404(Contractor, pk=contractor_id)

        if not selected_questions:
            messages.error(request, "Please select at least one pre-qualification question.")
            return redirect('contractor:contractor_onboarding')

        if not selected_documents:
            messages.error(request, "Please select at least one document requirement.")
            return redirect('contractor:contractor_onboarding')

        contact_name = contractor.contact_person
        contact_email = (contractor.email or '').strip().lower()

        ehs_name = contractor.ehs_officer_name
        ehs_email = (contractor.ehs_email or '').strip().lower()

        if not contact_email and not ehs_email:
            messages.error(
                request,
                "Contractor Contact Person and EHS Officer email are missing."
            )
            return redirect('contractor:contractor_onboarding')

        existing_onboarding = OnboardingRequest.objects.filter(
            contractor=contractor,
            status__in=['DRAFT', 'PENDING']
        ).first()

        if existing_onboarding:
            messages.warning(
                request,
                "An active onboarding request already exists for this contractor."
            )
            return redirect(
                'contractor:onboarding_detail',
                pk=existing_onboarding.pk
            )

        prequal_questions_list = PreQualificationQuestion.objects.filter(
            id__in=selected_questions,
            is_active=True
        ).order_by('sequence', 'id')

        document_types = DocumentType.objects.filter(
            id__in=selected_documents,
            is_active=True
        ).order_by('name')

        internal_ehs_officer = None
        if ehs_email:
            internal_ehs_officer = User.objects.filter(
                email__iexact=ehs_email
            ).first()

        onboarding = OnboardingRequest.objects.create(
            contractor=contractor,
            ehs_officer=internal_ehs_officer,
            pre_qualification_answers={
                str(question.id): False
                for question in prequal_questions_list
            },
            notes=notes,
            status='DRAFT',
            submitted_by=request.user,
            submitted_at=None
        )

        for doc_type in document_types:
            OnboardingDocumentRequirement.objects.create(
                onboarding=onboarding,
                document_type=doc_type,
                is_required=doc_type.is_mandatory,
                status='PENDING'
            )

        if contact_email:
            portal_user = ContractorPortalUser.objects.filter(
                contractor=contractor,
                email__iexact=contact_email
            ).first()

            temporary_password = generate_contractor_password()

            if portal_user:
                portal_user.name = contact_name
                portal_user.user_type = 'CONTACT_PERSON'
                portal_user.is_active = True
                portal_user.set_password(temporary_password)
                portal_user.save(
                    update_fields=[
                        'name',
                        'user_type',
                        'is_active',
                        'password',
                        'updated_at'
                    ]
                )
            else:
                portal_user = ContractorPortalUser.objects.create(
                    contractor=contractor,
                    name=contact_name,
                    email=contact_email,
                    user_type='CONTACT_PERSON',
                    is_active=True
                )
                portal_user.set_password(temporary_password)
                portal_user.save(update_fields=['password'])

            assignment = ContractorAssignment.objects.create(
                onboarding=onboarding,
                portal_user=portal_user,
                status='ACTIVE',
                is_access_active=True
            )

            portal_credentials.append({
                'portal_user': portal_user,
                'assignment': assignment,
                'password': temporary_password,
                'user_type': 'CONTACT_PERSON'
            })

        if ehs_email:
            existing_cred = None
            if ehs_email == contact_email:
                existing_cred = next(
                    (item for item in portal_credentials if item['portal_user'].email.lower() == ehs_email),
                    None
                )

            if existing_cred:
                portal_user = existing_cred['portal_user']
                temporary_password = existing_cred['password']
            else:
                portal_user = ContractorPortalUser.objects.filter(
                    contractor=contractor,
                    email__iexact=ehs_email
                ).first()
                temporary_password = generate_contractor_password()

                if portal_user:
                    portal_user.name = ehs_name
                    portal_user.user_type = 'EHS_OFFICER'
                    portal_user.is_active = True
                    portal_user.set_password(temporary_password)
                    portal_user.save(
                        update_fields=[
                            'name',
                            'user_type',
                            'is_active',
                            'password',
                            'updated_at'
                        ]
                    )
                else:
                    portal_user = ContractorPortalUser.objects.create(
                        contractor=contractor,
                        name=ehs_name,
                        email=ehs_email,
                        user_type='EHS_OFFICER',
                        is_active=True
                    )
                    portal_user.set_password(temporary_password)
                    portal_user.save(update_fields=['password'])

                assignment = ContractorAssignment.objects.create(
                    onboarding=onboarding,
                    portal_user=portal_user,
                    status='ACTIVE',
                    is_access_active=True
                )

                portal_credentials.append({
                    'portal_user': portal_user,
                    'assignment': assignment,
                    'password': temporary_password,
                    'user_type': 'EHS_OFFICER'
                })

        prequal_for_email = [
            {
                'question': q.question,
                'question_type': q.get_question_type_display(),
                'answer': False
            }
            for q in prequal_questions_list
        ]

        doc_requirements = onboarding.document_requirements.select_related('document_type').all()

        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        site_url = site_url.rstrip('/')

        login_path = reverse('contractor:portal_login')

        emails_sent = 0
        emails_failed = 0

        for credential in portal_credentials:
            portal_user = credential['portal_user']
            assignment = credential['assignment']
            temporary_password = credential['password']

            login_url = f"{site_url}{login_path}?assignment={assignment.access_token}"

            if portal_user.user_type == 'EHS_OFFICER':
                to_email = ehs_email
                cc_email = contact_email if contact_email and contact_email != ehs_email else None
            else:
                to_email = contact_email
                cc_email = None

            email_sent = NotificationService.send_contractor_onboarding_email(
                portal_user=portal_user,
                assignment=assignment,
                temporary_password=temporary_password,
                login_url=login_url,
                cc_email=cc_email,
                prequal_questions=prequal_for_email,
                document_requirements=doc_requirements
            )

            if email_sent:
                emails_sent += 1
            else:
                emails_failed += 1

        if emails_failed == 0:
            messages.success(
                request,
                f"Contractor onboarding created successfully. "
                f"{emails_sent} portal email(s) sent."
            )
        else:
            messages.warning(
                request,
                f"Contractor onboarding created successfully, "
                f"but {emails_failed} portal email(s) could not be sent."
            )

        return redirect(
            'contractor:onboarding_detail',
            pk=onboarding.pk
        )


class OnboardingListView(LoginRequiredMixin, ListView):
    """
    Display list of all onboarding requests.
    """
    model = OnboardingRequest
    template_name = 'contractor/onboarding_list.html'
    context_object_name = 'onboarding_requests'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(contractor__contractor_name__icontains=search) |
                Q(contractor__contractor_code__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = OnboardingRequest.STATUS_CHOICES
        context['selected_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context


class OnboardingDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed view of an onboarding request.
    """
    model = OnboardingRequest
    template_name = 'contractor/onboarding_detail.html'
    context_object_name = 'onboarding'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        onboarding = self.get_object()

        document_requirements = []
        docs = onboarding.document_requirements.select_related('document_type').all()

        for doc in docs:
            document_requirements.append({
                'document_type': doc.document_type,
                'document': doc,
                'status': doc.status,
                'is_required': doc.is_required,
                'document_file': doc.document_file,
                'comments': doc.comments or '',
                'get_status_display': doc.get_status_display(),
                'id': doc.id,
            })
        context['document_requirements'] = document_requirements

        prequal_questions = []

        if onboarding.pre_qualification_answers:
            for q_id, answer in onboarding.pre_qualification_answers.items():
                try:
                    question = PreQualificationQuestion.objects.get(id=int(q_id))

                    prequal_questions.append({
                        'question': question,
                        'answer': answer if not isinstance(answer, bool) else None,
                        'is_answered': bool(answer and str(answer).strip()) if not isinstance(answer, bool) else (answer is not None),
                    })
                except (PreQualificationQuestion.DoesNotExist, ValueError):
                    pass

        context['prequal_questions'] = prequal_questions

        context['can_approve'] = (
            self.request.user == onboarding.ehs_officer or
            self.request.user.is_superuser
        )
        context['can_delete'] = (
            self.request.user.has_perm('contractor.delete_onboardingrequest') or
            self.request.user.is_superuser
        )

        context['status_choices'] = OnboardingRequest.STATUS_CHOICES
        context['selected_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('search', '')

        return context


class OnboardingReviewView(LoginRequiredMixin, View):
    """
    View for EHS officer to review, approve, or reject onboarding.
    """
    template_name = 'contractor/onboarding_review.html'

    def get(self, request, *args, **kwargs):
        onboarding_id = kwargs.get('pk')
        onboarding = get_object_or_404(OnboardingRequest, pk=onboarding_id)

        questions_with_answers = []
        if onboarding.pre_qualification_answers:
            for q_id, answer in onboarding.pre_qualification_answers.items():
                try:
                    question = PreQualificationQuestion.objects.get(id=int(q_id))
                    is_answered = bool(answer and str(answer).strip()) if not isinstance(answer, bool) else (answer is not None)

                    remark = ''
                    if hasattr(onboarding, 'question_remarks') and onboarding.question_remarks:
                        remark = onboarding.question_remarks.get(str(q_id), '')

                    questions_with_answers.append({
                        'question': question,
                        'answer': answer if not isinstance(answer, bool) else '',
                        'is_answered': is_answered,
                        'remark': remark,
                    })
                except (PreQualificationQuestion.DoesNotExist, ValueError):
                    pass

        document_requirements = onboarding.document_requirements.select_related('document_type').all()

        context = {
            'onboarding': onboarding,
            'contractor': onboarding.contractor,
            'questions_with_answers': questions_with_answers,
            'document_requirements': document_requirements,
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        onboarding_id = kwargs.get('pk')
        onboarding = get_object_or_404(OnboardingRequest, pk=onboarding_id)

        action = request.POST.get('action')
        rejection_reason = request.POST.get('rejection_reason', '').strip()

        if not hasattr(onboarding, 'question_remarks') or onboarding.question_remarks is None:
            onboarding.question_remarks = {}

        for key, value in request.POST.items():
            if key.startswith('question_remark_'):
                question_id = key.replace('question_remark_', '')
                if question_id.isdigit():
                    onboarding.question_remarks[question_id] = value.strip()

        for key, value in request.POST.items():
            if key.startswith('document_remark_'):
                doc_id = key.replace('document_remark_', '')
                if doc_id.isdigit():
                    try:
                        doc = OnboardingDocumentRequirement.objects.get(id=doc_id)
                        doc.comments = value.strip()
                        doc.save()
                    except OnboardingDocumentRequirement.DoesNotExist:
                        pass

        if action == 'approve':
            onboarding.status = 'APPROVED'
            onboarding.approved_by = request.user
            onboarding.approved_at = timezone.now()
            onboarding.save()

            self.send_approval_email(onboarding)

            messages.success(request, f'Onboarding for "{onboarding.contractor.contractor_name}" has been approved!')
            return redirect('contractor:onboarding_detail', pk=onboarding.pk)

        elif action == 'reject':
            onboarding.status = 'REJECTED'
            onboarding.rejection_reason = rejection_reason
            onboarding.save()

            self.send_rejection_email(onboarding)

            messages.warning(request, f'Onboarding for "{onboarding.contractor.contractor_name}" has been rejected.')
            return redirect('contractor:onboarding_detail', pk=onboarding.pk)

        return redirect('contractor:onboarding_detail', pk=onboarding.pk)

    def send_approval_email(self, onboarding):
        contractor = onboarding.contractor
        portal_users = ContractorPortalUser.objects.filter(contractor=contractor, is_active=True)

        for portal_user in portal_users:
            try:
                NotificationService.send_contractor_onboarding_approved_email(
                    portal_user=portal_user,
                    contractor=contractor,
                    approved_by=onboarding.approved_by,
                    approved_at=onboarding.approved_at
                )
            except Exception as e:
                logger.error(f"Error sending approval email to {portal_user.email}: {e}")

    def send_rejection_email(self, onboarding):
        contractor = onboarding.contractor
        portal_users = ContractorPortalUser.objects.filter(contractor=contractor, is_active=True)

        for portal_user in portal_users:
            try:
                NotificationService.send_contractor_onboarding_rejected_email(
                    portal_user=portal_user,
                    contractor=contractor,
                    rejected_at=timezone.now(),
                    rejection_reason=onboarding.rejection_reason
                )
            except Exception as e:
                logger.error(f"Error sending rejection email to {portal_user.email}: {e}")


class OnboardingApproveView(LoginRequiredMixin, View):
    """
    Approve an onboarding request.
    """
    def post(self, request, *args, **kwargs):
        onboarding = get_object_or_404(OnboardingRequest, pk=kwargs.get('pk'))

        if request.user != onboarding.ehs_officer and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to approve this request.')
            return redirect('contractor:onboarding_detail', pk=onboarding.pk)

        onboarding.status = 'APPROVED'
        onboarding.approved_by = request.user
        onboarding.approved_at = timezone.now()
        onboarding.save()

        messages.success(request, f'Onboarding request for "{onboarding.contractor.contractor_name}" has been approved.')
        return redirect('contractor:onboarding_detail', pk=onboarding.pk)


class OnboardingRejectView(LoginRequiredMixin, View):
    """
    Reject an onboarding request.
    """
    def post(self, request, *args, **kwargs):
        onboarding = get_object_or_404(OnboardingRequest, pk=kwargs.get('pk'))

        if request.user != onboarding.ehs_officer and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to reject this request.')
            return redirect('contractor:onboarding_detail', pk=onboarding.pk)

        rejection_reason = request.POST.get('rejection_reason', '')

        onboarding.status = 'REJECTED'
        onboarding.rejection_reason = rejection_reason
        onboarding.save()

        portal_users = ContractorPortalUser.objects.filter(contractor=onboarding.contractor, is_active=True)
        for portal_user in portal_users:
            try:
                NotificationService.send_contractor_onboarding_rejected_email(
                    portal_user=portal_user,
                    contractor=onboarding.contractor,
                    rejected_at=timezone.now(),
                    rejection_reason=rejection_reason
                )
            except Exception as e:
                logger.error(f"Error sending rejection email to {portal_user.email}: {e}")

        messages.warning(request, f'Onboarding request for "{onboarding.contractor.contractor_name}" has been rejected.')
        return redirect('contractor:onboarding_detail', pk=onboarding.pk)


# ==========================================================
# ONBOARDING DELETE VIEWS
# ==========================================================

class OnboardingDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = OnboardingRequest
    template_name = 'contractor/onboarding_confirm_delete.html'
    context_object_name = 'onboarding'
    permission_required = 'contractor.delete_onboardingrequest'

    def get_success_url(self):
        return reverse_lazy('contractor:onboarding_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        contractor_name = self.object.contractor.contractor_name

        with transaction.atomic():
            self.object.document_requirements.all().delete()
            self.object.assignments.all().delete()
            response = super().delete(request, *args, **kwargs)

        messages.success(
            request,
            f'Onboarding request for "{contractor_name}" has been deleted successfully.'
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Delete Onboarding Request'
        context['warning_message'] = (
            'This action cannot be undone. All associated documents, '
            'portal users, and assignments will also be deleted.'
        )
        context['document_count'] = self.object.document_requirements.count()
        context['assignment_count'] = self.object.assignments.count()
        return context


class OnboardingBulkDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'contractor.delete_onboardingrequest'

    def post(self, request, *args, **kwargs):
        onboarding_ids = request.POST.getlist('onboarding_ids')

        if not onboarding_ids:
            messages.error(request, 'No onboarding requests selected for deletion.')
            return redirect('contractor:onboarding_list')

        onboarding_requests = OnboardingRequest.objects.filter(id__in=onboarding_ids)
        count = onboarding_requests.count()

        if count == 0:
            messages.error(request, 'No valid onboarding requests found.')
            return redirect('contractor:onboarding_list')

        contractor_names = list(onboarding_requests.values_list(
            'contractor__contractor_name', flat=True
        ))

        with transaction.atomic():
            for onboarding in onboarding_requests:
                onboarding.document_requirements.all().delete()
                onboarding.assignments.all().delete()
            onboarding_requests.delete()

        messages.success(
            request,
            f'Successfully deleted {count} onboarding request(s): {", ".join(contractor_names[:5])}'
            + (f' and {count - 5} more...' if count > 5 else '')
        )

        return redirect('contractor:onboarding_list')


class OnboardingSoftDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        onboarding = get_object_or_404(OnboardingRequest, pk=kwargs.get('pk'))

        if not request.user.has_perm('contractor.change_onboardingrequest') and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to archive this request.')
            return redirect('contractor:onboarding_detail', pk=onboarding.pk)

        onboarding.status = 'ARCHIVED'
        onboarding.save()

        messages.success(
            request,
            f'Onboarding request for "{onboarding.contractor.contractor_name}" has been archived.'
        )

        return redirect('contractor:onboarding_list')


# ==========================================================
# DOCUMENT UPLOAD/VERIFY VIEWS
# ==========================================================

class DocumentUploadView(View):
    def post(self, request, *args, **kwargs):
        requirement_id = kwargs.get('pk')

        try:
            requirement = OnboardingDocumentRequirement.objects.get(pk=requirement_id)
        except OnboardingDocumentRequirement.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Document requirement not found'}, status=404)

        portal_user_id = request.session.get('contractor_portal_user_id')
        assignment_id = request.session.get('contractor_assignment_id')

        if not portal_user_id or not assignment_id:
            return JsonResponse({'status': 'error', 'message': 'Not authenticated. Please login again.'}, status=401)

        try:
            assignment = ContractorAssignment.objects.get(
                id=assignment_id,
                portal_user_id=portal_user_id
            )
        except ContractorAssignment.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)

        if assignment.onboarding.id != requirement.onboarding.id:
            return JsonResponse({'status': 'error', 'message': 'Access denied to this document'}, status=403)

        document_file = request.FILES.get('document_file')
        if not document_file:
            return JsonResponse({'status': 'error', 'message': 'No file selected'}, status=400)

        if document_file.size > 10 * 1024 * 1024:
            return JsonResponse({'status': 'error', 'message': 'File size exceeds 10MB limit'}, status=400)

        try:
            requirement.document_file = document_file
            requirement.status = 'UPLOADED'
            requirement.uploaded_at = timezone.now()
            requirement.save()

            file_url = requirement.document_file.url if requirement.document_file else None

            return JsonResponse({
                'status': 'success',
                'message': 'Document uploaded successfully!',
                'file_url': file_url
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error saving file: {str(e)}'}, status=500)


class DocumentVerifyView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        requirement_id = kwargs.get('pk')
        requirement = get_object_or_404(OnboardingDocumentRequirement, pk=requirement_id)

        if request.user != requirement.onboarding.ehs_officer and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to verify documents.')
            return redirect('contractor:onboarding_detail', pk=requirement.onboarding.pk)

        action = request.POST.get('action')

        if action == 'verify':
            requirement.status = 'VERIFIED'
            requirement.verified_by = request.user
            requirement.verified_at = timezone.now()
            messages.success(request, f'Document "{requirement.document_type.name}" verified successfully.')
        elif action == 'reject':
            requirement.status = 'REJECTED'
            requirement.comments = request.POST.get('comments', '')
            messages.warning(request, f'Document "{requirement.document_type.name}" rejected.')

        requirement.save()
        return redirect('contractor:onboarding_detail', pk=requirement.onboarding.pk)


# ==========================================================
# CONTRACTOR PORTAL VIEWS (External Users)
# ==========================================================
class ContractorPortalLoginView(View):
    template_name = 'contractor/portal/login.html'

    def get(self, request, *args, **kwargs):
        assignment_token = request.GET.get('assignment')
        if assignment_token:
            request.session['contractor_login_token'] = assignment_token
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        assignment_token = (
            request.POST.get('assignment')
            or request.session.get('contractor_login_token')
        )

        DEBUG_LOGIN = True
        if DEBUG_LOGIN:
            logger.warning(
                "[PORTAL LOGIN] email=%r | pwd_len=%d | pwd_repr=%r | token=%r",
                email, len(password), password, assignment_token,
            )

        if not email or not password:
            if DEBUG_LOGIN:
                logger.warning("[PORTAL LOGIN] Missing email or password")
            messages.error(request, "Please enter your email and password.")
            return render(request, self.template_name)

        portal_user = ContractorPortalUser.objects.filter(
            email__iexact=email,
        ).first()

        if DEBUG_LOGIN:
            logger.warning(
                "[PORTAL LOGIN] user_found=%s | id=%s | active=%s | type=%s",
                bool(portal_user),
                portal_user.id if portal_user else None,
                portal_user.is_active if portal_user else None,
                portal_user.user_type if portal_user else None,
            )

        if not portal_user:
            messages.error(request, "Invalid email or password.")
            return render(request, self.template_name)

        if not portal_user.is_active:
            if DEBUG_LOGIN:
                logger.warning("[PORTAL LOGIN] User found but is_active=False")
            messages.error(
                request,
                "Your account is inactive. Please contact the EHS administrator."
            )
            return render(request, self.template_name)

        pwd_ok = portal_user.check_password(password)
        if DEBUG_LOGIN:
            logger.warning(
                "[PORTAL LOGIN] check_password=%s | stored_hash_prefix=%r",
                pwd_ok,
                portal_user.password[:20],
            )

        if not pwd_ok:
            messages.error(request, "Invalid email or password.")
            return render(request, self.template_name)

        assignment = None

        if assignment_token:
            assignment = ContractorAssignment.objects.filter(
                access_token=assignment_token,
                portal_user=portal_user,
            ).select_related(
                'onboarding', 'onboarding__contractor'
            ).first()

            if DEBUG_LOGIN:
                logger.warning(
                    "[PORTAL LOGIN] assignment_by_token=%s",
                    assignment.id if assignment else None,
                )

        if not assignment:
            assignment = ContractorAssignment.objects.filter(
                portal_user=portal_user,
                is_access_active=True,
                status='ACTIVE',
            ).select_related(
                'onboarding', 'onboarding__contractor'
            ).order_by('-assigned_at').first()

            if DEBUG_LOGIN:
                logger.warning(
                    "[PORTAL LOGIN] assignment_by_fallback=%s",
                    assignment.id if assignment else None,
                )

        if not assignment:
            messages.error(
                request,
                "No active contractor onboarding assignment found."
            )
            return render(request, self.template_name)

        if not assignment.can_access:
            messages.error(
                request,
                "This contractor assignment is no longer active."
            )
            return render(request, self.template_name)

        request.session['contractor_portal_user_id'] = portal_user.id
        request.session['contractor_assignment_id'] = assignment.id
        request.session.pop('contractor_login_token', None)

        portal_user.last_login = timezone.now()
        portal_user.save(update_fields=['last_login', 'updated_at'])

        if DEBUG_LOGIN:
            logger.warning(
                "[PORTAL LOGIN] SUCCESS for user=%s assignment=%s",
                portal_user.email, assignment.id,
            )

        messages.success(request, f"Welcome, {portal_user.name}.")
        return redirect('contractor:portal_home')


class ContractorPortalLogoutView(View):
    def get(self, request, *args, **kwargs):
        request.session.pop('contractor_portal_user_id', None)
        request.session.pop('contractor_assignment_id', None)
        request.session.pop('contractor_login_token', None)

        messages.success(request, "You have been logged out successfully.")
        return redirect('contractor:portal_login')


class ContractorPortalHomeView(View):
    template_name = 'contractor/portal/home.html'

    def get(self, request, *args, **kwargs):
        portal_user_id = request.session.get('contractor_portal_user_id')
        assignment_id = request.session.get('contractor_assignment_id')

        if not portal_user_id or not assignment_id:
            return redirect('contractor:portal_login')

        assignment = ContractorAssignment.objects.filter(
            id=assignment_id,
            portal_user_id=portal_user_id
        ).select_related(
            'portal_user',
            'onboarding',
            'onboarding__contractor'
        ).first()

        if not assignment:
            request.session.flush()
            messages.error(request, "Your contractor assignment could not be found.")
            return redirect('contractor:portal_login')

        if not assignment.can_access:
            request.session.pop('contractor_assignment_id', None)
            messages.error(request, "Your contractor assignment is no longer active.")
            return redirect('contractor:portal_login')

        onboarding = assignment.onboarding

        question_ids = []
        if onboarding.pre_qualification_answers:
            question_ids = [
                int(question_id)
                for question_id in onboarding.pre_qualification_answers.keys()
            ]

        questions = PreQualificationQuestion.objects.filter(
            id__in=question_ids,
            is_active=True
        ).order_by('sequence', 'id')

        questions_with_answers = []
        for question in questions:
            q_id = str(question.id)
            answer = ''
            remark = ''

            if onboarding.pre_qualification_answers:
                answer = onboarding.pre_qualification_answers.get(q_id, '')
                if isinstance(answer, bool):
                    answer = ''

            if hasattr(onboarding, 'question_remarks') and onboarding.question_remarks:
                remark = onboarding.question_remarks.get(q_id, '')

            questions_with_answers.append({
                'question': question,
                'answer': answer,
                'is_answered': bool(answer and str(answer).strip()),
                'remark': remark,
            })

        document_requirements = onboarding.document_requirements.select_related(
            'document_type'
        ).all()

        is_editable = onboarding.status in ['DRAFT', 'REJECTED']
        is_readonly = onboarding.status in ['PENDING', 'APPROVED', 'COMPLETED']

        context = {
            'portal_user': assignment.portal_user,
            'assignment': assignment,
            'onboarding': onboarding,
            'contractor': onboarding.contractor,
            'questions_with_answers': questions_with_answers,
            'document_requirements': document_requirements,
            'is_readonly': is_readonly,
            'is_editable': is_editable,
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        portal_user_id = request.session.get('contractor_portal_user_id')
        assignment_id = request.session.get('contractor_assignment_id')

        if not portal_user_id or not assignment_id:
            return redirect('contractor:portal_login')

        assignment = ContractorAssignment.objects.filter(
            id=assignment_id,
            portal_user_id=portal_user_id
        ).first()

        if not assignment:
            messages.error(request, "Assignment not found.")
            return redirect('contractor:portal_login')

        onboarding = assignment.onboarding

        if onboarding.pre_qualification_answers is None:
            onboarding.pre_qualification_answers = {}

        if 'save_answers' in request.POST:
            for key, value in request.POST.items():
                if key.startswith('question_'):
                    question_id = key.replace('question_', '')
                    if question_id.isdigit():
                        onboarding.pre_qualification_answers[question_id] = value.strip() if value else ''

            onboarding.save()
            messages.success(request, "Your answers have been saved successfully!")
            return redirect('contractor:portal_home')

        elif 'submit_for_approval' in request.POST:
            for key, value in request.POST.items():
                if key.startswith('question_'):
                    question_id = key.replace('question_', '')
                    if question_id.isdigit():
                        onboarding.pre_qualification_answers[question_id] = value.strip() if value else ''

            unanswered = []
            for q_id, answer in onboarding.pre_qualification_answers.items():
                if not str(answer).strip():
                    unanswered.append(q_id)

            if unanswered:
                messages.warning(request, f"Please answer all questions before submitting.")
                return redirect('contractor:portal_home')

            required_docs = onboarding.document_requirements.filter(is_required=True)
            missing_docs = []
            for doc in required_docs:
                if doc.status not in ['UPLOADED', 'VERIFIED']:
                    missing_docs.append(doc.document_type.name)

            if missing_docs:
                messages.warning(request, f"Please upload required documents: {', '.join(missing_docs)}")
                return redirect('contractor:portal_home')

            onboarding.status = 'PENDING'
            onboarding.submitted_at = timezone.now()
            onboarding.rejection_reason = ''
            onboarding.save()

            messages.success(request, "Onboarding submitted for approval successfully! 🎉")
            return redirect('contractor:portal_home')

        return redirect('contractor:portal_home')


# ==========================================================
# WORK ORDER VIEWS
# ==========================================================

class WorkOrderListView(LoginRequiredMixin, ListView):
    model = WorkOrder
    template_name = 'contractor/workorder_list.html'
    context_object_name = 'work_orders'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')

        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(work_order_number__icontains=search) |
                Q(contractor__contractor_name__icontains=search) |
                Q(work_description__icontains=search) |
                Q(contract_number__icontains=search)
            )

        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)

        contractor_id = self.request.GET.get('contractor', '')
        if contractor_id:
            queryset = queryset.filter(contractor_id=contractor_id)

        work_category = self.request.GET.get('work_category', '')
        if work_category:
            queryset = queryset.filter(work_category=work_category)

        risk_level = self.request.GET.get('risk_level', '')
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)

        plant_id = self.request.GET.get('plant', '')
        if plant_id:
            queryset = queryset.filter(plant_id=plant_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['status_choices'] = WorkOrder.STATUS_CHOICES
        context['work_category_choices'] = Contractor.WORK_CATEGORY_CHOICES
        context['risk_level_choices'] = WorkOrder.RISK_LEVEL_CHOICES

        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_contractor'] = self.request.GET.get('contractor', '')
        context['selected_work_category'] = self.request.GET.get('work_category', '')
        context['selected_risk_level'] = self.request.GET.get('risk_level', '')
        context['selected_plant'] = self.request.GET.get('plant', '')

        context['contractors'] = Contractor.objects.filter(is_active=True).order_by('contractor_name')
        context['plants'] = Plant.objects.filter(is_active=True).order_by('name')

        context['total_work_orders'] = WorkOrder.objects.count()
        context['approved_work_orders'] = WorkOrder.objects.filter(status='APPROVED').count()
        context['closed_work_orders'] = WorkOrder.objects.filter(status='CLOSED').count()
        context['pending_work_orders'] = WorkOrder.objects.filter(status='SUBMITTED').count()
        context['rejected_work_orders'] = WorkOrder.objects.filter(status='REJECTED').count()

        return context


class WorkOrderDetailView(LoginRequiredMixin, DetailView):
    model = WorkOrder
    template_name = 'contractor/workorder_detail.html'
    context_object_name = 'work_order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['can_edit'] = (
            self.request.user.has_perm('contractor.change_workorder') or
            self.request.user.is_superuser
        )
        context['can_delete'] = (
            self.request.user.has_perm('contractor.delete_workorder') or
            self.request.user.is_superuser
        )
        context['can_approve'] = (
            self.request.user.has_perm('contractor.approve_workorder') or
            self.request.user.is_superuser
        )

        return context


class WorkOrderCreateView(LoginRequiredMixin, CreateView):
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = 'contractor/workorder_form.html'

    def get_initial(self):
        initial = super().get_initial()

        contractor_id = self.request.GET.get('contractor')
        if contractor_id:
            try:
                contractor = Contractor.objects.get(id=contractor_id)
                initial['contractor'] = contractor
                initial['work_category'] = contractor.work_category
                initial['risk_level'] = 'MEDIUM'
                initial['number_of_workers'] = contractor.number_of_workers or 0

                if contractor.ehs_officer_name:
                    initial['contractor_supervisor'] = contractor.ehs_officer_name
                    initial['contractor_supervisor_contact'] = contractor.ehs_mobile or ''
                    initial['contractor_supervisor_email'] = contractor.ehs_email or ''

            except Contractor.DoesNotExist:
                pass

        onboarding_id = self.request.GET.get('onboarding')
        if onboarding_id:
            try:
                onboarding = OnboardingRequest.objects.get(id=onboarding_id)
                initial['onboarding'] = onboarding
                initial['contractor'] = onboarding.contractor
            except OnboardingRequest.DoesNotExist:
                pass

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Work Order'
        context['form_mode'] = 'add'
        context['button_text'] = 'Create Work Order'

        context['approved_contractors'] = Contractor.objects.filter(
            onboarding_requests__status='APPROVED',
            is_active=True
        ).distinct()

        context['users'] = User.objects.filter(is_active=True).order_by('first_name', 'last_name')

        return context

    def form_valid(self, form):
        work_order = form.save(commit=False)
        work_order.created_by = self.request.user
        work_order.status = 'SUBMITTED'
        work_order.save()

        messages.success(
            self.request,
            f'Work Order "{work_order.work_order_number}" created successfully!'
        )

        return redirect('contractor:workorder_detail', pk=work_order.pk)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class WorkOrderUpdateView(LoginRequiredMixin, UpdateView):
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = 'contractor/workorder_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Work Order'
        context['form_mode'] = 'edit'
        context['button_text'] = 'Update Work Order'

        context['approved_contractors'] = Contractor.objects.filter(
            onboarding_requests__status='APPROVED',
            is_active=True
        ).distinct()

        context['users'] = User.objects.filter(is_active=True).order_by('first_name', 'last_name')

        return context

    def form_valid(self, form):
        work_order = form.save()
        messages.success(
            self.request,
            f'Work Order "{work_order.work_order_number}" updated successfully!'
        )
        return redirect('contractor:workorder_detail', pk=work_order.pk)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class WorkOrderDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = WorkOrder
    template_name = 'contractor/workorder_confirm_delete.html'
    context_object_name = 'work_order'
    permission_required = 'contractor.delete_workorder'
    success_url = reverse_lazy('contractor:workorder_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Delete Work Order'
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        work_order_number = self.object.work_order_number

        with transaction.atomic():
            response = super().delete(request, *args, **kwargs)

        messages.success(request, f'Work Order "{work_order_number}" deleted successfully.')
        return response


class WorkOrderStatusUpdateView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        work_order = get_object_or_404(WorkOrder, pk=kwargs.get('pk'))
        action = request.POST.get('action')
        rejection_reason = request.POST.get('rejection_reason', '').strip()

        if action == 'approve':
            work_order.status = 'APPROVED'
            work_order.approved_by = request.user
            work_order.approved_at = timezone.now()
            messages.success(request, f'Work Order "{work_order.work_order_number}" approved!')

        elif action == 'reject':
            work_order.status = 'REJECTED'
            work_order.notes = f"Rejected: {rejection_reason}"
            messages.warning(request, f'Work Order "{work_order.work_order_number}" rejected.')

        work_order.save()
        return redirect('contractor:workorder_list')


class WorkOrderBulkDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'contractor.delete_workorder'

    def post(self, request, *args, **kwargs):
        work_order_ids = request.POST.getlist('work_order_ids')

        if not work_order_ids:
            messages.error(request, 'No work orders selected for deletion.')
            return redirect('contractor:workorder_list')

        work_orders = WorkOrder.objects.filter(id__in=work_order_ids)
        count = work_orders.count()

        if count == 0:
            messages.error(request, 'No valid work orders found.')
            return redirect('contractor:workorder_list')

        wo_numbers = list(work_orders.values_list('work_order_number', flat=True))

        with transaction.atomic():
            work_orders.delete()

        messages.success(
            request,
            f'Successfully deleted {count} work order(s): {", ".join(wo_numbers[:5])}'
            + (f' and {count - 5} more...' if count > 5 else '')
        )

        return redirect('contractor:workorder_list')


class WorkOrderReviewListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = WorkOrder
    template_name = 'contractor/workorder_review_list.html'
    context_object_name = 'work_orders'
    paginate_by = 15

    def get_queryset(self):
        queryset = WorkOrder.objects.filter(
            status='SUBMITTED'
        ).order_by('-created_at')

        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(work_order_number__icontains=search) |
                Q(contractor__contractor_name__icontains=search) |
                Q(work_description__icontains=search)
            )

        contractor_id = self.request.GET.get('contractor', '')
        if contractor_id:
            queryset = queryset.filter(contractor_id=contractor_id)

        risk_level = self.request.GET.get('risk_level', '')
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['risk_level_choices'] = WorkOrder.RISK_LEVEL_CHOICES

        context['search_query'] = self.request.GET.get('search', '')
        context['selected_contractor'] = self.request.GET.get('contractor', '')
        context['selected_risk_level'] = self.request.GET.get('risk_level', '')

        context['contractors'] = Contractor.objects.filter(is_active=True).order_by('contractor_name')

        context['total_pending'] = WorkOrder.objects.filter(status='SUBMITTED').count()

        return context


class WorkOrderReviewView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = WorkOrder
    template_name = 'contractor/workorder_review.html'
    context_object_name = 'work_order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['can_review'] = (
            self.request.user.is_superuser or self.request.user.is_admin_user
        )

        return context

    def post(self, request, *args, **kwargs):
        work_order = self.get_object()
        action = request.POST.get('action')
        rejection_reason = request.POST.get('rejection_reason', '').strip()

        if not (request.user.is_superuser or request.user.is_admin_user):
            messages.error(request, 'You do not have permission to review work orders.')
            return redirect('contractor:workorder_detail', pk=work_order.pk)

        if action == 'approve':
            if work_order.status != 'SUBMITTED':
                messages.error(request, 'Only Submitted work orders can be approved.')
                return redirect('contractor:workorder_detail', pk=work_order.pk)

            work_order.status = 'APPROVED'
            work_order.approved_by = request.user
            work_order.approved_at = timezone.now()
            work_order.save()

            messages.success(
                request,
                f'Work Order "{work_order.work_order_number}" has been approved successfully!'
            )
            return redirect('contractor:workorder_list')

        elif action == 'reject':
            if work_order.status != 'SUBMITTED':
                messages.error(request, 'Only Submitted work orders can be rejected.')
                return redirect('contractor:workorder_detail', pk=work_order.pk)

            if not rejection_reason:
                messages.error(request, 'Please provide a reason for rejection.')
                return redirect('contractor:workorder_review', pk=work_order.pk)

            work_order.status = 'REJECTED'
            work_order.notes = f"Rejected: {rejection_reason}"
            work_order.save()

            messages.warning(
                request,
                f'Work Order "{work_order.work_order_number}" has been rejected.'
            )
            return redirect('contractor:workorder_list')

        else:
            messages.error(request, 'Invalid action.')
            return redirect('contractor:workorder_detail', pk=work_order.pk)


# ==========================================================
# TRAINING SIGN-OFF VIEWS
# ==========================================================

class TrainingSignOffCreateView(LoginRequiredMixin, CreateView):
    model = TrainingSignOff
    form_class = TrainingSignOffForm
    template_name = 'contractor/training_signoff_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Training Sign-Off'

        user = self.request.user
        plant_name = 'the Plant'

        if hasattr(user, 'plant') and user.plant:
            plant_name = user.plant.name
        elif hasattr(user, 'plant_name') and user.plant_name:
            plant_name = user.plant_name
        elif hasattr(user, 'profile') and hasattr(user.profile, 'plant'):
            plant_name = user.profile.plant.name

        context['plant_name'] = plant_name
        context['current_user_name'] = user.get_full_name() or user.username

        return context

    def form_valid(self, form):
        try:
            signoff = form.save(commit=False)
            signoff.created_by = self.request.user

            if not signoff.company_representative and signoff.work_order:
                signoff.company_representative = signoff.work_order.company_representative

            signoff.status = 'SUBMITTED'
            signoff.save()

            try:
                from apps.notifications.services import NotificationService

                email_sent = NotificationService.send_training_signoff_email(signoff)

                if email_sent:
                    messages.success(
                        self.request,
                        f'Training Sign-Off "{signoff.signoff_number}" submitted successfully! '
                        f'An email with PDF has been sent to the contractor representative.'
                    )
                else:
                    messages.warning(
                        self.request,
                        f'Training Sign-Off "{signoff.signoff_number}" submitted successfully! '
                        f'However, the email notification could not be sent.'
                    )
            except Exception as e:
                logger.error(f"Error sending training sign-off email: {str(e)}")
                messages.warning(
                    self.request,
                    f'Training Sign-Off "{signoff.signoff_number}" submitted successfully! '
                    f'However, there was an issue sending the email notification.'
                )

            return redirect('contractor:training_signoff_detail', pk=signoff.pk)

        except Exception as e:
            logger.error(f"Error saving training sign-off: {str(e)}")
            messages.error(self.request, f'Error saving: {str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.error(f"Form errors: {form.errors}")

        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")

        return super().form_invalid(form)


class TrainingSignOffListView(LoginRequiredMixin, ListView):
    model = TrainingSignOff
    template_name = 'contractor/training_signoff_list.html'
    context_object_name = 'signoffs'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'contractor', 'work_order', 'session'
        ).order_by('-created_at')

        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(contractor__contractor_name__icontains=search) |
                Q(signoff_number__icontains=search)
            )

        return queryset


class TrainingSignOffDetailView(LoginRequiredMixin, DetailView):
    model = TrainingSignOff
    template_name = 'contractor/training_signoff_detail.html'
    context_object_name = 'signoff'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        signoff = self.get_object()

        user = self.request.user
        plant_name = 'the Plant'

        if hasattr(user, 'plant') and user.plant:
            plant_name = user.plant.name
        elif hasattr(user, 'plant_name') and user.plant_name:
            plant_name = user.plant_name
        elif hasattr(user, 'profile') and hasattr(user.profile, 'plant'):
            plant_name = user.profile.plant.name
        elif hasattr(signoff, 'work_order') and signoff.work_order and signoff.work_order.plant:
            plant_name = signoff.work_order.plant.name

        context['plant_name'] = plant_name
        context['current_user_name'] = user.get_full_name() or user.username

        return context


class UploadSignOffSignatureView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            signoff = get_object_or_404(TrainingSignOff, pk=pk)

            if signoff.created_by != request.user and not request.user.is_superuser:
                return JsonResponse({
                    'status': 'error',
                    'message': 'You do not have permission to upload this signature.'
                }, status=403)

            if 'signature_file' not in request.FILES:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No file uploaded.'
                }, status=400)

            file = request.FILES['signature_file']

            valid_types = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']
            if file.content_type not in valid_types:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid file type. Please upload JPG, PNG, or PDF.'
                }, status=400)

            if file.size > 5 * 1024 * 1024:
                return JsonResponse({
                    'status': 'error',
                    'message': 'File size exceeds 5MB limit.'
                }, status=400)

            signoff.company_signature = file
            signoff.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Signature uploaded successfully!'
            })

        except Exception as e:
            logger.error(f"Error uploading signature: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


class UploadSupportingDocumentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            signoff = get_object_or_404(TrainingSignOff, pk=pk)

            if signoff.created_by != request.user and not request.user.is_superuser:
                return JsonResponse({
                    'status': 'error',
                    'message': 'You do not have permission to upload this document.'
                }, status=403)

            if 'supporting_document' not in request.FILES:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No file uploaded.'
                }, status=400)

            file = request.FILES['supporting_document']

            valid_types = [
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'image/jpeg',
                'image/jpg',
                'image/png'
            ]
            if file.content_type not in valid_types:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid file type. Please upload PDF, DOC, DOCX, JPG, or PNG.'
                }, status=400)

            if file.size > 5 * 1024 * 1024:
                return JsonResponse({
                    'status': 'error',
                    'message': 'File size exceeds 5MB limit.'
                }, status=400)

            signoff.supporting_documents = file

            signoff.status = 'COMPLETED'

            signoff.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Document uploaded successfully! Sign-Off is now completed.'
            })

        except Exception as e:
            logger.error(f"Error uploading supporting document: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


# ==========================================================
# CONTRACTOR INSPECTION VIEWS
# ==========================================================

class ContractorInspectionListView(LoginRequiredMixin, ListView):
    model = ContractorInspection
    template_name = 'contractor/inspection_list.html'
    context_object_name = 'inspections'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'contractor', 'assigned_to', 'plant', 'zone', 'location'
        ).prefetch_related('selected_questions', 'responses')

        if not (self.request.user.is_superuser or getattr(self.request.user, 'is_admin_user', False)):
            queryset = queryset.filter(assigned_to=self.request.user)

        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(inspection_code__icontains=search) |
                Q(contractor__contractor_name__icontains=search) |
                Q(contractor__contractor_code__icontains=search)
            )

        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)

        contractor_id = self.request.GET.get('contractor', '')
        if contractor_id:
            queryset = queryset.filter(contractor_id=contractor_id)

        plant_id = self.request.GET.get('plant', '')
        if plant_id:
            queryset = queryset.filter(plant_id=plant_id)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        context['status_choices'] = ContractorInspection.STATUS_CHOICES
        context['contractors'] = Contractor.objects.filter(is_active=True)
        context['plants'] = Plant.objects.filter(is_active=True)
        context['search'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_contractor'] = self.request.GET.get('contractor', '')
        context['selected_plant'] = self.request.GET.get('plant', '')
        context['total'] = queryset.count()
        context['scheduled'] = queryset.filter(status='SCHEDULED').count()
        context['in_progress'] = queryset.filter(status='IN_PROGRESS').count()
        context['closed'] = queryset.filter(status='CLOSED').count()
        context['overdue'] = queryset.filter(status='OVERDUE').count()
        context['cancelled'] = queryset.filter(status='CANCELLED').count()
        return context


class ContractorInspectionCreateView(LoginRequiredMixin, CreateView):
    model = ContractorInspection
    form_class = ContractorInspectionForm
    template_name = 'contractor/inspection_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        context['title'] = 'Schedule Contractor Inspection'

        questions = ContractorInspectionQuestion.objects.filter(
            is_active=True
        ).order_by('category', 'display_order')

        questions_by_section = {}
        for q in questions:
            if q.category not in questions_by_section:
                questions_by_section[q.category] = []
            questions_by_section[q.category].append(q)

        context['questions_by_section'] = questions_by_section
        context['section_display'] = dict(ContractorInspectionQuestion.CATEGORY_CHOICES)
        context['total_questions'] = questions.count()
        context['selected_question_ids'] = []
        return context

    def get_initial(self):
        initial = super().get_initial()
        today = timezone.now().date()
        initial['inspection_start_date'] = today
        initial['inspection_end_date'] = today + timedelta(days=7)
        initial['due_date_offset_days'] = 7
        return initial

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            return self.form_valid(form)
        else:
            logger.error(f"Form errors: {form.errors}")
            return self.form_invalid(form)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                inspection = form.save(commit=False)
                inspection.assigned_by = self.request.user

                selected_question_ids = self.request.POST.getlist('selected_questions')

                if not selected_question_ids:
                    messages.error(self.request, 'Please select at least one question for the inspection.')
                    return self.form_invalid(form)

                plant = form.cleaned_data.get('plant')
                zone = form.cleaned_data.get('zone')
                location = form.cleaned_data.get('location')
                sublocation = form.cleaned_data.get('sublocation')

                if plant and not zone:
                    inspection.zone = None
                if zone and not location:
                    inspection.location = None
                if location and not sublocation:
                    inspection.sublocation = None

                if inspection.enable_auto_schedule:
                    if not inspection.due_date_offset_days:
                        inspection.due_date_offset_days = 7
                    start_date = inspection.inspection_start_date
                    inspection.inspection_end_date = start_date + timedelta(days=inspection.due_date_offset_days - 1)

                inspection.save()

                if selected_question_ids:
                    inspection.selected_questions.set(selected_question_ids)

                if inspection.enable_auto_schedule:
                    try:
                        next_month_copy = inspection.create_recurring_copy()
                        if next_month_copy:
                            messages.info(
                                self.request,
                                f'Recurring inspection scheduled for {next_month_copy.inspection_start_date} '
                                f'to {next_month_copy.inspection_end_date}'
                            )
                    except Exception as e:
                        logger.error(f"Error creating recurring copy: {e}")

                try:
                    from apps.notifications.services import NotificationService
                    NotificationService.notify(
                        content_object=inspection,
                        notification_type='INSPECTION_SCHEDULE',
                        module='CONTRACTOR_INSPECTION'
                    )
                except Exception as e:
                    logger.error(f"Notification error: {e}")

                messages.success(
                    self.request,
                    f'Inspection "{inspection.inspection_code}" scheduled successfully! '
                    f'{len(selected_question_ids)} question(s) selected.'
                )
                return redirect('contractor:inspection_detail', pk=inspection.pk)

        except Exception as e:
            logger.error(f"Error creating inspection: {e}")
            messages.error(self.request, f'Error creating inspection: {str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.error(f"Form errors: {form.errors}")

        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")

        context = self.get_context_data(form=form)

        questions = ContractorInspectionQuestion.objects.filter(
            is_active=True
        ).order_by('category', 'display_order')

        questions_by_section = {}
        for q in questions:
            if q.category not in questions_by_section:
                questions_by_section[q.category] = []
            questions_by_section[q.category].append(q)

        context['questions_by_section'] = questions_by_section
        context['total_questions'] = questions.count()

        return self.render_to_response(context)


class ContractorInspectionDetailView(LoginRequiredMixin, DetailView):
    model = ContractorInspection
    template_name = 'contractor/inspection_detail.html'
    context_object_name = 'inspection'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        inspection = self.get_object()

        responses = inspection.responses.select_related('question').all()
        responses_by_section = {}
        for response in responses:
            section = response.question.category
            if section not in responses_by_section:
                responses_by_section[section] = []
            responses_by_section[section].append(response)
        context['responses_by_section'] = responses_by_section

        selected_questions = inspection.selected_questions.filter(is_active=True).order_by('category', 'display_order')
        questions_by_section = {}
        for q in selected_questions:
            if q.category not in questions_by_section:
                questions_by_section[q.category] = []
            questions_by_section[q.category].append(q)
        context['questions_by_section'] = questions_by_section
        context['section_display'] = dict(ContractorInspectionQuestion.CATEGORY_CHOICES)

        total_questions = selected_questions.count()
        answered_questions = responses.count()
        yes_count = responses.filter(answer='YES').count()
        no_count = responses.filter(answer='NO').count()
        na_count = responses.filter(answer='NA').count()

        context['total_questions'] = total_questions
        context['answered_questions'] = answered_questions
        context['yes_count'] = yes_count
        context['no_count'] = no_count
        context['na_count'] = na_count
        context['compliance_score'] = round((yes_count / total_questions) * 100, 1) if total_questions > 0 else 0

        context['can_start'] = (
            inspection.status in ['SCHEDULED', 'OVERDUE'] and
            (self.request.user == inspection.assigned_to or self.request.user.is_superuser)
        )
        context['can_cancel'] = (
            inspection.status in ['SCHEDULED', 'IN_PROGRESS'] and
            (self.request.user == inspection.assigned_by or self.request.user.is_superuser)
        )
        return context


class ContractorInspectionConductView(LoginRequiredMixin, View):
    template_name = 'contractor/inspection_conduct.html'

    def get(self, request, pk):
        inspection = get_object_or_404(ContractorInspection, pk=pk)

        if request.user != inspection.assigned_to and not request.user.is_superuser:
            messages.error(request, 'You are not authorized to conduct this inspection.')
            return redirect('contractor:inspection_list')

        if inspection.status == 'CLOSED':
            messages.warning(request, 'This inspection is already closed.')
            return redirect('contractor:inspection_detail', pk=inspection.pk)

        if inspection.status == 'SCHEDULED':
            inspection.status = 'IN_PROGRESS'
            inspection.started_at = timezone.now()
            inspection.save(update_fields=['status', 'started_at'])

        selected_questions = inspection.selected_questions.filter(
            is_active=True
        ).order_by('category', 'display_order')

        questions_by_section = {}
        responses_dict = {r.question_id: r for r in inspection.responses.all()}

        for q in selected_questions:
            if q.category not in questions_by_section:
                questions_by_section[q.category] = []

            questions_by_section[q.category].append({
                'question': q,
                'response': responses_dict.get(q.id),
                'has_response': q.id in responses_dict
            })

        context = {
            'inspection': inspection,
            'questions_by_section': questions_by_section,
            'section_display': dict(ContractorInspectionQuestion.CATEGORY_CHOICES),
            'total_questions': selected_questions.count(),
            'answered_questions': len(responses_dict),
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        inspection = get_object_or_404(ContractorInspection, pk=pk)

        if request.user != inspection.assigned_to and not request.user.is_superuser:
            messages.error(request, 'You are not authorized to submit this inspection.')
            return redirect('contractor:inspection_list')

        selected_questions = inspection.selected_questions.filter(is_active=True)

        if not selected_questions.exists():
            messages.error(request, 'No questions found for this inspection.')
            return redirect('contractor:inspection_detail', pk=inspection.pk)

        with transaction.atomic():
            for question in selected_questions:
                answer = request.POST.get(f'answer_{question.id}')
                remarks = request.POST.get(f'remarks_{question.id}', '').strip()

                if answer:
                    response, created = ContractorInspectionResponse.objects.get_or_create(
                        inspection=inspection,
                        question=question
                    )
                    response.answer = answer
                    response.remarks = remarks

                    if f'photo_{question.id}' in request.FILES:
                        response.photo = request.FILES[f'photo_{question.id}']

                    response.save()

            all_answered = True
            unanswered_questions = []
            for question in selected_questions:
                try:
                    response = ContractorInspectionResponse.objects.get(
                        inspection=inspection,
                        question=question
                    )
                    if not response.answer:
                        all_answered = False
                        unanswered_questions.append(question)
                except ContractorInspectionResponse.DoesNotExist:
                    all_answered = False
                    unanswered_questions.append(question)

            if not all_answered:
                messages.warning(
                    request,
                    f'Please answer all questions before submitting. {len(unanswered_questions)} question(s) remaining.'
                )
                return redirect('contractor:inspection_conduct', pk=inspection.pk)

            inspection.status = 'CLOSED'
            inspection.closed_at = timezone.now()
            inspection.save(update_fields=['status', 'closed_at'])

            try:
                from apps.notifications.services import NotificationService
                NotificationService.notify(
                    content_object=inspection,
                    notification_type='INSPECTION_COMPLETED',
                    module='CONTRACTOR_INSPECTION'
                )
            except Exception as e:
                logger.error(f"Notification error: {e}")

        messages.success(
            request,
            f'Inspection "{inspection.inspection_code}" completed successfully!'
        )

        return redirect('contractor:inspection_detail', pk=inspection.pk)


class ContractorInspectionCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        inspection = get_object_or_404(ContractorInspection, pk=pk)

        if (inspection.status in ['CLOSED', 'CANCELLED']):
            messages.error(request, 'This inspection cannot be cancelled.')
            return redirect('contractor:inspection_detail', pk=inspection.pk)

        if (request.user != inspection.assigned_by and
            not request.user.is_superuser and
            not getattr(request.user, 'is_admin_user', False)):
            messages.error(request, 'You do not have permission to cancel this inspection.')
            return redirect('contractor:inspection_detail', pk=inspection.pk)

        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Please provide a reason for cancellation.')
            return redirect('contractor:inspection_detail', pk=inspection.pk)

        inspection.status = 'CANCELLED'
        inspection.notes = f"Cancelled: {reason}" if inspection.notes else f"Cancelled: {reason}"
        inspection.save(update_fields=['status', 'notes'])

        messages.success(request, f'Inspection "{inspection.inspection_code}" cancelled successfully.')
        return redirect('contractor:inspection_list')


class ContractorInspectionDeleteView(LoginRequiredMixin, DeleteView):
    model = ContractorInspection
    template_name = 'contractor/inspection_confirm_delete.html'
    context_object_name = 'inspection'
    success_url = reverse_lazy('contractor:inspection_list')

    def get_queryset(self):
        if self.request.user.is_superuser or getattr(self.request.user, 'is_admin_user', False):
            return super().get_queryset()
        return ContractorInspection.objects.none()

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        inspection_code = self.object.inspection_code

        with transaction.atomic():
            self.object.responses.all().delete()
            self.object.selected_questions.clear()
            response = super().delete(request, *args, **kwargs)

        messages.success(request, f'Inspection "{inspection_code}" deleted successfully.')
        return response


class ContractorInspectionUpdateView(LoginRequiredMixin, UpdateView):
    model = ContractorInspection
    form_class = ContractorInspectionForm
    template_name = 'contractor/inspection_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Edit'
        context['title'] = f'Edit Inspection: {self.object.inspection_code}'
        context['form_mode'] = 'edit'

        questions = ContractorInspectionQuestion.objects.filter(
            is_active=True
        ).order_by('category', 'display_order')

        questions_by_section = {}
        for q in questions:
            if q.category not in questions_by_section:
                questions_by_section[q.category] = []
            questions_by_section[q.category].append(q)

        context['questions_by_section'] = questions_by_section
        context['section_choices'] = ContractorInspectionQuestion.CATEGORY_CHOICES
        context['section_display'] = dict(ContractorInspectionQuestion.CATEGORY_CHOICES)

        context['selected_question_ids'] = list(
            self.object.selected_questions.values_list('id', flat=True)
        )
        context['total_questions'] = questions.count()

        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                inspection = form.save()

                selected_question_ids = self.request.POST.getlist('selected_questions')
                if selected_question_ids:
                    inspection.selected_questions.set(selected_question_ids)
                else:
                    messages.warning(
                        self.request,
                        'No questions were selected. Please select at least one question.'
                    )
                    return self.form_invalid(form)

                messages.success(
                    self.request,
                    f'Inspection "{inspection.inspection_code}" updated successfully!'
                )

                return redirect('contractor:inspection_detail', pk=inspection.pk)

        except Exception as e:
            logger.error(f"Error updating inspection: {e}")
            messages.error(self.request, f'Error updating inspection: {str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class MyContractorInspectionsView(LoginRequiredMixin, ListView):
    model = ContractorInspection
    template_name = 'contractor/my_inspections.html'
    context_object_name = 'inspections'
    paginate_by = 15

    def get_queryset(self):
        queryset = ContractorInspection.objects.filter(
            assigned_to=self.request.user
        ).select_related(
            'contractor', 'plant'
        ).prefetch_related('selected_questions')

        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)

        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(inspection_code__icontains=search) |
                Q(contractor__contractor_name__icontains=search)
            )

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        context['status_choices'] = ContractorInspection.STATUS_CHOICES
        context['selected_status'] = self.request.GET.get('status', '')
        context['search'] = self.request.GET.get('search', '')

        context['total'] = queryset.count()
        context['pending'] = queryset.filter(status='SCHEDULED').count()
        context['in_progress'] = queryset.filter(status='IN_PROGRESS').count()
        context['completed'] = queryset.filter(status='CLOSED').count()
        context['overdue'] = queryset.filter(status='OVERDUE').count()

        return context


# ==========================================================
# API VIEWS (AJAX)
# ==========================================================

class GetContractorDetailsAPIView(LoginRequiredMixin, View):
    def get(self, request, contractor_id):
        try:
            contractor = get_object_or_404(Contractor, pk=contractor_id)

            latest_work_order = WorkOrder.objects.filter(
                contractor=contractor,
                status='APPROVED'
            ).select_related(
                'plant',
                'department',
                'company_representative'
            ).order_by('-created_at').first()

            department = None
            if latest_work_order and latest_work_order.department:
                department = {
                    'id': latest_work_order.department.id,
                    'name': latest_work_order.department.name,
                }
            else:
                onboarding = OnboardingRequest.objects.filter(
                    contractor=contractor,
                    status='APPROVED'
                ).select_related('ehs_officer').first()

                if onboarding and hasattr(onboarding, 'department') and onboarding.department:
                    department = {
                        'id': onboarding.department.id,
                        'name': onboarding.department.name,
                    }

            plant = None
            if latest_work_order and latest_work_order.plant:
                plant = {
                    'id': latest_work_order.plant.id,
                    'name': latest_work_order.plant.name,
                }

            zone = None
            location = None
            sublocation = None

            if latest_work_order:
                if hasattr(latest_work_order, 'zone') and latest_work_order.zone:
                    if hasattr(latest_work_order.zone, 'id'):
                        zone = {
                            'id': latest_work_order.zone.id,
                            'name': latest_work_order.zone.name,
                        }
                elif latest_work_order.plant:
                    first_zone = Zone.objects.filter(plant=latest_work_order.plant, is_active=True).first()
                    if first_zone:
                        zone = {
                            'id': first_zone.id,
                            'name': first_zone.name,
                        }

                if hasattr(latest_work_order, 'location') and latest_work_order.location:
                    if hasattr(latest_work_order.location, 'id'):
                        location = {
                            'id': latest_work_order.location.id,
                            'name': latest_work_order.location.name,
                        }
                elif zone and zone.get('id'):
                    first_location = Location.objects.filter(zone_id=zone['id'], is_active=True).first()
                    if first_location:
                        location = {
                            'id': first_location.id,
                            'name': first_location.name,
                        }

                if hasattr(latest_work_order, 'sublocation') and latest_work_order.sublocation:
                    if hasattr(latest_work_order.sublocation, 'id'):
                        sublocation = {
                            'id': latest_work_order.sublocation.id,
                            'name': latest_work_order.sublocation.name,
                        }
                elif location and location.get('id'):
                    first_sublocation = SubLocation.objects.filter(location_id=location['id'], is_active=True).first()
                    if first_sublocation:
                        sublocation = {
                            'id': first_sublocation.id,
                            'name': first_sublocation.name,
                        }

            data = {
                'success': True,
                'contractor': {
                    'id': contractor.id,
                    'name': contractor.contractor_name,
                    'code': contractor.contractor_code,
                    'work_category': contractor.work_category,
                    'work_category_display': contractor.get_work_category_display(),
                    'nature_of_business': contractor.nature_of_business,
                    'service_description': contractor.service_description,
                    'years_of_experience': contractor.years_of_experience,
                    'number_of_workers': contractor.number_of_workers or 0,

                    'supervisor_name': contractor.ehs_officer_name or '',
                    'supervisor_designation': contractor.ehs_designation or '',
                    'supervisor_mobile': contractor.ehs_mobile or '',
                    'supervisor_email': contractor.ehs_email or '',

                    'contact_person': contractor.contact_person or '',
                    'contact_mobile': contractor.mobile or '',
                    'contact_email': contractor.email or '',

                    'address': f"{contractor.address_line1}, {contractor.city}, {contractor.state}" if contractor.address_line1 else '',

                    'plant': plant,
                    'zone': zone,
                    'location': location,
                    'sublocation': sublocation,
                    'department': department,

                    'latest_work_order': {
                        'id': latest_work_order.id if latest_work_order else None,
                        'number': latest_work_order.work_order_number if latest_work_order else None,
                    } if latest_work_order else None,
                }
            }
            return JsonResponse(data)
        except Exception as e:
            logger.error(f"Error getting contractor details: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class GetContractorWorkOrdersView(LoginRequiredMixin, View):
    def get(self, request, contractor_id):
        try:
            contractor = get_object_or_404(Contractor, id=contractor_id)
            work_orders = WorkOrder.objects.filter(
                contractor=contractor,
                is_active=True
            ).values('id', 'work_order_number', 'work_description', 'status', 'start_date', 'end_date')

            data = {
                'status': 'success',
                'work_orders': list(work_orders)
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=404)


class GetApprovedContractorsView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            contractors = Contractor.objects.filter(
                onboarding_requests__status='APPROVED',
                is_active=True
            ).distinct().values('id', 'contractor_code', 'contractor_name', 'work_category')

            data = {
                'status': 'success',
                'contractors': list(contractors)
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


class GetContractorApprovedWorkOrdersView(LoginRequiredMixin, View):
    def get(self, request, contractor_id):
        try:
            work_orders = WorkOrder.objects.filter(
                contractor_id=contractor_id,
                status='APPROVED'
            ).order_by('-created_at').values(
                'id', 'work_order_number', 'contract_number'
            )
            return JsonResponse({
                'status': 'success',
                'work_orders': list(work_orders)
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=404)


class GetWorkOrderSignoffDetailsView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            work_order = get_object_or_404(WorkOrder, pk=pk, status='APPROVED')
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=404)

        contractor = work_order.contractor
        company_rep = work_order.company_representative

        company_rep_designation = ''
        if company_rep:
            role = getattr(company_rep, 'role', None)
            company_rep_designation = role.name if role else 'Safety Manager'

        data = {
            'status': 'success',
            'contractor_id': contractor.id,
            'contractor_representative': work_order.contractor_supervisor or contractor.ehs_officer_name,
            'contractor_representative_designation': contractor.ehs_designation,
            'number_of_workers': work_order.number_of_workers,
            'contractor_supervisor': work_order.contractor_supervisor or contractor.ehs_officer_name,
            'contractor_supervisor_designation': contractor.ehs_designation,
            'company_representative_id': company_rep.id if company_rep else None,
            'company_representative_name': company_rep.get_full_name() if company_rep else '',
            'company_representative_designation': company_rep_designation,
            'contractor_name': contractor.contractor_name,
        }
        return JsonResponse(data)


class GetTrainingSessionDetailsView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            session = get_object_or_404(ToolboxTalkSessionPlan, pk=pk)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=404)

        category_name = ''
        if hasattr(session, 'category') and session.category:
            if hasattr(session.category, 'category_name'):
                category_name = session.category.category_name
            elif hasattr(session.category, 'name'):
                category_name = session.category.name
            else:
                category_name = str(session.category)

        department_name = ''
        if hasattr(session, 'department') and session.department:
            if hasattr(session.department, 'name'):
                department_name = session.department.name
            else:
                department_name = str(session.department)

        trainers = []
        if hasattr(session, 'trainers') and hasattr(session.trainers, 'all'):
            for t in session.trainers.all():
                try:
                    trainer_data = {
                        'id': t.id,
                        'name': t.get_full_name() if hasattr(t, 'get_full_name') else str(t),
                        'email': getattr(t, 'email', '')
                    }
                    trainers.append(trainer_data)
                except:
                    trainers.append({'id': 0, 'name': str(t), 'email': ''})

        incharges = []
        if hasattr(session, 'incharges') and hasattr(session.incharges, 'all'):
            for i in session.incharges.all():
                try:
                    incharge_data = {
                        'id': i.id,
                        'name': i.get_full_name() if hasattr(i, 'get_full_name') else str(i),
                        'email': getattr(i, 'email', '')
                    }
                    incharges.append(incharge_data)
                except:
                    incharges.append({'id': 0, 'name': str(i), 'email': ''})

        topic_details = []
        topic_title = getattr(session, 'topic_title', 'N/A')
        topic_description = ''

        if hasattr(session, 'topic') and session.topic:
            topic_title = getattr(session.topic, 'topic_title', 'N/A')
            topic_description = getattr(session.topic, 'description', 'No description provided.')

            if hasattr(session.topic, 'details') and hasattr(session.topic.details, 'all'):
                for detail in session.topic.details.all():
                    try:
                        topic_details.append({
                            'safety_point': getattr(detail, 'safety_point', '')
                        })
                    except:
                        pass

        data = {
            'status': 'success',
            'session_no': getattr(session, 'session_no', 'N/A'),
            'topic_title': topic_title,
            'topic_description': topic_description,
            'category': category_name,
            'department': department_name,
            'session_status': getattr(session, 'status', 'N/A'),
            'session_status_display': getattr(session, 'get_status_display', lambda: session.status)() if hasattr(session, 'get_status_display') else getattr(session, 'status', 'N/A'),
            'planned_date': session.planned_date.strftime('%Y-%m-%d') if hasattr(session, 'planned_date') and session.planned_date else 'N/A',
            'planned_time': session.planned_time.strftime('%H:%M') if hasattr(session, 'planned_time') and session.planned_time else 'N/A',
            'expected_participants': getattr(session, 'expected_participants', 0),
            'trainers': trainers,
            'incharges': incharges,
            'topic_details': topic_details,
        }

        return JsonResponse(data)


class GetPlantZonesAPIView(LoginRequiredMixin, View):
    def get(self, request, plant_id):
        try:
            zones = Zone.objects.filter(
                plant_id=plant_id,
                is_active=True
            ).values('id', 'name', 'code')
            return JsonResponse({'success': True, 'zones': list(zones)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class GetZoneLocationsAPIView(LoginRequiredMixin, View):
    def get(self, request, zone_id):
        try:
            locations = Location.objects.filter(
                zone_id=zone_id,
                is_active=True
            ).values('id', 'name', 'code')
            return JsonResponse({'success': True, 'locations': list(locations)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class GetLocationSublocationsAPIView(LoginRequiredMixin, View):
    def get(self, request, location_id):
        try:
            sublocations = SubLocation.objects.filter(
                location_id=location_id,
                is_active=True
            ).values('id', 'name', 'code')
            return JsonResponse({'success': True, 'sublocations': list(sublocations)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class GetPlantUsersAPIView(LoginRequiredMixin, View):
    def get(self, request, plant_id):
        try:
            users = User.objects.filter(
                plant_id=plant_id,
                role__name__in=['SAFETY MANAGER', 'PLANT HEAD'],
                is_active=True
            ).select_related('role').order_by('first_name', 'last_name')

            user_list = []
            for user in users:
                user_list.append({
                    'id': user.id,
                    'name': user.get_full_name() or user.username,
                    'role': user.role.name if user.role else '',
                })

            return JsonResponse({'success': True, 'users': user_list})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class GetContractorWorkOrdersAPIView(LoginRequiredMixin, View):
    def get(self, request, contractor_id):
        try:
            work_orders = WorkOrder.objects.filter(
                contractor_id=contractor_id,
                status='APPROVED'
            ).values('id', 'work_order_number', 'contract_number', 'work_description')
            return JsonResponse({'success': True, 'work_orders': list(work_orders)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ==========================================================
# PERFORMANCE VIEWS
# ==========================================================

class ContractorPerformanceDashboardView(LoginRequiredMixin, TemplateView):
    """
    Contractor Performance Dashboard — LIVE DATA.
    """
    template_name = 'contractor/performance_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.now().date()
        month = int(self.request.GET.get('month', today.month))
        year = int(self.request.GET.get('year', today.year))

        period_start = date(year, month, 1)
        if month == 12:
            period_end = date(year + 1, 1, 1)
        else:
            period_end = date(year, month + 1, 1)

        ranking = []
        contractors = Contractor.objects.filter(is_active=True).order_by('contractor_name')

        for contractor in contractors:
            metrics = self._calculate_live_metrics(
                contractor, period_start, period_end
            )
            if metrics is None:
                continue

            ranking.append({
                'contractor_id': contractor.id,
                'contractor_name': contractor.contractor_name,
                'contractor_code': contractor.contractor_code,
                'score': metrics['overall_score'],
                'rating': metrics['rating'],
                'risk_level': metrics['risk_level'],
                'onboarding_score': metrics['onboarding_score'],
                'training_score': metrics['training_score'],
                'inspection_score': metrics['inspection_score'],
                'work_order_score': metrics['work_order_score'],
                'inspections_count': metrics['inspections_count'],
                'work_orders_count': metrics['work_orders_count'],
                'training_count': metrics['training_count'],
            })

        ranking.sort(key=lambda x: x['score'], reverse=True)

        for idx, row in enumerate(ranking, 1):
            row['rank'] = idx

        context['ranking'] = ranking

        if ranking:
            scores = [r['score'] for r in ranking]
            context['avg_score'] = round(sum(scores) / len(scores), 1)
            context['max_score'] = max(scores)
            context['min_score'] = min(scores)
            context['total_contractors'] = len(ranking)
            context['excellent_count'] = len([r for r in ranking if r['rating'] == 'Excellent'])
            context['good_count'] = len([r for r in ranking if r['rating'] == 'Good'])
            context['needs_improvement_count'] = len([r for r in ranking if r['rating'] == 'Needs Improvement'])
            context['poor_count'] = len([r for r in ranking if r['rating'] == 'Poor'])
        else:
            context.update({
                'avg_score': 0, 'max_score': 0, 'min_score': 0,
                'total_contractors': 0, 'excellent_count': 0,
                'good_count': 0, 'needs_improvement_count': 0,
                'poor_count': 0,
            })

        context['current_month'] = month
        context['current_year'] = year
        context['month_options'] = [
            {'value': i, 'label': datetime(2000, i, 1).strftime('%B')}
            for i in range(1, 13)
        ]
        current_year = timezone.now().year
        context['year_options'] = list(range(current_year - 5, current_year + 2))

        return context

    def _calculate_live_metrics(self, contractor, period_start, period_end):
        inspections_qs = ContractorInspection.objects.filter(
            contractor=contractor,
            status='CLOSED',
            closed_at__gte=period_start,
            closed_at__lt=period_end,
        )
        inspections_count = inspections_qs.count()

        if inspections_count > 0:
            total_yes = 0
            total_questions = 0
            for insp in inspections_qs.prefetch_related('responses', 'selected_questions'):
                total_yes += insp.responses.filter(answer='YES').count()
                total_questions += insp.selected_questions.count()
            inspection_score = round((total_yes / total_questions) * 100, 2) if total_questions else 0
        else:
            inspection_score = 0

        trainings_qs = TrainingSignOff.objects.filter(
            contractor=contractor,
            status='COMPLETED',
            updated_at__gte=period_start,
            updated_at__lt=period_end,
        )
        training_count = trainings_qs.count()

        active_wo_count = WorkOrder.objects.filter(
            contractor=contractor,
            status='APPROVED',
            start_date__lt=period_end,
            end_date__gte=period_start,
        ).count()

        if active_wo_count > 0:
            training_score = round(min((training_count / active_wo_count) * 100, 100), 2)
        elif training_count > 0:
            training_score = 100.0
        else:
            training_score = 0

        wo_qs = WorkOrder.objects.filter(
            contractor=contractor,
            approved_at__gte=period_start,
            approved_at__lt=period_end,
        )
        work_orders_count = wo_qs.count()
        approved_count = wo_qs.filter(status='APPROVED').count()
        closed_count = wo_qs.filter(status='CLOSED').count()
        rejected_count = wo_qs.filter(status='REJECTED').count()

        if work_orders_count > 0:
            approval_ratio = (approved_count + closed_count) / work_orders_count
            rejection_penalty = (rejected_count / work_orders_count) * 0.5
            work_order_score = round(max((approval_ratio - rejection_penalty) * 100, 0), 2)
        else:
            work_order_score = 0

        # ------------------------------------------------------
        # 4. ONBOARDING / DOCUMENT SCORE
        # ------------------------------------------------------
        onboarding = OnboardingRequest.objects.filter(
            contractor=contractor,
            status='APPROVED',
        ).order_by('-approved_at').first()

        if onboarding:
            docs = onboarding.document_requirements.all()
            total_docs = docs.count()

            if total_docs == 0:
                onboarding_score = 100.0
            else:
                # Count both UPLOADED and VERIFIED as compliant
                completed_docs = docs.filter(status__in=['VERIFIED', 'UPLOADED']).count()
                onboarding_score = round((completed_docs / total_docs) * 100, 2)
        else:
            onboarding_score = 0

        overall_score = round(
            onboarding_score   * 0.25 +
            training_score     * 0.25 +
            inspection_score   * 0.30 +
            work_order_score   * 0.20,
            2,
        )

        if overall_score >= 90:
            rating, risk_level = 'Excellent', 'LOW'
        elif overall_score >= 75:
            rating, risk_level = 'Good', 'LOW'
        elif overall_score >= 60:
            rating, risk_level = 'Needs Improvement', 'MEDIUM'
        else:
            rating, risk_level = 'Poor', 'HIGH'

        return {
            'overall_score': overall_score,
            'rating': rating,
            'risk_level': risk_level,
            'onboarding_score': onboarding_score,
            'training_score': training_score,
            'inspection_score': inspection_score,
            'work_order_score': work_order_score,
            'inspections_count': inspections_count,
            'work_orders_count': work_orders_count,
            'training_count': training_count,
        }


class ContractorPerformanceDetailView(LoginRequiredMixin, DetailView):
    model = Contractor
    template_name = 'contractor/performance_detail.html'
    context_object_name = 'contractor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contractor = self.get_object()

        today = timezone.now().date()
        month = int(self.request.GET.get('month', today.month))
        year = int(self.request.GET.get('year', today.year))

        dashboard = ContractorPerformanceDashboardView()
        metrics = dashboard._calculate_live_metrics(
            contractor,
            date(year, month, 1),
            date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1),
        )

        context['latest_score'] = metrics['overall_score']
        context['latest_rating'] = metrics['rating']
        context['latest_risk'] = metrics['risk_level']
        context['latest_onboarding_score'] = metrics['onboarding_score']
        context['latest_training_score'] = metrics['training_score']
        context['latest_inspection_score'] = metrics['inspection_score']
        context['latest_work_order_score'] = metrics['work_order_score']
        context['inspections_count'] = metrics['inspections_count']
        context['work_orders_count'] = metrics['work_orders_count']
        context['training_count'] = metrics['training_count']

        context['current_month'] = month
        context['current_year'] = year

        trend = []
        for i in range(11, -1, -1):
            m = month - i
            y = year
            while m <= 0:
                m += 12
                y -= 1

            start = date(y, m, 1)
            end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)

            live = dashboard._calculate_live_metrics(contractor, start, end)
            trend.append({
                'period': f"{m}/{y}",
                'overall_score': live['overall_score'],
                'rating': live['rating'],
                'onboarding_score': live['onboarding_score'],
                'training_score': live['training_score'],
                'inspection_score': live['inspection_score'],
                'work_order_score': live['work_order_score'],
            })
        context['metrics'] = trend

        return context


class ContractorOverviewDashboardView(LoginRequiredMixin, TemplateView):
    """
    Contractor Analytics Dashboard — LIVE performance data.
    """
    template_name = 'contractor/reports/overview_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from apps.organizations.models import Plant
        from datetime import timedelta, date

        today = timezone.now().date()

        _live_engine = ContractorPerformanceDashboardView()

        def _avg(lst):
            return round(sum(lst) / len(lst), 1) if lst else 0

        plant_id = self.request.GET.get('plant')
        selected_plant = None
        if plant_id:
            selected_plant = Plant.objects.filter(id=plant_id).first()

        contractors_qs = Contractor.objects.all()
        if selected_plant:
            contractors_qs = contractors_qs.filter(
                work_orders__plant=selected_plant
            ).distinct()

        total_contractors = contractors_qs.count()
        active_contractors = contractors_qs.filter(is_active=True).count()
        inactive_contractors = contractors_qs.filter(is_active=False).count()

        onboarding_qs = OnboardingRequest.objects.all()
        if selected_plant:
            onboarding_qs = onboarding_qs.filter(
                contractor__work_orders__plant=selected_plant
            ).distinct()

        pending_approval = onboarding_qs.filter(status__in=['PENDING', 'DRAFT']).count()
        rejected_contractors = onboarding_qs.filter(status='REJECTED').count()

        context['overview'] = {
            'total_contractors': total_contractors,
            'active_contractors': active_contractors,
            'inactive_contractors': inactive_contractors,
            'pending_approval': pending_approval,
            'rejected_contractors': rejected_contractors,
        }

        pre_qual_qs = ContractorPreQualification.objects.filter(status='APPROVED')
        if selected_plant:
            pre_qual_qs = pre_qual_qs.filter(
                contractor__work_orders__plant=selected_plant
            ).distinct()

        context['risk_stats'] = {
            'high_risk_contractors': pre_qual_qs.filter(risk_level='HIGH').count(),
            'critical_risk_contractors': pre_qual_qs.filter(risk_level='CRITICAL').count(),
            'medium_risk_contractors': pre_qual_qs.filter(risk_level='MEDIUM').count(),
            'low_risk_contractors': pre_qual_qs.filter(risk_level='LOW').count(),
        }

        doc_qs = OnboardingDocumentRequirement.objects.all()
        if selected_plant:
            doc_qs = doc_qs.filter(
                onboarding__contractor__work_orders__plant=selected_plant
            ).distinct()

        context['document_stats'] = {
            'valid_documents': doc_qs.filter(status='VERIFIED').count(),
            'expiring_soon_documents': doc_qs.filter(status='UPLOADED').count(),
            'expired_documents': doc_qs.filter(status='REJECTED').count(),
            'pending_documents': doc_qs.filter(status='PENDING').count(),
        }

        current_month = today.month
        current_year = today.year

        live_period_start = date(current_year, current_month, 1)
        if current_month == 12:
            live_period_end = date(current_year + 1, 1, 1)
        else:
            live_period_end = date(current_year, current_month + 1, 1)

        live_scores = []
        live_compliance_scores = {
            'onboarding': [],
            'training': [],
            'inspection': [],
            'work_order': [],
        }

        for c in contractors_qs:
            lm = _live_engine._calculate_live_metrics(
                c, live_period_start, live_period_end
            )
            if lm is None:
                continue
            live_scores.append(lm['overall_score'])
            live_compliance_scores['onboarding'].append(lm['onboarding_score'])
            live_compliance_scores['training'].append(lm['training_score'])
            live_compliance_scores['inspection'].append(lm['inspection_score'])
            live_compliance_scores['work_order'].append(lm['work_order_score'])

        context['performance_stats'] = {
            'avg_performance_score': _avg(live_scores),
            'excellent_count': len([s for s in live_scores if s >= 90]),
            'good_count': len([s for s in live_scores if 75 <= s < 90]),
            'needs_improvement_count': len([s for s in live_scores if 60 <= s < 75]),
            'poor_count': len([s for s in live_scores if s < 60]),
        }

        total_onb = onboarding_qs.count()
        approved_onb = onboarding_qs.filter(status='APPROVED').count()
        approval_rate = round((approved_onb / total_onb * 100), 1) if total_onb else 0
        context['approval_rate'] = approval_rate

        context['avg_compliance'] = {
            'onboarding': _avg(live_compliance_scores['onboarding']),
            'training':   _avg(live_compliance_scores['training']),
            'inspection': _avg(live_compliance_scores['inspection']),
            'work_order': _avg(live_compliance_scores['work_order']),
        }

        trend_labels = []
        trend_values = []

        for i in range(5, -1, -1):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1

            month_start = date(y, m, 1)
            if m == 12:
                month_end = date(y + 1, 1, 1)
            else:
                month_end = date(y, m + 1, 1)

            month_scores = []
            for c in contractors_qs:
                lm = _live_engine._calculate_live_metrics(c, month_start, month_end)
                if lm is not None:
                    month_scores.append(lm['overall_score'])

            trend_labels.append(date(y, m, 1).strftime('%b %Y'))
            trend_values.append(_avg(month_scores))

        context['trend_chart_data'] = {
            'labels': trend_labels,
            'values': trend_values,
        }

        monthly_labels = []
        monthly_wo = []
        monthly_insp = []
        monthly_train = []

        for i in range(5, -1, -1):
            d = today.replace(day=1) - timedelta(days=i * 30)
            m_start = d.replace(day=1)

            if m_start.month == 12:
                m_end = m_start.replace(year=m_start.year + 1, month=1, day=1)
            else:
                m_end = m_start.replace(month=m_start.month + 1, day=1)

            monthly_labels.append(d.strftime('%b %Y'))

            wo_m = WorkOrder.objects.filter(
                created_at__gte=m_start, created_at__lt=m_end
            )
            insp_m = ContractorInspection.objects.filter(
                created_at__gte=m_start, created_at__lt=m_end
            )
            ts_m = TrainingSignOff.objects.filter(
                created_at__gte=m_start, created_at__lt=m_end
            )

            if selected_plant:
                wo_m = wo_m.filter(plant=selected_plant)
                insp_m = insp_m.filter(plant=selected_plant)

            monthly_wo.append(wo_m.count())
            monthly_insp.append(insp_m.count())
            monthly_train.append(ts_m.count())

        context['monthly_activity'] = {
            'labels': monthly_labels,
            'work_orders': monthly_wo,
            'inspections': monthly_insp,
            'trainings': monthly_train,
        }

        context['document_chart_data'] = {
            'labels': ['Valid', 'Expiring Soon', 'Expired', 'Pending'],
            'values': [
                context['document_stats']['valid_documents'],
                context['document_stats']['expiring_soon_documents'],
                context['document_stats']['expired_documents'],
                context['document_stats']['pending_documents'],
            ],
        }

        insp_qs = ContractorInspection.objects.all()
        if selected_plant:
            insp_qs = insp_qs.filter(plant=selected_plant)

        context['inspection_chart_data'] = {
            'labels': ['Scheduled', 'In Progress', 'Closed', 'Overdue', 'Cancelled'],
            'values': [
                insp_qs.filter(status='SCHEDULED').count(),
                insp_qs.filter(status='IN_PROGRESS').count(),
                insp_qs.filter(status='CLOSED').count(),
                insp_qs.filter(status='OVERDUE').count(),
                insp_qs.filter(status='CANCELLED').count(),
            ],
        }

        context['plants'] = Plant.objects.filter(is_active=True).order_by('name')
        context['selected_plant'] = plant_id

        return context


class ContractorReportsView(LoginRequiredMixin, TemplateView):
    """
    Reports listing and generation page.
    """
    template_name = 'contractor/reports/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['contractors'] = Contractor.objects.filter(
            is_active=True
        ).order_by('contractor_name')

        context['reports'] = ContractorReport.objects.select_related(
            'contractor', 'generated_by'
        ).order_by('-generated_at')[:3]

        return context


# ==========================================================
# OVERALL CONTRACTOR REPORT GENERATOR (PDF / Excel / CSV)
# ==========================================================

import os
from django.core.files.base import ContentFile


class GenerateContractorOverallReportView(LoginRequiredMixin, View):
    """
    Generate a detailed contractor report in CAPA-style white/grey format.
    Supports PDF, Excel, CSV output formats.
    """

    def post(self, request):
        contractor_id = request.POST.get('contractor')
        report_format = request.POST.get('report_format', 'PDF')

        if not contractor_id:
            messages.error(request, 'Please select a contractor.')
            return redirect('contractor:reports_list')

        contractor = get_object_or_404(Contractor, id=contractor_id)
        data = self._gather_contractor_data(contractor)

        report = ContractorReport.objects.create(
            report_type='CONTRACTOR_OVERVIEW',
            report_format=report_format,
            contractor=contractor,
            generated_by=request.user,
        )

        if report_format == 'PDF':
            return self._generate_pdf_report(request, report, contractor, data)
        elif report_format == 'EXCEL':
            return self._generate_excel_report(request, report, contractor, data)
        else:
            return self._generate_csv_report(request, report, contractor, data)

    def _gather_contractor_data(self, contractor):
        """Gather all data for the contractor report."""

        # ---- 1. REGISTRATION ----
        registration = {
            'contractor_code': contractor.contractor_code,
            'contractor_name': contractor.contractor_name,
            'contractor_type': contractor.get_contractor_type_display(),
            'registration_number': contractor.registration_number or 'N/A',
            'pan_number': contractor.pan_number or 'N/A',
            'gstin': contractor.gstin or 'N/A',
            'establishment_year': contractor.establishment_year or 'N/A',
            'contact_person': contractor.contact_person,
            'designation': contractor.designation,
            'mobile': contractor.mobile,
            'email': contractor.email,
            'alternate_mobile': contractor.alternate_mobile or 'N/A',
            'address_line1': contractor.address_line1,
            'address_line2': contractor.address_line2 or '',
            'city': contractor.city,
            'state': contractor.state,
            'country': contractor.country,
            'pincode': contractor.pincode,
            'nature_of_business': contractor.nature_of_business,
            'work_category': contractor.get_work_category_display(),
            'service_description': contractor.service_description,
            'years_of_experience': contractor.years_of_experience or 0,
            'number_of_workers': contractor.number_of_workers or 0,
            'ehs_officer_name': contractor.ehs_officer_name,
            'ehs_designation': contractor.ehs_designation or 'N/A',
            'ehs_mobile': contractor.ehs_mobile,
            'ehs_email': contractor.ehs_email,
            'is_active': contractor.is_active,
            'created_at': contractor.created_at,
        }

        # ---- 2. ONBOARDING ----
        onboarding = OnboardingRequest.objects.filter(
            contractor=contractor, status='APPROVED'
        ).order_by('-created_at').first()

        if not onboarding:
            onboarding = OnboardingRequest.objects.filter(
                contractor=contractor
            ).order_by('-created_at').first()

        onboarding_data = None
        if onboarding:
            doc_requirements = OnboardingDocumentRequirement.objects.filter(
                onboarding=onboarding
            ).select_related('document_type', 'uploaded_by', 'verified_by')

            documents = []
            for doc in doc_requirements:
                file_path = None
                file_name = None
                has_file = False
                is_image = False

                if doc.document_file:
                    try:
                        file_path = doc.document_file.path
                        file_name = doc.document_file.name.split('/')[-1]
                        has_file = True
                        is_image = file_name.lower().endswith(
                            ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
                        )
                    except Exception:
                        pass

                documents.append({
                    'document_name': doc.document_type.name,
                    'document_code': doc.document_type.code,
                    'description': doc.document_type.description or '',
                    'is_required': doc.is_required,
                    'status': doc.get_status_display(),
                    'has_file': has_file,
                    'file_path': file_path,
                    'file_name': file_name,
                    'is_image': is_image,
                    'uploaded_by': doc.uploaded_by.get_full_name() if doc.uploaded_by else 'N/A',
                    'uploaded_at': doc.uploaded_at,
                    'verified_by': doc.verified_by.get_full_name() if doc.verified_by else 'N/A',
                    'verified_at': doc.verified_at,
                    'comments': doc.comments or '',
                })

            prequal_questions = []
            if onboarding.pre_qualification_answers:
                for q_id, answer in onboarding.pre_qualification_answers.items():
                    try:
                        question = PreQualificationQuestion.objects.get(id=int(q_id))
                    except (PreQualificationQuestion.DoesNotExist, ValueError):
                        continue

                    if isinstance(answer, bool):
                        display_answer = "Yes" if answer else "No"
                        is_answered = True
                    elif answer is None or str(answer).strip() == "":
                        display_answer = "Not Answered"
                        is_answered = False
                    else:
                        display_answer = str(answer).strip()
                        is_answered = True

                    remark = ""
                    if getattr(onboarding, "question_remarks", None):
                        remark = onboarding.question_remarks.get(str(q_id), "") or ""

                    prequal_questions.append({
                        "sequence": question.sequence,
                        "question_text": question.question,
                        "question_type": question.get_question_type_display(),
                        "is_mandatory": question.is_mandatory,
                        "answer": display_answer,
                        "is_answered": is_answered,
                        "remark": remark,
                    })

                prequal_questions.sort(key=lambda x: x["sequence"])

            onboarding_data = {
                'status': onboarding.get_status_display(),
                'is_approved': onboarding.status == 'APPROVED',
                'submitted_by': onboarding.submitted_by.get_full_name() if onboarding.submitted_by else 'N/A',
                'submitted_at': onboarding.submitted_at,
                'approved_by': onboarding.approved_by.get_full_name() if onboarding.approved_by else 'N/A',
                'approved_at': onboarding.approved_at,
                'rejection_reason': onboarding.rejection_reason or '',
                'notes': onboarding.notes or '',
                'documents': documents,
                'total_documents': len(documents),
                'completed_documents': len([
                    d for d in documents if d['status'] in ['Verified', 'Uploaded']
                ]),
                'uploaded_documents': len([d for d in documents if d['has_file']]),
                'prequal_questions': prequal_questions,
                'total_prequal_questions': len(prequal_questions),
                'answered_prequal_questions': len([q for q in prequal_questions if q["is_answered"]]),
            }

        # ---- 3. WORK ORDERS ----
        work_orders = WorkOrder.objects.filter(
            contractor=contractor
        ).select_related(
            'plant', 'department', 'company_representative',
            'approved_by', 'created_by'
        ).order_by('-created_at')

        wo_list = []
        for wo in work_orders:
            wo_list.append({
                'work_order_number': wo.work_order_number,
                'contract_number': wo.contract_number or 'N/A',
                'work_description': wo.work_description or 'N/A',
                'work_category': wo.get_work_category_display(),
                'plant': wo.plant.name if wo.plant else 'N/A',
                'department': wo.department.name if wo.department else 'N/A',
                'location': wo.location or 'N/A',
                'start_date': wo.start_date,
                'end_date': wo.end_date,
                'number_of_workers': wo.number_of_workers,
                'contractor_supervisor': wo.contractor_supervisor or 'N/A',
                'contractor_supervisor_contact': wo.contractor_supervisor_contact or 'N/A',
                'contractor_supervisor_email': wo.contractor_supervisor_email or 'N/A',
                'company_representative': wo.company_representative.get_full_name() if wo.company_representative else 'N/A',
                'risk_level': wo.get_risk_level_display(),
                'status': wo.get_status_display(),
                'created_by': wo.created_by.get_full_name() if wo.created_by else 'N/A',
                'created_at': wo.created_at,
                'approved_by': wo.approved_by.get_full_name() if wo.approved_by else 'N/A',
                'approved_at': wo.approved_at,
                'closure_remarks': wo.closure_remarks or '',
                'attachment_path': self._safe_file_path(wo.attachment),
                'attachment_name': wo.attachment_name or '',
            })

        # ---- 4. TRAINING SIGN-OFFS ----
        training_signoffs = TrainingSignOff.objects.filter(
            contractor=contractor
        ).select_related(
            'session', 'session__topic', 'work_order',
            'company_representative', 'created_by'
        ).order_by('-created_at')

        training_list = []
        for ts in training_signoffs:
            topic_title = 'N/A'
            topic_description = ''
            session_no = 'N/A'
            training_date = ts.signoff_date

            if ts.session:
                session_no = ts.session.session_no
                if hasattr(ts.session, 'topic') and ts.session.topic:
                    topic_title = ts.session.topic.topic_title
                    topic_description = getattr(ts.session.topic, 'description', '') or ''
                if hasattr(ts.session, 'planned_date') and ts.session.planned_date:
                    training_date = ts.session.planned_date

            training_list.append({
                'signoff_number': ts.signoff_number,
                'session_no': session_no,
                'topic_title': topic_title,
                'topic_description': topic_description,
                'training_date': training_date,
                'work_order': ts.work_order.work_order_number if ts.work_order else 'N/A',
                'contractor_representative': ts.contractor_representative or 'N/A',
                'contractor_representative_designation': ts.contractor_representative_designation or 'N/A',
                'number_of_workers': ts.number_of_workers,
                'company_declaration': ts.company_declaration,
                'company_representative': ts.company_representative.get_full_name() if ts.company_representative else 'N/A',
                'company_representative_designation': ts.company_representative_designation or 'N/A',
                'company_signature_path': self._safe_file_path(ts.company_signature),
                'contractor_declaration': ts.contractor_declaration,
                'contractor_supervisor': ts.contractor_supervisor or 'N/A',
                'contractor_supervisor_designation': ts.contractor_supervisor_designation or 'N/A',
                'status': ts.get_status_display(),
                'supporting_document_path': self._safe_file_path(ts.supporting_documents),
                'created_by': ts.created_by.get_full_name() if ts.created_by else 'N/A',
                'created_at': ts.created_at,
            })

        # ---- 5. INSPECTIONS ----
        inspections = ContractorInspection.objects.filter(
            contractor=contractor
        ).select_related(
            'plant', 'zone', 'location', 'sublocation', 'department',
            'assigned_to', 'assigned_by', 'work_order'
        ).prefetch_related(
            'selected_questions', 'responses__question'
        ).order_by('-created_at')

        inspection_list = []
        for insp in inspections:
            responses_by_category = {}
            all_responses = insp.responses.select_related('question').all()

            for resp in all_responses:
                cat = resp.question.get_category_display()
                if cat not in responses_by_category:
                    responses_by_category[cat] = []
                responses_by_category[cat].append({
                    'question_text': resp.question.question_text,
                    'answer': resp.get_answer_display(),
                    'answer_raw': resp.answer,
                    'remarks': resp.remarks or '',
                    'photo_path': self._safe_file_path(resp.photo),
                })

            total_questions = insp.selected_questions.count()
            yes_count = all_responses.filter(answer='YES').count()
            no_count = all_responses.filter(answer='NO').count()
            compliance_score = round((yes_count / total_questions) * 100, 1) if total_questions > 0 else 0

            inspection_list.append({
                'inspection_code': insp.inspection_code,
                'plant': insp.plant.name if insp.plant else 'N/A',
                'zone': insp.zone.name if insp.zone else 'N/A',
                'location': insp.location.name if insp.location else 'N/A',
                'department': insp.department.name if insp.department else 'N/A',
                'work_order': insp.work_order.work_order_number if insp.work_order else 'N/A',
                'assigned_to': insp.assigned_to.get_full_name() if insp.assigned_to else 'N/A',
                'contractor_supervisor': insp.contractor_supervisor or 'N/A',
                'contractor_supervisor_mobile': insp.contractor_supervisor_mobile or 'N/A',
                'number_of_workers': insp.number_of_workers,
                'start_date': insp.inspection_start_date,
                'end_date': insp.inspection_end_date,
                'status': insp.get_status_display(),
                'notes': insp.notes or '',
                'total_questions': total_questions,
                'yes_count': yes_count,
                'no_count': no_count,
                'compliance_score': compliance_score,
                'rating': self._get_rating(compliance_score),
                'responses_by_category': responses_by_category,
                'created_at': insp.created_at,
            })

        # ---- 6. PERFORMANCE (LIVE) ----
        performance_data = None
        performance_history = []
        try:
            perf_engine = ContractorPerformanceDashboardView()
            today_d = timezone.now().date()
            period_start = date(today_d.year, today_d.month, 1)
            if today_d.month == 12:
                period_end = date(today_d.year + 1, 1, 1)
            else:
                period_end = date(today_d.year, today_d.month + 1, 1)

            live = perf_engine._calculate_live_metrics(contractor, period_start, period_end)
            performance_data = {
                'overall_score': live['overall_score'],
                'rating': live['rating'],
                'risk_level': live['risk_level'],
                'onboarding_score': live['onboarding_score'],
                'training_score': live['training_score'],
                'inspection_score': live['inspection_score'],
                'work_order_score': live['work_order_score'],
                'inspections_count': live['inspections_count'],
                'work_orders_count': live['work_orders_count'],
                'period': f"{today_d.month}/{today_d.year}",
                'calculated_at': timezone.now(),
            }

            for i in range(12):
                m = today_d.month - i
                y = today_d.year
                while m <= 0:
                    m += 12
                    y -= 1
                m_start = date(y, m, 1)
                m_end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
                live = perf_engine._calculate_live_metrics(contractor, m_start, m_end)
                performance_history.append({
                    'period': f"{m}/{y}",
                    'overall_score': live['overall_score'],
                    'rating': live['rating'],
                    'onboarding_score': live['onboarding_score'],
                    'training_score': live['training_score'],
                    'inspection_score': live['inspection_score'],
                    'work_order_score': live['work_order_score'],
                })
        except Exception as e:
            logger.error(f"Live performance calculation failed for report: {e}")

        return {
            'generated_at': timezone.now(),
            'registration': registration,
            'onboarding': onboarding_data,
            'work_orders': wo_list,
            'training_signoffs': training_list,
            'inspections': inspection_list,
            'performance': performance_data,
            'performance_history': performance_history,
            'summary': {
                'total_work_orders': len(wo_list),
                'total_training': len(training_list),
                'total_inspections': len(inspection_list),
            }
        }

    def _safe_file_path(self, file_field):
        if not file_field:
            return None
        try:
            return file_field.path
        except Exception:
            return None

    def _get_rating(self, score):
        if score >= 90:
            return 'Excellent'
        elif score >= 75:
            return 'Good'
        elif score >= 60:
            return 'Needs Improvement'
        return 'Poor'

    def _safe_embed_image(self, elements, file_path, value_style,
                          max_width_mm=60, max_height_mm=45, caption=None):
        from reportlab.platypus import Image as RLImage, Paragraph, Spacer
        from reportlab.lib.units import mm

        if not file_path or not os.path.exists(file_path):
            elements.append(Paragraph(
                f"<i>{caption or 'File'}: not available.</i>", value_style
            ))
            return

        ext = os.path.splitext(file_path)[1].lower()
        image_exts = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')

        if ext not in image_exts:
            elements.append(Paragraph(
                f"<i>{caption or 'File'}: {os.path.basename(file_path)} "
                f"(attached, not previewable inline)</i>", value_style
            ))
            return

        try:
            from PIL import Image as PILImage
            with PILImage.open(file_path) as im:
                img_w, img_h = im.size

            max_w = max_width_mm * mm
            max_h = max_height_mm * mm
            ratio = min(max_w / img_w, max_h / img_h, 1.0)
            draw_w = img_w * ratio
            draw_h = img_h * ratio

            if caption:
                elements.append(Paragraph(f"<b>{caption}</b>", value_style))
            elements.append(RLImage(file_path, width=draw_w, height=draw_h))
            elements.append(Spacer(1, 4))
        except Exception as e:
            logger.warning(f"Could not embed image {file_path}: {e}")
            elements.append(Paragraph(
                f"<i>{caption or 'Image'}: could not be rendered.</i>", value_style
            ))

    def _generate_pdf_report(self, request, report, contractor, data):
        try:
            from io import BytesIO
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm, inch
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_LEFT, TA_CENTER
            from reportlab.platypus import (
                Paragraph, Spacer, Table, TableStyle, PageBreak,
                SimpleDocTemplate,
            )
            from reportlab.pdfgen import canvas
            from .pdf_generators import get_val

            buffer = BytesIO()

            contractor_code = contractor.contractor_code
            contractor_name = contractor.contractor_name
            generated_date = timezone.now().strftime("%d-%m-%Y")

            BORDER_COLOR = colors.HexColor("#DEE2E6")
            HEADER_BG = colors.HexColor("#F8F9FA")

            LM = 15 * mm
            RM = 15 * mm
            TM = 1.6 * inch + 22 * mm
            BM = 25 * mm
            drawable_width = A4[0] - LM - RM
            col4 = drawable_width / 4

            styles = getSampleStyleSheet()
            primary_text_color = colors.HexColor("#212529")
            secondary_text_color = colors.HexColor("#495057")

            styles.add(ParagraphStyle(
                name="HeaderTitle", fontSize=10, fontName="Helvetica-Bold",
                alignment=TA_CENTER, textColor=primary_text_color,
            ))
            styles.add(ParagraphStyle(
                name="HeaderInfo", fontSize=9, fontName="Helvetica",
                alignment=TA_LEFT, textColor=secondary_text_color, leading=12,
            ))
            styles.add(ParagraphStyle(
                name="SectionHeader", fontSize=10, fontName="Helvetica-Bold",
                textColor=primary_text_color, spaceBefore=10, spaceAfter=4,
                alignment=TA_LEFT,
            ))
            styles.add(ParagraphStyle(
                name="SubSectionHeader", fontSize=9, fontName="Helvetica-Bold",
                textColor=secondary_text_color, spaceBefore=6, spaceAfter=3,
                alignment=TA_LEFT,
            ))
            styles.add(ParagraphStyle(
                name="Label", fontSize=9, fontName="Helvetica-Bold",
                textColor=primary_text_color, alignment=TA_LEFT,
            ))
            styles.add(ParagraphStyle(
                name="Value", fontSize=9, fontName="Helvetica",
                textColor=secondary_text_color, alignment=TA_LEFT, leading=12,
            ))
            styles.add(ParagraphStyle(
                name="FooterText", fontSize=8, fontName="Helvetica",
                textColor=colors.darkgrey, alignment=TA_CENTER,
            ))
            styles.add(ParagraphStyle(
                name="SmallValue", fontSize=7.5, fontName="Helvetica",
                textColor=colors.HexColor("#334155"), leading=9,
            ))

            class NumberedCanvas(canvas.Canvas):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self._saved_page_states = []

                def showPage(self):
                    self._saved_page_states.append(dict(self.__dict__))
                    self._startPage()

                def save(self):
                    num_pages = len(self._saved_page_states)
                    for state in self._saved_page_states:
                        self.__dict__.update(state)
                        self.draw_page_number(num_pages)
                        super().showPage()
                    super().save()

                def draw_page_number(self, page_count):
                    self.setFont("Helvetica", 9)
                    self.setFillColor(colors.darkgrey)
                    self.drawRightString(
                        200 * mm, 15 * mm,
                        f"Page {self._pageNumber} of {page_count}"
                    )

            logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.jpg")
            if os.path.exists(logo_path):
                from reportlab.platypus import Image as RLImage
                logo_img = RLImage(logo_path, width=2.2 * inch, height=1.6 * inch)
            else:
                logo_img = Paragraph("<b>COMPANY LOGO</b>", styles["HeaderTitle"])

            header_data = [
                [
                    logo_img,
                    Paragraph("<b>EHS MANAGEMENT SYSTEM [QEMS]</b>", styles["HeaderTitle"]),
                    Paragraph(f"DOC NO: {contractor_code}", styles["HeaderInfo"]),
                ],
                [
                    "",
                    Paragraph("<b>CONTRACTOR OVERALL REPORT</b>", styles["HeaderTitle"]),
                    Paragraph(
                        f"REV NO: 001 &amp;<br/>DATE: {generated_date}",
                        styles["HeaderInfo"],
                    ),
                ],
            ]
            header_table = Table(
                header_data,
                colWidths=[
                    drawable_width * 0.2875,
                    drawable_width * 0.4875,
                    drawable_width * 0.225,
                ],
                rowHeights=[0.8 * inch, 0.8 * inch],
            )
            header_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("SPAN", (0, 0), (0, 1)),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))

            def draw_header(canvas_obj, doc):
                canvas_obj.saveState()
                w, h = header_table.wrap(doc.width, doc.topMargin)
                header_table.drawOn(
                    canvas_obj,
                    doc.leftMargin,
                    doc.height + doc.topMargin - h + 5 * mm,
                )
                canvas_obj.restoreState()

            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=RM,
                leftMargin=LM,
                topMargin=TM,
                bottomMargin=BM,
                title=f"Contractor Report - {contractor_name}",
                author="EHS-360",
            )

            def kv_table(rows):
                t = Table(rows, colWidths=[col4] * 4)
                t.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                return t

            def single_cell_table(header_text, body_html, extra_bottom_pad=8):
                t = Table([
                    [Paragraph(f"<b>{header_text}</b>", styles["Label"])],
                    [Paragraph(body_html, styles["Value"])],
                ], colWidths=[drawable_width])
                t.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), extra_bottom_pad),
                    ("BACKGROUND", (0, 0), (0, 0), HEADER_BG),
                ]))
                return t

            def footer_paragraph():
                text = (
                    "Document generated from EHS-360 System on "
                    + timezone.now().strftime("%d-%b-%Y at %H:%M hrs")
                )
                return Paragraph(text, styles["FooterText"])

            story = []
            story.append(Spacer(1, 4 * mm))

            # ==========================================================
            # 1. CONTRACTOR REGISTRATION
            # ==========================================================
            story.append(Paragraph("<b>1. Contractor Registration Details</b>", styles["SectionHeader"]))
            reg = data["registration"]

            story.append(Paragraph("Basic Information", styles["SubSectionHeader"]))
            story.append(kv_table([
                [Paragraph("<b>Contractor Name:</b>", styles["Label"]),
                 Paragraph(get_val(reg["contractor_name"]), styles["Value"]),
                 Paragraph("<b>Contractor Code:</b>", styles["Label"]),
                 Paragraph(get_val(reg["contractor_code"]), styles["Value"])],
                [Paragraph("<b>Contractor Type:</b>", styles["Label"]),
                 Paragraph(get_val(reg["contractor_type"]), styles["Value"]),
                 Paragraph("<b>Work Category:</b>", styles["Label"]),
                 Paragraph(get_val(reg["work_category"]), styles["Value"])],
                [Paragraph("<b>Registration No:</b>", styles["Label"]),
                 Paragraph(get_val(reg["registration_number"]), styles["Value"]),
                 Paragraph("<b>PAN Number:</b>", styles["Label"]),
                 Paragraph(get_val(reg["pan_number"]), styles["Value"])],
                [Paragraph("<b>GSTIN:</b>", styles["Label"]),
                 Paragraph(get_val(reg["gstin"]), styles["Value"]),
                 Paragraph("<b>Establishment Year:</b>", styles["Label"]),
                 Paragraph(str(reg["establishment_year"]), styles["Value"])],
            ]))

            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph("Contact Information", styles["SubSectionHeader"]))
            story.append(kv_table([
                [Paragraph("<b>Contact Person:</b>", styles["Label"]),
                 Paragraph(get_val(reg["contact_person"]), styles["Value"]),
                 Paragraph("<b>Designation:</b>", styles["Label"]),
                 Paragraph(get_val(reg["designation"]), styles["Value"])],
                [Paragraph("<b>Mobile:</b>", styles["Label"]),
                 Paragraph(get_val(reg["mobile"]), styles["Value"]),
                 Paragraph("<b>Alternate Mobile:</b>", styles["Label"]),
                 Paragraph(get_val(reg["alternate_mobile"]), styles["Value"])],
                [Paragraph("<b>Email:</b>", styles["Label"]),
                 Paragraph(get_val(reg["email"]), styles["Value"]),
                 Paragraph("<b>Status:</b>", styles["Label"]),
                 Paragraph("Active" if reg["is_active"] else "Inactive", styles["Value"])],
                [Paragraph("<b>Address Line 1:</b>", styles["Label"]),
                 Paragraph(get_val(reg["address_line1"]), styles["Value"]),
                 Paragraph("<b>Address Line 2:</b>", styles["Label"]),
                 Paragraph(get_val(reg["address_line2"]), styles["Value"])],
                [Paragraph("<b>City:</b>", styles["Label"]),
                 Paragraph(get_val(reg["city"]), styles["Value"]),
                 Paragraph("<b>State:</b>", styles["Label"]),
                 Paragraph(get_val(reg["state"]), styles["Value"])],
                [Paragraph("<b>Country:</b>", styles["Label"]),
                 Paragraph(get_val(reg["country"]), styles["Value"]),
                 Paragraph("<b>Pincode:</b>", styles["Label"]),
                 Paragraph(get_val(reg["pincode"]), styles["Value"])],
            ]))

            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph("Business Information", styles["SubSectionHeader"]))
            story.append(kv_table([
                [Paragraph("<b>Nature of Business:</b>", styles["Label"]),
                 Paragraph(get_val(reg["nature_of_business"]), styles["Value"]),
                 Paragraph("<b>Years of Experience:</b>", styles["Label"]),
                 Paragraph(str(reg["years_of_experience"]), styles["Value"])],
                [Paragraph("<b>Service Description:</b>", styles["Label"]),
                 Paragraph(get_val(reg["service_description"]), styles["Value"]),
                 Paragraph("<b>Number of Workers:</b>", styles["Label"]),
                 Paragraph(str(reg["number_of_workers"]), styles["Value"])],
            ]))

            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph("EHS / Responsible Person", styles["SubSectionHeader"]))
            story.append(kv_table([
                [Paragraph("<b>EHS Officer Name:</b>", styles["Label"]),
                 Paragraph(get_val(reg["ehs_officer_name"]), styles["Value"]),
                 Paragraph("<b>Designation:</b>", styles["Label"]),
                 Paragraph(get_val(reg["ehs_designation"]), styles["Value"])],
                [Paragraph("<b>EHS Mobile:</b>", styles["Label"]),
                 Paragraph(get_val(reg["ehs_mobile"]), styles["Value"]),
                 Paragraph("<b>EHS Email:</b>", styles["Label"]),
                 Paragraph(get_val(reg["ehs_email"]), styles["Value"])],
            ]))

            # ==========================================================
            # 2. ONBOARDING
            # ==========================================================
            story.append(PageBreak())
            story.append(Paragraph("<b>2. Onboarding Requirements</b>", styles["SectionHeader"]))

            if data["onboarding"]:
                ob = data["onboarding"]
                story.append(kv_table([
                    [Paragraph("<b>Status:</b>", styles["Label"]),
                     Paragraph(get_val(ob["status"]), styles["Value"]),
                     Paragraph("<b>Documents:</b>", styles["Label"]),
                     Paragraph(f"{ob['completed_documents']}/{ob['total_documents']} completed",
                               styles["Value"])],
                    [Paragraph("<b>Submitted By:</b>", styles["Label"]),
                     Paragraph(get_val(ob["submitted_by"]), styles["Value"]),
                     Paragraph("<b>Submitted At:</b>", styles["Label"]),
                     Paragraph(ob["submitted_at"].strftime("%d-%m-%Y") if ob["submitted_at"] else "N/A",
                               styles["Value"])],
                    [Paragraph("<b>Approved By:</b>", styles["Label"]),
                     Paragraph(get_val(ob["approved_by"]), styles["Value"]),
                     Paragraph("<b>Approved At:</b>", styles["Label"]),
                     Paragraph(ob["approved_at"].strftime("%d-%m-%Y") if ob["approved_at"] else "N/A",
                               styles["Value"])],
                ]))

                if ob["rejection_reason"]:
                    story.append(Spacer(1, 3 * mm))
                    story.append(single_cell_table("Rejection Reason:", get_val(ob["rejection_reason"])))

                if ob["notes"]:
                    story.append(Spacer(1, 3 * mm))
                    story.append(single_cell_table("Notes:", get_val(ob["notes"])))

                story.append(Spacer(1, 4 * mm))
                story.append(Paragraph(
                    "Pre-Qualification Questions &amp; Answers",
                    styles["SubSectionHeader"],
                ))

                if ob.get("prequal_questions"):
                    pq_data = [[
                        Paragraph("<b>Sr.</b>", styles["Label"]),
                        Paragraph("<b>Question</b>", styles["Label"]),
                        Paragraph("<b>Type</b>", styles["Label"]),
                        Paragraph("<b>Mandatory</b>", styles["Label"]),
                        Paragraph("<b>Answer</b>", styles["Label"]),
                        Paragraph("<b>Remark</b>", styles["Label"]),
                    ]]
                    for idx, q in enumerate(ob["prequal_questions"], 1):
                        pq_data.append([
                            Paragraph(str(idx), styles["Value"]),
                            Paragraph(get_val(q["question_text"])[:120], styles["Value"]),
                            Paragraph(get_val(q["question_type"]), styles["Value"]),
                            Paragraph("Yes" if q["is_mandatory"] else "No", styles["Value"]),
                            Paragraph(get_val(q["answer"]), styles["Value"]),
                            Paragraph(get_val(q["remark"]) if q["remark"] else "-", styles["Value"]),
                        ])

                    pq_table = Table(pq_data, colWidths=[
                        drawable_width * 0.05,
                        drawable_width * 0.42,
                        drawable_width * 0.14,
                        drawable_width * 0.10,
                        drawable_width * 0.15,
                        drawable_width * 0.14,
                    ])
                    pq_table.setStyle(TableStyle([
                        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
                        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]))
                    story.append(pq_table)

                    answered = ob.get("answered_prequal_questions", 0)
                    total_q = ob.get("total_prequal_questions", 0)
                    story.append(Spacer(1, 2))
                    story.append(Paragraph(
                        f"<i>Answered: {answered} / {total_q}</i>",
                        styles["SmallValue"],
                    ))
                else:
                    story.append(Paragraph(
                        "No pre-qualification questions recorded.",
                        styles["Value"],
                    ))

                story.append(Spacer(1, 4 * mm))
                story.append(Paragraph(
                    "Document Requirements &amp; Verification",
                    styles["SubSectionHeader"],
                ))

                if ob["documents"]:
                    doc_data = [[
                        Paragraph("<b>Sr.</b>", styles["Label"]),
                        Paragraph("<b>Document Name</b>", styles["Label"]),
                        Paragraph("<b>Required</b>", styles["Label"]),
                        Paragraph("<b>Status</b>", styles["Label"]),
                        Paragraph("<b>Uploaded By</b>", styles["Label"]),
                        Paragraph("<b>Verified By</b>", styles["Label"]),
                    ]]
                    for idx, d in enumerate(ob["documents"], 1):
                        doc_data.append([
                            Paragraph(str(idx), styles["Value"]),
                            Paragraph(get_val(d["document_name"])[:60], styles["Value"]),
                            Paragraph("Yes" if d["is_required"] else "No", styles["Value"]),
                            Paragraph(get_val(d["status"]), styles["Value"]),
                            Paragraph(get_val(d["uploaded_by"])[:25], styles["Value"]),
                            Paragraph(get_val(d["verified_by"])[:25], styles["Value"]),
                        ])
                    doc_table = Table(doc_data, colWidths=[
                        drawable_width * 0.05,
                        drawable_width * 0.35,
                        drawable_width * 0.09,
                        drawable_width * 0.13,
                        drawable_width * 0.19,
                        drawable_width * 0.19,
                    ])
                    doc_table.setStyle(TableStyle([
                        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
                        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]))
                    story.append(doc_table)

                    story.append(Spacer(1, 4 * mm))
                    story.append(Paragraph("Document Attachments", styles["SubSectionHeader"]))
                    for d in ob["documents"]:
                        if d["has_file"]:
                            self._safe_embed_image(
                                story, d["file_path"], styles["Value"],
                                max_width_mm=70, max_height_mm=50,
                                caption=f"{d['document_name']} ({d['status']})",
                            )
                        else:
                            story.append(Paragraph(
                                f"<i>{d['document_name']}: no file uploaded.</i>",
                                styles["Value"],
                            ))
                        story.append(Spacer(1, 3))
                else:
                    story.append(Paragraph("No document requirements recorded.", styles["Value"]))
            else:
                story.append(Paragraph("No onboarding data available.", styles["Value"]))

            # ==========================================================
            # 3. WORK ORDERS
            # ==========================================================
            story.append(PageBreak())
            story.append(Paragraph("<b>3. Work Orders</b>", styles["SectionHeader"]))

            if data["work_orders"]:
                for idx, wo in enumerate(data["work_orders"], 1):
                    story.append(Paragraph(
                        f"Work Order #{idx}: {wo['work_order_number']}",
                        styles["SubSectionHeader"],
                    ))
                    story.append(kv_table([
                        [Paragraph("<b>Contract No:</b>", styles["Label"]),
                         Paragraph(get_val(wo["contract_number"]), styles["Value"]),
                         Paragraph("<b>Status:</b>", styles["Label"]),
                         Paragraph(get_val(wo["status"]), styles["Value"])],
                        [Paragraph("<b>Plant:</b>", styles["Label"]),
                         Paragraph(get_val(wo["plant"]), styles["Value"]),
                         Paragraph("<b>Department:</b>", styles["Label"]),
                         Paragraph(get_val(wo["department"]), styles["Value"])],
                        [Paragraph("<b>Location:</b>", styles["Label"]),
                         Paragraph(get_val(wo["location"]), styles["Value"]),
                         Paragraph("<b>Risk Level:</b>", styles["Label"]),
                         Paragraph(get_val(wo["risk_level"]), styles["Value"])],
                        [Paragraph("<b>Start Date:</b>", styles["Label"]),
                         Paragraph(wo["start_date"].strftime("%d-%m-%Y") if wo["start_date"] else "N/A",
                                   styles["Value"]),
                         Paragraph("<b>End Date:</b>", styles["Label"]),
                         Paragraph(wo["end_date"].strftime("%d-%m-%Y") if wo["end_date"] else "N/A",
                                   styles["Value"])],
                        [Paragraph("<b>Work Category:</b>", styles["Label"]),
                         Paragraph(get_val(wo["work_category"]), styles["Value"]),
                         Paragraph("<b>Workers:</b>", styles["Label"]),
                         Paragraph(str(wo["number_of_workers"]), styles["Value"])],
                    ]))

                    story.append(Spacer(1, 3))
                    story.append(single_cell_table(
                        "Work Description:",
                        get_val(wo["work_description"]),
                        extra_bottom_pad=6,
                    ))
                    story.append(Spacer(1, 3))

                    story.append(kv_table([
                        [Paragraph("<b>Supervisor:</b>", styles["Label"]),
                         Paragraph(get_val(wo["contractor_supervisor"]), styles["Value"]),
                         Paragraph("<b>Contact:</b>", styles["Label"]),
                         Paragraph(get_val(wo["contractor_supervisor_contact"]), styles["Value"])],
                        [Paragraph("<b>Supervisor Email:</b>", styles["Label"]),
                         Paragraph(get_val(wo["contractor_supervisor_email"]), styles["Value"]),
                         Paragraph("<b>Company Rep:</b>", styles["Label"]),
                         Paragraph(get_val(wo["company_representative"]), styles["Value"])],
                        [Paragraph("<b>Created By:</b>", styles["Label"]),
                         Paragraph(get_val(wo["created_by"]), styles["Value"]),
                         Paragraph("<b>Approved By:</b>", styles["Label"]),
                         Paragraph(get_val(wo["approved_by"]), styles["Value"])],
                    ]))

                    if wo["attachment_path"]:
                        story.append(Spacer(1, 3))
                        self._safe_embed_image(
                            story, wo["attachment_path"], styles["Value"],
                            max_width_mm=70, max_height_mm=50,
                            caption=f"Attachment: {wo['attachment_name'] or 'Work Order Document'}",
                        )

                    if wo["closure_remarks"]:
                        story.append(Spacer(1, 3))
                        story.append(single_cell_table("Closure Remarks:", get_val(wo["closure_remarks"])))

                    story.append(Spacer(1, 8))
            else:
                story.append(Paragraph("No work orders available.", styles["Value"]))

            # ==========================================================
            # 4. TRAINING SIGN-OFFS
            # ==========================================================
            story.append(PageBreak())
            story.append(Paragraph("<b>4. Training Sign-Offs</b>", styles["SectionHeader"]))

            if data["training_signoffs"]:
                for idx, ts in enumerate(data["training_signoffs"], 1):
                    story.append(Paragraph(
                        f"Sign-Off #{idx}: {ts['signoff_number']}",
                        styles["SubSectionHeader"],
                    ))
                    story.append(kv_table([
                        [Paragraph("<b>Session No:</b>", styles["Label"]),
                         Paragraph(get_val(ts["session_no"]), styles["Value"]),
                         Paragraph("<b>Training Date:</b>", styles["Label"]),
                         Paragraph(ts["training_date"].strftime("%d-%m-%Y") if ts["training_date"] else "N/A",
                                   styles["Value"])],
                        [Paragraph("<b>Topic:</b>", styles["Label"]),
                         Paragraph(get_val(ts["topic_title"])[:80], styles["Value"]),
                         Paragraph("<b>Work Order:</b>", styles["Label"]),
                         Paragraph(get_val(ts["work_order"]), styles["Value"])],
                        [Paragraph("<b>Status:</b>", styles["Label"]),
                         Paragraph(get_val(ts["status"]), styles["Value"]),
                         Paragraph("<b>Workers Trained:</b>", styles["Label"]),
                         Paragraph(str(ts["number_of_workers"]), styles["Value"])],
                    ]))

                    story.append(Spacer(1, 3))
                    story.append(Paragraph("Company Sign-Off", styles["SubSectionHeader"]))
                    story.append(kv_table([
                        [Paragraph("<b>Declaration:</b>", styles["Label"]),
                         Paragraph(
                             "I confirm that the above listed contractor and its workers "
                             "have received the required safety training and have been "
                             "made aware of the applicable EHS requirements.",
                             styles["Value"],
                         ),
                         Paragraph("<b>Agreed:</b>", styles["Label"]),
                         Paragraph("Yes" if ts["company_declaration"] else "No", styles["Value"])],
                        [Paragraph("<b>Representative:</b>", styles["Label"]),
                         Paragraph(get_val(ts["company_representative"]), styles["Value"]),
                         Paragraph("<b>Designation:</b>", styles["Label"]),
                         Paragraph(get_val(ts["company_representative_designation"]), styles["Value"])],
                    ]))

                    if ts["company_signature_path"]:
                        story.append(Spacer(1, 3))
                        self._safe_embed_image(
                            story, ts["company_signature_path"], styles["Value"],
                            max_width_mm=50, max_height_mm=25,
                            caption="Company Representative Signature",
                        )

                    story.append(Spacer(1, 4))
                    story.append(Paragraph("Contractor Sign-Off", styles["SubSectionHeader"]))
                    story.append(kv_table([
                        [Paragraph("<b>Declaration:</b>", styles["Label"]),
                         Paragraph(
                             "I confirm that the above listed workers have received "
                             "the required safety training and have understood the "
                             "applicable EHS requirements.",
                             styles["Value"],
                         ),
                         Paragraph("<b>Agreed:</b>", styles["Label"]),
                         Paragraph("Yes" if ts["contractor_declaration"] else "No", styles["Value"])],
                        [Paragraph("<b>Supervisor:</b>", styles["Label"]),
                         Paragraph(get_val(ts["contractor_supervisor"]), styles["Value"]),
                         Paragraph("<b>Designation:</b>", styles["Label"]),
                         Paragraph(get_val(ts["contractor_supervisor_designation"]), styles["Value"])],
                    ]))

                    if ts["supporting_document_path"]:
                        story.append(Spacer(1, 3))
                        self._safe_embed_image(
                            story, ts["supporting_document_path"], styles["Value"],
                            max_width_mm=70, max_height_mm=50,
                            caption="Supporting Document",
                        )

                    story.append(Spacer(1, 8))
            else:
                story.append(Paragraph("No training sign-offs available.", styles["Value"]))

            # ==========================================================
            # 5. INSPECTIONS
            # ==========================================================
            story.append(PageBreak())
            story.append(Paragraph("<b>5. Inspections</b>", styles["SectionHeader"]))

            if data["inspections"]:
                for idx, insp in enumerate(data["inspections"], 1):
                    story.append(Paragraph(
                        f"Inspection #{idx}: {insp['inspection_code']}",
                        styles["SubSectionHeader"],
                    ))
                    story.append(kv_table([
                        [Paragraph("<b>Plant:</b>", styles["Label"]),
                         Paragraph(get_val(insp["plant"]), styles["Value"]),
                         Paragraph("<b>Status:</b>", styles["Label"]),
                         Paragraph(get_val(insp["status"]), styles["Value"])],
                        [Paragraph("<b>Zone:</b>", styles["Label"]),
                         Paragraph(get_val(insp["zone"]), styles["Value"]),
                         Paragraph("<b>Location:</b>", styles["Label"]),
                         Paragraph(get_val(insp["location"]), styles["Value"])],
                        [Paragraph("<b>Department:</b>", styles["Label"]),
                         Paragraph(get_val(insp["department"]), styles["Value"]),
                         Paragraph("<b>Work Order:</b>", styles["Label"]),
                         Paragraph(get_val(insp["work_order"]), styles["Value"])],
                        [Paragraph("<b>Assigned To:</b>", styles["Label"]),
                         Paragraph(get_val(insp["assigned_to"]), styles["Value"]),
                         Paragraph("<b>Supervisor:</b>", styles["Label"]),
                         Paragraph(get_val(insp["contractor_supervisor"]), styles["Value"])],
                        [Paragraph("<b>Start Date:</b>", styles["Label"]),
                         Paragraph(insp["start_date"].strftime("%d-%m-%Y") if insp["start_date"] else "N/A",
                                   styles["Value"]),
                         Paragraph("<b>End Date:</b>", styles["Label"]),
                         Paragraph(insp["end_date"].strftime("%d-%m-%Y") if insp["end_date"] else "N/A",
                                   styles["Value"])],
                    ]))

                    story.append(Spacer(1, 3))
                    score_data = [[
                        Paragraph("<b>Total Q:</b>", styles["Label"]),
                        Paragraph(str(insp["total_questions"]), styles["Value"]),
                        Paragraph("<b>YES:</b>", styles["Label"]),
                        Paragraph(str(insp["yes_count"]), styles["Value"]),
                        Paragraph("<b>NO:</b>", styles["Label"]),
                        Paragraph(str(insp["no_count"]), styles["Value"]),
                        Paragraph("<b>Compliance:</b>", styles["Label"]),
                        Paragraph(f"<b>{insp['compliance_score']}%</b>", styles["Value"]),
                        Paragraph("<b>Rating:</b>", styles["Label"]),
                        Paragraph(get_val(insp["rating"]), styles["Value"]),
                    ]]
                    score_table = Table(
                        score_data,
                        colWidths=[drawable_width * 0.10] * 10,
                    )
                    score_table.setStyle(TableStyle([
                        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
                        ("BACKGROUND", (0, 0), (-1, -1), HEADER_BG),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]))
                    story.append(score_table)

                    if insp["responses_by_category"]:
                        story.append(Spacer(1, 4))
                        story.append(Paragraph("Detailed Responses", styles["SubSectionHeader"]))

                        for cat_name, responses in insp["responses_by_category"].items():
                            story.append(Paragraph(f"<b>{cat_name}</b>", styles["Value"]))
                            story.append(Spacer(1, 2))

                            cat_data = [[
                                Paragraph("<b>Sr.</b>", styles["Label"]),
                                Paragraph("<b>Question</b>", styles["Label"]),
                                Paragraph("<b>Answer</b>", styles["Label"]),
                                Paragraph("<b>Remarks</b>", styles["Label"]),
                            ]]
                            for r_idx, r in enumerate(responses, 1):
                                cat_data.append([
                                    Paragraph(str(r_idx), styles["Value"]),
                                    Paragraph(get_val(r["question_text"])[:90], styles["Value"]),
                                    Paragraph(get_val(r["answer"]), styles["Value"]),
                                    Paragraph(get_val(r["remarks"])[:60], styles["Value"]),
                                ])

                            cat_table = Table(cat_data, colWidths=[
                                drawable_width * 0.05,
                                drawable_width * 0.55,
                                drawable_width * 0.15,
                                drawable_width * 0.25,
                            ])
                            cat_table.setStyle(TableStyle([
                                ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
                                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                                ("TOPPADDING", (0, 0), (-1, -1), 4),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ]))
                            story.append(cat_table)
                            story.append(Spacer(1, 3))

                            for r in responses:
                                if r["photo_path"]:
                                    self._safe_embed_image(
                                        story, r["photo_path"], styles["Value"],
                                        max_width_mm=60, max_height_mm=45,
                                        caption=f"Photo: {r['question_text'][:50]}",
                                    )

                    story.append(Spacer(1, 8))
            else:
                story.append(Paragraph("No inspection data available.", styles["Value"]))

            # ==========================================================
            # 6. PERFORMANCE METRICS
            # ==========================================================
            story.append(PageBreak())
            story.append(Paragraph("<b>6. Performance Metrics</b>", styles["SectionHeader"]))

            if data["performance"]:
                perf = data["performance"]

                story.append(kv_table([
                    [Paragraph("<b>Period:</b>", styles["Label"]),
                     Paragraph(get_val(perf["period"]), styles["Value"]),
                     Paragraph("<b>Overall Score:</b>", styles["Label"]),
                     Paragraph(f"<b>{perf['overall_score']:.1f}%</b>", styles["Value"])],
                    [Paragraph("<b>Rating:</b>", styles["Label"]),
                     Paragraph(get_val(perf["rating"]), styles["Value"]),
                     Paragraph("<b>Risk Level:</b>", styles["Label"]),
                     Paragraph(get_val(perf["risk_level"]), styles["Value"])],
                    [Paragraph("<b>Inspections:</b>", styles["Label"]),
                     Paragraph(str(perf["inspections_count"]), styles["Value"]),
                     Paragraph("<b>Work Orders:</b>", styles["Label"]),
                     Paragraph(str(perf["work_orders_count"]), styles["Value"])],
                ]))

                story.append(Spacer(1, 4))
                story.append(Paragraph("Score Breakdown", styles["SubSectionHeader"]))

                breakdown_data = [
                    [
                        Paragraph("<b>Onboarding</b>", styles["Label"]),
                        Paragraph("<b>Training</b>", styles["Label"]),
                        Paragraph("<b>Inspection</b>", styles["Label"]),
                        Paragraph("<b>Work Order</b>", styles["Label"]),
                    ],
                    [
                        Paragraph(f"{perf['onboarding_score']:.1f}%", styles["Value"]),
                        Paragraph(f"{perf['training_score']:.1f}%", styles["Value"]),
                        Paragraph(f"{perf['inspection_score']:.1f}%", styles["Value"]),
                        Paragraph(f"{perf['work_order_score']:.1f}%", styles["Value"]),
                    ],
                ]
                breakdown_table = Table(breakdown_data, colWidths=[col4] * 4)
                breakdown_table.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
                    ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(breakdown_table)

                if data["performance_history"]:
                    story.append(Spacer(1, 5))
                    story.append(Paragraph(
                        "Performance History (Last 12 Periods)",
                        styles["SubSectionHeader"],
                    ))

                    hist_data = [[
                        Paragraph("<b>Period</b>", styles["Label"]),
                        Paragraph("<b>Overall</b>", styles["Label"]),
                        Paragraph("<b>Rating</b>", styles["Label"]),
                        Paragraph("<b>Onboarding</b>", styles["Label"]),
                        Paragraph("<b>Training</b>", styles["Label"]),
                        Paragraph("<b>Inspection</b>", styles["Label"]),
                        Paragraph("<b>Work Order</b>", styles["Label"]),
                    ]]
                    for h in data["performance_history"]:
                        hist_data.append([
                            Paragraph(get_val(h["period"]), styles["Value"]),
                            Paragraph(f"{h['overall_score']:.1f}%", styles["Value"]),
                            Paragraph(get_val(h["rating"]), styles["Value"]),
                            Paragraph(f"{h['onboarding_score']:.1f}%", styles["Value"]),
                            Paragraph(f"{h['training_score']:.1f}%", styles["Value"]),
                            Paragraph(f"{h['inspection_score']:.1f}%", styles["Value"]),
                            Paragraph(f"{h['work_order_score']:.1f}%", styles["Value"]),
                        ])

                    hist_table = Table(hist_data, colWidths=[
                        drawable_width * 0.13,
                        drawable_width * 0.13,
                        drawable_width * 0.18,
                        drawable_width * 0.14,
                        drawable_width * 0.14,
                        drawable_width * 0.14,
                        drawable_width * 0.14,
                    ])
                    hist_table.setStyle(TableStyle([
                        ("GRID", (0, 0), (-1, -1), 1, BORDER_COLOR),
                        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]))
                    story.append(hist_table)
            else:
                story.append(Paragraph("No performance data available.", styles["Value"]))

            story.append(Spacer(1, 10 * mm))
            story.append(footer_paragraph())

            doc.build(
                story,
                onFirstPage=draw_header,
                onLaterPages=draw_header,
                canvasmaker=NumberedCanvas,
            )

            pdf_content = buffer.getvalue()
            buffer.close()

            report.report_file.save(
                f'contractor_report_{contractor.contractor_code}_{report.id}.pdf',
                ContentFile(pdf_content),
                save=True,
            )

            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = (
                f'attachment; filename="contractor_report_{contractor.contractor_code}.pdf"'
            )
            return response

        except ImportError as e:
            logger.error(f"ReportLab/Pillow import error: {e}")
            messages.error(
                request,
                'PDF generation requires ReportLab and Pillow. '
                'Install: pip install reportlab pillow'
            )
            return redirect('contractor:reports_list')
        except Exception as e:
            logger.error(f"Error generating PDF: {e}", exc_info=True)
            messages.error(request, f'Error generating PDF: {str(e)}')
            return redirect('contractor:reports_list')

    def _generate_excel_report(self, request, report, contractor, data):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment

            wb = Workbook()

            ws1 = wb.active
            ws1.title = "Registration"
            ws1.merge_cells('A1:B1')
            ws1['A1'] = 'CONTRACTOR REGISTRATION DETAILS'
            ws1['A1'].font = Font(size=14, bold=True, color='FFFFFF')
            ws1['A1'].fill = PatternFill(start_color='4F4F4F', end_color='4F4F4F', fill_type='solid')
            ws1['A1'].alignment = Alignment(horizontal='center')

            row = 3
            for key, value in data['registration'].items():
                ws1.cell(row=row, column=1, value=key.replace('_', ' ').title()).font = Font(bold=True)
                ws1.cell(row=row, column=2, value=str(value) if value else 'N/A')
                row += 1
            ws1.column_dimensions['A'].width = 30
            ws1.column_dimensions['B'].width = 50

            if data['onboarding']:
                ws2 = wb.create_sheet("Onboarding")
                ws2.append(['Document Name', 'Required', 'Status', 'File Attached', 'Uploaded By', 'Verified By'])
                for cell in ws2[1]:
                    cell.font = Font(bold=True, color='FFFFFF')
                    cell.fill = PatternFill(start_color='4F4F4F', end_color='4F4F4F', fill_type='solid')
                for d in data['onboarding']['documents']:
                    ws2.append([
                        d['document_name'], 'Yes' if d['is_required'] else 'No',
                        d['status'], 'Yes' if d['has_file'] else 'No',
                        d['uploaded_by'], d['verified_by'],
                    ])

            ws3 = wb.create_sheet("Work Orders")
            ws3.append(['WO Number', 'Contract', 'Description', 'Plant', 'Start', 'End', 'Workers', 'Status'])
            for cell in ws3[1]:
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill(start_color='4F4F4F', end_color='4F4F4F', fill_type='solid')
            for wo in data['work_orders']:
                ws3.append([
                    wo['work_order_number'], wo['contract_number'], wo['work_description'],
                    wo['plant'], str(wo['start_date']), str(wo['end_date']),
                    wo['number_of_workers'], wo['status'],
                ])

            ws4 = wb.create_sheet("Training")
            ws4.append(['Sign-Off #', 'Topic', 'Date', 'Representative', 'Workers', 'Status'])
            for cell in ws4[1]:
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill(start_color='4F4F4F', end_color='4F4F4F', fill_type='solid')
            for ts in data['training_signoffs']:
                ws4.append([
                    ts['signoff_number'], ts['topic_title'], str(ts['training_date']),
                    ts['contractor_representative'], ts['number_of_workers'], ts['status'],
                ])

            ws5 = wb.create_sheet("Inspections")
            ws5.append(['Code', 'Plant', 'Status', 'Total Q', 'YES', 'NO', 'Score', 'Rating'])
            for cell in ws5[1]:
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill(start_color='4F4F4F', end_color='4F4F4F', fill_type='solid')
            for insp in data['inspections']:
                ws5.append([
                    insp['inspection_code'], insp['plant'], insp['status'],
                    insp['total_questions'], insp['yes_count'], insp['no_count'],
                    f"{insp['compliance_score']}%", insp['rating'],
                ])

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = (
                f'attachment; filename="contractor_report_{contractor.contractor_code}.xlsx"'
            )
            wb.save(response)
            return response
        except ImportError:
            messages.error(request, 'Excel export requires openpyxl. Install: pip install openpyxl')
            return redirect('contractor:reports_list')

    def _generate_csv_report(self, request, report, contractor, data):
        import csv

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="contractor_report_{contractor.contractor_code}.csv"'
        )

        writer = csv.writer(response)

        writer.writerow(['CONTRACTOR REGISTRATION DETAILS'])
        for key, value in data['registration'].items():
            writer.writerow([key.replace('_', ' ').title(), value])
        writer.writerow([])

        writer.writerow(['WORK ORDERS'])
        writer.writerow(['WO Number', 'Description', 'Plant', 'Start', 'End', 'Workers', 'Status'])
        for wo in data['work_orders']:
            writer.writerow([
                wo['work_order_number'], wo['work_description'], wo['plant'],
                wo['start_date'], wo['end_date'], wo['number_of_workers'], wo['status'],
            ])
        writer.writerow([])

        writer.writerow(['INSPECTIONS'])
        writer.writerow(['Code', 'Plant', 'Status', 'Total Q', 'YES', 'NO', 'Score', 'Rating'])
        for insp in data['inspections']:
            writer.writerow([
                insp['inspection_code'], insp['plant'], insp['status'],
                insp['total_questions'], insp['yes_count'], insp['no_count'],
                f"{insp['compliance_score']}%", insp['rating'],
            ])

        return response


# ==========================================================
# PDF GENERATION VIEWS
# ==========================================================

from django.contrib.auth.decorators import login_required as _login_required_deco


@_login_required_deco
def contractor_pdf_view(request, pk):
    """Generate Contractor Registration PDF."""
    contractor = get_object_or_404(Contractor, pk=pk)
    return generate_contractor_pdf(contractor)


@_login_required_deco
def work_order_pdf_view(request, pk):
    """Generate Work Order PDF."""
    work_order = get_object_or_404(WorkOrder, pk=pk)
    return generate_work_order_pdf(work_order)


@_login_required_deco
def training_signoff_pdf_view(request, pk):
    """Generate Training Sign-Off PDF."""
    signoff = get_object_or_404(TrainingSignOff, pk=pk)
    return generate_training_signoff_pdf(signoff)


@_login_required_deco
def inspection_pdf_view(request, pk):
    """Generate Contractor Inspection PDF."""
    inspection = get_object_or_404(ContractorInspection, pk=pk)
    return generate_inspection_pdf(inspection)


@_login_required_deco
def contractor_logbook_pdf_view(request, year):
    """Generate Contractor Log Book PDF for a given year."""
    return generate_contractor_logbook_pdf(int(year))


@_login_required_deco
def performance_pdf_view(request, pk):
    """Generate Contractor Performance PDF."""
    contractor = get_object_or_404(Contractor, pk=pk)
    return generate_performance_pdf(contractor)


@_login_required_deco
def onboarding_pdf_view(request, pk):
    """Generate Contractor Onboarding PDF."""
    onboarding = get_object_or_404(OnboardingRequest, pk=pk)
    return generate_onboarding_pdf(onboarding)