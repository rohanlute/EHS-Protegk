# apps/contractor/urls.py

from django.urls import path
from apps.contractor import views
from apps.contractor.views import (
    # ... other imports ...
    ContractorPerformanceDashboardView,
    ContractorPerformanceDetailView,
    ContractorReportsView,
    GenerateContractorOverallReportView,
    ContractorOverviewDashboardView,
     ContractorPerformanceDashboardView,
    ContractorPerformanceDetailView,
    ContractorReportsView,
    GenerateContractorOverallReportView,
    ContractorOverviewDashboardView,
)

app_name = 'contractor'

urlpatterns = [
    # ==========================================================
    # INTERNAL CONTRACTOR URLS (For Staff/Admin)
    # ==========================================================
    
    # Contractor CRUD
    path('', views.ContractorListView.as_view(), name='contractor_list'),
    path('add/', views.ContractorCreateView.as_view(), name='contractor_add'),
    path('<int:pk>/', views.ContractorDetailView.as_view(), name='contractor_detail'),
    path('<int:pk>/edit/', views.ContractorUpdateView.as_view(), name='contractor_edit'),
    path('<int:pk>/deactivate/', views.ContractorDeactivateView.as_view(), name='contractor_deactivate'),
    
    # Onboarding
    path('onboarding/', views.ContractorOnboardingView.as_view(), name='contractor_onboarding'),
    path('onboarding/list/', views.OnboardingListView.as_view(), name='onboarding_list'),
    path('onboarding/<int:pk>/', views.OnboardingDetailView.as_view(), name='onboarding_detail'),
    path('onboarding/<int:pk>/approve/', views.OnboardingApproveView.as_view(), name='onboarding_approve'),
    path('onboarding/<int:pk>/reject/', views.OnboardingRejectView.as_view(), name='onboarding_reject'),
    path('onboarding/<int:pk>/review/', views.OnboardingReviewView.as_view(), name='onboarding_review'),
    path('onboarding/<int:pk>/delete/', views.OnboardingDeleteView.as_view(), name='onboarding_delete'),
    path('onboarding/bulk-delete/', views.OnboardingBulkDeleteView.as_view(), name='onboarding_bulk_delete'),
    
    # Document upload/verify
    path('document/<int:pk>/upload/', views.DocumentUploadView.as_view(), name='document_upload'),
    path('document/<int:pk>/verify/', views.DocumentVerifyView.as_view(), name='document_verify'),
    
    # ==========================================================
    # CONTRACTOR PORTAL URLS (External Users)
    # ==========================================================
    path('portal/login/', views.ContractorPortalLoginView.as_view(), name='portal_login'),
    path('portal/', views.ContractorPortalHomeView.as_view(), name='portal_home'),
    path('portal/logout/', views.ContractorPortalLogoutView.as_view(), name='portal_logout'),
    
    # ==========================================================
    # WORK ORDER URLS
    # ==========================================================
    path('workorders/', views.WorkOrderListView.as_view(), name='workorder_list'),
    path('workorders/create/', views.WorkOrderCreateView.as_view(), name='workorder_create'),
    path('workorders/<int:pk>/', views.WorkOrderDetailView.as_view(), name='workorder_detail'),
    path('workorders/<int:pk>/edit/', views.WorkOrderUpdateView.as_view(), name='workorder_edit'),
    path('workorders/<int:pk>/delete/', views.WorkOrderDeleteView.as_view(), name='workorder_delete'),
    path('workorders/<int:pk>/status/', views.WorkOrderStatusUpdateView.as_view(), name='workorder_status_update'),
    path('workorders/bulk-delete/', views.WorkOrderBulkDeleteView.as_view(), name='workorder_bulk_delete'),
    path('workorders/review/', views.WorkOrderReviewListView.as_view(), name='workorder_review_list'),
    path('workorders/<int:pk>/review/', views.WorkOrderReviewView.as_view(), name='workorder_review'),
    
    # ==========================================================
    # TRAINING SIGN-OFF URLS
    # ==========================================================
    path('training-signoff/', views.TrainingSignOffListView.as_view(), name='training_signoff_list'),
    path('training-signoff/create/', views.TrainingSignOffCreateView.as_view(), name='training_signoff_create'),
    path('training-signoff/<int:pk>/', views.TrainingSignOffDetailView.as_view(), name='training_signoff_detail'),
    path('training-signoff/<int:pk>/upload-signature/', views.UploadSignOffSignatureView.as_view(), name='upload_signoff_signature'),
    path('training-signoff/<int:pk>/upload-supporting-document/', views.UploadSupportingDocumentView.as_view(), name='upload_supporting_document'),
    
    # ==========================================================
    # CONTRACTOR INSPECTION URLS
    # ==========================================================
    path('inspections/', views.ContractorInspectionListView.as_view(), name='inspection_list'),
    path('inspections/create/', views.ContractorInspectionCreateView.as_view(), name='inspection_create'),
    path('inspections/<int:pk>/', views.ContractorInspectionDetailView.as_view(), name='inspection_detail'),
    path('inspections/<int:pk>/edit/', views.ContractorInspectionUpdateView.as_view(), name='inspection_edit'),
    path('inspections/<int:pk>/conduct/', views.ContractorInspectionConductView.as_view(), name='inspection_conduct'),
    path('inspections/<int:pk>/cancel/', views.ContractorInspectionCancelView.as_view(), name='inspection_cancel'),
    path('inspections/<int:pk>/delete/', views.ContractorInspectionDeleteView.as_view(), name='inspection_delete'),
    path('inspections/my/', views.MyContractorInspectionsView.as_view(), name='my_inspections'),
    
    # ==========================================================
    # API URLS (AJAX)
    # ==========================================================
    # Contractor APIs - FIXED: Use correct view name
    path('api/contractor/<int:contractor_id>/details/', views.GetContractorDetailsAPIView.as_view(), name='api_contractor_details'),
    path('api/contractor/<int:contractor_id>/workorders/', views.GetContractorWorkOrdersAPIView.as_view(), name='api_contractor_workorders'),
    path('api/approved-contractors/', views.GetApprovedContractorsView.as_view(), name='api_approved_contractors'),
    path('api/contractor-workorders/<int:contractor_id>/', views.GetContractorWorkOrdersView.as_view(), name='api_contractor_workorders'),
    
    # Location Hierarchy APIs
    path('api/plant/<int:plant_id>/zones/', views.GetPlantZonesAPIView.as_view(), name='api_plant_zones'),
    path('api/zone/<int:zone_id>/locations/', views.GetZoneLocationsAPIView.as_view(), name='api_zone_locations'),
    path('api/location/<int:location_id>/sublocations/', views.GetLocationSublocationsAPIView.as_view(), name='api_location_sublocations'),
    path('api/plant/<int:plant_id>/users/', views.GetPlantUsersAPIView.as_view(), name='api_plant_users'),
    
    # Work Order APIs
    path('api/contractor/<int:contractor_id>/approved-workorders/', views.GetContractorApprovedWorkOrdersView.as_view(), name='api_contractor_approved_workorders'),
    
    # Training Sign-Off APIs
    path('api/workorder/<int:pk>/signoff-details/', views.GetWorkOrderSignoffDetailsView.as_view(), name='api_workorder_signoff_details'),
    path('api/training-session/<int:pk>/details/', views.GetTrainingSessionDetailsView.as_view(), name='api_training_session_details'),
    path('performance/', ContractorPerformanceDashboardView.as_view(), name='performance_dashboard'),
    path('performance/<int:pk>/', ContractorPerformanceDetailView.as_view(), name='performance_detail'),
    # apps/contractor/urls.py

    # Reports URLs
    path('reports/', ContractorReportsView.as_view(), name='reports_list'),
    path('reports/generate/', GenerateContractorOverallReportView.as_view(), name='generate_report'),
    path('reports/dashboard/', ContractorOverviewDashboardView.as_view(), name='overview_dashboard'),
    path('pdf/contractor/<int:pk>/', views.contractor_pdf_view, name='contractor_pdf'),
    path('pdf/workorder/<int:pk>/', views.work_order_pdf_view, name='workorder_pdf'),
    path('pdf/training-signoff/<int:pk>/', views.training_signoff_pdf_view, name='training_signoff_pdf'),
    path('pdf/inspection/<int:pk>/', views.inspection_pdf_view, name='inspection_pdf'),
    path('pdf/logbook/<int:year>/', views.contractor_logbook_pdf_view, name='contractor_logbook_pdf'),
    path('pdf/performance/<int:pk>/', views.performance_pdf_view, name='performance_pdf'),
    path('pdf/onboarding/<int:pk>/', views.onboarding_pdf_view, name='onboarding_pdf'),
]