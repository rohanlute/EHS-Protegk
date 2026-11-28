
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.hazop.models import (
    HAZOPRiskMatrix,
    HAZOPRiskRating,
    HAZOPRiskLevel,
)


class Command(BaseCommand):
    help = "Seed default HAZOP Risk Matrix, Risk Ratings, and Risk Levels"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE("Starting HAZOP Risk Data seeding...")
        )

        matrix = self.seed_risk_matrix()
        self.seed_risk_ratings(matrix)
        self.seed_risk_levels()

        self.stdout.write(
            self.style.SUCCESS(
                "HAZOP Risk Data seeded successfully."
            )
        )

    def seed_risk_matrix(self):
        matrix, created = HAZOPRiskMatrix.objects.update_or_create(
            name="Standard HAZOP 5x5 Risk Matrix",
            defaults={
                "description": (
                    "Standard 5x5 risk matrix used for HAZOP risk "
                    "evaluation. Risk score is calculated by multiplying "
                    "Likelihood by Severity."
                ),
                "likelihood_scale": 5,
                "severity_scale": 5,
                "is_default": True,
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Risk Matrix: {matrix.name}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Updated Risk Matrix: {matrix.name}"
                )
            )

        return matrix

    def seed_risk_ratings(self, matrix):
        likelihood_ratings = [
            {
                "score": 1,
                "name": "Rare",
                "description": (
                    "The event is highly unlikely to occur "
                    "under normal operating conditions."
                ),
            },
            {
                "score": 2,
                "name": "Unlikely",
                "description": (
                    "The event could occur, but is not expected "
                    "during normal operations."
                ),
            },
            {
                "score": 3,
                "name": "Possible",
                "description": (
                    "The event may occur occasionally "
                    "during the activity."
                ),
            },
            {
                "score": 4,
                "name": "Likely",
                "description": (
                    "The event is expected to occur "
                    "in some operating conditions."
                ),
            },
            {
                "score": 5,
                "name": "Almost Certain",
                "description": (
                    "The event is expected to occur frequently "
                    "or repeatedly."
                ),
            },
        ]

        severity_ratings = [
            {
                "score": 1,
                "name": "Insignificant",
                "description": (
                    "No injury or negligible impact. "
                    "Minimal operational disruption."
                ),
            },
            {
                "score": 2,
                "name": "Minor",
                "description": (
                    "Minor injury requiring basic first aid "
                    "or limited operational impact."
                ),
            },
            {
                "score": 3,
                "name": "Moderate",
                "description": (
                    "Medical treatment injury, moderate "
                    "environmental impact, or operational disruption."
                ),
            },
            {
                "score": 4,
                "name": "Major",
                "description": (
                    "Serious injury, major environmental impact, "
                    "or significant operational disruption."
                ),
            },
            {
                "score": 5,
                "name": "Catastrophic",
                "description": (
                    "Fatality, multiple serious injuries, "
                    "or severe environmental or business impact."
                ),
            },
        ]

        for rating in likelihood_ratings:
            obj, created = HAZOPRiskRating.objects.update_or_create(
                matrix=matrix,
                rating_type="LIKELIHOOD",
                score=rating["score"],
                defaults={
                    "name": rating["name"],
                    "description": rating["description"],
                    "is_active": True,
                },
            )

            self.stdout.write(
                f"{'Created' if created else 'Updated'} "
                f"Likelihood: {obj.score} - {obj.name}"
            )

        for rating in severity_ratings:
            obj, created = HAZOPRiskRating.objects.update_or_create(
                matrix=matrix,
                rating_type="SEVERITY",
                score=rating["score"],
                defaults={
                    "name": rating["name"],
                    "description": rating["description"],
                    "is_active": True,
                },
            )

            self.stdout.write(
                f"{'Created' if created else 'Updated'} "
                f"Severity: {obj.score} - {obj.name}"
            )

    def seed_risk_levels(self):
        risk_levels = [
            {
                "name": "Low",
                "minimum_score": 1,
                "maximum_score": 4,
                "color": "#198754",
                "requires_action": False,
            },
            {
                "name": "Medium",
                "minimum_score": 5,
                "maximum_score": 9,
                "color": "#ffc107",
                "requires_action": True,
            },
            {
                "name": "High",
                "minimum_score": 10,
                "maximum_score": 16,
                "color": "#fd7e14",
                "requires_action": True,
            },
            {
                "name": "Critical",
                "minimum_score": 17,
                "maximum_score": 25,
                "color": "#dc3545",
                "requires_action": True,
            },
        ]

        for level in risk_levels:
            obj, created = HAZOPRiskLevel.objects.update_or_create(
                name=level["name"],
                defaults={
                    "minimum_score": level["minimum_score"],
                    "maximum_score": level["maximum_score"],
                    "color": level["color"],
                    "requires_action": level["requires_action"],
                    "is_active": True,
                },
            )

            self.stdout.write(
                f"{'Created' if created else 'Updated'} "
                f"Risk Level: {obj.name} "
                f"({obj.minimum_score}-{obj.maximum_score})"
            )
