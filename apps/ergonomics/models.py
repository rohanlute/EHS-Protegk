import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.organizations.models import Department, Location, Plant, Zone

from .services.niosh_service import calculate_niosh
from .services.reba_service import calculate_reba
from .services.risk_service import (
    ergonomic_risk_level,
    recommended_action_for_level,
    risk_reduction_percent,
)
from .services.rula_service import calculate_rula


# =============================================================================
# ASSESSMENT METHOD MASTER
# =============================================================================
class ErgonomicAssessmentMethod(models.Model):
    METHOD_CHOICES = [
        ("RULA", "RULA"),
        ("REBA", "REBA"),
        ("NIOSH", "NIOSH Lifting Equation"),
        ("OWAS", "OWAS"),
        ("OCRA", "OCRA"),
        ("STRAIN_INDEX", "Strain Index"),
        ("SNOOK_CIRIELLO", "Snook & Ciriello"),
        ("OTHER", "Other"),
    ]
    name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=30, choices=METHOD_CHOICES, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_methods_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# =============================================================================
# ERGONOMIC ASSESSMENT (core)
# =============================================================================
class ErgonomicAssessment(models.Model):
    TYPE_CHOICES = [
        ("INITIAL", "Initial Assessment"),
        ("PERIODIC", "Periodic Assessment"),
        ("REASSESSMENT", "Reassessment"),
        ("POST_INCIDENT", "Post-Incident Assessment"),
        ("POST_MSD", "Post-MSD Assessment"),
        ("PROCESS_CHANGE", "Process Change Assessment"),
        ("CA_VERIFICATION", "Corrective Action Verification"),
    ]
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("IN_PROGRESS", "In Progress"),
        ("SUBMITTED", "Submitted"),
        ("UNDER_REVIEW", "Under Review"),
        ("APPROVED", "Approved"),
        ("CLOSED", "Closed"),
    ]
    RISK_LEVEL_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("VERY_HIGH", "Very High"),
    ]

    assessment_id = models.CharField(max_length=60, unique=True, editable=False)
    plant = models.ForeignKey(
        Plant, on_delete=models.PROTECT, related_name="ergonomic_assessments"
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="ergonomic_assessments"
    )
    zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_assessments",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_assessments",
    )
    area = models.CharField(max_length=150, blank=True)
    job_role = models.CharField(max_length=150)
    task = models.CharField(max_length=250)
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_worker_assessments",
    )
    workers_exposed = models.PositiveIntegerField(default=1)
    shift = models.CharField(max_length=80, blank=True)
    assessment_date = models.DateField(default=timezone.now)
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_assessments_done",
    )
    task_duration = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    exposure_duration = models.CharField(max_length=100, blank=True)
    assessment_type = models.CharField(
        max_length=30, choices=TYPE_CHOICES, default="INITIAL"
    )
    assessment_method = models.ForeignKey(
        ErgonomicAssessmentMethod,
        on_delete=models.PROTECT,
        related_name="assessments",
    )
    task_description = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="ergonomics/assessments/", blank=True, null=True
    )
    score = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, editable=False
    )
    risk_level = models.CharField(
        max_length=20, choices=RISK_LEVEL_CHOICES, blank=True, editable=False
    )
    action_level = models.CharField(max_length=80, blank=True, editable=False)
    recommended_action = models.TextField(blank=True, editable=False)
    next_assessment_date = models.DateField(null=True, blank=True)

    # Status is auto-derived from corrective-action workflow
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="SUBMITTED"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_assessments_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_assessments_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-assessment_date", "-created_at"]
        indexes = [
            models.Index(fields=["plant", "department"]),
            models.Index(fields=["risk_level", "status"]),
            models.Index(fields=["assessment_date"]),
        ]

    def __str__(self):
        return self.assessment_id

    def save(self, *args, **kwargs):
        if not self.assessment_id:
            today = datetime.date.today()
            plant_code = self.plant.code if self.plant_id else "XXX"
            prefix = f"ERGO-{plant_code}-{today:%Y%m%d}"
            count = ErgonomicAssessment.objects.filter(
                assessment_id__startswith=prefix
            ).count()
            self.assessment_id = f"{prefix}-{count + 1:03d}"
        super().save(*args, **kwargs)

    def apply_result(self, result):
        if "score" in result:
            self.score = result["score"]
        elif "lifting_index" in result:
            self.score = result["lifting_index"]
        self.risk_level = result.get("risk_level", ergonomic_risk_level(self.score))
        self.action_level = result.get("action_level", self.risk_level)
        self.recommended_action = result.get(
            "recommended_action", recommended_action_for_level(self.risk_level)
        )
        self.save(
            update_fields=[
                "score",
                "risk_level",
                "action_level",
                "recommended_action",
                "updated_at",
            ]
        )

    def refresh_status(self, save=True):
        """
        Derive assessment status from its corrective actions' statuses.

          - No actions yet                          → SUBMITTED
          - Any REJECTED or PENDING_VERIFICATION    → UNDER_REVIEW
          - All actions CLOSED                      → CLOSED
          - Otherwise (some open work remains)      → IN_PROGRESS
        """
        actions = self.corrective_actions.all()
        total = actions.count()

        if total == 0:
            new_status = "SUBMITTED"
        else:
            statuses = set(actions.values_list("status", flat=True))

            if "REJECTED" in statuses or "PENDING_VERIFICATION" in statuses:
                new_status = "UNDER_REVIEW"
            elif statuses <= {"CLOSED"}:
                new_status = "CLOSED"
            elif statuses & {"OPEN", "ASSIGNED", "IN_PROGRESS", "OVERDUE"}:
                new_status = "IN_PROGRESS"
            elif statuses <= {"COMPLETED"}:
                new_status = "UNDER_REVIEW"
            else:
                new_status = "IN_PROGRESS"

        if self.status != new_status:
            self.status = new_status
            if save:
                super().save(update_fields=["status", "updated_at"])

        return self.status


