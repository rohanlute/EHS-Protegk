from celery import shared_task

from apps.alert_engine.services import NotificationService


@shared_task(name="apps.alert_engine.tasks.send_investigation_overdue_notifications")
def send_investigation_overdue_notifications():
    import datetime

    from apps.accidents.models import Incident

    today = datetime.date.today()

    overdue_incidents = (
        Incident.objects.filter(
            investigation_required=True,
            investigation_deadline__lt=today,
            investigation_completed_date__isnull=True,
        )
        .exclude(status="CLOSED")
        .select_related("plant", "zone", "location", "reported_by", "incident_type")
    )

    total = overdue_incidents.count()
    if total == 0:
        return "No overdue investigations found."

    success_count = 0
    error_count = 0

    for incident in overdue_incidents:
        try:
            extra_recipients = [user for user in [incident.reported_by, incident.investigator] if user]
            NotificationService.notify(
                content_object=incident,
                notification_type="INCIDENT_INVESTIGATION_OVERDUE",
                module="INCIDENT",
                extra_recipients=extra_recipients or None,
            )
            success_count += 1
        except Exception:
            error_count += 1

    return f"Overdue notifications — Sent: {success_count}, Errors: {error_count}, Total: {total}"
