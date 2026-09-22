from django.urls import path
from . import views


app_name = "industrial_hygiene"


urlpatterns = [
    # Dashboard
    path("dashboard/",views.IndustrialHygieneDashboardView.as_view(),name="industrial_hygiene_dashboard"),

    # Report
    path("reports/",views.IndustrialHygieneReportsView.as_view(),name="reports"),
    

    # Hazard Master
    path("master/hazards/",views.HazardMasterListView.as_view(),name="hazard_list"),
    path("master/hazards/create/",views.HazardMasterCreateView.as_view(),name="hazard_create"),
    path("master/hazards/<int:pk>/edit/",views.HazardMasterUpdateView.as_view(),name="hazard_edit"),
    path("master/hazards/<int:pk>/delete/",views.HazardMasterDeleteView.as_view(),name="hazard_delete"),

    # Hazard Category Master
    path("master/hazard-categories/",views.HazardCategoryMasterListView.as_view(),name="hazard_category_list"),
    path("master/hazard-categories/create/",views.HazardCategoryMasterCreateView.as_view(),name="hazard_category_create"),
    path("master/hazard-categories/<int:pk>/edit/",views.HazardCategoryMasterUpdateView.as_view(),name="hazard_category_edit"),
    path("master/hazard-categories/<int:pk>/delete/",views.HazardCategoryMasterDeleteView.as_view(),name="hazard_category_delete"),

    # Exposure Type Master
    path("master/exposure-types/",views.ExposureTypeMasterListView.as_view(),name="exposure_type_list"),
    path("master/exposure-types/create/",views.ExposureTypeMasterCreateView.as_view(),name="exposure_type_create"),
    path("master/exposure-types/<int:pk>/edit/",views.ExposureTypeMasterUpdateView.as_view(),name="exposure_type_edit"),
    path("master/exposure-types/<int:pk>/delete/",views.ExposureTypeMasterDeleteView.as_view(),name="exposure_type_delete"),

    # Exposure Group / SEG Master
    path("master/exposure-groups/",views.ExposureGroupMasterListView.as_view(),name="exposure_group_list"),
    path("master/exposure-groups/create/",views.ExposureGroupMasterCreateView.as_view(),name="exposure_group_create"),
    path("master/exposure-groups/<int:pk>/edit/",views.ExposureGroupMasterUpdateView.as_view(),name="exposure_group_edit"),
    path("master/exposure-groups/<int:pk>/delete/",views.ExposureGroupMasterDeleteView.as_view(),name="exposure_group_delete"),

    # Monitoring Type Master
    path("master/monitoring-types/",views.MonitoringTypeMasterListView.as_view(),name="monitoring_type_list"),
    path("master/monitoring-types/create/",views.MonitoringTypeMasterCreateView.as_view(),name="monitoring_type_create"),
    path("master/monitoring-types/<int:pk>/edit/",views.MonitoringTypeMasterUpdateView.as_view(),name="monitoring_type_edit"),
    path("master/monitoring-types/<int:pk>/delete/",views.MonitoringTypeMasterDeleteView.as_view(),name="monitoring_type_delete"),

    # Monitoring Parameter Master
    path("master/monitoring-parameters/",views.MonitoringParameterMasterListView.as_view(),name="monitoring_parameter_list"),
    path("master/monitoring-parameters/create/",views.MonitoringParameterMasterCreateView.as_view(),name="monitoring_parameter_create"),
    path("master/monitoring-parameters/<int:pk>/edit/",views.MonitoringParameterMasterUpdateView.as_view(),name="monitoring_parameter_edit"),
    path("master/monitoring-parameters/<int:pk>/delete/",views.MonitoringParameterMasterDeleteView.as_view(),name="monitoring_parameter_delete"),

    # Unit Master
    path("master/units/",views.UnitMasterListView.as_view(),name="unit_list"),
    path("master/units/create/",views.UnitMasterCreateView.as_view(),name="unit_create"),
    path("master/units/<int:pk>/edit/",views.UnitMasterUpdateView.as_view(),name="unit_edit"),
    path("master/units/<int:pk>/delete/",views.UnitMasterDeleteView.as_view(),name="unit_delete"),

    # Exposure Limit / OEL Master
    path("master/exposure-limits/",views.ExposureLimitMasterListView.as_view(),name="exposure_limit_list"),
    path("master/exposure-limits/create/",views.ExposureLimitMasterCreateView.as_view(),name="exposure_limit_create"),
    path("master/exposure-limits/<int:pk>/edit/",views.ExposureLimitMasterUpdateView.as_view(),name="exposure_limit_edit"),
    path("master/exposure-limits/<int:pk>/delete/",views.ExposureLimitMasterDeleteView.as_view(),name="exposure_limit_delete"),

    # Instrument Master
    path("master/instruments/",views.InstrumentMasterListView.as_view(),name="instrument_list"),
    path("master/instruments/create/",views.InstrumentMasterCreateView.as_view(),name="instrument_create"),
    path("master/instruments/<int:pk>/edit/",views.InstrumentMasterUpdateView.as_view(),name="instrument_edit"),
    path("master/instruments/<int:pk>/delete/",views.InstrumentMasterDeleteView.as_view(),name="instrument_delete"),

    # Laboratory Master
    path("master/laboratories/",views.LaboratoryMasterListView.as_view(),name="laboratory_list"),
    path("master/laboratories/create/",views.LaboratoryMasterCreateView.as_view(),name="laboratory_create"),
    path("master/laboratories/<int:pk>/edit/",views.LaboratoryMasterUpdateView.as_view(),name="laboratory_edit"),
    path("master/laboratories/<int:pk>/delete/",views.LaboratoryMasterDeleteView.as_view(),name="laboratory_delete"),

    # =============================================
    # IH Program Management
    # =============================================
    path("programs/",views.IHProgramMasterListView.as_view(),name="ih_program_list"),
    path("programs/create/",views.IHProgramMasterCreateView.as_view(),name="ih_program_create"),
    path("programs/<int:pk>/edit/",views.IHProgramMasterUpdateView.as_view(),name="ih_program_edit"),
    path("programs/<int:pk>/",views.IHProgramMasterDetailView.as_view(),name="ih_program_detail"),


    # =============================================
    # Monitoring Plan Management
    # =============================================
    path("monitoring-plans/",views.MonitoringPlanListView.as_view(),name="monitoring_plan_list"),
    path("monitoring-plans/create/",views.MonitoringPlanCreateView.as_view(),name="monitoring_plan_create"),
    path("monitoring-plans/<int:pk>/",views.MonitoringPlanDetailView.as_view(),name="monitoring_plan_detail"),
    path("monitoring-plans/<int:pk>/edit/",views.MonitoringPlanUpdateView.as_view(),name="monitoring_plan_edit"),

    # =============================================
    # Monitoring Schedule Management
    # =============================================
    path("monitoring-schedules/",views.MonitoringScheduleListView.as_view(),name="monitoring_schedule_list"),
    path("monitoring-schedules/create/",views.MonitoringScheduleCreateView.as_view(),name="monitoring_schedule_create"),
    path("monitoring-schedules/<int:pk>/",views.MonitoringScheduleDetailView.as_view(),name="monitoring_schedule_detail"),
    path("monitoring-schedules/<int:pk>/edit/",views.MonitoringScheduleUpdateView.as_view(),name="monitoring_schedule_edit"),

    # =============================================
    # Sampling Management
    # =============================================
    path("sampling-management/",views.SamplingManagementListView.as_view(),name="sampling_management_list"),
    path("sampling-management/create/",views.SamplingManagementCreateView.as_view(),name="sampling_management_create"),
    path("sampling-management/<int:pk>/",views.SamplingManagementDetailView.as_view(),name="sampling_management_detail"),
    path("sampling-management/<int:pk>/edit/",views.SamplingManagementUpdateView.as_view(),name="sampling_management_edit"),

    # =============================================
    # Measurement Entry
    # =============================================
    path("measurement-entries/",views.MeasurementEntryListView.as_view(),name="measurement_entry_list"),
    path("measurement-entries/create/",views.MeasurementEntryCreateView.as_view(),name="measurement_entry_create"),
    path("measurement-entries/<int:pk>/",views.MeasurementEntryDetailView.as_view(),name="measurement_entry_detail"),
    path("measurement-entries/<int:pk>/edit/",views.MeasurementEntryUpdateView.as_view(),name="measurement_entry_edit"),

    # =============================================
    # Laboratory Result
    # =============================================
    path("laboratory-results/",views.LaboratoryResultListView.as_view(),name="laboratory_result_list"),
    path("laboratory-results/create/",views.LaboratoryResultCreateView.as_view(),name="laboratory_result_create"),
    path("laboratory-results/<int:pk>/",views.LaboratoryResultDetailView.as_view(),name="laboratory_result_detail"),
    path("laboratory-results/<int:pk>/edit/",views.LaboratoryResultUpdateView.as_view(),name="laboratory_result_edit"),

    # =============================================
    # Exposure Assessment
    # =============================================
    path("exposure-assessments/",views.ExposureAssessmentListView.as_view(),name="exposure_assessment_list"),
    path("exposure-assessments/create/",views.ExposureAssessmentCreateView.as_view(),name="exposure_assessment_create"),
    path("exposure-assessments/<int:pk>/",views.ExposureAssessmentDetailView.as_view(),name="exposure_assessment_detail"),
    path("exposure-assessments/<int:pk>/edit/",views.ExposureAssessmentUpdateView.as_view(),name="exposure_assessment_edit"),

    # =============================================
    # Compliance Management
    # =============================================
    path("compliance-records/",views.ComplianceRecordListView.as_view(),name="compliance_list"),
    path("compliance-records/create/",views.ComplianceRecordCreateView.as_view(),name="compliance_create"),
    path("compliance-records/<int:pk>/",views.ComplianceRecordDetailView.as_view(),name="compliance_detail"),
    path("compliance-records/<int:pk>/edit/",views.ComplianceRecordUpdateView.as_view(),name="compliance_edit"),

    # =============================================
    # Exceedance / Action Management
    # =============================================
    path("exceedance-actions/",views.ExceedanceActionListView.as_view(),name="exceedance_action_list"),
    path("exceedance-actions/create/",views.ExceedanceActionCreateView.as_view(),name="exceedance_action_create"),
    path("exceedance-actions/<int:pk>/",views.ExceedanceActionDetailView.as_view(),name="exceedance_action_detail"),
    path("exceedance-actions/<int:pk>/edit/",views.ExceedanceActionUpdateView.as_view(),name="exceedance_action_edit"),

    # =============================================
    # Re-Monitoring
    # =============================================
    path("re-monitoring/",views.ReMonitoringListView.as_view(),name="re_monitoring_list"),
    path("re-monitoring/create/",views.ReMonitoringCreateView.as_view(),name="re_monitoring_create"),
    path("re-monitoring/<int:pk>/",views.ReMonitoringDetailView.as_view(),name="re_monitoring_detail"),
    path("re-monitoring/<int:pk>/edit/",views.ReMonitoringUpdateView.as_view(),name="re_monitoring_edit"),

]