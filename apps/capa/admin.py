from django.contrib import admin

from apps.capa.models import (
    CAPA,
    CAPAAttachment,
    CAPAAuditLog,
    CAPAAction,
    CAPAActionCompletion,
    CAPAActionVerification,
    CAPAApproval,
    CAPAComment,
    CAPAEffectivenessReview,
    CAPAInvestigation,
)


class CAPAActionInline(admin.TabularInline):
    model = CAPAAction
    extra = 0


class CAPAAttachmentInline(admin.TabularInline):
    model = CAPAAttachment
    extra = 0


class CAPACommentInline(admin.TabularInline):
    model = CAPAComment
    extra = 0


@admin.register(CAPA)
class CAPAAdmin(admin.ModelAdmin):
    list_display = ("capa_number", "title", "plant", "owner", "status", "severity", "priority", "target_date", "created_at")
    list_filter = ("status", "severity", "priority", "source_type", "plant", "department")
    search_fields = ("capa_number", "title", "source_reference")
    readonly_fields = ("capa_number", "created_at", "updated_at", "closed_date", "reopened_date")
    inlines = [CAPAActionInline, CAPAAttachmentInline, CAPACommentInline]


@admin.register(CAPAInvestigation)
class CAPAInvestigationAdmin(admin.ModelAdmin):
    list_display = ("capa", "investigation_date", "lead_investigator", "investigation_method", "root_cause_category")
    search_fields = ("capa__capa_number", "problem_statement", "final_root_cause")


@admin.register(CAPAAction)
class CAPAActionAdmin(admin.ModelAdmin):
    list_display = ("capa", "action_plan_type", "assigned_to", "status", "target_date", "priority")
    list_filter = ("status", "action_plan_type", "priority")
    search_fields = ("capa__capa_number", "action_description")


@admin.register(CAPAActionCompletion)
class CAPAActionCompletionAdmin(admin.ModelAdmin):
    list_display = ("action", "completed_by", "completion_date", "submitted_for_verification")


@admin.register(CAPAActionVerification)
class CAPAActionVerificationAdmin(admin.ModelAdmin):
    list_display = ("action", "verified_by", "verification_date", "result")


@admin.register(CAPAEffectivenessReview)
class CAPAEffectivenessReviewAdmin(admin.ModelAdmin):
    list_display = ("capa", "reviewed_by", "review_date", "result")


@admin.register(CAPAAttachment)
class CAPAAttachmentAdmin(admin.ModelAdmin):
    list_display = ("capa", "action", "title", "uploaded_by", "uploaded_at")


@admin.register(CAPAComment)
class CAPACommentAdmin(admin.ModelAdmin):
    list_display = ("capa", "author", "created_at")


@admin.register(CAPAApproval)
class CAPAApprovalAdmin(admin.ModelAdmin):
    list_display = ("capa", "approval_type", "approved_by", "approved_at", "decision")


@admin.register(CAPAAuditLog)
class CAPAAuditLogAdmin(admin.ModelAdmin):
    list_display = ("capa", "user", "timestamp", "action")
    readonly_fields = ("capa", "user", "timestamp", "action", "old_value", "new_value", "comments")
