# apps/five_s/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from apps.accounts.models import User
from apps.organizations.models import Plant, Zone, Location, SubLocation

# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

PILLAR_CHOICES = [
    ('SEIRI',    'Seiri — Sort'),
    ('SEITON',   'Seiton — Set in Order'),
    ('SEISO',    'Seiso — Shine'),
    ('SEIKETSU', 'Seiketsu — Standardize'),
    ('SHITSUKE', 'Shitsuke — Sustain'),
]

FREQUENCY_CHOICES = [
    ('DAILY', 'Daily'),
    ('WEEKLY', 'Weekly'),
    ('MONTHLY', 'Monthly'),
    ('QUARTERLY', 'Quarterly'),
    ('YEARLY', 'Yearly'),
]

# ---------------------------------------------------------------------------
# Stage 1: Master Question Library
# ---------------------------------------------------------------------------

class FiveSQuestion(models.Model):
    """
    Master library of 5S checklist questions.

    NOTE: All questions behave identically during inspection.
      - Rating 1 (Poor) or 2 (Fair) → remarks + photo evidence are MANDATORY
      - Rating 3, 4, 5, or N/A      → remarks + photo evidence are OPTIONAL

    This rule is enforced in AuditAnswer.clean() and AuditAnswer.save().
    There are no per-question settings for remarks/photo requirements.
    """

    question_code = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        verbose_name="Question Code",
        help_text="Auto-generated: Q5S001, Q5S002, …",
    )
    pillar = models.CharField(
        max_length=20,
        choices=PILLAR_CHOICES,
        verbose_name="Pillar",
        db_index=True,
    )
    question_text = models.TextField(
        verbose_name="Question",
        help_text="Phrase as an observable standard, e.g. 'Are tools stored in labelled locations?'",
    )

    reference_standard = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Reference Standard",
        help_text="e.g., OSHA 1910.36, IS 2309",
    )
    guidance_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Guidance Notes",
        help_text="Additional guidance for the inspector on how to evaluate this question.",
    )

    is_active = models.BooleanField(default=True, verbose_name="Active")

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_five_s_questions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'five_s_questions'
        ordering = ['-created_at', '-question_code']
        verbose_name = "5S Question"
        verbose_name_plural = "5S Questions"
        indexes = [
            models.Index(fields=['pillar', 'is_active']),
            models.Index(fields=['question_code']),
        ]

    def __str__(self):
        return f"{self.question_code} — {self.question_text[:60]}"

    def save(self, *args, **kwargs):
        if not self.question_code:
            self.question_code = self.generate_question_code()
        super().save(*args, **kwargs)

    @classmethod
    def generate_question_code(cls):
        prefix = "Q5S"
        last = cls.objects.filter(
            question_code__startswith=prefix
        ).order_by('-question_code').values_list('question_code', flat=True).first()
        if not last:
            return f"{prefix}001"
        try:
            last_num = int(last[len(prefix):])
        except (TypeError, ValueError):
            last_num = 0
        return f"{prefix}{last_num + 1:03d}"


# ---------------------------------------------------------------------------
# Stage 1: Templates
# ---------------------------------------------------------------------------

class FiveSTemplate(models.Model):
    template_name = models.CharField(max_length=200, verbose_name="Template Name")
    template_code = models.CharField(max_length=50, verbose_name="Template Code")
    version = models.PositiveIntegerField(default=1, verbose_name="Version")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    min_compliance_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=80.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Minimum Compliance Score (%)",
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_five_s_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "five_s_templates"
        ordering = ["-created_at"]
        verbose_name = "5S Template"
        verbose_name_plural = "5S Templates"
        constraints = [
            models.UniqueConstraint(
                fields=["template_code", "version"],
                name="uniq_five_s_template_code_version",
            ),
        ]
        indexes = [
            models.Index(fields=["template_code", "version", "is_active"]),
        ]

    def __str__(self):
        return f"{self.template_code} v{self.version} - {self.template_name}"

    def get_total_questions(self):
        return self.template_questions.filter(question__is_active=True).count()


class FiveSTemplateQuestion(models.Model):
    template = models.ForeignKey(
        FiveSTemplate, on_delete=models.CASCADE,
        related_name="template_questions", verbose_name="Template",
    )
    question = models.ForeignKey(
        FiveSQuestion, on_delete=models.PROTECT,
        related_name="template_mappings", verbose_name="Question",
    )
    is_mandatory = models.BooleanField(default=True, verbose_name="Mandatory")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Display Order")
    section_name = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Section Name",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "five_s_template_questions"
        ordering = ["display_order", "id"]
        verbose_name = "5S Template Question"
        verbose_name_plural = "5S Template Questions"
        constraints = [
            models.UniqueConstraint(
                fields=["template", "question"],
                name="uniq_5s_tpl_question",
            ),
        ]
        indexes = [
            models.Index(
                fields=["template", "display_order"],
                name="five_s_tpl_order_idx",
            ),
        ]

    def __str__(self):
        return f"{self.template.template_code} — {self.question.question_code}"