# =============================================================================
# RISK FACTORS
# =============================================================================
class ErgonomicRiskFactor(models.Model):
    POSTURE_CHOICES = [
        ("NORMAL", "Normal"),
        ("SLIGHT", "Slightly Awkward"),
        ("AWKWARD", "Awkward"),
        ("HIGHLY_AWKWARD", "Highly Awkward"),
    ]
    FORCE_CHOICES = [
        ("LOW", "Low"),
        ("MODERATE", "Moderate"),
        ("HIGH", "High"),
        ("VERY_HIGH", "Very High"),
    ]
    HANDLING_CHOICES = [
        ("FLOOR", "Floor lifting"),
        ("WAIST", "Waist-level lifting"),
        ("SHOULDER", "Shoulder-level lifting"),
        ("OVERHEAD", "Overhead lifting"),
    ]

    assessment = models.OneToOneField(
        ErgonomicAssessment,
        on_delete=models.CASCADE,
        related_name="risk_factors",
    )

    # ---- A. Posture ----
    neck_posture = models.CharField(
        max_length=20, choices=POSTURE_CHOICES, default="NORMAL"
    )
    shoulder_posture = models.CharField(
        max_length=20, choices=POSTURE_CHOICES, default="NORMAL"
    )
    elbow_posture = models.CharField(
        max_length=20, choices=POSTURE_CHOICES, default="NORMAL"
    )
    wrist_posture = models.CharField(
        max_length=20, choices=POSTURE_CHOICES, default="NORMAL"
    )
    back_posture = models.CharField(
        max_length=20, choices=POSTURE_CHOICES, default="NORMAL"
    )
    hip_posture = models.CharField(
        max_length=20, choices=POSTURE_CHOICES, default="NORMAL"
    )
    knee_posture = models.CharField(
        max_length=20, choices=POSTURE_CHOICES, default="NORMAL"
    )
    ankle_posture = models.CharField(
        max_length=20, choices=POSTURE_CHOICES, default="NORMAL"
    )
    bending = models.BooleanField(default=False)
    twisting = models.BooleanField(default=False)
    reaching = models.BooleanField(default=False)
    overhead_work = models.BooleanField(default=False)
    kneeling = models.BooleanField(default=False)
    squatting = models.BooleanField(default=False)
    static_posture = models.BooleanField(default=False)

    # ---- B. Force ----
    force_required = models.CharField(
        max_length=20, choices=FORCE_CHOICES, default="LOW"
    )
    push_force_n = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    pull_force_n = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    grip_force_n = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    lift_force_kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    # ---- C. Repetition ----
    repetitions_per_minute = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    repetitions_per_hour = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    cycle_time_seconds = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    task_duration_minutes = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    cycles_per_shift = models.PositiveIntegerField(null=True, blank=True)

    # ---- D. Manual Handling ----
    object_weight_kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    lifting_frequency = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    lifting_height_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    starting_height_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    ending_height_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    horizontal_reach_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    carrying_distance_m = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    push_distance_m = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    pull_distance_m = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    handling_type = models.CharField(
        max_length=20, choices=HANDLING_CHOICES, blank=True
    )
    handling_person = models.CharField(
        max_length=10,
        choices=[("ONE", "One-person handling"), ("TWO", "Two-person handling")],
        blank=True,
    )
    mechanical_assistance_available = models.BooleanField(default=False)

    # ---- E. Vibration ----
    hand_arm_vibration = models.BooleanField(default=False)
    whole_body_vibration = models.BooleanField(default=False)
    vibration_exposure_duration = models.CharField(max_length=100, blank=True)
    vibration_tool_used = models.CharField(max_length=150, blank=True)

    # ---- F. Workstation ----
    work_surface_height_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    chair_height_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    monitor_height_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    keyboard_position = models.CharField(max_length=150, blank=True)
    mouse_position = models.CharField(max_length=150, blank=True)
    leg_room_adequate = models.BooleanField(default=False)
    reach_distance_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    lighting_adequate = models.BooleanField(default=False)
    workspace_adequate = models.BooleanField(default=False)
    adjustable_workstation_available = models.BooleanField(default=False)
    workstation_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Risk Factors — {self.assessment.assessment_id}"


