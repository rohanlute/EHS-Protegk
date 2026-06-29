import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.organizations.models import Department, Location, Plant, SubLocation, Zone


class EmergencyTopic(models.Model):
    CATEGORY_CHOICES = [
        ("FIRE_EMERGENCIES", "Fire emergencies"),
        ("CHEMICAL_SPILLS", "Chemical spills"),
        ("GAS_LEAKAGE", "Gas leakage"),
        ("ELECTRICAL_ACCIDENTS", "Electrical accidents"),
        ("MEDICAL_EMERGENCIES", "Medical emergencies"),
        ("NATURAL_DISASTERS", "Natural disasters"),
        ("EXPLOSION_INCIDENTS", "Explosion incidents"),
        ("EVACUATION_SITUATIONS", "Evacuation situations"),
    ]

    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text="Short code e.g. FIRE-01")
    description = models.TextField(blank=True)
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES)
    validity_period_days = models.PositiveIntegerField(
        default=365,
        help_text="After this many days, the drill certificate expires.",
    )
    passing_score = models.PositiveIntegerField(
        default=70,
        help_text="Minimum score (%) required to pass assessment. Set 0 if no assessment.",
    )
    is_mandatory = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="emergency_topics_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Emergency Topic"
        verbose_name_plural = "Emergency Topics"

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def active_questions_count(self):
        return self.questions.filter(is_active=True).count()


class EmergencySession(models.Model):
    STATUS_CHOICES = [
        ("SCHEDULED", "Scheduled"),
        ("ONGOING", "Ongoing"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    DRILL_TYPE_CHOICES = [
        ("FIRE_DRILL", "Fire Drill"),
        ("EVACUATION_DRILL", "Evacuation Drill"),
        ("CHEMICAL_SPILL_DRILL", "Chemical Spill Drill"),
        ("GAS_LEAKAGE_DRILL", "Gas Leakage Drill"),
        ("MEDICAL_EMERGENCY_DRILL", "Medical Emergency Drill"),
        ("EARTHQUAKE_DRILL", "Earthquake Drill"),
        ("RESCUE_DRILL", "Rescue Drill"),
        ("ELECTRICAL_EMERGENCY_DRILL", "Electrical Emergency Drill"),
    ]

    DRILL_CATEGORY_MAP = {
        "FIRE_DRILL": "Fire Safety",
        "EVACUATION_DRILL": "Safety",
        "CHEMICAL_SPILL_DRILL": "Chemical",
        "GAS_LEAKAGE_DRILL": "Chemical",
        "MEDICAL_EMERGENCY_DRILL": "Medical",
        "EARTHQUAKE_DRILL": "Natural Disaster",
        "RESCUE_DRILL": "Rescue",
        "ELECTRICAL_EMERGENCY_DRILL": "Electrical",
    }

    session_number = models.CharField(max_length=50, unique=True, editable=False)
    topic = models.ForeignKey(EmergencyTopic, on_delete=models.CASCADE, related_name="sessions")
    drill_type = models.CharField(max_length=40, choices=DRILL_TYPE_CHOICES)
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="emergency_sessions")
    zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_sessions",
    )
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="emergency_sessions")
    sublocation = models.ForeignKey(
        SubLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_sessions",
    )
    venue_details = models.CharField(max_length=255, blank=True)
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    duration_hours = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    agenda = models.TextField(blank=True)
    max_participants = models.PositiveIntegerField(default=30)
    remarks = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="emergency_materials/%Y/%m/",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SCHEDULED")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_sessions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_date", "-scheduled_time"]
        verbose_name = "Emergency Session"
        verbose_name_plural = "Emergency Sessions"

    def __str__(self):
        return f"{self.session_number} - {self.topic.name}"

    def save(self, *args, **kwargs):
        if not self.session_number:
            today = datetime.date.today()
            date_str = today.strftime("%Y%m%d")
            plant_code = self.plant.code if self.plant else "XXX"
            count = EmergencySession.objects.filter(
                session_number__contains=f"EMG-{plant_code}-{date_str}"
            ).count()
            self.session_number = f"EMG-{plant_code}-{date_str}-{count + 1:03d}"
        super().save(*args, **kwargs)

    @property
    def drill_category(self):
        return self.DRILL_CATEGORY_MAP.get(self.drill_type, "")

    @property
    def is_overdue(self):
        return self.status == "SCHEDULED" and self.scheduled_date < datetime.date.today()

    @property
    def primary_trainer(self):
        return self.trainers.order_by("id").first()

    @property
    def trainer_summary(self):
        trainer_names = [trainer.display_name for trainer in self.trainers.order_by("id")]
        if not trainer_names:
            return "No trainers added"
        if len(trainer_names) == 1:
            return trainer_names[0]
        return f"{trainer_names[0]} +{len(trainer_names) - 1} more"


