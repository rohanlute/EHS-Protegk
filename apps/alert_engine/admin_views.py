from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import Role
from apps.notifications.models import Notification
from .models import NotificationMaster

MODULE_CHOICES = [
    ('INCIDENT', 'Incident Management'),
    ('HAZARD', 'Hazard/Near Miss'),
    ('EMERGENCY', 'Emergency Management'),
    ('ENVIRONMENTAL', 'Environmental Data'),
    ('INSPECTION', 'Inspection Management'),
    ('TRAINING', 'Training Management'),
    ('LEGAL_COMPLIANCE', 'Legal Compliance'),
]

NOTIFICATION_EVENT_CHOICES = [
    ('INCIDENT_REPORTED', 'Incident Reported'),
    ('INCIDENT_INVESTIGATION_COMPLETED', 'Investigation Completed'),
    ('INCIDENT_INVESTIGATION_OVERDUE', 'Investigation Overdue'),
    ('INCIDENT_ACTION_ASSIGNED', 'Action Item Assigned'),
    ('INCIDENT_CLOSED', 'Incident Closed'),
    ('HAZARD_REPORTED', 'Hazard/Near Miss Reported'),
    ('HAZARD_CLOSED', 'Hazard Closed'),
    ('EMERGENCY_REPORTED', 'Emergency Reported'),
    ('EMERGENCY_ACTION_ASSIGNED', 'Emergency Action Assigned'),
    ('EMERGENCY_ACTION_COMPLETED', 'Emergency Action Completed'),
    ('EMERGENCY_INVESTIGATION_COMPLETED', 'Emergency Investigation Completed'),
    ('EMERGENCY_CAPA_CREATED', 'Emergency CAPA Created'),
    ('EMERGENCY_CAPA_UPDATED', 'Emergency CAPA Updated'),
    ('EMERGENCY_CLOSED', 'Emergency Closed'),
    ('ENV_MONTHLY_REPORT_GENERATED', 'Monthly Report Generated'),
    ('ENV_DATA_SUBMITTED', 'Environmental Data Submitted'),
    ('INSPECTION_SUBMITTED', 'Inspection Report Submitted'),
    ('INSPECTION_FINDING_CREATED', 'Finding Created'),
    ('INSPECTION_FINDING_CLOSED', 'Finding Closed'),
    ('INSPECTION_OVERDUE', 'Inspection Overdue'),
    ('NOTIFY_INSPECTION', 'Inspection Assigned / Reminder'),
    ('INSPECTION_NONCOMPLIANCE_ASSIGNED', 'Non-Compliance Assigned'),
    ('SESSION_SCHEDULED', 'Training Session Scheduled'),
    ('SESSION_REMINDER', 'Training Session Reminder'),
    ('SESSION_CANCELLED', 'Training Session Cancelled'),
    ('ATTENDANCE_MARKED', 'Attendance Marked'),
    ('CERTIFICATE_ISSUED', 'Certificate Issued'),
    ('EXPIRY_ALERT_60', 'Certificate Expiring in 60 Days'),
    ('EXPIRY_ALERT_30', 'Certificate Expiring in 30 Days'),
    ('EXPIRY_ALERT_7', 'Certificate Expiring in 7 Days'),
    ('CERTIFICATE_EXPIRED', 'Certificate Expired'),
    ('TRAINING_OVERDUE', 'Mandatory Training Overdue'),
    ('COMPLIANCE_REMINDER', 'Compliance Reminder'),
    ('COMPLIANCE_ESCALATION', 'Compliance Escalation'),
    ('CAPA', 'Corrective Action Plan'),
    ('NOTICE', 'Regulatory Notice'),
]

REMINDER_TYPE_CHOICES = [
    ('IMMEDIATE', 'Immediate (On Event)'),
    ('BEFORE_DEADLINE', 'Before Deadline'),
    ('AFTER_DEADLINE', 'After Deadline (Overdue)'),
    ('BOTH', 'Both Before and After'),
]


