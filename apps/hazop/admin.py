from django.contrib import admin

from .models import (
    HAZOPStudyType,
    HAZOPStudyStatus,
    HAZOPParameter,
    HAZOPGuideWord,
    HAZOPDeviationTemplate,
    HAZOPStudyMethodology,
    HAZOPStudyPriority,
    HAZOPProcessType,
    HAZOPNodeType,
    HAZOPEquipmentType,
    HAZOPCauseCategory,
    HAZOPConsequenceCategory,
    HAZOPSafeguardCategory,
    HAZOPRecommendationCategory,
    HAZOPSeverity,
    HAZOPLikelihood,
    HAZOPReviewFrequency,
    HAZOPParameterGuideWordMapping,
    HAZOPRiskLevel,
    HAZOPRiskMatrix,
    HAZOPRiskRating,
    HAZOPRiskAssessment,
)


@admin.register(HAZOPStudyType)
class HAZOPStudyTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_system_default", "is_active")
    list_filter = ("is_active", "is_system_default")
    search_fields = ("code", "name")
    ordering = ("name",)


@admin.register(HAZOPStudyStatus)
class HAZOPStudyStatusAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "sequence",
        "is_terminal",
        "is_system_default",
        "is_active",
    )
    list_filter = ("is_active", "is_terminal", "is_system_default")
    search_fields = ("code", "name")
    ordering = ("sequence", "name")


@admin.register(HAZOPParameter)
class HAZOPParameterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_system_default", "is_active")
    list_filter = ("is_active", "is_system_default")
    search_fields = ("code", "name")
    ordering = ("name",)


@admin.register(HAZOPGuideWord)
class HAZOPGuideWordAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_system_default", "is_active")
    list_filter = ("is_active", "is_system_default")
    search_fields = ("code", "name")
    ordering = ("name",)


@admin.register(HAZOPDeviationTemplate)
class HAZOPDeviationTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "parameter",
        "guide_word",
        "deviation_text",
        "is_system_default",
        "is_active",
    )
    list_filter = (
        "parameter",
        "guide_word",
        "is_active",
        "is_system_default",
    )
    search_fields = (
        "code",
        "deviation_text",
        "parameter__name",
        "guide_word__name",
    )
    ordering = ("parameter__name", "guide_word__name")



# ============================================================
# COMMON HAZOP CONFIGURATION ADMIN
# ============================================================

class HAZOPConfigMasterAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "is_system_default",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "is_system_default",
    )

    search_fields = (
        "code",
        "name",
        "description",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("name",)


# ============================================================
# HAZOP CONFIGURATION MASTERS
# ============================================================

@admin.register(HAZOPStudyMethodology)
class HAZOPStudyMethodologyAdmin(HAZOPConfigMasterAdmin):
    pass


@admin.register(HAZOPStudyPriority)
class HAZOPStudyPriorityAdmin(HAZOPConfigMasterAdmin):
    list_display = (
        "code",
        "name",
        "priority_order",
        "is_active",
    )

    ordering = ("priority_order", "name")


@admin.register(HAZOPProcessType)
class HAZOPProcessTypeAdmin(HAZOPConfigMasterAdmin):
    pass


@admin.register(HAZOPNodeType)
class HAZOPNodeTypeAdmin(HAZOPConfigMasterAdmin):
    pass


@admin.register(HAZOPEquipmentType)
class HAZOPEquipmentTypeAdmin(HAZOPConfigMasterAdmin):
    pass


@admin.register(HAZOPCauseCategory)
class HAZOPCauseCategoryAdmin(HAZOPConfigMasterAdmin):
    pass


@admin.register(HAZOPConsequenceCategory)
class HAZOPConsequenceCategoryAdmin(HAZOPConfigMasterAdmin):
    pass


@admin.register(HAZOPSafeguardCategory)
class HAZOPSafeguardCategoryAdmin(HAZOPConfigMasterAdmin):
    pass


@admin.register(HAZOPRecommendationCategory)
class HAZOPRecommendationCategoryAdmin(HAZOPConfigMasterAdmin):
    pass


@admin.register(HAZOPSeverity)
class HAZOPSeverityAdmin(HAZOPConfigMasterAdmin):
    list_display = (
        "code",
        "name",
        "severity_score",
        "is_active",
    )

    ordering = ("severity_score",)


@admin.register(HAZOPLikelihood)
class HAZOPLikelihoodAdmin(HAZOPConfigMasterAdmin):
    list_display = (
        "code",
        "name",
        "likelihood_score",
        "is_active",
    )

    ordering = ("likelihood_score",)


@admin.register(HAZOPReviewFrequency)
class HAZOPReviewFrequencyAdmin(HAZOPConfigMasterAdmin):
    list_display = (
        "code",
        "name",
        "interval_days",
        "is_active",
    )

    ordering = ("interval_days",)


# ============================================================
# PARAMETER-GUIDEWORD MAPPING
# ============================================================

@admin.register(HAZOPParameterGuideWordMapping)
class HAZOPParameterGuideWordMappingAdmin(admin.ModelAdmin):
    list_display = (
        "parameter",
        "guide_word",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "parameter",
        "guide_word",
    )

    search_fields = (
        "parameter__name",
        "parameter__code",
        "guide_word__name",
        "guide_word__code",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "parameter",
        "guide_word",
    )

    ordering = (
        "parameter__name",
        "guide_word__name",
    )




@admin.register(HAZOPRiskLevel)
class HAZOPRiskLevelAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "minimum_score",
        "maximum_score",
        "requires_action",
        "is_active",
    )

    list_editable = (
        "requires_action",
        "is_active",
    )

    ordering = ("minimum_score",)


@admin.register(HAZOPRiskMatrix)
class HAZOPRiskMatrixAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "likelihood_scale",
        "severity_scale",
        "is_default",
        "is_active",
    )

    list_filter = (
        "is_default",
        "is_active",
    )


@admin.register(HAZOPRiskRating)
class HAZOPRiskRatingAdmin(admin.ModelAdmin):
    list_display = (
        "matrix",
        "rating_type",
        "score",
        "name",
        "is_active",
    )

    list_filter = (
        "matrix",
        "rating_type",
        "is_active",
    )


@admin.register(HAZOPRiskAssessment)
class HAZOPRiskAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "assessment_number",
        "hazard_title",
        "initial_likelihood",
        "initial_severity",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "matrix",
    )

    search_fields = (
        "assessment_number",
        "hazard_title",
        "hazard_description",
    )

    readonly_fields = (
        "assessment_number",
        "created_at",
        "updated_at",
    )