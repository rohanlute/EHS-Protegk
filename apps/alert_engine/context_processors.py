from apps.notifications.models import Notification


def notification_context(request):
    if not request.user.is_authenticated:
        return {
            "notification_unread_count": 0,
            "recent_notifications": [],
        }

    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related("content_type")
        .order_by("-created_at")
    )

    return {
        "notification_unread_count": notifications.filter(is_read=False).count(),
        "recent_notifications": notifications[:6],
    }
