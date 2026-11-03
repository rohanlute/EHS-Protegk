from django.urls import path, include
from . import views

app_name = 'kaizen'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('source-records/', views.KaizenRelatedRecordSearchView.as_view(), name='source_records'),
    path('register/', views.KaizenListView.as_view(), name='kaizen_list'),
    path('create/', views.KaizenCreateView.as_view(), name='kaizen_create'),
    path('<int:pk>/edit/', views.KaizenEditView.as_view(), name='kaizen_edit'),
    path('mine/', views.MyKaizenListView.as_view(), name='my_kaizens'),
    path('actions/', views.MyKaizenActionsView.as_view(), name='my_actions'),
    path('implementation/<int:pk>/complete/', views.KaizenImplementationCompletionView.as_view(), name='implementation_completion'),
    path('<int:pk>/', views.KaizenDetailView.as_view(), name='kaizen_detail'),
    path('<int:kaizen_id>/review/', views.KaizenInitialReviewCreateView.as_view(), name='initial_review'),
    path('<int:kaizen_id>/technical-evaluation/', views.KaizenTechnicalEvaluationCreateView.as_view(), name='technical_evaluation'),
    path('<int:kaizen_id>/approval/', views.KaizenApprovalCreateView.as_view(), name='approval'),
    path('<int:kaizen_id>/implementation/create/', views.KaizenImplementationCreateView.as_view(), name='implementation_create'),
    path('implementation/<int:pk>/update/', views.KaizenImplementationUpdateView.as_view(), name='implementation_update'),
    path('<int:kaizen_id>/verification/', views.KaizenVerificationCreateView.as_view(), name='verification'),
    path('<int:kaizen_id>/attachments/add/', views.KaizenAttachmentCreateView.as_view(), name='attachment_create'),
    path('<int:kaizen_id>/closure/', views.KaizenClosureCreateView.as_view(), name='closure'),
    path('<int:pk>/final-report/', views.KaizenFinalReportView.as_view(), name='final_report'),
    path('<int:kaizen_id>/history/', views.KaizenHistoryListView.as_view(), name='history'),

    # Configuration
    path('category/', views.KaizenCategoryListView.as_view(), name='category_list'),
    path('category/create/', views.KaizenCategoryCreateView.as_view(), name='category_create'),
    path('category/<int:pk>/update/', views.KaizenCategoryUpdateView.as_view(), name='category_update'),
    path('category/<int:pk>/delete/', views.KaizenCategoryDeleteView.as_view(), name='category_delete'),
]