def _infer_module_from_event(event_code):
    if event_code.startswith(('INCIDENT_',)):
        return 'INCIDENT'
    if event_code.startswith(('HAZARD_',)):
        return 'HAZARD'
    if event_code.startswith(('EMERGENCY_',)):
        return 'EMERGENCY'
    if event_code.startswith(('ENV_', 'ENVIRONMENT_')):
        return 'ENVIRONMENTAL'
    if event_code.startswith(('INSPECTION_',)) or event_code == 'NOTIFY_INSPECTION':
        return 'INSPECTION'
    if event_code.startswith(('SESSION_', 'CERTIFICATE_', 'EXPIRY_', 'TRAINING_')):
        return 'TRAINING'
    if event_code.startswith(('COMPLIANCE_',)) or event_code in ('CAPA', 'NOTICE'):
        return 'LEGAL_COMPLIANCE'
    return 'INCIDENT'


@login_required
def notification_master_list(request):
    configurations = NotificationMaster.objects.all().select_related('role')

    roles_with_configs = {}
    for config in configurations:
        role_name = config.role.name if config.role else "No Role"
        roles_with_configs.setdefault(role_name, []).append(config)

    for role in roles_with_configs:
        roles_with_configs[role] = sorted(
            roles_with_configs[role],
            key=lambda x: (x.module, x.notification_event)
        )

    context = {
        'roles_with_configs': roles_with_configs,
        'total_configs': configurations.count(),
        'active_configs_count': configurations.filter(is_active=True).count(),
        'inactive_configs_count': configurations.filter(is_active=False).count(),
    }
    return render(request, 'notifications/master_list.html', context)


@login_required
def notification_master_create(request):
    if request.method == 'POST':
        role_id = request.POST.get('role')
        selected_events = request.POST.getlist('events')

        if not role_id or not selected_events:
            messages.error(request, 'Please select a role and at least one notification event.')
            return redirect('alert_engine:notification_master_create')

        role = Role.objects.get(id=role_id)
        reminder_type = request.POST.get('reminder_type', 'IMMEDIATE')
        days_before = int(request.POST.get('days_before_deadline', 0))
        days_after = int(request.POST.get('days_after_deadline', 0))
        filter_by_plant = request.POST.get('filter_by_plant') == 'on'
        filter_by_location = request.POST.get('filter_by_location') == 'on'
        filter_by_zone = request.POST.get('filter_by_zone') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        email_enabled = request.POST.get('email_enabled') == 'on'

        created_count = 0
        skipped_count = 0

        for event_code in selected_events:
            module = _infer_module_from_event(event_code)

            existing = NotificationMaster.objects.filter(
                role=role,
                notification_event=event_code
            ).exists()
            if existing:
                skipped_count += 1
                continue

            NotificationMaster.objects.create(
                role=role,
                module=module,
                notification_event=event_code,
                reminder_type=reminder_type,
                days_before_deadline=days_before,
                days_after_deadline=days_after,
                filter_by_plant=filter_by_plant,
                filter_by_location=filter_by_location,
                filter_by_zone=filter_by_zone,
                is_active=is_active,
                email_enabled=email_enabled,
                created_by=request.user
            )
            created_count += 1

        if created_count > 0:
            messages.success(request, f'Successfully created {created_count} notification configuration(s) for {role.name}!')
        if skipped_count > 0:
            messages.warning(request, f'Skipped {skipped_count} configuration(s) that already exist.')

        return redirect('alert_engine:notification_master_list')

    roles = Role.objects.all()
    context = {
        'roles': roles,
        'MODULE_CHOICES': MODULE_CHOICES,
        'NOTIFICATION_EVENT_CHOICES': NOTIFICATION_EVENT_CHOICES,
        'REMINDER_TYPE_CHOICES': REMINDER_TYPE_CHOICES,
    }
    return render(request, 'notifications/master_create.html', context)


