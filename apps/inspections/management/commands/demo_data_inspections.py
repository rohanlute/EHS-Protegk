'''
python manage.py demo_data_inspections
'''

from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.inspections.models import (
    InspectionCategory,
    InspectionFinding,
    InspectionQuestion,
    InspectionResponse,
    InspectionSchedule,
    InspectionSubmission,
    InspectionTemplate,
    TemplateQuestion,
)


class Command(BaseCommand):
    help = (
        "Create realistic inspection data using existing employees "
        "and organization assignments."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=None,
            help="Number of existing employees to use. Defaults to all eligible employees.",
        )
        parser.add_argument(
            "--records",
            type=int,
            default=100,
            help="Number of inspection submissions to generate.",
        )

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
            raise CommandError("No active employees are available for data.")

        selected_users = users[:employee_count] if employee_count else users
        if employee_count and len(users) < employee_count:
            self.stdout.write(
                self.style.WARNING(
                    f"Requested {employee_count} employees, but only {len(users)} "
                    "are available. Using all available employees."
                )
            )

        template, questions = self.create_master_data(selected_users[0])
        self.stdout.write(
            self.style.SUCCESS(
                f"Using {len(selected_users)} existing employees and "
                f"template '{template.template_name}'."
            )
        )

        schedules = []
        submissions = []
        response_count = 0
        finding_count = 0
        today = timezone.localdate()
        schedule_statuses = [
            "SCHEDULED",
            "IN_PROGRESS",
            "CLOSED",
            "CLOSED_LATE",
            "OVERDUE",
            "CANCELLED",
        ]
        finding_statuses = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]

        for index in range(record_count):
            user = selected_users[index % len(selected_users)]
            inspection_date = self.demo_date(index, record_count, today)
            schedule_status = schedule_statuses[index % len(schedule_statuses)]
            schedule = InspectionSchedule.objects.create(
                template=template,
                assigned_to=user,
                assigned_by=selected_users[0],
                scheduled_date=inspection_date,
                due_date=inspection_date + timedelta(days=7),
                status="SCHEDULED",
                assignment_notes="Inspection generated from existing organization data.",
                department=user.department,
            )
            if user.plant:
                schedule.plants.set([user.plant])
            if user.zone:
                schedule.zones.set([user.zone])
            if user.location:
                schedule.locations.set([user.location])
            if user.sublocation:
                schedule.sublocations.set([user.sublocation])
            schedule.assigned_users.set(selected_users)

            submitted_at = timezone.now() - timedelta(days=index % 30)
            submission = InspectionSubmission.objects.create(
                schedule=schedule,
                submitted_by=user,
                remarks="Inspection completed using realistic raw inspection responses.",
            )

            yes_count = 0
            for question_index, question in enumerate(questions):
                answer_selector = (index + question_index) % 11
                is_non_compliant = answer_selector == 0
                answer = (
                    "No"
                    if is_non_compliant
                    else ("N/A" if answer_selector == 1 else "Yes")
                )
                if answer == "Yes":
                    yes_count += 1

                response = InspectionResponse.objects.create(
                    submission=submission,
                    question=question,
                    answer=answer,
                    remarks=(
                        "Corrective action required for observed non-compliance."
                        if is_non_compliant
                        else "Requirement verified during inspection."
                    ),
                    assigned_to=(selected_users[(index + 1) % len(selected_users)]
                                 if is_non_compliant else None),
                    assigned_by=(selected_users[0] if is_non_compliant else None),
                    assigned_at=(timezone.now() if is_non_compliant else None),
                    specific_location=(
                        user.sublocation.name
                        if is_non_compliant and user.sublocation
                        else (user.location.name if is_non_compliant and user.location else "")
                    ),
                    assignment_remarks=(
                        "Review and close the corrective action."
                        if is_non_compliant
                        else ""
                    ),
                )
                response_count += 1

                if is_non_compliant and question.auto_generate_finding:
                    finding_status = finding_statuses[
                        finding_count % len(finding_statuses)
                    ]
                    InspectionFinding.objects.create(
                        submission=submission,
                        question=question,
                        finding_code=f"{schedule.schedule_code}-{question.question_code}",
                        description=f"Non-compliance found: {question.question_text}",
                        priority="HIGH" if question.is_critical else "MEDIUM",
                        status=finding_status,
                        assigned_to=response.assigned_to,
                        due_date=min(inspection_date + timedelta(days=14), today),
                        resolved_at=(
                            timezone.now()
                            if finding_status in ["RESOLVED", "CLOSED"]
                            else None
                        ),
                        resolution_notes=(
                            "Corrective action completed and verified."
                            if finding_status in ["RESOLVED", "CLOSED"]
                            else None
                        ),
                    )
                    finding_count += 1

            submission.compliance_score = round((yes_count / len(questions)) * 100, 2)
            submission.submitted_at = submitted_at
            submission.save(update_fields=["compliance_score", "submitted_at"])

            schedule.started_at = (
                timezone.now() - timedelta(minutes=45)
                if schedule_status in [
                    "IN_PROGRESS",
                    "CLOSED",
                    "CLOSED_LATE",
                    "OVERDUE",
                ]
                else None
            )
            schedule.closed_at = (
                timezone.now()
                if schedule_status in ["CLOSED", "CLOSED_LATE"]
                else None
            )
            schedule.status = schedule_status
            InspectionSchedule.objects.filter(pk=schedule.pk).update(
                started_at=schedule.started_at,
                closed_at=schedule.closed_at,
                status=schedule.status,
            )
            schedules.append(schedule)
            submissions.append(submission)

        self.stdout.write(self.style.SUCCESS(f"Created {len(schedules)} inspection schedules."))
        self.stdout.write(self.style.SUCCESS(f"Created {len(submissions)} inspection submissions."))
        self.stdout.write(self.style.SUCCESS(f"Created {response_count} inspection responses."))
        self.stdout.write(self.style.SUCCESS(f"Created {finding_count} inspection findings."))
        self.stdout.write(self.style.SUCCESS("Inspection data created successfully."))

    @staticmethod
    def demo_date(index, record_count, today):
        start_date = today - timedelta(days=180)
        total_days = (today - start_date).days
        if record_count <= 1:
            return start_date
        return start_date + timedelta(days=(index * total_days) // (record_count - 1))

    def create_master_data(self, created_by):
        template = InspectionTemplate.objects.filter(
            template_code="EHS-INSPECTION-001"
        ).first() or InspectionTemplate.objects.filter(
            template_name="Workplace Safety Inspection"
        ).first()
        if template is None:
            template = InspectionTemplate(
                template_code="",
                template_name="Workplace Safety Inspection",
                inspection_type="MONTHLY",
                description="Reusable template for inspection raw data.",
                min_compliance_score=80,
                is_active=True,
                created_by=created_by,
            )
            template.save()

        question_data = [
            ("HOUSEKEEPING", "Housekeeping", "Are work areas clean and free from obstructions?", False),
            ("HOUSEKEEPING", "Housekeeping", "Are waste containers available and properly used?", False),
            ("FIRE_SAFETY", "Fire Safety", "Are fire extinguishers accessible and inspected?", True),
            ("FIRE_SAFETY", "Fire Safety", "Are emergency exits clearly marked and unobstructed?", True),
            ("PPE", "Personal Protective Equipment", "Is required PPE available and being used?", True),
            ("PPE", "Personal Protective Equipment", "Is PPE stored in a clean and serviceable condition?", False),
            ("ELECTRICAL", "Electrical Safety", "Are electrical panels closed and properly identified?", True),
            ("ELECTRICAL", "Electrical Safety", "Are extension cables free from damage and unsafe joints?", False),
        ]

        questions = []
        for category_code, category_name, question_text, is_critical in question_data:
            category = InspectionCategory.objects.filter(
                category_code=category_code
            ).first() or InspectionCategory.objects.filter(
                category_name=category_name
            ).first()
            if category is None:
                category = InspectionCategory.objects.create(
                    category_name=category_name,
                    category_code=category_code,
                    description=f"{category_name.lower()} inspection checks.",
                    is_active=True,
                    created_by=created_by,
                )
            question_code = f"{category_code}-{len(questions) + 1:03d}"
            question, _ = InspectionQuestion.objects.get_or_create(
                question_code=question_code,
                defaults={
                    "category": category,
                    "question_text": question_text,
                    "question_type": "YES_NO",
                    "is_remarks_mandatory": True,
                    "is_critical": is_critical,
                    "auto_generate_finding": True,
                    "reference_standard": "EHS Checklist",
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            TemplateQuestion.objects.get_or_create(
                template=template,
                question=question,
                defaults={"is_mandatory": True, "section_name": category_name},
            )
            questions.append(question)

        template.applicable_plants.clear()
        return template, questions