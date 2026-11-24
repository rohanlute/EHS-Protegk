"""5S demo-data command. Reuses existing active users/plants; creates no org/users."""

import base64
import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Plant
from apps.five_s.models import (
    FiveSQuestion,
    FiveSTemplate,
    FiveSTemplateQuestion,
    FiveSSchedule,
    FiveSAudit,
    AuditAnswer,
    CorrectiveAction,
)


# Five pillars and practical observable questions for a general workplace.
QUESTION_DATA = {
    "SEIRI": [
        ("Are unnecessary tools and materials removed?", "Only required items remain in the area."),
        ("Are obsolete or damaged items identified and segregated?", "Check red-tag or quarantine items."),
        ("Are unwanted items disposed of through an approved process?", "Verify approved disposal or transfer."),
        ("Are items kept only where they are needed?", "Check workstations and storage points."),
        ("Are red-tagged items reviewed within the required time?", "Review the red-tag register."),
    ],
    "SEITON": [
        ("Are tools stored in their designated locations?", "Check labels and shadow boards."),
        ("Are storage locations clearly labelled?", "Labels must be visible and legible."),
        ("Are walkways and exits kept clear?", "Check emergency access routes."),
        ("Are frequently used items easy and safe to reach?", "Avoid excessive reaching or bending."),
        ("Are cables and hoses arranged to prevent trip hazards?", "Check floor-level routes."),
    ],
    "SEISO": [
        ("Are floors and work surfaces clean and spill-free?", "Check oil, water, dust, and contamination."),
        ("Are machines clean and free from abnormal leakage?", "Report leaks for maintenance."),
        ("Are cleaning tools available and stored properly?", "Check their condition and location."),
        ("Are waste bins clean, labelled, and not overflowing?", "Check waste segregation."),
        ("Are cleaning duties and frequencies followed?", "Review cleaning schedules."),
    ],
    "SEIKETSU": [
        ("Are 5S standards and visual controls displayed?", "Check photographs, labels, and instructions."),
        ("Are storage standards followed consistently?", "Compare similar work areas."),
        ("Are current inspection checklists available?", "Verify the latest approved checklist."),
        ("Are abnormal conditions clearly marked and reported?", "Check tags, barriers, and reports."),
        ("Are floor markings and safety signs maintained?", "Check visibility and condition."),
    ],
    "SHITSUKE": [
        ("Do employees follow established 5S standards?", "Observe actual work practices."),
        ("Are 5S checks completed at the assigned frequency?", "Review completed checklists."),
        ("Are previous findings closed on time?", "Verify action status and evidence."),
        ("Do employees understand housekeeping responsibilities?", "Ask about area ownership."),
        ("Are 5S improvement opportunities followed up?", "Check improvement actions."),
    ],
}

PILLAR_LABELS = {
    "SEIRI": "Seiri - Sort",
    "SEITON": "Seiton - Set in Order",
    "SEISO": "Seiso - Shine",
    "SEIKETSU": "Seiketsu - Standardize",
    "SHITSUKE": "Shitsuke - Sustain",
}


