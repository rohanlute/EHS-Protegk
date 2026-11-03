import re
from django.db import models, router, transaction
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from apps.organizations.models import *

# Kaizen category model
class KaizenCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text='Full name of Kaizen category')
    code = models.CharField(max_length=100, unique=True, help_text='Unique short code')
    description = models.TextField(blank=True, help_text='Description of the kaizen category')
    is_active = models.BooleanField(default=True,help_text='Is the kaizen category active?')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="kaizen_categories_created")
    class Meta:
        ordering = ["name"]
        verbose_name = "Kaizen Category"
        verbose_name_plural = "Kaizen Categories"

    def __str__(self):
        return f"{self.name} ({self.code})"


# Main kaizen model
class Kaizen(models.Model):
    class StatusChoices(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_INITIAL_REVIEW = "UNDER_INITIAL_REVIEW", "Under Initial Review"
        UNDER_TECHNICAL_EVALUATION = ("UNDER_TECHNICAL_EVALUATION", "Under Technical Evaluation")
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"
        APPROVED_FOR_IMPLEMENTATION = ("APPROVED_FOR_IMPLEMENTATION", "Approved for Implementation")
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        ON_HOLD = "ON_HOLD", "Implementation On Hold"
        PENDING_VERIFICATION = "PENDING_VERIFICATION", "Pending Verification"
        PENDING_CLOSURE = "PENDING_CLOSURE", "Pending Closure"
        CLOSED = "CLOSED", "Closed"
        RETURNED_FOR_CLARIFICATION = ("RETURNED_FOR_CLARIFICATION", "Returned for Clarification")
        RETURNED_FOR_REVISION = ("RETURNED_FOR_REVISION", "Returned for Revision")
        REJECTED = "REJECTED", "Rejected"
        DUPLICATE = "DUPLICATE", "Duplicate"
        VERIFICATION_FAILED = ("VERIFICATION_FAILED", "Verification Failed")

    class PriorityChoices(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class BenefitTypeChoices(models.TextChoices):
        SAFETY = "SAFETY", "Safety Improvement"
        HEALTH = "HEALTH", "Health Improvement"
        ENVIRONMENT = "ENVIRONMENT", "Environmental Improvement"
        QUALITY = "QUALITY", "Quality Improvement"
        PRODUCTIVITY = "PRODUCTIVITY", "Productivity Improvement"
        COST = "COST", "Cost Reduction"
        ERGONOMICS = "ERGONOMICS", "Ergonomics Improvement"
        COMPLIANCE = "COMPLIANCE", "Compliance Improvement"
        OTHER = "OTHER", "Other"

    class RelatedModuleChoices(models.TextChoices):
        INCIDENT = "incident", "Incident"
        HAZARD = "hazard", "Hazard"
        CAPA = "capa", "CAPA"
        INSPECTION = "inspection", "Inspection"
        AUDIT = "audit", "Audit"
        ERGONOMICS = "ergonomics", "Ergonomics"
        HIRA = "hira", "Risk Assessment"
        INDUSTRIAL_HYGIENE = "industrialhygiene", "Industrial Hygiene"


    kaizen_id = models.CharField(max_length=30, unique=True, blank=True, help_text="System-generated Kaizen reference number")
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(KaizenCategory, on_delete=models.PROTECT, related_name="kaizens")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="kaizens_submitted")
    submission_date = models.DateTimeField(null=True, blank=True)

    #location details
    plant = models.ForeignKey(Plant, on_delete=models.SET_NULL, null=True, blank=True, related_name="kaizens")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="kaizens")
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name="kaizens")
    location_record = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="kaizens")
    sublocation = models.ForeignKey(SubLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="kaizens")
    location = models.CharField(max_length=255, blank=True)
    additional_location_details = models.TextField(blank=True)

    # Improvement details
    problem_statement = models.TextField()
    proposed_solution = models.TextField()
    expected_benefits = models.TextField(blank=True)

    benefit_type = models.CharField(max_length=30,choices=BenefitTypeChoices.choices,default=BenefitTypeChoices.SAFETY)
    priority = models.CharField(max_length=20, choices=PriorityChoices.choices, default=PriorityChoices.MEDIUM)
    estimated_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    # Dynamic source record linking
    has_related_record = models.BooleanField(default=False, help_text="Select Yes if this Kaizen is linked to an existing EHS record.")
    related_module = models.CharField(max_length=50, choices=RelatedModuleChoices.choices, blank=True, null=True, help_text="Select the EHS module containing the source record.")
    related_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True, related_name="related_kaizens")
    related_object_id = models.PositiveBigIntegerField(null=True, blank=True)
    related_record = GenericForeignKey("related_content_type", "related_object_id")
    manual_source_reference = models.CharField(max_length=150, blank=True, help_text="Enter a manual source reference number.")

    # Supporting attachment
    related_attachment = models.FileField(upload_to="kaizen/related_attachments/%Y/%m/", null=True, blank=True, help_text="Upload supporting document or evidence.")

    # Workflow status
    status = models.CharField(max_length=40, choices=StatusChoices.choices, default=StatusChoices.DRAFT, db_index=True)
    current_stage = models.CharField(max_length=40, default="SUBMISSION")

    # General assignment
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="kaizens_assigned")

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="kaizens_created")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kaizen"
        verbose_name_plural = "Kaizens"
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["plant", "department"]),
        ]

    def __str__(self):
        return f"{self.kaizen_id or self.title} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.kaizen_id and self.category_id:
            using = kwargs.get('using') or self._state.db or router.db_for_write(
                type(self), instance=self,
            )
            with transaction.atomic(using=using):
                category = KaizenCategory.objects.using(using).select_for_update().get(
                    pk=self.category_id,
                )
                category_code = re.sub(
                    r'[^A-Za-z0-9]+', '', category.code or '',
                ).upper()[:10] or 'GEN'
                year = timezone.localdate().year
                prefix = f'KZN-{category_code}-{year}-'
                existing_ids = type(self).objects.using(using).filter(
                    kaizen_id__startswith=prefix,
                ).values_list('kaizen_id', flat=True)
                highest_sequence = max(
                    (
                        int(reference.rsplit('-', 1)[-1])
                        for reference in existing_ids
                        if reference.rsplit('-', 1)[-1].isdigit()
                    ),
                    default=0,
                )
                self.kaizen_id = f'{prefix}{highest_sequence + 1:03d}'
                kwargs.setdefault('using', using)
                if kwargs.get('update_fields') is not None:
                    kwargs['update_fields'] = set(kwargs['update_fields']) | {'kaizen_id'}
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)