# =============================================================================
# METHOD-SPECIFIC SCORING MODELS
# =============================================================================
class RULAAssessment(models.Model):
    assessment = models.OneToOneField(
        ErgonomicAssessment, on_delete=models.CASCADE, related_name="rula"
    )
    upper_arm_score = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(6)]
    )
    lower_arm_score = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    wrist_score = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    wrist_twist_score = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(2)],
        help_text="1 = mid-range of twist, 2 = at or near end of twisting range",
    )
    neck_score = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(6)]
    )
    trunk_score = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(6)]
    )
    leg_score = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(2)]
    )
    muscle_use_score = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    force_load_score = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(3)]
    )

    def __str__(self):
        return f"RULA — {self.assessment.assessment_id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.assessment.apply_result(calculate_rula(self.__dict__))


class REBAAssessment(models.Model):
    assessment = models.OneToOneField(
        ErgonomicAssessment, on_delete=models.CASCADE, related_name="reba"
    )
    trunk_score = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    neck_score = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    legs_score = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    upper_arm_score = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(6)]
    )
    lower_arm_score = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(2)]
    )
    wrist_score = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    load_force_score = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(3)]
    )
    coupling_score = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(3)]
    )
    activity_score = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(3)]
    )

    def __str__(self):
        return f"REBA — {self.assessment.assessment_id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.assessment.apply_result(calculate_reba(self.__dict__))


class NIOSHLiftingAssessment(models.Model):
    COUPLING_CHOICES = [("GOOD", "Good"), ("FAIR", "Fair"), ("POOR", "Poor")]

    assessment = models.OneToOneField(
        ErgonomicAssessment, on_delete=models.CASCADE, related_name="niosh"
    )
    load_weight = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    horizontal_location = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    vertical_location = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    vertical_travel_distance = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    asymmetry_angle = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(135)],
    )
    frequency_lifts_per_minute = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    duration_hours = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    coupling = models.CharField(
        max_length=10, choices=COUPLING_CHOICES, default="FAIR"
    )
    recommended_weight_limit = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, editable=False
    )
    lifting_index = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, editable=False
    )

    def __str__(self):
        return f"NIOSH — {self.assessment.assessment_id}"

    def save(self, *args, **kwargs):
        result = calculate_niosh(self.__dict__)
        self.recommended_weight_limit = result["recommended_weight_limit"]
        self.lifting_index = result["lifting_index"]
        super().save(*args, **kwargs)
        self.assessment.apply_result(result)


