from django.urls import path
from . import views

app_name = 'five_s'

urlpatterns = [
    # Questions
    path('questions/', views.QuestionListView.as_view(), name='question_list'),
    path('questions/new/', views.QuestionCreateView.as_view(), name='question_create'),
    path('questions/<int:pk>/', views.QuestionDetailView.as_view(), name='question_detail'),
    path('questions/<int:pk>/edit/', views.QuestionUpdateView.as_view(), name='question_edit'),
    path('questions/<int:pk>/deactivate/', views.QuestionDeactivateView.as_view(), name='question_deactivate'),
    path('questions/<int:pk>/reactivate/', views.QuestionReactivateView.as_view(), name='question_reactivate'),

    # Templates
    path('templates/', views.TemplateListView.as_view(), name='template_list'),
    path('templates/new/', views.TemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/', views.TemplateDetailView.as_view(), name='template_detail'),
    path('templates/<int:pk>/edit/', views.TemplateUpdateView.as_view(), name='template_edit'),
    path('templates/<int:pk>/clone/', views.TemplateCloneView.as_view(), name='template_clone'),
    path('templates/<int:pk>/deactivate/', views.TemplateDeactivateView.as_view(), name='template_deactivate'),

    # Template ↔ Question
    path('templates/<int:pk>/questions/add/', views.TemplateAddQuestionView.as_view(), name='template_add_question'),
    path('templates/<int:pk>/questions/bulk-add/', views.TemplateBulkAddQuestionsView.as_view(), name='template_bulk_add_questions'),
    path('templates/<int:pk>/questions/<int:question_pk>/remove/', views.TemplateRemoveQuestionView.as_view(), name='template_remove_question'),
    path('templates/<int:pk>/questions/<int:question_pk>/weight/', views.TemplateEditQuestionWeightView.as_view(), name='template_edit_question_weight'),

        # Schedules
    path('schedules/', views.ScheduleListView.as_view(), name='schedule_list'),
    path('schedules/new/', views.ScheduleCreateView.as_view(), name='schedule_create'),
    path('schedules/<int:pk>/', views.ScheduleDetailView.as_view(), name='schedule_detail'),
    path('schedules/<int:pk>/toggle-status/', views.ScheduleToggleStatusView.as_view(), name='schedule_toggle_status'),
    path('schedules/<int:pk>/transfer/', views.ScheduleTransferView.as_view(), name='schedule_transfer'),
    path('schedules/<int:pk>/edit/', views.ScheduleUpdateView.as_view(), name='schedule_edit'),
        # Location Cascading APIs
    path('api/zones/', views.GetZonesView.as_view(), name='get_zones'),
    path('api/locations/', views.GetLocationsView.as_view(), name='get_locations'),
    path('api/sublocations/', views.GetSublocationsView.as_view(), name='get_sublocations'),
    path('api/users-by-plant/', views.GetUsersByPlantView.as_view(), name='get_users_by_plant'),
    
     # My Inspections
    path('my-inspections/', views.MyInspectionsListView.as_view(), name='my_inspections'),
    path('my-inspections/<int:pk>/', views.InspectionFormView.as_view(), name='inspection_form'),
    
    path('audit/<int:pk>/', views.AuditDetailPageView.as_view(), name='audit_page'),
    path('actions/my/', views.MyActionsListView.as_view(), name='my_actions'),
    path('actions/<int:pk>/detail/', views.ActionDetailView.as_view(), name='action_detail'),
    path('actions/<int:pk>/complete/', views.ActionCompleteView.as_view(), name='action_complete'),
    path('actions/<int:pk>/approval/', views.ActionApprovalView.as_view(), name='action_approval'),
    path('actions/<int:pk>/submission/', views.ActionSubmissionDetailView.as_view(), name='action_submission_detail'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('findings/', views.AllFindingsListView.as_view(), name='all_findings'),
    path('all-actions/', views.AllActionsListView.as_view(), name='all_actions'),
    path('scorecards/', views.AreaScorecardView.as_view(), name='area_scorecards'),
    path('schedules/<int:pk>/report/', views.ScheduleReportView.as_view(), name='schedule_report'),
    path('audit/<int:pk>/pdf/',       views.AuditPDFView.as_view(),       name='audit_pdf'),
    
]