# ---------------------------------------------------------------------------
# Stage 2: Schedule & Auto-generation
# ---------------------------------------------------------------------------

class FiveSSchedule(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('PAUSED', 'Paused'),
        ('ENDED', 'Ended'),
    ]

    schedule_name = models.CharField(max_length=200, verbose_name="Schedule Name")
    template = models.ForeignKey(
        FiveSTemplate, on_delete=models.PROTECT,
        related_name='schedules', verbose_name="Checklist Template",
    )

    plant = models.ManyToManyField(
        Plant, related_name='five_s_schedules', verbose_name="Plants",
    )
    zone = models.ManyToManyField(
        Zone, blank=True, related_name='five_s_schedules', verbose_name="Zones",
    )
    location = models.ManyToManyField(
        Location, blank=True, related_name='five_s_schedules', verbose_name="Locations",
    )
    sublocation = models.ManyToManyField(
        SubLocation, blank=True,
        related_name='five_s_schedules', verbose_name="Sub-Locations",
    )

    assignee = models.ManyToManyField(
        User, related_name='five_s_assigned_schedules', verbose_name="Assigned To",
    )

    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default='MONTHLY',
        blank=True, verbose_name="Frequency",
    )
    start_date = models.DateField(verbose_name="Schedule Start Date")
    end_date = models.DateField(null=True, blank=True, verbose_name="Schedule End Date")

    enable_auto_schedule = models.BooleanField(
        default=False, verbose_name="Enable Auto-Schedule",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='ACTIVE',
        verbose_name="Status",
    )

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_five_s_schedules',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'five_s_schedules'
        ordering = ['-created_at']
        verbose_name = "5S Schedule"
        verbose_name_plural = "5S Schedules"

    def __str__(self):
        plants = ", ".join([p.name for p in self.plant.all()])
        return f"{self.schedule_name} ({self.get_frequency_display()}) - {plants}"

    def calculate_next_date(self):
        current_date = self.start_date
        if self.frequency == 'DAILY':
            return current_date + relativedelta(days=1)
        elif self.frequency == 'WEEKLY':
            return current_date + relativedelta(weeks=1)
        elif self.frequency == 'MONTHLY':
            return current_date + relativedelta(months=1)
        elif self.frequency == 'QUARTERLY':
            return current_date + relativedelta(months=3)
        elif self.frequency == 'YEARLY':
            return current_date + relativedelta(years=1)
        return current_date

    # ------------------------------------------------------------------
    # Pause / lock helpers (used by templates and views)
    # ------------------------------------------------------------------

    @property
    def is_locked(self):
        """True when writes are disabled (paused or ended)."""
        return self.status in ('PAUSED', 'ENDED')

    @property
    def is_paused(self):
        """True only when explicitly paused (not ended)."""
        return self.status == 'PAUSED'


class FiveSAudit(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('REVIEWED', 'Reviewed'),
        ('CLOSED', 'Closed'),
    ]

    schedule = models.ForeignKey(
        FiveSSchedule, on_delete=models.CASCADE, related_name='audits',
    )
    template_version = models.PositiveIntegerField(verbose_name="Template Version Used")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='my_five_s_audits',
    )
    cycle_key = models.CharField(max_length=50, unique=True, verbose_name="Cycle Key")

    # Digital Signature
    inspector_signature = models.ImageField(
        upload_to='five_s/signatures/%Y/%m/',
        null=True, blank=True, verbose_name="Inspector Signature",
    )

    scheduled_date = models.DateField(verbose_name="Scheduled Date")
    due_date = models.DateField(verbose_name="Due Date")
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='SCHEDULED',
        verbose_name="Status",
    )
    overall_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="Overall Score (%)",
    )
    submitted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='submitted_five_s_audits',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'five_s_audits'
        ordering = ['-scheduled_date', '-created_at']
        verbose_name = "5S Audit"
        verbose_name_plural = "5S Audits"

    def __str__(self):
        plants = ", ".join([p.name for p in self.schedule.plant.all()])
        return f"Audit {self.cycle_key} - {plants} ({self.get_status_display()})"

    # ------------------------------------------------------------------
    # Pause / lock helpers
    # ------------------------------------------------------------------

    @property
    def is_locked(self):
        """True when the parent schedule is paused or ended."""
        return self.schedule.status in ('PAUSED', 'ENDED')

    @property
    def schedule_status_display(self):
        """Convenience for templates: 'Paused' / 'Ended' / 'Active'."""
        return self.schedule.get_status_display()


