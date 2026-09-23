'''
python manage.py demo_data_emergency
'''
import datetime
from datetime import time, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.emergency.models import (
    EmergencyCAPA,
    EmergencyInvestigationReport,
    EmergencyReport,
    EmergencyActionItem,
    EmergencySession,
    EmergencySessionParticipant,
    EmergencySessionQuestionAssignment,
    EmergencySessionResponse,
    EmergencySessionSubmission,
    EmergencySessionTrainer,
    EmergencyTopic,
    ERTDepartmentQuestion,
)


class Command(BaseCommand):
    help = "Create realistic Emergency data using existing employees and organization assignments."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=None, help="Number of existing employees to use.")
        parser.add_argument("--records", type=int, default=20, help="Number of emergency records and sessions to generate.")

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
            raise CommandError("No active employees are available for emergency data.")

        selected_users = users[:employee_count] if employee_count else users
        assigned_users = [user for user in selected_users if user.plant and user.location]
        if not assigned_users:
            raise CommandError("No selected employees have both plant and location assignments.")

        topic_list = self.create_topics(selected_users[0])
        question_list = self.create_questions(selected_users[0], topic_list)
        today = timezone.localdate()
        session_statuses = ["SCHEDULED", "ONGOING", "COMPLETED", "CANCELLED"]
        participant_statuses = ["ASSIGNED", "IN_PROGRESS", "COMPLETED", "APPROVED", "REJECTED"]
        review_statuses = {"COMPLETED": "PENDING", "APPROVED": "APPROVED", "REJECTED": "REJECTED"}
        report_statuses = ["REPORTED", "ACTION_PENDING", "ACTION_PERFORMED", "INVESTIGATION_COMPLETED", "CLOSED"]
        capa_statuses = [EmergencyCAPA.STATUS_OPEN, EmergencyCAPA.STATUS_IN_PROGRESS, EmergencyCAPA.STATUS_CLOSED]

        session_count = participant_count = response_count = 0
        report_count = action_count = investigation_count = capa_count = 0

        for index in range(record_count):
            user = assigned_users[index % len(assigned_users)]
            plant = user.plant
            location = user.location
            session_date = today - timedelta(days=90) + timedelta(days=(index * 90) // max(record_count - 1, 1))
            session_status = session_statuses[index % len(session_statuses)]
            session = EmergencySession.objects.create(
                topic=topic_list[index % len(topic_list)],
                drill_type=EmergencySession.DRILL_TYPE_CHOICES[index % len(EmergencySession.DRILL_TYPE_CHOICES)][0],
                plant=plant,
                zone=user.zone,
                location=location,
                sublocation=user.sublocation,
                venue_details=f"{location.name} emergency assembly area",
                scheduled_date=session_date,
                scheduled_time=time(10, 0),
                end_time=time(12, 0),
                duration_hours=2,
                agenda="Emergency response drill, evacuation practice and role assessment.",
                max_participants=len(selected_users),
                remarks="Emergency session.",
                status=session_status,
                created_by=selected_users[0],
            )
            EmergencySessionTrainer.objects.create(
                session=session,
                trainer_user=selected_users[0],
                trainer_name=selected_users[0].get_full_name() or selected_users[0].username,
            )
            session_count += 1

            for participant_offset, employee in enumerate(selected_users[: min(5, len(selected_users))]):
                participant_status = participant_statuses[(index + participant_offset) % len(participant_statuses)]
                participant = EmergencySessionParticipant.objects.create(
                    session=session,
                    employee=employee,
                    status=participant_status,
                    started_at=timezone.now() if participant_status != "ASSIGNED" else None,
                    completed_at=timezone.now() if participant_status in ["COMPLETED", "APPROVED", "REJECTED"] else None,
                    reviewed_at=timezone.now() if participant_status in ["APPROVED", "REJECTED"] else None,
                    reviewed_by=selected_users[0] if participant_status in ["APPROVED", "REJECTED"] else None,
                )
                participant_count += 1

                assignments = []
                for question in question_list:
                    assignment = EmergencySessionQuestionAssignment.objects.create(
                        participant=participant,
                        question=question,
                    )
                    assignments.append(assignment)

                if participant_status in ["COMPLETED", "APPROVED", "REJECTED"]:
                    submission = EmergencySessionSubmission.objects.create(
                        participant=participant,
                        submitted_by=employee,
                        overall_remarks="Emergency drill assessment completed for data.",
                        review_status=review_statuses[participant_status],
                        reviewer_remarks=(
                            "Assessment reviewed and accepted."
                            if participant_status == "APPROVED"
                            else "Assessment requires corrective follow-up."
                            if participant_status == "REJECTED"
                            else "Awaiting review."
                        ),
                        reviewed_by=selected_users[0] if participant_status in ["APPROVED", "REJECTED"] else None,
                        reviewed_at=timezone.now() if participant_status in ["APPROVED", "REJECTED"] else None,
                    )
                    positive_count = 0
                    for response_index, assignment in enumerate(assignments):
                        answer = "No" if (index + response_index) % 5 == 0 else "Yes"
                        positive_count += answer == "Yes"
                        EmergencySessionResponse.objects.create(
                            submission=submission,
                            assignment=assignment,
                            question=assignment.question,
                            answer=answer,
                            remarks="Corrective action noted." if answer == "No" else "Requirement verified.",
                        )
                        response_count += 1
                    submission.compliance_score = round((positive_count / len(assignments)) * 100, 2)
                    submission.save(update_fields=["compliance_score"])

            report_status = report_statuses[index % len(report_statuses)]
            incident_date = today - timedelta(days=120) + timedelta(days=index * 4)
            report = EmergencyReport.objects.create(
                emergency_title=f"{topic_list[index % len(topic_list)].name} Emergency",
                emergency_type=EmergencyReport.EMERGENCY_TYPE_CHOICES[index % len(EmergencyReport.EMERGENCY_TYPE_CHOICES)][0],
                severity_level=EmergencyReport.SEVERITY_CHOICES[index % len(EmergencyReport.SEVERITY_CHOICES)][0],
                incident_date=incident_date,
                incident_time=time(14, 15),
                plant=plant,
                zone=user.zone,
                location=location,
                sublocation=user.sublocation,
                additional_location_details="Near the main emergency response point.",
                incident_department=user.department,
                department=user.department,
                description="Emergency report created for testing response workflows.",
                immediate_actions_taken="Area isolated and emergency response team notified.",
                reported_by=user,
                status=report_status,
                closure_remarks="Emergency closed after corrective actions were verified." if report_status == "CLOSED" else "",
                lessons_learned="Reinforce emergency communication and evacuation readiness.",
                preventive_measures="Conduct refresher drills and inspect emergency equipment.",
                is_recurrence_possible=index % 3 == 0,
                closure_date=timezone.now() if report_status == "CLOSED" else None,
                closed_by=selected_users[0] if report_status == "CLOSED" else None,
            )
            report.response_team_members.set(selected_users[: min(3, len(selected_users))])
            report_count += 1

            action_status = "ACTION_PERFORMED" if report_status in ["ACTION_PERFORMED", "INVESTIGATION_COMPLETED", "CLOSED"] else "PENDING"
            action_item = EmergencyActionItem.objects.create(
                report=report,
                action_description="Complete emergency corrective action and verify area readiness.",
                completion_datetime=timezone.now() if action_status == "ACTION_PERFORMED" else None,
                completion_remarks="Corrective action completed during workflow." if action_status == "ACTION_PERFORMED" else "",
                status="PENDING",
                created_by=selected_users[0],
            )
            action_item.assigned_to.set(selected_users[: min(2, len(selected_users))])
            if action_status == "ACTION_PERFORMED":
                action_item.completed_by_users.set([selected_users[0]])
                action_item.save()
            action_count += 1

            if report_status in ["INVESTIGATION_COMPLETED", "CLOSED"]:
                EmergencyInvestigationReport.objects.create(
                    report=report,
                    investigation_date=incident_date + timedelta(days=2),
                    investigator=selected_users[0],
                    investigation_team="EHS and Emergency Response Team",
                    sequence_of_events="Incident reported, area secured, response team deployed and controls restored.",
                    root_cause_analysis="Root cause identified as insufficient emergency preparedness.",
                    evidence_collected="Inspection notes, response log and team observations.",
                    witness_statements="Witness statements recorded.",
                    immediate_corrective_actions="Reinforce emergency response procedures.",
                    preventive_measures="Schedule refresher training and follow-up inspection.",
                    completed_date=incident_date + timedelta(days=5),
                )
                investigation_count += 1

            capa_status = capa_statuses[index % len(capa_statuses)]
            capa = EmergencyCAPA.objects.create(
                report=report,
                action_required="Implement and verify preventive emergency controls.",
                assigned_to=selected_users[(index + 1) % len(selected_users)],
                target_date=min(incident_date + timedelta(days=30), today),
                action_taken="Preventive controls implemented and verified." if capa_status == EmergencyCAPA.STATUS_CLOSED else "",
                status=capa_status,
                closure_remarks="CAPA closed after evidence review." if capa_status == EmergencyCAPA.STATUS_CLOSED else "",
                created_by=selected_users[0],
                closed_by=selected_users[0] if capa_status == EmergencyCAPA.STATUS_CLOSED else None,
                closed_at=timezone.now() if capa_status == EmergencyCAPA.STATUS_CLOSED else None,
            )
            capa_count += 1

        self.stdout.write(self.style.SUCCESS(f"Created {session_count} emergency sessions."))
        self.stdout.write(self.style.SUCCESS(f"Created {participant_count} session participants."))
        self.stdout.write(self.style.SUCCESS(f"Created {response_count} session responses."))
        self.stdout.write(self.style.SUCCESS(f"Created {report_count} emergency reports."))
        self.stdout.write(self.style.SUCCESS(f"Created {action_count} emergency action items."))
        self.stdout.write(self.style.SUCCESS(f"Created {investigation_count} investigation reports."))
        self.stdout.write(self.style.SUCCESS(f"Created {capa_count} emergency CAPAs."))
        self.stdout.write(self.style.SUCCESS("Emergency data created successfully."))

    def create_topics(self, created_by):
        topic_data = [
            ("Fire Emergency Response", "FIRE-01", "FIRE_EMERGENCIES"),
            ("Chemical Spill Response", "CHEM-01", "CHEMICAL_SPILLS"),
            ("Medical Emergency Response", "MED-01", "MEDICAL_EMERGENCIES"),
            ("Evacuation Readiness", "EVAC-01", "EVACUATION_SITUATIONS"),
        ]
        topics = []
        for name, code, category in topic_data:
            topic, _ = EmergencyTopic.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "category": category,
                    "description": f"Emergency topic for {name.lower()}.",
                    "validity_period_days": 365,
                    "passing_score": 70,
                    "is_mandatory": True,
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            topics.append(topic)
        return topics

    def create_questions(self, created_by, topics):
        department = created_by.department
        if department is None:
            raise CommandError("The first selected employee has no department for ERT questions.")
        question_data = [
            ("Is the emergency alarm system operational?", True),
            ("Are emergency exits and assembly points accessible?", True),
            ("Are emergency response roles clearly understood?", False),
            ("Is the required emergency equipment available?", False),
        ]
        questions = []
        for index, (text, critical) in enumerate(question_data, start=1):
            question, _ = ERTDepartmentQuestion.objects.get_or_create(
                question_code=f"EHS-ERT-{index:03d}",
                defaults={
                    "department": department,
                    "question_text": text,
                    "question_type": "YES_NO",
                    "is_remarks_mandatory": True,
                    "is_critical": critical,
                    "auto_generate_finding": True,
                    "reference_standard": "Emergency Response Checklist",
                    "guidance_notes": "Verify during emergency drill.",
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            question.topics.set(topics)
            questions.append(question)
        return questions