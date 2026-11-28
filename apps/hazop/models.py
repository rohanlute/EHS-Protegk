from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.organizations.models import (
    Plant,
    Zone,
    Location,
    SubLocation,
    Department,
)

class HAZOPConfigBase(models.Model):
    """
    Abstract base model for HAZOP configuration masters.
    """

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    is_system_default = models.BooleanField(
        default=False,
        help_text="Indicates that this record was included as a default configuration."
    )
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created_configs",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)


class HAZOPStudyType(HAZOPConfigBase):
    """
    Types of HAZOP studies.
    Example: Initial Study, Revalidation, MOC Review.
    """

    class Meta:
        ordering = ["name"]
        verbose_name = "HAZOP Study Type"
        verbose_name_plural = "HAZOP Study Types"


class HAZOPStudyStatus(HAZOPConfigBase):
    """
    Configurable study statuses.
    """

    sequence = models.PositiveIntegerField(default=0)

    is_terminal = models.BooleanField(
        default=False,
        help_text="Indicates whether this status represents a completed or closed state."
    )

    class Meta:
        ordering = ["sequence", "name"]
        verbose_name = "HAZOP Study Status"
        verbose_name_plural = "HAZOP Study Statuses"


class HAZOPParameter(HAZOPConfigBase):
    """
    Process parameters used during HAZOP analysis.
    Example: Flow, Pressure, Temperature, Level.
    """

    class Meta:
        ordering = ["name"]
        verbose_name = "HAZOP Parameter"
        verbose_name_plural = "HAZOP Parameters"


class HAZOPGuideWord(HAZOPConfigBase):
    """
    Guide words used to identify deviations.
    Example: No, More, Less, Reverse.
    """

    class Meta:
        ordering = ["name"]
        verbose_name = "HAZOP Guide Word"
        verbose_name_plural = "HAZOP Guide Words"


class HAZOPDeviationTemplate(models.Model):
    """
    Reusable deviation combinations of parameter and guide word.
    """

    code = models.CharField(max_length=50, unique=True)

    parameter = models.ForeignKey(
        HAZOPParameter,
        on_delete=models.PROTECT,
        related_name="deviation_templates",
    )

    guide_word = models.ForeignKey(
        HAZOPGuideWord,
        on_delete=models.PROTECT,
        related_name="deviation_templates",
    )

    deviation_text = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    is_system_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_hazop_deviation_templates",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["parameter__name", "guide_word__name"]
        verbose_name = "HAZOP Deviation Template"
        verbose_name_plural = "HAZOP Deviation Templates"

        constraints = [
            models.UniqueConstraint(
                fields=["parameter", "guide_word"],
                name="unique_hazop_parameter_guideword",
            )
        ]

    def __str__(self):
        return self.deviation_text

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        if self.deviation_text:
            self.deviation_text = self.deviation_text.strip()
        super().save(*args, **kwargs)



# ============================================================
# HAZOP CONFIGURATION MASTER MODELS
# ============================================================


class HAZOPStudyMethodology(HAZOPConfigBase):
    """
    Study methodology master.
    Example: IEC 61882, What-If, Checklist.
    """

    class Meta:
        verbose_name = "HAZOP Study Methodology"
        verbose_name_plural = "HAZOP Study Methodologies"
        ordering = ["name"]


class HAZOPStudyPriority(HAZOPConfigBase):
    """
    Study priority master.
    """

    priority_order = models.PositiveSmallIntegerField(
        default=1,
        help_text="Lower number represents higher priority."
    )

    class Meta:
        verbose_name = "HAZOP Study Priority"
        verbose_name_plural = "HAZOP Study Priorities"
        ordering = ["priority_order", "name"]


class HAZOPProcessType(HAZOPConfigBase):
    """
    Process type master.
    Example: Chemical, Manufacturing, Utilities.
    """

    class Meta:
        verbose_name = "HAZOP Process Type"
        verbose_name_plural = "HAZOP Process Types"
        ordering = ["name"]


