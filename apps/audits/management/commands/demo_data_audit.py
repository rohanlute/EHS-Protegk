# ============================================================
## run to generate data:
## python manage.py demo_data_audit
## Or explicitly for related to employees available:
## python manage.py demo_data_audit --count 13 --records 100
# ============================================================
# ============================================================
# Audit Demo Data Seeder
# Creates realistic demo data using existing users and
# existing organization assignments.
# ============================================================

from datetime import datetime, timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Plant, Zone, Location, SubLocation
from apps.audits.models import (
    AuditCategory,
    AuditTemplate,
    AuditQuestion,
    AuditSchedule,
    AuditResponse,
    AuditFinding,
    CAPA,
)


class Command(BaseCommand):
    help = "Create realistic Audit Management demo data for the current financial year."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of Audit Schedule records to create. Default: 100.",
        )

    def handle(self, *args, **options):
        count = options["count"]

        if count <= 0:
            raise CommandError("Count must be greater than 0.")

        today = timezone.localdate()
        fy_start = datetime(
            today.year if today.month >= 4 else today.year - 1,
            4,
            1,
        ).date()
        fy_end = today
        current_tz = timezone.get_current_timezone()

        # Reuse existing active users. No demo users are created.
        users = list(User.objects.filter(is_active=True).order_by("id"))

        # Reuse existing organization masters. No fake organization records
        # are created by this command.
        plants = list(Plant.objects.all().order_by("id"))
        zones = list(Zone.objects.all().order_by("id"))
        locations = list(Location.objects.all().order_by("id"))
        sublocations = list(SubLocation.objects.all().order_by("id"))

        if not users:
            raise CommandError(
                "No active User records found. Create/import users first."
            )

        if not plants:
            raise CommandError(
                "No Plant records found. Create/import Plant master data first."
            )

        # ------------------------------------------------------------------
        # AUDIT MASTER DATA
        # ------------------------------------------------------------------
        # Reuse existing categories/templates/questions where available.
        # If the Audit master tables are empty, create a small standard set
        # required to demonstrate the complete Audit workflow.
        standard_categories = [
            (
                "EHS Compliance",
                "EHS",
                "Environment, Health and Safety compliance audits.",
            ),
            (
                "Safety Management",
                "SAFETY",
                "Workplace safety and operational control audits.",
            ),
            (
                "Fire & Emergency",
                "FIRE",
                "Fire prevention and emergency preparedness audits.",
            ),
            (
                "Environmental",
                "ENV",
                "Environmental compliance and control audits.",
            ),
            (
                "Contractor Safety",
                "CONTRACTOR",
                "Contractor management and safety audits.",
            ),
        ]

        categories = list(AuditCategory.objects.filter(is_active=True).order_by("id"))

        for name, code, description in standard_categories:
            category = AuditCategory.objects.filter(category_code=code).first()
            if not category:
                category = AuditCategory.objects.create(
                    category_name=name,
                    category_code=code,
                    description=description,
                    is_active=True,
                    created_by=users[0],
                )
            elif not category.is_active:
                category.is_active = True
                category.save(update_fields=["is_active", "updated_at"])

        categories = list(AuditCategory.objects.filter(is_active=True).order_by("id"))

        if not categories:
            raise CommandError(
                "No active AuditCategory records are available."
            )

        standard_templates = [
            (
                "EHS General Compliance Audit",
                "EHS-GEN",
                "EHS",
                "General EHS compliance and workplace condition audit.",
            ),
            (
                "Safety Management System Audit",
                "SMS",
                "SAFETY",
                "Safety management system and operational control audit.",
            ),
            (
                "Fire & Emergency Preparedness Audit",
                "FIRE-ERP",
                "FIRE",
                "Fire protection, emergency preparedness and response audit.",
            ),
            (
                "Environmental Compliance Audit",
                "ENV-COMP",
                "ENV",
                "Environmental aspects, controls and compliance audit.",
            ),
            (
                "Contractor Safety Audit",
                "CON-SAFE",
                "CONTRACTOR",
                "Contractor safety management and site compliance audit.",
            ),
        ]

        templates = list(AuditTemplate.objects.all().order_by("id"))

        for title, version, category_code, reference in standard_templates:
            if not AuditTemplate.objects.filter(
                title=title,
                version=version,
            ).exists():
                category = AuditCategory.objects.filter(
                    category_code=category_code
                ).first() or categories[0]

                AuditTemplate.objects.create(
                    title=title,
                    version=version,
                    category=category,
                    standard_reference=reference,
                )

        templates = list(AuditTemplate.objects.all().order_by("id"))

        if not templates:
            raise CommandError(
                "No AuditTemplate records are available."
            )

        # Create questions only for templates that currently have no questions.
        # Existing customer questions are preserved and reused.
        standard_questions = [
            (
                "Is the work area clean and free from unsafe conditions?",
                "Housekeeping",
                False,
            ),
            (
                "Are required PPE and safety controls available and being used?",
                "PPE Compliance",
                False,
            ),
            (
                "Are emergency arrangements and access routes available?",
                "Emergency Preparedness",
                True,
            ),
            (
                "Are equipment isolation and energy control requirements followed?",
                "Isolation / LOTO",
                False,
            ),
            (
                "Are fire extinguishers and fire protection systems accessible?",
                "Fire Protection",
                True,
            ),
            (
                "Are relevant statutory records and permits available?",
                "Legal / Permit Compliance",
                False,
            ),
            (
                "Are employees and contractors trained for the assigned work?",
                "Training & Competency",
                False,
            ),
            (
                "Are environmental controls implemented for the activity?",
                "Environmental Control",
                True,
            ),
        ]

        for template in templates:
            if not template.questions.exists():
                for sequence, (text, clause, mandatory_photo) in enumerate(
                    standard_questions,
                    start=1,
                ):
                    AuditQuestion.objects.create(
                        template=template,
                        question_text=text,
                        compliance_clause=clause,
                        is_mandatory_photo=mandatory_photo,
                        sequence=sequence,
                    )

        # Refresh templates after creating questions.
        templates = list(AuditTemplate.objects.all().order_by("id"))

        # ------------------------------------------------------------------
        # VALID ORGANIZATION HIERARCHY
        # ------------------------------------------------------------------
        # The AuditSchedule supports multiple plants/zones/locations but also
        # has a primary Location FK. Build valid Location -> Zone -> Plant
        # combinations so the generated schedule always points to real data.
        valid_locations = []

        for location in locations:
            zone = getattr(location, "zone", None)
            plant = getattr(zone, "plant", None) if zone else None

            if zone and plant:
                valid_locations.append((plant, zone, location))

        if not valid_locations:
            raise CommandError(
                "No valid Plant -> Zone -> Location hierarchy found. "
                "Create/import valid organization master data first."
            )

        # ------------------------------------------------------------------
        # STATUS / PRIORITY DISTRIBUTION
        # ------------------------------------------------------------------
        schedule_statuses = [
            AuditSchedule.STATUS_DRAFT,
            AuditSchedule.STATUS_SCHEDULED,
            AuditSchedule.STATUS_IN_PROGRESS,
            AuditSchedule.STATUS_COMPLETED,
            AuditSchedule.STATUS_CLOSED,
            AuditSchedule.STATUS_SCHEDULED,
            AuditSchedule.STATUS_IN_PROGRESS,
            AuditSchedule.STATUS_COMPLETED,
            AuditSchedule.STATUS_CLOSED,
            AuditSchedule.STATUS_DRAFT,
        ]

        priorities = [
            AuditSchedule.PRIORITY_LOW,
            AuditSchedule.PRIORITY_MEDIUM,
            AuditSchedule.PRIORITY_MEDIUM,
            AuditSchedule.PRIORITY_HIGH,
            AuditSchedule.PRIORITY_CRITICAL,
        ]

        response_statuses = [
            AuditResponse.STATUS_PASS,
            AuditResponse.STATUS_PASS,
            AuditResponse.STATUS_PASS,
            AuditResponse.STATUS_FAIL,
            AuditResponse.STATUS_NA,
        ]

        finding_risks = [
            AuditFinding.RISK_MINOR,
            AuditFinding.RISK_MAJOR,
            AuditFinding.RISK_CRITICAL,
        ]

        finding_statuses_for_open_audit = [
            AuditFinding.STATUS_OPEN,
            AuditFinding.STATUS_IN_PROGRESS,
            AuditFinding.STATUS_RESOLVED,
        ]

        capa_statuses = [
            CAPA.STATUS_PENDING,
            CAPA.STATUS_FIXED,
            CAPA.STATUS_VERIFIED,
        ]

        created_schedules = 0
        created_responses = 0
        created_findings = 0
        created_capas = 0

        self.stdout.write(
            self.style.NOTICE(
                f"Audit Management demo data: {fy_start} to {fy_end}"
            )
        )
        self.stdout.write(
            self.style.NOTICE(
                f"Using {len(users)} existing users, {len(plants)} existing plants "
                f"and {len(valid_locations)} valid organization locations."
            )
        )

        fy_days = (fy_end - fy_start).days

        # ------------------------------------------------------------------
        # CREATE AUDIT SCHEDULES
        # ------------------------------------------------------------------
        for index in range(count):
            auditor = users[index % len(users)]
            reviewer = users[(index + 1) % len(users)]

            plant, zone, location = valid_locations[
                index % len(valid_locations)
            ]

            location_sublocations = [
                sub
                for sub in sublocations
                if getattr(sub, "location_id", None) == location.id
            ]
            sublocation = (
                location_sublocations[
                    index % len(location_sublocations)
                ]
                if location_sublocations
                else None
            )

            template = templates[index % len(templates)]

            requested_status = schedule_statuses[index % len(schedule_statuses)]
            priority = priorities[index % len(priorities)]

            # Keep every scheduled audit date inside the requested FY and
            # never generate a future date.
            schedule_offset = (index * 3) % (fy_days + 1)
            scheduled_date = fy_start + timedelta(days=schedule_offset)

            # Save first as DRAFT because AuditSchedule.save() calls
            # full_clean(), while completed/closed validation depends on
            # responses/findings being created first.
            schedule = AuditSchedule(
                template=template,
                auditor=auditor,
                location=location,
                scheduled_date=scheduled_date,
                priority=priority,
                status=AuditSchedule.STATUS_DRAFT,
            )

            schedule.full_clean()
            schedule.save()

            # Many-to-many organization scope.
            schedule.plants.add(plant)
            schedule.zones.add(zone)
            schedule.locations.add(location)

            if sublocation:
                schedule.sublocations.add(sublocation)

            # Use the primary location field as well as the M2M scope.
            schedule.location = location

            questions = list(
                template.questions.all().order_by("sequence", "id")
            )

            if not questions:
                # This should not happen after the master creation above,
                # but fail clearly if a customer configuration is incomplete.
                raise CommandError(
                    f"No questions found for AuditTemplate '{template}'."
                )

            # --------------------------------------------------------------
            # RESPONSES
            # --------------------------------------------------------------
            failed_questions = []

            for question_index, question in enumerate(questions):
                response_status = response_statuses[
                    (index + question_index) % len(response_statuses)
                ]

                # Keep some audits fully compliant so they can be closed
                # without creating unnecessary findings.
                if requested_status in (
                    AuditSchedule.STATUS_CLOSED,
                    AuditSchedule.STATUS_COMPLETED,
                ):
                    # A controlled mix: closed/completed audits mostly pass,
                    # with selected failures for realistic findings.
                    if (index + question_index) % 7 not in (0, 1):
                        response_status = AuditResponse.STATUS_PASS

                comment_map = {
                    AuditResponse.STATUS_PASS: (
                        "Requirement verified during audit; control was found effective."
                    ),
                    AuditResponse.STATUS_FAIL: (
                        "Observation identified during audit; corrective action is required."
                    ),
                    AuditResponse.STATUS_NA: (
                        "Requirement was not applicable to the audited activity."
                    ),
                }

                response = AuditResponse.objects.create(
                    schedule=schedule,
                    question=question,
                    status=response_status,
                    comment=comment_map[response_status],
                )

                created_responses += 1

                if response_status == AuditResponse.STATUS_FAIL:
                    failed_questions.append(question)

            # --------------------------------------------------------------
            # FINDINGS + CAPA
            # --------------------------------------------------------------
            # The AuditFinding model has a unique constraint on
            # (parent_audit, origin_question). Deduplicate failed questions
            # before creating findings so the command is safe even if the
            # question collection contains duplicate references.
            unique_failed_questions = []
            seen_question_ids = set()

            for failed_question in failed_questions:
                if failed_question.id not in seen_question_ids:
                    seen_question_ids.add(failed_question.id)
                    unique_failed_questions.append(failed_question)

            for finding_index, question in enumerate(unique_failed_questions):
                # Keep the number of findings controlled while still giving
                # the Audit module realistic non-conformity data.
                if finding_index > 1:
                    break

                # Protect against an existing finding for this audit/question
                # pair if the command is interrupted and continued.
                existing_finding = AuditFinding.objects.filter(
                    parent_audit=schedule,
                    origin_question=question,
                ).first()

                if existing_finding:
                    continue

                is_closed_audit = requested_status == AuditSchedule.STATUS_CLOSED

                if is_closed_audit:
                    finding_status = (
                        AuditFinding.STATUS_CLOSED
                        if finding_index % 2
                        else AuditFinding.STATUS_RESOLVED
                    )
                    review_status = AuditFinding.REVIEW_APPROVED
                else:
                    finding_status = finding_statuses_for_open_audit[
                        (index + finding_index) % len(
                            finding_statuses_for_open_audit
                        )
                    ]
                    review_status = [
                        AuditFinding.REVIEW_PENDING,
                        AuditFinding.REVIEW_APPROVED,
                        AuditFinding.REVIEW_REJECTED,
                    ][(index + finding_index) % 3]

                reviewed_by = (
                    reviewer
                    if review_status != AuditFinding.REVIEW_PENDING
                    else None
                )

                finding = AuditFinding(
                    parent_audit=schedule,
                    origin_question=question,
                    observation_detail=(
                        "Audit observation: required control was not fully "
                        "implemented at the time of inspection. Immediate "
                        "corrective action and follow-up verification are required."
                    ),
                    risk_score=finding_risks[
                        (index + finding_index) % len(finding_risks)
                    ],
                    status=finding_status,
                    manager_review_status=review_status,
                    manager_review_comment=(
                        "Finding reviewed by management."
                        if review_status == AuditFinding.REVIEW_APPROVED
                        else (
                            "Finding requires additional management review."
                            if review_status == AuditFinding.REVIEW_PENDING
                            else "Finding returned for clarification."
                        )
                    ),
                    reviewed_by=reviewed_by,
                    reviewed_at=(
                        timezone.now() - timedelta(hours=(index % 8) + 1)
                        if reviewed_by
                        else None
                    ),
                    is_archived=False,
                )

                finding.save()
                created_findings += 1

                # Every finding gets a CAPA to demonstrate the corrective
                # action workflow.
                capa_status = (
                    CAPA.STATUS_VERIFIED
                    if finding_status in (
                        AuditFinding.STATUS_RESOLVED,
                        AuditFinding.STATUS_CLOSED,
                    )
                    else capa_statuses[
                        (index + finding_index) % len(capa_statuses)
                    ]
                )

                due_offset = max(
                    0,
                    (index * 2 + finding_index * 7) % (fy_days + 1),
                )
                due_date = min(
                    fy_start + timedelta(days=due_offset),
                    fy_end,
                )

                if due_date < fy_start:
                    due_date = fy_start

                verified_by = (
                    reviewer if capa_status == CAPA.STATUS_VERIFIED else None
                )

                verified_at = (
                    timezone.now() - timedelta(days=1)
                    if capa_status == CAPA.STATUS_VERIFIED
                    else None
                )

                capa = CAPA(
                    finding=finding,
                    action_required=(
                        "Implement corrective action, brief responsible personnel, "
                        "verify the control and retain evidence of completion."
                    ),
                    assigned_to=users[
                        (index + finding_index + 2) % len(users)
                    ],
                    due_date=due_date,
                    verification_status=capa_status,
                    fixed_comment=(
                        "Corrective action implemented and evidence verified."
                        if capa_status in (
                            CAPA.STATUS_FIXED,
                            CAPA.STATUS_VERIFIED,
                        )
                        else ""
                    ),
                    verified_by=verified_by,
                    verified_at=verified_at,
                )

                capa.save()
                created_capas += 1

            # --------------------------------------------------------------
            # FINAL AUDIT STATUS
            # --------------------------------------------------------------
            # Mandatory-photo failed responses must have evidence before an
            # audit can become COMPLETED/CLOSED.
            if requested_status in (
                AuditSchedule.STATUS_COMPLETED,
                AuditSchedule.STATUS_CLOSED,
            ):
                mandatory_failures = AuditResponse.objects.filter(
                    schedule=schedule,
                    status=AuditResponse.STATUS_FAIL,
                    question__is_mandatory_photo=True,
                )

                for response in mandatory_failures:
                    response.photo_evidence.save(
                        f"audit_evidence_{schedule.id}_{response.id}.jpg",
                        ContentFile(
                            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01"
                            b"\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
                        ),
                        save=True,
                    )

            # For CLOSED audits every finding must be resolved/closed.
            # This also handles a schedule left behind by an earlier interrupted
            # run of this command that may already contain an open finding.
            if requested_status == AuditSchedule.STATUS_CLOSED:
                AuditFinding.objects.filter(
                    parent_audit=schedule,
                    is_archived=False,
                ).exclude(
                    status__in=(
                        AuditFinding.STATUS_RESOLVED,
                        AuditFinding.STATUS_CLOSED,
                    )
                ).update(
                    status=AuditFinding.STATUS_RESOLVED,
                    manager_review_status=AuditFinding.REVIEW_APPROVED,
                    reviewed_by=reviewer,
                    reviewed_at=timezone.now(),
                    manager_review_comment="Finding resolved for audit closure demo data.",
                )

            schedule.status = requested_status

            if requested_status in (
                AuditSchedule.STATUS_IN_PROGRESS,
                AuditSchedule.STATUS_COMPLETED,
                AuditSchedule.STATUS_CLOSED,
            ):
                schedule.started_at = timezone.make_aware(
                    datetime.combine(
                        scheduled_date,
                        datetime.min.time(),
                    ),
                    current_tz,
                )

                if schedule.started_at > timezone.now():
                    schedule.started_at = timezone.now()

            if requested_status in (
                AuditSchedule.STATUS_COMPLETED,
                AuditSchedule.STATUS_CLOSED,
            ):
                schedule.completed_at = timezone.make_aware(
                    datetime.combine(
                        scheduled_date,
                        datetime.min.time(),
                    ),
                    current_tz,
                )

                if schedule.completed_at > timezone.now():
                    schedule.completed_at = timezone.now()

            schedule.save()
            created_schedules += 1

            if created_schedules % 25 == 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created {created_schedules}/{count} audit schedules..."
                    )
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Audit demo data completed. Schedules created: {created_schedules}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Audit schedules total: {AuditSchedule.objects.count()}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Audit responses total: {AuditResponse.objects.count()}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Audit findings total: {AuditFinding.objects.count()}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"CAPA records total: {CAPA.objects.count()}"
            )
        )
