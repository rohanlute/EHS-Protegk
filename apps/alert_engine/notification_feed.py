from dataclasses import dataclass
from django.urls import reverse
from apps.notifications.models import Notification as LegacyNotification
from .models import Notification


@dataclass
class NotificationEntry:
    notification: object
    source: str

    def __getattr__(self, name):
        return getattr(self.notification, name)

    @property
    def open_url(self):
        query = "?source=legacy" if self.source == "legacy" else ""
        return f"{reverse('alert_engine:notification_detail', args=[self.pk])}{query}"

    @property
    def delete_url(self):
        query = "?source=legacy" if self.source == "legacy" else ""
        return f"{reverse('alert_engine:notification_delete', args=[self.pk])}{query}"

    @property
    def module(self):
        return self.notification_type.split("_", 1)[0].title()


def get_notification_feed(user):
    current = Notification.objects.filter(recipient=user).select_related("content_type")
    legacy = LegacyNotification.objects.filter(recipient=user).select_related("content_type")
    entries = [*(NotificationEntry(item, "alert") for item in current), *(NotificationEntry(item, "legacy") for item in legacy)]
    return sorted(entries, key=lambda entry: entry.created_at, reverse=True)


def get_notification(pk, user, source):
    model = LegacyNotification if source == "legacy" else Notification
    return model.objects.get(pk=pk, recipient=user)