import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.organizations.models import Plant

from apps.hazop.models import (
    HAZOPStudy,
    HAZOPStudyType,
    HAZOPStudyStatus,
    HAZOPStudyMethodology,
    HAZOPStudyPriority,
    HAZOPProcessType,
    HAZOPNode,
    HAZOPNodeType,
    HAZOPEquipmentType,
    HAZOPWorksheetEntry,
    HAZOPParameter,
    HAZOPGuideWord,
    HAZOPDeviationTemplate,
    HAZOPSeverity,
    HAZOPLikelihood,
    HAZOPCause,
    HAZOPCauseCategory,
    HAZOPConsequence,
    HAZOPConsequenceCategory,
    HAZOPSafeguard,
    HAZOPSafeguardCategory,
    HAZOPRecommendation,
    HAZOPRecommendationCategory,
    HAZOPRiskMatrix,
    HAZOPRiskAssessment,
    HAZOPRiskAssessmentReviewHistory,
    HAZOPAction,
    HAZOPActionHistory,
    HAZOPReviewFrequency,
    HAZOPStudyVersion,
)


class Command(BaseCommand):
    help = "Create demo data for the HAZOP module"

    # Number of demo studies to create
    TOTAL_STUDIES = 100

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE("Starting HAZOP demo data seeding...")
        )

        # Use existing active users and organization data
        User = get_user_model()

        users = list(User.objects.filter(is_active=True))
        plants = list(Plant.objects.all())

        if not users:
            raise CommandError(
                "No active users found. Please create users first."
            )

        if not plants:
            raise CommandError(
                "No plants found. Please create a plant first."
            )

        # Get existing HAZOP configuration masters
        study_types = list(HAZOPStudyType.objects.filter(is_active=True))
        methodologies = list(
            HAZOPStudyMethodology.objects.filter(is_active=True)
        )
        priorities = list(
            HAZOPStudyPriority.objects.filter(is_active=True)
        )
        process_types = list(
            HAZOPProcessType.objects.filter(is_active=True)
        )
        study_statuses = list(
            HAZOPStudyStatus.objects.filter(is_active=True)
        )
        node_types = list(HAZOPNodeType.objects.filter(is_active=True))
        equipment_types = list(
            HAZOPEquipmentType.objects.filter(is_active=True)
        )
        parameters = list(HAZOPParameter.objects.filter(is_active=True))
        guide_words = list(
            HAZOPGuideWord.objects.filter(is_active=True)
        )
        deviation_templates = list(
            HAZOPDeviationTemplate.objects.filter(is_active=True)
        )
        severities = list(
            HAZOPSeverity.objects.filter(is_active=True)
        )
        likelihoods = list(
            HAZOPLikelihood.objects.filter(is_active=True)
        )
        cause_categories = list(
            HAZOPCauseCategory.objects.filter(is_active=True)
        )
        consequence_categories = list(
            HAZOPConsequenceCategory.objects.filter(is_active=True)
        )
        safeguard_categories = list(
            HAZOPSafeguardCategory.objects.filter(is_active=True)
        )
        recommendation_categories = list(
            HAZOPRecommendationCategory.objects.filter(is_active=True)
        )
        review_frequencies = list(
            HAZOPReviewFrequency.objects.filter(is_active=True)
        )

        # Risk matrix must already be configured
        risk_matrix = (
            HAZOPRiskMatrix.objects.filter(
                is_active=True,
                is_default=True,
            ).first()
            or HAZOPRiskMatrix.objects.filter(is_active=True).first()
        )

        # Validate required configuration before creating records
        required_masters = {
            "Study Types": study_types,
            "Methodologies": methodologies,
            "Priorities": priorities,
            "Process Types": process_types,
            "Node Types": node_types,
            "Equipment Types": equipment_types,
            "Parameters": parameters,
            "Guide Words": guide_words,
            "Severities": severities,
            "Likelihoods": likelihoods,
        }

        missing_masters = [
            name for name, records in required_masters.items()
            if not records
        ]

        if missing_masters:
            raise CommandError(
                "Missing HAZOP configuration masters: "
                + ", ".join(missing_masters)
                + ". Run your HAZOP master seeder first."
            )

        if not risk_matrix:
            raise CommandError(
                "No active HAZOP risk matrix found. "
                "Run your risk matrix seeder first."
            )

        # Keep the random demo data consistent across runs
        random.seed(42)

        today = timezone.localdate()

        with transaction.atomic():
            for study_index in range(self.TOTAL_STUDIES):

                # Use existing organization and user records
                plant = random.choice(plants)
                leader = random.choice(users)
                reviewer = random.choice(users)
                approver = random.choice(users)

                # Select existing HAZOP masters
                study_type = random.choice(study_types)
                methodology = random.choice(methodologies)
                priority = random.choice(priorities)
                process_type = random.choice(process_types)
                node_type = random.choice(node_types)
                equipment_type = random.choice(equipment_types)
                review_frequency = (
                    random.choice(review_frequencies)
                    if review_frequencies
                    else None
                )

                study_status = (
                    random.choice(study_statuses)
                    if study_statuses
                    else None
                )

                # Create the main HAZOP study
                planned_start = today - timedelta(
                    days=random.randint(60, 180)
                )
                planned_end = planned_start + timedelta(
                    days=random.randint(10, 30)
                )

                study = HAZOPStudy.objects.create(
                    study_title=(
                        f"Demo HAZOP Study {study_index + 1:03d} "
                        f"- {process_type.name}"
                    ),
                    study_type=study_type,
                    methodology=methodology,
                    process_type=process_type,
                    priority=priority,
                    status=study_status,
                    plant=plant,
                    study_leader=leader,
                    planned_start_date=planned_start,
                    planned_end_date=planned_end,
                    actual_start_date=planned_start,
                    actual_end_date=planned_end,
                    review_frequency=review_frequency,
                    next_review_date=today + timedelta(days=365),
                    study_scope=(
                        "Demo study covering process deviations, "
                        "potential causes, consequences, safeguards "
                        "and recommended risk control measures."
                    ),
                    study_objective=(
                        "Identify process hazards and evaluate "
                        "existing safeguards to reduce operational risk."
                    ),
                    reference_documents="P&ID-Demo-001, Process-SOP-001",
                    remarks="Demo data generated for HAZOP module testing.",
                    created_by=leader,
                    updated_by=leader,
                )

                # Add team members from existing users
                team_members = random.sample(
                    users,
                    min(len(users), random.randint(1, 3)),
                )
                study.team_members.set(team_members)

                # Create two process nodes for each study
                for node_index in range(2):

                    node = HAZOPNode.objects.create(
                        study=study,
                        node_name=(
                            f"{process_type.name} Node "
                            f"{node_index + 1}"
                        ),
                        node_type=node_type,
                        equipment_type=equipment_type,
                        equipment_tag=(
                            f"EQ-{study_index + 1:03d}-"
                            f"{node_index + 1:02d}"
                        ),
                        description=(
                            "Demo process node for HAZOP analysis."
                        ),
                        design_intent=(
                            "Transfer and control process material "
                            "under defined operating conditions."
                        ),
                        operating_conditions=(
                            "Normal operating pressure and temperature."
                        ),
                        drawing_reference="P&ID-DEMO-001",
                        boundary_description=(
                            "From process inlet to process outlet."
                        ),
                        created_by=leader,
                        updated_by=leader,
                    )

                    # Create two worksheet entries per node
                    for entry_index in range(2):

                        parameter = random.choice(parameters)
                        guide_word = random.choice(guide_words)

                        deviation_template = (
                            HAZOPDeviationTemplate.objects.filter(
                                parameter=parameter,
                                guide_word=guide_word,
                                is_active=True,
                            ).first()
                        )

                        initial_severity = random.choice(severities)
                        initial_likelihood = random.choice(likelihoods)

                        residual_severity = random.choice(severities)
                        residual_likelihood = random.choice(likelihoods)

                        entry = HAZOPWorksheetEntry.objects.create(
                            node=node,
                            parameter=parameter,
                            guide_word=guide_word,
                            deviation_template=deviation_template,
                            deviation_description=(
                                f"{guide_word.name} "
                                f"{parameter.name} deviation"
                            ),
                            possible_causes=(
                                "Equipment failure, human error, "
                                "or abnormal operating conditions."
                            ),
                            operating_condition="Normal Operation",
                            initial_severity=initial_severity,
                            initial_likelihood=initial_likelihood,
                            residual_severity=residual_severity,
                            residual_likelihood=residual_likelihood,
                            remarks="Demo worksheet entry.",
                            created_by=leader,
                            updated_by=leader,
                        )

                        # Create possible cause
                        HAZOPCause.objects.create(
                            worksheet_entry=entry,
                            category=(
                                random.choice(cause_categories)
                                if cause_categories
                                else None
                            ),
                            cause_description=(
                                "Failure of process equipment or "
                                "incorrect operating procedure."
                            ),
                            created_by=leader,
                        )

                        # Create potential consequence
                        HAZOPConsequence.objects.create(
                            worksheet_entry=entry,
                            category=(
                                random.choice(consequence_categories)
                                if consequence_categories
                                else None
                            ),
                            consequence_description=(
                                "Potential injury, process disruption, "
                                "equipment damage or environmental impact."
                            ),
                            created_by=leader,
                        )

                        # Create existing safeguard
                        HAZOPSafeguard.objects.create(
                            worksheet_entry=entry,
                            category=(
                                random.choice(safeguard_categories)
                                if safeguard_categories
                                else None
                            ),
                            safeguard_description=(
                                "Existing alarm, inspection, "
                                "operating procedure or safety control."
                            ),
                            created_by=leader,
                        )

                        # Create recommendation
                        recommendation_status = random.choice([
                            "Open",
                            "In Progress",
                            "Completed",
                        ])

                        recommendation = HAZOPRecommendation.objects.create(
                            worksheet_entry=entry,
                            category=(
                                random.choice(
                                    recommendation_categories
                                )
                                if recommendation_categories
                                else None
                            ),
                            recommendation_description=(
                                "Review and improve the existing "
                                "risk control measures for this deviation."
                            ),
                            assigned_to=random.choice(users),
                            target_date=today + timedelta(
                                days=random.randint(15, 90)
                            ),
                            status=recommendation_status,
                            completion_remarks=(
                                "Demo recommendation remarks."
                            ),
                            created_by=leader,
                        )

                        # Create risk assessment for the worksheet entry
                        initial_risk_score = (
                            initial_severity.severity_score
                            * initial_likelihood.likelihood_score
                        )

                        residual_risk_score = (
                            residual_severity.severity_score
                            * residual_likelihood.likelihood_score
                        )

                        assessment_status = random.choice([
                            "DRAFT",
                            "SUBMITTED",
                            "UNDER_REVIEW",
                            "PENDING_APPROVAL",
                            "APPROVED",
                        ])

                        assessment = HAZOPRiskAssessment.objects.create(
                            worksheet_entry=entry,
                            matrix=risk_matrix,
                            hazard_title=(
                                f"{parameter.name} deviation hazard"
                            ),
                            hazard_description=(
                                "Potential process hazard identified "
                                "during HAZOP worksheet analysis."
                            ),
                            potential_consequence=(
                                "Injury, equipment damage, "
                                "environmental release or downtime."
                            ),
                            persons_exposed=(
                                "Operators, maintenance personnel "
                                "and nearby workers."
                            ),
                            existing_controls=(
                                "Operating procedures, alarms "
                                "and routine inspections."
                            ),
                            initial_likelihood=(
                                initial_likelihood.likelihood_score
                            ),
                            initial_severity=(
                                initial_severity.severity_score
                            ),
                            additional_controls=(
                                "Improve preventive maintenance, "
                                "inspection and operating controls."
                            ),
                            control_hierarchy="ENGINEERING",
                            action_required=(
                                initial_risk_score >= 10
                            ),
                            action_responsible=random.choice(users),
                            action_due_date=today + timedelta(
                                days=random.randint(15, 90)
                            ),
                            residual_likelihood=(
                                residual_likelihood.likelihood_score
                            ),
                            residual_severity=(
                                residual_severity.severity_score
                            ),
                            status=assessment_status,
                            assessor=leader,
                            reviewer=reviewer,
                            approver=approver,
                            review_comments=(
                                "Demo risk assessment review comments."
                            ),
                        )

                        # Create workflow history for risk assessment
                        if assessment_status != "DRAFT":
                            HAZOPRiskAssessmentReviewHistory.objects.create(
                                assessment=assessment,
                                action="SUBMITTED",
                                from_status="DRAFT",
                                to_status="SUBMITTED",
                                comments="Demo assessment submitted.",
                                performed_by=leader,
                            )

                        if assessment_status in [
                            "UNDER_REVIEW",
                            "PENDING_APPROVAL",
                            "APPROVED",
                        ]:
                            HAZOPRiskAssessmentReviewHistory.objects.create(
                                assessment=assessment,
                                action="UNDER_REVIEW",
                                from_status="SUBMITTED",
                                to_status="UNDER_REVIEW",
                                comments="Demo assessment review started.",
                                performed_by=reviewer,
                            )

                        if assessment_status == "APPROVED":
                            HAZOPRiskAssessmentReviewHistory.objects.create(
                                assessment=assessment,
                                action="APPROVED",
                                from_status="PENDING_APPROVAL",
                                to_status="APPROVED",
                                comments="Demo assessment approved.",
                                performed_by=approver,
                            )

                        # Create an action for each recommendation
                        action_status = random.choice([
                            "OPEN",
                            "IN_PROGRESS",
                            "SUBMITTED_FOR_VERIFICATION",
                            "VERIFIED",
                        ])

                        action = HAZOPAction.objects.create(
                            recommendation=recommendation,
                            action_description=(
                                "Implement the recommended risk "
                                "control measure and provide evidence."
                            ),
                            assigned_to=random.choice(users),
                            priority=random.choice([
                                "CRITICAL",
                                "HIGH",
                                "MEDIUM",
                                "LOW",
                            ]),
                            due_date=today + timedelta(
                                days=random.randint(15, 90)
                            ),
                            status=action_status,
                            completion_remarks=(
                                "Demo action completion remarks."
                            ),
                            created_by=leader,
                        )

                        # Add action history
                        HAZOPActionHistory.objects.create(
                            action=action,
                            event="CREATED",
                            previous_status="",
                            new_status="OPEN",
                            performed_by=leader,
                            remarks="Demo action created.",
                        )

                        if action_status == "IN_PROGRESS":
                            HAZOPActionHistory.objects.create(
                                action=action,
                                event="STARTED",
                                previous_status="OPEN",
                                new_status="IN_PROGRESS",
                                performed_by=action.assigned_to,
                                remarks="Demo action started.",
                            )

                        elif action_status == "SUBMITTED_FOR_VERIFICATION":
                            HAZOPActionHistory.objects.create(
                                action=action,
                                event="SUBMITTED",
                                previous_status="IN_PROGRESS",
                                new_status="SUBMITTED_FOR_VERIFICATION",
                                performed_by=action.assigned_to,
                                remarks="Demo action submitted for verification.",
                            )

                        elif action_status == "VERIFIED":
                            action.completed_by = action.assigned_to
                            action.completed_at = timezone.now()
                            action.verified_by = reviewer
                            action.verified_at = timezone.now()
                            action.verification_remarks = (
                                "Demo action verified."
                            )
                            action.save()

                            HAZOPActionHistory.objects.create(
                                action=action,
                                event="VERIFIED",
                                previous_status=(
                                    "SUBMITTED_FOR_VERIFICATION"
                                ),
                                new_status="VERIFIED",
                                performed_by=reviewer,
                                remarks="Demo action verified.",
                            )

                # Create version 1 for each study
                HAZOPStudyVersion.objects.create(
                    study=study,
                    version_number=1,
                    version_title="Initial Demo Version",
                    revision_reason="Initial HAZOP study version.",
                    status="DRAFT",
                    snapshot_data={
                        "study_number": study.study_number,
                        "study_title": study.study_title,
                        "plant_id": study.plant_id,
                        "study_type": study.study_type.name,
                        "methodology": study.methodology.name,
                        "process_type": study.process_type.name,
                        "priority": study.priority.name,
                    },
                    change_summary=[
                        "Initial study created",
                        "Demo HAZOP data generated",
                    ],
                    created_by=leader,
                )

                self.stdout.write(
                    f"Created study {study.study_number}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {self.TOTAL_STUDIES} "
                "HAZOP demo studies."
            )
        )