# ---------------------------------------------------------------------------
# Stage 3: Per-question answers
# ---------------------------------------------------------------------------

class AuditAnswer(models.Model):
    """
    A single question's answer within an audit.

    RULE (enforced in clean() and save()):
      - Rating 1 (Poor) or 2 (Fair) → remarks AND evidence are MANDATORY.
      - Rating 3, 4, 5, or N/A      → remarks and evidence are OPTIONAL.
    """

    ANSWER_CHOICES = [
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Good'),
        ('4', 'V. Good'),
        ('5', 'Excellent'),
        ('NA', 'N/A'),
    ]

    audit = models.ForeignKey(
        FiveSAudit, on_delete=models.CASCADE,
        related_name='answers', verbose_name="Audit",
    )
    question = models.ForeignKey(
        FiveSQuestion, on_delete=models.PROTECT,
        related_name='audit_answers', verbose_name="Question",
    )

    answer = models.CharField(
        max_length=10, choices=ANSWER_CHOICES, default='NA',
        verbose_name="Answer", db_index=True,
    )
    remarks = models.TextField(blank=True, null=True, verbose_name="Remarks")
    evidence = models.FileField(
        upload_to='five_s/evidence/%Y/%m/',
        blank=True, null=True, verbose_name="Evidence",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'five_s_audit_answers'
        verbose_name = "5S Audit Answer"
        verbose_name_plural = "5S Audit Answers"
        ordering = ['question__pillar', 'question__question_code']
        constraints = [
            models.UniqueConstraint(
                fields=['audit', 'question'],
                name='uniq_5s_audit_question_answer',
            ),
        ]
        indexes = [
            models.Index(fields=['audit', 'answer']),
        ]

    def __str__(self):
        return f"{self.audit.cycle_key} — {self.question.question_code} → {self.answer}"

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def is_finding(self):
        """True if this answer qualifies as a finding (1 or 2)."""
        return self.answer in ['1', '2']

    @property
    def is_bad(self):
        """True if rating is 1 or 2 (requires remark + evidence)."""
        return self.answer in ['1', '2']

    # ------------------------------------------------------------------
    # Validation — enforce remark + evidence on 1/2 ratings
    # ------------------------------------------------------------------

    def clean(self):
        """
        Enforce: any 1 (Poor) or 2 (Fair) rating MUST have:
          - a non-empty remark explaining the finding
          - a photo as "before" evidence
        Ratings 3, 4, 5, NA → both are optional.
        """
        from django.core.exceptions import ValidationError

        if self.answer in ('1', '2'):
            label = 'Poor' if self.answer == '1' else 'Fair'
            errors = {}

            if not self.remarks or not self.remarks.strip():
                errors['remarks'] = (
                    f'A remark is required when the rating is "{label}". '
                    f'Please describe the finding.'
                )

            if not self.evidence:
                errors['evidence'] = (
                    f'A photo is required when the rating is "{label}". '
                    f'This photo will serve as the "before" evidence for '
                    f'the corrective action.'
                )

            if errors:
                raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """
        Always run full_clean() before saving so the rule cannot be bypassed
        from views, admin, shell, or any other code path.

        To intentionally skip validation (e.g. data migrations), call:
            instance.save(skip_validation=True)
        """
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Stage 4: Corrective Actions
# ---------------------------------------------------------------------------

class CorrectiveAction(models.Model):
    STATUS_CHOICES = [
        ('ASSIGNED', 'Assigned'),
        ('SUBMITTED', 'Pending Approval'),
        ('CLOSED', 'Approved & Closed'),
        ('REJECTED', 'Rejected'),
    ]

    audit = models.ForeignKey(
        FiveSAudit, on_delete=models.CASCADE, related_name='corrective_actions',
    )
    question = models.ForeignKey(FiveSQuestion, on_delete=models.CASCADE)

    # Assignment
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='assigned_actions',
    )
    verifier = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='verifying_actions',
    )
    due_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(verbose_name="Action Remarks")

    # Completion (Filled by Assignee)
    completion_date = models.DateField(null=True, blank=True)
    completion_remarks = models.TextField(blank=True, null=True)
    completion_evidence = models.FileField(
        upload_to='five_s/corrective_evidence/%Y/%m/',
        blank=True, null=True,
    )

    # Approval (Filled by Manager)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='ASSIGNED',
    )
    approval_remarks = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_actions',
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_actions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Action: {self.question.question_code} ({self.get_status_display()})"

    # ------------------------------------------------------------------
    # Pause / lock helpers
    # ------------------------------------------------------------------

    @property
    def is_locked(self):
        """True when the action's audit belongs to a paused/ended schedule."""
        return self.audit.schedule.status in ('PAUSED', 'ENDED')