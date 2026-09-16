import datetime

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import OperationalError, ProgrammingError
from django.db import models
from django.utils import timezone

from apps.organizations.models import Department, Plant


def calculate_risk_score(likelihood, severity):
    if likelihood is None or severity is None:
        return 0
    return int(likelihood) * int(severity)


def risk_level_for_score(score):
    score = int(score or 0)
    if score <= 0:
        return ""
    try:
        level = RiskMatrixLevel.objects.filter(
            risk_matrix__is_active=True,
            is_active=True,
            min_score__lte=score,
            max_score__gte=score,
        ).select_related("risk_matrix").order_by(
            "-risk_matrix__created_at",
            "display_order",
            "min_score",
        ).first()
        if level:
            return level.risk_level
    except (OperationalError, ProgrammingError):
        pass
    if score <= 4:
        return "Low"
    if score <= 9:
        return "Medium"
    if score <= 16:
        return "High"
    return "Critical"


class HIRAModule(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.SlugField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "HIRA Module"
        verbose_name_plural = "HIRA Modules"

    def __str__(self):
        return self.name


class RiskMatrix(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    min_likelihood = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5)])
    max_likelihood = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    min_severity = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5)])
    max_severity = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hira_risk_matrices_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "name"]
        verbose_name = "HIRA Risk Matrix"
        verbose_name_plural = "HIRA Risk Matrices"

    def __str__(self):
        return self.name


class RiskMatrixLevel(models.Model):
    RISK_LEVEL_CHOICES = [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
        ("Critical", "Critical"),
    ]

    risk_matrix = models.ForeignKey(RiskMatrix, on_delete=models.CASCADE, related_name="levels")
    min_score = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(25)])
    max_score = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(25)])
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES)
    display_order = models.PositiveSmallIntegerField(default=1)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["risk_matrix", "display_order", "min_score"]
        verbose_name = "HIRA Risk Matrix Level"
        verbose_name_plural = "HIRA Risk Matrix Levels"

    def __str__(self):
        return f"{self.risk_matrix} | {self.min_score}-{self.max_score} {self.risk_level}"

    def clean(self):
        if self.min_score and self.max_score and self.min_score > self.max_score:
            from django.core.exceptions import ValidationError

            raise ValidationError({"max_score": "Maximum score must be greater than or equal to minimum score."})


class HazardRiskMaster(models.Model):
    module = models.ForeignKey(
        HIRAModule,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hazard_risk_rules",
        help_text="Blank means this rule applies to all HIRA modules.",
    )
    process = models.CharField(max_length=200, blank=True)
    activity = models.CharField(max_length=250)
    hazard_category = models.CharField(max_length=50, choices=[
        ("Mechanical", "Mechanical"),
        ("Electrical", "Electrical"),
        ("Chemical", "Chemical"),
        ("Physical", "Physical"),
        ("Fire / Explosion", "Fire / Explosion"),
        ("Ergonomic", "Ergonomic"),
        ("Biological", "Biological"),
        ("Vehicle", "Vehicle"),
        ("Environmental", "Environmental"),
        ("Other", "Other"),
    ])
    hazard = models.TextField()
    unsafe_act = models.TextField(blank=True)
    unsafe_condition = models.TextField(blank=True)
    consequence = models.TextField()
    existing_controls = models.TextField(blank=True)
    suggested_additional_controls = models.TextField(blank=True)
    default_likelihood = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    default_severity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hira_hazard_risk_masters_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["module__name", "activity", "hazard_category"]
        verbose_name = "HIRA Hazard & Risk Master"
        verbose_name_plural = "HIRA Hazard & Risk Masters"
        indexes = [
            models.Index(fields=["is_active", "activity"]),
            models.Index(fields=["hazard_category", "is_active"]),
        ]

    def __str__(self):
        module = self.module.name if self.module else "All Modules"
        return f"{module} | {self.activity} | {self.hazard_category}"

    def snapshot(self):
        return {
            "master_rule_id": self.pk,
            "module": self.module.name if self.module else "All Modules",
            "process": self.process,
            "activity": self.activity,
            "hazard_category": self.hazard_category,
            "hazard": self.hazard,
            "unsafe_act": self.unsafe_act,
            "unsafe_condition": self.unsafe_condition,
            "consequence": self.consequence,
            "existing_controls": self.existing_controls,
            "suggested_additional_controls": self.suggested_additional_controls,
            "default_likelihood": self.default_likelihood,
            "default_severity": self.default_severity,
            "captured_at": timezone.now().isoformat(),
        }


class HIRA(models.Model):
    ASSESSMENT_TYPE_CHOICES = [
        ("ROUTINE", "Routine"),
        ("NON_ROUTINE", "Non-Routine"),
        ("NEW_PROCESS", "New Process"),
        ("REVIEW", "Review"),
        ("INCIDENT_REVIEW", "Incident Review"),
    ]
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("UNDER_REVIEW", "Under Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    hira_number = models.CharField(max_length=50, unique=True, editable=False)
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="hira_assessments")
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="hira_assessments",
    )
    module = models.ForeignKey(HIRAModule, on_delete=models.PROTECT, related_name="assessments")
    process = models.CharField(max_length=200)
    assessment_date = models.DateField(default=timezone.now)
    assessment_type = models.CharField(
        max_length=30,
        choices=ASSESSMENT_TYPE_CHOICES,
        default="ROUTINE",
    )
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hira_prepared",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hira_reviewed",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hira_approved",
    )
    review_date = models.DateField(null=True, blank=True)
    approval_date = models.DateField(null=True, blank=True)
    revision_number = models.PositiveIntegerField(default=0)
    revision_description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    remarks = models.TextField(blank=True)
    source_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hira_source_headers",
    )
    source_object_id = models.PositiveIntegerField(null=True, blank=True)
    source_record = GenericForeignKey("source_content_type", "source_object_id")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hira_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-assessment_date", "-created_at"]
        verbose_name = "HIRA"
        verbose_name_plural = "HIRAs"

    def __str__(self):
        return self.hira_number

    def save(self, *args, **kwargs):
        if not self.hira_number:
            today = datetime.date.today()
            plant_code = self.plant.code if self.plant else "XXX"
            prefix = f"HIRA-{plant_code}-{today:%Y%m%d}"
            count = HIRA.objects.filter(hira_number__startswith=prefix).count()
            self.hira_number = f"{prefix}-{count + 1:03d}"
        super().save(*args, **kwargs)

    @property
    def highest_initial_risk_level(self):
        levels = ["", "Low", "Medium", "High", "Critical"]
        highest = ""
        for hazard in self.hazards.all():
            if levels.index(hazard.initial_risk_level) > levels.index(highest):
                highest = hazard.initial_risk_level
        return highest