# Initial Review Model
class KaizenInitialReview(models.Model):
    class DecisionChoices(models.TextChoices):
        ACCEPTED = "ACCEPTED", "Accepted for Technical Evaluation"
        CLARIFICATION = "CLARIFICATION", "Clarification Required"
        DUPLICATE = "DUPLICATE", "Duplicate Idea"
        REJECTED = "REJECTED", "Rejected"

    kaizen = models.ForeignKey(Kaizen, on_delete=models.CASCADE, related_name="initial_reviews")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="kaizen_initial_reviews")
    review_date = models.DateTimeField(default=timezone.now)
    decision = models.CharField(max_length=20, choices=DecisionChoices.choices)
    review_comments = models.TextField()
    clarification_required = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-review_date"]

    def __str__(self):
        return f"Initial Review - {self.kaizen}"


# Technical Evaluation
class KaizenTechnicalEvaluation(models.Model):
    class DecisionChoices(models.TextChoices):
        RECOMMEND_APPROVAL = "RECOMMEND_APPROVAL", "Recommend Approval"
        CLARIFICATION = "CLARIFICATION", "Request Clarification"
        REJECTED = "REJECTED", "Recommend Rejection"

    class FeasibilityChoices(models.TextChoices):
        FEASIBLE = "FEASIBLE", "Feasible"
        FEASIBLE_WITH_CHANGES = "FEASIBLE_WITH_CHANGES", "Feasible with Changes"
        NOT_FEASIBLE = "NOT_FEASIBLE", "Not Feasible"

    kaizen = models.ForeignKey(Kaizen, on_delete=models.CASCADE, related_name="technical_evaluations")
    evaluated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="kaizen_technical_evaluations")
    evaluation_date = models.DateTimeField(default=timezone.now)
    decision = models.CharField(
        max_length=30,
        choices=DecisionChoices.choices,
        default=DecisionChoices.RECOMMEND_APPROVAL,
    )
    feasibility = models.CharField(max_length=30, choices=FeasibilityChoices.choices)
    technical_comments = models.TextField(blank=True)
    safety_impact = models.TextField(blank=True)
    operational_impact = models.TextField(blank=True)
    resource_requirements = models.TextField(blank=True)
    estimated_implementation_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    estimated_completion_date = models.DateField(null=True, blank=True)
    recommendation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-evaluation_date"]

    def __str__(self):
        return f"Technical Evaluation - {self.kaizen}"


# Approval
class KaizenApproval(models.Model):
    class DecisionChoices(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        REVISION = "REVISION", "Revision Required"

    kaizen = models.ForeignKey(Kaizen, on_delete=models.CASCADE, related_name="approvals")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="kaizen_approvals")
    approval_date = models.DateTimeField(default=timezone.now)
    decision = models.CharField(max_length=20, choices=DecisionChoices.choices)
    approval_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-approval_date"]

    def __str__(self):
        return f"Approval - {self.kaizen}"


