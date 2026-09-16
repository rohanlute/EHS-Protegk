from .notification_feed import get_notification_feed


def notification_context(request):
    if not request.user.is_authenticated:
        return {
            "notification_unread_count": 0,
            "recent_notifications": [],
        }

    notifications = get_notification_feed(request.user)

    return {
        "notification_unread_count": sum(not notification.is_read for notification in notifications),
        "recent_notifications": notifications[:6],
    }