class HIRAHazard(models.Model):
    HAZARD_CATEGORY_CHOICES = [
        ("Mechanical", "Mechanical"),
        ("Electrical", "Electrical"),
        ("Chemical", "Chemical"),
        ("Physical", "Physical"),
        ("Fire / Explosion", "Fire / Explosion"),
        ("Ergonomic", "Ergonomic"),
        ("Biological", "Biological"),
        ("Vehicle", "Vehicle"),
        ("Environmental", "Environmental"),
        ("Other", "Other"),
    ]
    CONTROL_HIERARCHY_CHOICES = [
        ("Elimination", "Elimination"),
        ("Substitution", "Substitution"),
        ("Engineering Control", "Engineering Control"),
        ("Administrative Control", "Administrative Control"),
        ("PPE", "PPE"),
    ]

    hira = models.ForeignKey(HIRA, on_delete=models.CASCADE, related_name="hazards")
    master_rule = models.ForeignKey(
        HazardRiskMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hira_hazards",
    )
    master_snapshot = models.JSONField(default=dict, blank=True)
    activity = models.CharField(max_length=250)
    hazard = models.TextField()
    hazard_category = models.CharField(max_length=50, choices=HAZARD_CATEGORY_CHOICES)
    unsafe_act = models.TextField(blank=True)
    unsafe_condition = models.TextField(blank=True)
    potential_consequence = models.TextField()
    persons_exposed = models.CharField(max_length=250, blank=True)
    existing_controls = models.TextField(blank=True)
    control_hierarchy = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-separated hierarchy of controls.",
    )
    likelihood = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    severity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    initial_risk_score = models.PositiveSmallIntegerField(editable=False, default=0)
    initial_risk_level = models.CharField(max_length=20, editable=False, blank=True)
    additional_controls = models.TextField(blank=True)
    additional_control_hierarchy = models.CharField(max_length=255, blank=True)
    action_required = models.BooleanField(default=False)
    responsible_person = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hira_hazard_responsibilities",
    )
    target_date = models.DateField(null=True, blank=True)
    residual_likelihood = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    residual_severity = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    residual_risk_score = models.PositiveSmallIntegerField(editable=False, default=0)
    residual_risk_level = models.CharField(max_length=20, editable=False, blank=True)
    related_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_record = GenericForeignKey("related_content_type", "related_object_id")
    evidence_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "HIRA Hazard"
        verbose_name_plural = "HIRA Hazards"

    def __str__(self):
        return f"{self.hira.hira_number} - {self.activity}"

    def save(self, *args, **kwargs):
        if self.master_rule_id and not self.master_snapshot:
            self.master_snapshot = self.master_rule.snapshot()
        self.initial_risk_score = calculate_risk_score(self.likelihood, self.severity)
        self.initial_risk_level = risk_level_for_score(self.initial_risk_score)
        self.residual_risk_score = calculate_risk_score(self.residual_likelihood, self.residual_severity)
        self.residual_risk_level = risk_level_for_score(self.residual_risk_score)
        super().save(*args, **kwargs)
        if self.action_required and self.additional_controls and not self.actions.exists():
            HIRAAction.objects.create(
                hazard=self,
                action_description=self.additional_controls,
                responsible_person=self.responsible_person,
                target_date=self.target_date,
                priority=self.initial_risk_level or "Medium",
            )


class HIRAAction(models.Model):
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("OVERDUE", "Overdue"),
        ("VERIFIED", "Verified"),
        ("CLOSED", "Closed"),
    ]
    PRIORITY_CHOICES = [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
        ("Critical", "Critical"),
    ]

    action_id = models.CharField(max_length=50, unique=True, editable=False)
    hazard = models.ForeignKey(HIRAHazard, on_delete=models.CASCADE, related_name="actions")
    action_description = models.TextField()
    responsible_person = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hira_actions",
    )
    target_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="Medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="OPEN")
    completion_date = models.DateField(null=True, blank=True)
    verification = models.TextField(blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hira_verified_actions",
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["target_date", "id"]
        verbose_name = "HIRA Action"
        verbose_name_plural = "HIRA Actions"

    def __str__(self):
        return self.action_id

    def save(self, *args, **kwargs):
        if not self.action_id:
            year = datetime.date.today().year
            prefix = f"HIRA-ACT-{year}"
            count = HIRAAction.objects.filter(action_id__startswith=prefix).count()
            self.action_id = f"{prefix}-{count + 1:04d}"
        if self.status in {"COMPLETED", "VERIFIED", "CLOSED"} and not self.completion_date:
            self.completion_date = timezone.now().date()
        super().save(*args, **kwargs)
