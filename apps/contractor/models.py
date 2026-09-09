import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

User = get_user_model()


class Contractor(models.Model):
    """Main Contractor model."""
    
    # Contractor Type Choices
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
    
    # Work Category Choices
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

    # ==========================================================
    # SECTION A – Basic Information
    # ==========================================================
    contractor_code = models.CharField(
        max_length=50, 
        unique=True, 
        blank=True,
        help_text="Auto-generated unique identifier (e.g., CM001)"
    )
    contractor_name = models.CharField(
        max_length=200,
        verbose_name="Contractor Company Name"
    )
    contractor_type = models.CharField(
        max_length=50, 
        choices=CONTRACTOR_TYPE_CHOICES, 
        default='OTHER',
        verbose_name="Contractor Company Type"
    )
    registration_number = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name="Registration Number"
    )
    pan_number = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="PAN Number",
        help_text="Permanent Account Number"
    )
    gstin = models.CharField(
        max_length=30, 
        blank=True,
        verbose_name="GSTIN",
        help_text="Goods and Services Tax Identification Number"
    )
    establishment_year = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="Establishment Year",
        validators=[MinValueValidator(1900), MaxValueValidator(2100)]
    )

    # ==========================================================
    # SECTION B – Contact Information
    # ==========================================================
    contact_person = models.CharField(
        max_length=100,
        verbose_name="Contact Person"
    )
    designation = models.CharField(
        max_length=100,
        verbose_name="Designation"
    )
    mobile = models.CharField(
        max_length=15,
        verbose_name="Mobile Number"
    )
    email = models.EmailField(
        verbose_name="Email Address"
    )
    alternate_mobile = models.CharField(
        max_length=15, 
        blank=True,
        verbose_name="Alternate Mobile"
    )
    address_line1 = models.TextField(
        verbose_name="Address Line 1"
    )
    address_line2 = models.TextField(
        blank=True,
        verbose_name="Address Line 2"
    )
    country = models.CharField(
        max_length=50,
        verbose_name="Country"
    )
    state = models.CharField(
        max_length=50,
        verbose_name="State"
    )
    city = models.CharField(
        max_length=50,
        verbose_name="City"
    )
    pincode = models.CharField(
        max_length=10,
        verbose_name="Pincode"
    )

    # ==========================================================
    # SECTION C – Business / Work Information
    # ==========================================================
    nature_of_business = models.CharField(
        max_length=200,
        verbose_name="Nature of Business"
    )
    work_category = models.CharField(
        max_length=50, 
        choices=WORK_CATEGORY_CHOICES, 
        default='OTHER',
        verbose_name="Work Category"
    )
    service_description = models.TextField(
        verbose_name="Service Description"
    )
    years_of_experience = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="Years of Experience",
        validators=[MinValueValidator(0)]
    )
    number_of_workers = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="Number of Workers",
        validators=[MinValueValidator(0)]
    )

    # ==========================================================
    # SECTION D – EHS / Responsible Person
    # ==========================================================
    ehs_officer_name = models.CharField(
        max_length=100,
        verbose_name="EHS/Safety Officer Name"
    )
    ehs_designation = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name="EHS Designation"
    )
    ehs_mobile = models.CharField(
        max_length=15,
        verbose_name="EHS Mobile Number"
    )
    ehs_email = models.EmailField(
        verbose_name="EHS Email Address"
    )

    # ==========================================================
    # Status
    # ==========================================================
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active"
    )

    # ==========================================================
    # Metadata
    # ==========================================================
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_contractors',
        verbose_name="Created By"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

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
    """
    Separate login account for external Contractor Portal users.

    This is completely independent from the internal EHS-360 User model.
    """

    USER_TYPE_CHOICES = [
        ('CONTACT_PERSON', 'Contact Person'),
        ('EHS_OFFICER', 'EHS Officer'),
    ]

    contractor = models.ForeignKey(
        Contractor,
        on_delete=models.CASCADE,
        related_name='portal_users'
    )

    name = models.CharField(
        max_length=150,
        verbose_name="Name"
    )

    email = models.EmailField(
        verbose_name="Email Address"
    )

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        verbose_name="User Type"
    )

    password = models.CharField(
        max_length=255,
        verbose_name="Password"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Active"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    last_login = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Contractor Portal User'
        verbose_name_plural = 'Contractor Portal Users'

    def __str__(self):
        return f"{self.name} - {self.email}"

    def set_password(self, raw_password):
        """
        Store a hashed password using Django's password hashing.
        """
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """
        Check the supplied password against the stored hash.
        """
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)


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


