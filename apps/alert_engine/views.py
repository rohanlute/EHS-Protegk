from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView

from apps.notifications.models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "alert_engine/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 25

    def get_queryset(self):
        return (
            Notification.objects.filter(recipient=self.request.user)
            .select_related("content_type")
            .order_by("-created_at")
        )


@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user,
    )
    notification.mark_as_read()
    messages.success(request, "Notification marked as read.")
    return redirect(request.META.get("HTTP_REFERER") or "alert_engine:notification_list")


@login_required
def open_notification(request, pk):
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user,
    )
    notification.mark_as_read()

    target_url = notification.get_target_url()
    if not target_url:
        messages.warning(request, "This notification does not have a linked detail page.")
        return redirect(request.META.get("HTTP_REFERER") or "alert_engine:notification_list")

    return redirect(target_url)


@login_required
def delete_notification(request, pk):
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user,
    )

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
    messages.success(request, "All notifications marked as read.")
    return redirect(request.META.get("HTTP_REFERER") or "alert_engine:notification_list")
