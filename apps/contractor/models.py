# apps/contractor/models.py

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

User = get_user_model()


# ==========================================================
# SECTION 1: CONTRACTOR & PORTAL USER MODELS
# ==========================================================

class Contractor(models.Model):
    """Main Contractor model."""
    
    CONTRACTOR_TYPE_CHOICES = [
        ('ELECTRICAL', 'Electrical'),
        ('CIVIL', 'Civil'),
        ('MECHANICAL', 'Mechanical'),
        ('CONSTRUCTION', 'Construction'),
        ('HOUSEKEEPING', 'Housekeeping'),
        ('SECURITY', 'Security'),
        ('TRANSPORT', 'Transport'),
        ('WASTE_MANAGEMENT', 'Waste Management'),
        ('FACILITY_MANAGEMENT', 'Facility Management'),
        ('OTHER', 'Other'),
    ]
    
    WORK_CATEGORY_CHOICES = [
        ('ELECTRICAL', 'Electrical'),
        ('CIVIL', 'Civil'),
        ('MECHANICAL', 'Mechanical'),
        ('CONSTRUCTION', 'Construction'),
        ('HOUSEKEEPING', 'Housekeeping'),
        ('SECURITY', 'Security'),
        ('TRANSPORT', 'Transport'),
        ('WASTE_MANAGEMENT', 'Waste Management'),
        ('FACILITY_MANAGEMENT', 'Facility Management'),
        ('OTHER', 'Other'),
    ]

    # SECTION A – Basic Information
    contractor_code = models.CharField(
        max_length=50, unique=True, blank=True,
        help_text="Auto-generated unique identifier (e.g., CM001)"
    )
    contractor_name = models.CharField(max_length=200, verbose_name="Contractor Company Name")
    contractor_type = models.CharField(
        max_length=50, choices=CONTRACTOR_TYPE_CHOICES, default='OTHER',
        verbose_name="Contractor Company Type"
    )
    registration_number = models.CharField(max_length=100, blank=True, verbose_name="Registration Number")
    pan_number = models.CharField(max_length=20, blank=True, verbose_name="PAN Number")
    gstin = models.CharField(max_length=30, blank=True, verbose_name="GSTIN")
    establishment_year = models.IntegerField(
        null=True, blank=True, verbose_name="Establishment Year",
        validators=[MinValueValidator(1900), MaxValueValidator(2100)]
    )

    # SECTION B – Contact Information
    contact_person = models.CharField(max_length=100, verbose_name="Contact Person")
    designation = models.CharField(max_length=100, verbose_name="Designation")
    mobile = models.CharField(max_length=15, verbose_name="Mobile Number")
    email = models.EmailField(verbose_name="Email Address")
    alternate_mobile = models.CharField(max_length=15, blank=True, verbose_name="Alternate Mobile")
    address_line1 = models.TextField(verbose_name="Address Line 1")
    address_line2 = models.TextField(blank=True, verbose_name="Address Line 2")
    country = models.CharField(max_length=50, verbose_name="Country")
    state = models.CharField(max_length=50, verbose_name="State")
    city = models.CharField(max_length=50, verbose_name="City")
    pincode = models.CharField(max_length=10, verbose_name="Pincode")

    # SECTION C – Business / Work Information
    nature_of_business = models.CharField(max_length=200, verbose_name="Nature of Business")
    work_category = models.CharField(
        max_length=50, choices=WORK_CATEGORY_CHOICES, default='OTHER',
        verbose_name="Work Category"
    )
    service_description = models.TextField(verbose_name="Service Description")
    years_of_experience = models.IntegerField(
        null=True, blank=True, verbose_name="Years of Experience",
        validators=[MinValueValidator(0)]
    )
    number_of_workers = models.IntegerField(
        null=True, blank=True, verbose_name="Number of Workers",
        validators=[MinValueValidator(0)]
    )

    # SECTION D – EHS / Responsible Person
    ehs_officer_name = models.CharField(max_length=100, verbose_name="EHS/Safety Officer Name")
    ehs_designation = models.CharField(max_length=100, blank=True, verbose_name="EHS Designation")
    ehs_mobile = models.CharField(max_length=15, verbose_name="EHS Mobile Number")
    ehs_email = models.EmailField(verbose_name="EHS Email Address")

    # Status
    is_active = models.BooleanField(default=True, verbose_name="Active")

    # Metadata
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_contractors', verbose_name="Created By"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contractor'
        verbose_name_plural = 'Contractors'

    def __str__(self):
        return f"{self.contractor_code} - {self.contractor_name}"

    def save(self, *args, **kwargs):
        if not self.contractor_code:
            last_contractor = Contractor.objects.order_by('-id').first()
            if last_contractor and last_contractor.contractor_code:
                try:
                    last_number = int(last_contractor.contractor_code[2:])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            self.contractor_code = f'CM{str(new_number).zfill(3)}'
        super().save(*args, **kwargs)

    def get_contractor_type_display(self):
        return dict(self.CONTRACTOR_TYPE_CHOICES).get(self.contractor_type, self.contractor_type)

    def get_work_category_display(self):
        return dict(self.WORK_CATEGORY_CHOICES).get(self.work_category, self.work_category)

    def get_status_display(self):
        return 'Active' if self.is_active else 'Inactive'


