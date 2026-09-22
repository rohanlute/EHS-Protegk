from django.contrib import admin

from .models import (
    ErgonomicAssessment,
    ErgonomicAssessmentMethod,
    ErgonomicAssessmentSchedule,
    ErgonomicControl,
    ErgonomicCorrectiveAction,
    ErgonomicJobMapping,
    ErgonomicObservation,
    ErgonomicReassessment,
    ErgonomicRiskFactor,
    MSDDiscomfort,
    NIOSHLiftingAssessment,
    REBAAssessment,
    SnookCirielloAssessment,
    RULAAssessment,
    ErgonomicAuditLog,
    StrainIndexAssessment,
    OCRAAssessment,
    OWASAssessment,
)


# =============================================================================
# INLINES
# =============================================================================
class ErgonomicRiskFactorInline(admin.StackedInline):
    model = ErgonomicRiskFactor
    extra = 0
    can_delete = False


# =============================================================================
# ASSESSMENT METHOD MASTER
# =============================================================================
@admin.register(ErgonomicAssessmentMethod)
class ErgonomicAssessmentMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active", "code")
    search_fields = ("name", "code", "description")
    ordering = ("name",)


# =============================================================================
# ERGONOMIC ASSESSMENT
# =============================================================================
@admin.register(ErgonomicAssessment)
class ErgonomicAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "assessment_id",
        "plant",
        "department",
        "job_role",
        "task",
        "assessment_method",
        "score",
        "risk_level",
        "status",
    )
    list_filter = ("risk_level", "status", "assessment_method", "plant", "department")
    search_fields = (
        "assessment_id",
        "job_role",
        "task",
        "worker__first_name",
        "worker__last_name",
    )
    readonly_fields = (
        "assessment_id",
        "score",
        "risk_level",
        "action_level",
        "recommended_action",
        # Status is DERIVED from corrective-action workflow — never edit by hand
        "status",
        "created_at",
        "updated_at",
    )
    inlines = [ErgonomicRiskFactorInline]
    list_select_related = ("plant", "department", "assessment_method", "worker", "assessor")
    date_hierarchy = "assessment_date"
    ordering = ("-assessment_date", "-created_at")

    fieldsets = (
        ("Identification", {
            "fields": (
                "assessment_id",
                "assessment_type",
                "assessment_method",
                "status",
                "assessment_date",
                "next_assessment_date",
            )
        }),
        ("Location & Organisation", {
            "fields": ("plant", "department", "zone", "location", "area", "shift")
        }),
        ("Job / Task", {
            "fields": (
                "job_role",
                "task",
                "worker",
                "workers_exposed",
                "task_duration",
                "frequency",
                "exposure_duration",
                "task_description",
                "attachment",
            )
        }),
        ("People", {
            "fields": ("assessor", "created_by", "updated_by")
        }),
        ("Result (read-only)", {
            "fields": (
                "score",
                "risk_level",
                "action_level",
                "recommended_action",
            )
        }),
        ("Audit", {
            "fields": ("created_at", "updated_at")
        }),
    )


# =============================================================================
# METHOD-SPECIFIC SCORING MODELS
# =============================================================================
@admin.register(RULAAssessment)
class RULAAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "assessment",
        "upper_arm_score",
        "lower_arm_score",
        "wrist_score",
        "neck_score",
        "trunk_score",
        "leg_score",
    )
    list_select_related = ("assessment",)
    search_fields = ("assessment__assessment_id",)


@admin.register(REBAAssessment)
class REBAAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "assessment",
        "trunk_score",
        "neck_score",
        "legs_score",
        "upper_arm_score",
        "lower_arm_score",
        "wrist_score",
    )
    list_select_related = ("assessment",)
    search_fields = ("assessment__assessment_id",)


@admin.register(NIOSHLiftingAssessment)
class NIOSHLiftingAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "assessment",
        "load_weight",
        "horizontal_location",
        "vertical_location",
        "coupling",
        "lifting_index",
    )
    list_select_related = ("assessment",)
    search_fields = ("assessment__assessment_id",)


@admin.register(OWASAssessment)
class OWASAssessmentAdmin(admin.ModelAdmin):
    list_display = ("assessment", "back_score", "arms_score", "legs_score", "load_score")
    list_select_related = ("assessment",)
    search_fields = ("assessment__assessment_id",)


@admin.register(OCRAAssessment)
class OCRAAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "assessment",
        "actual_actions",
        "posture_multiplier",
        "force_multiplier",
        "ocra_index",
    )
    list_select_related = ("assessment",)
    search_fields = ("assessment__assessment_id",)