class EmergencySessionTrainer(models.Model):
    session = models.ForeignKey(
        EmergencySession,
        on_delete=models.CASCADE,
        related_name="trainers",
    )
    trainer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_session_trainer_entries",
    )
    trainer_name = models.CharField(max_length=200)
    trainer_designation = models.CharField(max_length=100, blank=True)
    trainer_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_session_trainers",
    )
    trainer_is_external = models.BooleanField(default=False)
    trainer_organization = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Emergency Session Trainer"
        verbose_name_plural = "Emergency Session Trainers"

    @property
    def display_name(self):
        if self.trainer_user_id:
            return self.trainer_user.get_full_name() or self.trainer_user.username
        return self.trainer_name

    @property
    def display_department(self):
        if self.trainer_user_id and self.trainer_user.department_id:
            return self.trainer_user.department
        return self.trainer_department

    def save(self, *args, **kwargs):
        if self.trainer_user_id:
            self.trainer_name = self.trainer_user.get_full_name() or self.trainer_user.username
            self.trainer_department = self.trainer_user.department
            self.trainer_designation = ""
            self.trainer_is_external = False
            self.trainer_organization = ""
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name


class ERTDepartmentQuestion(models.Model):
    QUESTION_TYPE_CHOICES = [
        ("YES_NO", "Yes/No"),
        ("TEXT", "Text Input"),
        ("NUMBER", "Numeric Input"),
        ("RATING", "Rating (1-5)"),
    ]

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="ert_questions",
        verbose_name="Department",
    )
    topics = models.ManyToManyField(
        EmergencyTopic,
        blank=True,
        related_name="questions",
        verbose_name="Applicable Topics",
        help_text="Questions will be assigned only for the selected emergency topics.",
    )
    question_text = models.TextField(
        verbose_name="Question Text",
        help_text="The actual ERT question",
    )
    question_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Question Code",
        help_text="Unique identifier like SAF-001",
    )
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default="YES_NO",
        verbose_name="Question Type",
    )
    is_remarks_mandatory = models.BooleanField(default=True, verbose_name="Remarks Mandatory")
    is_photo_required = models.BooleanField(default=False, verbose_name="Photo Required")
    is_critical = models.BooleanField(default=False, verbose_name="Critical Question")
    auto_generate_finding = models.BooleanField(default=True, verbose_name="Auto-Generate Finding")
    weightage = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    reference_standard = models.CharField(max_length=200, blank=True, null=True)
    guidance_notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Active Status")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_ert_questions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_ert_questions",
    )

    class Meta:
        ordering = ["department", "question_code"]
        verbose_name = "ERT Department Question"
        verbose_name_plural = "ERT Department Questions"
        indexes = [
            models.Index(fields=["department", "is_active"]),
            models.Index(fields=["question_code"]),
        ]

    def __str__(self):
        return f"{self.question_code} - {self.question_text[:50]}"

    def save(self, *args, **kwargs):
        if not self.question_code:
            self.question_code = self.generate_question_code()
        super().save(*args, **kwargs)

    def generate_question_code(self):
        department_code = self.department.code
        last_question = ERTDepartmentQuestion.objects.filter(
            department=self.department,
            question_code__startswith=department_code,
        ).order_by("-question_code").first()

        if last_question:
            try:
                last_num = int(last_question.question_code.split("-")[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1

        return f"{department_code}-{new_num:03d}"


class EmergencySessionParticipant(models.Model):
    STATUS_CHOICES = [
        ("ASSIGNED", "Assigned"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    session = models.ForeignKey(
        EmergencySession,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_session_participations",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ASSIGNED")
    assigned_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_emergency_session_participants",
    )

    class Meta:
        ordering = ["employee__first_name", "employee__last_name"]
        unique_together = ("session", "employee")
        verbose_name = "Emergency Session Participant"
        verbose_name_plural = "Emergency Session Participants"

    def __str__(self):
        return f"{self.session.session_number} - {self.employee.get_full_name()}"

    @property
    def has_submission(self):
        try:
            return self.submission_id is not None
        except AttributeError:
            try:
                self.submission
                return True
            except EmergencySessionSubmission.DoesNotExist:
                return False


class EmergencySessionQuestionAssignment(models.Model):
    participant = models.ForeignKey(
        EmergencySessionParticipant,
        on_delete=models.CASCADE,
        related_name="question_assignments",
    )
    question = models.ForeignKey(
        ERTDepartmentQuestion,
        on_delete=models.CASCADE,
        related_name="session_assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["question__department__name", "question__question_code"]
        unique_together = ("participant", "question")
        verbose_name = "Emergency Session Question Assignment"
        verbose_name_plural = "Emergency Session Question Assignments"

    def __str__(self):
        return f"{self.participant} - {self.question.question_code}"


class EmergencySessionSubmission(models.Model):
    REVIEW_STATUS_CHOICES = [
        ("PENDING", "Pending Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    participant = models.OneToOneField(
        EmergencySessionParticipant,
        on_delete=models.CASCADE,
        related_name="submission",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_session_submissions",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    compliance_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    overall_remarks = models.TextField(blank=True)
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS_CHOICES, default="PENDING")
    reviewer_remarks = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_emergency_session_submissions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "Emergency Session Submission"
        verbose_name_plural = "Emergency Session Submissions"

    def __str__(self):
        return f"Submission for {self.participant}"

    def calculate_compliance_score(self):
        responses = self.responses.all()
        total_questions = responses.count()
        if total_questions == 0:
            return 0

        positive_answers = responses.filter(answer__in=["Yes", "4", "5"]).count()
        return round((positive_answers / total_questions) * 100, 2)


class EmergencySessionResponse(models.Model):
    submission = models.ForeignKey(
        EmergencySessionSubmission,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    assignment = models.ForeignKey(
        EmergencySessionQuestionAssignment,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    question = models.ForeignKey(
        ERTDepartmentQuestion,
        on_delete=models.CASCADE,
        related_name="session_responses",
    )
    answer = models.CharField(max_length=100)
    remarks = models.TextField(blank=True)
    photo = models.ImageField(upload_to="emergency_responses/", blank=True, null=True)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["question__department__name", "question__question_code"]
        unique_together = ("submission", "assignment")
        verbose_name = "Emergency Session Response"
        verbose_name_plural = "Emergency Session Responses"

    def __str__(self):
        return f"{self.question.question_code} - {self.answer}"


class EmergencyReport(models.Model):
    EMERGENCY_TYPE_CHOICES = [
        ("FIRE", "Fire"),
        ("CHEMICAL_SPILL", "Chemical Spill"),
        ("GAS_LEAK", "Gas Leak"),
        ("ELECTRICAL", "Electrical"),
        ("MEDICAL", "Medical"),
        ("EXPLOSION", "Explosion"),
        ("NATURAL_DISASTER", "Natural Disaster"),
        ("OTHER", "Other"),
    ]

    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    STATUS_CHOICES = [
        ("REPORTED", "Reported"),
        ("ACTION_PENDING", "Action Pending"),
        ("ACTION_PERFORMED", "Action Performed"),
        ("INVESTIGATION_COMPLETED", "Investigation Completed"),
        ("CLOSED", "Closed"),
    ]

    report_number = models.CharField(max_length=50, unique=True, editable=False)
    emergency_title = models.CharField(max_length=255)
    emergency_type = models.CharField(max_length=30, choices=EMERGENCY_TYPE_CHOICES)
    other_emergency_type = models.CharField(max_length=255, blank=True)
    severity_level = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    incident_date = models.DateField()
    incident_time = models.TimeField()
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="emergency_reports")
    zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_reports",
    )
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="emergency_reports")
    sublocation = models.ForeignKey(
        SubLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_reports",
    )
    additional_location_details = models.TextField(blank=True)
    incident_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_emergency_reports",
        verbose_name="Incident Department",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_reports",
    )
    description = models.TextField()
    immediate_actions_taken = models.TextField(blank=True)
    response_team_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_emergency_reports",
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_reports_reported",
    )
    reported_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="REPORTED")
    closure_remarks = models.TextField(blank=True)
    lessons_learned = models.TextField(blank=True)
    preventive_measures = models.TextField(blank=True)
    is_recurrence_possible = models.BooleanField(default=False)
    closure_date = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_emergency_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-incident_date", "-incident_time", "-id"]
        verbose_name = "Emergency Report"
        verbose_name_plural = "Emergency Reports"
        indexes = [
            models.Index(fields=["report_number"]),
            models.Index(fields=["emergency_type"]),
            models.Index(fields=["severity_level"]),
            models.Index(fields=["status"]),
            models.Index(fields=["plant", "location"]),
        ]

    def __str__(self):
        return f"{self.report_number} - {self.emergency_title}"

    def save(self, *args, **kwargs):
        if not self.report_number:
            today = datetime.date.today()
            date_str = today.strftime("%Y%m%d")
            plant_code = self.plant.code if self.plant else "XXX"
            count = EmergencyReport.objects.filter(
                report_number__startswith=f"EMR-{plant_code}-{date_str}"
            ).count()
            self.report_number = f"EMR-{plant_code}-{date_str}-{count + 1:03d}"
        super().save(*args, **kwargs)

    @property
    def severity_badge_class(self):
        severity_classes = {
            "low": "badge-success",
            "medium": "badge-warning",
            "high": "badge-orange",
            "critical": "badge-danger",
        }
        return severity_classes.get(self.severity_level, "badge-secondary")

    @property
    def status_badge_class(self):
        status_classes = {
            "REPORTED": "badge-info",
            "ACTION_PENDING": "badge-warning",
            "ACTION_PERFORMED": "badge-primary",
            "INVESTIGATION_COMPLETED": "badge-success",
            "CLOSED": "badge-secondary",
        }
        return status_classes.get(self.status, "badge-secondary")

    @property
    def active_capas(self):
        return self.capas.exclude(status=EmergencyCAPA.STATUS_CLOSED)

    @property
    def latest_capa(self):
        return self.capas.order_by("-created_at", "-id").first()

    @property
    def can_create_capa(self):
        if self.status == "CLOSED":
            return False, "CAPA creation is blocked after the emergency has been closed."
        if self.status != "INVESTIGATION_COMPLETED" or not hasattr(self, "investigation_report"):
            return False, "CAPA can be created only after the investigation is completed."
        if self.active_capas.exists():
            return False, "An existing CAPA is still open or in progress."
        return True, "CAPA can be created."

    @property
    def can_be_closed(self):
        if self.status == "CLOSED":
            return False, "This emergency is already closed."
        if not hasattr(self, "investigation_report") or self.status != "INVESTIGATION_COMPLETED":
            return False, "Complete the investigation before closing the emergency."
        if hasattr(self, "action_item") and self.action_item.status != "ACTION_PERFORMED":
            return False, "Complete the emergency action item before closure."
        if self.active_capas.exists():
            return False, "Close all open CAPAs before closing the emergency."
        return True, "Ready for closure."

    @property
    def days_to_close(self):
        if self.closure_date:
            return (self.closure_date.date() - self.incident_date).days
        return None


class EmergencyActionItem(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACTION_PERFORMED", "Action Performed"),
    ]

    report = models.OneToOneField(
        EmergencyReport,
        on_delete=models.CASCADE,
        related_name="action_item",
    )
    action_description = models.TextField()
    assigned_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="emergency_action_items_assigned",
    )
    completed_by_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="emergency_action_items_completed",
    )
    completion_datetime = models.DateTimeField(null=True, blank=True)
    completion_remarks = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="emergency_action_attachments/%Y/%m/",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="PENDING")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_action_items_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Emergency Action Item"
        verbose_name_plural = "Emergency Action Items"

    def __str__(self):
        return f"{self.report.report_number} - Emergency Action Item"

    def save(self, *args, **kwargs):
        has_completed_users = self.pk and self.completed_by_users.exists()
        if has_completed_users:
            self.status = "ACTION_PERFORMED"
            if not self.completion_datetime:
                self.completion_datetime = timezone.now()
        else:
            self.status = "PENDING"
        super().save(*args, **kwargs)

    @property
    def is_completed(self):
        return self.status == "ACTION_PERFORMED"


