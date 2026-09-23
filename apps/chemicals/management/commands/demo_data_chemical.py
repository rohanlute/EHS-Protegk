# ============================================================
## run to generate data:
## python manage.py demo_data_chemical
## Or explicitly for related to employees available:
## python manage.py demo_data_chemical --count 13 --records 100
# ============================================================
# ============================================================
# Chemical Demo Data Seeder
# Creates realistic demo data using existing users and
# existing organization assignments.
# ============================================================

from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Plant, Zone, Location, SubLocation, Department
from apps.chemicals.models import Chemical


class Command(BaseCommand):
    help = "Create realistic Chemical master demo data using existing users and organization records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=25,
            help="Number of Chemical records to create. Default: 25.",
        )

    def handle(self, *args, **options):
        count = options["count"]

        if count <= 0:
            raise CommandError("Count must be greater than 0.")

        # Current financial year: 1 April 2026 onward, up to today.
        today = timezone.localdate()
        fy_start = today.replace(
            year=today.year if today.month >= 4 else today.year - 1,
            month=4,
            day=1,
        )
        fy_end = today

        # Reuse existing active users instead of creating fake users.
        users = list(
            User.objects.filter(is_active=True).order_by("id")
        )

        # Reuse existing plants instead of creating fake organization data.
        plants = list(
            Plant.objects.all().order_by("id")
        )

        if not users:
            raise CommandError(
                "No active User records found. Create/import users first."
            )

        if not plants:
            raise CommandError(
                "No Plant records found. Create/import Plant master data first."
            )

        zones = list(Zone.objects.all().order_by("id"))
        locations = list(Location.objects.all().order_by("id"))
        sublocations = list(SubLocation.objects.all().order_by("id"))
        departments = list(Department.objects.all().order_by("id"))

        # Realistic industrial chemical master data.
        chemical_master = [
            {
                "chemical_name": "Hydrochloric Acid",
                "trade_name": "HCl Industrial Grade",
                "cas_number": "7647-01-0",
                "un_number": "UN1789",
                "supplier": "Merck Life Science",
                "quantity": 250,
                "quantity_unit": "L",
                "storage_location": "Acid Store - Rack A1",
            },
            {
                "chemical_name": "Sulfuric Acid",
                "trade_name": "Sulfuric Acid 98%",
                "cas_number": "7664-93-9",
                "un_number": "UN1830",
                "supplier": "Thermo Fisher Scientific",
                "quantity": 180,
                "quantity_unit": "L",
                "storage_location": "Acid Store - Rack A2",
            },
            {
                "chemical_name": "Sodium Hydroxide",
                "trade_name": "Caustic Soda",
                "cas_number": "1310-73-2",
                "un_number": "UN1823",
                "supplier": "Brenntag India",
                "quantity": 320,
                "quantity_unit": "kg",
                "storage_location": "Alkali Store - Rack B1",
            },
            {
                "chemical_name": "Acetone",
                "trade_name": "Acetone AR Grade",
                "cas_number": "67-64-1",
                "un_number": "UN1090",
                "supplier": "SRL Chemicals",
                "quantity": 140,
                "quantity_unit": "L",
                "storage_location": "Flammable Store - Rack F1",
            },
            {
                "chemical_name": "Methanol",
                "trade_name": "Methanol AR",
                "cas_number": "67-56-1",
                "un_number": "UN1230",
                "supplier": "Loba Chemie",
                "quantity": 95,
                "quantity_unit": "L",
                "storage_location": "Flammable Store - Rack F2",
            },
            {
                "chemical_name": "Isopropyl Alcohol",
                "trade_name": "IPA 99%",
                "cas_number": "67-63-0",
                "un_number": "UN1219",
                "supplier": "Avantor",
                "quantity": 220,
                "quantity_unit": "L",
                "storage_location": "Flammable Store - Rack F3",
            },
            {
                "chemical_name": "Toluene",
                "trade_name": "Toluene AR",
                "cas_number": "108-88-3",
                "un_number": "UN1294",
                "supplier": "Merck Life Science",
                "quantity": 110,
                "quantity_unit": "L",
                "storage_location": "Flammable Store - Rack F4",
            },
            {
                "chemical_name": "Xylene",
                "trade_name": "Xylene Mixed Isomers",
                "cas_number": "1330-20-7",
                "un_number": "UN1307",
                "supplier": "Thermo Fisher Scientific",
                "quantity": 90,
                "quantity_unit": "L",
                "storage_location": "Flammable Store - Rack F5",
            },
            {
                "chemical_name": "Hydrogen Peroxide",
                "trade_name": "Hydrogen Peroxide 50%",
                "cas_number": "7722-84-1",
                "un_number": "UN2014",
                "supplier": "GACL",
                "quantity": 100,
                "quantity_unit": "L",
                "storage_location": "Oxidizer Store - Rack O1",
            },
            {
                "chemical_name": "Sodium Hypochlorite",
                "trade_name": "Sodium Hypochlorite Solution",
                "cas_number": "7681-52-9",
                "un_number": "UN1791",
                "supplier": "Aditya Birla Chemicals",
                "quantity": 160,
                "quantity_unit": "L",
                "storage_location": "Chemical Store - Rack C1",
            },
            {
                "chemical_name": "Ammonia",
                "trade_name": "Ammonia Solution 25%",
                "cas_number": "1336-21-6",
                "un_number": "UN2672",
                "supplier": "Loba Chemie",
                "quantity": 75,
                "quantity_unit": "L",
                "storage_location": "Chemical Store - Rack C2",
            },
            {
                "chemical_name": "Nitric Acid",
                "trade_name": "Nitric Acid 68%",
                "cas_number": "7697-37-2",
                "un_number": "UN2031",
                "supplier": "Merck Life Science",
                "quantity": 80,
                "quantity_unit": "L",
                "storage_location": "Acid Store - Rack A3",
            },
            {
                "chemical_name": "Phosphoric Acid",
                "trade_name": "Phosphoric Acid 85%",
                "cas_number": "7664-38-2",
                "un_number": "UN1805",
                "supplier": "GACL",
                "quantity": 120,
                "quantity_unit": "L",
                "storage_location": "Acid Store - Rack A4",
            },
            {
                "chemical_name": "Acetic Acid",
                "trade_name": "Glacial Acetic Acid",
                "cas_number": "64-19-7",
                "un_number": "UN2789",
                "supplier": "Avantor",
                "quantity": 85,
                "quantity_unit": "L",
                "storage_location": "Acid Store - Rack A5",
            },
            {
                "chemical_name": "Ethylene Glycol",
                "trade_name": "Ethylene Glycol Industrial",
                "cas_number": "107-21-1",
                "un_number": "UN3082",
                "supplier": "Reliance Industries",
                "quantity": 200,
                "quantity_unit": "L",
                "storage_location": "Chemical Store - Rack C3",
            },
            {
                "chemical_name": "Zinc Oxide",
                "trade_name": "Zinc Oxide Powder",
                "cas_number": "1314-13-2",
                "un_number": "UN3077",
                "supplier": "Nocil",
                "quantity": 150,
                "quantity_unit": "kg",
                "storage_location": "Powder Store - Rack P1",
            },
            {
                "chemical_name": "Calcium Carbonate",
                "trade_name": "Calcium Carbonate Industrial",
                "cas_number": "471-34-1",
                "un_number": None,
                "supplier": "Gulshan Polyols",
                "quantity": 500,
                "quantity_unit": "kg",
                "storage_location": "Powder Store - Rack P2",
            },
            {
                "chemical_name": "Sodium Carbonate",
                "trade_name": "Soda Ash Light",
                "cas_number": "497-19-8",
                "un_number": "UN3378",
                "supplier": "Tata Chemicals",
                "quantity": 400,
                "quantity_unit": "kg",
                "storage_location": "Powder Store - Rack P3",
            },
            {
                "chemical_name": "Potassium Hydroxide",
                "trade_name": "Caustic Potash",
                "cas_number": "1310-58-3",
                "un_number": "UN1813",
                "supplier": "Brenntag India",
                "quantity": 180,
                "quantity_unit": "kg",
                "storage_location": "Alkali Store - Rack B2",
            },
            {
                "chemical_name": "Formaldehyde",
                "trade_name": "Formalin 37%",
                "cas_number": "50-00-0",
                "un_number": "UN2209",
                "supplier": "SRL Chemicals",
                "quantity": 70,
                "quantity_unit": "L",
                "storage_location": "Chemical Store - Rack C4",
            },
            {
                "chemical_name": "Ammonium Hydroxide",
                "trade_name": "Ammonia Water",
                "cas_number": "1336-21-6",
                "un_number": "UN2672",
                "supplier": "Thermo Fisher Scientific",
                "quantity": 60,
                "quantity_unit": "L",
                "storage_location": "Chemical Store - Rack C5",
            },
            {
                "chemical_name": "Sodium Metabisulfite",
                "trade_name": "SMBS Industrial",
                "cas_number": "7681-57-4",
                "un_number": "UN3262",
                "supplier": "Tata Chemicals",
                "quantity": 125,
                "quantity_unit": "kg",
                "storage_location": "Powder Store - Rack P4",
            },
            {
                "chemical_name": "Potassium Permanganate",
                "trade_name": "Potassium Permanganate",
                "cas_number": "7722-64-7",
                "un_number": "UN1490",
                "supplier": "Merck Life Science",
                "quantity": 35,
                "quantity_unit": "kg",
                "storage_location": "Oxidizer Store - Rack O2",
            },
            {
                "chemical_name": "Hydrogen Fluoride",
                "trade_name": "Hydrofluoric Acid",
                "cas_number": "7664-39-3",
                "un_number": "UN1790",
                "supplier": "Avantor",
                "quantity": 35,
                "quantity_unit": "L",
                "storage_location": "Acid Store - Rack A6",
            },
            {
                "chemical_name": "Ethyl Acetate",
                "trade_name": "Ethyl Acetate AR",
                "cas_number": "141-78-6",
                "un_number": "UN1173",
                "supplier": "Loba Chemie",
                "quantity": 100,
                "quantity_unit": "L",
                "storage_location": "Flammable Store - Rack F6",
            },
            {
                "chemical_name": "N-Hexane",
                "trade_name": "n-Hexane AR",
                "cas_number": "110-54-3",
                "un_number": "UN1208",
                "supplier": "SRL Chemicals",
                "quantity": 65,
                "quantity_unit": "L",
                "storage_location": "Flammable Store - Rack F7",
            },
            {
                "chemical_name": "Methyl Ethyl Ketone",
                "trade_name": "MEK Industrial",
                "cas_number": "78-93-3",
                "un_number": "UN1193",
                "supplier": "BASF India",
                "quantity": 80,
                "quantity_unit": "L",
                "storage_location": "Flammable Store - Rack F8",
            },
            {
                "chemical_name": "Chloroform",
                "trade_name": "Chloroform AR",
                "cas_number": "67-66-3",
                "un_number": "UN1888",
                "supplier": "Merck Life Science",
                "quantity": 45,
                "quantity_unit": "L",
                "storage_location": "Toxic Chemical Store - Rack T1",
            },
            {
                "chemical_name": "Phenol",
                "trade_name": "Phenol Crystal",
                "cas_number": "108-95-2",
                "un_number": "UN1671",
                "supplier": "Thermo Fisher Scientific",
                "quantity": 40,
                "quantity_unit": "kg",
                "storage_location": "Toxic Chemical Store - Rack T2",
            },
            {
                "chemical_name": "Sodium Sulfate",
                "trade_name": "Sodium Sulfate Anhydrous",
                "cas_number": "7757-82-6",
                "un_number": None,
                "supplier": "Tata Chemicals",
                "quantity": 300,
                "quantity_unit": "kg",
                "storage_location": "Powder Store - Rack P5",
            },
        ]

        # Map the requested number of records onto the available master list.
        records_to_create = chemical_master[:min(count, len(chemical_master))]

        # If more than the built-in master list is requested, repeat the list
        # with unique CAS numbers so the Chemical unique constraint is respected.
        if count > len(chemical_master):
            records_to_create = []
            for index in range(count):
                base = chemical_master[index % len(chemical_master)].copy()
                base["cas_number"] = f"{base['cas_number']}-D{index + 1:03d}"
                base["lot_number"] = f"DEMO-FY2627-{index + 1:04d}"
                records_to_create.append(base)

        statuses = [
            "in_stock",
            "in_stock",
            "in_stock",
            "low_stock",
            "low_stock",
            "out_of_stock",
            "expired",
        ]

        created = 0
        skipped = 0

        self.stdout.write(
            self.style.NOTICE(
                f"Chemical demo data: {fy_start} to {fy_end}"
            )
        )
        self.stdout.write(
            self.style.NOTICE(
                f"Using {len(users)} existing users and {len(plants)} existing plants."
            )
        )

        for index, data in enumerate(records_to_create):
            # Avoid creating duplicate Chemical records when the command is rerun.
            if Chemical.objects.filter(cas_number=data["cas_number"]).exists():
                skipped += 1
                continue

            user = users[index % len(users)]

            # Build a complete valid Plant -> Zone -> Location hierarchy.
            # The Chemical model validates these relationships, and Location
            # is required by the current database/model validation.
            valid_locations = [
                loc for loc in locations
                if getattr(loc, "zone_id", None)
                and getattr(loc.zone, "plant_id", None)
            ]

            if not valid_locations:
                raise CommandError(
                    "No valid Location records found with a Zone and Plant relationship. "
                    "Create/import the Plant -> Zone -> Location master hierarchy first."
                )

            location = valid_locations[index % len(valid_locations)]
            zone = location.zone
            plant = zone.plant

            location_sublocations = [
                sub for sub in sublocations
                if getattr(sub, "location_id", None) == location.id
            ]
            sublocation = (
                location_sublocations[index % len(location_sublocations)]
                if location_sublocations
                else None
            )

            plant_departments = [
                dept for dept in departments
                if getattr(dept, "plant_id", None) == plant.id
            ]
            department = (
                plant_departments[index % len(plant_departments)]
                if plant_departments
                else None
            )

            # Keep all transaction dates inside the current financial year.
            date_range = (fy_end - fy_start).days
            receipt_offset = (index * 11) % (date_range + 1)
            receipt_date = fy_start + timedelta(days=receipt_offset)

            # Most demo records remain valid; a few are deliberately expired
            # so the inventory status distribution is useful for testing.
            status = statuses[index % len(statuses)]

            if status == "expired":
                expiration_date = receipt_date + timedelta(days=90)
                if expiration_date >= fy_end:
                    expiration_date = fy_end - timedelta(days=1)
            else:
                expiration_date = fy_end + timedelta(days=30 + (index % 6) * 30)

            lot_number = data.get("lot_number") or f"LOT-FY2627-{index + 1:04d}"

            ehs_compliance = {
                "ghs": [
                    "Flammable" if index % 3 == 0 else "Corrosive",
                    "Health Hazard" if index % 4 == 0 else "Environmental Hazard",
                ],
                "ppe": [
                    "Chemical Resistant Gloves",
                    "Safety Goggles",
                    "Protective Clothing",
                ],
            }

            # FileField is mandatory in the Chemical model, so create a small
            # demo SDS placeholder file for each Chemical record.
            pdf_content = (
                b"%PDF-1.4\n"
                b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
                b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
                b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Contents 4 0 R >>endobj\n"
                b"4 0 obj<< /Length 44 >>stream\n"
                b"BT /F1 12 Tf 72 720 Td (Demo Chemical SDS) Tj ET\n"
                b"endstream endobj\n"
                b"xref\n0 5\n0000000000 65535 f \n"
                b"trailer<< /Size 5 /Root 1 0 R >>\n"
                b"startxref\n0\n%%EOF"
            )

            chemical = Chemical(
                chemical_name=data["chemical_name"],
                trade_name=data.get("trade_name"),
                cas_number=data["cas_number"],
                un_number=data.get("un_number"),
                supplier=data.get("supplier"),
                lot_number=lot_number,
                receipt_date=receipt_date,
                expiration_date=expiration_date,
                plant=plant,
                zone=zone,
                location=location,
                sublocation=sublocation,
                department=department,
                quantity=data["quantity"],
                quantity_unit=data["quantity_unit"],
                storage_location=data["storage_location"],
                owner=user.get_full_name() or user.username,
                status=status,
                ehs_compliance=ehs_compliance,
                created_by=user,
            )

            # FileField is required by the Chemical model, so attach the
            # demo SDS file before full_clean() validates the model.
            chemical.sds_file = ContentFile(
                pdf_content,
                name=f"demo_chemical_sds_{index + 1:04d}.pdf",
            )

            # Validate the plant/zone/location/sub-location hierarchy and all
            # required model fields before saving the Chemical record.
            chemical.full_clean()

            chemical.save()

            created += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Chemical demo data completed. Created: {created}, Skipped: {skipped}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Total Chemical records now: {Chemical.objects.count()}"
            )
        )
