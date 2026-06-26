from django.contrib import admin

from .models import *


class EmergencySessionTrainerInline(admin.TabularInline):
    model = EmergencySessionTrainer
    extra = 1


class EmergencyReportPhotoInline(admin.TabularInline):
    model = EmergencyReportPhoto
    extra = 0


@admin.register(EmergencyTopic)
class EmergencyTopicAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "category", "is_active", "is_mandatory")
    list_filter = ("category", "is_active", "is_mandatory")
    search_fields = ("name", "code", "description")


@admin.register(EmergencySession)
class EmergencySessionAdmin(admin.ModelAdmin):
    list_display = ("session_number", "topic", "drill_type", "scheduled_date", "plant", "status")
    list_filter = ("status", "drill_type", "plant")
    search_fields = ("session_number", "topic__name")
    inlines = [EmergencySessionTrainerInline]


@admin.register(ERTDepartmentQuestion)
class ERTDepartmentQuestionAdmin(admin.ModelAdmin):
    list_display = ("question_code", "department", "question_type", "is_critical", "is_active")
    list_filter = ("department", "question_type", "is_critical", "is_active")
    search_fields = ("question_code", "question_text", "department__name")
    filter_horizontal = ("topics",)


@admin.register(EmergencySessionParticipant)
class EmergencySessionParticipantAdmin(admin.ModelAdmin):
    list_display = ("session", "employee", "status", "assigned_at", "completed_at")
    list_filter = ("status", "session__plant", "session__topic")
    search_fields = ("session__session_number", "employee__first_name", "employee__last_name", "employee__employee_id")


@admin.register(EmergencySessionSubmission)
class EmergencySessionSubmissionAdmin(admin.ModelAdmin):
    list_display = ("participant", "submitted_by", "review_status", "submitted_at", "reviewed_at")
    list_filter = ("review_status",)
    search_fields = ("participant__session__session_number", "participant__employee__first_name", "participant__employee__last_name")


@admin.register(EmergencyReport)
class EmergencyReportAdmin(admin.ModelAdmin):
    list_display = (
        "report_number",
        "emergency_title",
        "emergency_type",
        "severity_level",
        "incident_date",
        "plant",
        "incident_department",
        "department",
        "status",
    )
    list_filter = ("emergency_type", "severity_level", "status", "plant", "incident_department", "department")
    search_fields = ("report_number", "emergency_title", "description", "incident_department__name", "department__name")
    filter_horizontal = ("response_team_members",)
    inlines = [EmergencyReportPhotoInline]


@admin.register(EmergencyActionItem)
class EmergencyActionItemAdmin(admin.ModelAdmin):
    list_display = ("report", "status", "completion_datetime", "created_by")
    list_filter = ("status", "report__plant")
    search_fields = ("report__report_number", "action_description")
    filter_horizontal = ("assigned_to", "completed_by_users")


@admin.register(EmergencyInvestigationReport)
class EmergencyInvestigationReportAdmin(admin.ModelAdmin):
    list_display = ("report", "investigation_date", "investigator", "completed_date")
    search_fields = ("report__report_number", "sequence_of_events", "root_cause_analysis")

@admin.register(EmergencyCAPA)
class EmergencyCAPAAdmin(admin.ModelAdmin):
    list_display = ("capa_number", "report", "assigned_to", "target_date", "status", "closed_at")
    list_filter = ("status", "report__plant")
    search_fields = ("capa_number", "report__report_number", "action_required", "action_taken")