class Command(BaseCommand):
    help = "Create demo data for the 5S module."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Schedules/audits to create (default 100).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]

        if count < 1:
            raise CommandError("--count must be at least 1.")

        # Current financial year starts on April 1.
        today = timezone.localdate()
        fy_start = datetime(
            today.year if today.month >= 4 else today.year - 1,
            4,
            1,
        ).date()

        day_span = max((today - fy_start).days, 0)

        # Reuse existing active users and plants.
        users = list(User.objects.filter(is_active=True).order_by("pk"))
        plants = list(Plant.objects.filter(is_active=True).order_by("pk"))

        if not users:
            raise CommandError("No active users found. Add users first.")

        if not plants:
            raise CommandError("No active plants found. Add plants first.")

        self.stdout.write(f"Creating 5S demo data: {fy_start} to {today}")
        self.stdout.write(
            f"Using {len(users)} active users and {len(plants)} active plants."
        )

        # ---------------------------------------------------------
        # 1. Seed or reuse 25 master checklist questions.
        # ---------------------------------------------------------
        questions = []

        for pillar, data in QUESTION_DATA.items():
            for number, (question_text, guidance) in enumerate(data, 1):
                code = f"DEMO5S-{pillar}-{number:02d}"

                question, _ = FiveSQuestion.objects.get_or_create(
                    question_code=code,
                    defaults={
                        "pillar": pillar,
                        "question_text": question_text,
                        "reference_standard": "Internal 5S Workplace Standard",
                        "guidance_notes": guidance,
                        "is_active": True,
                        "created_by": users[0],
                    },
                )

                # Keep demo questions active and refresh their wording.
                fields_to_update = []

                for field, value in (
                    ("pillar", pillar),
                    ("question_text", question_text),
                    ("guidance_notes", guidance),
                    ("is_active", True),
                ):
                    if getattr(question, field) != value:
                        setattr(question, field, value)
                        fields_to_update.append(field)

                if fields_to_update:
                    question.save(
                        update_fields=fields_to_update + ["updated_at"]
                    )

                questions.append((question, PILLAR_LABELS[pillar]))

        # ---------------------------------------------------------
        # 2. Create or reuse the General 5S checklist template.
        # ---------------------------------------------------------
        template, _ = FiveSTemplate.objects.get_or_create(
            template_code="DEMO-5S-GENERAL",
            version=1,
            defaults={
                "template_name": "Demo General Workplace 5S Checklist",
                "description": "Demo checklist covering all five 5S pillars.",
                "min_compliance_score": Decimal("80.00"),
                "is_active": True,
                "created_by": users[0],
            },
        )

        # Map every question to the template in pillar order.
        for order, (question, pillar_label) in enumerate(questions, 1):
            FiveSTemplateQuestion.objects.get_or_create(
                template=template,
                question=question,
                defaults={
                    "is_mandatory": True,
                    "display_order": order,
                    "section_name": pillar_label,
                },
            )

        mappings = list(
            template.template_questions.filter(
                question__is_active=True
            ).select_related(
                "question"
            ).order_by(
                "display_order", "id"
            )
        )

        if not mappings:
            raise CommandError(
                "The demo 5S template has no active questions."
            )

        # ---------------------------------------------------------
        # 3. Sample PNG evidence for Poor/Fair answers.
        # AuditAnswer.save() requires remarks and evidence for ratings 1/2.
        # ---------------------------------------------------------
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
            "/x8AAwMCAO+j2ioAAAAASUVORK5CYII="
        )

        audit_statuses = [
            "SCHEDULED",
            "IN_PROGRESS",
            "SUBMITTED",
            "REVIEWED",
            "CLOSED",
        ]

        schedule_statuses = [
            "ACTIVE",
            "ACTIVE",
            "ACTIVE",
            "PAUSED",
            "ENDED",
        ]

        frequencies = [
            "DAILY",
            "WEEKLY",
            "MONTHLY",
            "QUARTERLY",
            "YEARLY",
        ]

        action_statuses = [
            "ASSIGNED",
            "SUBMITTED",
            "CLOSED",
            "REJECTED",
        ]

        new_audits = 0
        new_answers = 0
        new_actions = 0

        # ---------------------------------------------------------
        # 4. Create schedules, audits, answers, and corrective actions.
        # ---------------------------------------------------------
        for index in range(count):
            plant = plants[index % len(plants)]
            inspector = users[index % len(users)]
            assignee = users[(index + 1) % len(users)]
            verifier = users[(index + 2) % len(users)]

            schedule_status = random.choice(schedule_statuses)

            # Generate dates within the current FY, up to today.
            start_date = fy_start + timedelta(
                days=random.randint(0, day_span)
            )

            schedule_name = f"Demo 5S Schedule {index + 1:03d}"

            # Reuse schedule by stable name to avoid duplicates on rerun.
            schedule = FiveSSchedule.objects.filter(
                schedule_name=schedule_name,
                template=template,
            ).first()

            if schedule is None:
                schedule = FiveSSchedule.objects.create(
                    schedule_name=schedule_name,
                    template=template,
                    start_date=start_date,
                    frequency=random.choice(frequencies),
                    end_date=(
                        today if schedule_status == "ENDED" else None
                    ),
                    enable_auto_schedule=(index % 2 == 0),
                    status=schedule_status,
                    created_by=inspector,
                )

            schedule.status = schedule_status
            schedule.end_date = (
                today if schedule_status == "ENDED" else None
            )
            schedule.enable_auto_schedule = (index % 2 == 0)
            schedule.save()

            # Assign existing plant and user.
            schedule.plant.set([plant])
            schedule.assignee.set([assignee])

            # -----------------------------------------------------
            # Create or reuse an audit cycle.
            # -----------------------------------------------------
            audit_date = fy_start + timedelta(
                days=random.randint(0, day_span)
            )

            due_date = min(
                audit_date + timedelta(days=random.randint(1, 7)),
                today,
            )

            audit_status = random.choice(audit_statuses)

            cycle_key = f"DEMO5S-{today.year}-{index + 1:05d}"

            audit, created = FiveSAudit.objects.get_or_create(
                cycle_key=cycle_key,
                defaults={
                    "schedule": schedule,
                    "template_version": template.version,
                    "user": inspector,
                    "scheduled_date": audit_date,
                    "due_date": due_date,
                    "status": audit_status,
                    "started_at": (
                        timezone.make_aware(
                            datetime.combine(audit_date, time(9))
                        )
                        if audit_status != "SCHEDULED"
                        else None
                    ),
                    "submitted_at": (
                        timezone.make_aware(
                            datetime.combine(audit_date, time(16))
                        )
                        if audit_status in (
                            "SUBMITTED",
                            "REVIEWED",
                            "CLOSED",
                        )
                        else None
                    ),
                    "submitted_by": (
                        inspector
                        if audit_status in (
                            "SUBMITTED",
                            "REVIEWED",
                            "CLOSED",
                        )
                        else None
                    ),
                },
            )

            if created:
                new_audits += 1
            else:
                # Reuse existing audit instead of creating a duplicate.
                audit.schedule = schedule
                audit.template_version = template.version
                audit.user = inspector
                audit.scheduled_date = audit_date
                audit.due_date = due_date
                audit.status = audit_status
                audit.save()

            scores = []

            # -----------------------------------------------------
            # Create answers for each checklist question.
            # -----------------------------------------------------
            for mapping in mappings:
                question = mapping.question

                rating = random.choices(
                    ["1", "2", "3", "4", "5", "NA"],
                    weights=[8, 12, 25, 25, 20, 10],
                    k=1,
                )[0]

                remarks = ""
                evidence = None

                if rating in ("1", "2"):
                    remarks = random.choice([
                        "Finding observed during the 5S walk-through.",
                        "The area does not meet the defined 5S standard.",
                        "Corrective action is required to restore the standard.",
                    ])

                    evidence = ContentFile(
                        png,
                        name=(
                            f"demo5s_{index + 1}_"
                            f"{question.question_code}.png"
                        ),
                    )

                answer, answer_created = AuditAnswer.objects.get_or_create(
                    audit=audit,
                    question=question,
                    defaults={
                        "answer": rating,
                        "remarks": remarks,
                        "evidence": evidence,
                    },
                )

                if answer_created:
                    new_answers += 1

                # On rerun, use the saved answer and preserve existing data.
                actual_answer = answer.answer

                if actual_answer in ("1", "2", "3", "4", "5"):
                    scores.append(int(actual_answer))

                # -------------------------------------------------
                # Create corrective action for Poor/Fair answers.
                # -------------------------------------------------
                if actual_answer in ("1", "2"):
                    action_status = random.choice(action_statuses)

                    action_due = min(
                        audit_date + timedelta(days=random.randint(3, 15)),
                        today,
                    )

                    action, action_created = CorrectiveAction.objects.get_or_create(
                        audit=audit,
                        question=question,
                        defaults={
                            "assigned_to": assignee,
                            "verifier": verifier,
                            "due_date": action_due,
                            "remarks": (
                                "Correct the 5S finding and restore the required "
                                "standard. Submit completion evidence for verification."
                            ),
                            "status": action_status,
                            "created_by": inspector,
                        },
                    )

                    if action_created:
                        new_actions += 1

                    if action.status in ("SUBMITTED", "CLOSED"):
                        action.completion_date = min(action_due, today)
                        action.completion_remarks = (
                            "The required housekeeping correction is completed."
                        )

                    if action.status == "CLOSED":
                        action.approval_remarks = (
                            "Verified. Corrective action approved and closed."
                        )
                        action.approved_by = verifier
                        action.approved_at = timezone.now()

                    action.save()

            # Calculate audit score, excluding N/A answers.
            if scores:
                score = Decimal(
                    str(
                        round(
                            sum(scores) / (len(scores) * 5) * 100,
                            2,
                        )
                    )
                )

                audit.overall_score = score
                audit.save(update_fields=["overall_score"])

        self.stdout.write(
            self.style.SUCCESS("5S demo data created successfully.")
        )
        self.stdout.write(
            f"Active questions: {FiveSQuestion.objects.filter(is_active=True).count()}"
        )
        self.stdout.write(
            f"Template: {template.template_code} v{template.version}"
        )
        self.stdout.write(
            f"Template mappings: {template.template_questions.count()}"
        )
        self.stdout.write(f"Schedules processed: {count}")
        self.stdout.write(f"New audits: {new_audits}")
        self.stdout.write(f"New answers: {new_answers}")
        self.stdout.write(f"New corrective actions: {new_actions}")