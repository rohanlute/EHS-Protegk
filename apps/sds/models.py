from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from apps.chemicals.models import Chemical

def generate_sds_number():
        year = timezone.now().year
        prefix = f'SDS-{year}-BIT'
        last_sds = SDS.objects.filter(
            sds_number__startswith=prefix
        ).order_by('-id').first()
        if last_sds and last_sds.sds_number:
            try:
                last_number = int(last_sds.sds_number.replace(prefix, ''))
            except ValueError:
                last_number = 0
        else:
            last_number = 0
        return f'{prefix}{last_number + 1:02d}'

class SDS(models.Model):
    """
    Main Safety Data Sheet master/register.

    One SDS represents the controlled SDS record for a chemical/product.
    Revision history is maintained separately through SDSVersion.
    """

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('ACTIVE', 'Active'),
        ('REJECTED', 'Rejected'),
        ('SUPERSEDED', 'Superseded'),
        ('EXPIRED', 'Expired'),
    ]

    SDS_TYPE_CHOICES = [
        ('MANUFACTURER', 'Manufacturer SDS'),
        ('SUPPLIER', 'Supplier SDS'),
        ('INTERNAL', 'Internal SDS'),
    ]

    # ==========================================================
    # SDS IDENTIFICATION
    # ==========================================================
    chemical = models.ForeignKey(
        Chemical,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sds_records',
        verbose_name='Chemical'
    )
    sds_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='SDS Number',
        help_text='Unique identifier for this SDS record.'
    )

    product_name = models.CharField(
        max_length=255,
        verbose_name='Product / Chemical Name'
    )

    product_identifier = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Product Identifier',
        help_text='Product code, catalogue number, CAS-related identifier, etc.'
    )

    sds_type = models.CharField(
        max_length=20,
        choices=SDS_TYPE_CHOICES,
        default='MANUFACTURER',
        verbose_name='SDS Type'
    )

    # ==========================================================
    # MANUFACTURER / SUPPLIER
    # ==========================================================

    manufacturer_name = models.CharField(
        max_length=255,
        verbose_name='Manufacturer Name'
    )

    manufacturer_address = models.TextField(
        blank=True,
        verbose_name='Manufacturer Address'
    )

    manufacturer_phone = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Manufacturer Phone'
    )

    manufacturer_email = models.EmailField(
        blank=True,
        verbose_name='Manufacturer Email'
    )

    supplier_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Supplier Name'
    )

    supplier_address = models.TextField(
        blank=True,
        verbose_name='Supplier Address'
    )

    supplier_phone = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Supplier Phone'
    )

    supplier_email = models.EmailField(
        blank=True,
        verbose_name='Supplier Email'
    )

    # ==========================================================
    # ORGANIZATION / LOCATION
    # ==========================================================

    plant = models.ForeignKey(
        'organizations.Plant',
        on_delete=models.PROTECT,
        related_name='sds_records',
        null=True,
        blank=True,
        verbose_name='Plant'
    )

    zone = models.ForeignKey(
        'organizations.Zone',
        on_delete=models.PROTECT,
        related_name='sds_records',
        null=True,
        blank=True,
        verbose_name='Zone'
    )

    location = models.ForeignKey(
        'organizations.Location',
        on_delete=models.PROTECT,
        related_name='sds_records',
        null=True,
        blank=True,
        verbose_name='Location'
    )

    sublocation = models.ForeignKey(
        'organizations.SubLocation',
        on_delete=models.PROTECT,
        related_name='sds_records',
        null=True,
        blank=True,
        verbose_name='Sub-Location'
    )

    # ==========================================================
    # DOCUMENT INFORMATION
    # ==========================================================

    document = models.FileField(
        upload_to='sds/documents/%Y/%m/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf']
            )
        ],
        null=True,
        blank=True,
        verbose_name='SDS Document',
        help_text='Upload the official SDS document in PDF format.'
    )

    document_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Document Name'
    )

    document_language = models.CharField(
        max_length=50,
        default='English',
        verbose_name='Document Language'
    )

    # ==========================================================
    # REVISION / DATE INFORMATION
    # ==========================================================

    issue_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Issue Date'
    )

    revision_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Revision Date'
    )

    next_review_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Next Review Date'
    )

    # ==========================================================
    # STATUS / CONTROL
    # ==========================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        db_index=True
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Active'
    )

    remarks = models.TextField(
        blank=True,
        verbose_name='Remarks'
    )

    # ==========================================================
    # AUDIT INFORMATION
    # ==========================================================

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_sds_records',
        verbose_name='Created By'
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_sds_records',
        verbose_name='Updated By'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['product_name']
        verbose_name = 'Safety Data Sheet'
        verbose_name_plural = 'Safety Data Sheets'
        constraints = [
            models.UniqueConstraint(fields=['chemical'],condition=models.Q(
                    status='ACTIVE',is_active=True),name='unique_active_sds_per_chemical')
        ]

    def __str__(self):
        return f'{self.sds_number} - {self.product_name}'

    @property
    def is_expired(self):
        """Return True when the SDS review date has passed."""
        if self.next_review_date:
            return self.next_review_date < timezone.now().date()
        return False

    @property
    def days_until_review(self):
        """Return number of days until the next SDS review."""
        if not self.next_review_date:
            return None

        return (self.next_review_date - timezone.now().date()).days

    @property
    def current_version(self):
        """Return the current active version of this SDS."""
        return self.versions.filter(status='ACTIVE').order_by('-version_number').first()

    def clean(self):
        errors = {}

        if self.status == 'ACTIVE':
            if not self.pk:
                errors['status'] = ('An SDS cannot be activated before it has an active version.')
            elif not self.current_version:
                errors['status'] = ('An SDS cannot be ACTIVE without an active SDS version.')

            if not self.chemical:
                errors['chemical'] = ('An active SDS must be linked to a Chemical.')

        if self.is_active and self.status == 'ACTIVE' and self.chemical:
            existing_active = SDS.objects.filter(chemical=self.chemical,status='ACTIVE',
                is_active=True).exclude(pk=self.pk)

            if existing_active.exists():
                errors['chemical'] = ('This Chemical already has an active SDS.')

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.sds_number:
            self.sds_number = generate_sds_number()
        super().save(*args, **kwargs)