# Kaizen Implementation
class KaizenImplementation(models.Model):
    class ImplementationStatusChoices(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not Started"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        ON_HOLD = "ON_HOLD", "On Hold"
        COMPLETED = "COMPLETED", "Completed"

    kaizen = models.ForeignKey(Kaizen, on_delete=models.CASCADE, related_name="implementations")
    implementation_owner = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="kaizen_implementations")
    implementation_status = models.CharField(max_length=20, choices=ImplementationStatusChoices.choices, default=ImplementationStatusChoices.NOT_STARTED, db_index=True)
    planned_start_date = models.DateField(null=True, blank=True)
    planned_end_date = models.DateField(null=True, blank=True)
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    implementation_actions = models.TextField(blank=True, help_text="Overall implementation approach or plan.")
    resources_used = models.TextField(blank=True)
    actual_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    implementation_remarks = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kaizen Implementation"
        verbose_name_plural = "Kaizen Implementations"

    def __str__(self):
        return f"Implementation - {self.kaizen}"

# KAIZEN VERIFICATION
# Overall verification after implementation

class KaizenVerification(models.Model):
    class ResultChoices(models.TextChoices):
        SUCCESSFUL = "SUCCESSFUL", "Successful"
        PARTIAL = "PARTIAL", "Partially Successful"
        FAILED = "FAILED", "Failed - Rework Required"

    kaizen = models.ForeignKey(Kaizen, on_delete=models.CASCADE, related_name="verifications")
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="kaizen_verifications")
    verification_date = models.DateTimeField(default=timezone.now)
    result = models.CharField(max_length=20, choices=ResultChoices.choices)
    rework_required = models.BooleanField(
        null=True,
        blank=True,
        help_text='For partially successful verification, indicate whether the implementation needs rework.',
    )
    verification_method = models.TextField(blank=True)
    before_improvement = models.TextField(blank=True)
    after_improvement = models.TextField(blank=True)
    actual_benefits = models.TextField(blank=True)
    evidence_details = models.TextField(blank=True)
    verification_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-verification_date"]
        verbose_name = "Kaizen Verification"
        verbose_name_plural = "Kaizen Verifications"

    def __str__(self):
        return f"Verification - {self.kaizen}"


# KAIZEN ATTACHMENTS
class KaizenAttachment(models.Model):
    class AttachmentTypeChoices(models.TextChoices):
        BEFORE = "BEFORE", "Before Improvement"
        PROPOSAL = "PROPOSAL", "Proposal"
        TECHNICAL = "TECHNICAL", "Technical Evaluation"
        IMPLEMENTATION = "IMPLEMENTATION", "Implementation Evidence"
        AFTER = "AFTER", "After Improvement"
        VERIFICATION = "VERIFICATION", "Verification Evidence"
        OTHER = "OTHER", "Other"

    kaizen = models.ForeignKey(Kaizen, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="kaizen/attachments/%Y/%m/")
    attachment_type = models.CharField(max_length=20, choices=AttachmentTypeChoices.choices, default=AttachmentTypeChoices.OTHER)
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="kaizen_attachments_uploaded")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Kaizen Attachment"
        verbose_name_plural = "Kaizen Attachments"

    def __str__(self):
        return f"{self.kaizen} - {self.file.name}"


# KAIZEN CLOSURE

class KaizenClosure(models.Model):

    kaizen = models.OneToOneField(Kaizen, on_delete=models.CASCADE, related_name="closure")
    # Final outcome of the improvement
    final_outcome = models.TextField(help_text="Summary of the implemented improvement and final outcome.")
    # Actual benefits achieved
    actual_benefits = models.TextField(help_text="Describe the actual benefits or savings achieved.")
    # Financial details
    actual_implementation_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text="Final actual implementation cost.")
    # Lessons learned
    lessons_learned = models.TextField(blank=True, help_text="What worked well and what should be reused or improved.")
    # Final closure comments
    closure_comments = models.TextField(blank=True)
    # Closure details
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="kaizens_closed")
    closure_date = models.DateTimeField( default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-closure_date"]
        verbose_name = "Kaizen Closure"
        verbose_name_plural = "Kaizen Closures"

    def __str__(self):
        return f"Closure - {self.kaizen}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.kaizen_id:
            closure_ready = self.kaizen.verifications.filter(
                Q(result=KaizenVerification.ResultChoices.SUCCESSFUL)
                | Q(
                    result=KaizenVerification.ResultChoices.PARTIAL,
                    rework_required=False,
                )
            ).exists()

            if not closure_ready:
                raise ValidationError(
                    "Kaizen cannot be closed unless verification is successful or any partial result has no rework required."
                )


# KAIZEN WORKFLOW HISTORY
class KaizenHistory(models.Model):

    kaizen = models.ForeignKey(Kaizen, on_delete=models.CASCADE, related_name="history")
    previous_status = models.CharField(max_length=40, blank=True)
    new_status = models.CharField(max_length=40)
    action = models.CharField(max_length=100, blank=True)
    comments = models.TextField(blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="kaizen_status_changes")
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = "Kaizen History"
        verbose_name_plural = "Kaizen History"

    def __str__(self):
        return f"{self.kaizen} - {self.new_status}"
