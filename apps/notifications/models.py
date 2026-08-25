from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

User = get_user_model()


class NotificationMaster(models.Model):
    """
    Master configuration for which roles receive which notifications
    """
    
    MODULE_CHOICES = [
        ('INCIDENT', 'Incident Management'),
        ('HAZARD', 'Hazard/Near Miss'),
        ('EMERGENCY', 'Emergency Management'),
        ('ENVIRONMENTAL', 'Environmental Data'),
        ('INSPECTION', 'Inspection Management'),
        ('LEGAL_COMPLIANCE', 'Legal Compliance'),
    ]
    
    NOTIFICATION_EVENT_CHOICES = [
        # Incident Module
        ('INCIDENT_REPORTED', 'Incident Reported'),
        ('INCIDENT_INVESTIGATION_COMPLETED', 'Investigation Completed'),
        # ('INCIDENT_INVESTIGATION_DUE', 'Investigation Due Soon'),
        ('INCIDENT_INVESTIGATION_OVERDUE', 'Investigation Overdue'),
        ('INCIDENT_ACTION_ASSIGNED', 'Action Item Assigned'),
        ('INCIDENT_CLOSED', 'Incident Closed'),
        
        # Hazard Module
        ('HAZARD_REPORTED', 'Hazard/Near Miss Reported'),
        ('HAZARD_CLOSED', 'Hazard Closed'),

        # Emergency Module
        ('EMERGENCY_REPORTED', 'Emergency Reported'),
        ('EMERGENCY_ACTION_ASSIGNED', 'Emergency Action Assigned'),
        ('EMERGENCY_ACTION_COMPLETED', 'Emergency Action Completed'),
        ('EMERGENCY_INVESTIGATION_COMPLETED', 'Emergency Investigation Completed'),
        ('EMERGENCY_CAPA_CREATED', 'Emergency CAPA Created'),
        ('EMERGENCY_CAPA_UPDATED', 'Emergency CAPA Updated'),
        ('EMERGENCY_CLOSED', 'Emergency Closed'),
        
        # Environmental Module
        ('ENV_MONTHLY_REPORT_GENERATED', 'Monthly Report Generated'),
        # ('ENV_SUBMISSION_OVERDUE', 'Submission Overdue'),
        ('ENV_DATA_SUBMITTED', 'Environmental Data Submitted'),
        
        # Inspection Module
        ('INSPECTION_SUBMITTED', 'Inspection Report Submitted'),
        ('INSPECTION_FINDING_CREATED', 'Finding Created'),
        ('INSPECTION_FINDING_CLOSED', 'Finding Closed'),
        ('INSPECTION_OVERDUE', 'Inspection Overdue'),
        ('NOTIFY_INSPECTION', 'Inspection Assigned / Reminder'),
        ('INSPECTION_NONCOMPLIANCE_ASSIGNED', 'Non-Compliance Assigned'),

        # Legal Compliance Module
        ('COMPLIANCE_REMINDER', 'Compliance Reminder'),
        ('COMPLIANCE_ESCALATION', 'Compliance Escalation'),

    ]
    
    REMINDER_TYPE_CHOICES = [
        ('IMMEDIATE', 'Immediate (On Event)'),
        ('BEFORE_DEADLINE', 'Before Deadline'),
        ('AFTER_DEADLINE', 'After Deadline (Overdue)'),
        ('BOTH', 'Both Before and After'),
    ]
    
    # Auto-generated name based on module + notification_event
    name = models.CharField(
        max_length=200, 
        editable=False,  # Not editable in forms
        blank=True
    )
    
    module = models.CharField(max_length=50, choices=MODULE_CHOICES)
    notification_event = models.CharField(max_length=50, choices=NOTIFICATION_EVENT_CHOICES)
    
    # ===== FIXED: Changed field name from 'roles' to 'role' =====
    role = models.ForeignKey(
        'accounts.Role',
        on_delete=models.CASCADE, 
        related_name='notification_configs',
        help_text="Select role that should receive this notification"
    )
    
    # Reminder Settings
    reminder_type = models.CharField(
        max_length=20, 
        choices=REMINDER_TYPE_CHOICES,
        default='IMMEDIATE'
    )
    days_before_deadline = models.IntegerField(
        default=0,
        help_text="Send reminder X days before deadline (0 = disabled)"
    )
    days_after_deadline = models.IntegerField(
        default=0,
        help_text="Send reminder X days after deadline (escalation)"
    )
    
    # Filters
    filter_by_plant = models.BooleanField(
        default=True,
        help_text="Only notify users from the same plant"
    )
    filter_by_location = models.BooleanField(
        default=False,
        help_text="Only notify users from the same location"
    )
    filter_by_zone = models.BooleanField(
        default=False,
        help_text="Only notify users from the same zone"
    )
    
    # Email Configuration
    email_enabled = models.BooleanField(default=True)
    email_template = models.CharField(
        max_length=200,
        blank=True,
        help_text="Path to email template (auto-populated)"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='notification_configs_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['role', 'module', 'notification_event']
        verbose_name = "Notification Configuration"
        verbose_name_plural = "Notification Configurations"
        unique_together = [['role','module','notification_event']]  # ✅ Now matches field name
    
    def save(self, *args, **kwargs):
        """Auto-generate name from role, module and event"""
        if not self.name:
            # Generate name like: "Safety Manager - Incident Management - Incident Reported"
            self.name = f"{self.role.name} - {self.get_module_display()} - {self.get_notification_event_display()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def get_role_name(self):
        """Get role name"""
        return self.role.name if self.role else "No Role"


class Notification(models.Model):
    """
    Generic notification model that can be used across all modules
    """
    
    NOTIFICATION_TYPES = NotificationMaster.NOTIFICATION_EVENT_CHOICES
    
    # Generic relation to any module's object (Incident, Hazard, Inspection, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Notification details
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications_received'
    )
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Metadata
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

    def get_target_url(self):
        """
        Return the detail URL for the object this notification points to.

        Notifications can be attached either to a main record (hazard, incident,
        emergency report, inspection schedule) or to a related action item. In
        the action-item case we redirect to the parent object detail page.
        """
        obj = self.content_object
        if not obj:
            return None

        # Prefer an object-specific URL helper when one exists.
        get_absolute_url = getattr(obj, "get_absolute_url", None)
        if callable(get_absolute_url):
            try:
                return get_absolute_url()
            except Exception:
                pass

        try:
            if hasattr(obj, "hazard") and getattr(obj, "hazard", None):
                return reverse("hazards:hazard_detail", kwargs={"pk": obj.hazard.pk})

            if hasattr(obj, "incident") and getattr(obj, "incident", None):
                return reverse("accidents:incident_detail", kwargs={"pk": obj.incident.pk})

            if hasattr(obj, "report") and getattr(obj, "report", None):
                return reverse("emergency:report_detail", kwargs={"pk": obj.report.pk})

            if hasattr(obj, "schedule") and getattr(obj, "schedule", None):
                return reverse("inspections:schedule_detail", kwargs={"pk": obj.schedule.pk})

            if hasattr(obj, "submission") and getattr(obj, "submission", None):
                return reverse("inspections:schedule_detail", kwargs={"pk": obj.submission.schedule.pk})

            app_label = obj._meta.app_label
            model_name = obj._meta.model_name

            direct_routes = {
                ("hazards", "hazard"): "hazards:hazard_detail",
                ("accidents", "incident"): "accidents:incident_detail",
                ("emergency", "emergencyreport"): "emergency:report_detail",
                ("inspections", "inspectionschedule"): "inspections:schedule_detail",
            }

            route_name = direct_routes.get((app_label, model_name))
            if route_name:
                return reverse(route_name, kwargs={"pk": obj.pk})
        except Exception:
            return None

        return None
