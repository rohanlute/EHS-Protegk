from django.urls import path
from apps.contractor import views

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
    path('onboarding/<int:pk>/delete/', views.OnboardingDeleteView.as_view(), name='onboarding_delete'),
    path('onboarding/bulk-delete/', views.OnboardingBulkDeleteView.as_view(), name='onboarding_bulk_delete'),
    
    # Document upload/verify
    path('document/<int:pk>/upload/', views.DocumentUploadView.as_view(), name='document_upload'),
    path('document/<int:pk>/verify/', views.DocumentVerifyView.as_view(), name='document_verify'),
    path('onboarding/<int:pk>/review/', views.OnboardingReviewView.as_view(), name='onboarding_review'),
    
    # API
    path('api/contractor-details/<int:pk>/', views.GetContractorDetailsView.as_view(), name='contractor_details_api'),
    
    # ==========================================================
    # CONTRACTOR PORTAL URLS (External Users)
    # ==========================================================
    # These are the portal URLs for external contractor access
    # Accessed via: /contractor/portal/login/, /contractor/portal/, etc.
    path('portal/login/', views.ContractorPortalLoginView.as_view(), name='portal_login'),
    path('portal/', views.ContractorPortalHomeView.as_view(), name='portal_home'),
    path('portal/logout/', views.ContractorPortalLogoutView.as_view(), name='portal_logout'),
    path('workorders/', views.WorkOrderListView.as_view(), name='workorder_list'),
    path('workorders/create/', views.WorkOrderCreateView.as_view(), name='workorder_create'),
    path('workorders/<int:pk>/', views.WorkOrderDetailView.as_view(), name='workorder_detail'),
    path('workorders/<int:pk>/edit/', views.WorkOrderUpdateView.as_view(), name='workorder_edit'),
    path('workorders/<int:pk>/delete/', views.WorkOrderDeleteView.as_view(), name='workorder_delete'),
    path('workorders/<int:pk>/status/', views.WorkOrderStatusUpdateView.as_view(), name='workorder_status_update'),
    path('workorders/bulk-delete/', views.WorkOrderBulkDeleteView.as_view(), name='workorder_bulk_delete'),
    
    # API URLs
    path('api/contractor-details/<int:pk>/', views.GetContractorDetailsView.as_view(), name='api_contractor_details'),
    path('api/contractor-workorders/<int:contractor_id>/', views.GetContractorWorkOrdersView.as_view(), name='api_contractor_workorders'),
    path('api/approved-contractors/', views.GetApprovedContractorsView.as_view(), name='api_approved_contractors'),
    path('workorders/review/', views.WorkOrderReviewListView.as_view(), name='workorder_review_list'),
    path('workorders/<int:pk>/review/', views.WorkOrderReviewView.as_view(), name='workorder_review'),
]