# apps/contractor/models.py

class OnboardingRequest(models.Model):
    """Onboarding request for contractor with pre-qualification and documents"""
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    ]
    
    # Link to Contractor (Main)
    contractor = models.ForeignKey(
        Contractor,
        on_delete=models.CASCADE,
        related_name='onboarding_requests'
    )
    
    # Responsible Person / EHS Officer (Link to User)
    ehs_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_onboarding',
        verbose_name="EHS Officer / Responsible Person"
    )
    
    # Pre-Qualification Questions with answers (JSON field)
    pre_qualification_answers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Stores question_id: answer pairs (true/false or text)"
    )
    
    # ==========================================================
    # ADD THIS FIELD - Question Remarks from EHS Officer
    # ==========================================================
    question_remarks = models.JSONField(
        default=dict,
        blank=True,
        help_text="Stores question_id: remark pairs from EHS officer"
    )
    
    # Documents selected for this onboarding (Many-to-Many via through model)
    documents = models.ManyToManyField(
        DocumentType,
        through='OnboardingDocumentRequirement',
        related_name='onboarding_requests'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )
    
    notes = models.TextField(blank=True)
    
    # Submission details
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submitted_onboarding'
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    # Approval details
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approved_onboarding',
        blank=True
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



class ContractorAssignment(models.Model):
    """
    Controls external Contractor Portal access for an onboarding assignment.
    """

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
    ]

    onboarding = models.ForeignKey(
        OnboardingRequest,
        on_delete=models.CASCADE,
        related_name='assignments'
    )

    portal_user = models.ForeignKey(
        ContractorPortalUser,
        on_delete=models.CASCADE,
        related_name='assignments'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )

    is_access_active = models.BooleanField(
        default=True,
        verbose_name="Access Active"
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )
    access_token = models.UUIDField(
        default=uuid.uuid4,
        null=True,
        blank=True,
        editable=False
    )

    class Meta:
        ordering = ['-assigned_at']
        verbose_name = 'Contractor Assignment'
        verbose_name_plural = 'Contractor Assignments'

    def __str__(self):
        return (
            f"{self.onboarding.contractor.contractor_name} - "
            f"{self.portal_user.email}"
        )

    def deactivate(self, status='COMPLETED'):
        """
        Deactivate portal access.
        """
        self.status = status
        self.is_access_active = False

        if status == 'COMPLETED':
            self.completed_at = timezone.now()

        self.save(
            update_fields=[
                'status',
                'is_access_active',
                'completed_at'
            ]
        )

    @property
    def can_access(self):
        """
        Check whether this assignment is currently accessible.
        """
        if not self.is_access_active:
            return False

        if self.status != 'ACTIVE':
            return False

        if self.expires_at and timezone.now() >= self.expires_at:
            self.status = 'EXPIRED'
            self.is_access_active = False
            self.save(
                update_fields=[
                    'status',
                    'is_access_active'
                ]
            )
            return False

        return True