class HAZOPNodeType(HAZOPConfigBase):
    """
    Node type master.
    Example: Process Line, Equipment, Storage Tank.
    """

    class Meta:
        verbose_name = "HAZOP Node Type"
        verbose_name_plural = "HAZOP Node Types"
        ordering = ["name"]


class HAZOPEquipmentType(HAZOPConfigBase):
    """
    Equipment type master.
    Example: Pump, Valve, Reactor, Compressor.
    """

    class Meta:
        verbose_name = "HAZOP Equipment Type"
        verbose_name_plural = "HAZOP Equipment Types"
        ordering = ["name"]


class HAZOPCauseCategory(HAZOPConfigBase):
    """
    Cause category master.
    """

    class Meta:
        verbose_name = "HAZOP Cause Category"
        verbose_name_plural = "HAZOP Cause Categories"
        ordering = ["name"]


class HAZOPConsequenceCategory(HAZOPConfigBase):
    """
    Consequence category master.
    """

    class Meta:
        verbose_name = "HAZOP Consequence Category"
        verbose_name_plural = "HAZOP Consequence Categories"
        ordering = ["name"]


class HAZOPSafeguardCategory(HAZOPConfigBase):
    """
    Safeguard category master.
    """

    class Meta:
        verbose_name = "HAZOP Safeguard Category"
        verbose_name_plural = "HAZOP Safeguard Categories"
        ordering = ["name"]


class HAZOPRecommendationCategory(HAZOPConfigBase):
    """
    Recommendation category master.
    """

    class Meta:
        verbose_name = "HAZOP Recommendation Category"
        verbose_name_plural = "HAZOP Recommendation Categories"
        ordering = ["name"]



class HAZOPAction(models.Model):
    """
    Action assigned to implement a HAZOP recommendation.
    One recommendation can have multiple actions.
    """

    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("SUBMITTED_FOR_VERIFICATION", "Submitted for Verification"),
        ("VERIFIED", "Verified"),
        ("REOPENED", "Reopened"),
        ("CANCELLED", "Cancelled"),
    ]

    PRIORITY_CHOICES = [
        ("CRITICAL", "Critical"),
        ("HIGH", "High"),
        ("MEDIUM", "Medium"),
        ("LOW", "Low"),
    ]

    # Action identification
    action_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        editable=False,
    )

    recommendation = models.ForeignKey(
        "HAZOPRecommendation",
        on_delete=models.CASCADE,
        related_name="actions",
    )

    action_description = models.TextField()

    # Assignment
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hazop_actions",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_actions_assigned",
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="MEDIUM",
    )

    due_date = models.DateField()

    # Action progress
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="OPEN",
    )

    completion_remarks = models.TextField(blank=True)

    evidence = models.FileField(
        upload_to="hazop/action_evidence/%Y/%m/",
        null=True,
        blank=True,
    )

    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_actions_completed",
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Verification
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_actions_verified",
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    verification_remarks = models.TextField(blank=True)

    # Record control
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_actions_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "created_at"]
        verbose_name = "HAZOP Action"
        verbose_name_plural = "HAZOP Actions"

    def __str__(self):
        return f"{self.action_number} - {self.action_description[:80]}"

    def save(self, *args, **kwargs):
        if not self.action_number:
            super().save(*args, **kwargs)

            self.action_number = f"HAZOP-ACT-{self.pk:05d}"

            super().save(update_fields=["action_number"])
            return

        super().save(*args, **kwargs)




class HAZOPSeverity(HAZOPConfigBase):
    """
    Severity rating master.
    """

    severity_score = models.PositiveSmallIntegerField(
        unique=True,
        help_text="Numeric severity score used in risk assessment."
    )

    class Meta:
        verbose_name = "HAZOP Severity"
        verbose_name_plural = "HAZOP Severity Levels"
        ordering = ["severity_score"]


