# ============================================================
## run to generate data:
## python manage.py demo_data_legal_compliance
## Or explicitly for related to employees available:
## python manage.py demo_data_legal_compliance --count 13 --records 100
# ============================================================
# ============================================================
# Legal Compliance Demo Data Seeder
# Creates realistic demo data using existing users and
# existing organization assignments.
# ============================================================

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.apps import apps
from django.conf import settings
from django.utils import timezone


class Command(BaseCommand):
    """
    Create realistic Legal Compliance demo data for the current financial year.

    Usage:
        python manage.py demo_data_legal_compliance
        python manage.py demo_data_legal_compliance --count 10

    The command:
    - Reuses existing users, plants and departments.
    - Creates missing legal-compliance master records only when required.
    - Creates current-FY compliance transactions with varied statuses.
    - Creates requirements, instances, submissions, responses, findings,
      regulatory notices and notifications.
    """

    help = "Create current financial year demo data for Legal Compliance."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of compliance transaction sets to create (default: 100).",
        )

    def get_model(self, model_name):
        """Find a model by class name without depending on the Django app label."""
        matches = [
            model
            for model in apps.get_models()
            if model.__name__.lower() == model_name.lower()
        ]
        if not matches:
            raise CommandError(
                f"Could not find model '{model_name}'. "
                "Make sure the Legal Compliance app is installed."
            )
        return matches[0]

    def pdf_content(self, title, body):
        """Create a small valid PDF-like demo file for FileField demo data."""
        # A plain text PDF payload is enough for demo storage when no PDF validator
        # is configured on the model fields in the supplied Legal Compliance models.
        content = (
            f"LEGAL COMPLIANCE DEMO DOCUMENT\n"
            f"{title}\n\n"
            f"{body}\n"
        ).encode("utf-8")
        return ContentFile(content, name=f"demo_{title.lower().replace(' ', '_')}.pdf")

    def current_fy(self):
        today = timezone.localdate()
        start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
        return start, today

    def fy_date(self, fy_start, fy_end, offset_days):
        """Return a date inside the current FY."""
        total_days = max((fy_end - fy_start).days, 0)
        return fy_start + timedelta(days=offset_days % (total_days + 1))

    def user_pool(self):
        User = apps.get_model(settings.AUTH_USER_MODEL.split(".")[0], settings.AUTH_USER_MODEL.split(".")[1])
        users = list(User.objects.filter(is_active=True).order_by("id"))
        if not users:
            raise CommandError("No active users found. Please create users first.")
        return users

    def handle(self, *args, **options):
        count = options["count"]
        if count < 1:
            raise CommandError("--count must be at least 1.")

        fy_start, fy_end = self.current_fy()

        LegalAct = self.get_model("LegalAct")
        ComplianceQuestion = self.get_model("ComplianceQuestion")
        ComplianceRequirement = self.get_model("ComplianceRequirement")
        ComplianceRequirementQuestion = self.get_model("ComplianceRequirementQuestion")
        ComplianceSubmission = self.get_model("ComplianceSubmission")
        ComplianceResponse = self.get_model("ComplianceResponse")
        ComplianceFinding = self.get_model("ComplianceFinding")
        RegulatoryNotice = self.get_model("RegulatoryNotice")
        ComplianceInstance = self.get_model("ComplianceInstance")
        ComplianceNotification = self.get_model("ComplianceNotification")

        User = apps.get_model(settings.AUTH_USER_MODEL.split(".")[0], settings.AUTH_USER_MODEL.split(".")[1])
        Plant = self.get_model("Plant")
        Department = self.get_model("Department")

        users = list(User.objects.filter(is_active=True).order_by("id"))
        plants = list(Plant.objects.all().order_by("id"))
        departments = list(Department.objects.all().order_by("id"))

        if not users:
            raise CommandError("No active users found.")
        if not plants:
            raise CommandError("No Plant records found. Create organization master data first.")
        if not departments:
            self.stdout.write(
                self.style.WARNING(
                    "No Department records found. Department relationships will be left empty."
                )
            )

        self.stdout.write(
            f"Legal Compliance demo data: {fy_start} to {fy_end}"
        )
        self.stdout.write(
            f"Using {len(users)} existing users, {len(plants)} existing plants and "
            f"{len(departments)} existing departments."
        )

        with transaction.atomic():
            # ============================================================
            # LEGAL ACT MASTER
            # ============================================================
            act_seed = [
                ("Factories Act / Occupational Safety", "Factories Act", "Factory Inspectorate", "CENTRAL", "FACTORY"),
                ("Environment Protection Act", "EPA", "Ministry / Environment Authority", "CENTRAL", "ENVIRONMENT"),
                ("Hazardous Waste Management Rules", "HW Rules", "Pollution Control Board", "CENTRAL", "ENVIRONMENT"),
                ("Fire Safety / Fire NOC Requirements", "Fire NOC", "Fire Department", "STATE", "FIRE"),
                ("Electrical Safety Regulations", "Electrical Safety", "Electrical Inspectorate", "STATE", "ELECTRICAL"),
                ("Occupational Health Requirements", "Occupational Health", "Labour / Health Authority", "STATE", "HEALTH"),
                ("Chemical Safety Requirements", "Chemical Safety", "Regulatory Authority", "CENTRAL", "CHEMICAL"),
                ("Labour Welfare and Employment Requirements", "Labour Compliance", "Labour Department", "STATE", "LABOUR"),
                ("Water Pollution Control Requirements", "Water Consent", "Pollution Control Board", "STATE", "ENVIRONMENT"),
                ("Air Pollution Control Requirements", "Air Consent", "Pollution Control Board", "STATE", "ENVIRONMENT"),
            ]

            acts = []
            for name, short, authority, level, category in act_seed:
                act = LegalAct.objects.filter(act_name=name).first()
                if not act:
                    act = LegalAct(
                        act_name=name,
                        short_name=short,
                        authority_name=authority,
                        government_level=level,
                        category=category,
                        description=f"Demo regulatory register entry for {name}.",
                        applicability_notes="Applicable based on plant activities, location and regulatory scope.",
                        effective_date=fy_start,
                        is_active=True,
                        created_by=users[0],
                    )
                    act.save()
                acts.append(act)

            # ============================================================
            # COMPLIANCE QUESTION MASTER
            # ============================================================
            question_seed = [
                "Is the required statutory licence / registration valid?",
                "Has the required statutory return been submitted?",
                "Are mandatory inspection records maintained?",
                "Are applicable permits and approvals available?",
                "Are required environmental records maintained?",
                "Are emergency and fire compliance requirements fulfilled?",
                "Are employee health and safety statutory requirements fulfilled?",
                "Are hazardous chemical records maintained as required?",
                "Are statutory registers updated and available?",
                "Has the competent authority requirement been reviewed?",
            ]

            questions = []
            for index, text in enumerate(question_seed):
                act = acts[index % len(acts)]
                question = (
                    ComplianceQuestion.objects
                    .filter(legal_act=act, question_text=text)
                    .first()
                )
                if not question:
                    qtype = "YES_NO"
                    submission_type = "BOTH" if index % 3 == 0 else "CHECKLIST"
                    question = ComplianceQuestion(
                        legal_act=act,
                        question_text=text,
                        question_type=qtype,
                        submission_type=submission_type,
                        is_mandatory=True,
                        is_document_required=(index % 3 == 0),
                        is_critical=(index % 4 == 0),
                        auto_generate_finding=True,
                        reference_standard=f"{act.short_name or act.act_name} - Statutory Requirement",
                        guidance_notes="Verify applicable legal requirement and retain supporting evidence.",
                        is_active=True,
                        created_by=users[index % len(users)],
                    )
                    question.save()

                    if plants:
                        question.applicable_plants.set([plants[index % len(plants)]])
                    if departments:
                        question.applicable_departments.set(
                            [departments[index % len(departments)]]
                        )

                questions.append(question)

            # ============================================================
            # COMPLIANCE REQUIREMENT MASTER
            # ============================================================
            requirement_seed = [
                ("Maintain statutory licence / registration", "YEARLY", "HIGH"),
                ("Submit applicable statutory return", "YEARLY", "CRITICAL"),
                ("Conduct statutory inspection", "QUARTERLY", "HIGH"),
                ("Maintain environmental compliance records", "MONTHLY", "HIGH"),
                ("Review fire and emergency compliance", "HALF_YEARLY", "CRITICAL"),
                ("Complete occupational health compliance review", "YEARLY", "HIGH"),
                ("Review hazardous chemical compliance", "MONTHLY", "CRITICAL"),
                ("Maintain labour statutory registers", "MONTHLY", "MEDIUM"),
                ("Review pollution consent conditions", "QUARTERLY", "HIGH"),
                ("Review electrical statutory compliance", "HALF_YEARLY", "HIGH"),
            ]

            requirements = []
            for index, (title, frequency, criticality) in enumerate(requirement_seed):
                act = acts[index % len(acts)]
                requirement = (
                    ComplianceRequirement.objects
                    .filter(title=title, legal_act=act)
                    .first()
                )
                if not requirement:
                    scheduled = self.fy_date(fy_start, fy_end, index * 17)
                    due = min(scheduled + timedelta(days=30), fy_end)
                    requirement = ComplianceRequirement(
                        title=title,
                        legal_act=act,
                        description=f"Operational compliance obligation for {title.lower()}.",
                        frequency=frequency,
                        criticality=criticality,
                        scheduled_date=scheduled,
                        due_date=due,
                        status="PENDING",
                        evidence_required=True,
                        requires_approval=True,
                        due_days_before=7,
                        next_due_date=due + timedelta(days=365),
                        reminder_days=3,
                        escalation_days=1,
                        is_active=True,
                        created_by=users[index % len(users)],
                    )
                    requirement.save()

                    if plants:
                        requirement.applicable_plants.set([plants[index % len(plants)]])
                    if departments:
                        requirement.applicable_departments.set(
                            [departments[index % len(departments)]]
                        )

                    responsible = users[index % len(users):]
                    responsible = responsible[: min(3, len(responsible))]
                    requirement.responsible_person.set(responsible)

                    reviewers = [users[(index + 1) % len(users)]]
                    requirement.reviewer.set(reviewers)

                # Ensure every seeded requirement has questions.
                mapped_questions = list(
                    requirement.questions.filter(is_active=True)[:5]
                )
                if not mapped_questions:
                    selected = questions[index % len(questions):] + questions[: index % len(questions)]
                    selected = selected[:3]
                    for q_index, question in enumerate(selected):
                        ComplianceRequirementQuestion.objects.get_or_create(
                            compliance_requirement=requirement,
                            question=question,
                            defaults={
                                "is_mandatory": True,
                                "section_name": (
                                    "General Compliance"
                                    if q_index == 0
                                    else "Supporting Evidence"
                                ),
                            },
                        )

                requirements.append(requirement)

            # ============================================================
            # TRANSACTION DATA
            # ============================================================
            instance_statuses = [
                "PENDING", "IN_PROGRESS", "SUBMITTED",
                "COMPLETED", "OVERDUE", "REJECTED"
            ]
            submission_statuses = [
                "DRAFT", "SUBMITTED", "APPROVED", "REJECTED"
            ]
            finding_statuses = [
                "OPEN", "IN_PROGRESS", "OVERDUE", "CLOSED"
            ]
            notice_statuses = [
                "OPEN", "UNDER_REVIEW", "REPLY_SUBMITTED",
                "CLOSED", "ESCALATED"
            ]
            notice_priorities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            notification_types = [
                "COMPLIANCE", "CAPA", "NOTICE", "REMINDER", "ESCALATION"
            ]

            for index in range(count):
                user = users[index % len(users)]
                plant = plants[index % len(plants)]
                department = (
                    departments[index % len(departments)]
                    if departments else None
                )
                requirement = requirements[index % len(requirements)]

                # Dates remain inside the current financial year.
                scheduled = self.fy_date(fy_start, fy_end, index * 7)
                due = min(scheduled + timedelta(days=15 + (index % 25)), fy_end)

                instance_status = instance_statuses[index % len(instance_statuses)]
                completed_at = None
                if instance_status == "COMPLETED":
                    completed_at = timezone.make_aware(
                        datetime.combine(
                            min(due, fy_end),
                            time(16, 0),
                        )
                    )

                instance = ComplianceInstance.objects.create(
                    requirement=requirement,
                    scheduled_date=scheduled,
                    due_date=due,
                    status=instance_status,
                    completed_at=completed_at,
                )

                # --------------------------------------------------------
                # Submission
                # --------------------------------------------------------
                submission_status = submission_statuses[index % len(submission_statuses)]
                submitted_at = None
                reviewed_at = None
                reviewed_by = None

                if submission_status in ["SUBMITTED", "APPROVED", "REJECTED"]:
                    submitted_at = timezone.make_aware(
                        datetime.combine(
                            min(scheduled + timedelta(days=3), fy_end),
                            time(11, 0),
                        )
                    )

                if submission_status in ["APPROVED", "REJECTED"]:
                    reviewed_at = timezone.make_aware(
                        datetime.combine(
                            min(scheduled + timedelta(days=5), fy_end),
                            time(15, 0),
                        )
                    )
                    reviewed_by = users[(index + 1) % len(users)]

                submission = ComplianceSubmission.objects.create(
                    requirement=requirement,
                    submitted_by=user,
                    status=submission_status,
                    remarks=(
                        "Demo compliance submission with supporting statutory evidence."
                    ),
                    reviewer_comments=(
                        "Reviewed against the applicable compliance requirement."
                        if reviewed_by else None
                    ),
                    reviewed_by=reviewed_by,
                    submitted_at=submitted_at,
                    reviewed_at=reviewed_at,
                )

                # --------------------------------------------------------
                # Responses - unique submission/question
                # --------------------------------------------------------
                mapped_questions = list(
                    requirement.questions.filter(is_active=True)[:5]
                )
                if not mapped_questions:
                    mapped_questions = questions[index % len(questions):][:3]

                for q_index, question in enumerate(mapped_questions):
                    # Every fourth response is non-compliant to generate
                    # realistic findings; other responses vary between YES/NA.
                    if (index + q_index) % 4 == 0:
                        answer = "NO"
                    elif (index + q_index) % 7 == 0:
                        answer = "NA"
                    else:
                        answer = "YES"

                    evidence = None
                    if (
                        question.is_document_required
                        and answer == "YES"
                    ):
                        evidence = self.pdf_content(
                            "Compliance Evidence",
                            f"Requirement: {requirement.title}\n"
                            f"Question: {question.question_text}\n"
                            f"Plant: {plant}\n"
                            f"Financial Year: {fy_start.year}-{fy_end.year}",
                        )

                    response = ComplianceResponse(
                        submission=submission,
                        question=question,
                        answer=answer,
                        remarks=(
                            "Requirement verified."
                            if answer == "YES"
                            else "Supporting evidence / corrective action required."
                        ),
                        evidence_file=evidence,
                    )
                    response.save()

                # --------------------------------------------------------
                # Compliance Finding for non-compliant response
                # --------------------------------------------------------
                if index % 3 != 2:
                    finding_status = finding_statuses[index % len(finding_statuses)]
                    target_date = min(
                        due + timedelta(days=10 + (index % 20)),
                        fy_end,
                    )

                    closure_date = (
                        min(target_date, fy_end)
                        if finding_status == "CLOSED"
                        else None
                    )

                    finding = ComplianceFinding(
                        requirement=requirement,
                        submission=submission,
                        finding_description=(
                            "Non-compliance identified during statutory "
                            "compliance verification."
                        ),
                        violated_provision=(
                            f"{requirement.legal_act.short_name or requirement.legal_act.act_name}"
                        ),
                        corrective_action=(
                            "Complete the required compliance action and retain "
                            "documentary evidence."
                        ),
                        responsible_person=users[(index + 2) % len(users)],
                        reviewer=users[(index + 3) % len(users)],
                        target_date=target_date,
                        closure_date=closure_date,
                        status=finding_status,
                        remarks=(
                            "Corrective action tracking generated as demo data."
                        ),
                        created_by=user,
                    )
                    finding.evidence_file = self.pdf_content(
                        "Finding Evidence",
                        "Demo evidence for statutory compliance finding.",
                    )
                    finding.save()

                # --------------------------------------------------------
                # Regulatory Notice
                # --------------------------------------------------------
                if index % 4 == 0:
                    notice_status = notice_statuses[index % len(notice_statuses)]
                    notice_date = self.fy_date(fy_start, fy_end, index * 11)
                    response_due = min(
                        notice_date + timedelta(days=20 + (index % 15)),
                        fy_end,
                    )

                    reply_file = None
                    closure_remarks = None
                    if notice_status in ["REPLY_SUBMITTED", "CLOSED"]:
                        reply_file = self.pdf_content(
                            "Regulatory Reply",
                            "Demo reply submitted to the regulatory authority.",
                        )
                    if notice_status == "CLOSED":
                        closure_remarks = "Regulatory notice closed after response."

                    notice = RegulatoryNotice(
                        legal_act=requirement.legal_act,
                        authority_name=requirement.legal_act.authority_name,
                        notice_title=f"Statutory Compliance Notice - {index + 1:03d}",
                        notice_description=(
                            "Demo regulatory notice created for compliance tracking."
                        ),
                        notice_date=notice_date,
                        response_due_date=response_due,
                        priority=notice_priorities[index % len(notice_priorities)],
                        status=notice_status,
                        plant=plant,
                        department=department,
                        responsible_person=users[(index + 1) % len(users)],
                        reviewer=users[(index + 2) % len(users)],
                        notice_file=self.pdf_content(
                            "Regulatory Notice",
                            "Demo statutory notice document.",
                        ),
                        reply_file=reply_file,
                        closure_remarks=closure_remarks,
                        created_by=user,
                    )
                    notice.save()

                # --------------------------------------------------------
                # Notification
                # --------------------------------------------------------
                ComplianceNotification.objects.create(
                    user=user,
                    notification_type=notification_types[index % len(notification_types)],
                    title=f"Legal Compliance Update - {index + 1:03d}",
                    message=(
                        f"Compliance activity '{requirement.title}' requires "
                        f"attention for {plant}."
                    ),
                    is_read=(index % 3 == 0),
                    redirect_url="/legal-compliance/",
                )

                if (index + 1) % 25 == 0:
                    self.stdout.write(
                        f"Created {index + 1}/{count} compliance transaction sets..."
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Legal Compliance demo data completed successfully. "
                f"Transaction sets created: {count}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Created/reused Legal Acts, Compliance Questions, Requirements, "
                "Instances, Submissions, Responses, Findings, Regulatory Notices "
                "and Notifications using existing organization/user data."
            )
        )
