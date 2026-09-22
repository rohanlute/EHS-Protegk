from django.contrib import admin
from .models import (HazardMaster,HazardCategoryMaster,ExposureTypeMaster,ExposureGroupMaster,
                     MonitoringTypeMaster,MonitoringParameterMaster)


# =============================================
# HazardMasterAdmin - Configures Hazard Master records in Django Admin.
# =============================================
@admin.register(HazardMaster)
class HazardMasterAdmin(admin.ModelAdmin):
    list_display = ("hazard_category","hazard","is_active","created_at","updated_at")
    list_filter = ("hazard_category","is_active")
    search_fields = ("hazard","hazard_category__category_name","description")
    ordering = ("hazard_category__category_name","hazard")


# =============================================
# HazardCategoryMasterAdmin - Configures Hazard Category Master records in Django Admin.
# =============================================
@admin.register(HazardCategoryMaster)
class HazardCategoryMasterAdmin(admin.ModelAdmin):
    list_display = ("category_name","is_active","created_at","updated_at")
    list_filter = ("is_active",)
    search_fields = ("category_name","description")
    ordering = ("category_name",)


# =============================================
# ExposureTypeMasterAdmin - Configures Exposure Type Master records in Django Admin.
# =============================================
@admin.register(ExposureTypeMaster)
class ExposureTypeMasterAdmin(admin.ModelAdmin):
    list_display = ("exposure_type","is_active","created_at","updated_at")
    list_filter = ("is_active",)
    search_fields = ("exposure_type","description")
    ordering = ("exposure_type",)




# =============================================
# ExposureGroupMasterAdmin - Configures Exposure Group / SEG Master in Django Admin.
# =============================================
@admin.register(ExposureGroupMaster)
class ExposureGroupMasterAdmin(admin.ModelAdmin):
    list_display = ("exposure_group","is_active","created_at","updated_at")
    list_filter = ("is_active",)
    search_fields = ("exposure_group","description")
    ordering = ("exposure_group",)



# =============================================
# MonitoringTypeMasterAdmin - Configures Monitoring Type Master records in Django Admin.
# =============================================
@admin.register(MonitoringTypeMaster)
class MonitoringTypeMasterAdmin(admin.ModelAdmin):
    list_display = ("monitoring_type","is_active","created_at","updated_at")
    list_filter = ("is_active",)
    search_fields = ("monitoring_type","description")
    ordering = ("monitoring_type",)



# =============================================
# MonitoringParameterMasterAdmin - Configures Monitoring Parameter Master records in Django Admin.
# =============================================
@admin.register(MonitoringParameterMaster)
class MonitoringParameterMasterAdmin(admin.ModelAdmin):
    list_display = ("parameter_name","is_active","created_at","updated_at")
    list_filter = ("is_active",)
    search_fields = ("parameter_name","description")
    ordering = ("parameter_name",)