class HAZOPLikelihood(HAZOPConfigBase):
    """
    Likelihood rating master.
    """

    likelihood_score = models.PositiveSmallIntegerField(
        unique=True,
        help_text="Numeric likelihood score used in risk assessment."
    )

    class Meta:
        verbose_name = "HAZOP Likelihood"
        verbose_name_plural = "HAZOP Likelihood Levels"
        ordering = ["likelihood_score"]


class HAZOPReviewFrequency(HAZOPConfigBase):
    """
    Study review frequency master.
    """

    interval_days = models.PositiveIntegerField(
        default=365,
        help_text="Review interval in days."
    )

    class Meta:
        verbose_name = "HAZOP Review Frequency"
        verbose_name_plural = "HAZOP Review Frequencies"
        ordering = ["interval_days"]


class HAZOPParameterGuideWordMapping(models.Model):
    """
    Defines which guidewords can be used with each parameter.
    """

    parameter = models.ForeignKey(
        HAZOPParameter,
        on_delete=models.PROTECT,
        related_name="guideword_mappings"
    )

    guide_word = models.ForeignKey(
        HAZOPGuideWord,
        on_delete=models.PROTECT,
        related_name="parameter_mappings"
    )

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_hazop_parameter_guideword_mappings"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Parameter-Guideword Mapping"
        verbose_name_plural = "Parameter-Guideword Mappings"
        ordering = ["parameter__name", "guide_word__name"]

        constraints = [
            models.UniqueConstraint(
                fields=["parameter", "guide_word"],
                name="unique_hazop_parameter_guideword_mapping"
            )
        ]

    def __str__(self):
        return f"{self.parameter.name} - {self.guide_word.name}"
    




# ============================================================
# HAZOP STUDY REGISTER
# ============================================================


