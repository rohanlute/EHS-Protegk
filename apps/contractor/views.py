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
    PreQualificationQuestion
)
from apps.contractor.forms import ContractorForm
from django.contrib.auth import get_user_model

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
    
    def post(self, request):
        contractor_id = request.POST.get('contractor')
        prequal_question_ids = request.POST.getlist('prequal_questions')
        document_ids = request.POST.getlist('documents')
        notes = request.POST.get('notes', '')
        
        # Validate
        if not contractor_id:
            messages.error(request, 'Please select a contractor.')
            return self.get(request)
        
        if not prequal_question_ids:
            messages.error(request, 'Please select at least one pre-qualification question.')
            return self.get(request)
        
        if not document_ids:
            messages.error(request, 'Please select at least one document for verification.')
            return self.get(request)
        
        contractor = get_object_or_404(Contractor, id=contractor_id)
        
        # Check if contractor already has a pending onboarding
        existing_onboarding = OnboardingRequest.objects.filter(
            contractor=contractor,
            status__in=['DRAFT', 'PENDING']
        ).first()
        
        if existing_onboarding:
            messages.warning(request, f'Contractor "{contractor.contractor_name}" already has a pending onboarding request.')
            return redirect('contractor:onboarding_detail', pk=existing_onboarding.pk)
        
        # Create Onboarding Request - EHS Officer is auto-assigned from contractor
        onboarding = OnboardingRequest.objects.create(
            contractor=contractor,
            ehs_officer=contractor.ehs_officer_name,  # Store EHS officer name from contractor
            notes=notes,
            submitted_by=request.user,
            status='PENDING'
        )
        
        # Add pre-qualification questions (store as JSON)
        prequal_answers = {}
        for q_id in prequal_question_ids:
            prequal_answers[str(q_id)] = False  # Default answer, will be filled by contractor
        onboarding.pre_qualification_answers = prequal_answers
        onboarding.save()
        
        # Add selected documents
        for doc_id in document_ids:
            doc_type = get_object_or_404(DocumentType, id=doc_id)
            OnboardingDocumentRequirement.objects.create(
                onboarding=onboarding,
                document_type=doc_type,
                is_required=True,
                status='PENDING'
            )
        
        onboarding.submitted_at = timezone.now()
        onboarding.save()
        
        messages.success(
            request, 
            f'Onboarding request sent successfully! Documents and questions sent to {contractor.ehs_officer_name} for upload.'
        )
        
        return redirect('contractor:contractor_list')


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