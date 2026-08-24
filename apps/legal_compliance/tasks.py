from celery import shared_task

from django.utils import timezone

from apps.legal_compliance.models import (
    ComplianceSchedule
)

from apps.notifications.services import NotificationService as CoreNotificationService
from apps.alert_engine.services import (
    NotificationService as AlertNotificationService
)


@shared_task(
    name='apps.legal_compliance.tasks.send_compliance_reminders'
)
def send_compliance_reminders():

    today = timezone.now().date()

    schedules = (
        ComplianceSchedule.objects.select_related(
            'compliance_requirement',
            'assigned_to'
        )
        .filter(
            status__in=[
                'PENDING',
                'IN_PROGRESS'
            ]
        )
    )

    total = schedules.count()

    if total == 0:

        print("✅ No pending compliance schedules found.")

        return "No pending compliance schedules found."

    sent_count = 0

    error_count = 0

    for schedule in schedules:

        try:

            if not schedule.assigned_to:
                continue

            reminder_days = (
                schedule.compliance_requirement.reminder_days
            )

            reminder_date = (
                schedule.due_date -
                timezone.timedelta(days=reminder_days)
            )

            # SEND REMINDER ONLY WHEN DATE ARRIVES

            if today >= reminder_date:

                CoreNotificationService.notify(

                    content_object=schedule,

                    notification_type='COMPLIANCE_REMINDER',

                    module='LEGAL_COMPLIANCE',

                    extra_recipients=[
                        schedule.assigned_to
                    ]
                )

                sent_count += 1

                print(
                    f"✅ Reminder sent for "
                    f"{schedule.schedule_code}"
                )

        except Exception as e:

            error_count += 1

            print(
                f"❌ Error for "
                f"{schedule.schedule_code}: {e}"
            )

    result = (
        f"Compliance reminders — "
        f"Sent: {sent_count}, "
        f"Errors: {error_count}, "
        f"Total: {total}"
    )

    print(result)

    return result



@shared_task(
    name='apps.legal_compliance.tasks.send_overdue_escalations'
)
def send_overdue_escalations():

    today = timezone.now().date()

    overdue_schedules = (
        ComplianceSchedule.objects.select_related(
            'compliance_requirement',
            'assigned_to',
            'reviewed_by'
        )
        .filter(
            status='OVERDUE'
        )
    )

    total = overdue_schedules.count()

    if total == 0:

        print("✅ No overdue schedules found.")

        return "No overdue schedules found."

    escalation_count = 0

    error_count = 0

    for schedule in overdue_schedules:

        try:

            escalation_days = (
                schedule.compliance_requirement.escalation_days
            )

            escalation_date = (
                schedule.due_date +
                timezone.timedelta(days=escalation_days)
            )

            if today >= escalation_date:

                recipients = []

                if schedule.assigned_to:
                    recipients.append(schedule.assigned_to)

                if schedule.reviewed_by:
                    recipients.append(schedule.reviewed_by)

                if not recipients:
                    continue

                CoreNotificationService.notify(

                    content_object=schedule,

                    notification_type='COMPLIANCE_ESCALATION',

                    module='LEGAL_COMPLIANCE',

                    extra_recipients=recipients
                )

                escalation_count += 1

                print(
                    f"⚠️ Escalation sent for "
                    f"{schedule.schedule_code}"
                )

        except Exception as e:

            error_count += 1

            print(
                f"❌ Error for "
                f"{schedule.schedule_code}: {e}"
            )

    result = (
        f"Escalations — "
        f"Sent: {escalation_count}, "
        f"Errors: {error_count}, "
        f"Total: {total}"
    )

    print(result)

    return result