class HAZOPStudy(models.Model):
    """
    Main HAZOP Study Register.

    Stores study details, organization hierarchy, study team,
    planning dates, scope and workflow status.
    """

    # --------------------------------------------------------
    # STUDY IDENTIFICATION
    # --------------------------------------------------------

    study_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        db_index=True,
    )

    study_title = models.CharField(
        max_length=255,
    )

    study_type = models.ForeignKey(
        HAZOPStudyType,
        on_delete=models.PROTECT,
        related_name="studies",
    )

    methodology = models.ForeignKey(
        HAZOPStudyMethodology,
        on_delete=models.PROTECT,
        related_name="studies",
    )

    process_type = models.ForeignKey(
        HAZOPProcessType,
        on_delete=models.PROTECT,
        related_name="studies",
    )

    priority = models.ForeignKey(
        HAZOPStudyPriority,
        on_delete=models.PROTECT,
        related_name="studies",
    )

    status = models.ForeignKey(
        HAZOPStudyStatus,
        on_delete=models.PROTECT,
        related_name="studies",
        null=True,
        blank=True,
    )

    # --------------------------------------------------------
    # ORGANIZATION HIERARCHY
    # --------------------------------------------------------

    plant = models.ForeignKey(
        Plant,
        on_delete=models.PROTECT,
        related_name="hazop_studies",
    )

    zone = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        related_name="hazop_studies",
        null=True,
        blank=True,
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="hazop_studies",
        null=True,
        blank=True,
    )

    sub_location = models.ForeignKey(
        SubLocation,
        on_delete=models.PROTECT,
        related_name="hazop_studies",
        null=True,
        blank=True,
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="hazop_studies",
        null=True,
        blank=True,
    )

    # --------------------------------------------------------
    # STUDY TEAM
    # --------------------------------------------------------

    study_leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hazop_studies_led",
    )

    team_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="hazop_studies",
        blank=True,
    )

    # --------------------------------------------------------
    # PLANNING AND SCHEDULE
    # --------------------------------------------------------

    planned_start_date = models.DateField(
        null=True,
        blank=True,
    )

    planned_end_date = models.DateField(
        null=True,
        blank=True,
    )

    actual_start_date = models.DateField(
        null=True,
        blank=True,
    )

    actual_end_date = models.DateField(
        null=True,
        blank=True,
    )

    review_frequency = models.ForeignKey(
        HAZOPReviewFrequency,
        on_delete=models.PROTECT,
        related_name="studies",
        null=True,
        blank=True,
    )

    next_review_date = models.DateField(
        null=True,
        blank=True,
    )

    # --------------------------------------------------------
    # STUDY DESCRIPTION
    # --------------------------------------------------------

    study_scope = models.TextField(
        blank=True,
        help_text="Define the process boundaries and scope of the study.",
    )

    study_objective = models.TextField(
        blank=True,
    )

    reference_documents = models.TextField(
        blank=True,
        help_text="List P&IDs, process documents and other references.",
    )

    remarks = models.TextField(
        blank=True,
    )

    # --------------------------------------------------------
    # RECORD CONTROL
    # --------------------------------------------------------

    is_active = models.BooleanField(
        default=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_studies_created",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_studies_updated",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # --------------------------------------------------------
    # MODEL OPTIONS
    # --------------------------------------------------------

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "HAZOP Study"
        verbose_name_plural = "HAZOP Studies"

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    def __str__(self):
        return f"{self.study_number} - {self.study_title}"

    # --------------------------------------------------------
    # STUDY NUMBER GENERATION
    # --------------------------------------------------------

    @classmethod
    def generate_study_number(cls):
        """
        Generate study number in the format:
        HAZOP-2026-0001
        """

        year = timezone.localdate().year
        prefix = f"HAZOP-{year}-"

        last_study = (
            cls.objects
            .filter(study_number__startswith=prefix)
            .order_by("-study_number")
            .first()
        )

        if last_study:
            try:
                last_number = int(
                    last_study.study_number.split("-")[-1]
                )
            except (ValueError, IndexError):
                last_number = 0
        else:
            last_number = 0

        next_number = last_number + 1

        return f"{prefix}{next_number:04d}"

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    def clean(self):
        super().clean()

        errors = {}

        # Validate planned dates
        if (
            self.planned_start_date
            and self.planned_end_date
            and self.planned_end_date < self.planned_start_date
        ):
            errors["planned_end_date"] = (
                "Planned end date cannot be earlier than planned start date."
            )

        # Validate actual dates
        if (
            self.actual_start_date
            and self.actual_end_date
            and self.actual_end_date < self.actual_start_date
        ):
            errors["actual_end_date"] = (
                "Actual end date cannot be earlier than actual start date."
            )

        # Validate actual dates against planned dates
        if (
            self.planned_start_date
            and self.actual_start_date
            and self.actual_start_date < self.planned_start_date
        ):
            errors["actual_start_date"] = (
                "Actual start date cannot be earlier than planned start date."
            )

        # Validate organization hierarchy

        # Zone must belong to the selected plant
        if self.zone:
            if not self.plant:
                errors["plant"] = (
                    "Please select a plant when selecting a zone."
                )
            elif self.zone.plant_id != self.plant_id:
                errors["zone"] = (
                    "Selected zone does not belong to the selected plant."
                )


        # Location must belong to the selected zone
        if self.location:
            if not self.zone:
                errors["zone"] = (
                    "Please select a zone when selecting a location."
                )
            elif self.location.zone_id != self.zone_id:
                errors["location"] = (
                    "Selected location does not belong to the selected zone."
                )


        # Sub-location must belong to the selected location
        if self.sub_location:
            if not self.location:
                errors["location"] = (
                    "Please select a location when selecting a sub-location."
                )
            elif self.sub_location.location_id != self.location_id:
                errors["sub_location"] = (
                    "Selected sub-location does not belong to the selected location."
                )

        if errors:
            raise ValidationError(errors)

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    def save(self, *args, **kwargs):
        if not self.study_number:
            self.study_number = self.generate_study_number()

        if self.study_title:
            self.study_title = self.study_title.strip()

        super().save(*args, **kwargs)





# ============================================================
# HAZOP NODE REGISTER
# ============================================================

class HAZOPNode(models.Model):
    """
    A process node within a HAZOP study.

    Example:
    Study: HAZOP-2026-0001
    Node: HAZOP-2026-0001-N001
    """

    study = models.ForeignKey(
        HAZOPStudy,
        on_delete=models.CASCADE,
        related_name="nodes",
    )

    node_number = models.CharField(
        max_length=80,
        editable=False,
        db_index=True,
    )

    node_name = models.CharField(
        max_length=200,
        verbose_name="Node Name",
    )

    node_type = models.ForeignKey(
        HAZOPNodeType,
        on_delete=models.PROTECT,
        related_name="hazop_nodes",
    )

    equipment_type = models.ForeignKey(
        HAZOPEquipmentType,
        on_delete=models.PROTECT,
        related_name="hazop_nodes",
        null=True,
        blank=True,
    )

    equipment_tag = models.CharField(
        max_length=100,
        blank=True,
        help_text="Equipment or process tag, for example P-101 or V-201.",
    )

    description = models.TextField(
        blank=True,
        help_text="Brief description of the process node.",
    )

    design_intent = models.TextField(
        blank=True,
        help_text="What the process node is intended to do.",
    )

    operating_conditions = models.TextField(
        blank=True,
        help_text="Normal operating pressure, temperature, flow or other conditions.",
    )

    drawing_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="P&ID or drawing reference for this node.",
    )

    boundary_description = models.TextField(
        blank=True,
        help_text="Define the inlet, outlet and boundaries of the node.",
    )

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_nodes_created",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_nodes_updated",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "HAZOP Node"
        verbose_name_plural = "HAZOP Nodes"

        constraints = [
            models.UniqueConstraint(
                fields=["study", "node_number"],
                name="unique_hazop_node_number_per_study",
            ),
        ]

    def __str__(self):
        return f"{self.node_number} - {self.node_name}"

    def save(self, *args, **kwargs):
        if not self.node_number and self.study_id:
            with transaction.atomic():
                # Lock the study row while generating the next node number.
                study = (
                    HAZOPStudy.objects
                    .select_for_update()
                    .get(pk=self.study_id)
                )

                existing_count = HAZOPNode.objects.filter(
                    study_id=self.study_id
                ).count()

                next_number = existing_count + 1

                self.node_number = (
                    f"{study.study_number}-N{next_number:03d}"
                )

                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)




