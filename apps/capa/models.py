from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone

from apps.organizations.models import Department, Location, Plant, SubLocation, Zone


User = settings.AUTH_USER_MODEL


class CAPA(models.Model):
    class SourceType(models.TextChoices):
        INCIDENT = "INCIDENT", "Incident"
        HAZARD = "HAZARD", "Hazard"
        INSPECTION = "INSPECTION", "Inspection"
        AUDIT = "AUDIT", "Audit"
        OBSERVATION = "OBSERVATION", "Observation"
        RISK_ASSESSMENT = "RISK_ASSESSMENT", "Risk Assessment"
        LEGAL_COMPLIANCE = "LEGAL_COMPLIANCE", "Legal Compliance"
        MANAGEMENT_REVIEW = "MANAGEMENT_REVIEW", "Management Review"
        MANUAL = "MANUAL", "Manual"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        OPEN = "OPEN", "Open"
        INVESTIGATION_IN_PROGRESS = "INVESTIGATION_IN_PROGRESS", "Investigation in Progress"
        INVESTIGATION_SUBMITTED = "INVESTIGATION_SUBMITTED", "Investigation Submitted"
        INVESTIGATION_APPROVED = "INVESTIGATION_APPROVED", "Investigation Approved"
        INVESTIGATION_REJECTED = "INVESTIGATION_REJECTED", "Investigation Rejected"
        ACTION_PLAN_IN_PROGRESS = "ACTION_PLAN_IN_PROGRESS", "Action Plan in Progress"
        ACTION_IMPLEMENTATION = "ACTION_IMPLEMENTATION", "Action Implementation"
        VERIFICATION = "VERIFICATION", "Verification"
        EFFECTIVENESS_REVIEW = "EFFECTIVENESS_REVIEW", "Effectiveness Review"
        CLOSED = "CLOSED", "Closed"
        REOPENED = "REOPENED", "Reopened"
        CANCELLED = "CANCELLED", "Cancelled"

    class Severity(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    capa_number = models.CharField(max_length=30, unique=True, editable=False, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    source_type = models.CharField(max_length=30, choices=SourceType.choices, default=SourceType.MANUAL)
    source_content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    source_object_id = models.PositiveIntegerField(null=True, blank=True)
    source_object = GenericForeignKey("source_content_type", "source_object_id")
    source_reference = models.CharField(max_length=255, blank=True)
    source_snapshot = models.JSONField(default=dict, blank=True)

    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="capas")
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name="capas")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="capas")
    sublocation = models.ForeignKey(SubLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="capas")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="capas")

    category = models.CharField(max_length=100, blank=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MEDIUM)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    owner = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_capas")
    target_date = models.DateField(null=True, blank=True)
    reason_required = models.TextField(blank=True)

    capa_recommended = models.BooleanField(default=False)
    capa_reason = models.TextField(blank=True)

    status = models.CharField(max_length=40, choices=Status.choices, default=Status.DRAFT, db_index=True)
    progress = models.PositiveSmallIntegerField(default=0)

    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_capas")
    updated_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_capas")
    closed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="closed_capas")
    reopened_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="reopened_capas")
    closed_date = models.DateTimeField(null=True, blank=True)
    reopened_date = models.DateTimeField(null=True, blank=True)

    closure_remarks = models.TextField(blank=True)
    lessons_learned = models.TextField(blank=True)
    final_recommendations = models.TextField(blank=True)

    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "CAPA"
        verbose_name_plural = "CAPAs"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["source_type"]),
            models.Index(fields=["plant", "status"]),
        ]

    def __str__(self):
        return f"{self.capa_number} - {self.title}"

    def get_absolute_url(self):
        return reverse("capa:detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if not self.capa_number:
            today = timezone.localdate()
            prefix = f"CAPA-{today:%Y}"
            with transaction.atomic():
                last = CAPA.objects.select_for_update().filter(capa_number__startswith=prefix).order_by("-capa_number").first()
                next_num = 1
                if last and last.capa_number.rsplit("-", 1)[-1].isdigit():
                    next_num = int(last.capa_number.rsplit("-", 1)[-1]) + 1
                self.capa_number = f"{prefix}-{next_num:05d}"

        if self.status == self.Status.CLOSED and not self.closed_date:
            self.closed_date = timezone.now()

        if self.status == self.Status.REOPENED and not self.reopened_date:
            self.reopened_date = timezone.now()

        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return bool(self.target_date and self.status not in {self.Status.CLOSED, self.Status.CANCELLED} and timezone.localdate() > self.target_date)

    @property
    def action_summary(self):
        return self.actions.count(), self.actions.filter(status=CAPAAction.Status.VERIFIED).count()


class CAPAInvestigation(models.Model):
    class Method(models.TextChoices):
        FIVE_WHY = "FIVE_WHY", "5 Why"
        FISHBONE = "FISHBONE", "Fishbone / Ishikawa"
        FAULT_TREE = "FAULT_TREE", "Fault Tree Analysis"
        OTHER = "OTHER", "Other"

    class RootCauseCategory(models.TextChoices):
        HUMAN_FACTOR = "HUMAN_FACTOR", "Human Factor"
        EQUIPMENT_FAILURE = "EQUIPMENT_FAILURE", "Equipment / Machine Failure"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        PROCEDURE_SOP = "PROCEDURE_SOP", "Procedure / SOP"
        TRAINING = "TRAINING", "Training / Competency"
        SUPERVISION = "SUPERVISION", "Supervision"
        DESIGN_ENGINEERING = "DESIGN_ENGINEERING", "Design / Engineering"
        MATERIAL = "MATERIAL", "Material"
        PROCESS_METHOD = "PROCESS_METHOD", "Process / Method"
        COMMUNICATION = "COMMUNICATION", "Communication"
        RISK_ASSESSMENT = "RISK_ASSESSMENT", "Risk Assessment"
        CONTRACTOR = "CONTRACTOR", "Contractor Management"
        MANAGEMENT_SYSTEM = "MANAGEMENT_SYSTEM", "Management System"
        ENVIRONMENTAL = "ENVIRONMENTAL", "Environmental Condition"
        RESOURCE = "RESOURCE", "Resource / Availability"
        COMPLIANCE = "COMPLIANCE", "Compliance"
        OTHER = "OTHER", "Other"

    class Likelihood(models.IntegerChoices):
        ONE = 1, "1"
        TWO = 2, "2"
        THREE = 3, "3"
        FOUR = 4, "4"
        FIVE = 5, "5"

    class Severity(models.IntegerChoices):
        ONE = 1, "1"
        TWO = 2, "2"
        THREE = 3, "3"
        FOUR = 4, "4"
        FIVE = 5, "5"

    capa = models.OneToOneField(CAPA, on_delete=models.CASCADE, related_name="investigation")
    investigation_date = models.DateField(null=True, blank=True)
    lead_investigator = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="lead_capa_investigations")
    investigation_team = models.TextField(blank=True)
    investigation_method = models.CharField(max_length=20, choices=Method.choices, default=Method.FIVE_WHY)

    problem_statement = models.TextField(blank=True)
    what_happened = models.TextField(blank=True)
    impact_consequence = models.TextField(blank=True)
    what_was_affected = models.TextField(blank=True)
    sequence_of_events = models.TextField(blank=True)
    findings = models.TextField(blank=True)
    evidence_collected = models.TextField(blank=True)
    witness_statements = models.TextField(blank=True)
    existing_controls = models.TextField(blank=True)

    existing_control_in_place = models.BooleanField(default=False)
    existing_control_followed = models.CharField(max_length=20, blank=True)
    existing_control_adequate = models.CharField(max_length=20, blank=True)
    control_failure_reason = models.TextField(blank=True)
    control_gap_identified = models.TextField(blank=True)

    why1 = models.TextField(blank=True)
    why2 = models.TextField(blank=True)
    why3 = models.TextField(blank=True)
    why4 = models.TextField(blank=True)
    why5 = models.TextField(blank=True)
    final_root_cause = models.TextField(blank=True)
    root_cause_category = models.CharField(max_length=40, choices=RootCauseCategory.choices, blank=True)
    root_cause_details = models.TextField(blank=True)

    contributing_factors = models.JSONField(default=list, blank=True)
    extent_analysis = models.JSONField(default=dict, blank=True)
    affected_plants = models.ManyToManyField(Plant, blank=True, related_name="capa_investigations")
    affected_departments = models.ManyToManyField(Department, blank=True, related_name="capa_investigations")
    affected_locations = models.ManyToManyField(Location, blank=True, related_name="capa_investigations")
    related_references = models.TextField(blank=True)

    initial_likelihood = models.PositiveSmallIntegerField(null=True, blank=True)
    initial_severity = models.PositiveSmallIntegerField(null=True, blank=True)
    initial_risk_score = models.PositiveSmallIntegerField(null=True, blank=True)
    existing_controls_summary = models.TextField(blank=True)
    residual_likelihood = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_severity = models.PositiveSmallIntegerField(null=True, blank=True)
    residual_risk_score = models.PositiveSmallIntegerField(null=True, blank=True)
    risk_assessment_update_required = models.BooleanField(default=False)
    risk_assessment_remarks = models.TextField(blank=True)

    procedure_sop_revision_required = models.BooleanField(default=False)
    training_required = models.BooleanField(default=False)
    risk_assessment_revision_required = models.BooleanField(default=False)
    engineering_modification_required = models.BooleanField(default=False)
    moc_required = models.BooleanField(default=False)
    legal_compliance_review_required = models.BooleanField(default=False)
    document_control_update_required = models.BooleanField(default=False)
    management_system_impact_details = models.TextField(blank=True)

    investigation_conclusion = models.TextField(blank=True)
    root_cause_confirmed = models.CharField(max_length=20, blank=True)
    additional_investigation_required = models.BooleanField(default=False)
    systemic_issue_identified = models.BooleanField(default=False)
    extent_analysis_required = models.BooleanField(default=False)
    action_plan_required = models.BooleanField(default=True)
    investigator_recommendation = models.TextField(blank=True)

    completed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="completed_capa_investigations")
    completed_date = models.DateField(null=True, blank=True)
    reviewer = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_capa_investigations")
    review_date = models.DateField(null=True, blank=True)
    reviewer_comments = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "CAPA Investigation"
        verbose_name_plural = "CAPA Investigations"

    def __str__(self):
        return f"Investigation - {self.capa.capa_number}"


