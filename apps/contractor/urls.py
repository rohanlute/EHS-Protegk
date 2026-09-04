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
]