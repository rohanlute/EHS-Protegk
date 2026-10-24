from django.urls import path
from .views import *

app_name = 'permit'

urlpatterns = [
    # Configuration URLs
    path('permit-types/', PermitTypeListView.as_view(), name='permit_type_list'),
    path('permit-types/create/', PermitTypeCreateView.as_view(), name='permit_type_create'),
    path('permit-types/<int:pk>/edit/', PermitTypeUpdateView.as_view(), name='permit_type_update'),
    path('permit-types/<int:pk>/delete/', PermitTypeDeleteView.as_view(), name='permit_type_delete'),

    # Permit URLs
    path('permits/create/', PermitCreateView.as_view(), name='permit_create'),
    path('permits/permit-list/', PermitListView.as_view(), name='permit_list'),
    path('permits/analytics/', PermitAnalyticsDashboardView.as_view(), name='permit_analytics'),
    path('permits/<int:pk>/', PermitDetailView.as_view(), name='permit_detail'),
    path('permits/<int:pk>/edit/', PermitUpdateView.as_view(), name='permit_update'),
    path('permits/approvals/', PermitApprovalDashboardView.as_view(), name='permit_approvals'),
    path('permits/<int:pk>/approve/', PermitApprovalView.as_view(), name='permit_approve'),
    path('permits/approvals/', PermitApprovalDashboardView.as_view(), name='permit_approvals'),
    path('permits/<int:pk>/approve/', PermitApprovalView.as_view(), name='permit_approve'),
    path('permits/<int:pk>/reject/', PermitRejectView.as_view(), name='permit_reject'),
    path('permits/<int:pk>/close/', PermitCloseView.as_view(), name='permit_close'),
    path('permits/<int:pk>/extend/', PermitExtensionRequestView.as_view(), name='permit_extend'),
    path('permits/<int:pk>/pdf/', PermitPDFView.as_view(), name='permit_pdf'),
    # path('extensions/<int:pk>/review/', PermitExtensionReviewView.as_view(), name='extension_review'),

    ]
