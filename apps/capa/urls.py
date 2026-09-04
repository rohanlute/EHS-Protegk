from django.urls import path

from apps.capa import views


app_name = "capa"

urlpatterns = [
    path("", views.CAPADashboardView.as_view(), name="dashboard"),
    path("list/", views.CAPAListView.as_view(), name="list"),
    path("create/", views.CAPACreateView.as_view(), name="create"),
    path("create/from/incident/<int:incident_id>/", views.CAPASourceCreateFromIncidentView.as_view(), name="create_from_incident"),
    path("create/from/hazard/<int:hazard_id>/", views.CAPASourceCreateFromHazardView.as_view(), name="create_from_hazard"),
    path("source-references/", views.CAPASourceReferenceView.as_view(), name="source_references"),
    path("<int:pk>/", views.CAPADetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.CAPAUpdateView.as_view(), name="edit"),
    path("<int:pk>/investigation/", views.CAPAInvestigationView.as_view(), name="investigation"),
    path("<int:pk>/investigation/detail/", views.CAPAInvestigationDetailView.as_view(), name="investigation_detail"),
    path("<int:pk>/investigation/review/", views.CAPAInvestigationReviewView.as_view(), name="investigation_review"),
    path("<int:pk>/actions/add/", views.CAPAActionCreateView.as_view(), name="action_add"),
    path("my-action-items/", views.CAPAMyActionItemsView.as_view(), name="my_action_items"),
    path("actions/<int:pk>/complete/", views.CAPAActionCompletionView.as_view(), name="action_complete"),
    path("actions/<int:pk>/verify/", views.CAPAActionVerificationView.as_view(), name="action_verify"),
    path("<int:pk>/effectiveness/", views.CAPAEffectivenessReviewView.as_view(), name="effectiveness"),
    path("<int:pk>/close/", views.CAPAClosureView.as_view(), name="close"),
    path("<int:pk>/reopen/", views.CAPAReopenView.as_view(), name="reopen"),
    path("<int:pk>/comments/add/", views.CAPACommentCreateView.as_view(), name="comment_add"),
    path("<int:pk>/attachments/add/", views.CAPAAttachmentCreateView.as_view(), name="attachment_add"),
    path("actions/<int:pk>/", views.CAPAActionDetailView.as_view(), name="action_detail"),
]
