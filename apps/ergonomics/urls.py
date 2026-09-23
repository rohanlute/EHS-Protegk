from django.urls import path
from . import views, models, forms

app_name = "ergonomics"

urlpatterns = [
    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------
    path("", views.ErgonomicsDashboardView.as_view(), name="dashboard"),

    # -------------------------------------------------------------------------
    # Assessments
    # -------------------------------------------------------------------------
    path("assessments/", views.ErgonomicAssessmentListView.as_view(), name="assessments"),
    path("assessments/create/", views.ErgonomicAssessmentCreateView.as_view(), name="assessment_create"),
    path("assessments/<int:pk>/", views.ErgonomicAssessmentDetailView.as_view(), name="detail"),
    path("assessments/<int:pk>/edit/", views.ErgonomicAssessmentUpdateView.as_view(), name="assessment_edit"),
    path("assessments/<int:pk>/delete/", views.ErgonomicAssessmentDeleteView.as_view(), name="assessment_delete"),

    # Risk factors (one-to-one per assessment)
    path(
        "assessments/<int:assessment_pk>/risk-factors/",
        views.RiskFactorUpdateView.as_view(),
        name="risk_factors",
    ),

    # Method-specific scoring: rula / reba / niosh / owas / ocra / strain_index / snook_ciriello
    path(
        "assessments/<int:assessment_pk>/method/<str:method>/",
        views.MethodScoreUpdateView.as_view(),
        name="method_score",
    ),

    # Reassessment (dedicated view pre-fills previous score/risk)
    path(
        "assessments/<int:assessment_pk>/reassess/",
        views.ErgonomicReassessmentCreateView.as_view(),
        name="reassess",
    ),

    # Controls (dedicated view pre-fills assessment)
    path(
        "assessments/<int:assessment_pk>/controls/create/",
        views.ErgonomicControlCreateView.as_view(),
        name="control_create",
    ),

    # -------------------------------------------------------------------------
    # Quick observations
    # -------------------------------------------------------------------------
    path("observations/", views.ErgonomicObservationListView.as_view(), name="observations"),
    path("observations/create/", views.ErgonomicObservationCreateView.as_view(), name="observation_create"),
    path("observations/<int:pk>/convert/", views.ConvertObservationView.as_view(), name="observation_convert"),

    # -------------------------------------------------------------------------
    # Corrective actions
    # -------------------------------------------------------------------------
    path("actions/", views.CorrectiveActionListView.as_view(), name="actions"),
    path("actions/create/", views.CorrectiveActionCreateView.as_view(), name="action_create"),
    path("actions/<int:pk>/", views.CorrectiveActionDetailView.as_view(), name="action_detail"),
    path("actions/<int:pk>/edit/", views.CorrectiveActionUpdateView.as_view(), name="action_edit"),

    # -------------------------------------------------------------------------
    # My Actions — Responsible Person flow
    # -------------------------------------------------------------------------
    path("my-actions/", views.MyErgonomicActionsView.as_view(), name="my_actions"),
    path("my-actions/<int:pk>/edit/", views.MyActionUpdateView.as_view(), name="my_action_edit"),

    # -------------------------------------------------------------------------
    # MSD / Discomfort
    # -------------------------------------------------------------------------
    path("msd/", views.MSDDiscomfortListView.as_view(), name="msd_list"),
    path("msd/create/", views.MSDDiscomfortCreateView.as_view(), name="msd_create"),

    # -------------------------------------------------------------------------
    # Employee / Job Mapping
    # -------------------------------------------------------------------------
    path("job-mapping/", views.ErgonomicJobMappingListView.as_view(), name="job_mapping"),
    path("job-mapping/create/", views.ErgonomicJobMappingCreateView.as_view(), name="job_mapping_create"),

    # -------------------------------------------------------------------------
    # Assessment Schedule
    # -------------------------------------------------------------------------
    path("schedule/", views.ErgonomicAssessmentScheduleListView.as_view(), name="schedule"),
    path("schedule/create/", views.ErgonomicAssessmentScheduleCreateView.as_view(), name="schedule_create"),

    # -------------------------------------------------------------------------
    # Assessment Method Master
    # -------------------------------------------------------------------------
    path("methods/", views.ErgonomicAssessmentMethodListView.as_view(), name="method_list"),
    path("methods/create/", views.ErgonomicAssessmentMethodCreateView.as_view(), name="method_create"),

    # -------------------------------------------------------------------------
    # Reports / Analytics / API
    # -------------------------------------------------------------------------
    path("reports/export/", views.ErgonomicsReportExportView.as_view(), name="report_export"),
    path("reports/department/export/", views.DepartmentReportExportView.as_view(), name="department_report_export"),
    path("reports/management/export/", views.ManagementReportExportView.as_view(), name="management_report_export"),
    path("api/site-benchmarks/", views.SiteBenchmarksAPIView.as_view(), name="site_benchmarks_api"),
    
    # Verification queue
path(
    "verifications/",
    views.VerificationListView.as_view(),
    name="verifications",
),
path(
    "verifications/<int:pk>/",
    views.VerificationDetailView.as_view(),
    name="verification_detail",
),
path(
    "verifications/<int:pk>/approve/",
    views.ApproveActionView.as_view(),
    name="approve_action",
),
path(
    "verifications/<int:pk>/reject/",
    views.RejectActionView.as_view(),
    name="reject_action",
),
path(
    "observations/<int:pk>/convert/",
    views.ConvertObservationView.as_view(),
    name="observation_convert",
),
path(
    "observations/<int:pk>/convert/confirm/",
    views.ConvertObservationConfirmView.as_view(),
    name="observation_convert_confirm",
),
path("benchmarks/", views.SiteBenchmarksView.as_view(), name="site_benchmarks"),
path(
        "reports/ergonomic.pdf",
        views.ErgonomicsReportPDFView.as_view(),
        name="ergonomic_report_pdf",
    ),
]