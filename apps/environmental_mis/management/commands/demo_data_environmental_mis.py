# ============================================================
## run to generate data:
## python manage.py demo_data_environmental_mis
## Or explicitly for related to employees available:
## python manage.py demo_data_environmental_mis --count 13 --records 100
# ============================================================
# ============================================================
# Environmental Mis Demo Data Seeder
# Creates realistic demo data using existing users and
# existing organization assignments.
# ============================================================



from decimal import Decimal
from datetime import date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.apps import apps
from django.utils import timezone


class Command(BaseCommand):
    """
    Create realistic Environmental MIS demo data for the current financial year.

    Usage:
        python manage.py demo_data_environmental_mis
        python manage.py demo_data_environmental_mis --count 100

    Existing Plant records are reused. No fake organization records are created.
    The command is safe to rerun because demo rows use stable DEMO row names.
    """

    help = "Create current financial year demo data for Environmental MIS."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of Waste Report, Environment Entry and Safety Indicator demo rows to create (default: 100).",
        )

    def get_model(self, model_name):
        """Find a model by class name without depending on the app label."""
        matches = [
            model for model in apps.get_models()
            if model.__name__.lower() == model_name.lower()
        ]
        if not matches:
            raise CommandError(
                f"Could not find model '{model_name}'. "
                "Make sure the Environmental MIS app is installed."
            )
        return matches[0]

    def current_fy(self):
        today = timezone.localdate()
        start_year = today.year if today.month >= 4 else today.year - 1
        return start_year, today

    def active_month_numbers(self, today):
        """
        Return months belonging to the current FY up to today.

        FY 2026-27 currently contains Apr-Sep 2026, so Oct-Mar remain zero.
        """
        fy_months = list(range(4, 13)) + list(range(1, 4))
        return [month for month in fy_months if (
            date(today.year, month, 1) <= today
            if month >= 4
            else date(today.year + 1, month, 1) <= today
        )]

    def monthly_values(self, index, base, today):
        """Create varied monthly quantities/costs only for elapsed FY months."""
        values = {month: Decimal("0.00") for month in range(1, 13)}
        months = self.active_month_numbers(today)

        for position, month in enumerate(months):
            variation = Decimal(1 + ((index + position) % 5) * 0.08)
            values[month] = (Decimal(str(base)) * variation).quantize(
                Decimal("0.01")
            )

        return values

    def set_month_fields(self, obj, prefix, values):
        for month, value in values.items():
            setattr(
                obj,
                f"{prefix}{self.month_name(month)}",
                value,
            )

    def month_name(self, month):
        return [
            "",
            "jan_", "feb_", "mar_", "apr_", "may_", "jun_",
            "jul_", "aug_", "sep_", "oct_", "nov_", "dec_",
        ][month][:-1]

    def set_decimal_month_fields(self, obj, prefix, values):
        names = {
            1: "jan", 2: "feb", 3: "mar", 4: "apr",
            5: "may", 6: "jun", 7: "jul", 8: "aug",
            9: "sep", 10: "oct", 11: "nov", 12: "dec",
        }
        for month, value in values.items():
            setattr(obj, f"{names[month]}_{prefix}", value)

    def fy_quarters(self, values):
        """
        Calculate FY quarters:
        Q1 = Apr-Jun
        Q2 = Jul-Sep
        Q3 = Oct-Dec
        Q4 = Jan-Mar
        """
        return {
            "q1": sum((values[m] for m in (4, 5, 6)), Decimal("0.00")),
            "q2": sum((values[m] for m in (7, 8, 9)), Decimal("0.00")),
            "q3": sum((values[m] for m in (10, 11, 12)), Decimal("0.00")),
            "q4": sum((values[m] for m in (1, 2, 3)), Decimal("0.00")),
        }

    def set_quarter_fields(self, obj, values, cost_values=None):
        quarters = self.fy_quarters(values)

        obj.q1_quantity = quarters["q1"]
        obj.q2_quantity = quarters["q2"]
        obj.q3_quantity = quarters["q3"]
        obj.q4_quantity = quarters["q4"]

        if cost_values is not None:
            cost_quarters = self.fy_quarters(cost_values)
            obj.q1_cost = cost_quarters["q1"]
            obj.q2_cost = cost_quarters["q2"]
            obj.q3_cost = cost_quarters["q3"]
            obj.q4_cost = cost_quarters["q4"]

    def handle(self, *args, **options):
        count = options["count"]

        if count < 1:
            raise CommandError("--count must be at least 1.")

        WasteReportData = self.get_model("WasteReportData")
        WasteSummary = self.get_model("WasteSummary")
        EnvironmentEntry = self.get_model("EnvironmentEntry")
        SafetyIndicatorEntry = self.get_model("SafetyIndicatorEntry")
        Plant = self.get_model("Plant")

        plants = list(Plant.objects.all().order_by("id"))

        if not plants:
            raise CommandError(
                "No Plant records found. Create organization master data first."
            )

        fy_year, today = self.current_fy()
        fy_label = f"{fy_year}-{str(fy_year + 1)[-2:]}"

        self.stdout.write(
            f"Environmental MIS demo data: FY {fy_label} "
            f"(01-Apr-{fy_year} to {today.strftime('%d-%b-%Y')})"
        )
        self.stdout.write(
            f"Using {len(plants)} existing plants."
        )

        waste_rows = [
            ("Used Oil", "WST-USED-OIL", "R"),
            ("Metal Scrap", "WST-METAL", "R"),
            ("Plastic Waste", "WST-PLASTIC", "R"),
            ("Paper and Cardboard", "WST-PAPER", "R"),
            ("Hazardous Process Waste", "WST-HAZ-PROC", "D"),
            ("Chemical Sludge", "WST-SLUDGE", "D"),
            ("General Solid Waste", "WST-GENERAL", "D"),
            ("E-Waste", "WST-EWASTE", "R"),
            ("Wood Waste", "WST-WOOD", "R"),
            ("Packaging Waste", "WST-PACK", "R"),
        ]

        environment_rows = [
            "Water Consumption",
            "Fresh Water Consumption",
            "Process Water",
            "Domestic Water",
            "Energy Consumption",
            "Natural Gas Consumption",
            "Diesel Consumption",
            "LPG Consumption",
            "Production Volume",
            "Environmental Incidents",
        ]

        safety_rows = [
            "Safety Training Hours",
            "Safety Inspections",
            "Safety Observations",
            "Near Miss Reports",
            "Emergency Drills",
            "Toolbox Talks",
            "Safety Audits",
            "PPE Compliance",
            "Corrective Actions Closed",
            "Hazard Reports",
        ]

        with transaction.atomic():
            # ============================================================
            # WASTE REPORT DATA
            # ============================================================
            waste_created = 0

            for index in range(count):
                plant = plants[index % len(plants)]
                row_index = index % len(waste_rows)
                row_name, part_code, treatment = waste_rows[row_index]

                # Add a stable demo suffix so the model's unique constraint
                # (plant, year, report_type, row_name) remains valid.
                demo_row_name = f"{row_name} - DEMO-{index + 1:03d}"

                report_type = (
                    "MANUFACTURING"
                    if index % 2 == 0
                    else "NON_MANUFACTURING"
                )

                quantity = self.monthly_values(
                    index,
                    20 + (index % 15) * 4,
                    today,
                )

                cost = {
                    month: (value * Decimal(str(18 + (index % 6) * 3))).quantize(
                        Decimal("0.01")
                    )
                    for month, value in quantity.items()
                }

                quarters = self.fy_quarters(quantity)
                cost_quarters = self.fy_quarters(cost)

                obj, _ = WasteReportData.objects.update_or_create(
                    plant=plant,
                    year=fy_year,
                    report_type=report_type,
                    row_name=demo_row_name,
                    defaults={
                        "part_code": f"{part_code}-{index + 1:03d}",
                        "treatment": treatment,
                        "jan_qty": quantity[1],
                        "feb_qty": quantity[2],
                        "mar_qty": quantity[3],
                        "apr_qty": quantity[4],
                        "may_qty": quantity[5],
                        "jun_qty": quantity[6],
                        "jul_qty": quantity[7],
                        "aug_qty": quantity[8],
                        "sep_qty": quantity[9],
                        "oct_qty": quantity[10],
                        "nov_qty": quantity[11],
                        "dec_qty": quantity[12],
                        "jan_cost": cost[1],
                        "feb_cost": cost[2],
                        "mar_cost": cost[3],
                        "apr_cost": cost[4],
                        "may_cost": cost[5],
                        "jun_cost": cost[6],
                        "jul_cost": cost[7],
                        "aug_cost": cost[8],
                        "sep_cost": cost[9],
                        "oct_cost": cost[10],
                        "nov_cost": cost[11],
                        "dec_cost": cost[12],
                        "q1_quantity": quarters["q1"],
                        "q2_quantity": quarters["q2"],
                        "q3_quantity": quarters["q3"],
                        "q4_quantity": quarters["q4"],
                        "q1_cost": cost_quarters["q1"],
                        "q2_cost": cost_quarters["q2"],
                        "q3_cost": cost_quarters["q3"],
                        "q4_cost": cost_quarters["q4"],
                        "total_quantity": sum(quantity.values()),
                        "total_cost": sum(cost.values()),
                    },
                )
                waste_created += 1

            # ============================================================
            # ENVIRONMENT ENTRIES
            # ============================================================
            environment_created = 0

            for index in range(count):
                plant = plants[index % len(plants)]
                row_name = (
                    f"{environment_rows[index % len(environment_rows)]}"
                    f" - DEMO-{index + 1:03d}"
                )

                quantity = self.monthly_values(
                    index,
                    100 + (index % 20) * 15,
                    today,
                )

                quarters = self.fy_quarters(quantity)

                EnvironmentEntry.objects.update_or_create(
                    plant=plant,
                    year=fy_year,
                    report_type=(
                        "MANUFACTURING_ENV"
                        if index % 2 == 0
                        else "NON_MANUFACTURING_ENV"
                    ),
                    row_name=row_name,
                    defaults={
                        "year_2024": float(800 + index * 4),
                        "year_2025": float(900 + index * 5),
                        "jan_qty": float(quantity[1]),
                        "feb_qty": float(quantity[2]),
                        "mar_qty": float(quantity[3]),
                        "apr_qty": float(quantity[4]),
                        "may_qty": float(quantity[5]),
                        "jun_qty": float(quantity[6]),
                        "jul_qty": float(quantity[7]),
                        "aug_qty": float(quantity[8]),
                        "sep_qty": float(quantity[9]),
                        "oct_qty": float(quantity[10]),
                        "nov_qty": float(quantity[11]),
                        "dec_qty": float(quantity[12]),
                        "q1_quantity": float(quarters["q1"]),
                        "q2_quantity": float(quarters["q2"]),
                        "q3_quantity": float(quarters["q3"]),
                        "q4_quantity": float(quarters["q4"]),
                        "total_quantity": float(sum(quantity.values())),
                    },
                )
                environment_created += 1

            # ============================================================
            # SAFETY INDICATOR ENTRIES
            # ============================================================
            safety_created = 0

            for index in range(count):
                plant = plants[index % len(plants)]
                row_name = (
                    f"{safety_rows[index % len(safety_rows)]}"
                    f" - DEMO-{index + 1:03d}"
                )

                quantity = self.monthly_values(
                    index,
                    10 + (index % 12) * 2,
                    today,
                )

                SafetyIndicatorEntry.objects.update_or_create(
                    plant=plant,
                    year=fy_year,
                    report_type=(
                        "LEADING_IND"
                        if index % 2 == 0
                        else "LAGGING_IND"
                    ),
                    row_name=row_name,
                    defaults={
                        "year_2025": float(100 + index * 3),
                        "jan_qty": float(quantity[1]),
                        "feb_qty": float(quantity[2]),
                        "mar_qty": float(quantity[3]),
                        "apr_qty": float(quantity[4]),
                        "may_qty": float(quantity[5]),
                        "jun_qty": float(quantity[6]),
                        "jul_qty": float(quantity[7]),
                        "aug_qty": float(quantity[8]),
                        "sep_qty": float(quantity[9]),
                        "oct_qty": float(quantity[10]),
                        "nov_qty": float(quantity[11]),
                        "dec_qty": float(quantity[12]),
                        "total_quantity": float(sum(quantity.values())),
                    },
                )
                safety_created += 1

            # ============================================================
            # WASTE SUMMARIES
            # ============================================================
            # WasteSummary has a unique constraint on
            # plant + year + report_type + summary_type, so summaries are
            # maintained once per plant/report type/summary type.
            summary_types = [
                "NON_HAZ",
                "HAZ_PROCESS",
                "E_WASTE",
                "GRAND_WASTE",
                "PRODUCTION",
                "NON_HAZ_UNIT",
                "PROC_HAZ_UNIT",
                "NON_PROC_HAZ",
                "DIVERSION_RATE",
            ]

            summary_created = 0

            for plant_index, plant in enumerate(plants):
                for report_type in [
                    "MANUFACTURING",
                    "NON_MANUFACTURING",
                ]:
                    for summary_index, summary_type in enumerate(summary_types):
                        base = Decimal(
                            str(
                                500
                                + plant_index * 100
                                + summary_index * 75
                            )
                        )

                        quantity = self.monthly_values(
                            plant_index + summary_index,
                            base,
                            today,
                        )

                        cost = {
                            month: (
                                value * Decimal("12.50")
                            ).quantize(Decimal("0.01"))
                            for month, value in quantity.items()
                        }

                        quarters = self.fy_quarters(quantity)
                        cost_quarters = self.fy_quarters(cost)

                        WasteSummary.objects.update_or_create(
                            plant=plant,
                            year=fy_year,
                            report_type=report_type,
                            summary_type=summary_type,
                            defaults={
                                "jan_qty": quantity[1],
                                "feb_qty": quantity[2],
                                "mar_qty": quantity[3],
                                "apr_qty": quantity[4],
                                "may_qty": quantity[5],
                                "jun_qty": quantity[6],
                                "jul_qty": quantity[7],
                                "aug_qty": quantity[8],
                                "sep_qty": quantity[9],
                                "oct_qty": quantity[10],
                                "nov_qty": quantity[11],
                                "dec_qty": quantity[12],
                                "jan_cost": cost[1],
                                "feb_cost": cost[2],
                                "mar_cost": cost[3],
                                "apr_cost": cost[4],
                                "may_cost": cost[5],
                                "jun_cost": cost[6],
                                "jul_cost": cost[7],
                                "aug_cost": cost[8],
                                "sep_cost": cost[9],
                                "oct_cost": cost[10],
                                "nov_cost": cost[11],
                                "dec_cost": cost[12],
                                "q1_quantity": quarters["q1"],
                                "q2_quantity": quarters["q2"],
                                "q3_quantity": quarters["q3"],
                                "q4_quantity": quarters["q4"],
                                "q1_cost": cost_quarters["q1"],
                                "q2_cost": cost_quarters["q2"],
                                "q3_cost": cost_quarters["q3"],
                                "q4_cost": cost_quarters["q4"],
                                "total_quantity": sum(quantity.values()),
                                "total_cost": sum(cost.values()),
                            },
                        )
                        summary_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Environmental MIS demo data completed successfully."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Waste report rows: {waste_created}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Environment entry rows: {environment_created}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Safety indicator rows: {safety_created}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Waste summaries maintained: {summary_created}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Financial year: FY {fy_label} | Data through {today}"
            )
        )