# ============================================================
# HAZOP WORKSHEET ENTRY
# ============================================================

class HAZOPWorksheetEntry(models.Model):
    """
    One deviation analysis row in a HAZOP node worksheet.
    """

    node = models.ForeignKey(
        HAZOPNode,
        on_delete=models.CASCADE,
        related_name="worksheet_entries",
    )

    entry_number = models.PositiveIntegerField(
        editable=False,
    )

    parameter = models.ForeignKey(
        HAZOPParameter,
        on_delete=models.PROTECT,
        related_name="hazop_worksheet_entries",
    )

    guide_word = models.ForeignKey(
        HAZOPGuideWord,
        on_delete=models.PROTECT,
        related_name="hazop_worksheet_entries",
    )

    deviation_template = models.ForeignKey(
        HAZOPDeviationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="worksheet_entries",
    )

    deviation_description = models.TextField()

    possible_causes = models.TextField(
        blank=True,
        help_text="Describe possible causes of the deviation."
    )

    operating_condition = models.CharField(
        max_length=100,
        blank=True,
        help_text="For example: Normal, Startup, Shutdown or Maintenance",
    )

    # Initial risk assessment
    initial_severity = models.ForeignKey(
        HAZOPSeverity,
        on_delete=models.PROTECT,
        related_name="initial_hazop_entries",
    )

    initial_likelihood = models.ForeignKey(
        HAZOPLikelihood,
        on_delete=models.PROTECT,
        related_name="initial_hazop_entries",
    )

    # Residual risk after safeguards and recommendations
    residual_severity = models.ForeignKey(
        HAZOPSeverity,
        on_delete=models.PROTECT,
        related_name="residual_hazop_entries",
        null=True,
        blank=True,
    )

    residual_likelihood = models.ForeignKey(
        HAZOPLikelihood,
        on_delete=models.PROTECT,
        related_name="residual_hazop_entries",
        null=True,
        blank=True,
    )

    remarks = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_entries_created",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_entries_updated",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["node", "entry_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["node", "entry_number"],
                name="unique_hazop_entry_number_per_node",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.entry_number and self.node_id:
            with transaction.atomic():
                HAZOPNode.objects.select_for_update().get(
                    pk=self.node_id
                )

                last_entry = (
                    HAZOPWorksheetEntry.objects
                    .filter(node_id=self.node_id)
                    .order_by("-entry_number")
                    .first()
                )

                self.entry_number = (
                    last_entry.entry_number + 1
                    if last_entry else 1
                )

                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    @property
    def initial_risk_score(self):
        return (
            self.initial_severity.severity_score
            * self.initial_likelihood.likelihood_score
        )

    @property
    def residual_risk_score(self):
        if not self.residual_severity or not self.residual_likelihood:
            return None

        return (
            self.residual_severity.severity_score
            * self.residual_likelihood.likelihood_score
        )

    def __str__(self):
        return (
            f"{self.node.node_number} - "
            f"Entry {self.entry_number}"
        )


# ============================================================
# HAZOP CAUSE
# ============================================================

class HAZOPCause(models.Model):
    worksheet_entry = models.ForeignKey(
        HAZOPWorksheetEntry,
        on_delete=models.CASCADE,
        related_name="causes",
    )

    category = models.ForeignKey(
        HAZOPCauseCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hazop_causes",
    )

    cause_description = models.TextField()

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_causes_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.cause_description[:100]


# ============================================================
# HAZOP CONSEQUENCE
# ============================================================

class HAZOPConsequence(models.Model):
    worksheet_entry = models.ForeignKey(
        HAZOPWorksheetEntry,
        on_delete=models.CASCADE,
        related_name="consequences",
    )

    category = models.ForeignKey(
        HAZOPConsequenceCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hazop_consequences",
    )

    consequence_description = models.TextField()

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_consequences_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.consequence_description[:100]


# ============================================================
# HAZOP SAFEGUARD
# ============================================================

class HAZOPSafeguard(models.Model):
    worksheet_entry = models.ForeignKey(
        HAZOPWorksheetEntry,
        on_delete=models.CASCADE,
        related_name="safeguards",
    )

    category = models.ForeignKey(
        HAZOPSafeguardCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hazop_safeguards",
    )

    safeguard_description = models.TextField()

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_safeguards_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.safeguard_description[:100]


# ============================================================
# HAZOP RECOMMENDATION
# ============================================================

class HAZOPRecommendation(models.Model):
    worksheet_entry = models.ForeignKey(
        HAZOPWorksheetEntry,
        on_delete=models.CASCADE,
        related_name="recommendations",
    )

    category = models.ForeignKey(
        HAZOPRecommendationCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hazop_recommendations",
    )

    recommendation_description = models.TextField()

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_recommendations_assigned",
    )

    target_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        default="Open",
        choices=[
            ("Open", "Open"),
            ("In Progress", "In Progress"),
            ("Completed", "Completed"),
            ("Cancelled", "Cancelled"),
        ],
    )

    completion_remarks = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_recommendations_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["target_date", "created_at"]

    def __str__(self):
        return self.recommendation_description[:100]