class OnboardingDocumentRequirement(models.Model):
    """Individual document requirement for onboarding"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('UPLOADED', 'Uploaded'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
    ]
    
    # Link to OnboardingRequest
    onboarding = models.ForeignKey(
        OnboardingRequest,
        on_delete=models.CASCADE,
        related_name='document_requirements'
    )
    
    # Link to DocumentType
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.CASCADE
    )
    
    is_required = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    
    # Document upload
    document_file = models.FileField(
        upload_to='onboarding_documents/%Y/%m/%d/',
        null=True,
        blank=True
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_documents'
    )
    uploaded_at = models.DateTimeField(null=True, blank=True)
    
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents'
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


class ContractorPreQualification(models.Model):
    """
    Stores contractor pre-qualification assessment and risk classification.
    This is a separate assessment that can be done independently of onboarding.
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

    # Link to Contractor
    contractor = models.ForeignKey(
        "Contractor",
        on_delete=models.CASCADE,
        related_name="pre_qualifications"
    )

    assessment_date = models.DateField(auto_now_add=True)

    # Experience
    years_of_experience = models.PositiveIntegerField(
        default=0
    )

    similar_work_experience = models.TextField(
        blank=True,
        null=True,
        help_text="Details of similar work carried out by the contractor."
    )

    previous_clients = models.TextField(
        blank=True,
        null=True,
        help_text="Major previous clients/projects."
    )

    # EHS Performance
    previous_ehs_performance = models.TextField(
        blank=True,
        null=True
    )

    accident_history = models.PositiveIntegerField(
        default=0
    )

    fatality_history = models.PositiveIntegerField(
        default=0
    )

    lost_time_injuries = models.PositiveIntegerField(
        default=0
    )

    regulatory_violations = models.PositiveIntegerField(
        default=0
    )

    # Safety Capability
    safety_manpower = models.PositiveIntegerField(
        default=0,
        help_text="Number of dedicated safety personnel."
    )

    total_manpower = models.PositiveIntegerField(
        default=0
    )

    has_safety_policy = models.BooleanField(
        default=False
    )

    has_training_system = models.BooleanField(
        default=False
    )

    has_emergency_preparedness = models.BooleanField(
        default=False
    )

    # Technical / Operational Capability
    equipment_capability = models.TextField(
        blank=True,
        null=True
    )

    training_capability = models.TextField(
        blank=True,
        null=True
    )

    # Insurance
    has_insurance = models.BooleanField(
        default=False
    )

    # Risk Classification
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        default="MEDIUM"
    )

    risk_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for assigning the contractor risk level."
    )

    # Approval Workflow
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="DRAFT"
    )

    reviewer_comments = models.TextField(
        blank=True,
        null=True
    )

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_contractor_prequalifications"
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Contractor Pre-Qualification"
        verbose_name_plural = "Contractor Pre-Qualifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.contractor} - {self.get_risk_level_display()}"