class OWASAssessment(models.Model):
    """
    OWAS — Ovako Working Posture Analysing System.

    Four posture codes (back / arms / legs / load), each integer with
    fixed ranges; the model computes the OWAS Action Category (1-4) on
    save and pushes it onto the parent ErgonomicAssessment.
    """
    BACK_CHOICES = [
        (1, "1 — Straight"),
        (2, "2 — Bent"),
        (3, "3 — Bent and twisted"),
        (4, "4 — Straight and twisted"),
    ]
    ARMS_CHOICES = [
        (1, "1 — Both arms below shoulder level"),
        (2, "2 — One arm at or above shoulder level"),
        (3, "3 — Both arms at or above shoulder level"),
    ]
    LEGS_CHOICES = [
        (1, "1 — Sitting"),
        (2, "2 — Standing, both legs straight"),
        (3, "3 — Standing on one straight leg"),
        (4, "4 — Standing with both knees bent"),
        (5, "5 — Kneeling"),
        (6, "6 — Walking / moving"),
    ]
    LOAD_CHOICES = [
        (1, "1 — Less than 10 kg"),
        (2, "2 — 10 to 20 kg"),
        (3, "3 — More than 20 kg"),
    ]

    assessment = models.OneToOneField(
        ErgonomicAssessment, on_delete=models.CASCADE, related_name="owas"
    )
    back_score = models.PositiveSmallIntegerField(default=1, choices=BACK_CHOICES)
    arms_score = models.PositiveSmallIntegerField(default=1, choices=ARMS_CHOICES)
    legs_score = models.PositiveSmallIntegerField(default=2, choices=LEGS_CHOICES)
    load_score = models.PositiveSmallIntegerField(default=1, choices=LOAD_CHOICES)

    def __str__(self):
        return f"OWAS — {self.assessment.assessment_id}"

    def save(self, *args, **kwargs):
        from .services.owas_service import calculate_owas
        super().save(*args, **kwargs)
        self.assessment.apply_result(calculate_owas(self.__dict__))


class OCRAAssessment(models.Model):
    """
    OCRA Index — Occupational Repetitive Actions.

    Stores the seven multipliers plus actual actions; computes the OCRA
    Index on save and pushes the score/risk level onto the parent
    ErgonomicAssessment.
    """
    assessment = models.OneToOneField(
        ErgonomicAssessment, on_delete=models.CASCADE, related_name="ocra"
    )
    actual_actions = models.PositiveIntegerField(
        default=0,
        help_text="Total technical actions performed during the shift",
    )
    constant_frequency = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=30,
        help_text="Frequency constant (default 30 actions/min)",
    )
    posture_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1,
        validators=[MinValueValidator(0.01), MaxValueValidator(1)],
        help_text="0.01–1.00 (1.00 = best posture)",
    )
    force_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1,
        validators=[MinValueValidator(0.01), MaxValueValidator(1)],
        help_text="0.01–1.00 (1.00 = no significant force)",
    )
    repetitiveness_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1,
        validators=[MinValueValidator(0.01), MaxValueValidator(1)],
        help_text="0.01–1.00 (1.00 = low repetitiveness)",
    )
    additional_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1,
        validators=[MinValueValidator(0.01), MaxValueValidator(1)],
        help_text="0.01–1.00 (vibration, precision, etc.)",
    )
    recovery_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1,
        validators=[MinValueValidator(0.01), MaxValueValidator(1)],
        help_text="0.01–1.00 (1.00 = adequate recovery breaks)",
    )
    duration_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1,
        validators=[MinValueValidator(0.01), MaxValueValidator(1)],
        help_text="0.01–1.00 (1.00 = short duration)",
    )
    ocra_index = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, editable=False
    )

    def __str__(self):
        return f"OCRA — {self.assessment.assessment_id}"

    def save(self, *args, **kwargs):
        from .services.ocra_service import calculate_ocra
        result = calculate_ocra(self.__dict__)
        self.ocra_index = result["score"]
        super().save(*args, **kwargs)
        self.assessment.apply_result(result)


