"""
Create demo data for the Kaizen Improvement Management module.

Run:
    python manage.py demo_data_kaizen
    python manage.py demo_data_kaizen --count 100

This command:
- Reuses existing active users, plants, and departments.
- Does not create fake users or organization records.
- Creates Kaizen categories and improvement ideas.
- Creates workflow records according to Kaizen status.
- Uses dates from the current financial year through today.
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Plant, Department

from apps.kaizen.models import (
    KaizenCategory,
    Kaizen,
    KaizenInitialReview,
    KaizenTechnicalEvaluation,
    KaizenApproval,
    KaizenImplementation,
    KaizenVerification,
    KaizenClosure,
    KaizenHistory,
)


# ---------------------------------------------------------
# Kaizen categories
# ---------------------------------------------------------
CATEGORY_DATA = [
    (
        "Safety Improvement",
        "SAFETY",
        "Improvements to workplace safety and accident prevention.",
    ),
    (
        "Health Improvement",
        "HEALTH",
        "Improvements to employee health and occupational hygiene.",
    ),
    (
        "Environmental Improvement",
        "ENVIRONMENT",
        "Improvements to environmental performance and waste reduction.",
    ),
    (
        "Quality Improvement",
        "QUALITY",
        "Improvements to product and process quality.",
    ),
    (
        "Productivity Improvement",
        "PRODUCTIVITY",
        "Improvements to operational productivity and efficiency.",
    ),
    (
        "Cost Reduction",
        "COST",
        "Improvements that reduce operational or maintenance costs.",
    ),
    (
        "Ergonomics Improvement",
        "ERGONOMICS",
        "Improvements to workplace ergonomics and employee comfort.",
    ),
    (
        "Compliance Improvement",
        "COMPLIANCE",
        "Improvements to legal and regulatory compliance.",
    ),
]


# ---------------------------------------------------------
# Realistic Kaizen improvement ideas
# ---------------------------------------------------------
KAIZEN_IDEAS = [
    {
        "title": "Improve Emergency Exit Accessibility",
        "problem": "Emergency exits are partially blocked by temporary materials.",
        "solution": "Create marked no-storage zones and introduce daily exit checks.",
        "benefits": "Improved emergency evacuation and reduced safety risk.",
        "type": "SAFETY",
        "priority": "HIGH",
        "cost": 15000,
    },
    {
        "title": "Reduce Compressed Air Leakage",
        "problem": "Compressed air leakage is increasing energy consumption.",
        "solution": "Conduct a leakage survey and repair identified leak points.",
        "benefits": "Reduced energy consumption and maintenance costs.",
        "type": "COST",
        "priority": "MEDIUM",
        "cost": 25000,
    },
    {
        "title": "Improve Chemical Storage Identification",
        "problem": "Chemical containers are not consistently identified.",
        "solution": "Introduce standard labels and a chemical storage identification system.",
        "benefits": "Improved chemical safety and compliance.",
        "type": "COMPLIANCE",
        "priority": "HIGH",
        "cost": 12000,
    },
    {
        "title": "Reduce Paper Usage in Inspection",
        "problem": "Inspection teams use printed checklists for routine inspections.",
        "solution": "Introduce digital inspection forms using the EHS application.",
        "benefits": "Reduced paper consumption and faster reporting.",
        "type": "ENVIRONMENT",
        "priority": "MEDIUM",
        "cost": 30000,
    },
    {
        "title": "Improve Machine Guarding",
        "problem": "Existing machine guards require improvement for safer operation.",
        "solution": "Redesign and install suitable machine guards.",
        "benefits": "Reduced exposure to moving machine parts.",
        "type": "SAFETY",
        "priority": "CRITICAL",
        "cost": 50000,
    },
    {
        "title": "Improve Waste Segregation",
        "problem": "Different waste types are being mixed in common waste bins.",
        "solution": "Install colour-coded bins with clear waste segregation labels.",
        "benefits": "Improved recycling and waste management.",
        "type": "ENVIRONMENT",
        "priority": "MEDIUM",
        "cost": 18000,
    },
    {
        "title": "Reduce Material Handling Distance",
        "problem": "Operators travel long distances to collect frequently used materials.",
        "solution": "Reorganize material storage closer to the production workstation.",
        "benefits": "Improved productivity and reduced physical effort.",
        "type": "PRODUCTIVITY",
        "priority": "MEDIUM",
        "cost": 22000,
    },
    {
        "title": "Improve Workstation Ergonomics",
        "problem": "Operators experience discomfort due to repetitive bending.",
        "solution": "Adjust workstation height and introduce ergonomic fixtures.",
        "benefits": "Reduced ergonomic risk and improved employee comfort.",
        "type": "ERGONOMICS",
        "priority": "HIGH",
        "cost": 35000,
    },
    {
        "title": "Improve First Aid Kit Monitoring",
        "problem": "First aid kit contents are not checked consistently.",
        "solution": "Introduce a monthly digital first aid kit checklist.",
        "benefits": "Improved emergency preparedness.",
        "type": "HEALTH",
        "priority": "MEDIUM",
        "cost": 5000,
    },
    {
        "title": "Reduce Production Changeover Time",
        "problem": "Production changeovers take longer due to unorganized tools.",
        "solution": "Introduce a standardized changeover tool arrangement.",
        "benefits": "Reduced downtime and improved productivity.",
        "type": "PRODUCTIVITY",
        "priority": "HIGH",
        "cost": 20000,
    },
    {
        "title": "Improve Fire Extinguisher Identification",
        "problem": "Fire extinguisher locations are not clearly visible.",
        "solution": "Install visible identification boards and floor markings.",
        "benefits": "Improved emergency response.",
        "type": "SAFETY",
        "priority": "HIGH",
        "cost": 8000,
    },
    {
        "title": "Reduce Water Consumption",
        "problem": "Water consumption is high in the cleaning area.",
        "solution": "Install controlled-flow nozzles and monitor water usage.",
        "benefits": "Reduced water consumption and operating costs.",
        "type": "ENVIRONMENT",
        "priority": "MEDIUM",
        "cost": 16000,
    },
]


STATUS_LIST = [
    "DRAFT",
    "SUBMITTED",
    "UNDER_INITIAL_REVIEW",
    "UNDER_TECHNICAL_EVALUATION",
    "PENDING_APPROVAL",
    "APPROVED_FOR_IMPLEMENTATION",
    "IN_PROGRESS",
    "ON_HOLD",
    "PENDING_VERIFICATION",
    "PENDING_CLOSURE",
    "CLOSED",
    "RETURNED_FOR_CLARIFICATION",
    "RETURNED_FOR_REVISION",
    "REJECTED",
    "DUPLICATE",
    "VERIFICATION_FAILED",
]

PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

BENEFIT_TYPES = [
    "SAFETY",
    "HEALTH",
    "ENVIRONMENT",
    "QUALITY",
    "PRODUCTIVITY",
    "COST",
    "ERGONOMICS",
    "COMPLIANCE",
    "OTHER",
]


class Command(BaseCommand):
    help = "Create demo data for the Kaizen module."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of Kaizen records to create (default: 100).",
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

        # Reuse existing active users and organization records.
        users = list(
            User.objects.filter(is_active=True).order_by("pk")
        )

        plants = list(
            Plant.objects.filter(is_active=True).order_by("pk")
        )

        departments = list(
            Department.objects.filter(is_active=True).order_by("pk")
        )

        if not users:
            raise CommandError(
                "No active users found. Please add users first."
            )

        if not plants:
            raise CommandError(
                "No active plants found. Please add plants first."
            )

        self.stdout.write(
            f"Creating Kaizen demo data from {fy_start} to {today}..."
        )

        self.stdout.write(
            f"Using {len(users)} active users, "
            f"{len(plants)} active plants, "
            f"and {len(departments)} active departments."
        )

        # -----------------------------------------------------
        # 1. Create or reuse Kaizen categories.
        # Search by unique name first to avoid duplicate errors.
        # -----------------------------------------------------
        category_map = {}

        for name, code, description in CATEGORY_DATA:
            category = KaizenCategory.objects.filter(
                name=name
            ).first()

            if category is None:
                category = KaizenCategory.objects.filter(
                    code=code
                ).first()

            if category is None:
                category = KaizenCategory.objects.create(
                    name=name,
                    code=code,
                    description=description,
                    is_active=True,
                    created_by=users[0],
                )
            else:
                # Reuse existing category and activate it.
                update_fields = []

                if not category.is_active:
                    category.is_active = True
                    update_fields.append("is_active")

                if not category.description:
                    category.description = description
                    update_fields.append("description")

                if update_fields:
                    category.save(update_fields=update_fields)

            category_map[code] = category

        # -----------------------------------------------------
        # 2. Create Kaizen records and workflow records.
        # -----------------------------------------------------
        created_kaizens = 0
        created_reviews = 0
        created_evaluations = 0
        created_approvals = 0
        created_implementations = 0
        created_verifications = 0
        created_closures = 0
        created_histories = 0

        for index in range(count):
            submitter = users[index % len(users)]
            reviewer = users[(index + 1) % len(users)]
            evaluator = users[(index + 2) % len(users)]
            approver = users[(index + 3) % len(users)]
            owner = users[(index + 4) % len(users)]

            plant = plants[index % len(plants)]

            department = (
                departments[index % len(departments)]
                if departments
                else None
            )

            idea = KAIZEN_IDEAS[index % len(KAIZEN_IDEAS)]

            category = category_map.get(idea["type"])

            if category is None:
                category = random.choice(
                    list(category_map.values())
                )

            status = STATUS_LIST[index % len(STATUS_LIST)]

            # Create date within current FY.
            submission_date = fy_start + timedelta(
                days=random.randint(0, day_span)
            )

            submission_datetime = timezone.make_aware(
                datetime.combine(
                    submission_date,
                    datetime.min.time(),
                )
            )

            # -------------------------------------------------
            # Create the main Kaizen idea.
            # -------------------------------------------------
            kaizen, created = Kaizen.objects.get_or_create(
                title=f"{idea['title']} - Demo {index + 1:03d}",
                defaults={
                    "description": (
                        f"Demo Kaizen improvement proposal for "
                        f"{plant.name}. This improvement is intended "
                        f"to improve workplace performance."
                    ),
                    "category": category,
                    "submitted_by": submitter,
                    "submission_date": submission_datetime,
                    "plant": plant,
                    "department": department,
                    "location": f"{plant.name} - Production Area",
                    "additional_location_details": (
                        "Demo location for Kaizen improvement."
                    ),
                    "problem_statement": idea["problem"],
                    "proposed_solution": idea["solution"],
                    "expected_benefits": idea["benefits"],
                    "benefit_type": idea["type"],
                    "priority": idea["priority"],
                    "estimated_cost": Decimal(
                        str(idea["cost"])
                    ),
                    "has_related_record": False,
                    "status": status,
                    "current_stage": status,
                    "assigned_to": owner,
                    "created_by": submitter,
                },
            )

            if created:
                created_kaizens += 1

            # Keep existing records unchanged on rerun.
            # Workflow data is created only when missing.

            # -------------------------------------------------
            # Initial review
            # -------------------------------------------------
            review_statuses = [
                "UNDER_INITIAL_REVIEW",
                "UNDER_TECHNICAL_EVALUATION",
                "PENDING_APPROVAL",
                "APPROVED_FOR_IMPLEMENTATION",
                "IN_PROGRESS",
                "ON_HOLD",
                "PENDING_VERIFICATION",
                "PENDING_CLOSURE",
                "CLOSED",
                "RETURNED_FOR_CLARIFICATION",
                "RETURNED_FOR_REVISION",
                "REJECTED",
                "DUPLICATE",
                "VERIFICATION_FAILED",
            ]

            if status in review_statuses:
                review_decision = "ACCEPTED"

                if status == "RETURNED_FOR_CLARIFICATION":
                    review_decision = "CLARIFICATION"

                elif status == "DUPLICATE":
                    review_decision = "DUPLICATE"

                elif status == "REJECTED":
                    review_decision = "REJECTED"

                review, review_created = (
                    KaizenInitialReview.objects.get_or_create(
                        kaizen=kaizen,
                        defaults={
                            "reviewed_by": reviewer,
                            "review_date": submission_datetime,
                            "decision": review_decision,
                            "review_comments": (
                                "Demo initial review completed. "
                                "The proposal has been reviewed."
                            ),
                            "clarification_required": (
                                "Please provide additional details."
                                if review_decision == "CLARIFICATION"
                                else ""
                            ),
                        },
                    )
                )

                if review_created:
                    created_reviews += 1

            # -------------------------------------------------
            # Technical evaluation
            # -------------------------------------------------
            technical_statuses = [
                "UNDER_TECHNICAL_EVALUATION",
                "PENDING_APPROVAL",
                "APPROVED_FOR_IMPLEMENTATION",
                "IN_PROGRESS",
                "ON_HOLD",
                "PENDING_VERIFICATION",
                "PENDING_CLOSURE",
                "CLOSED",
                "VERIFICATION_FAILED",
            ]

            if status in technical_statuses:
                evaluation, evaluation_created = (
                    KaizenTechnicalEvaluation.objects.get_or_create(
                        kaizen=kaizen,
                        defaults={
                            "evaluated_by": evaluator,
                            "evaluation_date": submission_datetime,
                            "decision": "RECOMMEND_APPROVAL",
                            "feasibility": "FEASIBLE",
                            "technical_comments": (
                                "The proposed improvement is technically "
                                "feasible for the demo scenario."
                            ),
                            "safety_impact": (
                                "Expected to improve workplace safety."
                            ),
                            "operational_impact": (
                                "Expected to improve operational efficiency."
                            ),
                            "resource_requirements": (
                                "Existing manpower and suitable materials."
                            ),
                            "estimated_implementation_cost": Decimal(
                                str(idea["cost"])
                            ),
                            "estimated_completion_date": min(
                                today + timedelta(days=15),
                                today,
                            ),
                            "recommendation": (
                                "Recommended for approval and implementation."
                            ),
                        },
                    )
                )

                if evaluation_created:
                    created_evaluations += 1

            # -------------------------------------------------
            # Approval
            # -------------------------------------------------
            approval_statuses = [
                "APPROVED_FOR_IMPLEMENTATION",
                "IN_PROGRESS",
                "ON_HOLD",
                "PENDING_VERIFICATION",
                "PENDING_CLOSURE",
                "CLOSED",
                "VERIFICATION_FAILED",
            ]

            if status in approval_statuses:
                approval_decision = "APPROVED"

                if status == "VERIFICATION_FAILED":
                    approval_decision = "REVISION"

                approval, approval_created = (
                    KaizenApproval.objects.get_or_create(
                        kaizen=kaizen,
                        defaults={
                            "approved_by": approver,
                            "approval_date": submission_datetime,
                            "decision": approval_decision,
                            "approval_comments": (
                                "Demo approval record created."
                            ),
                        },
                    )
                )

                if approval_created:
                    created_approvals += 1

            # -------------------------------------------------
            # Implementation
            # -------------------------------------------------
            implementation_statuses = [
                "IN_PROGRESS",
                "ON_HOLD",
                "PENDING_VERIFICATION",
                "PENDING_CLOSURE",
                "CLOSED",
                "VERIFICATION_FAILED",
            ]

            if status in implementation_statuses:
                impl_status = "IN_PROGRESS"

                if status == "ON_HOLD":
                    impl_status = "ON_HOLD"

                elif status in (
                    "PENDING_VERIFICATION",
                    "PENDING_CLOSURE",
                    "CLOSED",
                    "VERIFICATION_FAILED",
                ):
                    impl_status = "COMPLETED"

                implementation, implementation_created = (
                    KaizenImplementation.objects.get_or_create(
                        kaizen=kaizen,
                        defaults={
                            "implementation_owner": owner,
                            "implementation_status": impl_status,
                            "planned_start_date": submission_date,
                            "planned_end_date": today,
                            "actual_start_date": submission_date,
                            "actual_end_date": (
                                today
                                if impl_status == "COMPLETED"
                                else None
                            ),
                            "implementation_actions": (
                                idea["solution"]
                            ),
                            "resources_used": (
                                "Existing manpower, tools, and materials."
                            ),
                            "actual_cost": Decimal(
                                str(idea["cost"])
                            ),
                            "implementation_remarks": (
                                "Demo implementation record."
                            ),
                            "completed_at": (
                                timezone.now()
                                if impl_status == "COMPLETED"
                                else None
                            ),
                        },
                    )
                )

                if implementation_created:
                    created_implementations += 1

            # -------------------------------------------------
            # Verification
            # -------------------------------------------------
            verification_statuses = [
                "PENDING_CLOSURE",
                "CLOSED",
                "VERIFICATION_FAILED",
            ]

            if status in verification_statuses:
                verification_result = "SUCCESSFUL"

                if status == "VERIFICATION_FAILED":
                    verification_result = "FAILED"

                verification, verification_created = (
                    KaizenVerification.objects.get_or_create(
                        kaizen=kaizen,
                        defaults={
                            "verified_by": reviewer,
                            "verification_date": submission_datetime,
                            "result": verification_result,
                            "rework_required": (
                                True
                                if verification_result == "FAILED"
                                else False
                            ),
                            "verification_method": (
                                "Physical verification and review of "
                                "implementation evidence."
                            ),
                            "before_improvement": idea["problem"],
                            "after_improvement": idea["solution"],
                            "actual_benefits": idea["benefits"],
                            "evidence_details": (
                                "Demo verification evidence recorded."
                            ),
                            "verification_comments": (
                                "Demo verification completed."
                            ),
                        },
                    )
                )

                if verification_created:
                    created_verifications += 1

            # -------------------------------------------------
            # Closure
            # Only create closure after successful verification.
            # -------------------------------------------------
            if status == "CLOSED":
                closure, closure_created = (
                    KaizenClosure.objects.get_or_create(
                        kaizen=kaizen,
                        defaults={
                            "final_outcome": (
                                "The improvement was implemented "
                                "and verified successfully."
                            ),
                            "actual_benefits": idea["benefits"],
                            "actual_implementation_cost": Decimal(
                                str(idea["cost"])
                            ),
                            "lessons_learned": (
                                "Standardize the improvement and "
                                "share it with similar work areas."
                            ),
                            "closure_comments": (
                                "Demo Kaizen closed after verification."
                            ),
                            "closed_by": approver,
                            "closure_date": submission_datetime,
                        },
                    )
                )

                if closure_created:
                    created_closures += 1

            # -------------------------------------------------
            # Workflow history
            # -------------------------------------------------
            history, history_created = (
                KaizenHistory.objects.get_or_create(
                    kaizen=kaizen,
                    new_status=status,
                    defaults={
                        "previous_status": "DRAFT",
                        "action": "DEMO_STATUS_UPDATE",
                        "comments": (
                            f"Demo workflow status set to {status}."
                        ),
                        "changed_by": submitter,
                    },
                )
            )

            if history_created:
                created_histories += 1

        # -----------------------------------------------------
        # Final summary
        # -----------------------------------------------------
        self.stdout.write(
            self.style.SUCCESS(
                "Kaizen demo data created successfully."
            )
        )

        self.stdout.write(
            f"Kaizen categories: {KaizenCategory.objects.count()}"
        )
        self.stdout.write(
            f"Kaizen records created: {created_kaizens}"
        )
        self.stdout.write(
            f"Initial reviews created: {created_reviews}"
        )
        self.stdout.write(
            f"Technical evaluations created: {created_evaluations}"
        )
        self.stdout.write(
            f"Approvals created: {created_approvals}"
        )
        self.stdout.write(
            f"Implementations created: {created_implementations}"
        )
        self.stdout.write(
            f"Verifications created: {created_verifications}"
        )
        self.stdout.write(
            f"Closures created: {created_closures}"
        )
        self.stdout.write(
            f"History records created: {created_histories}"
        )