class SDSVersion(models.Model):
    """
    Revision history for an SDS.

    Previous versions are retained rather than overwritten.
    """

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('ACTIVE', 'Active'),
        ('SUPERSEDED', 'Superseded'),
        ('REJECTED', 'Rejected'),
    ]

    sds = models.ForeignKey(
        SDS,
        on_delete=models.CASCADE,
        related_name='versions'
    )

    version_number = models.PositiveIntegerField(
        verbose_name='Version Number'
    )

    revision_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Revision Number'
    )

    version_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Version Title'
    )

    document = models.FileField(
        upload_to='sds/versions/%Y/%m/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf']
            )
        ],
        verbose_name='Version Document'
    )

    issue_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Issue Date'
    )

    revision_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Revision Date'
    )

    effective_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Effective Date'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        db_index=True
    )

    change_summary = models.TextField(
        blank=True,
        verbose_name='Change Summary',
        help_text='Describe what changed from the previous version.'
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_sds_versions'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # =========================================================
    # SDS SECTION COMPLETION
    # =========================================================
    @property
    def section_completion_count(self):
        section_models = [
            SDSSection1,
            SDSSection2,
            SDSSection3,
            SDSSection4,
            SDSSection5,
            SDSSection6,
            SDSSection7,
            SDSSection8,
            SDSSection9,
            SDSSection10,
            SDSSection11,
            SDSSection12,
            SDSSection13,
            SDSSection14,
            SDSSection15,
            SDSSection16,
        ]

        completed_count = 0

        for section_model in section_models:
            if section_model.objects.filter(
                sds_version=self
            ).exists():
                completed_count += 1

        return completed_count

    @property
    def section_total_count(self):
        return 16

    @property
    def section_completion_percentage(self):
        return int(
            (
                self.section_completion_count
                / self.section_total_count
            ) * 100
        )

    @property
    def is_section_complete(self):
        return self.section_completion_count == 16

    # =========================================================
    # SDS REVIEW DUE MANAGEMENT
    # =========================================================
    @property
    def review_period_months(self):
        return 12

    @property
    def next_review_date(self):
        if not self.effective_date:
            return None

        return self.effective_date + relativedelta(
            months=self.review_period_months
        )

    @property
    def days_until_review(self):
        if not self.next_review_date:
            return None

        return (
            self.next_review_date - timezone.localdate()
        ).days

    @property
    def review_due_status(self):
        days = self.days_until_review

        if days is None:
            return 'NO_DATE'

        if days < 0:
            return 'OVERDUE'

        if days <= 30:
            return 'DUE_SOON'

        return 'NOT_DUE'

    @property
    def is_review_overdue(self):
        return self.review_due_status == 'OVERDUE'

    @property
    def is_review_due_soon(self):
        return self.review_due_status == 'DUE_SOON'

    class Meta:
        ordering = ['-version_number']
        verbose_name = 'SDS Version'
        verbose_name_plural = 'SDS Versions'
        constraints = [
            models.UniqueConstraint(
                fields=['sds', 'version_number'],
                name='unique_sds_version'
            )
        ]

    def __str__(self):
        return f'{self.sds.sds_number} - Version {self.version_number}'

    def clean(self):
        """
        Prevent multiple active versions for the same SDS.
        """
        if self.status == 'ACTIVE':
            existing_active = SDSVersion.objects.filter(
                sds=self.sds,
                status='ACTIVE'
            ).exclude(pk=self.pk)

            if existing_active.exists():
                raise ValidationError(
                    'Only one active version is allowed for an SDS.'
                )


class SDSReview(models.Model):
    """
    Review and approval record for an SDS.
    """

    REVIEW_TYPE_CHOICES = [
        ('INITIAL', 'Initial Review'),
        ('PERIODIC', 'Periodic Review'),
        ('REVISION', 'Revision Review'),
        ('EMERGENCY', 'Emergency Review'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_REVIEW', 'In Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    sds = models.ForeignKey(
        SDS,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    version = models.ForeignKey(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True
    )

    review_type = models.CharField(
        max_length=20,
        choices=REVIEW_TYPE_CHOICES,
        default='INITIAL'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sds_reviews'
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_sds_reviews'
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    review_remarks = models.TextField(
        blank=True
    )

    rejection_reason = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'SDS Review'
        verbose_name_plural = 'SDS Reviews'

    def __str__(self):
        return f'{self.sds.sds_number} - {self.get_review_type_display()}'


# =========================================================
# SDS AUDIT LOG
# =========================================================
class SDSAuditLog(models.Model):
    """
    Immutable audit trail for SDS and SDS version activities.
    """

    ACTION_CHOICES = [
        ('SDS_CREATED', 'SDS Created'),
        ('SDS_UPDATED', 'SDS Updated'),
        ('VERSION_CREATED', 'Version Created'),
        ('VERSION_STATUS_CHANGED', 'Version Status Changed'),
        ('VERSION_ACTIVATED', 'Version Activated'),
        ('VERSION_SUPERSEDED', 'Version Superseded'),
        ('VERSION_RETURNED_TO_DRAFT', 'Version Returned to Draft'),
        ('SECTION_UPDATED', 'Section Updated'),
        ('REVIEW_CREATED', 'Review Created'),
        ('REVIEW_UPDATED', 'Review Updated'),
        ('REVIEW_APPROVED', 'Review Approved'),
        ('REVIEW_REJECTED', 'Review Rejected'),
    ]

    sds = models.ForeignKey(
        SDS,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )

    version = models.ForeignKey(
        SDSVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )

    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        db_index=True
    )

    description = models.TextField(
        blank=True
    )

    old_status = models.CharField(
        max_length=20,
        blank=True
    )

    new_status = models.CharField(
        max_length=20,
        blank=True
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sds_audit_actions'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'SDS Audit Log'
        verbose_name_plural = 'SDS Audit Logs'

    def __str__(self):
        return (
            f'{self.sds.sds_number} - '
            f'{self.get_action_display()} - '
            f'{self.created_at:%d %b %Y %H:%M}'
        )
    


# =============================================
# SDS Section 1 - Identification
# =============================================
class SDSSection1(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_1',
        verbose_name='SDS Version'
    )
    product_identifier = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Product Identifier'
    )
    recommended_use = models.TextField(
        blank=True,
        verbose_name='Recommended Use'
    )
    restrictions_on_use = models.TextField(
        blank=True,
        verbose_name='Restrictions on Use'
    )
    manufacturer_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Manufacturer Name'
    )
    manufacturer_address = models.TextField(
        blank=True,
        verbose_name='Manufacturer Address'
    )
    manufacturer_phone = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Manufacturer Phone'
    )
    manufacturer_email = models.EmailField(
        blank=True,
        verbose_name='Manufacturer Email'
    )
    manufacturer_website = models.URLField(
        blank=True,
        verbose_name='Manufacturer Website'
    )
    emergency_contact_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Emergency Contact Name'
    )
    emergency_contact_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Emergency Contact Number'
    )
    emergency_contact_email = models.EmailField(
        blank=True,
        verbose_name='Emergency Contact Email'
    )
    emergency_contact_available = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Emergency Contact Availability'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 1 - Identification'
        verbose_name_plural = 'SDS Section 1 - Identification'
        ordering = ['sds_version']

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 1'