class CAPAAction(models.Model):
    class ActionType(models.TextChoices):
        CORRECTION = "CORRECTION", "Correction"
        CONTAINMENT = "CONTAINMENT", "Containment Action"
        CORRECTIVE = "CORRECTIVE", "Corrective Action"
        PREVENTIVE = "PREVENTIVE", "Preventive Action"
        SYSTEM_IMPROVEMENT = "SYSTEM_IMPROVEMENT", "System Improvement"
        TRAINING = "TRAINING", "Training"
        RISK_ASSESSMENT = "RISK_ASSESSMENT", "Risk Assessment"
        PROCEDURE = "PROCEDURE", "Procedure / SOP"
        ENGINEERING = "ENGINEERING", "Engineering Control"
        INSPECTION = "INSPECTION", "Inspection / Monitoring"
        COMPLIANCE = "COMPLIANCE", "Compliance"
        MOC = "MOC", "Management of Change"
        COMMUNICATION = "COMMUNICATION", "Communication"
        DOCUMENT_CONTROL = "DOCUMENT_CONTROL", "Document Control"

    class ControlType(models.TextChoices):
        ADMINISTRATIVE = "ADMINISTRATIVE", "Administrative"
        ENGINEERING = "ENGINEERING", "Engineering"
        BEHAVIORAL = "BEHAVIORAL", "Behavioral"
        ELIMINATION = "ELIMINATION", "Elimination"
        SUBSTITUTION = "SUBSTITUTION", "Substitution"
        PPE = "PPE", "PPE"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        SUBMITTED = "SUBMITTED", "Submitted"
        REJECTED = "REJECTED", "Rejected"
        PENDING_VERIFICATION = "PENDING_VERIFICATION", "Pending Verification"
        VERIFIED = "VERIFIED", "Verified"
        CLOSED = "CLOSED", "Closed"
        OVERDUE = "OVERDUE", "Overdue"

    capa = models.ForeignKey(CAPA, on_delete=models.CASCADE, related_name="actions")
    action_plan_type = models.CharField(max_length=40, choices=ActionType.choices)
    action_description = models.TextField()
    assigned_to = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_capa_actions")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="capa_actions")
    target_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=20, choices=CAPA.Priority.choices, default=CAPA.Priority.MEDIUM)
    control_type = models.CharField(max_length=20, choices=ControlType.choices, blank=True)
    evidence_required = models.BooleanField(default=True)
    verification_required = models.BooleanField(default=True)
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.PENDING, db_index=True)

    source_action_content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL, related_name="capa_source_action_items")
    source_action_object_id = models.PositiveIntegerField(null=True, blank=True)
    source_action_object = GenericForeignKey("source_action_content_type", "source_action_object_id")

    completion_remarks = models.TextField(blank=True)
    verified_remarks = models.TextField(blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_capa_actions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["target_date", "-created_at"]

    def __str__(self):
        return f"{self.capa.capa_number} - Action {self.pk or 'new'}"

    @property
    def is_overdue(self):
        return bool(self.target_date and self.status not in {self.Status.VERIFIED, self.Status.CLOSED} and timezone.localdate() > self.target_date)


class CAPAActionCompletion(models.Model):
    action = models.OneToOneField(CAPAAction, on_delete=models.CASCADE, related_name="completion")
    completed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="capa_action_completions")
    completion_date = models.DateField(default=timezone.localdate)
    completion_remarks = models.TextField(blank=True)
    evidence = models.FileField(upload_to="capa/action_completion/%Y/%m/", blank=True, null=True)
    submitted_for_verification = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Completion - {self.action_id}"