@login_required
def notification_master_edit(request, pk):
    config = get_object_or_404(NotificationMaster, pk=pk)

    if request.method == 'POST':
        role_id = request.POST.get('role')
        config.role = Role.objects.get(id=role_id)
        config.module = request.POST.get('module')
        config.notification_event = request.POST.get('notification_event')
        config.reminder_type = request.POST.get('reminder_type')
        config.days_before_deadline = int(request.POST.get('days_before_deadline', 0))
        config.days_after_deadline = int(request.POST.get('days_after_deadline', 0))
        config.filter_by_plant = request.POST.get('filter_by_plant') == 'on'
        config.filter_by_location = request.POST.get('filter_by_location') == 'on'
        config.filter_by_zone = request.POST.get('filter_by_zone') == 'on'
        config.is_active = request.POST.get('is_active') == 'on'
        config.email_enabled = request.POST.get('email_enabled') == 'on'
        config.name = ""
        config.save()

        messages.success(request, f'Configuration "{config.name}" updated successfully!')
        return redirect('alert_engine:notification_master_list')

    roles = Role.objects.all()
    context = {
        'config': config,
        'roles': roles,
        'MODULE_CHOICES': MODULE_CHOICES,
        'NOTIFICATION_EVENT_CHOICES': NOTIFICATION_EVENT_CHOICES,
        'REMINDER_TYPE_CHOICES': REMINDER_TYPE_CHOICES,
    }
    return render(request, 'notifications/master_edit.html', context)


@login_required
def notification_master_delete(request, pk):
    config = get_object_or_404(NotificationMaster, pk=pk)

    if request.method == 'POST':
        name = config.name
        config.delete()
        messages.success(request, f'Configuration "{name}" deleted successfully!')
        return redirect('alert_engine:notification_master_list')

    return render(request, 'notifications/master_delete_confirm.html', {'config': config})


@login_required
def notification_master_toggle(request, pk):
    config = get_object_or_404(NotificationMaster, pk=pk)
    config.is_active = not config.is_active
    config.save()

    status = "enabled" if config.is_active else "disabled"
    return JsonResponse({'success': True, 'status': status, 'is_active': config.is_active})


@login_required
def get_notification_events(request):
    module = request.GET.get('module')
    if not module:
        return JsonResponse({'events': []})

    events = []
    for event_code, event_name in NotificationMaster.NOTIFICATION_EVENT_CHOICES:
        if _infer_module_from_event(event_code) == module:
            events.append({'code': event_code, 'name': event_name})

    return JsonResponse({'events': events})


@login_required
def notification_tracking_view(request):
    user = request.user

    notifications = Notification.objects.select_related(
        'recipient',
        'recipient__role'
    )

    roles = Role.objects.all()

    if not user.is_superuser and user.role and user.role.name != "ADMIN":
        roles = roles.filter(name=user.role.name)
        notifications = notifications.filter(recipient__role__name=user.role.name)

    tracking_by_role = {}

    for role in roles:
        role_notifications = notifications.filter(recipient__role=role)
        records = []
        masters = NotificationMaster.objects.filter(role=role)

        for master in masters:
            event_notifications = role_notifications.filter(notification_type=master.notification_event)
            last_notification = event_notifications.order_by('-created_at').first()

            records.append({
                'module': master.module,
                'event_name': master.get_notification_event_display(),
                'event_code': master.notification_event,
                'total_sent': event_notifications.count(),
                'success_count': event_notifications.filter(is_email_sent=True).count(),
                'failed_count': event_notifications.filter(is_email_sent=False).count(),
                'last_sent_at': last_notification.created_at if last_notification else None,
                'email': master.email_enabled,
            })

        if records:
            tracking_by_role[role.name] = records

    total_sent = sum(r['total_sent'] for records in tracking_by_role.values() for r in records)
    email_sent_count = sum(r['success_count'] for records in tracking_by_role.values() for r in records)
    failed_count = sum(r['failed_count'] for records in tracking_by_role.values() for r in records)

    context = {
        'tracking_by_role': tracking_by_role,
        'total_sent': total_sent,
        'email_sent_count': email_sent_count,
        'failed_count': failed_count,
    }

    return render(request, 'notifications/notification_tracking.html', context)