class ContractorPortalUser(models.Model):
    """Separate login account for external Contractor Portal users."""

    USER_TYPE_CHOICES = [
        ('CONTACT_PERSON', 'Contact Person'),
        ('EHS_OFFICER', 'EHS Officer'),
    ]

    contractor = models.ForeignKey(Contractor, on_delete=models.CASCADE, related_name='portal_users')
    name = models.CharField(max_length=150, verbose_name="Name")
    email = models.EmailField(verbose_name="Email Address")
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, verbose_name="User Type")
    password = models.CharField(max_length=255, verbose_name="Password")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Contractor Portal User'
        verbose_name_plural = 'Contractor Portal Users'

    def __str__(self):
        return f"{self.name} - {self.email}"

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)


# ==========================================================
# SECTION 2: PRE-QUALIFICATION & DOCUMENT MODELS
# ==========================================================

class PreQualificationQuestion(models.Model):
    """Pre-qualification questions for contractor assessment"""
    
    QUESTION_TYPE_CHOICES = [
        ('EXPERIENCE', 'Experience'),
        ('EHS_PERFORMANCE', 'EHS Performance'),
        ('SAFETY_CAPABILITY', 'Safety Capability'),
        ('TECHNICAL_CAPABILITY', 'Technical Capability'),
        ('INSURANCE', 'Insurance'),
        ('FINANCIAL', 'Financial'),
        ('GENERAL', 'General'),
    ]
    
    question = models.CharField(max_length=500)
    question_type = models.CharField(max_length=30, choices=QUESTION_TYPE_CHOICES, default='GENERAL')
    is_active = models.BooleanField(default=True)
    is_mandatory = models.BooleanField(default=False)
    sequence = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sequence', 'id']
        verbose_name = 'Pre-Qualification Question'
        verbose_name_plural = 'Pre-Qualification Questions'

    def __str__(self):
        return self.question


class DocumentType(models.Model):
    """Document types for onboarding checklist"""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Document Type'
        verbose_name_plural = 'Document Types'

    def __str__(self):
        return self.name


class ContractorPreQualification(models.Model):
    """
    Stores contractor pre-qualification assessment and risk classification.
    """
    
    RISK_LEVEL_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("CRITICAL", "Critical"),
    ]

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("UNDER_REVIEW", "Under Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    contractor = models.ForeignKey("Contractor", on_delete=models.CASCADE, related_name="pre_qualifications")
    assessment_date = models.DateField(auto_now_add=True)

    # Experience
    years_of_experience = models.PositiveIntegerField(default=0)
    similar_work_experience = models.TextField(blank=True, null=True)
    previous_clients = models.TextField(blank=True, null=True)

    # EHS Performance
    previous_ehs_performance = models.TextField(blank=True, null=True)
    accident_history = models.PositiveIntegerField(default=0)
    fatality_history = models.PositiveIntegerField(default=0)
    lost_time_injuries = models.PositiveIntegerField(default=0)
    regulatory_violations = models.PositiveIntegerField(default=0)

    # Safety Capability
    safety_manpower = models.PositiveIntegerField(default=0)
    total_manpower = models.PositiveIntegerField(default=0)
    has_safety_policy = models.BooleanField(default=False)
    has_training_system = models.BooleanField(default=False)
    has_emergency_preparedness = models.BooleanField(default=False)

    # Technical / Operational Capability
    equipment_capability = models.TextField(blank=True, null=True)
    training_capability = models.TextField(blank=True, null=True)

    # Insurance
    has_insurance = models.BooleanField(default=False)

    # Risk Classification
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default="MEDIUM")
    risk_reason = models.TextField(blank=True, null=True)

    # Approval Workflow
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="DRAFT")
    reviewer_comments = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_contractor_prequalifications"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contractor Pre-Qualification"
        verbose_name_plural = "Contractor Pre-Qualifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.contractor} - {self.get_risk_level_display()}"