class CAPAActionVerification(models.Model):
    class Result(models.TextChoices):
        VERIFIED = "VERIFIED", "Verified / Accepted"
        PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED", "Partially Verified"
        REJECTED = "REJECTED", "Rejected"

    class Method(models.TextChoices):
        PHYSICAL_INSPECTION = "PHYSICAL_INSPECTION", "Physical Inspection"
        DOCUMENT_REVIEW = "DOCUMENT_REVIEW", "Document Review"
        PHOTO_VIDEO_REVIEW = "PHOTO_VIDEO_REVIEW", "Photo / Video Review"
        INTERVIEW = "INTERVIEW", "Interview"
        OBSERVATION = "OBSERVATION", "Observation"
        MEASUREMENT_TEST = "MEASUREMENT_TEST", "Measurement / Test"
        SYSTEM_RECORD_REVIEW = "SYSTEM_RECORD_REVIEW", "System Record Review"
        OTHER = "OTHER", "Other"

    action = models.OneToOneField(CAPAAction, on_delete=models.CASCADE, related_name="verification")
    verification_date = models.DateField(null=True, blank=True)
    verified_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_capa_actions")
    verification_method = models.CharField(max_length=40, choices=Method.choices, blank=True)
    was_implemented = models.BooleanField(default=False)
    matches_approved_action = models.BooleanField(default=False)
    evidence_sufficient = models.BooleanField(default=False)
    meets_required_standard = models.BooleanField(default=False)
    verification_findings = models.TextField(blank=True)
    deviation_deficiency = models.TextField(blank=True)
    additional_evidence_required = models.BooleanField(default=False)
    additional_evidence_remarks = models.TextField(blank=True)
    result = models.CharField(max_length=30, choices=Result.choices, default=Result.VERIFIED)
    rejection_reason = models.TextField(blank=True)
    additional_action_required = models.TextField(blank=True)
    reverification_required = models.BooleanField(default=False)
    reverification_due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Verification - {self.action_id}"


