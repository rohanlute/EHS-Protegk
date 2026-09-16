from django.urls import path

from . import views

app_name = "hira"

urlpatterns = [
    path("", views.HIRADashboardView.as_view(), name="dashboard"),
    path("register/", views.HIRAListView.as_view(), name="register"),
    path("create/", views.HIRACreateView.as_view(), name="create"),
    path("create/from-source/", views.HIRACreateFromSourceView.as_view(), name="create_from_source"),
    path("ajax/source-records/", views.HIRASourceRecordsAjaxView.as_view(), name="ajax_source_records"),
    path("<int:pk>/", views.HIRADetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.HIRAUpdateView.as_view(), name="edit"),
    path("<int:pk>/<str:action>/", views.HIRAStatusView.as_view(), name="status"),
    path("actions/", views.HIRAActionListView.as_view(), name="actions"),
    path("actions/<int:pk>/edit/", views.HIRAActionUpdateView.as_view(), name="action_edit"),
    path("masters/hazards/", views.HIRAHazardMasterListView.as_view(), name="hazard_master"),
    path("masters/hazards/create/", views.HIRAHazardMasterCreateView.as_view(), name="hazard_master_create"),
    path("masters/hazards/<int:pk>/", views.HIRAHazardMasterDetailView.as_view(), name="hazard_master_detail"),
    path("masters/hazards/<int:pk>/edit/", views.HIRAHazardMasterUpdateView.as_view(), name="hazard_master_edit"),
    path("masters/hazards/<int:pk>/toggle/", views.HIRAHazardMasterToggleView.as_view(), name="hazard_master_toggle"),
    path("masters/hazards/<int:pk>/delete/", views.HIRAHazardMasterDeleteView.as_view(), name="hazard_master_delete"),
    path("masters/risk-matrix/", views.HIRARiskMatrixListView.as_view(), name="risk_matrix_master"),
    path("masters/risk-matrix/create/", views.HIRARiskMatrixCreateView.as_view(), name="risk_matrix_create"),
    path("masters/risk-matrix/<int:pk>/edit/", views.HIRARiskMatrixUpdateView.as_view(), name="risk_matrix_edit"),
    path("masters/risk-matrix/levels/create/", views.HIRARiskMatrixLevelCreateView.as_view(), name="risk_matrix_level_create"),
    path("masters/risk-matrix/levels/<int:pk>/edit/", views.HIRARiskMatrixLevelUpdateView.as_view(), name="risk_matrix_level_edit"),
    path("masters/risk-matrix/levels/<int:pk>/delete/", views.HIRARiskMatrixLevelDeleteView.as_view(), name="risk_matrix_level_delete"),
    path("reports/", views.HIRAReportView.as_view(), name="report"),
    path("reports/export/", views.HIRAExcelExportView.as_view(), name="excel_export"),
]