@admin.register(StrainIndexAssessment)
class StrainIndexAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "assessment",
        "intensity_of_exertion",
        "efforts_per_minute",
        "speed_of_work",
    )
    list_select_related = ("assessment",)
    search_fields = ("assessment__assessment_id",)


@admin.register(SnookCirielloAssessment)
class SnookCirielloAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "assessment",
        "task_type",
        "gender",
        "position",
        "percentile",
        "actual_load",
        "ratio",
    )
    list_filter = ("task_type", "gender", "position")
    list_select_related = ("assessment",)
    search_fields = ("assessment__assessment_id",)


# =============================================================================
# CONTROLS
# =============================================================================
@admin.register(ErgonomicControl)
class ErgonomicControlAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "assessment",
        "control_type",
        "implemented",
        "implementation_date",
    )
    list_filter = ("control_type", "implemented")
    search_fields = ("assessment__assessment_id", "description")
    list_select_related = ("assessment",)


# =============================================================================
# CORRECTIVE ACTIONS
# =============================================================================
@admin.register(ErgonomicCorrectiveAction)
class ErgonomicCorrectiveActionAdmin(admin.ModelAdmin):
    list_display = (
        "action_id",
        "assessment",
        "priority",
        "status",
        "responsible_person",
        "target_date",
    )
    list_filter = ("status", "priority", "control_type", "department")
    search_fields = (
        "action_id",
        "action_description",
        "assessment__assessment_id",
        "responsible_person__first_name",
        "responsible_person__last_name",
    )
    readonly_fields = ("action_id", "created_at", "updated_at")
    list_select_related = ("assessment", "responsible_person", "department")
    date_hierarchy = "target_date"
    ordering = ("target_date", "id")


# =============================================================================
# REASSESSMENT
# =============================================================================
@admin.register(ErgonomicReassessment)
class ErgonomicReassessmentAdmin(admin.ModelAdmin):
    list_display = (
        "assessment",
        "reassessment_date",
        "previous_score",
        "new_score",
        "control_effectiveness",
        "risk_reduction_percent",
    )
    list_filter = ("control_effectiveness",)
    search_fields = ("assessment__assessment_id",)
    list_select_related = ("assessment",)
    date_hierarchy = "reassessment_date"


# =============================================================================
# QUICK OBSERVATIONS
# =============================================================================
@admin.register(ErgonomicObservation)
class ErgonomicObservationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "plant",
        "department",
        "task",
        "worker",
        "observation_date",
        "risk_level",
    )
    list_filter = ("risk_level", "plant", "department")
    search_fields = ("task", "observation", "worker__first_name", "worker__last_name")
    list_select_related = ("plant", "department", "worker", "observer")
    date_hierarchy = "observation_date"


# =============================================================================
# MSD / DISCOMFORT
# =============================================================================
@admin.register(MSDDiscomfort)
class MSDDiscomfortAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "worker",
        "department",
        "body_part",
        "severity",
        "date_reported",
        "medical_referral",
        "work_restriction",
    )
    list_filter = ("body_part", "severity", "medical_referral", "work_restriction")
    search_fields = (
        "worker__first_name",
        "worker__last_name",
        "job",
        "task",
        "discomfort_type",
    )
    list_select_related = ("worker", "department")
    date_hierarchy = "date_reported"


# =============================================================================
# EMPLOYEE / JOB MAPPING
# =============================================================================
@admin.register(ErgonomicJobMapping)
class ErgonomicJobMappingAdmin(admin.ModelAdmin):
    list_display = ("worker", "department", "job", "task", "is_active")
    list_filter = ("is_active", "department")
    search_fields = (
        "worker__first_name",
        "worker__last_name",
        "job",
        "task",
    )
    list_select_related = ("worker", "department")


# =============================================================================
# ASSESSMENT SCHEDULE
# =============================================================================
@admin.register(ErgonomicAssessmentSchedule)
class ErgonomicAssessmentScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "plant",
        "department",
        "job",
        "task",
        "due_date",
        "reason",
        "status",
    )
    list_filter = ("status", "reason", "plant", "department")
    search_fields = ("job", "task")
    list_select_related = ("plant", "department", "assigned_to")
    date_hierarchy = "due_date"
@admin.register(ErgonomicAuditLog)
class ErgonomicAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "user",
        "action",
        "model_name",
        "object_repr",
        "short_message",
    )
    list_filter = ("action", "model_name", "timestamp")
    search_fields = (
        "object_repr",
        "object_id",
        "message",
        "user__username",
        "user__first_name",
        "user__last_name",
    )
    readonly_fields = [f.name for f in ErgonomicAuditLog._meta.fields]
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)
    list_per_page = 100

    @admin.display(description="Message")
    def short_message(self, obj):
        return (obj.message or "")[:80]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser