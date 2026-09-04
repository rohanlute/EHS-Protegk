from django.core.mail import EmailMultiAlternatives
from django.template.loader import select_template
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import NotificationMaster, Notification
from apps.accidents.models import IncidentType
import logging
from django.urls import reverse
from django.conf import settings

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationService:
    """
    Generic notification service that uses NotificationMaster configurations
    """

    EMAIL_TEMPLATE_MAP = {
        'INCIDENT_REPORTED': 'emails/incident/notification.html',
        'INCIDENT_INVESTIGATION_COMPLETED': 'emails/incident_investigation_reported/notification.html',
        'INCIDENT_INVESTIGATION_OVERDUE': 'emails/investigation_overdue/notification.html',
        'INCIDENT_ACTION_ASSIGNED': 'emails/incident_action/notification.html',
        'INCIDENT_CLOSED': 'emails/incident_closed/notification.html',
        'HAZARD_REPORTED': 'emails/hazard/notification.html',
        'HAZARD_ACTION_ASSIGNED': 'emails/hazard_action/notification.html',
        'HAZARD_ACTION_COMPLETED': 'emails/hazard_action/notification.html',
        'EMERGENCY_REPORTED': 'emails/emergency/notification.html',
        'EMERGENCY_ACTION_ASSIGNED': 'emails/emergency/notification.html',
        'EMERGENCY_ACTION_COMPLETED': 'emails/emergency/notification.html',
        'EMERGENCY_INVESTIGATION_COMPLETED': 'emails/emergency/notification.html',
        'EMERGENCY_CAPA_CREATED': 'emails/emergency/notification.html',
        'EMERGENCY_CAPA_UPDATED': 'emails/emergency/notification.html',
        'EMERGENCY_CLOSED': 'emails/emergency/notification.html',
        'ENV_DATA_SUBMITTED': 'emails/env/notification.html',
        'INSPECTION_SUBMITTED': 'emails/inspection/notification.html',
        'NOTIFY_INSPECTION': 'emails/notify_inspection/notification.html',
        'INSPECTION_SCHEDULE': 'emails/notify_inspection/notification.html',
        'INSPECTION_NONCOMPLIANCE_ASSIGNED': 'emails/inspection_noncompliance/notification.html',
        'CAPA_CREATED': 'emails/capa/notification.html',
        'CAPA_INVESTIGATION_ASSIGNED': 'emails/capa/notification.html',
        'CAPA_INVESTIGATION_DUE': 'emails/capa/notification.html',
        'CAPA_INVESTIGATION_OVERDUE': 'emails/capa/notification.html',
        'CAPA_INVESTIGATION_SUBMITTED': 'emails/capa/notification.html',
        'CAPA_INVESTIGATION_APPROVED': 'emails/capa/notification.html',
        'CAPA_INVESTIGATION_REJECTED': 'emails/capa/notification.html',
        'CAPA_ACTION_ASSIGNED': 'emails/capa/notification.html',
        'CAPA_ACTION_DUE': 'emails/capa/notification.html',
        'CAPA_ACTION_OVERDUE': 'emails/capa/notification.html',
        'CAPA_ACTION_SUBMITTED': 'emails/capa/notification.html',
        'CAPA_ACTION_REJECTED': 'emails/capa/notification.html',
        'CAPA_ACTION_VERIFIED': 'emails/capa/notification.html',
        'CAPA_EFFECTIVENESS_REVIEW_DUE': 'emails/capa/notification.html',
        'CAPA_EFFECTIVENESS_FAILED': 'emails/capa/notification.html',
        'CAPA_REOPENED': 'emails/capa/notification.html',
        'CAPA_CLOSED': 'emails/capa/notification.html',
        'SESSION_SCHEDULED': 'emails/notification.html',
        'SESSION_REMINDER': 'emails/notification.html',
        'SESSION_CANCELLED': 'emails/notification.html',
        'CERTIFICATE_ISSUED': 'emails/notification.html',
        'COMPLIANCE_REMINDER': 'emails/notification.html',
        'COMPLIANCE_ESCALATION': 'emails/notification.html',
    }

    @staticmethod
    def _normalize_users(value):
        """
        Normalize a single user, queryset, many-related manager, or list into User objects.
        """
        if not value:
            return []

        if hasattr(value, "all"):
            return [user for user in value.all() if user]

        if isinstance(value, (list, tuple, set)):
            users = []
            for item in value:
                users.extend(NotificationService._normalize_users(item))
            return users

        if hasattr(value, "pk"):
            return [value]

        return []
    
    @staticmethod
    def get_stakeholders_for_event(event_type, plant=None, location=None, zone=None):
        """
        Get stakeholders based on NotificationMaster configuration
        
        Args:
            event_type: Notification event type (e.g., 'INCIDENT_REPORTED')
            plant: Plant object
            location: Location object
            zone: Zone object
        
        Returns:
            List of User objects who should receive this notification
        """
        # print(f"\n{'='*70}")
        # print(f"FINDING STAKEHOLDERS FOR: {event_type}")
        # print(f"{'='*70}")
        # print(f"Plant: {plant}")
        # print(f"Location: {location}")
        # print(f"Zone: {zone}")
        
        # Get all active notification configurations for this event type
        configs = NotificationMaster.objects.filter(
            notification_event=event_type,
            is_active=True
        ).select_related('role')
        
        if not configs.exists():
            # print(f"⚠️ No notification configurations found for {event_type}")
            return []
        
        # print(f"\nFound {configs.count()} active configuration(s)")
        
        stakeholders = []
        
        for config in configs:
            # print(f"\n--- Processing Config: {config.name} ---")
            # print(f"Role: {config.role.name}")
            # print(f"Filters: Plant={config.filter_by_plant}, Location={config.filter_by_location}, Zone={config.filter_by_zone}")

            # Build query to find users with this role
            query = User.objects.filter(
                    role=config.role,
                    is_active=True
                )
            
            if config.role.name == 'PLANT HEAD':
                config.filter_by_plant = True
                
            # Apply filters based on configuration
            if config.filter_by_plant and plant:
                query = query.filter(plant=plant)
                # print(f"  - Filtered by plant: {plant.name}")
            
            if config.filter_by_location and location:
                query = query.filter(location=location)
                # print(f"  - Filtered by location: {location.name}")
            
            if config.filter_by_zone and zone:
                query = query.filter(zone=zone)
                # print(f"  - Filtered by zone: {zone.name}")
            
            users = query.all()
            # print(f"  - Found {users.count()} user(s) with role {config.role.name}")
            
            for user in users:
                # print(f"    • {user.username} | {user.get_full_name()} | {user.email}")
                if user not in stakeholders:
                    stakeholders.append(user)
        
        # print(f"\n{'='*70}")
        # print(f"TOTAL UNIQUE STAKEHOLDERS: {len(stakeholders)}")
        # print(f"{'='*70}\n")
        
        return stakeholders
    
    
    @staticmethod
    def create_notification(recipient, content_object, notification_type, title, message):
        """
        Create a notification in the database
        
        Args:
            recipient: User object
            content_object: The object (Incident/Hazard) being notified about
            notification_type: Type of notification
            title: Notification title
            message: Notification message
        """
        # print(f"\n--- CREATING NOTIFICATION ---")
        # print(f"Recipient: {recipient.username}")
        # print(f"Type: {notification_type}")
        # print(f"Title: {title[:50]}...")
        
        try:
            content_type = ContentType.objects.get_for_model(content_object)
            
            notification = Notification(
                recipient=recipient,
                content_type=content_type,
                object_id=content_object.id,
                notification_type=notification_type,
                title=title,
                message=message,
                is_read=False
            )
            
            notification.save()
            # print(f"  ✅ SAVED! Notification ID: {notification.id}")
            return notification
            
        except Exception as e:
            # print(f"  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    
    @staticmethod
    def send_email(recipient, subject, message, html_template=None, context=None):
        """
        Send email notification
        
        Args:
            recipient: User object
            subject: Email subject
            message: Plain text message
            html_template: Path to HTML template (optional)
            context: Template context dictionary (optional)
        """
        # print(f"\n--- SENDING EMAIL ---")
        # print(f"To: {recipient.email}")
        # print(f"Subject: {subject}")
        
        # Check if email is configured
        if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
            # print("  ⚠️ EMAIL NOT CONFIGURED - Skipping email send")
            return False
        
        try:
            # Render HTML template if provided
            if html_template and context:
                html_content = select_template([html_template, 'emails/notification.html']).render(context)
            else:
                html_content = None
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient.email]
            )
            
            if html_content:
                email.attach_alternative(html_content, "text/html")
            
            email.send(fail_silently=False)
            # print("  ✅ Email sent successfully")
            return True
            
        except Exception as e:
            # print(f"  ❌ Email error: {e}")
            import traceback
            traceback.print_exc()
            return False

    # Add this method to your NotificationService class

    @staticmethod
    def send_contractor_onboarding_email(
        portal_user,
        assignment,
        temporary_password,
        login_url,
        cc_email=None,
        prequal_questions=None,
        document_requirements=None
    ):
        """
        Send Contractor Portal onboarding credentials with full details.
        
        Args:
            portal_user: ContractorPortalUser instance
            assignment: ContractorAssignment instance
            temporary_password: Generated password string
            login_url: Full login URL with assignment token
            cc_email: Optional CC email address
            prequal_questions: List of pre-qualification questions with answers
            document_requirements: List of document requirements
        """
        
        if not portal_user or not portal_user.email:
            logger.error("Contractor portal email cannot be sent: email is missing.")
            return False

        if not assignment:
            logger.error("Contractor portal email cannot be sent: assignment is missing.")
            return False

        contractor = assignment.onboarding.contractor
        onboarding = assignment.onboarding

        subject = (
            f"EHS-360 Contractor Portal Access - "
            f"{contractor.contractor_name}"
        )

        # Build plain text message
        message = f"""
    Hello {portal_user.name},

    You have been assigned an onboarding task in the EHS-360 Contractor Portal.

    CONTRACTOR DETAILS
    --------------------------------------------------
    Company Name         : {contractor.contractor_name}
    Company Type         : {contractor.get_contractor_type_display()}
    Address              : {contractor.address_line1}, {contractor.city}, {contractor.state}, {contractor.country} - {contractor.pincode}
    Service Description  : {contractor.service_description[:200]}{'...' if contractor.service_description and len(contractor.service_description) > 200 else ''}

    PORTAL LOGIN DETAILS
    --------------------------------------------------
    Login URL           : {login_url}
    Email               : {portal_user.email}
    Password            : {temporary_password}

    IMPORTANT INSTRUCTIONS
    --------------------------------------------------
    • Keep your login credentials confidential
    • Complete all pre-qualification questions
    • Upload all required documents
    • Your assignment will expire if not completed within timeframe
    • For assistance, contact your EHS administrator

    If you did not expect this email, please contact the EHS administrator.

    Regards,
    EHS-360
    EHS Management System
    """

        # Build context for HTML template
        context = {
            'portal_user': portal_user,
            'assignment': assignment,
            'contractor': contractor,
            'onboarding': onboarding,
            'temporary_password': temporary_password,
            'login_url': login_url,
            'prequal_questions': prequal_questions or [],
            'document_requirements': document_requirements or [],
        }

        try:
            # Try to load the specific template
            html_content = select_template([
                'notifications/contractor_onboarding.html',
                'emails/contractor_onboarding.html',
                'emails/notification.html',
            ]).render(context)
            
            cc = []
            if cc_email:
                cc_email = cc_email.strip().lower()
                if cc_email and cc_email.lower() != portal_user.email.lower():
                    cc.append(cc_email)

            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[portal_user.email],
                cc=cc,
                reply_to=[settings.DEFAULT_FROM_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)

            logger.info(
                "Contractor onboarding email sent successfully to %s, CC: %s",
                portal_user.email,
                cc
            )
            return True

        except Exception as e:
            logger.exception(
                "Failed to send contractor onboarding email to %s: %s",
                portal_user.email,
                e
            )
            return False
    @staticmethod
    def _resolve_email_template(notification_type, module):
        template = {
            'INCIDENT_REPORTED': 'emails/incident/notification.html',
            'INCIDENT_INVESTIGATION_COMPLETED': 'emails/incident_investigation_reported/notification.html',
            'INCIDENT_INVESTIGATION_OVERDUE': 'emails/investigation_overdue/notification.html',
            'INCIDENT_ACTION_ASSIGNED': 'emails/incident_action/notification.html',
            'INCIDENT_CLOSED': 'emails/incident_closed/notification.html',
            'HAZARD_REPORTED': 'emails/hazard/notification.html',
            'HAZARD_ACTION_ASSIGNED': 'emails/hazard_action/notification.html',
            'HAZARD_ACTION_COMPLETED': 'emails/hazard_action/notification.html',
            'EMERGENCY_REPORTED': 'emails/emergency/notification.html',
            'EMERGENCY_ACTION_ASSIGNED': 'emails/emergency/notification.html',
            'EMERGENCY_ACTION_COMPLETED': 'emails/emergency/notification.html',
            'EMERGENCY_INVESTIGATION_COMPLETED': 'emails/emergency/notification.html',
            'EMERGENCY_CAPA_CREATED': 'emails/emergency/notification.html',
            'EMERGENCY_CAPA_UPDATED': 'emails/emergency/notification.html',
            'EMERGENCY_CLOSED': 'emails/emergency/notification.html',
            'ENV_DATA_SUBMITTED': 'emails/env/notification.html',
            'INSPECTION_SUBMITTED': 'emails/inspection/notification.html',
            'NOTIFY_INSPECTION': 'emails/notify_inspection/notification.html',
            'INSPECTION_SCHEDULE': 'emails/notify_inspection/notification.html',
            'INSPECTION_NONCOMPLIANCE_ASSIGNED': 'emails/inspection_noncompliance/notification.html',
            'CAPA_CREATED': 'emails/capa/notification.html',
            'CAPA_INVESTIGATION_ASSIGNED': 'emails/capa/notification.html',
            'CAPA_INVESTIGATION_DUE': 'emails/capa/notification.html',
            'CAPA_INVESTIGATION_OVERDUE': 'emails/capa/notification.html',
            'CAPA_INVESTIGATION_SUBMITTED': 'emails/capa/notification.html',
            'CAPA_INVESTIGATION_APPROVED': 'emails/capa/notification.html',
            'CAPA_INVESTIGATION_REJECTED': 'emails/capa/notification.html',
            'CAPA_ACTION_ASSIGNED': 'emails/capa/notification.html',
            'CAPA_ACTION_DUE': 'emails/capa/notification.html',
            'CAPA_ACTION_OVERDUE': 'emails/capa/notification.html',
            'CAPA_ACTION_SUBMITTED': 'emails/capa/notification.html',
            'CAPA_ACTION_REJECTED': 'emails/capa/notification.html',
            'CAPA_ACTION_VERIFIED': 'emails/capa/notification.html',
            'CAPA_EFFECTIVENESS_REVIEW_DUE': 'emails/capa/notification.html',
            'CAPA_EFFECTIVENESS_FAILED': 'emails/capa/notification.html',
            'CAPA_REOPENED': 'emails/capa/notification.html',
            'CAPA_CLOSED': 'emails/capa/notification.html',
        }.get(notification_type)

        if template:
            return template

        normalized_module = (module or '').upper()
        module_templates = {
            'ENV': 'emails/env/notification.html',
            'ENVIRONMENTAL': 'emails/env/notification.html',
            'INSPECTION': 'emails/inspection/notification.html',
            'CAPA': 'emails/capa/notification.html',
            'INVESTIGATION_OVERDUE': 'emails/investigation_overdue/notification.html',
        }
        return module_templates.get(
            normalized_module,
            f'emails/{(module or "notification").lower()}/notification.html',
        )

    @staticmethod
    def notify(content_object, notification_type, module='INCIDENT', extra_recipients=None):
        """
        Main notification function - finds stakeholders and sends notifications

        Args:
            content_object: The object (Incident/Hazard/InvestigationReport) being notified about
            notification_type: Type of notification (e.g., 'INCIDENT_REPORTED')
            module: Module name for template selection
        """
        # print("\n" + "*"*70)
        # print(f"NOTIFICATION SYSTEM - {notification_type}")
        # print("*"*70)
        if content_object is None:
            # print(f"\n❌ ERROR: content_object is None. Cannot send notification for {notification_type}")
            return

        # Determine object type and extract plant/location/zone
        # Auto-detect object type
        if hasattr(content_object, 'incident'):
            # Investigation Report
            incident = content_object.incident
            plant = incident.plant
            location = incident.location
            zone = incident.zone
        elif hasattr(content_object, 'report'):
            report = content_object.report
            plant = report.plant
            location = report.location
            zone = report.zone
        elif hasattr(content_object, 'hazard'):
            hazard = content_object.hazard
            plant = hazard.plant
            location = hazard.location
            zone = hazard.zone
        elif hasattr(content_object, 'submission'):
            schedule = content_object.submission.schedule
            plant = schedule.plant.first() if schedule.plants.exists() else None
            location = schedule.location
            zone = schedule.zone
        else:
            # Incident / Hazard
            plant = getattr(content_object, 'plant', None)
            location = getattr(content_object, 'location', None)
            zone = getattr(content_object, 'zone', None)


        # inspection schedule - only notify assigned user
        if notification_type == 'INSPECTION_SCHEDULE':
            stakeholders = []
            if hasattr(content_object, 'assigned_to') and content_object.assigned_to:
                stakeholders.extend(NotificationService._normalize_users(content_object.assigned_to))
        else:
            stakeholders = NotificationService.get_stakeholders_for_event(
                event_type=notification_type,
                plant=plant,
                location=location,
                zone=zone
            )

            # For responsible person
            if extra_recipients:
                for user in NotificationService._normalize_users(extra_recipients):
                    if user not in stakeholders:
                        stakeholders.append(user)

            # Add assigned_to if present
            if hasattr(content_object, 'assigned_to') and content_object.assigned_to:
                for user in NotificationService._normalize_users(content_object.assigned_to):
                    if user not in stakeholders:
                        stakeholders.append(user)

            # Add responsible persons for action items
            if hasattr(content_object, 'responsible_person'):
                for user in NotificationService._normalize_users(content_object.responsible_person):
                    if user not in stakeholders:
                        stakeholders.append(user)

            # Add responsible emails if present
            if hasattr(content_object, 'responsible_emails') and content_object.responsible_emails:
                emails = [e.strip() for e in content_object.responsible_emails.split(',') if e.strip()]
                responsible_users = User.objects.filter(email__in=emails, is_active=True)
                for user in responsible_users:
                    if user not in stakeholders:
                        stakeholders.append(user)
       


        if not stakeholders and not extra_recipients:
            # print("\n❌ ERROR: No stakeholders found!")
            return

        notifications_created = 0
        emails_sent = 0

        # Build notification context
        if notification_type == 'INCIDENT_REPORTED':
            context = NotificationService._build_incident_context(content_object)
        elif notification_type == 'INCIDENT_CLOSED':
            context = NotificationService._build_incident_close_context(content_object)
        elif notification_type == 'INCIDENT_ACTION_ASSIGNED':
            context = NotificationService._build_incident_action_context(content_object)
        elif notification_type == 'INCIDENT_INVESTIGATION_COMPLETED':
            context = NotificationService._build_incident_report_context(content_object)
        elif notification_type == 'HAZARD_REPORTED':
            context = NotificationService._build_hazard_context(content_object)
        elif notification_type in ['HAZARD_ACTION_COMPLETED', 'HAZARD_ACTION_ASSIGNED']:
            context = NotificationService._build_hazard_action_context(content_object)
        elif notification_type == 'EMERGENCY_REPORTED':
            context = NotificationService._build_emergency_reported_context(content_object)
        elif notification_type == 'EMERGENCY_ACTION_ASSIGNED':
            context = NotificationService._build_emergency_action_assigned_context(content_object)
        elif notification_type == 'EMERGENCY_ACTION_COMPLETED':
            context = NotificationService._build_emergency_action_completed_context(content_object)
        elif notification_type == 'EMERGENCY_INVESTIGATION_COMPLETED':
            context = NotificationService._build_emergency_investigation_context(content_object)
        elif notification_type == 'EMERGENCY_CAPA_CREATED':
            context = NotificationService._build_emergency_capa_created_context(content_object)
        elif notification_type == 'EMERGENCY_CAPA_UPDATED':
            context = NotificationService._build_emergency_capa_updated_context(content_object)
        elif notification_type == 'EMERGENCY_CLOSED':
            context = NotificationService._build_emergency_closed_context(content_object)
        elif notification_type == 'ENV_DATA_SUBMITTED':
            context = NotificationService._build_environment_context(content_object)
        elif notification_type == 'NOTIFY_INSPECTION':
            context = NotificationService._build_notify_inspection_context(content_object)
        elif notification_type == 'INSPECTION_NONCOMPLIANCE_ASSIGNED':
            context = NotificationService._build_noncompliance_assigned_context(content_object)
        elif notification_type == 'INCIDENT_INVESTIGATION_OVERDUE':
            context = NotificationService._build_investigation_overdue_context(content_object)
        elif notification_type.startswith('CAPA_') or module == 'CAPA':
            context = NotificationService._build_capa_context(content_object, notification_type)
        elif module == 'INSPECTION':
            context = NotificationService._build_inspection_context(content_object)
        else:
            logger.error(f"Unknown notification type: {notification_type}")
            return


        for stakeholder in stakeholders:
            # print("📨 Processing stakeholder:", stakeholder.email)

            notification = NotificationService.create_notification(
                recipient=stakeholder,
                content_object=content_object,
                notification_type=notification_type,
                title=context.get('title', ''),
                message=context.get('message', '')
            )

            is_responsible_user = (
                (hasattr(content_object, 'responsible_person') and stakeholder in content_object.responsible_person.all())
                or (hasattr(content_object, 'responsible_emails') and stakeholder.email in [e.strip() for e in content_object.responsible_emails.split(',')])
            )

            role_config = NotificationMaster.objects.filter(
                notification_event=notification_type,
                role=stakeholder.role,
                is_active=True
            ).first()

            normalized_extra_recipients = NotificationService._normalize_users(extra_recipients)
            is_extra_recipient = stakeholder in normalized_extra_recipients
            should_send_email = (
                notification_type == 'INSPECTION_SCHEDULE'
                or is_responsible_user
                or (notification_type.startswith('EMERGENCY_') and is_extra_recipient)
                or (role_config and role_config.email_enabled)
            )
            if should_send_email:
                context['recipient'] = stakeholder
                email_sent = NotificationService.send_email(
                    recipient=stakeholder,
                    subject=context.get('subject', ''),
                    message=context.get('message', ''),
                    html_template=NotificationService._resolve_email_template(notification_type, module),
                    context=context
                )

                if email_sent and notification:
                    emails_sent += 1
                    notification.is_email_sent = True
                    notification.email_sent_at = timezone.now()
                    notification.save()

        # print(f"\n{'='*70}")
        # print("NOTIFICATION SUMMARY")
        # print(f"{'='*70}")
        # print(f"Total stakeholders: {len(stakeholders)}")
        # print(f"Notifications created: {notifications_created}")
        # print(f"Emails sent: {emails_sent}")
        # print(f"{'='*70}\n")

    
    
    @staticmethod
    def _build_incident_context(incident):
        """Build context for incident notifications"""
        incident_type = (
            incident.incident_type.name
            if incident.incident_type else 'NA'
        )
        incident_url = f"{settings.SITE_URL}{reverse('accidents:incident_detail', args=[incident.id])}"
        return {
            'title': f"New Injury Reported | {incident.report_number}",
            'subject': f"⚠️ New Injury Reported - {incident.report_number}",
            'message': f"""
Hello,

A new {incident_type} has been reported.

INJURY DETAILS
--------------------------------------------------
Injury Number      : {incident.report_number}
Date & Time          : {incident.incident_date} {incident.incident_time}
Plant                : {incident.plant.name}
Location             : {incident.location.name if incident.location else 'N/A'}
Reported By          : {incident.reported_by.get_full_name()}
Investigation Deadline: {incident.investigation_deadline}

DESCRIPTION
--------------------------------------------------
{incident.description[:300]}{'...' if len(incident.description) > 300 else ''}

Please review this incident and take necessary action.

Regards,
EHS Management System
""",
            'incident': incident,
            'incident_url': incident_url,
        }
    
    
    @staticmethod
    def _build_hazard_context(hazard):
        """Build context for hazard notifications"""
        hazard_url = f"{settings.SITE_URL}{reverse('hazards:hazard_detail', args=[hazard.id])}"

        return {
            'title': f"New Hazard Reported | {hazard.report_number}",
            'subject': f"⚠️ New Hazard Reported - {hazard.report_number}",
            'message': f"""
Hello,

A new hazard has been reported.

HAZARD DETAILS
--------------------------------------------------
Hazard Number   : {hazard.report_number}
Type            : {hazard.get_hazard_type_display()}
Severity        : {hazard.get_severity_display()}
Plant           : {hazard.plant.name}
Location        : {hazard.location.name if hazard.location else 'N/A'}
Reported By     : {hazard.reported_by.get_full_name()}

DESCRIPTION
--------------------------------------------------
{hazard.hazard_description[:300]}{'...' if len(hazard.hazard_description) > 300 else ''}

Please review and take necessary action.

Regards,
EHS Management System
""",
            'hazard': hazard,
            'hazard_url': hazard_url,
        }
    
    @staticmethod
    def _build_incident_report_context(incidentinvestigationreport):
        """
        Build context for Incident Investigation Report notifications
        """
        incident = incidentinvestigationreport.incident
        incident_type = (
            incident.incident_type.name
            if incident.incident_type else 'NA'
        )
        incident_url = f"{settings.SITE_URL}{reverse('accidents:incident_detail', args=[incident.id])}"

        return {
            'title': f"Incident Investigation Completed | {incident.report_number}",
            'subject': f"📝 Investigation Report Submitted - {incident.report_number}",
            'message': f"""
Hello,
The investigation report for the following incident has been completed and submitted.

INCIDENT DETAILS
--------------------------------------------------
Incident Number      : {incident.report_number}
Incident Type        : {incident_type}
Date & Time          : {incident.incident_date} {incident.incident_time}
Plant                : {incident.plant.name}
Zone                 : {incident.zone.name if incident.zone else 'N/A'}
Location             : {incident.location.name if incident.location else 'N/A'}
Sub-Location         : {incident.sublocation.name if incident.sublocation else 'N/A'}
Reported By          : {incident.reported_by.get_full_name()}
Investigation Date   : {incidentinvestigationreport.investigation_date}
Investigator         : {incidentinvestigationreport.investigator.get_full_name()}
Completed On         : {incidentinvestigationreport.completed_date}

INCIDENT DESCRIPTION
--------------------------------------------------
{incident.description[:300]}{'...' if len(incident.description) > 300 else ''}

KEY FINDINGS
--------------------------------------------------
Sequence of Events:
{incidentinvestigationreport.sequence_of_events[:300]}{'...' if len(incidentinvestigationreport.sequence_of_events) > 300 else ''}

Root Cause Analysis:
{incidentinvestigationreport.root_cause_analysis[:300]}{'...' if len(incidentinvestigationreport.root_cause_analysis) > 300 else ''}

RECOMMENDATIONS
--------------------------------------------------
Immediate Corrective Actions:
{incidentinvestigationreport.immediate_corrective_actions[:300]}{'...' if len(incidentinvestigationreport.immediate_corrective_actions) > 300 else ''}

Preventive Measures:
{incidentinvestigationreport.preventive_measures[:300]}{'...' if len(incidentinvestigationreport.preventive_measures) > 300 else ''}

Please review the investigation findings and proceed with action item assignment if required.

Regards,
EHS Management System
""",
        'investigation_report': incidentinvestigationreport,
        'incident':incident,
        'incident_url':incident_url
    }


    @staticmethod
    def _build_incident_close_context(incident):
        """Build context for incident closure notifications"""

        incident_type = (
            incident.incident_type.name
            if incident.incident_type else 'NA'
        )

        plant_name = incident.plant.name if incident.plant else "N/A"
        location_name = incident.location.name if incident.location else "N/A"
        closed_by_name = (
            incident.closed_by.get_full_name()
            if incident.closed_by else "System"
        )

        description = (
            incident.description[:300] + "..."
            if incident.description and len(incident.description) > 300
            else incident.description or "N/A"
        )

        incident_url = f"{settings.SITE_URL}{reverse('accidents:incident_detail', args=[incident.id])}"

        return {
            'title': f"Incident Closed | {incident.report_number}",
            'subject': f"Incident Closed ✅ - {incident.report_number}",
            'message': f"""
Hello,

A {incident_type} has been closed.

INCIDENT DETAILS 
----------------------------------------------------------------------------------
Incident Number     : {incident.report_number}
Date & Time         : {incident.incident_date} {incident.incident_time}
Plant               : {plant_name}
Location            : {location_name}
Closed By           : {closed_by_name}
Closure Date        : {incident.closure_date}

DESCRIPTION
---------------------------------------------------------------------------------
{description}

Regards,
EHS Management System
""",
        'incident': incident,
        'incident_url': incident_url,
    }

    
    @staticmethod
    def _build_incident_action_context(action_item):
        """
        Build context for Incident Action notifications
        """
        incident = action_item.incident
        incident_type = incident.incident_type.name if incident.incident_type else 'NA'
        action_url = f"{settings.SITE_URL}{reverse('accidents:action_item_complete', args=[action_item.id])}"
        
        return {
            'title' : f"Incident Action Assigned | {incident.report_number}",
            'subject': f"✅ Incident Action Assigned - {incident.report_number}",
            'message': f"""
Hello,

An action item for the following incident has been assigned.

INCIDENT DETAILS
------------------------------------------------------------------
Incident Number      : {incident.report_number}
Incident Type        : {incident_type}
Date & Time          : {incident.incident_date} {incident.incident_time}
Plant                : {incident.plant.name}
Zone                 : {incident.zone.name if incident.zone else 'N/A'}
Location             : {incident.location.name if incident.location else 'N/A'}
Sub-Location         : {incident.sublocation.name if incident.sublocation else 'N/A'}
Reported By          : {incident.reported_by.get_full_name()}
Target Date          : {action_item.target_date}
Status               : {action_item.status}
Completion Date      : {action_item.completion_date}

INCIDENT DESCRIPTION
--------------------------------------------------
{incident.description[:300]}{'...' if len(incident.description) > 300 else ''}

ACTION DESCRIPTION
--------------------------------------------------
{action_item.action_description[:300]}{'...' if len(action_item.action_description) > 300 else ''}

Please review and take necessary action.

Regards,
EHS Management System
""",
            'action_item': action_item,
            'incident': incident,
            'action_url':action_url
        }
    

    @staticmethod
    def _build_hazard_action_context(action_item):
        hazard = action_item.hazard
        action_url = f"{settings.SITE_URL}{reverse('hazards:action_item_complete', args=[action_item.id])}"

        return {
            'title': f"Hazard Action Assigned | {hazard.report_number}",
            'subject': f"⚠️ Hazard Action Assigned - {hazard.report_number}",

            'message': f"""
Hello,

A hazard action item has been assigned to you.

HAZARD DETAILS
--------------------------------------------------
Hazard Number     : {hazard.report_number}
Hazard Type       : {hazard.get_hazard_type_display()}
Reported Date     : {hazard.reported_date}
Plant             : {hazard.plant.name}
Zone              : {hazard.zone.name if hazard.zone else 'N/A'}
Location          : {hazard.location.name if hazard.location else 'N/A'}
Sub-Location      : {hazard.sublocation.name if hazard.sublocation else 'N/A'}

ACTION DETAILS
--------------------------------------------------
Description       : {action_item.action_description}
Target Date       : {action_item.target_date}
Status            : {action_item.status}

Please complete the action within the target date.

Regards,
EHS Management System
""",
            'hazard': hazard,
            'action_item': action_item,
            'action_url': action_url,
        }

    @staticmethod
    def _build_emergency_reported_context(report):
        report_url = f"{settings.SITE_URL}{reverse('emergency:report_detail', args=[report.id])}"
        return {
            'title': f"Emergency Reported | {report.report_number}",
            'subject': f"Emergency Reported - {report.report_number}",
            'message': f"""
Hello,

A new emergency has been reported.

EMERGENCY DETAILS
--------------------------------------------------
Emergency Number : {report.report_number}
Emergency Title  : {report.emergency_title}
Type             : {report.get_emergency_type_display()}
Severity         : {report.get_severity_level_display()}
Date & Time      : {report.incident_date} {report.incident_time}
Plant            : {report.plant.name}
Zone             : {report.zone.name if report.zone else 'N/A'}
Location         : {report.location.name if report.location else 'N/A'}
Sub-Location     : {report.sublocation.name if report.sublocation else 'N/A'}
Reported By      : {report.reported_by.get_full_name()}

DESCRIPTION
--------------------------------------------------
{report.description[:500]}{'...' if len(report.description) > 500 else ''}

Please review and take necessary action.

Regards,
EHS Management System
""",
            'report': report,
            'report_url': report_url,
        }

    @staticmethod
    def _build_emergency_action_assigned_context(action_item):
        report = action_item.report
        report_url = f"{settings.SITE_URL}{reverse('emergency:report_detail', args=[report.id])}"
        return {
            'title': f"Emergency Action Assigned | {report.report_number}",
            'subject': f"Emergency Action Assigned - {report.report_number}",
            'message': f"""
Hello,

An emergency action item has been assigned.

EMERGENCY DETAILS
--------------------------------------------------
Emergency Number : {report.report_number}
Emergency Title  : {report.emergency_title}
Type             : {report.get_emergency_type_display()}
Severity         : {report.get_severity_level_display()}
Plant            : {report.plant.name}
Location         : {report.location.name if report.location else 'N/A'}
Reported By      : {report.reported_by.get_full_name()}

ACTION DETAILS
--------------------------------------------------
Description      : {action_item.action_description[:500]}{'...' if len(action_item.action_description) > 500 else ''}
Status           : {action_item.get_status_display()}

Please review and complete the assigned emergency action.

Regards,
EHS Management System
""",
            'report': report,
            'action_item': action_item,
            'report_url': report_url,
        }

    @staticmethod
    def _build_emergency_action_completed_context(action_item):
        report = action_item.report
        report_url = f"{settings.SITE_URL}{reverse('emergency:report_detail', args=[report.id])}"
        completed_by = ", ".join(
            user.get_full_name() or user.username
            for user in action_item.completed_by_users.all()
        ) or 'N/A'
        return {
            'title': f"Emergency Action Completed | {report.report_number}",
            'subject': f"Emergency Action Completed - {report.report_number}",
            'message': f"""
Hello,

An emergency action has been completed.

EMERGENCY DETAILS
--------------------------------------------------
Emergency Number : {report.report_number}
Emergency Title  : {report.emergency_title}
Type             : {report.get_emergency_type_display()}
Severity         : {report.get_severity_level_display()}
Plant            : {report.plant.name}
Location         : {report.location.name if report.location else 'N/A'}

ACTION COMPLETION
--------------------------------------------------
Completed By     : {completed_by}
Completed On     : {action_item.completion_datetime if action_item.completion_datetime else 'N/A'}
Remarks          : {(action_item.completion_remarks or 'N/A')[:500]}

Regards,
EHS Management System
""",
            'report': report,
            'action_item': action_item,
            'report_url': report_url,
        }

    @staticmethod
    def _build_emergency_investigation_context(investigation):
        report = investigation.report
        report_url = f"{settings.SITE_URL}{reverse('emergency:report_detail', args=[report.id])}"
        return {
            'title': f"Emergency Investigation Completed | {report.report_number}",
            'subject': f"Emergency Investigation Completed - {report.report_number}",
            'message': f"""
Hello,

The emergency investigation has been completed.

EMERGENCY DETAILS
--------------------------------------------------
Emergency Number : {report.report_number}
Emergency Title  : {report.emergency_title}
Type             : {report.get_emergency_type_display()}
Plant            : {report.plant.name}
Location         : {report.location.name if report.location else 'N/A'}

INVESTIGATION DETAILS
--------------------------------------------------
Investigator     : {investigation.investigator.get_full_name() if investigation.investigator else 'N/A'}
Investigation Date: {investigation.investigation_date}
Completed On     : {investigation.completed_date}

Regards,
EHS Management System
""",
            'report': report,
            'investigation': investigation,
            'report_url': report_url,
        }

    @staticmethod
    def _build_emergency_capa_created_context(capa):
        report = capa.report
        report_url = f"{settings.SITE_URL}{reverse('emergency:report_detail', args=[report.id])}"
        return {
            'title': f"Emergency CAPA Created | {capa.capa_number}",
            'subject': f"Emergency CAPA Created - {capa.capa_number}",
            'message': f"""
Hello,

A CAPA has been created for an emergency report.

CAPA DETAILS
--------------------------------------------------
CAPA Number      : {capa.capa_number}
Emergency Number : {report.report_number}
Emergency Title  : {report.emergency_title}
Assigned To      : {capa.assigned_to.get_full_name() if capa.assigned_to else 'N/A'}
Target Date      : {capa.target_date}
Status           : {capa.get_status_display()}

ACTION REQUIRED
--------------------------------------------------
{capa.action_required[:500]}{'...' if len(capa.action_required) > 500 else ''}

Regards,
EHS Management System
""",
            'report': report,
            'capa': capa,
            'report_url': report_url,
        }

    @staticmethod
    def _build_emergency_capa_updated_context(capa):
        report = capa.report
        report_url = f"{settings.SITE_URL}{reverse('emergency:report_detail', args=[report.id])}"
        return {
            'title': f"Emergency CAPA Updated | {capa.capa_number}",
            'subject': f"Emergency CAPA Updated - {capa.capa_number}",
            'message': f"""
Hello,

An emergency CAPA has been updated.

CAPA DETAILS
--------------------------------------------------
CAPA Number      : {capa.capa_number}
Emergency Number : {report.report_number}
Assigned To      : {capa.assigned_to.get_full_name() if capa.assigned_to else 'N/A'}
Status           : {capa.get_status_display()}
Target Date      : {capa.target_date}
Closed By        : {capa.closed_by.get_full_name() if capa.closed_by else 'N/A'}

ACTION TAKEN
--------------------------------------------------
{(capa.action_taken or 'N/A')[:500]}

Regards,
EHS Management System
""",
            'report': report,
            'capa': capa,
            'report_url': report_url,
        }

    @staticmethod
    def _build_emergency_closed_context(report):
        report_url = f"{settings.SITE_URL}{reverse('emergency:report_detail', args=[report.id])}"
        return {
            'title': f"Emergency Closed | {report.report_number}",
            'subject': f"Emergency Closed - {report.report_number}",
            'message': f"""
Hello,

The emergency report has been closed.

EMERGENCY DETAILS
--------------------------------------------------
Emergency Number : {report.report_number}
Emergency Title  : {report.emergency_title}
Type             : {report.get_emergency_type_display()}
Severity         : {report.get_severity_level_display()}
Plant            : {report.plant.name}
Location         : {report.location.name if report.location else 'N/A'}
Closed By        : {report.closed_by.get_full_name() if report.closed_by else 'N/A'}
Closed On        : {report.closure_date if report.closure_date else 'N/A'}

CLOSURE REMARKS
--------------------------------------------------
{(report.closure_remarks or 'N/A')[:500]}

Regards,
EHS Management System
""",
            'report': report,
            'report_url': report_url,
        }
    
    @staticmethod
    def _build_environment_context(plant):
        dashboard_url = f"{settings.SITE_URL}{reverse('environmental:plant-data-view')}"
        return{
            'title': f"Enviromental Data Submitted | {plant.name}",
            'subject': f"🌱 Environmental Data Submitted - {plant.name}",
            'message': f"""
Hello,

Monthly environmental data has been submitted successfully.

PLANT DETAILS
--------------------------------------------------
Plant Name : {plant.name}

Please review the submitted enviromental data.

Regards,
EHS Management System
""",
            'plant':plant,
            'dashboard_url':dashboard_url,
        }
    
    @staticmethod
    def _build_inspection_context(schedule):
        inspection_url = f"{settings.SITE_URL}{reverse('inspections:schedule_detail', args=[schedule.id])}"
        
        return{
            'title': f"Inspection {schedule.get_status_display()} | {schedule.schedule_code}",
            'subject': f"📝 Inspection {schedule.get_status_display()} - {schedule.schedule_code}",
            'message': f"""
Hello,

An inspection update has occurred.

INSPECTION DETAILS
--------------------------------------------------
Schedule Code      : {schedule.schedule_code}
Template           : {schedule.template.template_name}
Inspection Type    : {schedule.template.get_inspection_type_display()}
Plant              : {", ".join([p.name for p in schedule.plants.all()]) if schedule.plants.exists() else "N/A"}Department         : {schedule.department.name if schedule.department else 'N/A'}

ASSIGNED DETAILS
--------------------------------------------------
Assigned To        : {schedule.assigned_to.get_full_name()}
Assigned By        : {schedule.assigned_by.get_full_name()}
Scheduled Date     : {schedule.scheduled_date}
Due Date           : {schedule.due_date}

STATUS
--------------------------------------------------
Current Status     : {schedule.get_status_display()}

Please log in to the EHS system for more details.

Regards,
EHS Management System
""",
        'schedule': schedule,
        'inspection_url': inspection_url,
    }

    @staticmethod
    def _build_notify_inspection_context(schedule):
        inspection_url = f"{settings.SITE_URL}{reverse('inspections:schedule_detail', args=[schedule.id])}"
        return{
            'title': f"Inspection Reminder | {schedule.schedule_code}",
            'subject': f"⏰ Reminder: Inspection {schedule.get_status_display()} - {schedule.schedule_code}",
            'message': f"""

Hello {schedule.assigned_to.get_full_name()},

This is a reminder regarding the upcoming inspection.

INSPECTION DETAILS
--------------------------------------------------
Schedule Code      : {schedule.schedule_code}
Template           : {schedule.template.template_name}
Inspection Type    : {schedule.template.get_inspection_type_display()}
Plant              : {", ".join([p.name for p in schedule.plants.all()]) if schedule.plants.exists() else "N/A"}Department         : {schedule.department.name if schedule.department else 'N/A'}
Assigned By        : {schedule.assigned_by.get_full_name()}
Scheduled Date     : {schedule.scheduled_date}
Due Date           : {schedule.due_date}
Current Status     : {schedule.get_status_display()}

Please ensure the inspection is completed within the scheduled timeframe.

Regards,
EHS Management System
""",
        'schedule': schedule,
        'recipient': schedule.assigned_to,
        'inspection_url': inspection_url,
    }

    @staticmethod
    def _build_noncompliance_assigned_context(response):
        schedule = response.submission.schedule
        no_answer_url = f"{settings.SITE_URL}{reverse('inspections:no_answers_list')}"


        return {
            'title': f"Non-Compliance Assigned | {schedule.schedule_code}",
            'subject': f"⚠️ Non-Compliance Assigned - {schedule.schedule_code}",
            'message': f"""

Hello {response.assigned_to.get_full_name()},

A non-compliance item has been assigned to you for corrective action.

NON-COMPLIANCE DETAILS
--------------------------------------------------
Schedule Code      : {schedule.schedule_code}
Inspection Type    : {schedule.template.get_inspection_type_display()}
Template           : {schedule.template.template_name}
Plant              : {schedule.plant.name}
Department         : {schedule.department.name if schedule.department else 'N/A'}
Question           : {response.question.question_text}
Response           : {response.answer}
Assigned By        : {response.assigned_by.get_full_name()}
Assigned On        : {response.assigned_at}
Remarks            : {response.assignment_remarks if response.assignment_remarks else 'N/A'}

Please review the issue and take necessary corrective action at the earliest.

Regards,
EHS Management System
""",
        'response': response,
        'recipient': response.assigned_to,
        'no_answer_url': no_answer_url,
    }

    @staticmethod
    def _build_compliance_base_context(requirement, event_label, subject_prefix):
        requirement_url = f"{settings.SITE_URL}{reverse('legal_compliance:compliance_detail', args=[requirement.id])}"

        responsible_names = ", ".join(
            filter(
                None,
                [
                    user.get_full_name() or user.username
                    for user in requirement.responsible_person.all()
                ],
            )
        ) or "N/A"

        reviewer_names = ", ".join(
            filter(
                None,
                [
                    user.get_full_name() or user.username
                    for user in requirement.reviewer.all()
                ],
            )
        ) or "N/A"

        return {
            'title': f"{event_label} | {requirement.requirement_code}",
            'subject': f"{subject_prefix} - {requirement.requirement_code}",
            'message': f"""
Hello,

A legal compliance item requires your attention.

COMPLIANCE DETAILS
--------------------------------------------------
Requirement Code   : {requirement.requirement_code}
Title              : {requirement.title}
Legal Act          : {requirement.legal_act.act_name if requirement.legal_act else 'N/A'}
Criticality        : {requirement.get_criticality_display()}
Status             : {requirement.get_status_display()}
Due Date           : {requirement.due_date if requirement.due_date else 'N/A'}
Responsible Users  : {responsible_names}
Reviewers          : {reviewer_names}

DESCRIPTION
--------------------------------------------------
{(requirement.description or 'N/A')[:500]}

Please review the requirement in the system and take the necessary action.

Regards,
EHS Management System
""",
            'compliance_requirement': requirement,
            'compliance_url': requirement_url,
        }

    @staticmethod
    def _build_compliance_reminder_context(requirement):
        return NotificationService._build_compliance_base_context(
            requirement,
            event_label=f"Compliance Reminder",
            subject_prefix=f"Compliance Reminder",
        )

    @staticmethod
    def _build_compliance_escalation_context(requirement):
        return NotificationService._build_compliance_base_context(
            requirement,
            event_label=f"Compliance Escalation",
            subject_prefix=f"Compliance Escalation",
        )

    @staticmethod
    def _build_investigation_overdue_context(incident):
        """Build context for investigation overdue notifications"""
        import datetime
        days_overdue = (datetime.date.today() - incident.investigation_deadline).days
        
        incident_type = (
            incident.incident_type.name
            if incident.incident_type else 'NA'
        )
        incident_url = f"{settings.SITE_URL}{reverse('accidents:incident_detail', args=[incident.id])}"

        
        return {
            'title': f"Investigation Overdue | {incident.report_number}",
            'subject': f"⚠️ Investigation Overdue ({days_overdue} day(s)) - {incident.report_number}",
            'message': f"""
    Hello,

    The investigation for the following incident is OVERDUE by {days_overdue} day(s).

    INCIDENT DETAILS
    --------------------------------------------------
    Incident Number       : {incident.report_number}
    Incident Type         : {incident_type}
    Date & Time           : {incident.incident_date} {incident.incident_time}
    Plant                 : {incident.plant.name}
    Zone                  : {incident.zone.name if incident.zone else 'N/A'}
    Location              : {incident.location.name if incident.location else 'N/A'}
    Reported By           : {incident.reported_by.get_full_name()}

    INVESTIGATION STATUS
    --------------------------------------------------
    Investigation Deadline : {incident.investigation_deadline}
    Days Overdue           : {days_overdue} day(s)
    Current Status         : {incident.get_status_display()}

    Please ensure the investigation is completed immediately.

    Regards,
    EHS Management System
    """,
            'incident': incident,
            'days_overdue': days_overdue,
            'incident_url':incident_url,
        }

    @staticmethod
    def _build_capa_context(capa, notification_type):
        capa_url = f"{settings.SITE_URL}{reverse('capa:detail', args=[capa.id])}"
        label = notification_type.replace("CAPA_", "").replace("_", " ").title()
        return {
            'title': f"{label} | {capa.capa_number}",
            'subject': f"CAPA Update - {capa.capa_number}",
            'message': f"""
Hello,

CAPA update: {label}

CAPA DETAILS
--------------------------------------------------
CAPA Number : {capa.capa_number}
Title       : {capa.title}
Status      : {capa.get_status_display()}
Owner       : {capa.owner.get_full_name() if capa.owner else 'N/A'}
Plant       : {capa.plant.name if capa.plant else 'N/A'}
Target Date : {capa.target_date if capa.target_date else 'N/A'}

Please review the CAPA record in the EHS system.

Regards,
EHS Management System
""",
            'capa': capa,
            'capa_url': capa_url,
        }