class StrainIndexAssessment(models.Model):
    """
    Strain Index (Moore & Garg, 1995) for distal upper-extremity MSD risk.
    Stores the eight multiplier choice keys; computes SI on save and
    pushes score/risk onto the parent ErgonomicAssessment.
    """
    INTENSITY_CHOICES = [
        ("LIGHT", "Light (Borg ~1-2)"),
        ("SOMEWHAT_HARD", "Somewhat hard (Borg ~3)"),
        ("HARD", "Hard (Borg ~4-5)"),
        ("VERY_HARD", "Very hard (Borg ~6-7)"),
        ("NEAR_MAXIMAL", "Near maximal (Borg ~8-10)"),
    ]
    DURATION_EXERTION_CHOICES = [
        ("<10", "< 10 % of cycle"),
        ("10-29", "10–29 %"),
        ("30-49", "30–49 %"),
        ("50-79", "50–79 %"),
        (">=80", "≥ 80 %"),
    ]
    EFFORTS_PER_MIN_CHOICES = [
        ("<4", "< 4 per minute"),
        ("4-8", "4–8 per minute"),
        ("9-14", "9–14 per minute"),
        ("15-19", "15–19 per minute"),
        (">=20", "≥ 20 per minute"),
    ]
    HAND_WRIST_CHOICES = [
        ("VERY_GOOD", "Very good — neutral"),
        ("GOOD", "Good — near neutral"),
        ("FAIR", "Fair — slight deviation"),
        ("BAD", "Bad — marked deviation"),
        ("VERY_BAD", "Very bad — extreme deviation"),
    ]
    SPEED_CHOICES = [
        ("VERY_SLOW", "Very slow"),
        ("SLOW", "Slow"),
        ("FAIR", "Fair"),
        ("FAST", "Fast"),
        ("VERY_FAST", "Very fast"),
    ]
    DURATION_PER_DAY_CHOICES = [
        ("<1", "< 1 hour"),
        ("1-2", "1–2 hours"),
        ("2-4", "2–4 hours"),
        ("4-8", "4–8 hours"),
        (">=8", "≥ 8 hours"),
    ]
    EFFORTS_PER_HOUR_CHOICES = [
        ("0-1", "0–1 per hour"),
        ("2-3", "2–3 per hour"),
        ("4-5", "4–5 per hour"),
        ("6-7", "6–7 per hour"),
        (">=8", "≥ 8 per hour"),
    ]

    assessment = models.OneToOneField(
        ErgonomicAssessment, on_delete=models.CASCADE, related_name="strain_index"
    )
    intensity_of_exertion = models.CharField(
        max_length=20, choices=INTENSITY_CHOICES, default="LIGHT"
    )
    duration_of_exertion = models.CharField(
        max_length=10, choices=DURATION_EXERTION_CHOICES, default="<10"
    )
    efforts_per_minute = models.CharField(
        max_length=10, choices=EFFORTS_PER_MIN_CHOICES, default="<4"
    )
    hand_wrist_posture = models.CharField(
        max_length=15, choices=HAND_WRIST_CHOICES, default="FAIR"
    )
    speed_of_work = models.CharField(
        max_length=15, choices=SPEED_CHOICES, default="FAIR"
    )
    duration_per_day_hours = models.CharField(
        max_length=10, choices=DURATION_PER_DAY_CHOICES, default="<1"
    )
    daily_duration_hours = models.CharField(
        max_length=10, choices=DURATION_PER_DAY_CHOICES, default="<1"
    )
    efforts_per_hour = models.CharField(
        max_length=10, choices=EFFORTS_PER_HOUR_CHOICES, default="0-1"
    )

    def __str__(self):
        return f"Strain Index — {self.assessment.assessment_id}"

    def save(self, *args, **kwargs):
        from .services.strain_index_service import calculate_strain_index
        super().save(*args, **kwargs)
        self.assessment.apply_result(calculate_strain_index(self.__dict__))


class SnookCirielloAssessment(models.Model):
    """
    Snook & Ciriello (1991) psychophysical tables for manual handling.
    Stores task/gender/position/percentile/actual load; the service
    looks up the Maximum Acceptable Weight and computes the ratio.
    """
    TASK_TYPE_CHOICES = [
        ("LIFT", "Lift"),
        ("LOWER", "Lower"),
        ("PUSH", "Push"),
        ("PULL", "Pull"),
        ("CARRY", "Carry"),
    ]
    GENDER_CHOICES = [
        ("MALE", "Male"),
        ("FEMALE", "Female"),
    ]
    POSITION_CHOICES = [
        ("FLOOR", "Floor level"),
        ("KNUCKLE", "Knuckle height"),
        ("SHOULDER", "Shoulder height"),
        ("CLOSE", "Close (≤ 40 cm)"),
        ("MEDIUM", "Medium (40–60 cm)"),
        ("FAR", "Far (> 60 cm)"),
    ]
    PERCENTILE_CHOICES = [
        (10, "10th percentile (weakest 10 %)"),
        (25, "25th percentile"),
        (50, "50th percentile (median)"),
        (75, "75th percentile"),
        (90, "90th percentile"),
    ]

    assessment = models.OneToOneField(
        ErgonomicAssessment, on_delete=models.CASCADE, related_name="snook_ciriello"
    )
    task_type = models.CharField(
        max_length=10, choices=TASK_TYPE_CHOICES, default="LIFT"
    )
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, default="MALE"
    )
    position = models.CharField(
        max_length=15, choices=POSITION_CHOICES, default="KNUCKLE"
    )
    percentile = models.PositiveSmallIntegerField(
        choices=PERCENTILE_CHOICES, default=50
    )
    actual_load = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Actual weight handled in kg",
    )
    max_acceptable_weight = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, editable=False
    )
    ratio = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, editable=False
    )

    def __str__(self):
        return f"Snook & Ciriello — {self.assessment.assessment_id}"

    def save(self, *args, **kwargs):
        from .services.snook_service import calculate_snook
        result = calculate_snook(self.__dict__)
        self.max_acceptable_weight = result["maw"]
        self.ratio = result["score"]
        super().save(*args, **kwargs)
        self.assessment.apply_result(result)