class HAZOPRiskLevel(models.Model):
    """
    Risk level configuration.
    Example: Low, Medium, High, Extreme.
    """

    name = models.CharField(max_length=50, unique=True)
    minimum_score = models.PositiveIntegerField()
    maximum_score = models.PositiveIntegerField()

    color = models.CharField(
        max_length=20,
        default="#198754",
        help_text="Hex color for displaying this risk level."
    )

    requires_action = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["minimum_score"]
        verbose_name = "HAZOP Risk Level"
        verbose_name_plural = "HAZOP Risk Levels"

    def __str__(self):
        return f"{self.name} ({self.minimum_score}-{self.maximum_score})"


class HAZOPRiskMatrix(models.Model):
    """
    Configurable risk matrix master.
    """

    name = models.CharField(
        max_length=100,
        default="Standard Risk Matrix"
    )

    description = models.TextField(blank=True)

    likelihood_scale = models.PositiveIntegerField(default=5)
    severity_scale = models.PositiveIntegerField(default=5)

    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_hazop_risk_matrices"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "HAZOP Risk Matrix"
        verbose_name_plural = "HAZOP Risk Matrices"

    def __str__(self):
        return self.name


class HAZOPRiskRating(models.Model):
    """
    Likelihood and Severity rating master.
    """

    RATING_TYPE_CHOICES = [
        ("LIKELIHOOD", "Likelihood"),
        ("SEVERITY", "Severity"),
    ]

    matrix = models.ForeignKey(
        HAZOPRiskMatrix,
        on_delete=models.CASCADE,
        related_name="ratings"
    )

    rating_type = models.CharField(
        max_length=20,
        choices=RATING_TYPE_CHOICES
    )

    score = models.PositiveIntegerField()

    name = models.CharField(max_length=100)

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["rating_type", "score"]
        unique_together = [
            ("matrix", "rating_type", "score")
        ]

    def __str__(self):
        return f"{self.rating_type} - {self.score}: {self.name}"


