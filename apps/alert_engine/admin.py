from django.contrib import admin

from .models import NotificationMaster


@admin.register(NotificationMaster)
class NotificationMasterAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "module", "notification_event", "is_active", "email_enabled", "updated_at")
    list_filter = ("module", "notification_event", "is_active", "email_enabled", "role")
    search_fields = ("name", "role__name", "notification_event", "module")

