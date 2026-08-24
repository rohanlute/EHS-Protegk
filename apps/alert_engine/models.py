from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

User = get_user_model()


class NotificationMaster(models.Model):
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

    name = models.CharField(max_length=200, editable=False, blank=True)
    module = models.CharField(max_length=50, choices=MODULE_CHOICES)
    notification_event = models.CharField(max_length=50, choices=NOTIFICATION_EVENT_CHOICES)
    role = models.ForeignKey(
        'accounts.Role',
        on_delete=models.CASCADE,
        related_name='alert_engine_notification_configs',
        help_text="Select role that should receive this notification",
    )
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES, default='IMMEDIATE')
    days_before_deadline = models.IntegerField(default=0)
    days_after_deadline = models.IntegerField(default=0)
    filter_by_plant = models.BooleanField(default=True)
    filter_by_location = models.BooleanField(default=False)
    filter_by_zone = models.BooleanField(default=False)
    email_enabled = models.BooleanField(default=True)
    email_template = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='alert_engine_notification_configs_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['role', 'module', 'notification_event']
        verbose_name = "Notification Configuration"
        verbose_name_plural = "Notification Configurations"
        unique_together = [['role', 'module', 'notification_event']]

    def save(self, *args, **kwargs):
        if not self.name and self.role_id:
            self.name = f"{self.role.name} - {self.get_module_display()} - {self.get_notification_event_display()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Notification(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='alert_engine_notification_set',
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='alert_engine_notifications_received',
    )
    notification_type = models.CharField(max_length=50, choices=NotificationMaster.NOTIFICATION_EVENT_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    is_email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.recipient.get_full_name()} - {self.title}"

    def mark_as_read(self):
        from django.utils import timezone

        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
