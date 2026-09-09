# apps/contractor/views.py

import secrets
import string
import json
import logging
from datetime import datetime, date, timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db import transaction
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.utils import timezone
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.contrib.auth import get_user_model

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
)
from .forms import (
    ContractorForm,
    WorkOrderForm,
    WorkOrderStatusForm,
    TrainingSignOffForm,
    ContractorInspectionForm,
    ContractorInspectionResponseForm,
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
        
        # Search
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(contractor_code__icontains=search_query) |
                Q(contractor_name__icontains=search_query) |
                Q(contact_person__icontains=search_query) |
                Q(mobile__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        # Filters
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
        
        # Get filter choices
        context['contractor_type_choices'] = Contractor.CONTRACTOR_TYPE_CHOICES
        context['work_category_choices'] = Contractor.WORK_CATEGORY_CHOICES
        context['status_choices'] = [('active', 'Active'), ('inactive', 'Inactive')]
        
        # Preserve filter values
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_type'] = self.request.GET.get('contractor_type', '')
        context['selected_work_category'] = self.request.GET.get('work_category', '')
        context['selected_status'] = self.request.GET.get('status', '')
        
        # Statistics
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
        
        # Check permissions
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

        # ---------------------------------------------------------
        # Basic validation
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # Get contractor contact details
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # Prevent duplicate active onboarding
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # Get pre-qualification questions and document types
        # ---------------------------------------------------------
        prequal_questions_list = PreQualificationQuestion.objects.filter(
            id__in=selected_questions,
            is_active=True
        ).order_by('sequence', 'id')

        document_types = DocumentType.objects.filter(
            id__in=selected_documents,
            is_active=True
        ).order_by('name')

        # ---------------------------------------------------------
        # Existing internal EHS officer lookup
        # ---------------------------------------------------------
        internal_ehs_officer = None
        if ehs_email:
            internal_ehs_officer = User.objects.filter(
                email__iexact=ehs_email
            ).first()

        # ---------------------------------------------------------
        # Create Onboarding Request - Set status to DRAFT
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # Create document requirements
        # ---------------------------------------------------------
        for doc_type in document_types:
            OnboardingDocumentRequirement.objects.create(
                onboarding=onboarding,
                document_type=doc_type,
                is_required=doc_type.is_mandatory,
                status='PENDING'
            )

        # ---------------------------------------------------------
        # Create Contact Person portal assignment
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # Create EHS Officer portal assignment
        # ---------------------------------------------------------
        if ehs_email:
            # Check if same as contact email
            existing_cred = None
            if ehs_email == contact_email:
                existing_cred = next(
                    (item for item in portal_credentials if item['portal_user'].email.lower() == ehs_email),
                    None
                )

            if existing_cred:
                # Same account - reuse the password
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

        # ---------------------------------------------------------
        # Prepare data for email
        # ---------------------------------------------------------
        prequal_for_email = [
            {
                'question': q.question,
                'question_type': q.get_question_type_display(),
                'answer': False
            }
            for q in prequal_questions_list
        ]

        doc_requirements = onboarding.document_requirements.select_related('document_type').all()

        # ---------------------------------------------------------
        # Get the site URL from settings
        # ---------------------------------------------------------
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        site_url = site_url.rstrip('/')
        
        # Get the login path
        login_path = reverse('contractor:portal_login')

        # ---------------------------------------------------------
        # Send Contractor Portal Login Emails
        # ---------------------------------------------------------
        emails_sent = 0
        emails_failed = 0

        for credential in portal_credentials:
            portal_user = credential['portal_user']
            assignment = credential['assignment']
            temporary_password = credential['password']

            # Build assignment-specific login URL
            login_url = f"{site_url}{login_path}?assignment={assignment.access_token}"

            # Determine recipients
            if portal_user.user_type == 'EHS_OFFICER':
                to_email = ehs_email
                cc_email = contact_email if contact_email and contact_email != ehs_email else None
            else:
                to_email = contact_email
                cc_email = None

            # Send email with all details
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

        # ---------------------------------------------------------
        # Success / Email Status
        # ---------------------------------------------------------
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
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Search by contractor name
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
        
        # ==========================================================
        # GET DOCUMENT REQUIREMENTS
        # ==========================================================
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
        
        # ==========================================================
        # GET PRE-QUALIFICATION QUESTIONS WITH ANSWERS (NO REMARKS)
        # ==========================================================
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
        
        # ==========================================================
        # CHECK PERMISSIONS
        # ==========================================================
        context['can_approve'] = (
            self.request.user == onboarding.ehs_officer or 
            self.request.user.is_superuser
        )
        context['can_delete'] = (
            self.request.user.has_perm('contractor.delete_onboardingrequest') or 
            self.request.user.is_superuser
        )
        
        # ==========================================================
        # ADD STATUS CHOICES FOR FILTERS
        # ==========================================================
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

        # ==========================================================
        # GET QUESTIONS WITH ANSWERS AND REMARKS
        # ==========================================================
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

        # ==========================================================
        # GET DOCUMENT REQUIREMENTS
        # ==========================================================
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

        # ==========================================================
        # SAVE QUESTION REMARKS
        # ==========================================================
        if not hasattr(onboarding, 'question_remarks') or onboarding.question_remarks is None:
            onboarding.question_remarks = {}

        for key, value in request.POST.items():
            if key.startswith('question_remark_'):
                question_id = key.replace('question_remark_', '')
                if question_id.isdigit():
                    onboarding.question_remarks[question_id] = value.strip()

        # ==========================================================
        # SAVE DOCUMENT REMARKS
        # ==========================================================
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

        # ==========================================================
        # PROCESS ACTION
        # ==========================================================
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
        """Send approval email to all portal users"""
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
        """Send rejection email to all portal users"""
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
        
        # Check permission
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
        
        # Check permission
        if request.user != onboarding.ehs_officer and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to reject this request.')
            return redirect('contractor:onboarding_detail', pk=onboarding.pk)
        
        rejection_reason = request.POST.get('rejection_reason', '')
        
        onboarding.status = 'REJECTED'
        onboarding.rejection_reason = rejection_reason
        onboarding.save()
        
        # ==========================================================
        # SEND REJECTION EMAIL
        # ==========================================================
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
    """
    Delete an onboarding request.
    Requires delete permission.
    """
    model = OnboardingRequest
    template_name = 'contractor/onboarding_confirm_delete.html'
    context_object_name = 'onboarding'
    permission_required = 'contractor.delete_onboardingrequest'
    
    def get_success_url(self):
        return reverse_lazy('contractor:onboarding_list')
    
    def delete(self, request, *args, **kwargs):
        """
        Override delete to add custom message.
        """
        self.object = self.get_object()
        contractor_name = self.object.contractor.contractor_name
        
        with transaction.atomic():
            # Delete related document requirements
            self.object.document_requirements.all().delete()
            # Delete related assignments
            self.object.assignments.all().delete()
            # Delete the onboarding request
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
        # Get related counts
        context['document_count'] = self.object.document_requirements.count()
        context['assignment_count'] = self.object.assignments.count()
        return context


class OnboardingBulkDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Bulk delete multiple onboarding requests.
    """
    permission_required = 'contractor.delete_onboardingrequest'
    
    def post(self, request, *args, **kwargs):
        onboarding_ids = request.POST.getlist('onboarding_ids')
        
        if not onboarding_ids:
            messages.error(request, 'No onboarding requests selected for deletion.')
            return redirect('contractor:onboarding_list')
        
        # Get the objects to delete
        onboarding_requests = OnboardingRequest.objects.filter(id__in=onboarding_ids)
        count = onboarding_requests.count()
        
        if count == 0:
            messages.error(request, 'No valid onboarding requests found.')
            return redirect('contractor:onboarding_list')
        
        # Store contractor names for the message
        contractor_names = list(onboarding_requests.values_list(
            'contractor__contractor_name', flat=True
        ))
        
        # Delete with transaction
        with transaction.atomic():
            # Delete all related records first
            for onboarding in onboarding_requests:
                onboarding.document_requirements.all().delete()
                onboarding.assignments.all().delete()
            # Then delete the onboarding requests
            onboarding_requests.delete()
        
        messages.success(
            request,
            f'Successfully deleted {count} onboarding request(s): {", ".join(contractor_names[:5])}'
            + (f' and {count - 5} more...' if count > 5 else '')
        )
        
        return redirect('contractor:onboarding_list')


class OnboardingSoftDeleteView(LoginRequiredMixin, View):
    """
    Soft delete (archive) an onboarding request instead of permanent deletion.
    Useful for keeping audit trail.
    """
    def post(self, request, *args, **kwargs):
        onboarding = get_object_or_404(OnboardingRequest, pk=kwargs.get('pk'))
        
        # Check permission
        if not request.user.has_perm('contractor.change_onboardingrequest') and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to archive this request.')
            return redirect('contractor:onboarding_detail', pk=onboarding.pk)
        
        # Soft delete - mark as archived
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
    """
    Upload a document for an onboarding requirement.
    This view is accessible to contractor portal users via session.
    """
    def post(self, request, *args, **kwargs):
        requirement_id = kwargs.get('pk')
        
        try:
            requirement = OnboardingDocumentRequirement.objects.get(pk=requirement_id)
        except OnboardingDocumentRequirement.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Document requirement not found'}, status=404)

        # Check if the user is logged in via contractor portal session
        portal_user_id = request.session.get('contractor_portal_user_id')
        assignment_id = request.session.get('contractor_assignment_id')

        if not portal_user_id or not assignment_id:
            return JsonResponse({'status': 'error', 'message': 'Not authenticated. Please login again.'}, status=401)

        # Verify the user has access to this document
        try:
            assignment = ContractorAssignment.objects.get(
                id=assignment_id,
                portal_user_id=portal_user_id
            )
        except ContractorAssignment.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)

        # Verify this document belongs to the user's onboarding
        if assignment.onboarding.id != requirement.onboarding.id:
            return JsonResponse({'status': 'error', 'message': 'Access denied to this document'}, status=403)

        document_file = request.FILES.get('document_file')
        if not document_file:
            return JsonResponse({'status': 'error', 'message': 'No file selected'}, status=400)

        # Validate file size (max 10MB)
        if document_file.size > 10 * 1024 * 1024:
            return JsonResponse({'status': 'error', 'message': 'File size exceeds 10MB limit'}, status=400)

        # Save the file
        try:
            requirement.document_file = document_file
            requirement.status = 'UPLOADED'
            requirement.uploaded_at = timezone.now()
            requirement.save()

            # Get the full URL for the file
            file_url = requirement.document_file.url if requirement.document_file else None

            return JsonResponse({
                'status': 'success',
                'message': 'Document uploaded successfully!',
                'file_url': file_url
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error saving file: {str(e)}'}, status=500)


class DocumentVerifyView(LoginRequiredMixin, View):
    """
    Verify an uploaded document.
    """
    def post(self, request, *args, **kwargs):
        requirement_id = kwargs.get('pk')
        requirement = get_object_or_404(OnboardingDocumentRequirement, pk=requirement_id)
        
        # Check permission
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
    """
    Separate login for external Contractor Portal users.
    """
    template_name = 'contractor/portal/login.html'

    def get(self, request, *args, **kwargs):
        assignment_token = request.GET.get('assignment')
        if assignment_token:
            request.session['contractor_login_token'] = assignment_token
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        assignment_token = request.POST.get('assignment') or request.session.get('contractor_login_token')

        if not email or not password:
            messages.error(request, "Please enter your email and password.")
            return render(request, self.template_name)

        portal_user = ContractorPortalUser.objects.filter(
            email__iexact=email,
            is_active=True
        ).first()

        if not portal_user:
            messages.error(request, "Invalid email or password.")
            return render(request, self.template_name)

        if not portal_user.check_password(password):
            messages.error(request, "Invalid email or password.")
            return render(request, self.template_name)

        assignment = None
        if assignment_token:
            assignment = ContractorAssignment.objects.filter(
                access_token=assignment_token,
                portal_user=portal_user
            ).select_related('onboarding', 'onboarding__contractor').first()

        if not assignment:
            assignment = ContractorAssignment.objects.filter(
                portal_user=portal_user,
                is_access_active=True,
                status='ACTIVE'
            ).select_related('onboarding', 'onboarding__contractor').order_by('-assigned_at').first()

        if not assignment:
            messages.error(request, "No active contractor onboarding assignment found.")
            return render(request, self.template_name)

        if not assignment.can_access:
            messages.error(request, "This contractor assignment is no longer active.")
            return render(request, self.template_name)

        request.session['contractor_portal_user_id'] = portal_user.id
        request.session['contractor_assignment_id'] = assignment.id
        request.session.pop('contractor_login_token', None)

        portal_user.last_login = timezone.now()
        portal_user.save(update_fields=['last_login', 'updated_at'])

        messages.success(request, f"Welcome, {portal_user.name}.")
        return redirect('contractor:portal_home')


class ContractorPortalLogoutView(View):
    """
    Logout external Contractor Portal user.
    """
    def get(self, request, *args, **kwargs):
        request.session.pop('contractor_portal_user_id', None)
        request.session.pop('contractor_assignment_id', None)
        request.session.pop('contractor_login_token', None)

        messages.success(request, "You have been logged out successfully.")
        return redirect('contractor:portal_login')


class ContractorPortalHomeView(View):
    """
    Main page for an authenticated Contractor Portal user.
    """
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

        # Get question IDs
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

        # ==========================================================
        # BUILD QUESTIONS WITH ANSWERS AND REMARKS
        # ==========================================================
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
        """Handle POST requests - Save answers and submit for approval"""
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

        # Initialize pre_qualification_answers if None
        if onboarding.pre_qualification_answers is None:
            onboarding.pre_qualification_answers = {}

        # ==========================================================
        # Save Answers
        # ==========================================================
        if 'save_answers' in request.POST:
            for key, value in request.POST.items():
                if key.startswith('question_'):
                    question_id = key.replace('question_', '')
                    if question_id.isdigit():
                        onboarding.pre_qualification_answers[question_id] = value.strip() if value else ''
            
            onboarding.save()
            messages.success(request, "Your answers have been saved successfully!")
            return redirect('contractor:portal_home')

        # ==========================================================
        # Submit for Approval
        # ==========================================================
        elif 'submit_for_approval' in request.POST:
            # Save any answers from the form
            for key, value in request.POST.items():
                if key.startswith('question_'):
                    question_id = key.replace('question_', '')
                    if question_id.isdigit():
                        onboarding.pre_qualification_answers[question_id] = value.strip() if value else ''

            # Check if all questions are answered
            unanswered = []
            for q_id, answer in onboarding.pre_qualification_answers.items():
                if not str(answer).strip():
                    unanswered.append(q_id)

            if unanswered:
                messages.warning(request, f"Please answer all questions before submitting.")
                return redirect('contractor:portal_home')

            # Check if all required documents are uploaded
            required_docs = onboarding.document_requirements.filter(is_required=True)
            missing_docs = []
            for doc in required_docs:
                if doc.status not in ['UPLOADED', 'VERIFIED']:
                    missing_docs.append(doc.document_type.name)

            if missing_docs:
                messages.warning(request, f"Please upload required documents: {', '.join(missing_docs)}")
                return redirect('contractor:portal_home')

            # Update status to PENDING
            onboarding.status = 'PENDING'
            onboarding.submitted_at = timezone.now()
            # Clear rejection reason when resubmitting
            onboarding.rejection_reason = ''
            onboarding.save()

            messages.success(request, "Onboarding submitted for approval successfully! 🎉")
            return redirect('contractor:portal_home')

        return redirect('contractor:portal_home')


# ==========================================================
# WORK ORDER VIEWS
# ==========================================================

class WorkOrderListView(LoginRequiredMixin, ListView):
    """
    Display list of all work orders with search and filter.
    """
    model = WorkOrder
    template_name = 'contractor/workorder_list.html'
    context_object_name = 'work_orders'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(work_order_number__icontains=search) |
                Q(contractor__contractor_name__icontains=search) |
                Q(work_description__icontains=search) |
                Q(contract_number__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by contractor
        contractor_id = self.request.GET.get('contractor', '')
        if contractor_id:
            queryset = queryset.filter(contractor_id=contractor_id)
        
        # Filter by work category
        work_category = self.request.GET.get('work_category', '')
        if work_category:
            queryset = queryset.filter(work_category=work_category)
        
        # Filter by risk level
        risk_level = self.request.GET.get('risk_level', '')
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)
        
        # Filter by plant
        plant_id = self.request.GET.get('plant', '')
        if plant_id:
            queryset = queryset.filter(plant_id=plant_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filter choices
        context['status_choices'] = WorkOrder.STATUS_CHOICES
        context['work_category_choices'] = Contractor.WORK_CATEGORY_CHOICES
        context['risk_level_choices'] = WorkOrder.RISK_LEVEL_CHOICES
        
        # Preserve filter values
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_contractor'] = self.request.GET.get('contractor', '')
        context['selected_work_category'] = self.request.GET.get('work_category', '')
        context['selected_risk_level'] = self.request.GET.get('risk_level', '')
        context['selected_plant'] = self.request.GET.get('plant', '')
        
        # Get contractors and plants for filter dropdowns
        context['contractors'] = Contractor.objects.filter(is_active=True).order_by('contractor_name')
        context['plants'] = Plant.objects.filter(is_active=True).order_by('name')
        
        # Statistics - Only SUBMITTED, APPROVED, REJECTED, CLOSED
        context['total_work_orders'] = WorkOrder.objects.count()
        context['approved_work_orders'] = WorkOrder.objects.filter(
            status='APPROVED'
        ).count()
        context['closed_work_orders'] = WorkOrder.objects.filter(
            status='CLOSED'
        ).count()
        context['pending_work_orders'] = WorkOrder.objects.filter(
            status='SUBMITTED'
        ).count()
        context['rejected_work_orders'] = WorkOrder.objects.filter(
            status='REJECTED'
        ).count()
        
        return context


class WorkOrderDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed view of a work order.
    """
    model = WorkOrder
    template_name = 'contractor/workorder_detail.html'
    context_object_name = 'work_order'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        work_order = self.get_object()
        
        # Check permissions
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
    """
    Create a new work order for an approved contractor.
    """
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = 'contractor/workorder_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Pre-populate from URL parameters
        contractor_id = self.request.GET.get('contractor')
        if contractor_id:
            try:
                contractor = Contractor.objects.get(id=contractor_id)
                initial['contractor'] = contractor
                initial['work_category'] = contractor.work_category
                initial['risk_level'] = 'MEDIUM'
                initial['number_of_workers'] = contractor.number_of_workers or 0
                
                # Auto-fill supervisor from contractor's EHS Officer
                if contractor.ehs_officer_name:
                    initial['contractor_supervisor'] = contractor.ehs_officer_name
                    initial['contractor_supervisor_contact'] = contractor.ehs_mobile or ''
                    initial['contractor_supervisor_email'] = contractor.ehs_email or ''
                
            except Contractor.DoesNotExist:
                pass
        
        # Pre-populate from onboarding
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
        
        # Get approved contractors for quick selection
        context['approved_contractors'] = Contractor.objects.filter(
            onboarding_requests__status='APPROVED',
            is_active=True
        ).distinct()
        
        # Get all active users for dropdowns
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
    """
    Update an existing work order.
    """
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = 'contractor/workorder_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Work Order'
        context['form_mode'] = 'edit'
        context['button_text'] = 'Update Work Order'
        
        # Get approved contractors for quick selection
        context['approved_contractors'] = Contractor.objects.filter(
            onboarding_requests__status='APPROVED',
            is_active=True
        ).distinct()
        
        # Get all active users for dropdowns
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
    """
    Delete a work order.
    """
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
    """
    Bulk delete multiple work orders.
    """
    permission_required = 'contractor.delete_workorder'
    
    def post(self, request, *args, **kwargs):
        work_order_ids = request.POST.getlist('work_order_ids')
        
        if not work_order_ids:
            messages.error(request, 'No work orders selected for deletion.')
            return redirect('contractor:workorder_list')
        
        # Get the objects to delete
        work_orders = WorkOrder.objects.filter(id__in=work_order_ids)
        count = work_orders.count()
        
        if count == 0:
            messages.error(request, 'No valid work orders found.')
            return redirect('contractor:workorder_list')
        
        # Store work order numbers for the message
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
    """
    Display list of work orders pending review (SUBMITTED status only).
    """
    model = WorkOrder
    template_name = 'contractor/workorder_review_list.html'
    context_object_name = 'work_orders'
    paginate_by = 15
    
    def get_queryset(self):
        # Only show SUBMITTED work orders (pending review)
        queryset = WorkOrder.objects.filter(
            status='SUBMITTED'
        ).order_by('-created_at')
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(work_order_number__icontains=search) |
                Q(contractor__contractor_name__icontains=search) |
                Q(work_description__icontains=search)
            )
        
        # Filter by contractor
        contractor_id = self.request.GET.get('contractor', '')
        if contractor_id:
            queryset = queryset.filter(contractor_id=contractor_id)
        
        # Filter by risk level
        risk_level = self.request.GET.get('risk_level', '')
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filter choices
        context['risk_level_choices'] = WorkOrder.RISK_LEVEL_CHOICES
        
        # Preserve filter values
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_contractor'] = self.request.GET.get('contractor', '')
        context['selected_risk_level'] = self.request.GET.get('risk_level', '')
        
        # Get contractors for filter dropdown
        context['contractors'] = Contractor.objects.filter(is_active=True).order_by('contractor_name')
        
        # Statistics
        context['total_pending'] = WorkOrder.objects.filter(status='SUBMITTED').count()
        
        return context


class WorkOrderReviewView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    """
    View for reviewing and approving/rejecting a work order.
    """
    model = WorkOrder
    template_name = 'contractor/workorder_review.html'
    context_object_name = 'work_order'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        work_order = self.get_object()
        
        # Since AdminRequiredMixin already restricts page access to admins,
        # can_review simply reflects that the user reached this page.
        context['can_review'] = (
            self.request.user.is_superuser or self.request.user.is_admin_user
        )
        
        return context
    
    def post(self, request, *args, **kwargs):
        work_order = self.get_object()
        action = request.POST.get('action')
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        
        # Check permission - Admin only
        if not (request.user.is_superuser or request.user.is_admin_user):
            messages.error(request, 'You do not have permission to review work orders.')
            return redirect('contractor:workorder_detail', pk=work_order.pk)
        # ==========================================================
        # APPROVE
        # ==========================================================
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
        
        # ==========================================================
        # REJECT
        # ==========================================================
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
    """
    Create a Training Sign-Off record.
    """
    model = TrainingSignOff
    form_class = TrainingSignOffForm
    template_name = 'contractor/training_signoff_form.html'

    def get_form_kwargs(self):
        """Pass request to form"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Training Sign-Off'
        
        # Get the logged-in user's plant name
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
            
            # Ensure company_representative is set from work_order
            if not signoff.company_representative and signoff.work_order:
                signoff.company_representative = signoff.work_order.company_representative
            
            signoff.status = 'SUBMITTED'
            signoff.save()
            
            # Send email with PDF attachment
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
        # Log form errors for debugging
        logger.error(f"Form errors: {form.errors}")
        
        # Display specific error messages
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        
        return super().form_invalid(form)


class TrainingSignOffListView(LoginRequiredMixin, ListView):
    """
    Display list of all training sign-offs.
    """
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
    """
    Display detailed view of a training sign-off.
    """
    model = TrainingSignOff
    template_name = 'contractor/training_signoff_detail.html'
    context_object_name = 'signoff'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        signoff = self.get_object()
        
        # Get the logged-in user's plant name
        user = self.request.user
        plant_name = 'the Plant'  # Default fallback
        
        # Try different ways to get plant name from user
        if hasattr(user, 'plant') and user.plant:
            plant_name = user.plant.name
        elif hasattr(user, 'plant_name') and user.plant_name:
            plant_name = user.plant_name
        elif hasattr(user, 'profile') and hasattr(user.profile, 'plant'):
            plant_name = user.profile.plant.name
        elif hasattr(signoff, 'work_order') and signoff.work_order and signoff.work_order.plant:
            # Get plant from work order if available
            plant_name = signoff.work_order.plant.name
        
        context['plant_name'] = plant_name
        context['current_user_name'] = user.get_full_name() or user.username
        
        return context


class UploadSignOffSignatureView(LoginRequiredMixin, View):
    """
    Upload signature for a training sign-off via AJAX.
    """
    def post(self, request, pk):
        try:
            signoff = get_object_or_404(TrainingSignOff, pk=pk)
            
            # Check if user has permission
            if signoff.created_by != request.user and not request.user.is_superuser:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'You do not have permission to upload this signature.'
                }, status=403)
            
            # Check if file is in request
            if 'signature_file' not in request.FILES:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'No file uploaded.'
                }, status=400)
            
            file = request.FILES['signature_file']
            
            # Validate file type
            valid_types = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']
            if file.content_type not in valid_types:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Invalid file type. Please upload JPG, PNG, or PDF.'
                }, status=400)
            
            # Validate file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'File size exceeds 5MB limit.'
                }, status=400)
            
            # Save the file
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
    """
    Upload supporting document for a training sign-off via AJAX.
    """
    def post(self, request, pk):
        try:
            signoff = get_object_or_404(TrainingSignOff, pk=pk)
            
            # Check if user has permission
            if signoff.created_by != request.user and not request.user.is_superuser:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'You do not have permission to upload this document.'
                }, status=403)
            
            # Check if file is in request
            if 'supporting_document' not in request.FILES:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'No file uploaded.'
                }, status=400)
            
            file = request.FILES['supporting_document']
            
            # Validate file type
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
            
            # Validate file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'File size exceeds 5MB limit.'
                }, status=400)
            
            # Save the file
            signoff.supporting_documents = file
            
            # ==========================================================
            # CHANGE STATUS TO COMPLETED WHEN DOCUMENT IS SUBMITTED
            # ==========================================================
            action = request.POST.get('action', '')
            if action == 'submit':
                signoff.status = 'COMPLETED'
            else:
                signoff.status = 'SUBMITTED'
            
            signoff.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Document uploaded successfully!' if action != 'submit' else 'Sign-Off submitted successfully!'
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
# apps/contractor/views.py - Add these views (add to existing file)

# ==========================================================
# CONTRACTOR INSPECTION VIEWS
# ==========================================================

class ContractorInspectionListView(LoginRequiredMixin, ListView):
    """Display list of all contractor inspections with filters and pagination"""
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


# apps/contractor/views.py - Update ContractorInspectionCreateView

class ContractorInspectionCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new contractor inspection with question selection
    """
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
        """
        Handle POST requests with proper error handling
        """
        form = self.get_form()
        
        # Validate the form
        if form.is_valid():
            return self.form_valid(form)
        else:
            # Log the errors for debugging
            logger.error(f"Form errors: {form.errors}")
            
            # Re-render the form with errors
            return self.form_invalid(form)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                inspection = form.save(commit=False)
                inspection.assigned_by = self.request.user
                
                # Get selected questions from POST
                selected_question_ids = self.request.POST.getlist('selected_questions')
                
                # Validate that questions are selected
                if not selected_question_ids:
                    messages.error(self.request, 'Please select at least one question for the inspection.')
                    return self.form_invalid(form)
                
                # Handle zone, location, sublocation - they are optional
                plant = form.cleaned_data.get('plant')
                zone = form.cleaned_data.get('zone')
                location = form.cleaned_data.get('location')
                sublocation = form.cleaned_data.get('sublocation')
                
                # If plant is selected but zone is not, clear zone
                if plant and not zone:
                    inspection.zone = None
                if zone and not location:
                    inspection.location = None
                if location and not sublocation:
                    inspection.sublocation = None
                
                # If auto-schedule is enabled, calculate end date from start date + offset
                if inspection.enable_auto_schedule:
                    if not inspection.due_date_offset_days:
                        inspection.due_date_offset_days = 7
                    # End date = start date + offset - 1
                    start_date = inspection.inspection_start_date
                    inspection.inspection_end_date = start_date + timedelta(days=inspection.due_date_offset_days - 1)
                
                # Save the inspection
                inspection.save()
                
                # Save selected questions (Many-to-Many)
                if selected_question_ids:
                    inspection.selected_questions.set(selected_question_ids)
                
                # If auto-schedule is enabled, create first recurring copy
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

                # Send notification
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
        # Log form errors for debugging
        logger.error(f"Form errors: {form.errors}")
        
        # Display specific error messages
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        
        # Re-render the form with errors
        context = self.get_context_data(form=form)
        
        # Re-populate the questions_by_section in context
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
    """Display detailed view of a contractor inspection"""
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


# apps/contractor/views.py

class ContractorInspectionConductView(LoginRequiredMixin, View):
    """Conduct the inspection - show only selected questions"""
    template_name = 'contractor/inspection_conduct.html'

    def get(self, request, pk):
        inspection = get_object_or_404(ContractorInspection, pk=pk)
        
        # Check permission
        if request.user != inspection.assigned_to and not request.user.is_superuser:
            messages.error(request, 'You are not authorized to conduct this inspection.')
            return redirect('contractor:inspection_list')

        # Check if already closed
        if inspection.status == 'CLOSED':
            messages.warning(request, 'This inspection is already closed.')
            return redirect('contractor:inspection_detail', pk=inspection.pk)

        # Update status to IN_PROGRESS
        if inspection.status == 'SCHEDULED':
            inspection.status = 'IN_PROGRESS'
            inspection.started_at = timezone.now()
            inspection.save(update_fields=['status', 'started_at'])

        # Get ONLY selected questions grouped by section
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
        
        # Check permission
        if request.user != inspection.assigned_to and not request.user.is_superuser:
            messages.error(request, 'You are not authorized to submit this inspection.')
            return redirect('contractor:inspection_list')

        # Get selected questions only
        selected_questions = inspection.selected_questions.filter(is_active=True)

        if not selected_questions.exists():
            messages.error(request, 'No questions found for this inspection.')
            return redirect('contractor:inspection_detail', pk=inspection.pk)

        # Process responses
        with transaction.atomic():
            for question in selected_questions:
                answer = request.POST.get(f'answer_{question.id}')
                remarks = request.POST.get(f'remarks_{question.id}', '').strip()

                if answer:
                    # Update or create response
                    response, created = ContractorInspectionResponse.objects.get_or_create(
                        inspection=inspection,
                        question=question
                    )
                    response.answer = answer
                    response.remarks = remarks

                    # Handle photo upload
                    if f'photo_{question.id}' in request.FILES:
                        response.photo = request.FILES[f'photo_{question.id}']

                    response.save()

            # Check if all questions answered
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

            # Close inspection
            inspection.status = 'CLOSED'
            inspection.closed_at = timezone.now()
            inspection.save(update_fields=['status', 'closed_at'])

            # Send notification
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
    """
    Cancel an inspection (POST only)
    """
    def post(self, request, pk):
        inspection = get_object_or_404(ContractorInspection, pk=pk)

        # Check permission
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
    """
    Delete an inspection (Admin only)
    """
    model = ContractorInspection
    template_name = 'contractor/inspection_confirm_delete.html'
    context_object_name = 'inspection'
    success_url = reverse_lazy('contractor:inspection_list')

    def get_queryset(self):
        # Only superusers and admins can delete
        if self.request.user.is_superuser or getattr(self.request.user, 'is_admin_user', False):
            return super().get_queryset()
        return ContractorInspection.objects.none()

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        inspection_code = self.object.inspection_code
        
        with transaction.atomic():
            # Delete responses
            self.object.responses.all().delete()
            # Clear selected questions
            self.object.selected_questions.clear()
            # Delete the inspection
            response = super().delete(request, *args, **kwargs)
        
        messages.success(request, f'Inspection "{inspection_code}" deleted successfully.')
        return response


class ContractorInspectionUpdateView(LoginRequiredMixin, UpdateView):
    """
    Edit an existing contractor inspection
    """
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

        # Get all active questions grouped by section
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
        
        # Get selected question IDs
        context['selected_question_ids'] = list(
            self.object.selected_questions.values_list('id', flat=True)
        )
        context['total_questions'] = questions.count()

        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                inspection = form.save()

                # Update selected questions
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
    """
    View for assigned users to see their inspections
    """
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

        # Status filter
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)

        # Search
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

        # Statistics
        context['total'] = queryset.count()
        context['pending'] = queryset.filter(status='SCHEDULED').count()
        context['in_progress'] = queryset.filter(status='IN_PROGRESS').count()
        context['completed'] = queryset.filter(status='CLOSED').count()
        context['overdue'] = queryset.filter(status='OVERDUE').count()

        return context


