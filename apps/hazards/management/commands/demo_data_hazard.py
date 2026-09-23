'''
python manage.py demo_data_hazard
'''
from datetime import timedelta
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.hazards.models import Hazard, HazardActionItem


class Command(BaseCommand):
    help = "Create raw hazard management records using existing employees and organization assignments."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=None, help="Number of existing employees to use.")
        parser.add_argument("--records", type=int, default=20, help="Number of hazard records to create.")

    @transaction.atomic
    def handle(self, *args, **options):
        employee_count = options["count"]
        record_count = options["records"]
        if employee_count is not None and employee_count < 1:
            raise CommandError("Employee count must be greater than 0.")
        if record_count < 1:
            raise CommandError("Records must be greater than 0.")

        users = list(
            User.objects.filter(is_active=True, is_active_employee=True)
            .exclude(is_superuser=True)
            .select_related("department", "plant", "zone", "location", "sublocation")
            .order_by("id")
        )
        if not users:
            raise CommandError("No active employees are available for hazard data.")
        selected_users = users[:employee_count] if employee_count else users
        assigned_users = [user for user in selected_users if user.plant and user.location]
        if not assigned_users:
            raise CommandError("No selected employees have both plant and location assignments.")

        statuses = ["REPORTED", "ACTION_ASSIGNED", "IN_PROGRESS", "CLOSED"]
        approval_statuses = ["PENDING", "APPROVED", "REJECTED"]
        action_statuses = ["PENDING", "IN_PROGRESS", "COMPLETED", "OVERDUE"]
        categories = [value for value, _ in Hazard.HAZARD_CATEGORIES]
        severities = [value for value, _ in Hazard.SEVERITY_CHOICES]
        hazard_types = [value for value, _ in Hazard.HAZARD_TYPE_CHOICES]
        today = timezone.localdate()
        hazard_count = action_count = 0

        for index in range(record_count):
            user = assigned_users[index % len(assigned_users)]
            status = statuses[index % len(statuses)]
            approval_status = approval_statuses[index % len(approval_statuses)]
            is_closed = status == "CLOSED"
            identified_at = timezone.now() - timedelta(days=120 - min(index * 3, 110))
            action_status = action_statuses[index % len(action_statuses)]
            hazard = Hazard.objects.create(
                reporter_name=user.get_full_name() or user.username,
                reporter_email=user.email,
                reporter_phone=user.phone or "",
                behalf_person_name=user.get_full_name() or user.username,
                behalf_person=user,
                behalf_person_dept=user.department,
                hazard_title=[
                    "Unprotected electrical connection",
                    "Blocked emergency access route",
                    "Material stored outside designated area",
                    "Missing personal protective equipment",
                ][index % 4],
                hazard_description="An unsafe workplace condition was identified during routine observation.",
                immediate_action="Area was made safe and the responsible supervisor was informed.",
                hazard_category=categories[index % len(categories)],
                incident_datetime=identified_at,
                severity=severities[index % len(severities)],
                hazard_type=hazard_types[index % len(hazard_types)],
                plant=user.plant,
                zone=user.zone,
                location=user.location,
                sublocation=user.sublocation,
                location_details="Observed near the assigned operating area.",
                injury_status="no",
                witnesses="Work-team members present in the area.",
                user_agent="Operational reporting portal",
                report_source="web_portal",
                reported_by=user,
                assigned_to=selected_users[(index + 1) % len(selected_users)],
                status=status,
                approval_status=approval_status,
                approved_by=selected_users[0] if approval_status == "APPROVED" else None,
                approved_date=timezone.now() if approval_status == "APPROVED" else None,
                approved_remarks="Reviewed by the responsible safety team." if approval_status == "APPROVED" else "",
                corrective_action_plan="Install the required control and verify it during the next area inspection.",
                action_deadline=min(identified_at.date() + timedelta(days=14), today),
                action_completed_date=identified_at.date() + timedelta(days=10) if action_status == "COMPLETED" else None,
                closure_date=today if is_closed else None,
                closure_remarks="Corrective action verified and hazard closed." if is_closed else "",
                forwarded_to=selected_users[(index + 2) % len(selected_users)] if index % 3 == 0 else None,
                forwarded_from=user if index % 3 == 0 else None,
                forward_reason="Requires support from the responsible department." if index % 3 == 0 else "",
                forward_date=timezone.now() if index % 3 == 0 else None,
            )
            hazard_count += 1

            action = HazardActionItem.objects.create(
                hazard=hazard,
                action_description="Implement corrective control and provide verification evidence.",
                responsible_emails=selected_users[(index + 1) % len(selected_users)].email,
                created_by=user,
                is_self_assigned=index % 2 == 0,
                attachment=ContentFile(
                    b"Corrective action record\nWorkplace control verification completed.",
                    name=f"action_record_{index + 1:04d}.txt",
                ),
                target_date=min(identified_at.date() + timedelta(days=14), today),
                status=action_status,
                completion_date=identified_at.date() + timedelta(days=10) if action_status == "COMPLETED" else None,
                completion_remarks="Control implemented and verified." if action_status == "COMPLETED" else "",
                verified_by=selected_users[0] if action_status == "COMPLETED" else None,
                verification_date=identified_at.date() + timedelta(days=11) if action_status == "COMPLETED" else None,
            )
            if action_status == "COMPLETED":
                action.completed_by_users.set([selected_users[0]])
            action_count += 1

        self.stdout.write(self.style.SUCCESS(f"Created {hazard_count} hazard records."))
        self.stdout.write(self.style.SUCCESS(f"Created {action_count} hazard action items."))
        self.stdout.write(self.style.SUCCESS("Hazard management data created successfully."))