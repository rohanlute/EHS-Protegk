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