class EmergencyInvestigationReport(models.Model):
    report = models.OneToOneField(
        EmergencyReport,
        on_delete=models.CASCADE,
        related_name="investigation_report",
    )
    investigation_date = models.DateField()
    investigator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_reports_investigated",
    )
    investigation_team = models.TextField(
        help_text="Enter email(s), separated by commas.",
    )
    sequence_of_events = models.TextField()
    root_cause_analysis = models.TextField()
    evidence_collected = models.TextField(blank=True)
    witness_statements = models.TextField(blank=True)
    immediate_corrective_actions = models.TextField()
    preventive_measures = models.TextField()
    completed_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Emergency Investigation Report"
        verbose_name_plural = "Emergency Investigation Reports"

    def __str__(self):
        return f"Investigation - {self.report.report_number}"

class EmergencyCAPA(models.Model):
    STATUS_OPEN = "OPEN"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_CLOSED, "Closed"),
    ]

    capa_number = models.CharField(max_length=50, unique=True, editable=False)
    report = models.ForeignKey(
        EmergencyReport,
        on_delete=models.CASCADE,
        related_name="capas",
    )
    action_required = models.TextField()
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_capas_assigned",
    )
    target_date = models.DateField()
    action_taken = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    evidence = models.FileField(upload_to="emergency_capa/%Y/%m/", blank=True, null=True)
    closure_remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_capas_created",
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_capas_closed",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Emergency CAPA"
        verbose_name_plural = "Emergency CAPAs"

    def __str__(self):
        return f"{self.capa_number} - {self.report.report_number}"

    def save(self, *args, **kwargs):
        if not self.capa_number:
            today = datetime.date.today()
            date_str = today.strftime("%Y%m%d")
            prefix = f"ECAPA-{date_str}"
            count = EmergencyCAPA.objects.filter(capa_number__startswith=prefix).count()
            self.capa_number = f"{prefix}-{count + 1:03d}"
        super().save(*args, **kwargs)


class EmergencyReportPhoto(models.Model):
    report = models.ForeignKey(
        EmergencyReport,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    photo = models.ImageField(upload_to="emergency_report_photos/%Y/%m/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_report_photos_uploaded",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]
        verbose_name = "Emergency Report Photo"
        verbose_name_plural = "Emergency Report Photos"

    def __str__(self):
        return f"{self.report.report_number} - Photo {self.id}"