# =============================================================================
# CORRECTIVE ACTION QUERYSET (defined before the model that uses it)
# =============================================================================
class ErgonomicCorrectiveActionQuerySet(models.QuerySet):
    """
    Manager/queryset for corrective actions.

    OVERDUE is no longer set inside model.save(). It is set by
    refresh_overdue() — called from list/dashboard views or a
    management command / scheduled job.
    """

    def refresh_overdue(self):
        return self.filter(
            status__in=["OPEN", "ASSIGNED", "IN_PROGRESS"],
            target_date__lt=timezone.now().date(),
        ).update(status="OVERDUE")

    def overdue(self):
        return self.filter(status="OVERDUE")

    def open_actions(self):
        return self.exclude(status__in=["COMPLETED", "CLOSED", "REJECTED"])


# =============================================================================
# CONTROLS
# =============================================================================
class ErgonomicControl(models.Model):
    CONTROL_TYPE_CHOICES = [
        ("ELIMINATION", "Elimination"),
        ("SUBSTITUTION", "Substitution"),
        ("ENGINEERING", "Engineering Control"),
        ("ADMINISTRATIVE", "Administrative Control"),
        ("PPE", "PPE"),
    ]
    assessment = models.ForeignKey(
        ErgonomicAssessment, on_delete=models.CASCADE, related_name="controls"
    )
    control_type = models.CharField(max_length=20, choices=CONTROL_TYPE_CHOICES)
    description = models.TextField()
    implemented = models.BooleanField(default=False)
    implementation_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_controls_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_control_type_display()} — {self.assessment.assessment_id}"


# =============================================================================
# CORRECTIVE ACTIONS
# =============================================================================
class ErgonomicCorrectiveAction(models.Model):
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("ASSIGNED", "Assigned"),
        ("IN_PROGRESS", "In Progress"),
        ("PENDING_VERIFICATION", "Pending Verification"),
        ("COMPLETED", "Completed"),
        ("REJECTED", "Rejected"),
        ("OVERDUE", "Overdue"),
        ("CLOSED", "Closed"),
    ]
    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("VERY_HIGH", "Very High"),
    ]

    action_id = models.CharField(max_length=60, unique=True, editable=False)
    assessment = models.ForeignKey(
        ErgonomicAssessment, on_delete=models.CASCADE, related_name="corrective_actions"
    )
    action_description = models.TextField()
    root_cause = models.TextField(blank=True)
    control_type = models.CharField(
        max_length=20, choices=ErgonomicControl.CONTROL_TYPE_CHOICES
    )
    responsible_person = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_ergonomic_actions",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_actions",
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="MEDIUM"
    )
    target_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="OPEN")
    completion_date = models.DateField(null=True, blank=True)
    evidence = models.FileField(
        upload_to="ergonomics/actions/", blank=True, null=True
    )
    verification = models.TextField(blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_ergonomic_actions",
    )
    verification_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    rejection_remark = models.TextField(
        blank=True,
        help_text="Reason provided by the verifier when rejecting the action.",
    )
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_ergonomic_actions",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_actions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Custom manager (class-level, NOT inside Meta)
    objects = ErgonomicCorrectiveActionQuerySet.as_manager()

    class Meta:
        ordering = ["target_date", "id"]
        indexes = [
            models.Index(fields=["status", "target_date"]),
            models.Index(fields=["priority"]),
        ]

    def __str__(self):
        return self.action_id or f"Action #{self.pk}"

    def clean(self):
        if self.status == "CLOSED" and (
            not self.evidence or not self.verified_by or not self.verification
        ):
            raise ValidationError(
                "Closure requires evidence, verification, and verified by."
            )

    def save(self, *args, **kwargs):
        if not self.action_id:
            year = datetime.date.today().year
            prefix = f"ERGO-ACT-{year}"
            count = ErgonomicCorrectiveAction.objects.filter(
                action_id__startswith=prefix
            ).count()
            self.action_id = f"{prefix}-{count + 1:04d}"
        # NOTE: OVERDUE is NOT set here anymore. Use
        # ErgonomicCorrectiveAction.objects.refresh_overdue() from views
        # / management commands instead.
        super().save(*args, **kwargs)