class HAZOPRiskAssessment(models.Model):
    """
    Risk assessment record connected to a HAZOP worksheet entry.
    """

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted for Review"),
        ("UNDER_REVIEW", "Under Review"),
        ("PENDING_APPROVAL", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CLOSED", "Closed"),
    ]

    worksheet_entry = models.ForeignKey(
        "hazop.HAZOPWorksheetEntry",
        on_delete=models.CASCADE,
        related_name="risk_assessments"
    )

    matrix = models.ForeignKey(
        HAZOPRiskMatrix,
        on_delete=models.PROTECT,
        related_name="assessments"
    )

    assessment_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True
    )

    hazard_title = models.CharField(max_length=200)

    hazard_description = models.TextField()

    potential_consequence = models.TextField(blank=True)

    persons_exposed = models.TextField(blank=True)

    existing_controls = models.TextField(blank=True)

    # Initial risk
    initial_likelihood = models.PositiveIntegerField()
    initial_severity = models.PositiveIntegerField()

    # Additional risk control measures
    additional_controls = models.TextField(blank=True)

    control_hierarchy = models.CharField(
        max_length=30,
        choices=[
            ("ELIMINATION", "Elimination"),
            ("SUBSTITUTION", "Substitution"),
            ("ENGINEERING", "Engineering Control"),
            ("ADMINISTRATIVE", "Administrative Control"),
            ("PPE", "Personal Protective Equipment"),
        ],
        blank=True
    )

    action_required = models.BooleanField(default=False)

    action_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_risk_actions"
    )

    action_due_date = models.DateField(null=True, blank=True)

    # Residual risk
    residual_likelihood = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    residual_severity = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT"
    )

    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_risk_assessments"
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_risk_reviews"
    )

    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_risk_approvals"
    )

    
    review_comments = models.TextField(blank=True)

    # Workflow timestamps
    submitted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ["-created_at"]
        verbose_name = "HAZOP Risk Assessment"
        verbose_name_plural = "HAZOP Risk Assessments"

    def __str__(self):
        return self.assessment_number or self.hazard_title

    @property
    def initial_risk_score(self):
        return self.initial_likelihood * self.initial_severity

    @property
    def residual_risk_score(self):
        if (
            self.residual_likelihood is not None
            and self.residual_severity is not None
        ):
            return (
                self.residual_likelihood
                * self.residual_severity
            )

        return None

    def get_risk_level(self, score):
        return HAZOPRiskLevel.objects.filter(
            is_active=True,
            minimum_score__lte=score,
            maximum_score__gte=score
        ).first()

    @property
    def initial_risk_level(self):
        return self.get_risk_level(self.initial_risk_score)

    @property
    def residual_risk_level(self):
        score = self.residual_risk_score

        if score is None:
            return None

        return self.get_risk_level(score)

    def save(self, *args, **kwargs):
        if not self.assessment_number:
            last_assessment = (
                HAZOPRiskAssessment.objects
                .order_by("-id")
                .first()
            )

            next_number = (
                last_assessment.id + 1
                if last_assessment
                else 1
            )

            self.assessment_number = (
                f"HRA-{next_number:05d}"
            )

        super().save(*args, **kwargs)




