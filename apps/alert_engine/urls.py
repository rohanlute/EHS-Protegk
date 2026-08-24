from django.urls import path

from . import admin_views as notification_admin_views
from .views import NotificationListView, mark_all_notifications_read, mark_notification_read

app_name = "alert_engine"

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification_list"),
    path("inbox/", NotificationListView.as_view(), name="notification_inbox"),
    path("<int:pk>/read/", mark_notification_read, name="notification_read"),
    path("read-all/", mark_all_notifications_read, name="notifications_read_all"),

    path("master/", notification_admin_views.notification_master_list, name="notification_master_list"),
    path("master/create/", notification_admin_views.notification_master_create, name="notification_master_create"),
    path("master/<int:pk>/edit/", notification_admin_views.notification_master_edit, name="notification_master_edit"),
    path("master/<int:pk>/delete/", notification_admin_views.notification_master_delete, name="notification_master_delete"),
    path("master/<int:pk>/toggle/", notification_admin_views.notification_master_toggle, name="notification_master_toggle"),
    path("master/tracking/", notification_admin_views.notification_tracking_view, name="notification_tracking_view"),
    path("get-events/", notification_admin_views.get_notification_events, name="get_notification_events"),
]
