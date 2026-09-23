# ============================================================
## run to generate data:
## python manage.py demo_data_envdata
## Or explicitly for related to employees available:
## python manage.py demo_data_envdata --count 13 --records 100
# ============================================================
# ============================================================
# ENV Data Demo Data Seeder
# Creates realistic demo data using existing users and
# existing organization assignments.
# ============================================================


from datetime import date, timedelta
import random

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = "Create current-FY demo data for the Environmental Data module."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of monthly environmental transaction records to create (default: 100).",
        )

    def _get_model(self, model_name):
        for model in apps.get_models():
            if model.__name__ == model_name:
                return model
        raise CommandError(f"Could not find model: {model_name}")

    def _current_fy(self):
        today = timezone.localdate()
        fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
        return fy_start, today

    def _elapsed_months(self, fy_start, today):
        months = []
        cursor = fy_start
        while cursor <= today:
            months.append(cursor)
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)
        return months

    def _month_code(self, value):
        return value.strftime("%b").upper()

    def _demo_pdf(self, title, plant_name, indicator, month, value, unit):
        text = (
            "Environmental Demo Attachment\n\n"
            f"Title: {title}\n"
            f"Plant: {plant_name}\n"
            f"Indicator: {indicator}\n"
            f"Month: {month}\n"
            f"Value: {value} {unit}\n"
            "This document is generated for EHS-360 demo/testing data."
        )
        return ContentFile(text.encode("utf-8"), name=f"env_demo_{plant_name}_{month.lower()}.txt")

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        if count <= 0:
            raise CommandError("--count must be greater than 0.")

        Plant = self._get_model("Plant")
        User = self._get_model("User")
        UnitCategory = self._get_model("UnitCategory")
        Unit = self._get_model("Unit")
        EnvironmentalQuestion = self._get_model("EnvironmentalQuestion")
        MonthlyIndicatorData = self._get_model("MonthlyIndicatorData")
        MonthlyIndicatorAttachment = self._get_model("MonthlyIndicatorAttachment")

        fy_start, today = self._current_fy()
        elapsed_months = self._elapsed_months(fy_start, today)

        users = list(User.objects.filter(is_active=True).order_by("id"))
        plants = list(Plant.objects.all().order_by("id"))

        if not users:
            raise CommandError("No active users found. Create users first.")
        if not plants:
            raise CommandError("No plants found. Create organization/plant data first.")

        creator = users[0]

        # Reuse existing unit categories/units where available; create only missing demo masters.
        category_defaults = [
            ("Energy", "Energy consumption units"),
            ("Volume", "Volume measurement units"),
            ("Weight", "Weight measurement units"),
            ("Water", "Water consumption units"),
        ]

        categories = {}
        for name, description in category_defaults:
            category, _ = UnitCategory.objects.get_or_create(
                name=name,
                defaults={
                    "description": description,
                    "is_active": True,
                    "created_at": timezone.now(),
                    "created_by": creator,
                },
            )
            categories[name] = category

        unit_defaults = [
            ("Energy", "kWh", "kWh", 1.0),
            ("Volume", "L", "L", 1.0),
            ("Weight", "kg", "kg", 1.0),
            ("Water", "m3", "m3", 1.0),
        ]

        units = {}
        for category_name, name, base_unit, conversion_rate in unit_defaults:
            unit, _ = Unit.objects.get_or_create(
                category=categories[category_name],
                name=name,
                defaults={
                    "base_unit": base_unit,
                    "conversion_rate": conversion_rate,
                    "is_active": True,
                    "created_by": creator,
                },
            )
            units[name] = unit

        question_defaults = [
            ("Electricity Consumption", "MANUAL", "electricity", "CONSUMPTION", "Energy", "kWh"),
            ("Diesel Consumption", "MANUAL", "fuel", "DIESEL", "Volume", "L"),
            ("Petrol Consumption", "MANUAL", "fuel", "PETROL", "Volume", "L"),
            ("LPG Consumption", "MANUAL", "fuel", "LPG", "Weight", "kg"),
            ("Water Consumption", "MANUAL", "water", "CONSUMPTION", "Water", "m3"),
            ("Hazardous Waste Generated", "MANUAL", "waste_type", "HAZARDOUS", "Weight", "kg"),
            ("Non-Hazardous Waste Generated", "MANUAL", "waste_type", "NON_HAZARDOUS", "Weight", "kg"),
            ("E-Waste Generated", "MANUAL", "waste_type", "E_WASTE", "Weight", "kg"),
            ("Paper Waste Generated", "MANUAL", "waste_type", "PAPER", "Weight", "kg"),
            ("Wastewater Generated", "MANUAL", "waste_type", "WASTEWATER", "Volume", "m3"),
            ("Scope 1 Fuel Consumption", "MANUAL", "scope", "SCOPE_1", "Volume", "L"),
            ("Scope 2 Electricity Consumption", "MANUAL", "scope", "SCOPE_2", "Energy", "kWh"),
            ("Renewable Energy Consumption", "MANUAL", "energy_type", "RENEWABLE", "Energy", "kWh"),
            ("Recycled Waste Quantity", "MANUAL", "waste_status", "RECYCLED", "Weight", "kg"),
            ("Water Recycled", "MANUAL", "water_type", "RECYCLED", "Water", "m3"),
            ("Environmental Incident Count", "INCIDENT", "incident_type", "ENVIRONMENTAL", None, None),
            ("Environmental Hazard Count", "HAZARD", "hazard_type", "ENVIRONMENTAL", None, None),
            ("Fire Inspection Environmental Findings", "INSPECTION", "inspection_type", "FIRE", None, None),
            ("Manual Environmental Observation", "MANUAL", None, None, None, None),
            ("Green Energy Percentage", "MANUAL", "energy_type", "GREEN", None, None),
        ]

        questions = []
        for index, item in enumerate(question_defaults, start=1):
            text, source_type, filter_field, filter_value, category_name, unit_name = item
            question = (
                EnvironmentalQuestion.objects.filter(question_text=text).first()
            )
            if not question:
                question = EnvironmentalQuestion.objects.create(
                    question_text=text,
                    source_type=source_type,
                    filter_field=filter_field,
                    filter_value=filter_value,
                    unit_category=categories.get(category_name) if category_name else None,
                    default_unit=units.get(unit_name) if unit_name else None,
                    unit_options=unit_name or "",
                    order=index,
                    is_active=True,
                    is_system=False,
                    created_by=creator,
                )
            else:
                # Reuse existing questions and ensure the demo command can use them.
                if not question.is_active:
                    question.is_active = True
                    question.save(update_fields=["is_active"])
            if unit_name and units.get(unit_name):
                question.selected_units.add(units[unit_name])
            questions.append(question)

        random.seed(20260923)

        values = {
            "Electricity Consumption": (9000, 28000),
            "Diesel Consumption": (500, 3500),
            "Petrol Consumption": (100, 1000),
            "LPG Consumption": (100, 900),
            "Water Consumption": (500, 5000),
            "Hazardous Waste Generated": (20, 500),
            "Non-Hazardous Waste Generated": (100, 1500),
            "E-Waste Generated": (10, 250),
            "Paper Waste Generated": (20, 300),
            "Wastewater Generated": (300, 4000),
            "Scope 1 Fuel Consumption": (500, 3500),
            "Scope 2 Electricity Consumption": (9000, 28000),
            "Renewable Energy Consumption": (1000, 12000),
            "Recycled Waste Quantity": (50, 900),
            "Water Recycled": (100, 2500),
            "Environmental Incident Count": (0, 5),
            "Environmental Hazard Count": (1, 12),
            "Fire Inspection Environmental Findings": (0, 8),
            "Manual Environmental Observation": (0, 10),
            "Green Energy Percentage": (20, 95),
        }

        created_data = 0
        created_attachments = 0

        # The command creates transaction rows only for elapsed months in the current FY.
        # Records are distributed across existing plants/users/questions.
        for index in range(count):
            plant = plants[index % len(plants)]
            question = questions[index % len(questions)]
            month_date = elapsed_months[index % len(elapsed_months)]
            month = self._month_code(month_date)
            user = users[index % len(users)]

            low, high = values[question.question_text]
            if question.question_text in {
                "Environmental Incident Count",
                "Environmental Hazard Count",
                "Fire Inspection Environmental Findings",
                "Manual Environmental Observation",
            }:
                value = str(random.randint(int(low), int(high)))
            elif question.question_text == "Green Energy Percentage":
                value = f"{random.uniform(low, high):.2f}"
            else:
                value = f"{random.uniform(low, high):.2f}"

            unit = question.default_unit

            MonthlyIndicatorData.objects.create(
                plant=plant,
                indicator=question,
                month=month,
                value=value,
                unit=unit,
                created_by=user,
            )
            created_data += 1

            # Add an attachment for roughly every third transaction.
            if index % 3 == 0:
                attachment = MonthlyIndicatorAttachment(
                    plant=plant,
                    indicator=question,
                    month=month,
                    uploaded_by=user,
                )
                attachment.file = self._demo_pdf(
                    "Environmental Monthly Indicator Evidence",
                    plant.name,
                    question.question_text,
                    month,
                    value,
                    unit.name if unit else "",
                )
                try:
                    attachment.full_clean()
                    attachment.save()
                    created_attachments += 1
                except Exception:
                    # The attachment has a unique plant+indicator+month cell.
                    # If that cell already exists, keep the transaction data.
                    pass

        self.stdout.write(self.style.SUCCESS(
            f"Environmental demo data created for FY {fy_start} to {today}."
        ))
        self.stdout.write(
            f"monthly_indicator_data: {created_data} | "
            f"attachments: {created_attachments} | "
            f"questions reused/created: {len(questions)} | "
            f"units reused/created: {len(units)}"
        )
        self.stdout.write(
            f"Reused {len(users)} active users and {len(plants)} plants. "
            "No users or organization records were created."
        )