class HAZOPRiskAssessmentReviewHistory(models.Model):
    """
    Stores workflow actions and review history
    for each HAZOP Risk Assessment.
    """

    ACTION_CHOICES = [
        ("SUBMITTED", "Submitted for Review"),
        ("UNDER_REVIEW", "Review Started"),
        ("REVIEW_SUBMITTED", "Review Submitted to Approver"),
        ("REJECTED", "Rejected"),
        ("APPROVED", "Approved"),
        ("CLOSED", "Closed"),
        ("RESUBMITTED", "Resubmitted"),
    ]

    assessment = models.ForeignKey(
        HAZOPRiskAssessment,
        on_delete=models.CASCADE,
        related_name="review_history"
    )

    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES
    )

    from_status = models.CharField(
        max_length=20,
        blank=True
    )

    to_status = models.CharField(
        max_length=20
    )

    comments = models.TextField(
        blank=True
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_assessment_review_history"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "HAZOP Risk Assessment Review History"
        verbose_name_plural = "HAZOP Risk Assessment Review Histories"

    def __str__(self):
        return (
            f"{self.assessment.assessment_number} - "
            f"{self.get_action_display()}"
        )





class HAZOPActionHistory(models.Model):
    """
    Audit trail for HAZOP Action workflow and progress changes.
    """

    EVENT_CHOICES = [
        ("CREATED", "Action Created"),
        ("UPDATED", "Action Details Updated"),
        ("STARTED", "Action Started"),
        ("PROGRESS_UPDATED", "Progress Updated"),
        ("SUBMITTED", "Submitted for Verification"),
        ("VERIFIED", "Action Verified"),
        ("REOPENED", "Action Reopened"),
    ]

    action = models.ForeignKey(
        HAZOPAction,
        on_delete=models.CASCADE,
        related_name="history",
    )

    event = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES,
    )

    previous_status = models.CharField(
        max_length=30,
        blank=True,
    )

    new_status = models.CharField(
        max_length=30,
        blank=True,
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_action_history",
    )

    remarks = models.TextField(blank=True)

    evidence_name = models.CharField(
        max_length=255,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "HAZOP Action History"
        verbose_name_plural = "HAZOP Action Histories"

    def __str__(self):
        return (
            f"{self.action.action_number} - "
            f"{self.get_event_display()}"
        )





# ============================================================
# HAZOP VERSION CONTROL
# ============================================================

class HAZOPStudyVersion(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("UNDER_REVIEW", "Under Review"),
        ("APPROVED", "Approved"),
        ("SUPERSEDED", "Superseded"),
    ]

    study = models.ForeignKey(
        HAZOPStudy,
        on_delete=models.CASCADE,
        related_name="versions",
    )

    version_number = models.PositiveIntegerField()

    version_title = models.CharField(
        max_length=200,
        blank=True,
    )

    revision_reason = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )

    # Complete read-only snapshot of the study at this version.
    snapshot_data = models.JSONField(
        default=dict,
    )

    # Changes compared with the previous version.
    change_summary = models.JSONField(
        default=list,
        blank=True,
    )

    parent_version = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_versions",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_versions_created",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazop_versions_approved",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["study", "version_number"],
                name="unique_hazop_study_version",
            )
        ]

    def __str__(self):
        return f"{self.study.study_number} - V{self.version_number}"