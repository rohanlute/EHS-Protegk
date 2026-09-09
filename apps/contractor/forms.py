# apps/contractor/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone  
from apps.contractor.models import Contractor, WorkOrder, OnboardingRequest, TrainingSignOff
from apps.organizations.models import Plant, Department
import re

User = get_user_model()


# ==========================================================
# CONTRACTOR FORM
# ==========================================================

class ContractorForm(forms.ModelForm):
    class Meta:
        model = Contractor
        fields = [
            'contractor_code', 'contractor_name', 'contractor_type',
            'registration_number', 'pan_number', 'gstin', 'establishment_year',
            'contact_person', 'designation', 'mobile', 'email',
            'alternate_mobile', 'address_line1', 'address_line2',
            'country', 'state', 'city', 'pincode',
            'nature_of_business', 'work_category', 'service_description',
            'years_of_experience', 'number_of_workers',
            'ehs_officer_name', 'ehs_designation', 'ehs_mobile', 'ehs_email',
            'is_active',
        ]
        widgets = {
            'contractor_code': forms.TextInput(attrs={
                'readonly': 'readonly',
                'class': 'form-control',
                'id': 'id_contractor_code'
            }),
            'contractor_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_contractor_name',
                'required': 'required'
            }),
            'contractor_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_contractor_type',
                'required': 'required'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_registration_number'
            }),
            'pan_number': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_pan_number',
                'maxlength': '10'
            }),
            'gstin': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_gstin',
                'maxlength': '15'
            }),
            'establishment_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'id_establishment_year',
                'min': '1900',
                'max': '2100'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_contact_person',
                'required': 'required'
            }),
            'designation': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_designation',
                'required': 'required'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_mobile',
                'required': 'required'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'id': 'id_email',
                'required': 'required'
            }),
            'alternate_mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_alternate_mobile'
            }),
            'address_line1': forms.Textarea(attrs={
                'class': 'form-control',
                'id': 'id_address_line1',
                'rows': '2',
                'required': 'required'
            }),
            'address_line2': forms.Textarea(attrs={
                'class': 'form-control',
                'id': 'id_address_line2',
                'rows': '2'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_country',
                'required': 'required'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_state',
                'required': 'required'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_city',
                'required': 'required'
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_pincode',
                'required': 'required',
                'maxlength': '6',
                'pattern': '[0-9]{5,6}'
            }),
            'nature_of_business': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_nature_of_business',
                'required': 'required'
            }),
            'work_category': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_work_category',
                'required': 'required'
            }),
            'service_description': forms.Textarea(attrs={
                'class': 'form-control',
                'id': 'id_service_description',
                'rows': '3',
                'required': 'required'
            }),
            'years_of_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'id_years_of_experience',
                'min': '0'
            }),
            'number_of_workers': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'id_number_of_workers',
                'min': '0'
            }),
            'ehs_officer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_ehs_officer_name',
                'required': 'required'
            }),
            'ehs_designation': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_ehs_designation'
            }),
            'ehs_mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_ehs_mobile',
                'required': 'required'
            }),
            'ehs_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'id': 'id_ehs_email',
                'required': 'required'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
                'id': 'id_is_active'
            }),
        }
        labels = {
            'contractor_code': 'Contractor Code',
            'contractor_name': 'Contractor Name',
            'contractor_type': 'Contractor Type',
            'registration_number': 'Registration Number',
            'pan_number': 'PAN Number',
            'gstin': 'GSTIN',
            'establishment_year': 'Establishment Year',
            'contact_person': 'Contact Person',
            'designation': 'Designation',
            'mobile': 'Mobile Number',
            'email': 'Email Address',
            'alternate_mobile': 'Alternate Mobile',
            'address_line1': 'Address Line 1',
            'address_line2': 'Address Line 2',
            'country': 'Country',
            'state': 'State',
            'city': 'City',
            'pincode': 'Pincode',
            'nature_of_business': 'Nature of Business',
            'work_category': 'Work Category',
            'service_description': 'Service Description',
            'years_of_experience': 'Years of Experience',
            'number_of_workers': 'Number of Workers',
            'ehs_officer_name': 'EHS/Safety Officer Name',
            'ehs_designation': 'Designation',
            'ehs_mobile': 'Mobile Number',
            'ehs_email': 'Email Address',
            'is_active': 'Active',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contractor_type'].empty_label = "-- Select Contractor Type --"
        self.fields['work_category'].empty_label = "-- Select Work Category --"
        if not self.instance.pk:
            self.fields['is_active'].initial = True


# ==========================================================
# WORK ORDER FORM
# ==========================================================

class WorkOrderForm(forms.ModelForm):
    """
    Form for creating and editing work orders.
    """
    
    class Meta:
        model = WorkOrder
        fields = [
            'contractor', 
            'onboarding', 
            'contract_number',
            'work_description', 
            'work_category',
            'plant', 
            'department', 
            'location',
            'contractor_supervisor', 
            'contractor_supervisor_contact', 
            'contractor_supervisor_email',
            'company_representative',
            'number_of_workers', 
            'worker_details',
            'start_date', 
            'end_date',
            'risk_level', 
            'attachment', 
            'attachment_name',
            'notes',
        ]
        widgets = {
            'work_description': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'form-control',
                'placeholder': 'Describe the work to be performed in detail...'
            }),
            'worker_details': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control', 
                'placeholder': 'Optional: List of workers assigned to this work order'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control',
                'placeholder': 'Additional notes or remarks...'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
            'contract_number': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Auto-generated on save (CN-YY-XXX)'
            }),
            'attachment_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., Work Order WO-2026-001.pdf'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., Building A, Floor 3, Near HT Panel'
            }),
            'work_category': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Auto-filled from contractor registration'
            }),
            'contractor_supervisor': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Auto-filled from contractor registration'
            }),
            'contractor_supervisor_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Auto-filled from contractor\'s EHS Mobile'
            }),
            'contractor_supervisor_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Auto-filled from contractor\'s EHS Email'
            }),
            'risk_level': forms.Select(attrs={'class': 'form-select'}),
            'contractor': forms.Select(attrs={'class': 'form-select'}),
            'onboarding': forms.Select(attrs={'class': 'form-select'}),
            'plant': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'company_representative': forms.Select(attrs={'class': 'form-select'}),
            'number_of_workers': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 0,
                'placeholder': 'Enter number of workers'
            }),
        }
        labels = {
            'contractor': 'Contractor',
            'onboarding': 'Onboarding Request',
            'contract_number': 'Contract Number',
            'work_description': 'Work Description',
            'work_category': 'Work Category',
            'plant': 'Site / Plant',
            'department': 'Department',
            'location': 'Work Location',
            'contractor_supervisor': 'Contractor Supervisor',
            'contractor_supervisor_contact': 'Supervisor Contact',
            'contractor_supervisor_email': 'Supervisor Email',
            'company_representative': 'Company Representative',
            'number_of_workers': 'Number of Workers',
            'worker_details': 'Worker Details',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'risk_level': 'Risk Level',
            'attachment': 'Attachment',
            'attachment_name': 'Attachment Name',
            'notes': 'Notes',
        }
        help_texts = {
            'contract_number': 'Auto-generated on save (CN-YY-XXX)',
            'work_category': 'Auto-filled from contractor registration',
            'contractor_supervisor': 'Auto-filled from contractor\'s EHS Officer Name',
            'contractor_supervisor_contact': 'Auto-filled from contractor\'s EHS Mobile',
            'contractor_supervisor_email': 'Auto-filled from contractor\'s EHS Email',
            'company_representative': 'Select a Safety Manager from the system',
            'number_of_workers': 'Manual input - Enter the number of workers for this specific work order',
            'risk_level': 'Select the risk level for this work',
            'worker_details': 'Optional: Additional details about workers',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # ==========================================================
        # RISK LEVEL - ADD EMPTY LABEL (First Option)
        # ==========================================================
        self.fields['risk_level'].choices = [('', '-- Select Risk Level --')] + list(WorkOrder.RISK_LEVEL_CHOICES)
        self.fields['risk_level'].initial = ''
        
        # ==========================================================
        # QUERYSETS
        # ==========================================================
        self.fields['contractor'].queryset = Contractor.objects.filter(
            is_active=True,
            onboarding_requests__status='APPROVED'
        ).distinct().order_by('contractor_name')
        self.fields['contractor'].empty_label = "-- Select Contractor --"
        
        self.fields['onboarding'].queryset = OnboardingRequest.objects.filter(
            status='APPROVED'
        )
        self.fields['onboarding'].empty_label = "-- Select Onboarding Request (Optional) --"
        
        self.fields['plant'].queryset = Plant.objects.filter(is_active=True)
        self.fields['plant'].empty_label = "-- Select Plant --"
        
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        self.fields['department'].empty_label = "-- Select Department --"
        
        # ==========================================================
        # COMPANY REPRESENTATIVE - Only show users with Safety Manager role
        # ==========================================================
               # ==========================================================
        # COMPANY REPRESENTATIVE - Only users whose Role is "Safety Manager"
        # ==========================================================
        self.fields['company_representative'].queryset = User.objects.filter(
            role__name__iexact='Safety Manager',
            is_active=True
        ).order_by('first_name', 'last_name')
        
        self.fields['company_representative'].empty_label = "-- Select Company Representative --"
        
        # ==========================================================
        # MAKE FIELDS READ-ONLY / DISABLED
        # ==========================================================
        self.fields['contract_number'].disabled = True
        self.fields['work_category'].disabled = True
        self.fields['contractor_supervisor'].disabled = True
        self.fields['contractor_supervisor_contact'].disabled = True
        self.fields['contractor_supervisor_email'].disabled = True
        
        # ==========================================================
        # REQUIRED FIELDS
        # ==========================================================
        required_fields = [
            'contractor', 
            'work_description', 
            'number_of_workers', 
            'start_date', 
            'end_date',
            'risk_level',
            'company_representative',  # Make it required
        ]
        for field in required_fields:
            self.fields[field].required = True
        
        # ==========================================================
        # NOT REQUIRED (auto-filled)
        # ==========================================================
        self.fields['work_category'].required = False
        self.fields['contractor_supervisor'].required = False
        
        # ==========================================================
        # AUTO-FILL FROM CONTRACTOR IF INSTANCE EXISTS
        # ==========================================================
        if self.instance and self.instance.contractor_id:
            contractor = self.instance.contractor
            if contractor:
                if contractor.work_category:
                    work_category_display = contractor.get_work_category_display()
                    self.initial['work_category'] = work_category_display or contractor.work_category
                    self.fields['work_category'].initial = work_category_display or contractor.work_category
                
                if contractor.ehs_officer_name:
                    self.initial['contractor_supervisor'] = contractor.ehs_officer_name
                    self.fields['contractor_supervisor'].initial = contractor.ehs_officer_name
                
                if contractor.ehs_mobile:
                    self.initial['contractor_supervisor_contact'] = contractor.ehs_mobile
                    self.fields['contractor_supervisor_contact'].initial = contractor.ehs_mobile
                
                if contractor.ehs_email:
                    self.initial['contractor_supervisor_email'] = contractor.ehs_email
                    self.fields['contractor_supervisor_email'].initial = contractor.ehs_email
                
                self.fields['number_of_workers'].help_text = (
                    f"Manual input. Registered workers: {contractor.number_of_workers or 0}"
                )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # DATE VALIDATION
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise ValidationError("End date cannot be before start date.")
        
        # CONTRACTOR VALIDATION
        contractor = cleaned_data.get('contractor')
        onboarding = cleaned_data.get('onboarding')
        if contractor and onboarding and onboarding.contractor != contractor:
            raise ValidationError(
                "The selected onboarding request does not belong to the selected contractor."
            )
        
        # WORKER COUNT VALIDATION
        number_of_workers = cleaned_data.get('number_of_workers')
        if number_of_workers is not None and number_of_workers < 0:
            raise ValidationError("Number of workers cannot be negative.")
        
        # ATTACHMENT VALIDATION
        attachment = cleaned_data.get('attachment')
        attachment_name = cleaned_data.get('attachment_name')
        if attachment and not attachment_name:
            attachment_name = attachment.name
            cleaned_data['attachment_name'] = attachment_name
        
        return cleaned_data


# ==========================================================
# WORK ORDER STATUS FORM
# ==========================================================

class WorkOrderStatusForm(forms.ModelForm):
    """
    Form for updating work order status.
    """
    
    class Meta:
        model = WorkOrder
        fields = ['status', 'closure_remarks']
        widgets = {
            'closure_remarks': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control',
                'placeholder': 'Enter closure remarks or reason for status change...'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].choices = WorkOrder.STATUS_CHOICES
        self.fields['status'].label = "Status"
        self.fields['status'].empty_label = None
        self.fields['closure_remarks'].required = False
        self.fields['closure_remarks'].label = "Closure Remarks"
        
        if self.instance and self.instance.status in ['CLOSED']:
            self.fields['closure_remarks'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        closure_remarks = cleaned_data.get('closure_remarks')
        
        if status == 'CLOSED' and not closure_remarks:
            self.add_error('closure_remarks', 'Closure remarks are required when closing a work order.')
        
        return cleaned_data

# apps/contractor/forms.py - Corrected TrainingSignOffForm

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.contractor.models import Contractor, WorkOrder, OnboardingRequest, TrainingSignOff
from apps.organizations.models import Plant, Department
from apps.toolbox_talk.models import ToolboxTalkSessionPlan
import re

User = get_user_model()


class TrainingSignOffForm(forms.ModelForm):
    """
    Form for creating a Training Sign-Off record.
    """

    class Meta:
        model = TrainingSignOff
        fields = [
            'contractor',
            'work_order',
            'session',
            'contractor_representative',
            'contractor_representative_designation',
            'number_of_workers',
            'company_declaration',
            'company_representative',
            'company_representative_designation',
            'company_signature',
            'contractor_declaration',
            'contractor_supervisor',
            'contractor_supervisor_designation',
            'signoff_date',
            'signoff_time',
            'supporting_documents',
            # REMOVED: company_remarks, contractor_supervisor_remarks, supporting_documents_description
        ]
        widgets = {
            'contractor': forms.Select(attrs={
                'class': 'form-select', 'id': 'id_contractor', 'required': 'required'
            }),
            'work_order': forms.Select(attrs={
                'class': 'form-select', 'id': 'id_work_order'
            }),
            'session': forms.Select(attrs={
                'class': 'form-select', 'id': 'id_session', 'required': 'required'
            }),
            'contractor_representative': forms.TextInput(attrs={
                'class': 'form-control', 'id': 'id_contractor_representative', 'readonly': 'readonly'
            }),
            'contractor_representative_designation': forms.TextInput(attrs={
                'class': 'form-control', 'id': 'id_contractor_representative_designation', 'readonly': 'readonly'
            }),
            'number_of_workers': forms.NumberInput(attrs={
                'class': 'form-control', 'id': 'id_number_of_workers', 'readonly': 'readonly'
            }),
            'company_declaration': forms.CheckboxInput(attrs={
                'class': 'form-check-input', 'id': 'id_company_declaration'
            }),
            'company_representative': forms.Select(attrs={
                'class': 'form-select', 'id': 'id_company_representative'
            }),
            'company_representative_designation': forms.TextInput(attrs={
                'class': 'form-control', 'id': 'id_company_representative_designation', 'readonly': 'readonly'
            }),
            'company_signature': forms.ClearableFileInput(attrs={
                'class': 'form-control', 'id': 'id_company_signature'
            }),
            'contractor_declaration': forms.CheckboxInput(attrs={
                'class': 'form-check-input', 'id': 'id_contractor_declaration'
            }),
            'contractor_supervisor': forms.TextInput(attrs={
                'class': 'form-control', 'id': 'id_contractor_supervisor', 'readonly': 'readonly'
            }),
            'contractor_supervisor_designation': forms.TextInput(attrs={
                'class': 'form-control', 'id': 'id_contractor_supervisor_designation', 'readonly': 'readonly'
            }),
            'signoff_date': forms.DateInput(attrs={
                'type': 'date', 'class': 'form-control', 'id': 'id_signoff_date'
            }),
            'signoff_time': forms.TimeInput(attrs={
                'type': 'time', 'class': 'form-control', 'id': 'id_signoff_time'
            }),
            'supporting_documents': forms.ClearableFileInput(attrs={
                'class': 'form-control', 
                'id': 'id_supporting_documents',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png'
            }),
        }
        labels = {
            'company_declaration': "I confirm the above statement.",
            'contractor_declaration': "I confirm the above statement.",
            'supporting_documents': "Supporting Documents",
        }

    def __init__(self, *args, **kwargs):
        # Pop request from kwargs before calling super()
        self.request = kwargs.pop('request', None)
        
        super().__init__(*args, **kwargs)

        # Make signature and documents fields NOT required at the field level
        self.fields['company_signature'].required = False
        self.fields['supporting_documents'].required = False

        # Contractor queryset
        self.fields['contractor'].queryset = Contractor.objects.filter(
            is_active=True,
            work_orders__status='APPROVED'
        ).distinct().order_by('contractor_name')
        self.fields['contractor'].empty_label = "-- Select Contractor --"

        # Work Order - queryset will be filtered by contractor in clean()
        self.fields['work_order'].queryset = WorkOrder.objects.filter(status='APPROVED')
        self.fields['work_order'].empty_label = "-- Select Work Order --"
        self.fields['work_order'].required = True

        # Session queryset
        self.fields['session'].queryset = ToolboxTalkSessionPlan.objects.filter(
            status='COMPLETED'
        ).order_by('-planned_date', '-planned_time')
        self.fields['session'].empty_label = "-- Select Training Session --"

        # Company representative
        self.fields['company_representative'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        self.fields['company_representative'].empty_label = "-- Select Plant Representative --"
        self.fields['company_representative'].required = True

        # Make readonly fields not required
        for f in [
            'contractor_representative', 'contractor_representative_designation',
            'number_of_workers', 'contractor_supervisor',
            'contractor_supervisor_designation', 'company_representative_designation',
        ]:
            self.fields[f].required = False

        # Set initial values for date and time
        if not self.instance.pk:
            self.fields['signoff_date'].initial = timezone.now().date()
            self.fields['signoff_time'].initial = timezone.now().time()

    def clean(self):
        cleaned_data = super().clean()
        work_order = cleaned_data.get('work_order')
        contractor = cleaned_data.get('contractor')
        session = cleaned_data.get('session')

        # Validate work_order belongs to contractor
        if work_order and contractor:
            if work_order.contractor_id != contractor.id:
                self.add_error('work_order', "The selected Work Order does not belong to the selected Contractor.")
        elif work_order and not contractor:
            self.add_error('contractor', "Please select a contractor first.")

        # Validate work order is approved
        if work_order and work_order.status != 'APPROVED':
            self.add_error('work_order', "Training sign-off can only be created for an Approved Work Order.")

        # Validate session exists
        if session and not session:
            self.add_error('session', "Please select a valid training session.")

        # Validate declarations
        if not cleaned_data.get('company_declaration'):
            self.add_error('company_declaration', "Company declaration must be confirmed.")

        if not cleaned_data.get('contractor_declaration'):
            self.add_error('contractor_declaration', "Contractor declaration must be confirmed.")

        # Validate Company Signature
        company_signature = None
        
        # Get files from request if available
        if hasattr(self, 'request') and self.request:
            if 'company_signature' in self.request.FILES:
                company_signature = self.request.FILES['company_signature']
        
        # Also check files attribute as fallback
        if not company_signature and hasattr(self, 'files'):
            if 'company_signature' in self.files:
                company_signature = self.files['company_signature']

        # Validate company signature
        if not company_signature:
            self.add_error('company_signature', "Company representative signature is required. Please upload a signature file.")
        elif hasattr(company_signature, 'size') and company_signature.size == 0:
            self.add_error('company_signature', "The uploaded signature file is empty. Please upload a valid file.")

        # Auto-fill company_representative from work_order if not set
        if work_order and not cleaned_data.get('company_representative'):
            cleaned_data['company_representative'] = work_order.company_representative

        return cleaned_data