# =============================================
# SDS Section 2 - Hazard(s) Identification
# =============================================
class SDSSection2(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_2',
        verbose_name='SDS Version'
    )
    hazard_classification = models.TextField(
        blank=True,
        verbose_name='Hazard Classification'
    )
    signal_word = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Signal Word'
    )
    hazard_statements = models.TextField(
        blank=True,
        verbose_name='Hazard Statements'
    )
    precautionary_statements = models.TextField(
        blank=True,
        verbose_name='Precautionary Statements'
    )
    ghs_pictograms = models.TextField(
        blank=True,
        verbose_name='GHS Pictograms'
    )
    other_hazards = models.TextField(
        blank=True,
        verbose_name='Other Hazards'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'SDS Section 2 - Hazard Identification'
        verbose_name_plural = 'SDS Section 2 - Hazard Identification'
        ordering = ['sds_version']

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 2'



# =============================================
# SDS Section 3 - Composition / Information on Ingredients
# =============================================
class SDSSection3(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_3',
        verbose_name='SDS Version'
    )
    composition_notes = models.TextField(
        blank=True,
        verbose_name='Composition Notes'
    )
    trade_secret_information = models.TextField(
        blank=True,
        verbose_name='Trade Secret Information'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'SDS Section 3 - Composition'
        verbose_name_plural = 'SDS Section 3 - Composition'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 3'


# =============================================
# SDS Section 3 - Ingredient / Component
# =============================================
class SDSSection3Ingredient(models.Model):
    sds_section = models.ForeignKey(
        SDSSection3,
        on_delete=models.CASCADE,
        related_name='ingredients',
        verbose_name='SDS Section 3'
    )
    ingredient_name = models.CharField(
        max_length=255,
        verbose_name='Ingredient / Component Name'
    )
    cas_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='CAS Number'
    )
    ec_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='EC Number'
    )
    concentration = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Concentration'
    )
    concentration_range = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Concentration Range'
    )
    hazard_classification = models.TextField(
        blank=True,
        verbose_name='Hazard Classification'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    display_order = models.PositiveIntegerField(
        default=1,
        verbose_name='Display Order'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'SDS Section 3 Ingredient'
        verbose_name_plural = 'SDS Section 3 Ingredients'
        ordering = ['display_order', 'id']

    def __str__(self):
        return (
            f'{self.ingredient_name} - '
            f'{self.sds_section.sds_version.sds.sds_number}'
        )



# =============================================
# SDS Section 4 - First-Aid Measures
# =============================================
class SDSSection4(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_4',
        verbose_name='SDS Version'
    )
    general_first_aid = models.TextField(
        blank=True,
        verbose_name='General First-Aid Information'
    )
    inhalation = models.TextField(
        blank=True,
        verbose_name='Inhalation'
    )
    skin_contact = models.TextField(
        blank=True,
        verbose_name='Skin Contact'
    )
    eye_contact = models.TextField(
        blank=True,
        verbose_name='Eye Contact'
    )
    ingestion = models.TextField(
        blank=True,
        verbose_name='Ingestion'
    )
    most_important_symptoms = models.TextField(
        blank=True,
        verbose_name='Most Important Symptoms and Effects'
    )
    medical_attention = models.TextField(
        blank=True,
        verbose_name='Indication of Immediate Medical Attention and Special Treatment'
    )
    first_responder_notes = models.TextField(
        blank=True,
        verbose_name='Special Notes for First Responders'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 4'
        verbose_name_plural = 'SDS Section 4'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 4'



# =============================================
# SDS Section 5 - Fire-Fighting Measures
# =============================================
class SDSSection5(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_5',
        verbose_name='SDS Version'
    )
    suitable_extinguishing_media = models.TextField(
        blank=True,
        verbose_name='Suitable Extinguishing Media'
    )
    unsuitable_extinguishing_media = models.TextField(
        blank=True,
        verbose_name='Unsuitable Extinguishing Media'
    )
    specific_hazards = models.TextField(
        blank=True,
        verbose_name='Specific Hazards Arising from the Chemical'
    )
    hazardous_combustion_products = models.TextField(
        blank=True,
        verbose_name='Hazardous Combustion Products'
    )
    special_protective_equipment = models.TextField(
        blank=True,
        verbose_name='Special Protective Equipment for Firefighters'
    )
    special_fire_fighting_procedures = models.TextField(
        blank=True,
        verbose_name='Special Fire-Fighting Procedures'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 5'
        verbose_name_plural = 'SDS Section 5'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 5'


# =============================================
# SDS Section 6 - Accidental Release Measures
# =============================================
class SDSSection6(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_6',
        verbose_name='SDS Version'
    )
    personal_precautions = models.TextField(
        blank=True,
        verbose_name='Personal Precautions'
    )
    emergency_procedures = models.TextField(
        blank=True,
        verbose_name='Emergency Procedures'
    )
    environmental_precautions = models.TextField(
        blank=True,
        verbose_name='Environmental Precautions'
    )
    containment_methods = models.TextField(
        blank=True,
        verbose_name='Methods and Materials for Containment'
    )
    cleanup_methods = models.TextField(
        blank=True,
        verbose_name='Methods and Materials for Cleanup'
    )
    other_section_references = models.TextField(
        blank=True,
        verbose_name='Reference to Other SDS Sections'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 6'
        verbose_name_plural = 'SDS Section 6'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 6'



# =============================================
# SDS Section 7 - Handling and Storage
# =============================================
class SDSSection7(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_7',
        verbose_name='SDS Version'
    )
    precautions_for_safe_handling = models.TextField(
        blank=True,
        verbose_name='Precautions for Safe Handling'
    )
    conditions_for_safe_storage = models.TextField(
        blank=True,
        verbose_name='Conditions for Safe Storage'
    )
    incompatible_materials = models.TextField(
        blank=True,
        verbose_name='Incompatible Materials'
    )
    storage_temperature = models.TextField(
        blank=True,
        verbose_name='Storage Temperature'
    )
    ventilation_requirements = models.TextField(
        blank=True,
        verbose_name='Ventilation Requirements'
    )
    specific_end_use = models.TextField(
        blank=True,
        verbose_name='Specific End Use'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 7'
        verbose_name_plural = 'SDS Section 7'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 7'


# =============================================
# SDS Section 8 - Exposure Controls / Personal Protection
# =============================================
class SDSSection8(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_8',
        verbose_name='SDS Version'
    )
    occupational_exposure_limits = models.TextField(
        blank=True,
        verbose_name='Occupational Exposure Limits'
    )
    biological_exposure_limits = models.TextField(
        blank=True,
        verbose_name='Biological Exposure Limits'
    )
    appropriate_engineering_controls = models.TextField(
        blank=True,
        verbose_name='Appropriate Engineering Controls'
    )
    ventilation_requirements = models.TextField(
        blank=True,
        verbose_name='Ventilation Requirements'
    )
    respiratory_protection = models.TextField(
        blank=True,
        verbose_name='Respiratory Protection'
    )
    hand_protection = models.TextField(
        blank=True,
        verbose_name='Hand Protection'
    )
    eye_face_protection = models.TextField(
        blank=True,
        verbose_name='Eye / Face Protection'
    )
    skin_body_protection = models.TextField(
        blank=True,
        verbose_name='Skin / Body Protection'
    )
    thermal_hazards_protection = models.TextField(
        blank=True,
        verbose_name='Thermal Hazards Protection'
    )
    hygiene_measures = models.TextField(
        blank=True,
        verbose_name='Hygiene Measures'
    )
    environmental_exposure_controls = models.TextField(
        blank=True,
        verbose_name='Environmental Exposure Controls'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 8'
        verbose_name_plural = 'SDS Section 8'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 8'



# =============================================
# SDS Section 9 - Physical and Chemical Properties
# =============================================
class SDSSection9(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_9',
        verbose_name='SDS Version'
    )
    physical_state = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Physical State'
    )
    appearance = models.TextField(
        blank=True,
        verbose_name='Appearance'
    )
    color = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Color'
    )
    odor = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Odor'
    )
    odor_threshold = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Odor Threshold'
    )
    ph = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='pH'
    )
    melting_freezing_point = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Melting / Freezing Point'
    )
    boiling_point = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Initial Boiling Point / Boiling Range'
    )
    flash_point = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Flash Point'
    )
    evaporation_rate = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Evaporation Rate'
    )
    flammability = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Flammability'
    )
    explosive_limits = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Upper / Lower Explosive or Flammability Limits'
    )
    vapor_pressure = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Vapor Pressure'
    )
    vapor_density = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Vapor Density'
    )
    relative_density = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Relative Density'
    )
    solubility = models.TextField(
        blank=True,
        verbose_name='Solubility'
    )
    partition_coefficient = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Partition Coefficient'
    )
    auto_ignition_temperature = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Auto-Ignition Temperature'
    )
    decomposition_temperature = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Decomposition Temperature'
    )
    viscosity = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Viscosity'
    )
    particle_characteristics = models.TextField(
        blank=True,
        verbose_name='Particle Characteristics'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 9'
        verbose_name_plural = 'SDS Section 9'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 9'




# =============================================
# SDS Section 10 - Stability and Reactivity
# =============================================
class SDSSection10(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_10',
        verbose_name='SDS Version'
    )
    reactivity = models.TextField(
        blank=True,
        verbose_name='Reactivity'
    )
    chemical_stability = models.TextField(
        blank=True,
        verbose_name='Chemical Stability'
    )
    possibility_of_hazardous_reactions = models.TextField(
        blank=True,
        verbose_name='Possibility of Hazardous Reactions'
    )
    conditions_to_avoid = models.TextField(
        blank=True,
        verbose_name='Conditions to Avoid'
    )
    incompatible_materials = models.TextField(
        blank=True,
        verbose_name='Incompatible Materials'
    )
    hazardous_decomposition_products = models.TextField(
        blank=True,
        verbose_name='Hazardous Decomposition Products'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 10'
        verbose_name_plural = 'SDS Section 10'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 10'




# =============================================
# SDS Section 11 - Toxicological Information
# =============================================
class SDSSection11(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_11',
        verbose_name='SDS Version'
    )
    likely_routes_of_exposure = models.TextField(
        blank=True,
        verbose_name='Likely Routes of Exposure'
    )
    acute_toxicity = models.TextField(
        blank=True,
        verbose_name='Acute Toxicity'
    )
    skin_corrosion_irritation = models.TextField(
        blank=True,
        verbose_name='Skin Corrosion / Irritation'
    )
    serious_eye_damage_irritation = models.TextField(
        blank=True,
        verbose_name='Serious Eye Damage / Eye Irritation'
    )
    respiratory_skin_sensitization = models.TextField(
        blank=True,
        verbose_name='Respiratory or Skin Sensitization'
    )
    germ_cell_mutagenicity = models.TextField(
        blank=True,
        verbose_name='Germ Cell Mutagenicity'
    )
    carcinogenicity = models.TextField(
        blank=True,
        verbose_name='Carcinogenicity'
    )
    reproductive_toxicity = models.TextField(
        blank=True,
        verbose_name='Reproductive Toxicity'
    )
    stot_single_exposure = models.TextField(
        blank=True,
        verbose_name='Specific Target Organ Toxicity - Single Exposure'
    )
    stot_repeated_exposure = models.TextField(
        blank=True,
        verbose_name='Specific Target Organ Toxicity - Repeated Exposure'
    )
    aspiration_hazard = models.TextField(
        blank=True,
        verbose_name='Aspiration Hazard'
    )
    symptoms_related_to_exposure = models.TextField(
        blank=True,
        verbose_name='Symptoms Related to Physical, Chemical and Toxicological Characteristics'
    )
    delayed_immediate_effects = models.TextField(
        blank=True,
        verbose_name='Delayed and Immediate Effects'
    )
    interactive_effects = models.TextField(
        blank=True,
        verbose_name='Interactive Effects'
    )
    numerical_measures_of_toxicity = models.TextField(
        blank=True,
        verbose_name='Numerical Measures of Toxicity'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 11'
        verbose_name_plural = 'SDS Section 11'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 11'



# =============================================
# SDS Section 12 - Ecological Information
# =============================================
class SDSSection12(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_12',
        verbose_name='SDS Version'
    )
    aquatic_toxicity = models.TextField(
        blank=True,
        verbose_name='Aquatic Toxicity'
    )
    acute_aquatic_toxicity = models.TextField(
        blank=True,
        verbose_name='Acute Aquatic Toxicity'
    )
    chronic_aquatic_toxicity = models.TextField(
        blank=True,
        verbose_name='Chronic Aquatic Toxicity'
    )
    persistence_degradability = models.TextField(
        blank=True,
        verbose_name='Persistence and Degradability'
    )
    bioaccumulative_potential = models.TextField(
        blank=True,
        verbose_name='Bioaccumulative Potential'
    )
    mobility_in_soil = models.TextField(
        blank=True,
        verbose_name='Mobility in Soil'
    )
    results_of_pbt_vpvb_assessment = models.TextField(
        blank=True,
        verbose_name='Results of PBT and vPvB Assessment'
    )
    endocrine_disrupting_properties = models.TextField(
        blank=True,
        verbose_name='Endocrine Disrupting Properties'
    )
    other_adverse_effects = models.TextField(
        blank=True,
        verbose_name='Other Adverse Effects'
    )
    environmental_precautions = models.TextField(
        blank=True,
        verbose_name='Environmental Precautions'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 12'
        verbose_name_plural = 'SDS Section 12'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 12'




# =============================================
# SDS Section 13 - Disposal Considerations
# =============================================
class SDSSection13(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_13',
        verbose_name='SDS Version'
    )
    waste_treatment_methods = models.TextField(
        blank=True,
        verbose_name='Waste Treatment Methods'
    )
    product_disposal = models.TextField(
        blank=True,
        verbose_name='Product Disposal'
    )
    contaminated_packaging_disposal = models.TextField(
        blank=True,
        verbose_name='Contaminated Packaging Disposal'
    )
    disposal_precautions = models.TextField(
        blank=True,
        verbose_name='Disposal Precautions'
    )
    waste_classification = models.TextField(
        blank=True,
        verbose_name='Waste Classification'
    )
    relevant_waste_regulations = models.TextField(
        blank=True,
        verbose_name='Relevant Waste Regulations'
    )
    sewer_drain_disposal_restrictions = models.TextField(
        blank=True,
        verbose_name='Sewer / Drain Disposal Restrictions'
    )
    environmental_disposal_considerations = models.TextField(
        blank=True,
        verbose_name='Environmental Disposal Considerations'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 13'
        verbose_name_plural = 'SDS Section 13'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 13'



# =============================================
# SDS Section 14 - Transport Information
# =============================================
class SDSSection14(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_14',
        verbose_name='SDS Version'
    )
    un_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='UN Number'
    )
    un_proper_shipping_name = models.TextField(
        blank=True,
        verbose_name='UN Proper Shipping Name'
    )
    transport_hazard_class = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Transport Hazard Class'
    )
    packing_group = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Packing Group'
    )
    environmental_hazards = models.TextField(
        blank=True,
        verbose_name='Environmental Hazards'
    )
    special_precautions = models.TextField(
        blank=True,
        verbose_name='Special Precautions for User'
    )
    transport_in_bulk = models.TextField(
        blank=True,
        verbose_name='Transport in Bulk'
    )
    maritime_transport_information = models.TextField(
        blank=True,
        verbose_name='Maritime Transport Information'
    )
    air_transport_information = models.TextField(
        blank=True,
        verbose_name='Air Transport Information'
    )
    road_rail_transport_information = models.TextField(
        blank=True,
        verbose_name='Road / Rail Transport Information'
    )
    inland_waterway_transport_information = models.TextField(
        blank=True,
        verbose_name='Inland Waterway Transport Information'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 14'
        verbose_name_plural = 'SDS Section 14'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 14'
    


# =============================================
# SDS Section 15 - Regulatory Information
# =============================================
class SDSSection15(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_15',
        verbose_name='SDS Version'
    )
    safety_health_environmental_regulations = models.TextField(
        blank=True,
        verbose_name='Safety, Health and Environmental Regulations'
    )
    chemical_specific_regulations = models.TextField(
        blank=True,
        verbose_name='Chemical-Specific Regulations'
    )
    national_regulations = models.TextField(
        blank=True,
        verbose_name='National Regulations'
    )
    regional_regulations = models.TextField(
        blank=True,
        verbose_name='Regional Regulations'
    )
    international_regulations = models.TextField(
        blank=True,
        verbose_name='International Regulations'
    )
    chemical_inventory_status = models.TextField(
        blank=True,
        verbose_name='Chemical Inventory Status'
    )
    restricted_prohibited_use = models.TextField(
        blank=True,
        verbose_name='Restricted or Prohibited Uses'
    )
    regulatory_authorities = models.TextField(
        blank=True,
        verbose_name='Applicable Regulatory Authorities'
    )
    reporting_notification_requirements = models.TextField(
        blank=True,
        verbose_name='Reporting and Notification Requirements'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 15'
        verbose_name_plural = 'SDS Section 15'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 15'
    


# =============================================
# SDS Section 16 - Other Information
# =============================================
class SDSSection16(models.Model):
    sds_version = models.OneToOneField(
        SDSVersion,
        on_delete=models.CASCADE,
        related_name='section_16',
        verbose_name='SDS Version'
    )
    preparation_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Preparation Date'
    )
    revision_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Revision Date'
    )
    revision_summary = models.TextField(
        blank=True,
        verbose_name='Revision Summary'
    )
    key_changes_from_previous_version = models.TextField(
        blank=True,
        verbose_name='Key Changes from Previous Version'
    )
    abbreviations = models.TextField(
        blank=True,
        verbose_name='Abbreviations and Acronyms'
    )
    references = models.TextField(
        blank=True,
        verbose_name='References and Sources'
    )
    data_sources = models.TextField(
        blank=True,
        verbose_name='Data Sources'
    )
    training_information = models.TextField(
        blank=True,
        verbose_name='Training Information'
    )
    disclaimer = models.TextField(
        blank=True,
        verbose_name='Disclaimer'
    )
    prepared_by = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Prepared By'
    )
    reviewed_by = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Reviewed By'
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name='Additional Information'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = 'SDS Section 16'
        verbose_name_plural = 'SDS Section 16'

    def __str__(self):
        return f'{self.sds_version.sds.sds_number} - Section 16'