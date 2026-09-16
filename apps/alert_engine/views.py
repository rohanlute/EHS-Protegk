from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView

from .models import Notification
from .notification_feed import get_notification, get_notification_feed


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "alert_engine/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 25

    def get_queryset(self):
        return get_notification_feed(self.request.user)


def _get_notification(request, pk):
    source = request.GET.get("source", "alert")
    from apps.notifications.models import Notification as LegacyNotification

    model = LegacyNotification if source == "legacy" else Notification
    return get_object_or_404(model, pk=pk, recipient=request.user)


@login_required
def mark_notification_read(request, pk):
    notification = _get_notification(request, pk)
    notification.mark_as_read()
    messages.success(request, "Notification marked as read.")
    return redirect(request.META.get("HTTP_REFERER") or "alert_engine:notification_list")


@login_required
def open_notification(request, pk):
    notification = _get_notification(request, pk)
    notification.mark_as_read()

    target_url = notification.get_target_url()
    if not target_url:
        messages.warning(request, "This notification does not have a linked detail page.")
        return redirect(request.META.get("HTTP_REFERER") or "alert_engine:notification_list")

    return redirect(target_url)


@login_required
def delete_notification(request, pk):
    notification = _get_notification(request, pk)

    if request.method != "POST":
        return redirect(request.META.get("HTTP_REFERER") or "alert_engine:notification_list")

    notification.delete()
    messages.success(request, "Notification deleted.")
    return redirect(request.META.get("HTTP_REFERER") or "alert_engine:notification_list")


@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(is_read=True)
    from apps.notifications.models import Notification as LegacyNotification

    LegacyNotification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect(request.META.get("HTTP_REFERER") or "alert_engine:notification_list")