# ==========================================================
# API VIEWS (AJAX)
# ==========================================================
# apps/contractor/views.py - Fixed GetContractorDetailsAPIView

class GetContractorDetailsAPIView(LoginRequiredMixin, View):
    """
    API: Get contractor details including work orders, plant, zone, location, sublocation, department
    """
    def get(self, request, contractor_id):
        try:
            contractor = get_object_or_404(Contractor, pk=contractor_id)
            
            # Get the latest approved work order with all location details
            # Note: WorkOrder has plant as ForeignKey, but zone, location, sublocation are CharFields
            latest_work_order = WorkOrder.objects.filter(
                contractor=contractor,
                status='APPROVED'
            ).select_related(
                'plant', 
                'department',
                'company_representative'
            ).order_by('-created_at').first()
            
            # Get department from contractor's work orders or onboarding
            department = None
            if latest_work_order and latest_work_order.department:
                department = {
                    'id': latest_work_order.department.id,
                    'name': latest_work_order.department.name,
                }
            else:
                # Try to get department from onboarding
                onboarding = OnboardingRequest.objects.filter(
                    contractor=contractor,
                    status='APPROVED'
                ).select_related('ehs_officer').first()
                
                if onboarding and hasattr(onboarding, 'department') and onboarding.department:
                    department = {
                        'id': onboarding.department.id,
                        'name': onboarding.department.name,
                    }
            
            # Get plant details from work order
            plant = None
            if latest_work_order and latest_work_order.plant:
                plant = {
                    'id': latest_work_order.plant.id,
                    'name': latest_work_order.plant.name,
                }
            
            # Get zone, location, sublocation from work order (these are CharFields, not ForeignKeys)
            # So we need to get them from the plant's zones/locations or from the work order's stored values
            zone = None
            location = None
            sublocation = None
            
            if latest_work_order:
                # If work order has zone/location stored as foreign keys, check that
                # Otherwise, we need to look up from the plant
                if hasattr(latest_work_order, 'zone') and latest_work_order.zone:
                    # If zone is a ForeignKey
                    if hasattr(latest_work_order.zone, 'id'):
                        zone = {
                            'id': latest_work_order.zone.id,
                            'name': latest_work_order.zone.name,
                        }
                elif latest_work_order.plant:
                    # Get first zone from the plant
                    first_zone = Zone.objects.filter(plant=latest_work_order.plant, is_active=True).first()
                    if first_zone:
                        zone = {
                            'id': first_zone.id,
                            'name': first_zone.name,
                        }
                
                # Location
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
                
                # Sub-location
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
                    
                    # EHS Officer details (Contractor Supervisor)
                    'supervisor_name': contractor.ehs_officer_name or '',
                    'supervisor_designation': contractor.ehs_designation or '',
                    'supervisor_mobile': contractor.ehs_mobile or '',
                    'supervisor_email': contractor.ehs_email or '',
                    
                    # Contact Person
                    'contact_person': contractor.contact_person or '',
                    'contact_mobile': contractor.mobile or '',
                    'contact_email': contractor.email or '',
                    
                    # Address
                    'address': f"{contractor.address_line1}, {contractor.city}, {contractor.state}" if contractor.address_line1 else '',
                    
                    # Location details from latest work order
                    'plant': plant,
                    'zone': zone,
                    'location': location,
                    'sublocation': sublocation,
                    'department': department,
                    
                    # Work order info (for reference)
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
    """
    API view to get work orders for a specific contractor.
    """
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
    """
    API view to get approved contractors for work order creation.
    """
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
    """
    GET /api/contractor/<contractor_id>/approved-workorders/
    Returns the Approved work orders for a contractor.
    """
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
    """
    GET /api/workorder/<pk>/signoff-details/
    Returns the auto-fill values for the Training Sign-Off form.
    """
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
    """
    GET /api/training-session/<pk>/details/
    Returns Toolbox Talk session details for the read-only detail panel.
    """
    def get(self, request, pk):
        try:
            session = get_object_or_404(ToolboxTalkSessionPlan, pk=pk)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=404)

        # Get category name safely
        category_name = ''
        if hasattr(session, 'category') and session.category:
            if hasattr(session.category, 'category_name'):
                category_name = session.category.category_name
            elif hasattr(session.category, 'name'):
                category_name = session.category.name
            else:
                category_name = str(session.category)

        # Get department name safely
        department_name = ''
        if hasattr(session, 'department') and session.department:
            if hasattr(session.department, 'name'):
                department_name = session.department.name
            else:
                department_name = str(session.department)

        # Get trainers - with detailed info
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

        # Get incharges - with detailed info
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

        # Get topic details
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

        # Build response
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
    """
    API: Get zones for a plant
    """
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
    """
    API: Get locations for a zone
    """
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
    """
    API: Get sublocations for a location
    """
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
    """
    API: Get Safety Managers and Plant Heads for a plant
    """
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
    """
    API: Get approved work orders for a contractor
    """
    def get(self, request, contractor_id):
        try:
            work_orders = WorkOrder.objects.filter(
                contractor_id=contractor_id,
                status='APPROVED'
            ).values('id', 'work_order_number', 'contract_number', 'work_description')
            return JsonResponse({'success': True, 'work_orders': list(work_orders)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
# apps/contractor/views.py - Add these views at the end of the file

# ==========================================================
# PERFORMANCE VIEWS
# ==========================================================

from django.views.generic import TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import datetime
from .models import Contractor, ContractorPerformanceMetric
from .services.performance_service import BulkPerformanceCalculator


# apps/contractor/views.py

class ContractorPerformanceDashboardView(LoginRequiredMixin, TemplateView):
    """
    Contractor Performance Dashboard.
    """
    template_name = 'contractor/performance_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current period
        today = timezone.now().date()
        month = int(self.request.GET.get('month', today.month))
        year = int(self.request.GET.get('year', today.year))
        
        # Get performance metrics
        from .services.performance_service import BulkPerformanceCalculator
        
        # Get ranking - this now includes 'id' field
        ranking = BulkPerformanceCalculator.get_contractor_ranking(month, year)
        context['ranking'] = ranking
        
        # Calculate summary statistics
        if ranking:
            scores = [r['score'] for r in ranking]
            context['avg_score'] = round(sum(scores) / len(scores), 1) if scores else 0
            context['max_score'] = max(scores) if scores else 0
            context['min_score'] = min(scores) if scores else 0
            context['total_contractors'] = len(ranking)
            context['excellent_count'] = len([r for r in ranking if r['rating'] == 'Excellent'])
            context['good_count'] = len([r for r in ranking if r['rating'] == 'Good'])
            context['needs_improvement_count'] = len([r for r in ranking if r['rating'] == 'Needs Improvement'])
            context['poor_count'] = len([r for r in ranking if r['rating'] == 'Poor'])
        else:
            context['total_contractors'] = 0
            context['excellent_count'] = 0
            context['good_count'] = 0
            context['needs_improvement_count'] = 0
            context['poor_count'] = 0
        
        context['current_month'] = month
        context['current_year'] = year
        
        # Month options for filter
        context['month_options'] = [
            {'value': i, 'label': datetime(2000, i, 1).strftime('%B')}
            for i in range(1, 13)
        ]
        
        # Year options for filter - generate dynamically
        current_year = timezone.now().year
        context['year_options'] = list(range(current_year - 5, current_year + 2))
        
        return context

# apps/contractor/views.py - ContractorPerformanceDetailView

class ContractorPerformanceDetailView(LoginRequiredMixin, DetailView):
    """
    Detailed performance view for a single contractor.
    """
    model = Contractor
    template_name = 'contractor/performance_detail.html'
    context_object_name = 'contractor'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contractor = self.get_object()
        
        # Get all performance metrics for this contractor
        metrics = ContractorPerformanceMetric.objects.filter(
            contractor=contractor
        ).order_by('-period_year', '-period_month')
        
        context['metrics'] = metrics
        
        # Get latest metric
        latest = metrics.first()
        if latest:
            context['latest_score'] = latest.overall_performance_score
            context['latest_rating'] = latest.rating
            context['latest_risk'] = latest.risk_level
            context['latest_inspection_score'] = latest.inspection_compliance_score
            context['latest_training_score'] = latest.training_compliance_score
            context['latest_onboarding_score'] = latest.document_compliance_score  # Renamed variable
            context['latest_work_order_score'] = latest.work_order_completion_score
            context['inspections_count'] = latest.inspections_count
        else:
            context['latest_score'] = 0
            context['latest_rating'] = 'N/A'
            context['latest_risk'] = 'N/A'
            context['latest_inspection_score'] = 0
            context['latest_training_score'] = 0
            context['latest_onboarding_score'] = 0
            context['latest_work_order_score'] = 0
            context['inspections_count'] = 0
        
        return context