class CAPAEffectivenessReview(models.Model):
    class Result(models.TextChoices):
        EFFECTIVE = "EFFECTIVE", "Effective"
        PARTIALLY_EFFECTIVE = "PARTIALLY_EFFECTIVE", "Partially Effective"
        NOT_EFFECTIVE = "NOT_EFFECTIVE", "Not Effective"

    capa = models.OneToOneField(CAPA, on_delete=models.CASCADE, related_name="effectiveness_review")
    review_date = models.DateField(null=True, blank=True)
    reviewed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="effectiveness_reviews")
    corrective_working_as_intended = models.BooleanField(default=False)
    preventive_working_as_intended = models.BooleanField(default=False)
    risk_reduced_as_expected = models.BooleanField(default=False)
    controls_adequate = models.BooleanField(default=False)
    systemic_cause_addressed = models.BooleanField(default=False)
    effectiveness_evidence = models.TextField(blank=True)
    evidence_description = models.TextField(blank=True)
    review_findings = models.TextField(blank=True)
    observed_improvement = models.TextField(blank=True)
    remaining_risk_gap = models.TextField(blank=True)
    result = models.CharField(max_length=30, choices=Result.choices, default=Result.EFFECTIVE)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Effectiveness - {self.capa.capa_number}"


class CAPAAttachment(models.Model):
    capa = models.ForeignKey(CAPA, on_delete=models.CASCADE, related_name="attachments")
    action = models.ForeignKey(CAPAAction, on_delete=models.CASCADE, null=True, blank=True, related_name="attachments")
    file = models.FileField(upload_to="capa/attachments/%Y/%m/")
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="uploaded_capa_attachments")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Attachment {self.pk}"


class CAPAComment(models.Model):
    capa = models.ForeignKey(CAPA, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="capa_comments")
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment {self.pk} on {self.capa.capa_number}"


class CAPAApproval(models.Model):
    class Type(models.TextChoices):
        INVESTIGATION = "INVESTIGATION", "Investigation"
        CLOSURE = "CLOSURE", "Closure"

    capa = models.ForeignKey(CAPA, on_delete=models.CASCADE, related_name="approvals")
    approval_type = models.CharField(max_length=20, choices=Type.choices)
    approved_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="capa_approvals")
    approved_at = models.DateTimeField(null=True, blank=True)
    decision = models.CharField(max_length=20, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-approved_at", "-id"]

    def __str__(self):
        return f"{self.approval_type} approval for {self.capa.capa_number}"


class CAPAAuditLog(models.Model):
    capa = models.ForeignKey(CAPA, on_delete=models.CASCADE, related_name="audit_logs")
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="capa_audit_logs")
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=80)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp", "-id"]

    def __str__(self):
        return f"{self.action} @ {self.timestamp:%Y-%m-%d %H:%M}"
