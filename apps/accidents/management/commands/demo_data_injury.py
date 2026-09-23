'''
python manage.py demo_data_injury
'''
import datetime
from datetime import time, timedelta
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.accidents.models import (
    Incident,
    IncidentActionItem,
    IncidentInvestigationReport,
    IncidentType,
)


class Command(BaseCommand):
    help = "Create raw incident and injury management records using existing employees."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=None, help="Number of existing employees to use.")
        parser.add_argument("--records", type=int, default=20, help="Number of incident records to create.")

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
            raise CommandError("No active employees are available for incident data.")
        selected_users = users[:employee_count] if employee_count else users
        assigned_users = [user for user in selected_users if user.plant and user.location]
        if not assigned_users:
            raise CommandError("No selected employees have both plant and location assignments.")

        incident_types = self.create_incident_types(selected_users[0])
        statuses = [
            "REPORTED", "INVESTIGATION_IN_PROGRESS", "ACTION_PLAN_PENDING",
            "PENDING_APPROVAL", "REJECTED", "PENDING_CLOSE", "CLOSED",
        ]
        approval_statuses = ["PENDING", "APPROVED", "REJECTED"]
        action_statuses = ["PENDING", "IN_PROGRESS", "COMPLETED", "OVERDUE"]
        today = timezone.localdate()
        incident_count = investigation_count = action_count = 0

        for index in range(record_count):
            user = assigned_users[index % len(assigned_users)]
            incident_date = today - timedelta(days=120 - min(index * 3, 110))
            status = statuses[index % len(statuses)]
            approval_status = approval_statuses[index % len(approval_statuses)]
            is_closed = status == "CLOSED"
            incident = Incident.objects.create(
                affected_employment_category=(
                    user.employment_type if user.employment_type in {"CONTRACT", "FULL_TIME"}
                    else "PERMANENT"
                ),
                affected_person_name=user.get_full_name() or user.username,
                affected_person_employee_id=user.employee_id or f"EMP-{user.pk:04d}",
                affected_person_department=user.department,
                affected_date_of_birth=user.date_of_birth,
                affected_age=(today.year - user.date_of_birth.year if user.date_of_birth else None),
                affected_gender=user.gender or "PREFER_NOT_TO_SAY",
                affected_job_title=user.job_title or "Operations Employee",
                affected_date_of_joining=user.date_joined_company,
                incident_type=incident_types[index % len(incident_types)],
                incident_date=incident_date,
                incident_time=time(10, 30),
                plant=user.plant,
                zone=user.zone,
                location=user.location,
                sublocation=user.sublocation,
                additional_location_details="Work area near the assigned operating equipment.",
                description="Employee reported an incident during routine workplace activity.",
                unsafe_acts=["Inadequate attention to the immediate work condition"],
                unsafe_conditions=["Temporary obstruction in the work area"],
                affected_person=user,
                affected_body_parts=["Hand"],
                nature_of_injury="Minor strain requiring first aid assessment.",
                reported_by=user,
                investigation_required=True,
                investigation_completed_date=(incident_date + timedelta(days=5) if status in ["PENDING_CLOSE", "CLOSED"] else None),
                investigator=selected_users[0] if status in ["PENDING_CLOSE", "CLOSED"] else None,
                root_cause="Work-area control was not maintained consistently.",
                contributing_factors="Insufficient housekeeping follow-up.",
                action_plan="Reinforce housekeeping checks and supervisor verification.",
                action_plan_deadline=min(incident_date + timedelta(days=21), today),
                action_plan_responsible_person=selected_users[(index + 1) % len(selected_users)],
                action_plan_status=("COMPLETED" if is_closed else "IN_PROGRESS" if status in ["ACTION_PLAN_PENDING", "PENDING_CLOSE"] else "PENDING"),
                status=status,
                assigned_to=selected_users[(index + 1) % len(selected_users)],
                safety_manager_notified=True,
                location_head_notified=index % 2 == 0,
                plant_head_notified=is_closed,
                approval_status=approval_status,
                approved_by=selected_users[0] if approval_status == "APPROVED" else None,
                approved_date=timezone.now() if approval_status == "APPROVED" else None,
                rejection_remarks="Additional investigation details required." if approval_status == "REJECTED" else "",
                closure_date=timezone.now() if is_closed else None,
                closed_by=selected_users[0] if is_closed else None,
                closure_remarks="Corrective actions verified and incident closed." if is_closed else "",
                lessons_learned="Maintain clear work areas and complete supervisor checks.",
                preventive_measures="Repeat toolbox briefing and verify controls during inspections.",
                is_recurrence_possible=index % 3 == 0,
            )
            incident_count += 1

            if status in ["PENDING_CLOSE", "CLOSED"]:
                IncidentInvestigationReport.objects.create(
                    incident=incident,
                    investigation_date=incident_date + timedelta(days=2),
                    investigator=selected_users[0],
                    investigation_team="EHS and department representatives",
                    sequence_of_events="Incident reported, area secured, facts reviewed and actions assigned.",
                    root_cause_analysis="Control verification was not completed at the required frequency.",
                    personal_factors=["Work pace"],
                    job_factors=["Housekeeping control"],
                    evidence_collected="Supervisor notes and employee statement.",
                    witness_statements="Work-team statement recorded.",
                    immediate_corrective_actions="Remove obstruction and brief the work team.",
                    preventive_measures="Add verification to the routine area checklist.",
                    completed_by=selected_users[0],
                    completed_date=incident_date + timedelta(days=5),
                    reviewed_by=selected_users[0] if is_closed else None,
                    reviewed_date=incident_date + timedelta(days=6) if is_closed else None,
                )
                investigation_count += 1

            action_status = action_statuses[index % len(action_statuses)]
            action = IncidentActionItem.objects.create(
                incident=incident,
                action_description="Implement corrective controls and verify completion.",
                target_date=min(incident_date + timedelta(days=14), today),
                status=action_status,
                completion_date=incident_date + timedelta(days=10) if action_status == "COMPLETED" else None,
                completion_remarks="Corrective control verified." if action_status == "COMPLETED" else "",
                assignment_type="SELF" if index % 2 == 0 else "FORWARD",
                created_by=selected_users[0],
                verified_by=selected_users[0] if action_status == "COMPLETED" else None,
                verification_date=incident_date + timedelta(days=11) if action_status == "COMPLETED" else None,
            )
            action.responsible_person.set([selected_users[(index + 1) % len(selected_users)]])
            if action_status == "COMPLETED":
                action.completed_by.set([selected_users[0]])
            action_count += 1

        self.stdout.write(self.style.SUCCESS(f"Created {incident_count} incident records."))
        self.stdout.write(self.style.SUCCESS(f"Created {investigation_count} investigation reports."))
        self.stdout.write(self.style.SUCCESS(f"Created {action_count} incident action items."))
        self.stdout.write(self.style.SUCCESS("Incident and injury data created successfully."))

    def create_incident_types(self, created_by):
        type_data = [
            ("First Aid Case", "FAC", "Minor injury requiring first aid."),
            ("Near Miss", "NMI", "Unplanned event with no injury or damage."),
            ("Medical Treatment Case", "MTC", "Injury requiring medical treatment."),
            ("Property Damage", "PD", "Event resulting in workplace property damage."),
        ]
        types = []
        for name, code, description in type_data:
            incident_type = IncidentType.objects.filter(code=code).first()
            if incident_type is None:
                incident_type = IncidentType.objects.filter(name=name).first()
            if incident_type is None:
                incident_type = IncidentType.objects.create(
                    name=name, code=code, description=description,
                    is_active=True, created_by=created_by,
                )
            types.append(incident_type)
        return types