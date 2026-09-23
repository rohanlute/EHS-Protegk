# ============================================================
## run to generate data:
## python manage.py demo_data_hira
## Or explicitly for related to employees available:
## python manage.py demo_data_hira --count 13 --records 100
# ============================================================
# ============================================================
# HIRA Demo Data Seeder
# Creates realistic demo data using existing users and
# existing organization assignments.
# ============================================================

import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.organizations.models import Department, Plant

from apps.hira.models import (
    HIRAModule,
    RiskMatrix,
    RiskMatrixLevel,
    HazardRiskMaster,
    HIRA,
    HIRAHazard,
    HIRAAction,
)


class Command(BaseCommand):
    help = "Create HIRA demo data for the current financial year using existing users and organization records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of HIRA assessments to create (default: 100).",
        )

    def handle(self, *args, **options):
        count = options["count"]
        if count <= 0:
            raise CommandError("--count must be greater than 0.")

        today = timezone.localdate()
        fy_start = datetime.date(today.year if today.month >= 4 else today.year - 1, 4, 1)

        User = get_user_model()
        users = list(User.objects.filter(is_active=True).order_by("pk"))
        plants = list(Plant.objects.filter(is_active=True).order_by("pk"))
        departments = list(Department.objects.filter(is_active=True).order_by("pk"))

        if not users:
            raise CommandError("No active users found. Create users before running HIRA demo data.")
        if not plants:
            raise CommandError("No active plants found. Create plants before running HIRA demo data.")
        if not departments:
            raise CommandError("No active departments found. Create departments before running HIRA demo data.")

        with transaction.atomic():
            modules = self._get_modules(users)
            risk_matrix = self._get_risk_matrix(users[0])
            self._get_risk_levels(risk_matrix)
            master_rules = self._get_hazard_risk_masters(modules, users[0])

            created_assessments = []
            hazard_count = 0
            action_count = 0

            activities = [
                ("Material Handling", "Manual lifting of material", "Ergonomic"),
                ("Machine Operation", "Contact with moving machine parts", "Mechanical"),
                ("Electrical Maintenance", "Electrical shock during maintenance", "Electrical"),
                ("Chemical Handling", "Exposure to hazardous chemical", "Chemical"),
                ("Hot Work", "Fire or explosion during hot work", "Fire / Explosion"),
                ("Work at Height", "Fall from elevated work area", "Physical"),
                ("Forklift Movement", "Vehicle-pedestrian interaction", "Vehicle"),
                ("Cleaning Activity", "Slip and fall on wet surface", "Physical"),
                ("Welding", "Welding fumes and radiation exposure", "Chemical"),
                ("Confined Space", "Oxygen deficiency or hazardous atmosphere", "Physical"),
            ]

            assessment_types = ["ROUTINE", "NON_ROUTINE", "NEW_PROCESS", "REVIEW", "INCIDENT_REVIEW"]
            hira_statuses = ["DRAFT", "SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED"]
            action_statuses = ["OPEN", "IN_PROGRESS", "COMPLETED", "OVERDUE", "VERIFIED", "CLOSED"]

            for index in range(count):
                plant = plants[index % len(plants)]
                department = departments[index % len(departments)]
                prepared_by = users[index % len(users)]
                reviewed_by = users[(index + 1) % len(users)]
                approved_by = users[(index + 2) % len(users)]

                assessment_date = self._fy_date(fy_start, today, index)

                module = modules[index % len(modules)]
                status = hira_statuses[index % len(hira_statuses)]

                review_date = assessment_date + datetime.timedelta(days=1) if status in {"UNDER_REVIEW", "APPROVED", "REJECTED"} else None
                approval_date = assessment_date + datetime.timedelta(days=2) if status == "APPROVED" else None

                hira = HIRA.objects.create(
                    plant=plant,
                    department=department,
                    module=module,
                    process=activities[index % len(activities)][0],
                    assessment_date=assessment_date,
                    assessment_type=assessment_types[index % len(assessment_types)],
                    prepared_by=prepared_by,
                    reviewed_by=reviewed_by if status in {"UNDER_REVIEW", "APPROVED", "REJECTED"} else None,
                    approved_by=approved_by if status == "APPROVED" else None,
                    review_date=review_date,
                    approval_date=approval_date,
                    revision_number=(index % 3),
                    revision_description="Demo HIRA revision for current financial year.",
                    status=status,
                    remarks="Demo HIRA assessment created for testing and dashboard validation.",
                    created_by=prepared_by,
                )
                created_assessments.append(hira)

                # Create two hazards per assessment so the HIRA has realistic risk coverage.
                for hazard_offset in range(2):
                    activity, hazard_text, category = activities[(index + hazard_offset) % len(activities)]
                    master = next(
                        (
                            rule for rule in master_rules
                            if rule.hazard_category == category
                        ),
                        master_rules[(index + hazard_offset) % len(master_rules)],
                    )

                    likelihood = ((index + hazard_offset) % 5) + 1
                    severity = ((index * 2 + hazard_offset) % 5) + 1
                    action_required = (index + hazard_offset) % 3 != 0

                    target_date = today - datetime.timedelta(days=(index % 20) + 1) if index % 5 == 4 else today + datetime.timedelta(days=(index % 30) + 1)
                    residual_likelihood = max(1, likelihood - 1)
                    residual_severity = max(1, severity - 1)

                    hazard = HIRAHazard.objects.create(
                        hira=hira,
                        master_rule=master,
                        activity=activity,
                        hazard=hazard_text,
                        hazard_category=category,
                        unsafe_act="Improper operating or handling practice." if index % 2 == 0 else "",
                        unsafe_condition="Inadequate guarding, housekeeping or access control." if index % 3 == 0 else "",
                        potential_consequence="Injury, occupational exposure, property damage or operational interruption.",
                        persons_exposed=f"{department.name} employees and contractors",
                        existing_controls=master.existing_controls,
                        control_hierarchy="Engineering Control, Administrative Control, PPE",
                        likelihood=likelihood,
                        severity=severity,
                        additional_controls=(
                            "Improve engineering controls, reinforce SOP requirements and conduct toolbox training."
                            if action_required else ""
                        ),
                        additional_control_hierarchy="Engineering Control, Administrative Control, PPE" if action_required else "",
                        action_required=action_required,
                        responsible_person=users[(index + hazard_offset + 3) % len(users)] if action_required else None,
                        target_date=target_date if action_required else None,
                        residual_likelihood=residual_likelihood if action_required else None,
                        residual_severity=residual_severity if action_required else None,
                        evidence_remarks="Demo evidence/remarks for HIRA risk treatment.",
                    )
                    hazard_count += 1

                    # HIRAHazard.save() automatically creates an HIRAAction when
                    # action_required=True and additional_controls are supplied.
                    action = hazard.actions.order_by("-id").first()
                    if action:
                        desired_status = action_statuses[(index + hazard_offset) % len(action_statuses)]
                        completion_date = None
                        verification = ""
                        verified_by = None

                        if desired_status in {"COMPLETED", "VERIFIED", "CLOSED"}:
                            completion_date = min(
                                today,
                                (action.target_date or today) - datetime.timedelta(days=1),
                            )
                        if desired_status in {"VERIFIED", "CLOSED"}:
                            verification = "Demo verification completed by EHS reviewer."
                            verified_by = users[(index + 4) % len(users)]

                        action.status = desired_status
                        action.completion_date = completion_date
                        action.verification = verification
                        action.verified_by = verified_by
                        action.remarks = "Demo HIRA corrective action."
                        action.save()
                        action_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"HIRA demo data created for FY {fy_start} to {today}."
                )
            )
            self.stdout.write(
                f"assessments: {len(created_assessments)} | "
                f"hazards: {hazard_count} | "
                f"actions: {action_count} | "
                f"modules: {len(modules)} | "
                f"risk_matrices: {RiskMatrix.objects.count()} | "
                f"risk_levels: {RiskMatrixLevel.objects.count()} | "
                f"hazard_risk_masters: {len(master_rules)}"
            )
            self.stdout.write(
                f"Reused {len(users)} active users, {len(plants)} plants and {len(departments)} departments. "
                "No users or organization records were created."
            )

    def _get_modules(self, users):
        definitions = [
            ("Production", "production"),
            ("Maintenance", "maintenance"),
            ("Warehouse", "warehouse"),
            ("Material Handling", "material-handling"),
            ("Utilities", "utilities"),
            ("Projects", "projects"),
            ("EHS Operations", "ehs-operations"),
            ("General Workplace", "general-workplace"),
        ]
        modules = []
        for name, code in definitions:
            module = HIRAModule.objects.filter(code=code).first()
            if not module:
                module = HIRAModule.objects.filter(name=name).first()
            if not module:
                module = HIRAModule.objects.create(
                    name=name,
                    code=code,
                    description=f"Demo HIRA module for {name}.",
                    is_active=True,
                )
            modules.append(module)
        return modules

    def _get_risk_matrix(self, user):
        matrix = RiskMatrix.objects.filter(name="5x5 HIRA Risk Matrix").first()
        if not matrix:
            matrix = RiskMatrix.objects.create(
                name="5x5 HIRA Risk Matrix",
                description="Standard 5x5 likelihood and severity risk matrix for HIRA demo data.",
                min_likelihood=1,
                max_likelihood=5,
                min_severity=1,
                max_severity=5,
                is_active=True,
                created_by=user,
            )
        return matrix

    def _get_risk_levels(self, matrix):
        levels = [
            (1, 4, "Low", 1),
            (5, 9, "Medium", 2),
            (10, 16, "High", 3),
            (17, 25, "Critical", 4),
        ]
        for min_score, max_score, risk_level, display_order in levels:
            RiskMatrixLevel.objects.get_or_create(
                risk_matrix=matrix,
                min_score=min_score,
                max_score=max_score,
                defaults={
                    "risk_level": risk_level,
                    "display_order": display_order,
                    "description": f"{risk_level} risk range for demo 5x5 matrix.",
                    "is_active": True,
                },
            )

    def _get_hazard_risk_masters(self, modules, user):
        definitions = [
            ("Material Handling", "Manual lifting of material", "Ergonomic", "Musculoskeletal injury", 3, 3),
            ("Machine Operation", "Contact with moving machine parts", "Mechanical", "Crush or amputation injury", 3, 5),
            ("Electrical Maintenance", "Electrical shock during maintenance", "Electrical", "Electric shock or burn", 2, 5),
            ("Chemical Handling", "Exposure to hazardous chemical", "Chemical", "Exposure, burn or poisoning", 3, 4),
            ("Hot Work", "Fire or explosion during hot work", "Fire / Explosion", "Fire, burn or explosion", 2, 5),
            ("Work at Height", "Fall from elevated work area", "Physical", "Serious injury or fatality", 3, 5),
            ("Forklift Movement", "Vehicle-pedestrian interaction", "Vehicle", "Collision or struck-by injury", 3, 4),
            ("Cleaning Activity", "Slip and fall on wet surface", "Physical", "Slip, trip and fall injury", 3, 3),
            ("Welding", "Welding fumes and radiation exposure", "Chemical", "Respiratory or eye exposure", 3, 4),
            ("Confined Space", "Oxygen deficiency or hazardous atmosphere", "Physical", "Asphyxiation or toxic exposure", 2, 5),
        ]
        rules = []
        for index, (activity, hazard, category, consequence, likelihood, severity) in enumerate(definitions):
            module = modules[index % len(modules)]
            rule = HazardRiskMaster.objects.filter(
                module=module,
                activity=activity,
                hazard_category=category,
            ).first()
            if not rule:
                rule = HazardRiskMaster.objects.create(
                    module=module,
                    process=activity,
                    activity=activity,
                    hazard_category=category,
                    hazard=hazard,
                    unsafe_act="Improper work practice.",
                    unsafe_condition="Inadequate control or housekeeping.",
                    consequence=consequence,
                    existing_controls="SOP, training, supervision and PPE.",
                    suggested_additional_controls="Engineering improvement, administrative control and refresher training.",
                    default_likelihood=likelihood,
                    default_severity=severity,
                    is_active=True,
                    created_by=user,
                )
            rules.append(rule)
        return rules

    @staticmethod
    def _fy_date(start, end, index):
        span = (end - start).days
        if span <= 0:
            return start
        return start + datetime.timedelta(days=(index * 7) % (span + 1))