class ContractorDocument(models.Model):
    """
    Stores important contractor documents and their verification/expiry status.
    """

    DOCUMENT_TYPE_CHOICES = [
        ("COMPANY_REGISTRATION", "Company Registration"),
        ("PAN", "PAN"),
        ("GST", "GST"),
        ("CONTRACTOR_LICENSE", "Contractor License"),
        ("PF", "PF Registration"),
        ("ESIC", "ESIC Registration"),
        ("INSURANCE", "Insurance"),
        ("WORKMEN_COMPENSATION", "Workmen Compensation"),
        ("PUBLIC_LIABILITY", "Public Liability Insurance"),
        ("SAFETY_POLICY", "Safety Policy"),
        ("EHS_CERTIFICATION", "EHS Certification"),
    ]

    contractor = models.ForeignKey(Contractor, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    document = models.FileField(upload_to="contractors/documents/")
    remarks = models.TextField(blank=True, null=True)
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="verified_contractor_documents"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contractor Document"
        verbose_name_plural = "Contractor Documents"
        ordering = ["document_type"]

    def __str__(self):
        return f"{self.contractor} - {self.get_document_type_display()}"


# ==========================================================
# SECTION 3: ONBOARDING MODELS
# ==========================================================

class OnboardingRequest(models.Model):
    """Onboarding request for contractor with pre-qualification and documents"""
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    ]
    
    contractor = models.ForeignKey(Contractor, on_delete=models.CASCADE, related_name='onboarding_requests')
    ehs_officer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='assigned_onboarding',
        verbose_name="EHS Officer / Responsible Person"
    )
    pre_qualification_answers = models.JSONField(default=dict, blank=True)
    question_remarks = models.JSONField(default=dict, blank=True)
    documents = models.ManyToManyField(
        DocumentType, through='OnboardingDocumentRequirement', related_name='onboarding_requests'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    notes = models.TextField(blank=True)
    submitted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='submitted_onboarding'
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='approved_onboarding', blank=True
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Onboarding Request'
        verbose_name_plural = 'Onboarding Requests'

    def __str__(self):
        return f"{self.contractor.contractor_code} - {self.contractor.contractor_name}"


class OnboardingDocumentRequirement(models.Model):
    """Individual document requirement for onboarding"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('UPLOADED', 'Uploaded'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
    ]
    
    onboarding = models.ForeignKey(
        OnboardingRequest, on_delete=models.CASCADE, related_name='document_requirements'
    )
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE)
    is_required = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    document_file = models.FileField(upload_to='onboarding_documents/%Y/%m/%d/', null=True, blank=True)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_documents'
    )
    uploaded_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_documents'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['document_type__name']
        unique_together = ['onboarding', 'document_type']
        verbose_name = 'Onboarding Document Requirement'
        verbose_name_plural = 'Onboarding Document Requirements'

    def __str__(self):
        return f"{self.onboarding.contractor.contractor_name} - {self.document_type.name}"


class ContractorAssignment(models.Model):
    """Controls external Contractor Portal access for an onboarding assignment."""

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
    ]

    onboarding = models.ForeignKey(OnboardingRequest, on_delete=models.CASCADE, related_name='assignments')
    portal_user = models.ForeignKey(ContractorPortalUser, on_delete=models.CASCADE, related_name='assignments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    is_access_active = models.BooleanField(default=True, verbose_name="Access Active")
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    access_token = models.UUIDField(default=uuid.uuid4, null=True, blank=True, editable=False)

    class Meta:
        ordering = ['-assigned_at']
        verbose_name = 'Contractor Assignment'
        verbose_name_plural = 'Contractor Assignments'

    def __str__(self):
        return f"{self.onboarding.contractor.contractor_name} - {self.portal_user.email}"

    def deactivate(self, status='COMPLETED'):
        self.status = status
        self.is_access_active = False
        if status == 'COMPLETED':
            self.completed_at = timezone.now()
        self.save(update_fields=['status', 'is_access_active', 'completed_at'])

    @property
    def can_access(self):
        if not self.is_access_active:
            return False
        if self.status != 'ACTIVE':
            return False
        if self.expires_at and timezone.now() >= self.expires_at:
            self.status = 'EXPIRED'
            self.is_access_active = False
            self.save(update_fields=['status', 'is_access_active'])
            return False
        return True


# ==========================================================
# SECTION 4: WORK ORDER MODEL
# ==========================================================

class WorkOrder(models.Model):
    """Work Order / Contract for approved contractors."""
    
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CLOSED', 'Closed'),
    ]
    
    RISK_LEVEL_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    work_order_number = models.CharField(max_length=50, unique=True, blank=True)
    contract_number = models.CharField(max_length=50, unique=True, blank=True)
    contractor = models.ForeignKey(
        Contractor, on_delete=models.CASCADE, related_name='work_orders',
        limit_choices_to={'onboarding_requests__status': 'APPROVED'},
    )
    onboarding = models.ForeignKey(
        OnboardingRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='work_orders'
    )
    work_description = models.TextField(verbose_name="Work Description")
    work_category = models.CharField(max_length=50, verbose_name="Work Category")
    plant = models.ForeignKey(
        'organizations.Plant', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='work_orders', verbose_name="Site / Plant"
    )
    department = models.ForeignKey(
        'organizations.Department', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='work_orders', verbose_name="Department"
    )
    location = models.CharField(max_length=200, blank=True, verbose_name="Work Location")
    contractor_supervisor = models.CharField(max_length=100, blank=True, verbose_name="Contractor Supervisor")
    contractor_supervisor_contact = models.CharField(max_length=15, blank=True, verbose_name="Supervisor Contact")
    contractor_supervisor_email = models.EmailField(blank=True, verbose_name="Supervisor Email")
    company_representative = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='work_orders_representative', verbose_name="Company Representative"
    )
    number_of_workers = models.PositiveIntegerField(default=0, verbose_name="Number of Workers")
    worker_details = models.TextField(blank=True, verbose_name="Worker Details")
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default='MEDIUM', verbose_name="Risk Level")
    attachment = models.FileField(upload_to='work_orders/%Y/%m/%d/', null=True, blank=True, verbose_name="Work Order Attachment")
    attachment_name = models.CharField(max_length=200, blank=True, verbose_name="Attachment Name")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_work_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_work_orders'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='closed_work_orders'
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closure_remarks = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Work Order'
        verbose_name_plural = 'Work Orders'
    
    def __str__(self):
        return f"{self.work_order_number} - {self.contractor.contractor_name}"
    
    def save(self, *args, **kwargs):
        # Auto-generate WO number
        if not self.work_order_number:
            year = timezone.now().year
            last_wo = WorkOrder.objects.filter(work_order_number__startswith=f'WO-{year}-').order_by('-work_order_number').first()
            if last_wo and last_wo.work_order_number:
                try:
                    last_number = int(last_wo.work_order_number.split('-')[-1])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            self.work_order_number = f'WO-{year}-{str(new_number).zfill(4)}'
        
        # Auto-generate Contract number
        if not self.contract_number:
            current_year = timezone.now().year
            year_short = str(current_year)[-2:]
            last_contract = WorkOrder.objects.filter(contract_number__startswith=f'CN-{year_short}-').order_by('-contract_number').first()
            if last_contract and last_contract.contract_number:
                try:
                    last_number = int(last_contract.contract_number.split('-')[-1])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            self.contract_number = f'CN-{year_short}-{str(new_number).zfill(3)}'
        
        # Auto-fill from contractor
        if self.contractor:
            if not self.work_category:
                self.work_category = self.contractor.work_category
            if not self.contractor_supervisor:
                self.contractor_supervisor = self.contractor.ehs_officer_name or ''
            if not self.contractor_supervisor_contact:
                self.contractor_supervisor_contact = self.contractor.ehs_mobile or ''
            if not self.contractor_supervisor_email:
                self.contractor_supervisor_email = self.contractor.ehs_email or ''
        
        super().save(*args, **kwargs)
    
    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def get_risk_level_display(self):
        return dict(self.RISK_LEVEL_CHOICES).get(self.risk_level, self.risk_level)
    
    def get_work_category_display(self):
        return dict(Contractor.WORK_CATEGORY_CHOICES).get(self.work_category, self.work_category)
    
    @property
    def is_completed(self):
        return self.status in ['CLOSED']
    
    @property
    def is_active_work(self):
        return self.status in ['APPROVED']
    
    @property
    def is_pending(self):
        return self.status in ['SUBMITTED']
    
    @property
    def days_remaining(self):
        if self.end_date:
            delta = self.end_date - timezone.now().date()
            return delta.days
        return None
    
    @property
    def plant_name(self):
        return self.plant.name if self.plant else 'N/A'
    
    @property
    def department_name(self):
        return self.department.name if self.department else 'N/A'
    
    @property
    def company_representative_name(self):
        return self.company_representative.get_full_name() if self.company_representative else 'N/A'
    
    @property
    def contractor_supervisor_name(self):
        return self.contractor_supervisor if self.contractor_supervisor else 'N/A'
    
    @property
    def contractor_workers(self):
        return self.contractor.number_of_workers if self.contractor else 0


# ==========================================================
# SECTION 5: TRAINING SIGN-OFF MODEL
# ==========================================================

class TrainingSignOff(models.Model):
    """Post-training confirmation / sign-off record."""

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('COMPLETED', 'Completed'),
    ]

    signoff_number = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    contractor = models.ForeignKey(Contractor, on_delete=models.PROTECT, related_name='training_signoffs')
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.PROTECT, related_name='training_signoffs',
        limit_choices_to={'status': 'APPROVED'}
    )
    session = models.ForeignKey(
        'toolbox_talk.ToolboxTalkSessionPlan', on_delete=models.PROTECT,
        related_name='contractor_signoffs'
    )
    contractor_representative = models.CharField(max_length=150, verbose_name="Contractor Representative")
    contractor_representative_designation = models.CharField(max_length=150, blank=True)
    number_of_workers = models.PositiveIntegerField(default=0)
    
    # Company Sign-Off
    company_declaration = models.BooleanField(default=False)
    company_representative = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='training_signoffs_as_company_rep'
    )
    company_representative_designation = models.CharField(max_length=150, blank=True)
    company_signature = models.FileField(
        upload_to='training_signoff/signatures/company/%Y/%m/%d/', null=True, blank=True
    )
    
    # Contractor Sign-Off
    contractor_declaration = models.BooleanField(default=False)
    contractor_supervisor = models.CharField(max_length=150, blank=True)
    contractor_supervisor_designation = models.CharField(max_length=150, blank=True)
    
    # Supporting Documents
    supporting_documents = models.FileField(
        upload_to='training_signoff/documents/%Y/%m/%d/', null=True, blank=True
    )
    
    # Meta
    signoff_date = models.DateField(default=timezone.now, verbose_name="Date")
    signoff_time = models.TimeField(default=timezone.now, verbose_name="Time")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_training_signoffs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Training Sign-Off'
        verbose_name_plural = 'Training Sign-Offs'

    def __str__(self):
        return f"{self.signoff_number} - {self.contractor.contractor_name}"

    def save(self, *args, **kwargs):
        if not self.signoff_number:
            year = timezone.now().year
            last = TrainingSignOff.objects.filter(signoff_number__startswith=f'TSO-{year}-').order_by('-signoff_number').first()
            if last and last.signoff_number:
                try:
                    last_number = int(last.signoff_number.split('-')[-1])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            self.signoff_number = f'TSO-{year}-{str(new_number).zfill(4)}'
        super().save(*args, **kwargs)

    @property
    def is_fully_signed(self):
        return bool(self.company_declaration and self.company_signature and self.contractor_declaration)
    
    @property
    def has_documents(self):
        return bool(self.supporting_documents)


# ==========================================================
# SECTION 6: CONTRACTOR INSPECTION MODELS
# ==========================================================

class ContractorInspectionQuestion(models.Model):
    """Pre-defined questions for contractor inspections"""
    
    CATEGORY_CHOICES = [
        ('PPE', 'PPE'),
        ('SAFETY', 'Safety'),
        ('HOUSEKEEPING', 'Housekeeping'),
        ('CONTRACTOR_MANAGEMENT', 'Contractor Management'),
    ]
    
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    question_text = models.TextField()
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'display_order']
        verbose_name = 'Contractor Inspection Question'
        verbose_name_plural = 'Contractor Inspection Questions'
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.question_text[:50]}"


class ContractorInspection(models.Model):
    """Contractor Inspection Schedule"""
    
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('CLOSED', 'Closed'),
        ('CANCELLED', 'Cancelled'),
        ('OVERDUE', 'Overdue'),
    ]
    
    inspection_code = models.CharField(max_length=50, unique=True, blank=True)
    contractor = models.ForeignKey('Contractor', on_delete=models.CASCADE, related_name='inspections')
    work_order = models.ForeignKey('WorkOrder', on_delete=models.SET_NULL, null=True, blank=True, related_name='inspections')
    plant = models.ForeignKey('organizations.Plant', on_delete=models.SET_NULL, null=True, related_name='contractor_inspections')
    zone = models.ForeignKey('organizations.Zone', on_delete=models.SET_NULL, null=True, blank=True, related_name='contractor_inspections')
    location = models.ForeignKey('organizations.Location', on_delete=models.SET_NULL, null=True, blank=True, related_name='contractor_inspections')
    sublocation = models.ForeignKey('organizations.SubLocation', on_delete=models.SET_NULL, null=True, blank=True, related_name='contractor_inspections')
    department = models.ForeignKey('organizations.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='contractor_inspections')
    
    # Snapshot fields
    contractor_work_category = models.CharField(max_length=50, blank=True)
    contractor_supervisor = models.CharField(max_length=150, blank=True)
    contractor_supervisor_designation = models.CharField(max_length=150, blank=True)
    contractor_supervisor_mobile = models.CharField(max_length=15, blank=True)
    contractor_supervisor_email = models.EmailField(blank=True)
    number_of_workers = models.PositiveIntegerField(default=0)
    
    selected_questions = models.ManyToManyField(ContractorInspectionQuestion, related_name='inspections', blank=True)
    
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_contractor_inspections')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_contractor_inspections')
    
    inspection_start_date = models.DateField()
    inspection_end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    notes = models.TextField(blank=True)
    
    # Auto Schedule
    enable_auto_schedule = models.BooleanField(default=False)
    due_date_offset_days = models.PositiveIntegerField(default=7)
    parent_inspection = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_inspections')
    is_recurring_copy = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contractor Inspection'
        verbose_name_plural = 'Contractor Inspections'
    
    def __str__(self):
        return f"{self.inspection_code} - {self.contractor.contractor_name}"
    
    def save(self, *args, **kwargs):
        if not self.inspection_code:
            year = timezone.now().year
            last = ContractorInspection.objects.filter(inspection_code__startswith=f'CI-{year}-').order_by('-inspection_code').first()
            if last and last.inspection_code:
                try:
                    last_number = int(last.inspection_code.split('-')[-1])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            self.inspection_code = f'CI-{year}-{str(new_number).zfill(4)}'
        
        if self.contractor:
            if not self.contractor_work_category:
                self.contractor_work_category = self.contractor.work_category
            if not self.contractor_supervisor:
                self.contractor_supervisor = self.contractor.ehs_officer_name
            if not self.contractor_supervisor_designation:
                self.contractor_supervisor_designation = self.contractor.ehs_designation
            if not self.contractor_supervisor_mobile:
                self.contractor_supervisor_mobile = self.contractor.ehs_mobile
            if not self.contractor_supervisor_email:
                self.contractor_supervisor_email = self.contractor.ehs_email
            if not self.number_of_workers and self.contractor.number_of_workers:
                self.number_of_workers = self.contractor.number_of_workers
        
        super().save(*args, **kwargs)
    
    def create_recurring_copy(self):
        """Create a copy for next month."""
        from datetime import timedelta
        today = timezone.now().date()
        
        if today.month == 12:
            next_month_start = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month_start = today.replace(month=today.month + 1, day=1)
        
        next_month_end = next_month_start + timedelta(days=self.due_date_offset_days - 1)
        
        new_inspection = ContractorInspection(
            contractor=self.contractor, work_order=self.work_order, plant=self.plant,
            zone=self.zone, location=self.location, sublocation=self.sublocation,
            department=self.department,
            contractor_work_category=self.contractor_work_category,
            contractor_supervisor=self.contractor_supervisor,
            contractor_supervisor_designation=self.contractor_supervisor_designation,
            contractor_supervisor_mobile=self.contractor_supervisor_mobile,
            contractor_supervisor_email=self.contractor_supervisor_email,
            number_of_workers=self.number_of_workers, assigned_to=self.assigned_to,
            assigned_by=self.assigned_by, inspection_start_date=next_month_start,
            inspection_end_date=next_month_end, enable_auto_schedule=True,
            due_date_offset_days=self.due_date_offset_days, parent_inspection=self,
            is_recurring_copy=True, status='SCHEDULED',
            notes=f"Auto-generated recurring from {self.inspection_code}"
        )
        new_inspection.save()
        new_inspection.selected_questions.set(self.selected_questions.all())
        return new_inspection


class ContractorInspectionResponse(models.Model):
    """Response to inspection questions"""
    
    ANSWER_CHOICES = [
        ('YES', 'Yes'),
        ('NO', 'No'),
    ]
    
    inspection = models.ForeignKey(ContractorInspection, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(ContractorInspectionQuestion, on_delete=models.CASCADE)
    answer = models.CharField(max_length=10, choices=ANSWER_CHOICES)
    remarks = models.TextField(blank=True)
    photo = models.ImageField(upload_to='contractor_inspections/%Y/%m/%d/', null=True, blank=True)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['inspection', 'question']
        ordering = ['question__category', 'question__display_order']
    
    def __str__(self):
        return f"{self.inspection.inspection_code} - {self.question.question_text[:30]}"


# ==========================================================
# SECTION 7: PERFORMANCE MONITORING MODELS (DEFINED ONCE)
# ==========================================================

class ContractorPerformanceMetric(models.Model):
    """Stores performance metrics for a contractor for a specific period."""
    
    PERIOD_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]
    
    contractor = models.ForeignKey(Contractor, on_delete=models.CASCADE, related_name='performance_metrics')
    period_type = models.CharField(max_length=20, choices=PERIOD_CHOICES, default='MONTHLY')
    period_month = models.IntegerField(help_text="Month (1-12)")
    period_year = models.IntegerField(help_text="Year")
    
    # Individual Scores
    pre_qualification_score = models.FloatField(default=0)
    risk_level = models.CharField(max_length=20, choices=ContractorPreQualification.RISK_LEVEL_CHOICES, default='MEDIUM')
    document_compliance_score = models.FloatField(default=0)
    training_compliance_score = models.FloatField(default=0)
    inspection_compliance_score = models.FloatField(default=0)
    inspections_count = models.IntegerField(default=0)
    work_order_completion_score = models.FloatField(default=0)
    work_orders_count = models.IntegerField(default=0)
    
    # Overall
    overall_performance_score = models.FloatField(default=0)
    rating = models.CharField(max_length=30, blank=True)
    
    calculated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-period_year', '-period_month']
        verbose_name = 'Contractor Performance Metric'
        verbose_name_plural = 'Contractor Performance Metrics'
        unique_together = ['contractor', 'period_type', 'period_month', 'period_year']
    
    def __str__(self):
        return f"{self.contractor.contractor_name} - {self.period_type} {self.period_month}/{self.period_year}"


# apps/contractor/models.py

class PerformanceWeightConfig(models.Model):
    """Configurable weights for performance calculation."""
    
    name = models.CharField(max_length=100, default='Default Configuration')
    # weight_pre_qualification = models.FloatField(default=0)  # REMOVED
    weight_onboarding_compliance = models.FloatField(default=25)
    weight_training_compliance = models.FloatField(default=25)
    weight_inspection_compliance = models.FloatField(default=30)
    weight_work_order_completion = models.FloatField(default=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Performance Weight Configuration'
        verbose_name_plural = 'Performance Weight Configurations'
    
    def __str__(self):
        return f"{self.name} (Active: {self.is_active})"
    
    def get_total_weight(self):
        return (
            self.weight_onboarding_compliance +
            self.weight_training_compliance +
            self.weight_inspection_compliance +
            self.weight_work_order_completion
        )

class PerformanceScoreHistory(models.Model):
    """Historical record of performance scores for trend analysis."""
    
    contractor = models.ForeignKey(Contractor, on_delete=models.CASCADE, related_name='performance_history')
    metric = models.ForeignKey(
        'ContractorPerformanceMetric', on_delete=models.CASCADE, related_name='history_entries'
    )
    overall_score = models.FloatField()
    rating = models.CharField(max_length=30)
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-calculated_at']
        verbose_name = 'Performance Score History'
        verbose_name_plural = 'Performance Score Histories'
    
    def __str__(self):
        return f"{self.contractor.contractor_name} - {self.overall_score}% ({self.rating})"


class ContractorDashboardSnapshot(models.Model):
    """Stores dashboard snapshots for trend analysis."""
    
    snapshot_date = models.DateField(auto_now_add=True)
    snapshot_type = models.CharField(
        max_length=20,
        choices=[('DAILY', 'Daily'), ('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly')],
        default='DAILY'
    )
    
    total_contractors = models.IntegerField(default=0)
    active_contractors = models.IntegerField(default=0)
    inactive_contractors = models.IntegerField(default=0)
    pending_approval = models.IntegerField(default=0)
    rejected_contractors = models.IntegerField(default=0)
    
    high_risk_contractors = models.IntegerField(default=0)
    critical_risk_contractors = models.IntegerField(default=0)
    medium_risk_contractors = models.IntegerField(default=0)
    low_risk_contractors = models.IntegerField(default=0)
    
    expired_documents = models.IntegerField(default=0)
    expiring_soon_documents = models.IntegerField(default=0)
    valid_documents = models.IntegerField(default=0)
    
    avg_performance_score = models.FloatField(default=0)
    excellent_count = models.IntegerField(default=0)
    good_count = models.IntegerField(default=0)
    needs_improvement_count = models.IntegerField(default=0)
    poor_count = models.IntegerField(default=0)
    
    contractors_requiring_attention = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-snapshot_date']
        verbose_name = 'Contractor Dashboard Snapshot'
        verbose_name_plural = 'Contractor Dashboard Snapshots'
    
    def __str__(self):
        return f"{self.snapshot_type} - {self.snapshot_date}"


# ==========================================================
# SECTION 8: REPORT MODEL
# ==========================================================

class ContractorReport(models.Model):
    """Stores generated contractor reports."""
    
    REPORT_TYPE_CHOICES = [
        ('CONTRACTOR_OVERVIEW', 'Contractor Overview'),
        ('PERFORMANCE_SUMMARY', 'Performance Summary'),
        ('DOCUMENT_COMPLIANCE', 'Document Compliance'),
        ('TRAINING_COMPLIANCE', 'Training Compliance'),
        ('INSPECTION_SUMMARY', 'Inspection Summary'),
        ('RISK_ASSESSMENT', 'Risk Assessment'),
        ('WORK_ORDER_SUMMARY', 'Work Order Summary'),
    ]
    
    FORMAT_CHOICES = [
        ('PDF', 'PDF'),
        ('EXCEL', 'Excel'),
        ('CSV', 'CSV'),
    ]
    
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES, default='CONTRACTOR_OVERVIEW')
    report_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='PDF')
    report_file = models.FileField(upload_to='reports/contractor/%Y/%m/%d/', null=True, blank=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    plant = models.ForeignKey(
        'organizations.Plant', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='contractor_reports'
    )
    contractor = models.ForeignKey(
        Contractor, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports'
    )
    generated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='generated_contractor_reports'
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-generated_at']
        verbose_name = 'Contractor Report'
        verbose_name_plural = 'Contractor Reports'
    
    def __str__(self):
        if self.contractor:
            return f"{self.get_report_type_display()} - {self.contractor.contractor_name}"
        return f"{self.get_report_type_display()} - {self.generated_at.strftime('%Y-%m-%d')}"
    
    def get_file_size(self):
        if self.report_file:
            try:
                size = self.report_file.size
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024:
                        return f"{size:.1f} {unit}"
                    size /= 1024
                return f"{size:.1f} TB"
            except Exception:
                return "N/A"
        return "N/A"
    
    def get_file_name(self):
        if self.report_file:
            try:
                return self.report_file.name.split('/')[-1]
            except Exception:
                return "N/A"
        return "N/A"