class ContractorDocument(models.Model):
    """
    Stores important contractor documents and their verification/expiry status.
    This is for documents uploaded directly against a contractor.
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

    # Link to Contractor
    contractor = models.ForeignKey(
        Contractor,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES
    )

    document = models.FileField(
        upload_to="contractors/documents/"
    )

    remarks = models.TextField(
        blank=True,
        null=True
    )

    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_contractor_documents"
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Contractor Document"
        verbose_name_plural = "Contractor Documents"
        ordering = ["document_type"]

    def __str__(self):
        return f"{self.contractor} - {self.get_document_type_display()}"
# apps/contractor/models.py - Corrected WorkOrder model

class WorkOrder(models.Model):
    """
    Work Order / Contract for approved contractors.
    After a contractor is approved, work orders can be created.
    """
    
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
    
    # ==========================================================
    # Basic Information
    # ==========================================================
    work_order_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True
    )
    
    contract_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True
    )
    
    # Link to Contractor (Only ONE definition)
    contractor = models.ForeignKey(
        Contractor,
        on_delete=models.CASCADE,
        related_name='work_orders',
        limit_choices_to={'onboarding_requests__status': 'APPROVED'},
    )
    
    # Link to Onboarding Request
    onboarding = models.ForeignKey(
        OnboardingRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_orders'
    )
    
    # ==========================================================
    # Work Details
    # ==========================================================
    work_description = models.TextField(
        verbose_name="Work Description"
    )
    
    # Work Category - Auto-filled from Contractor
    work_category = models.CharField(
        max_length=50,
        verbose_name="Work Category"
    )
    
    # Site/Plant Information
    plant = models.ForeignKey(
        'organizations.Plant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_orders',
        verbose_name="Site / Plant"
    )
    
    department = models.ForeignKey(
        'organizations.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_orders',
        verbose_name="Department"
    )
    
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Work Location"
    )
    
    # ==========================================================
    # Personnel
    # ==========================================================
    
    # CONTRACTOR SUPERVISOR - Auto-filled from Contractor's EHS Officer Name
    contractor_supervisor = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Contractor Supervisor",
        help_text="Auto-filled from contractor's EHS Officer Name"
    )
    
    contractor_supervisor_contact = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="Supervisor Contact",
        help_text="Auto-filled from contractor's EHS Mobile"
    )
    
    contractor_supervisor_email = models.EmailField(
        blank=True,
        verbose_name="Supervisor Email",
        help_text="Auto-filled from contractor's EHS Email"
    )
        
    company_representative = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_orders_representative',
        verbose_name="Company Representative"
    )
        
    # ==========================================================
    # Worker Information - MANUAL INPUT
    # ==========================================================
    number_of_workers = models.PositiveIntegerField(
        default=0,
        verbose_name="Number of Workers"
    )
    
    worker_details = models.TextField(
        blank=True,
        verbose_name="Worker Details"
    )
    
    # ==========================================================
    # Work Dates
    # ==========================================================
    start_date = models.DateField(
        verbose_name="Start Date"
    )
    end_date = models.DateField(
        verbose_name="End Date"
    )
    
    # ==========================================================
    # Risk Level - Dropdown
    # ==========================================================
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        default='MEDIUM',
        verbose_name="Risk Level"
    )
    
    # ==========================================================
    # Attachments
    # ==========================================================
    attachment = models.FileField(
        upload_to='work_orders/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Work Order Attachment"
    )
    attachment_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Attachment Name"
    )
    
    # ==========================================================
    # Status and Approval
    # ==========================================================
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SUBMITTED'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_work_orders'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Approval fields
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_work_orders'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Closure fields
    closed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_work_orders'
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closure_remarks = models.TextField(blank=True)
    
    # ==========================================================
    # Additional Info
    # ==========================================================
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Work Order'
        verbose_name_plural = 'Work Orders'
    
    def __str__(self):
        return f"{self.work_order_number} - {self.contractor.contractor_name}"
    
    def save(self, *args, **kwargs):
        # ==========================================================
        # AUTO-GENERATE WORK ORDER NUMBER: WO-YYYY-XXXX
        # ==========================================================
        if not self.work_order_number:
            year = timezone.now().year
            last_wo = WorkOrder.objects.filter(
                work_order_number__startswith=f'WO-{year}-'
            ).order_by('-work_order_number').first()
            
            if last_wo and last_wo.work_order_number:
                try:
                    last_number = int(last_wo.work_order_number.split('-')[-1])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            
            self.work_order_number = f'WO-{year}-{str(new_number).zfill(4)}'
        
        # ==========================================================
        # AUTO-GENERATE CONTRACT NUMBER: CN-YY-XXX
        # ==========================================================
        if not self.contract_number:
            current_year = timezone.now().year
            year_short = str(current_year)[-2:]
            
            last_contract = WorkOrder.objects.filter(
                contract_number__startswith=f'CN-{year_short}-'
            ).order_by('-contract_number').first()
            
            if last_contract and last_contract.contract_number:
                try:
                    last_number = int(last_contract.contract_number.split('-')[-1])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            
            self.contract_number = f'CN-{year_short}-{str(new_number).zfill(3)}'
        
        # ==========================================================
        # AUTO-FILL FROM CONTRACTOR
        # ==========================================================
        if self.contractor:
            # 1. Auto-fill Work Category
            if not self.work_category:
                self.work_category = self.contractor.work_category
            
            # 2. Auto-fill Contractor Supervisor (EHS Officer Name)
            if not self.contractor_supervisor:
                self.contractor_supervisor = self.contractor.ehs_officer_name or ''
            
            # 3. Auto-fill Supervisor Contact (EHS Mobile)
            if not self.contractor_supervisor_contact:
                self.contractor_supervisor_contact = self.contractor.ehs_mobile or ''
            
            # 4. Auto-fill Supervisor Email (EHS Email)
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
# apps/contractor/models.py - TrainingSignOff model (without remarks and doc description)

# ==========================================================
# TRAINING SIGN-OFF MODEL
# ==========================================================

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.contractor.models import Contractor, WorkOrder
from apps.toolbox_talk.models import ToolboxTalkSessionPlan

User = get_user_model()


class TrainingSignOff(models.Model):
    """
    Post-training confirmation / sign-off record.
    """

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('COMPLETED', 'Completed'),
    ]

    signoff_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        editable=False,
        verbose_name="Sign-Off Number"
    )

    # ==========================================================
    # SECTION 1 - Contractor / Work Order / Training Session
    # ==========================================================
    contractor = models.ForeignKey(
        Contractor,
        on_delete=models.PROTECT,
        related_name='training_signoffs',
        verbose_name="Contractor"
    )

    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.PROTECT,
        related_name='training_signoffs',
        verbose_name="Work Order",
        limit_choices_to={'status': 'APPROVED'},
        help_text="Only Approved work orders are eligible for training sign-off"
    )

    session = models.ForeignKey(
        ToolboxTalkSessionPlan,
        on_delete=models.PROTECT,
        related_name='contractor_signoffs',
        verbose_name="Training Session"
    )

    # ---- Snapshot fields ----
    contractor_representative = models.CharField(
        max_length=150,
        verbose_name="Contractor Representative",
        help_text="Auto-filled from the Work Order's Contractor Supervisor"
    )
    contractor_representative_designation = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Designation (EHS Officer)",
        help_text="Auto-filled from the Contractor's EHS Designation"
    )
    number_of_workers = models.PositiveIntegerField(
        default=0,
        verbose_name="Number of Workers",
        help_text="Auto-filled from the Work Order"
    )

    # ==========================================================
    # SECTION 2 - Company Sign-Off
    # ==========================================================
    company_declaration = models.BooleanField(
        default=False,
        verbose_name="Company Declaration",
        help_text=(
            "I confirm that the above listed contractor and its workers have "
            "received the required safety training and have been made aware "
            "of the applicable EHS requirements."
        )
    )
    company_representative = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='training_signoffs_as_company_rep',
        verbose_name="Company Representative",
        help_text="Auto-filled from the Work Order's Company Representative"
    )
    company_representative_designation = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Designation",
        help_text="Auto-filled from system (e.g. Safety Manager role)"
    )
    company_signature = models.FileField(
        upload_to='training_signoff/signatures/company/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Company Representative Signature"
    )

    # ==========================================================
    # SECTION 3 - Contractor Sign-Off
    # ==========================================================
    contractor_declaration = models.BooleanField(
        default=False,
        verbose_name="Contractor Declaration",
        help_text=(
            "I confirm that the above listed workers have received the "
            "required safety training and have understood the applicable "
            "EHS requirements."
        )
    )
    contractor_supervisor = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Contractor Supervisor",
        help_text="Auto-filled from the Work Order's Contractor Supervisor"
    )
    contractor_supervisor_designation = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Designation",
        help_text="Auto-filled from the Contractor's EHS Designation"
    )

    # ==========================================================
    # SECTION 4 - Supporting Documents
    # ==========================================================
    supporting_documents = models.FileField(
        upload_to='training_signoff/documents/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Supporting Documents",
        help_text="Upload any supporting documents related to the training (e.g., attendance sheet, training material, etc.)"
    )

    # ==========================================================
    # Meta info
    # ==========================================================
    signoff_date = models.DateField(default=timezone.now, verbose_name="Date")
    signoff_time = models.TimeField(default=timezone.now, verbose_name="Time")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_training_signoffs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Training Sign-Off'
        verbose_name_plural = 'Training Sign-Offs'

    def __str__(self):
        return f"{self.signoff_number} - {self.contractor.contractor_name}"

    def save(self, *args, **kwargs):
        # AUTO-GENERATE SIGN-OFF NUMBER: TSO-YYYY-XXXX
        if not self.signoff_number:
            year = timezone.now().year
            last = TrainingSignOff.objects.filter(
                signoff_number__startswith=f'TSO-{year}-'
            ).order_by('-signoff_number').first()

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
        return bool(
            self.company_declaration and self.company_signature and
            self.contractor_declaration
        )
    
    @property
    def has_documents(self):
        """Check if supporting documents are uploaded."""
        return bool(self.supporting_documents)