# =============================================================================
# REASSESSMENT
# =============================================================================
class ErgonomicReassessment(models.Model):
    EFFECTIVENESS_CHOICES = [
        ("EFFECTIVE", "Effective"),
        ("PARTIAL", "Partially Effective"),
        ("NOT_EFFECTIVE", "Not Effective"),
    ]
    assessment = models.ForeignKey(
        ErgonomicAssessment, on_delete=models.CASCADE, related_name="reassessments"
    )
    corrective_action = models.ForeignKey(
        ErgonomicCorrectiveAction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reassessments",
    )
    reassessment_date = models.DateField(default=timezone.now)
    previous_score = models.DecimalField(max_digits=8, decimal_places=2)
    new_score = models.DecimalField(max_digits=8, decimal_places=2)
    previous_risk = models.CharField(
        max_length=20, choices=ErgonomicAssessment.RISK_LEVEL_CHOICES
    )
    new_risk = models.CharField(
        max_length=20, choices=ErgonomicAssessment.RISK_LEVEL_CHOICES, blank=True
    )
    control_effectiveness = models.CharField(
        max_length=20, choices=EFFECTIVENESS_CHOICES
    )
    residual_risk = models.CharField(
        max_length=20, choices=ErgonomicAssessment.RISK_LEVEL_CHOICES, blank=True
    )
    risk_reduction_percent = models.DecimalField(
        max_digits=6, decimal_places=2, default=0, editable=False
    )
    additional_action_required = models.BooleanField(default=False)
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_reassessments",
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reassessment — {self.assessment.assessment_id} ({self.reassessment_date})"

    def save(self, *args, **kwargs):
        self.new_risk = self.new_risk or ergonomic_risk_level(self.new_score)
        self.residual_risk = self.new_risk
        self.risk_reduction_percent = risk_reduction_percent(
            self.previous_score, self.new_score
        )
        self.additional_action_required = (
            self.additional_action_required
            or self.control_effectiveness == "NOT_EFFECTIVE"
        )
        super().save(*args, **kwargs)


# =============================================================================
# QUICK OBSERVATIONS
# =============================================================================
class ErgonomicObservation(models.Model):
    assessment = models.ForeignKey(
        ErgonomicAssessment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_observations",
    )
    plant = models.ForeignKey(
        Plant, on_delete=models.PROTECT, related_name="ergonomic_observations"
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="ergonomic_observations"
    )
    area = models.CharField(max_length=150, blank=True)
    task = models.CharField(max_length=250)
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_observations",
    )
    observation_date = models.DateField(default=timezone.now)
    observer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_observations_made",
    )
    risk_factor = models.CharField(max_length=120)
    observation = models.TextField()
    risk_level = models.CharField(
        max_length=20,
        choices=ErgonomicAssessment.RISK_LEVEL_CHOICES,
        default="MEDIUM",
    )
    immediate_action = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to="ergonomics/observations/", blank=True, null=True
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Observation #{self.pk} — {self.task}"


# =============================================================================
# MSD / DISCOMFORT
# =============================================================================
class MSDDiscomfort(models.Model):
    BODY_PART_CHOICES = [
        ("NECK", "Neck"),
        ("SHOULDER", "Shoulder"),
        ("UPPER_BACK", "Upper Back"),
        ("LOWER_BACK", "Lower Back"),
        ("ELBOW", "Elbow"),
        ("WRIST", "Wrist"),
        ("HAND", "Hand"),
        ("HIP", "Hip"),
        ("KNEE", "Knee"),
        ("ANKLE", "Ankle"),
        ("OTHER", "Other"),
    ]
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="msd_discomforts",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="msd_discomforts",
    )
    job = models.CharField(max_length=150, blank=True)
    task = models.CharField(max_length=250, blank=True)
    date_reported = models.DateField(default=timezone.now)
    body_part = models.CharField(max_length=30, choices=BODY_PART_CHOICES)
    discomfort_type = models.CharField(max_length=120)
    severity = models.CharField(
        max_length=20, choices=ErgonomicAssessment.RISK_LEVEL_CHOICES
    )
    frequency = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    work_relatedness = models.CharField(max_length=100, blank=True)
    medical_referral = models.BooleanField(default=False)
    work_restriction = models.BooleanField(default=False)
    related_assessment = models.ForeignKey(
        ErgonomicAssessment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="msd_cases",
    )
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="msd_cases_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MSD #{self.pk} — {self.get_body_part_display()}"


