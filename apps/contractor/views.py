import secrets
import string
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.utils import timezone
from datetime import datetime, date
from django.http import JsonResponse
from apps.contractor.models import (
    Contractor,
    OnboardingRequest,
    OnboardingDocumentRequirement,
    DocumentType,
    PreQualificationQuestion,
    ContractorPortalUser,
    ContractorAssignment,
)
from apps.contractor.forms import ContractorForm
from django.contrib.auth import get_user_model
from apps.notifications.services import NotificationService

User = get_user_model()


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
# Genrate Contractor Password
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

        contractor = get_object_or_404(
            Contractor,
            pk=contractor_id
        )

        if not selected_questions:
            messages.error(
                request,
                "Please select at least one pre-qualification question."
            )
            return redirect('contractor:contractor_onboarding')

        if not selected_documents:
            messages.error(
                request,
                "Please select at least one document requirement."
            )
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
        # Existing internal EHS officer lookup
        # ---------------------------------------------------------
        internal_ehs_officer = None

        if ehs_email:
            internal_ehs_officer = User.objects.filter(
                email__iexact=ehs_email
            ).first()

        # ---------------------------------------------------------
        # Create Onboarding Request
        # ---------------------------------------------------------
        onboarding = OnboardingRequest.objects.create(
            contractor=contractor,
            ehs_officer=internal_ehs_officer,
            pre_qualification_answers={
                str(question_id): False
                for question_id in selected_questions
            },
            notes=notes,
            status='PENDING',
            submitted_by=request.user,
            submitted_at=timezone.now()
        )

        # ---------------------------------------------------------
        # Create document requirements
        # ---------------------------------------------------------
        for document_id in selected_documents:
            document_type = get_object_or_404(
                DocumentType,
                pk=document_id
            )

            OnboardingDocumentRequirement.objects.create(
                onboarding=onboarding,
                document_type=document_type,
                is_required=True,
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
                    password='',
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
            })

        # ---------------------------------------------------------
        # Create EHS Officer portal assignment
        # ---------------------------------------------------------
        if ehs_email:

            # ---------------------------------------------------------
            # Same email as Contact Person
            # ---------------------------------------------------------
            if ehs_email == contact_email:

                portal_user = ContractorPortalUser.objects.filter(
                    contractor=contractor,
                    email__iexact=ehs_email
                ).first()

                if portal_user:

                    # Same account, so do not generate another password.
                    existing_credentials = next(
                        (
                            item
                            for item in portal_credentials
                            if item['portal_user'].id == portal_user.id
                        ),
                        None
                    )

                    if existing_credentials:
                        temporary_password = existing_credentials['password']
                    else:
                        temporary_password = generate_contractor_password()
                        portal_user.set_password(temporary_password)
                        portal_user.save(
                            update_fields=['password', 'updated_at']
                        )

                else:
                    temporary_password = generate_contractor_password()

                    portal_user = ContractorPortalUser.objects.create(
                        contractor=contractor,
                        name=ehs_name,
                        email=ehs_email,
                        user_type='EHS_OFFICER',
                        password='',
                        is_active=True
                    )

                    portal_user.set_password(temporary_password)
                    portal_user.save(update_fields=['password'])

                if not onboarding.assignments.filter(
                    portal_user=portal_user
                ).exists():

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
                    })

            # ---------------------------------------------------------
            # Different email from Contact Person
            # ---------------------------------------------------------
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
                        password='',
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
                })

        # ---------------------------------------------------------
        # Send Contractor Portal Login Emails
        # ---------------------------------------------------------

        emails_sent = 0
        emails_failed = 0

        contact_email = (
            contractor.email or ''
        ).strip().lower()

        ehs_email = (
            contractor.ehs_email or ''
        ).strip().lower()


        for credential in portal_credentials:

            portal_user = credential['portal_user']
            assignment = credential['assignment']
            temporary_password = credential['password']

            # ---------------------------------------------------------
            # Build assignment-specific login URL
            # ---------------------------------------------------------

            login_path = reverse(
                'contractor_portal:login'
            )

            login_url = request.build_absolute_uri(
                f"{login_path}?assignment={assignment.access_token}"
            )

            # ---------------------------------------------------------
            # Determine recipients
            # ---------------------------------------------------------

            if portal_user.user_type == 'EHS_OFFICER':

                # EHS Officer is primary recipient
                to_email = ehs_email

                # Contact Person is CC
                cc_email = contact_email

            else:

                # Contact Person receives their own credentials
                to_email = contact_email

                # No CC required
                cc_email = None

            # ---------------------------------------------------------
            # Send email
            # ---------------------------------------------------------

            email_sent = NotificationService.send_contractor_onboarding_email(
                portal_user=portal_user,
                assignment=assignment,
                temporary_password=temporary_password,
                login_url=login_url,
                cc_email=cc_email
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




class ContractorPortalLoginView(View):
    """
    Separate login for external Contractor Portal users.

    This does NOT use the internal accounts.User authentication.
    """

    template_name = 'contractor/portal/login.html'

    def get(self, request, *args, **kwargs):
        """
        Display contractor portal login page.
        """

        assignment_token = request.GET.get('assignment')

        if assignment_token:
            request.session['contractor_login_token'] = assignment_token

        return render(
            request,
            self.template_name
        )

    def post(self, request, *args, **kwargs):
        """
        Authenticate ContractorPortalUser and verify assignment access.
        """

        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()

        assignment_token = (
            request.POST.get('assignment')
            or request.session.get('contractor_login_token')
        )

        # ---------------------------------------------------------
        # Basic validation
        # ---------------------------------------------------------
        if not email or not password:
            messages.error(
                request,
                "Please enter your email and password."
            )

            return render(
                request,
                self.template_name
            )

        # ---------------------------------------------------------
        # Find external contractor portal user
        # ---------------------------------------------------------
        portal_user = ContractorPortalUser.objects.filter(
            email__iexact=email,
            is_active=True
        ).first()

        if not portal_user:
            messages.error(
                request,
                "Invalid email or password."
            )

            return render(
                request,
                self.template_name
            )

        # ---------------------------------------------------------
        # Check password
        # ---------------------------------------------------------
        if not portal_user.check_password(password):
            messages.error(
                request,
                "Invalid email or password."
            )

            return render(
                request,
                self.template_name
            )

        # ---------------------------------------------------------
        # Find assignment
        # ---------------------------------------------------------
        assignment = None

        if assignment_token:

            assignment = ContractorAssignment.objects.filter(
                access_token=assignment_token,
                portal_user=portal_user
            ).select_related(
                'onboarding',
                'onboarding__contractor'
            ).first()

        else:

            assignment = ContractorAssignment.objects.filter(
                portal_user=portal_user
            ).select_related(
                'onboarding',
                'onboarding__contractor'
            ).order_by('-assigned_at').first()

        # ---------------------------------------------------------
        # Assignment validation
        # ---------------------------------------------------------
        if not assignment:
            messages.error(
                request,
                "No contractor onboarding assignment was found."
            )

            return render(
                request,
                self.template_name
            )

        if not assignment.can_access:
            messages.error(
                request,
                "This contractor assignment is no longer active."
            )

            return render(
                request,
                self.template_name
            )

        # ---------------------------------------------------------
        # Create separate contractor portal session
        # ---------------------------------------------------------
        request.session['contractor_portal_user_id'] = portal_user.id
        request.session['contractor_assignment_id'] = assignment.id

        # Remove temporary login token
        request.session.pop(
            'contractor_login_token',
            None
        )

        # Update last login
        portal_user.last_login = timezone.now()
        portal_user.save(
            update_fields=[
                'last_login',
                'updated_at'
            ]
        )

        messages.success(
            request,
            f"Welcome, {portal_user.name}."
        )

        return redirect(
            'contractor_portal:home'
        )




class ContractorPortalLogoutView(View):
    """
    Logout external Contractor Portal user.
    """

    def get(self, request, *args, **kwargs):

        request.session.pop(
            'contractor_portal_user_id',
            None
        )

        request.session.pop(
            'contractor_assignment_id',
            None
        )

        request.session.pop(
            'contractor_login_token',
            None
        )

        messages.success(
            request,
            "You have been logged out successfully."
        )

        return redirect(
            'contractor_portal:login'
        )



class ContractorPortalHomeView(View):
    """
    Main page for an authenticated Contractor Portal user.

    The user can see ONLY their assigned onboarding.
    """

    template_name = 'contractor/portal/home.html'

    def get(self, request, *args, **kwargs):

        portal_user_id = request.session.get(
            'contractor_portal_user_id'
        )

        assignment_id = request.session.get(
            'contractor_assignment_id'
        )

        # ---------------------------------------------------------
        # Check contractor portal session
        # ---------------------------------------------------------
        if not portal_user_id or not assignment_id:
            return redirect(
                'contractor_portal:login'
            )

        # ---------------------------------------------------------
        # Get assignment
        # ---------------------------------------------------------
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

            messages.error(
                request,
                "Your contractor assignment could not be found."
            )

            return redirect(
                'contractor_portal:login'
            )

        # ---------------------------------------------------------
        # Check assignment access
        # ---------------------------------------------------------
        if not assignment.can_access:
            request.session.pop(
                'contractor_assignment_id',
                None
            )

            messages.error(
                request,
                "Your contractor assignment is no longer active."
            )

            return redirect(
                'contractor_portal:login'
            )

        onboarding = assignment.onboarding

        # ---------------------------------------------------------
        # Get selected pre-qualification questions
        # ---------------------------------------------------------
        question_ids = []

        if onboarding.pre_qualification_answers:
            question_ids = [
                int(question_id)
                for question_id in onboarding.pre_qualification_answers.keys()
            ]

        questions = PreQualificationQuestion.objects.filter(
            id__in=question_ids,
            is_active=True
        ).order_by(
            'sequence',
            'id'
        )

        # ---------------------------------------------------------
        # Get required documents
        # ---------------------------------------------------------
        document_requirements = onboarding.document_requirements.select_related(
            'document_type'
        ).all()

        context = {
            'portal_user': assignment.portal_user,
            'assignment': assignment,
            'onboarding': onboarding,
            'contractor': onboarding.contractor,
            'questions': questions,
            'document_requirements': document_requirements,
        }

        return render(
            request,
            self.template_name,
            context
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
        
        # Get document requirements
        context['document_requirements'] = onboarding.document_requirements.all()
        
        # Get pre-qualification questions with answers
        prequal_questions = []
        for q_id, answer in onboarding.pre_qualification_answers.items():
            try:
                question = PreQualificationQuestion.objects.get(id=int(q_id))
                prequal_questions.append({
                    'question': question,
                    'answer': answer
                })
            except (PreQualificationQuestion.DoesNotExist, ValueError):
                pass
        context['prequal_questions'] = prequal_questions
        
        # Check permissions
        context['can_approve'] = (
            self.request.user == onboarding.ehs_officer or 
            self.request.user.is_superuser
        )
        
        return context


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
        
        messages.warning(request, f'Onboarding request for "{onboarding.contractor.contractor_name}" has been rejected.')
        return redirect('contractor:onboarding_detail', pk=onboarding.pk)


class DocumentUploadView(LoginRequiredMixin, View):
    """
    Upload a document for an onboarding requirement.
    """
    def post(self, request, *args, **kwargs):
        requirement_id = kwargs.get('pk')
        requirement = get_object_or_404(OnboardingDocumentRequirement, pk=requirement_id)
        
        # Check permission - only the responsible person or contractor can upload
        if request.user != requirement.onboarding.ehs_officer and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to upload documents for this request.')
            return redirect('contractor:onboarding_detail', pk=requirement.onboarding.pk)
        
        document_file = request.FILES.get('document_file')
        if not document_file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('contractor:onboarding_detail', pk=requirement.onboarding.pk)
        
        requirement.document_file = document_file
        requirement.status = 'UPLOADED'
        requirement.uploaded_by = request.user
        requirement.uploaded_at = timezone.now()
        requirement.save()
        
        messages.success(request, f'Document "{requirement.document_type.name}" uploaded successfully.')
        return redirect('contractor:onboarding_detail', pk=requirement.onboarding.pk)


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
# API VIEWS
# ==========================================================

class GetContractorDetailsView(LoginRequiredMixin, View):
    """
    API view to get contractor details for preview.
    """
    def get(self, request, pk):
        try:
            contractor = get_object_or_404(Contractor, pk=pk)
            data = {
                'contractor_code': contractor.contractor_code,
                'contractor_name': contractor.contractor_name,
                'contractor_type': contractor.get_contractor_type_display(),
                'contact_person': contractor.contact_person,
                'designation': contractor.designation,
                'mobile': contractor.mobile,
                'email': contractor.email,
                'address': f"{contractor.address_line1}, {contractor.city}, {contractor.state}, {contractor.country} - {contractor.pincode}",
                'ehs_officer_name': contractor.ehs_officer_name,
                'ehs_mobile': contractor.ehs_mobile,
                'ehs_email': contractor.ehs_email,
                'work_category': contractor.get_work_category_display(),
                'years_of_experience': contractor.years_of_experience,
                'number_of_workers': contractor.number_of_workers,
                'nature_of_business': contractor.nature_of_business,
                'service_description': contractor.service_description,
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=404)