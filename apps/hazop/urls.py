from django.urls import path
from . import views, views_analytics, views_version_control

app_name = "hazop"

urlpatterns = [
    # ========================================================
    # HAZOP DASHBOARD
    # ========================================================

    path(
        "",
        views.HazopDashboardView.as_view(),
        name="dashboard",
    ),

    # ========================================================
    # CONFIGURATION DASHBOARD
    # ========================================================

    path(
        "configuration/",
        views.HAZOPConfigurationDashboardView.as_view(),
        name="configuration",
    ),

    # ========================================================
    # STUDY TYPES
    # ========================================================

    path(
        "configuration/study-types/",
        views.HAZOPStudyTypeListView.as_view(),
        name="study_type_list",
    ),
    path(
        "configuration/study-types/create/",
        views.HAZOPStudyTypeCreateView.as_view(),
        name="study_type_create",
    ),
    path(
        "configuration/study-types/<int:pk>/edit/",
        views.HAZOPStudyTypeUpdateView.as_view(),
        name="study_type_edit",
    ),
    path(
        "configuration/study-types/<int:pk>/toggle/",
        views.HAZOPStudyTypeToggleView.as_view(),
        name="study_type_toggle",
    ),

    # ========================================================
    # STUDY STATUSES
    # ========================================================

    path(
        "configuration/study-statuses/",
        views.HAZOPStudyStatusListView.as_view(),
        name="study_status_list",
    ),
    path(
        "configuration/study-statuses/create/",
        views.HAZOPStudyStatusCreateView.as_view(),
        name="study_status_create",
    ),
    path(
        "configuration/study-statuses/<int:pk>/edit/",
        views.HAZOPStudyStatusUpdateView.as_view(),
        name="study_status_edit",
    ),
    path(
        "configuration/study-statuses/<int:pk>/toggle/",
        views.HAZOPStudyStatusToggleView.as_view(),
        name="study_status_toggle",
    ),

    # ========================================================
    # PARAMETERS
    # ========================================================

    path(
        "configuration/parameters/",
        views.HAZOPParameterListView.as_view(),
        name="parameter_list",
    ),
    path(
        "configuration/parameters/create/",
        views.HAZOPParameterCreateView.as_view(),
        name="parameter_create",
    ),
    path(
        "configuration/parameters/<int:pk>/edit/",
        views.HAZOPParameterUpdateView.as_view(),
        name="parameter_edit",
    ),
    path(
        "configuration/parameters/<int:pk>/toggle/",
        views.HAZOPParameterToggleView.as_view(),
        name="parameter_toggle",
    ),

    # ========================================================
    # GUIDE WORDS
    # ========================================================

    path(
        "configuration/guide-words/",
        views.HAZOPGuideWordListView.as_view(),
        name="guide_word_list",
    ),
    path(
        "configuration/guide-words/create/",
        views.HAZOPGuideWordCreateView.as_view(),
        name="guide_word_create",
    ),
    path(
        "configuration/guide-words/<int:pk>/edit/",
        views.HAZOPGuideWordUpdateView.as_view(),
        name="guide_word_edit",
    ),
    path(
        "configuration/guide-words/<int:pk>/toggle/",
        views.HAZOPGuideWordToggleView.as_view(),
        name="guide_word_toggle",
    ),

    # ========================================================
    # DEVIATION TEMPLATES
    # ========================================================

    path(
        "configuration/deviation-templates/",
        views.HAZOPDeviationTemplateListView.as_view(),
        name="deviation_template_list",
    ),
    path(
        "configuration/deviation-templates/create/",
        views.HAZOPDeviationTemplateCreateView.as_view(),
        name="deviation_template_create",
    ),
    path(
        "configuration/deviation-templates/<int:pk>/edit/",
        views.HAZOPDeviationTemplateUpdateView.as_view(),
        name="deviation_template_edit",
    ),
    path(
        "configuration/deviation-templates/<int:pk>/toggle/",
        views.HAZOPDeviationTemplateToggleView.as_view(),
        name="deviation_template_toggle",
    ),

    # ========================================================
    # STUDY METHODOLOGY
    # ========================================================

    path(
        "configuration/methodologies/",
        views.StudyMethodologyListView.as_view(),
        name="study_methodology_list",
    ),
    path(
        "configuration/methodologies/create/",
        views.StudyMethodologyCreateView.as_view(),
        name="study_methodology_create",
    ),
    path(
        "configuration/methodologies/<int:pk>/edit/",
        views.StudyMethodologyUpdateView.as_view(),
        name="study_methodology_edit",
    ),
    path(
        "configuration/methodologies/<int:pk>/toggle/",
        views.StudyMethodologyToggleView.as_view(),
        name="study_methodology_toggle",
    ),

    # ========================================================
    # STUDY PRIORITY
    # ========================================================

    path(
        "configuration/priorities/",
        views.StudyPriorityListView.as_view(),
        name="study_priority_list",
    ),
    path(
        "configuration/priorities/create/",
        views.StudyPriorityCreateView.as_view(),
        name="study_priority_create",
    ),
    path(
        "configuration/priorities/<int:pk>/edit/",
        views.StudyPriorityUpdateView.as_view(),
        name="study_priority_edit",
    ),
    path(
        "configuration/priorities/<int:pk>/toggle/",
        views.StudyPriorityToggleView.as_view(),
        name="study_priority_toggle",
    ),

    # ========================================================
    # PROCESS TYPE
    # ========================================================

    path(
        "configuration/process-types/",
        views.ProcessTypeListView.as_view(),
        name="process_type_list",
    ),
    path(
        "configuration/process-types/create/",
        views.ProcessTypeCreateView.as_view(),
        name="process_type_create",
    ),
    path(
        "configuration/process-types/<int:pk>/edit/",
        views.ProcessTypeUpdateView.as_view(),
        name="process_type_edit",
    ),
    path(
        "configuration/process-types/<int:pk>/toggle/",
        views.ProcessTypeToggleView.as_view(),
        name="process_type_toggle",
    ),

    # ========================================================
    # NODE TYPE
    # ========================================================

    path(
        "configuration/node-types/",
        views.NodeTypeListView.as_view(),
        name="node_type_list",
    ),
    path(
        "configuration/node-types/create/",
        views.NodeTypeCreateView.as_view(),
        name="node_type_create",
    ),
    path(
        "configuration/node-types/<int:pk>/edit/",
        views.NodeTypeUpdateView.as_view(),
        name="node_type_edit",
    ),
    path(
        "configuration/node-types/<int:pk>/toggle/",
        views.NodeTypeToggleView.as_view(),
        name="node_type_toggle",
    ),

    # ========================================================
    # EQUIPMENT TYPE
    # ========================================================

    path(
        "configuration/equipment-types/",
        views.EquipmentTypeListView.as_view(),
        name="equipment_type_list",
    ),
    path(
        "configuration/equipment-types/create/",
        views.EquipmentTypeCreateView.as_view(),
        name="equipment_type_create",
    ),
    path(
        "configuration/equipment-types/<int:pk>/edit/",
        views.EquipmentTypeUpdateView.as_view(),
        name="equipment_type_edit",
    ),
    path(
        "configuration/equipment-types/<int:pk>/toggle/",
        views.EquipmentTypeToggleView.as_view(),
        name="equipment_type_toggle",
    ),

    # ========================================================
    # CAUSE CATEGORY
    # ========================================================

    path(
        "configuration/cause-categories/",
        views.CauseCategoryListView.as_view(),
        name="cause_category_list",
    ),
    path(
        "configuration/cause-categories/create/",
        views.CauseCategoryCreateView.as_view(),
        name="cause_category_create",
    ),
    path(
        "configuration/cause-categories/<int:pk>/edit/",
        views.CauseCategoryUpdateView.as_view(),
        name="cause_category_edit",
    ),
    path(
        "configuration/cause-categories/<int:pk>/toggle/",
        views.CauseCategoryToggleView.as_view(),
        name="cause_category_toggle",
    ),

    # ========================================================
    # CONSEQUENCE CATEGORY
    # ========================================================

    path(
        "configuration/consequence-categories/",
        views.ConsequenceCategoryListView.as_view(),
        name="consequence_category_list",
    ),
    path(
        "configuration/consequence-categories/create/",
        views.ConsequenceCategoryCreateView.as_view(),
        name="consequence_category_create",
    ),
    path(
        "configuration/consequence-categories/<int:pk>/edit/",
        views.ConsequenceCategoryUpdateView.as_view(),
        name="consequence_category_edit",
    ),
    path(
        "configuration/consequence-categories/<int:pk>/toggle/",
        views.ConsequenceCategoryToggleView.as_view(),
        name="consequence_category_toggle",
    ),

    # ========================================================
    # SAFEGUARD CATEGORY
    # ========================================================

    path(
        "configuration/safeguard-categories/",
        views.SafeguardCategoryListView.as_view(),
        name="safeguard_category_list",
    ),
    path(
        "configuration/safeguard-categories/create/",
        views.SafeguardCategoryCreateView.as_view(),
        name="safeguard_category_create",
    ),
    path(
        "configuration/safeguard-categories/<int:pk>/edit/",
        views.SafeguardCategoryUpdateView.as_view(),
        name="safeguard_category_edit",
    ),
    path(
        "configuration/safeguard-categories/<int:pk>/toggle/",
        views.SafeguardCategoryToggleView.as_view(),
        name="safeguard_category_toggle",
    ),

    # ========================================================
    # RECOMMENDATION CATEGORY
    # ========================================================

    path(
        "configuration/recommendation-categories/",
        views.RecommendationCategoryListView.as_view(),
        name="recommendation_category_list",
    ),
    path(
        "configuration/recommendation-categories/create/",
        views.RecommendationCategoryCreateView.as_view(),
        name="recommendation_category_create",
    ),
    path(
        "configuration/recommendation-categories/<int:pk>/edit/",
        views.RecommendationCategoryUpdateView.as_view(),
        name="recommendation_category_edit",
    ),
    path(
        "configuration/recommendation-categories/<int:pk>/toggle/",
        views.RecommendationCategoryToggleView.as_view(),
        name="recommendation_category_toggle",
    ),

    # ========================================================
    # SEVERITY
    # ========================================================

    path(
        "configuration/severity/",
        views.SeverityListView.as_view(),
        name="severity_list",
    ),
    path(
        "configuration/severity/create/",
        views.SeverityCreateView.as_view(),
        name="severity_create",
    ),
    path(
        "configuration/severity/<int:pk>/edit/",
        views.SeverityUpdateView.as_view(),
        name="severity_edit",
    ),
    path(
        "configuration/severity/<int:pk>/toggle/",
        views.SeverityToggleView.as_view(),
        name="severity_toggle",
    ),

    # ========================================================
    # LIKELIHOOD
    # ========================================================

    path(
        "configuration/likelihood/",
        views.LikelihoodListView.as_view(),
        name="likelihood_list",
    ),
    path(
        "configuration/likelihood/create/",
        views.LikelihoodCreateView.as_view(),
        name="likelihood_create",
    ),
    path(
        "configuration/likelihood/<int:pk>/edit/",
        views.LikelihoodUpdateView.as_view(),
        name="likelihood_edit",
    ),
    path(
        "configuration/likelihood/<int:pk>/toggle/",
        views.LikelihoodToggleView.as_view(),
        name="likelihood_toggle",
    ),

    # ========================================================
    # REVIEW FREQUENCY
    # ========================================================

    path(
        "configuration/review-frequencies/",
        views.ReviewFrequencyListView.as_view(),
        name="review_frequency_list",
    ),
    path(
        "configuration/review-frequencies/create/",
        views.ReviewFrequencyCreateView.as_view(),
        name="review_frequency_create",
    ),
    path(
        "configuration/review-frequencies/<int:pk>/edit/",
        views.ReviewFrequencyUpdateView.as_view(),
        name="review_frequency_edit",
    ),
    path(
        "configuration/review-frequencies/<int:pk>/toggle/",
        views.ReviewFrequencyToggleView.as_view(),
        name="review_frequency_toggle",
    ),

    # ========================================================
    # PARAMETER-GUIDEWORD MAPPING
    # ========================================================

    path(
        "configuration/parameter-guideword-mapping/",
        views.ParameterGuideWordMappingListView.as_view(),
        name="parameter_guideword_mapping_list",
    ),
    path(
        "configuration/parameter-guideword-mapping/create/",
        views.ParameterGuideWordMappingCreateView.as_view(),
        name="parameter_guideword_mapping_create",
    ),
    path(
        "configuration/parameter-guideword-mapping/<int:pk>/edit/",
        views.ParameterGuideWordMappingUpdateView.as_view(),
        name="parameter_guideword_mapping_edit",
    ),
    path(
        "configuration/parameter-guideword-mapping/<int:pk>/toggle/",
        views.ParameterGuideWordMappingToggleView.as_view(),
        name="parameter_guideword_mapping_toggle",
    ),

    # ============================================================
    # HAZOP ORGANIZATION AJAX URLS
    # ============================================================

    path("ajax/zones/",views.zones_by_plant,name="zones_by_plant"),
    path("ajax/locations/",views.locations_by_zone,name="locations_by_zone"),
    path("ajax/sub-locations/",views.sub_locations_by_location,name="sub_locations_by_location"),

    # ========================================================
    # HAZOP STUDY REGISTER
    # ========================================================

    path(
        "studies/",
        views.HAZOPStudyListView.as_view(),
        name="study_list",
    ),

    path(
        "studies/create/",
        views.HAZOPStudyCreateView.as_view(),
        name="study_create",
    ),

    path(
        "studies/<int:pk>/edit/",
        views.HAZOPStudyUpdateView.as_view(),
        name="study_edit",
    ),


    # ============================================================
    # HAZOP NODE REGISTER
    # ============================================================

    path(
        "studies/<int:study_pk>/nodes/",
        views.HAZOPNodeListView.as_view(),
        name="node_list",
    ),

    path(
        "studies/<int:study_pk>/nodes/create/",
        views.HAZOPNodeCreateView.as_view(),
        name="node_create",
    ),

    path(
        "studies/<int:study_pk>/nodes/<int:pk>/edit/",
        views.HAZOPNodeUpdateView.as_view(),
        name="node_edit",
    ),


    # ==========================================================
    # HAZOP WORKSHEET
    # ==========================================================

    path(
        "nodes/<int:node_pk>/worksheet/",
        views.HAZOPWorksheetEntryListView.as_view(),
        name="worksheet_list",
    ),

    path(
        "nodes/<int:node_pk>/worksheet/create/",
        views.HAZOPWorksheetEntryCreateView.as_view(),
        name="worksheet_create",
    ),

    path(
        "nodes/<int:node_pk>/worksheet/<int:pk>/edit/",
        views.HAZOPWorksheetEntryUpdateView.as_view(),
        name="worksheet_edit",
    ),

    # Cause
    path(
        "worksheet/<int:entry_pk>/causes/",
        views.HAZOPCauseListView.as_view(),
        name="cause_list",
    ),
    path(
        "worksheet/<int:entry_pk>/causes/create/",
        views.HAZOPCauseCreateView.as_view(),
        name="cause_create",
    ),
    path(
        "worksheet/<int:entry_pk>/causes/<int:pk>/edit/",
        views.HAZOPCauseUpdateView.as_view(),
        name="cause_edit",
    ),
    path(
        "worksheet/<int:entry_pk>/causes/<int:pk>/deactivate/",
        views.HAZOPCauseDeactivateView.as_view(),
        name="cause_deactivate",
    ),

    # Consequence
    path(
        "worksheet/<int:entry_pk>/consequences/",
        views.HAZOPConsequenceListView.as_view(),
        name="consequence_list",
    ),
    path(
        "worksheet/<int:entry_pk>/consequences/create/",
        views.HAZOPConsequenceCreateView.as_view(),
        name="consequence_create",
    ),
    path(
        "worksheet/<int:entry_pk>/consequences/<int:pk>/edit/",
        views.HAZOPConsequenceUpdateView.as_view(),
        name="consequence_edit",
    ),
    path(
        "worksheet/<int:entry_pk>/consequences/<int:pk>/deactivate/",
        views.HAZOPConsequenceDeactivateView.as_view(),
        name="consequence_deactivate",
    ),

    # Safeguard
    path(
        "worksheet/<int:entry_pk>/safeguards/",
        views.HAZOPSafeguardListView.as_view(),
        name="safeguard_list",
    ),
    path(
        "worksheet/<int:entry_pk>/safeguards/create/",
        views.HAZOPSafeguardCreateView.as_view(),
        name="safeguard_create",
    ),
    path(
        "worksheet/<int:entry_pk>/safeguards/<int:pk>/edit/",
        views.HAZOPSafeguardUpdateView.as_view(),
        name="safeguard_edit",
    ),
    path(
        "worksheet/<int:entry_pk>/safeguards/<int:pk>/deactivate/",
        views.HAZOPSafeguardDeactivateView.as_view(),
        name="safeguard_deactivate",
    ),


    # Risk Matrix
    path(
        "risk-matrix/",
        views.hazop_risk_matrix_list,
        name="risk_matrix_list",
    ),

    path(
        "risk-matrix/create/",
        views.hazop_risk_matrix_create,
        name="risk_matrix_create",
    ),

    path(
        "risk-matrix/<int:matrix_pk>/ratings/",
        views.hazop_risk_matrix_rating_create,
        name="risk_matrix_rating_create",
    ),

    path(
        "risk-levels/",
        views.hazop_risk_level_list,
        name="risk_level_list",
    ),

    # Risk Assessment
    path(
        "node/<int:node_pk>/risk-assessments/",
        views.hazop_risk_assessment_list,
        name="risk_assessment_list",
    ),

    path(
        "node/<int:node_pk>/worksheet/<int:entry_pk>/risk-assessment/create/",
        views.hazop_risk_assessment_create,
        name="risk_assessment_create",
    ),

    path(
        "risk-assessment/<int:assessment_pk>/",
        views.hazop_risk_assessment_detail,
        name="risk_assessment_detail",
    ),

    path(
        "risk-assessment/<int:assessment_pk>/edit/",
        views.hazop_risk_assessment_edit,
        name="risk_assessment_edit",
    ),

    path(
        "risk-assessments/<int:assessment_pk>/submit/",
        views.risk_assessment_submit,
        name="risk_assessment_submit",
    ),

    path(
        "risk-assessments/<int:assessment_pk>/start-review/",
        views.risk_assessment_start_review,
        name="risk_assessment_start_review",
    ),

    path(
        "risk-assessments/<int:assessment_pk>/submit-review/",
        views.risk_assessment_submit_review,
        name="risk_assessment_submit_review",
    ),

    path(
        "risk-assessments/<int:assessment_pk>/reject/",
        views.risk_assessment_reject,
        name="risk_assessment_reject",
    ),

    path(
        "risk-assessments/<int:assessment_pk>/approve/",
        views.risk_assessment_approve,
        name="risk_assessment_approve",
    ),

    path(
        "risk-assessments/<int:assessment_pk>/close/",
        views.risk_assessment_close,
        name="risk_assessment_close",
    ),

    path(
        "actions/",
        views.hazop_action_list,
        name="hazop_action_list",
    ),

    path(
        "actions/create/",
        views.hazop_action_create,
        name="hazop_action_create",
    ),

    path(
        "actions/<int:pk>/edit/",
        views.hazop_action_edit,
        name="hazop_action_edit",
    ),

    path(
        "actions/<int:pk>/",
        views.hazop_action_detail,
        name="hazop_action_detail",
    ),

    path(
        "actions/<int:pk>/workflow/",
        views.hazop_action_workflow,
        name="hazop_action_workflow",
    ),

    path(
        "risk-assessment/<int:assessment_pk>/export-excel/",
        views.risk_assessment_export_excel,
        name="risk_assessment_export_excel",
    ),

    path(
        "analytics/",
        views_analytics.hazop_analytics_dashboard,
        name="analytics_dashboard",
    ),

    path(
        "analytics/export-excel/",
        views_analytics.hazop_analytics_export_excel,
        name="analytics_export_excel",
    ),

    # ============================================================
    # HAZOP VERSION CONTROL
    # ============================================================

    path(
        "studies/<int:study_id>/versions/",
        views_version_control.hazop_version_history,
        name="version_history",
    ),

    path(
        "studies/<int:study_id>/versions/create/",
        views_version_control.hazop_create_version,
        name="create_version",
    ),

    path(
        "studies/<int:study_id>/versions/compare/",
        views_version_control.hazop_compare_versions,
        name="compare_versions",
    ),
]