# =============================================================================
# EMPLOYEE / JOB MAPPING
# =============================================================================
class ErgonomicJobMapping(models.Model):
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ergonomic_job_mappings",
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="ergonomic_job_mappings"
    )
    job = models.CharField(max_length=150)
    task = models.CharField(max_length=250)
    assessment = models.ForeignKey(
        ErgonomicAssessment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_mappings",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["worker", "job", "task"]

    def __str__(self):
        return f"{self.worker} — {self.job} / {self.task}"


# =============================================================================
# ASSESSMENT SCHEDULE
# =============================================================================
class ErgonomicAssessmentSchedule(models.Model):
    REASON_CHOICES = [
        ("PERIODIC", "Periodic review"),
        ("PROCESS_CHANGE", "Process change"),
        ("NEW_EQUIPMENT", "New equipment"),
        ("NEW_WORKSTATION", "New workstation"),
        ("ERGONOMIC_INCIDENT", "Ergonomic incident"),
        ("MSD_CASE", "MSD case"),
        ("CORRECTIVE_ACTION", "Corrective action"),
        ("HIGH_RISK", "Previous high-risk assessment"),
    ]
    STATUS_CHOICES = [
        ("DUE", "Due"),
        ("UPCOMING", "Upcoming"),
        ("OVERDUE", "Overdue"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]
    assessment = models.ForeignKey(
        ErgonomicAssessment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="schedules",
    )
    plant = models.ForeignKey(
        Plant, on_delete=models.PROTECT, related_name="ergonomic_schedules"
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="ergonomic_schedules"
    )
    job = models.CharField(max_length=150)
    task = models.CharField(max_length=250)
    due_date = models.DateField()
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="UPCOMING"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_schedules",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_schedules_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Schedule #{self.pk} — {self.job} due {self.due_date}"

    def save(self, *args, **kwargs):
        if (
            self.status not in {"COMPLETED", "CANCELLED"}
            and self.due_date < timezone.now().date()
        ):
            self.status = "OVERDUE"
        super().save(*args, **kwargs)
# =============================================================================
# AUDIT LOG — ergonomics-local
# =============================================================================
class ErgonomicAuditLog(models.Model):
    """
    Audit trail for ergonomics records (assessments, corrective actions,
    observations, MSD cases).

    Append-only. One row per state change worth remembering.
    """

    ACTION_CREATE = "CREATE"
    ACTION_UPDATE = "UPDATE"
    ACTION_DELETE = "DELETE"
    ACTION_STATUS_CHANGE = "STATUS_CHANGE"
    ACTION_VERIFY = "VERIFY"
    ACTION_REJECT = "REJECT"
    ACTION_OTHER = "OTHER"

    ACTION_CHOICES = [
        (ACTION_CREATE, "Created"),
        (ACTION_UPDATE, "Updated"),
        (ACTION_DELETE, "Deleted"),
        (ACTION_STATUS_CHANGE, "Status Changed"),
        (ACTION_VERIFY, "Verified"),
        (ACTION_REJECT, "Rejected"),
        (ACTION_OTHER, "Other"),
    ]

    # Who / when
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ergonomic_audit_logs",
        help_text="User who performed the action (null = system).",
    )
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    # What
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, db_index=True)

    # Denormalized for fast lookup — avoids joins
    model_name = models.CharField(max_length=80, db_index=True)
    object_id = models.CharField(max_length=64, db_index=True)
    object_repr = models.CharField(max_length=255, blank=True)

    # Structured diff: {"field": ["old", "new"], ...}
    changes = models.JSONField(default=dict, blank=True)
    message = models.TextField(blank=True)

    # Request context (optional)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Ergonomic Audit Log"
        verbose_name_plural = "Ergonomic Audit Logs"
        indexes = [
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
        ]

    def __str__(self):
        who = self.user.get_username() if self.user else "system"
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {who} {self.action} {self.object_repr}"

    @property
    def changes_list(self):
        """Template-friendly view of `changes`."""
        if not self.changes:
            return []
        out = []
        for field, pair in self.changes.items():
            old = new = ""
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                old, new = pair
            out.append({"field": field, "old": old, "new": new})
        return out
