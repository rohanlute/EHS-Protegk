from django.contrib import admin

from .models import HIRA, HIRAAction, HIRAHazard, HIRAModule, HazardRiskMaster, RiskMatrix, RiskMatrixLevel


class HIRAHazardInline(admin.TabularInline):
    model = HIRAHazard
    extra = 0
    readonly_fields = ("initial_risk_score", "initial_risk_level", "residual_risk_score", "residual_risk_level")


@admin.register(HIRAModule)
class HIRAModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}


class RiskMatrixLevelInline(admin.TabularInline):
    model = RiskMatrixLevel
    extra = 0


@admin.register(RiskMatrix)
class RiskMatrixAdmin(admin.ModelAdmin):
    list_display = ("name", "min_likelihood", "max_likelihood", "min_severity", "max_severity", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    inlines = [RiskMatrixLevelInline]


@admin.register(HazardRiskMaster)
class HazardRiskMasterAdmin(admin.ModelAdmin):
    list_display = ("module", "activity", "hazard_category", "default_likelihood", "default_severity", "is_active")
    list_filter = ("module", "hazard_category", "is_active")
    search_fields = ("activity", "process", "hazard", "consequence")


@admin.register(HIRA)
class HIRAAdmin(admin.ModelAdmin):
    list_display = ("hira_number", "plant", "department", "module", "process", "status", "assessment_date")
    list_filter = ("status", "module", "plant", "department")
    search_fields = ("hira_number", "process")
    readonly_fields = ("hira_number", "created_at", "updated_at")
    inlines = [HIRAHazardInline]


@admin.register(HIRAHazard)
class HIRAHazardAdmin(admin.ModelAdmin):
    list_display = ("hira", "activity", "hazard_category", "initial_risk_score", "initial_risk_level", "residual_risk_score", "residual_risk_level")
    list_filter = ("hazard_category", "initial_risk_level", "residual_risk_level")
    search_fields = ("activity", "hazard", "hira__hira_number")
    readonly_fields = ("initial_risk_score", "initial_risk_level", "residual_risk_score", "residual_risk_level")


@admin.register(HIRAAction)
class HIRAActionAdmin(admin.ModelAdmin):
    list_display = ("action_id", "hazard", "responsible_person", "target_date", "priority", "status")
    list_filter = ("priority", "status")
    search_fields = ("action_id", "action_description", "hazard__hira__hira_number")
    readonly_fields = ("action_id", "created_at", "updated_at")
