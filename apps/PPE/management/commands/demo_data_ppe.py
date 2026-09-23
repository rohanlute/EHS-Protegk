# ============================================================
## run to generate data:
## python manage.py demo_data_ppe
## Or explicitly for related to employees available:
## python manage.py demo_data_ppe --count 13 --records 100
# ============================================================
# ============================================================
# PPE Demo Data Seeder
# Creates realistic demo data using existing users and
# existing organization assignments.
# ============================================================



from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import random

from apps.PPE.models import (
    PPECategory,
    PPEItem,
    PPESizeQuantity,
    PPEStockTransaction,
    PPEIssueManagement,
    PPEReturnManagement,
    PPEInspectionSchedule,
    PPEInspection,
    PPEInspectionAssessment,
)
from apps.accounts.models import User
from apps.organizations.models import Plant, Department


class Command(BaseCommand):
    help = "Create realistic PPE demo data for the current financial year."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=100)

    def handle(self, *args, **options):
        count = options["count"]
        today = timezone.now().date()

        # Current Indian financial year: 1 April to today.
        fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)

        users = list(
            User.objects.filter(is_active=True).order_by("id")
        )
        plants = list(
            Plant.objects.filter(is_active=True).order_by("id")
        )
        departments = list(
            Department.objects.filter(is_active=True).order_by("id")
        )

        if not users:
            self.stdout.write(self.style.ERROR("No active users found."))
            return
        if not plants:
            self.stdout.write(self.style.ERROR("No active plants found."))
            return

        random.seed(260923)

        self.stdout.write(
            f"Creating PPE demo data from {fy_start} to {today}..."
        )
        self.stdout.write(
            f"Using {len(users)} active users, {len(plants)} active plants "
            f"and {len(departments)} active departments."
        )

        categories_data = [
            ("Head Protection", "HEL", "Safety helmets and head protection."),
            ("Eye Protection", "EYE", "Safety spectacles and goggles."),
            ("Hand Protection", "GLO", "Safety gloves for different activities."),
            ("Foot Protection", "SHO", "Safety shoes and protective footwear."),
            ("Respiratory Protection", "RES", "Respirators and face masks."),
            ("Hearing Protection", "EAR", "Ear plugs and ear muffs."),
            ("Body Protection", "BOD", "Safety jackets, aprons and protective clothing."),
            ("Fall Protection", "FAL", "Harnesses and fall protection equipment."),
        ]

        category_map = {}
        for name, code, description in categories_data:
            # Reuse an existing category by name first because category_name is unique.
            # Older/demo data may have the same name with a different category_code.
            category = PPECategory.objects.filter(category_name=name).first()
            created = False

            # If the name does not exist, try the unique category code.
            if category is None:
                category = PPECategory.objects.filter(category_code=code).first()

            # Create only when neither the name nor code already exists.
            if category is None:
                category = PPECategory.objects.create(
                    category_name=name,
                    category_code=code,
                    description=description,
                    is_active=True,
                )
                created = True

            # Update non-unique descriptive fields only.
            if not created:
                changed = False
                update_fields = []

                if not category.description:
                    category.description = description
                    update_fields.append("description")

                if not category.is_active:
                    category.is_active = True
                    update_fields.append("is_active")

                if update_fields:
                    category.save(update_fields=update_fields)

            category_map[code] = category

        item_data = [
            ("HEL", "Industrial Safety Helmet", "Karam", "KH-01", "NO", "NO", "YES"),
            ("HEL", "Electrical Safety Helmet", "Mallcom", "EH-220", "NO", "NO", "YES"),
            ("HEL", "Ventilated Safety Helmet", "Udyogi", "UH-100", "NO", "NO", "YES"),
            ("EYE", "Clear Safety Spectacles", "3M", "SF-401", "YES", "NO", "NO"),
            ("EYE", "Anti-Fog Safety Goggles", "Udyogi", "AFG-12", "YES", "NO", "NO"),
            ("EYE", "Chemical Splash Goggles", "Mallcom", "CSG-20", "YES", "YES", "NO"),
            ("GLO", "Nitrile Chemical Gloves", "Ansell", "NIT-45", "YES", "YES", "YES"),
            ("GLO", "Cut Resistant Gloves", "Karam", "CRG-05", "YES", "YES", "YES"),
            ("GLO", "Heat Resistant Gloves", "Udyogi", "HRG-08", "YES", "YES", "YES"),
            ("SHO", "Steel Toe Safety Shoes", "Allen Cooper", "AC-100", "YES", "NO", "YES"),
            ("SHO", "Electrical Safety Shoes", "Bata Industrials", "ES-210", "YES", "NO", "YES"),
            ("SHO", "Chemical Resistant Safety Boots", "Hillson", "CRB-30", "YES", "YES", "YES"),
            ("RES", "N95 Respirator", "3M", "N95-8210", "YES", "YES", "NO"),
            ("RES", "Half Face Respirator", "Drager", "HF-200", "YES", "YES", "NO"),
            ("RES", "Full Face Respirator", "3M", "FF-6000", "YES", "YES", "NO"),
            ("EAR", "Disposable Ear Plugs", "3M", "EP-1100", "NO", "NO", "NO"),
            ("EAR", "Reusable Ear Plugs", "Honeywell", "EP-R20", "NO", "YES", "NO"),
            ("EAR", "Ear Muff", "Udyogi", "EM-25", "YES", "YES", "NO"),
            ("BOD", "Reflective Safety Jacket", "Karam", "SJ-101", "NO", "NO", "YES"),
            ("BOD", "Chemical Protective Apron", "Ansell", "CPA-10", "YES", "YES", "NO"),
            ("BOD", "Welding Apron", "Udyogi", "WA-50", "YES", "YES", "NO"),
            ("FAL", "Full Body Safety Harness", "Karam", "FBH-500", "YES", "YES", "YES"),
            ("FAL", "Double Lanyard", "Udyogi", "DL-22", "YES", "YES", "NO"),
            ("FAL", "Retractable Lifeline", "Karam", "RLL-15", "YES", "YES", "NO"),
        ]

        items = []
        for code, name, brand, model, inspection_required, replacement_required, size_applicable in item_data:
            category = category_map[code]
            item = PPEItem.objects.filter(
                name=name,
                category=category,
            ).first()

            if not item:
                manufacturing_date = fy_start - timedelta(days=random.randint(30, 300))
                expiry_date = manufacturing_date + timedelta(days=random.randint(730, 1825))
                item = PPEItem.objects.create(
                    name=name,
                    category=category,
                    description=f"Demo PPE item for {category.category_name}.",
                    manufacturer_brand=brand,
                    model_number=model,
                    manufacturing_date=manufacturing_date,
                    expiry_date=expiry_date,
                    inspection_required=inspection_required,
                    replacement_required=replacement_required,
                    size_applicable=size_applicable,
                    is_active=True,
                )
            items.append(item)

        # Use practical sizes. Non-size PPE still gets one stock bucket because
        # the current PPE stock model requires a size record for issue/return flow.
        size_sets = {
            "HEL": ["M", "L", "XL"],
            "EYE": ["STD"],
            "GLO": ["M", "L", "XL"],
            "SHO": ["7", "8", "9", "10"],
            "RES": ["STD"],
            "EAR": ["STD"],
            "BOD": ["M", "L", "XL"],
            "FAL": ["STD"],
        }

        item_sizes = {}
        for item in items:
            sizes = size_sets.get(item.category.category_code, ["STD"])
            # category_code is normally present; fallback safely if needed.
            if not sizes:
                sizes = ["STD"]
            item_sizes[item.id] = []
            for size in sizes:
                plant = plants[0]
                # Create a base size record. Plant-specific records are created below.
                base, _ = PPESizeQuantity.objects.get_or_create(
                    ppe_item=item,
                    plant=plant,
                    size=size,
                    defaults={"available_quantity": 0},
                )
                item_sizes[item.id].append(size)

        def get_size_record(item, plant, size):
            obj, _ = PPESizeQuantity.objects.get_or_create(
                ppe_item=item,
                plant=plant,
                size=size,
                defaults={"available_quantity": 0},
            )
            return obj

        def random_date():
            days = max((today - fy_start).days, 1)
            return fy_start + timedelta(days=random.randint(0, days))

        created_stock = 0
        created_issues = 0
        created_returns = 0
        created_schedules = 0
        created_inspections = 0
        created_assessments = 0

        with transaction.atomic():
            # ------------------------------------------------------------
            # 1. Stock transactions
            # ------------------------------------------------------------
            for i in range(count):
                item = items[i % len(items)]
                plant = plants[i % len(plants)]
                size = item_sizes[item.id][i % len(item_sizes[item.id])]
                size_obj = get_size_record(item, plant, size)

                quantity = random.randint(15, 80)
                transaction_type = ["OPENING", "STOCK_IN", "ADJUSTMENT"][i % 3]
                tx_date = random_date()

                size_obj.available_quantity += quantity
                size_obj.save(update_fields=["available_quantity", "updated_at"])

                PPEStockTransaction.objects.create(
                    plant=plant,
                    ppe_item=item,
                    size=size_obj,
                    size_quantities={size: quantity},
                    quantity=quantity,
                    unit="PAIR" if item.category.category_code in ["GLO", "SHO"] else "NOS",
                    total=quantity,
                    transaction_type=transaction_type,
                    transaction_date=tx_date,
                    reference_number=f"GRN-PPE-{fy_start.year}-{i + 1:04d}",
                    remarks=f"Demo {transaction_type.lower().replace('_', ' ')} transaction.",
                    created_by=users[i % len(users)],
                    is_active=True,
                )
                created_stock += 1

            # ------------------------------------------------------------
            # 2. PPE issue transactions
            # ------------------------------------------------------------
            issue_records = []
            for i in range(count):
                item = items[(i * 3) % len(items)]
                plant = plants[(i * 2) % len(plants)]
                size = item_sizes[item.id][i % len(item_sizes[item.id])]
                size_obj = get_size_record(item, plant, size)

                # Ensure enough stock remains for the issue.
                if size_obj.available_quantity < 10:
                    extra = 25
                    size_obj.available_quantity += extra
                    size_obj.save(update_fields=["available_quantity", "updated_at"])
                    PPEStockTransaction.objects.create(
                        plant=plant,
                        ppe_item=item,
                        size=size_obj,
                        size_quantities={size: extra},
                        quantity=extra,
                        unit="PAIR" if item.category.category_code in ["GLO", "SHO"] else "NOS",
                        total=extra,
                        transaction_type="STOCK_IN",
                        transaction_date=random_date(),
                        reference_number=f"GRN-PPE-EXTRA-{i + 1:04d}",
                        remarks="Additional demo stock created for issue flow.",
                        created_by=users[(i + 1) % len(users)],
                        is_active=True,
                    )

                qty = random.randint(1, min(5, size_obj.available_quantity))
                employee = users[i % len(users)]
                issue_to = "EMPLOYEE" if i % 5 != 0 else "CONTRACTOR"
                contractor_name = "" if issue_to == "EMPLOYEE" else [
                    "Apex Engineering Solutions",
                    "SafeTech Services",
                    "Prime Industrial Contractors",
                    "Shree Maintenance Services",
                ][i % 4]

                issue_date = random_date()
                issue = PPEIssueManagement.objects.create(
                    issue_group_no=f"PPE-ISS-GRP-{i + 1:04d}",
                    issue_date=issue_date,
                    plant=plant,
                    plant_name=plant.name,
                    ppe_item=item,
                    available_quantity=size_obj.available_quantity,
                    issue_to=issue_to,
                    employee=employee if issue_to == "EMPLOYEE" else None,
                    contractor_name=contractor_name,
                    contractor_department="Maintenance" if issue_to == "CONTRACTOR" else "",
                    department=(
                        employee.department
                        if issue_to == "EMPLOYEE" and getattr(employee, "department_id", None)
                        else (departments[i % len(departments)] if departments else None)
                    ),
                    size=size_obj,
                    quantity_issue=qty,
                    remarks="Demo PPE issue transaction.",
                    created_by=users[(i + 2) % len(users)],
                )

                size_obj.available_quantity -= qty
                size_obj.save(update_fields=["available_quantity", "updated_at"])

                issue_records.append(issue)
                created_issues += 1

            # ------------------------------------------------------------
            # 3. PPE returns
            # ------------------------------------------------------------
            for i, issue in enumerate(issue_records):
                # Return most issued PPE; some remain pending to create realistic data.
                if i % 5 == 0:
                    continue

                returned_already = 0
                max_return = issue.quantity_issue - returned_already
                if max_return <= 0:
                    continue

                return_qty = random.randint(1, max_return)
                return_date = min(
                    today,
                    issue.issue_date + timedelta(days=random.randint(7, 90)),
                )

                # Returning stock first.
                size_obj = issue.size
                size_obj.available_quantity += return_qty
                size_obj.save(update_fields=["available_quantity", "updated_at"])

                PPEReturnManagement.objects.create(
                    return_group_no=f"PPE-RET-GRP-{i + 1:04d}",
                    issue=issue,
                    return_date=return_date,
                    return_qty=return_qty,
                    remarks=random.choice([
                        "Returned after replacement.",
                        "Returned after inspection.",
                        "Returned on employee transfer.",
                        "Returned after task completion.",
                    ]),
                    created_by=users[(i + 3) % len(users)],
                    updated_by=users[(i + 4) % len(users)],
                )
                created_returns += 1

            # ------------------------------------------------------------
            # 4. Inspection schedules
            # ------------------------------------------------------------
            return_records = list(
                PPEReturnManagement.objects.select_related(
                    "issue", "ppe_item", "plant", "size"
                ).order_by("id")[:count]
            )

            schedule_records = []
            for i, return_obj in enumerate(return_records):
                plant = return_obj.plant
                assigned_user = users[(i + 5) % len(users)]

                # Use HOD / Safety Manager where available; otherwise keep HOD
                # because the model only supports these two role values.
                role_name = ""
                if getattr(assigned_user, "role", None):
                    role_name = str(assigned_user.role.name).upper()

                assigned_role = (
                    "SAFETY_MANAGER"
                    if "SAFETY MANAGER" in role_name
                    else "HOD"
                )

                scheduled_date = min(
                    today,
                    return_obj.return_date + timedelta(days=random.randint(1, 15)),
                )
                scheduled_end_date = scheduled_date + timedelta(
                    days=random.randint(1, 7)
                )

                if i % 10 == 0:
                    status = "CANCELLED"
                elif i % 7 == 0:
                    status = "OVERDUE"
                elif i % 4 == 0:
                    status = "IN_PROGRESS"
                elif i % 3 == 0:
                    status = "COMPLETED"
                else:
                    status = "SCHEDULED"

                # Avoid model.save() converting an intended future schedule to
                # OVERDUE by keeping scheduled end date at/after today for active records.
                if status in ["SCHEDULED", "IN_PROGRESS"]:
                    scheduled_date = today + timedelta(days=random.randint(1, 30))
                    scheduled_end_date = scheduled_date + timedelta(days=random.randint(1, 7))

                if status == "OVERDUE":
                    scheduled_end_date = today - timedelta(days=random.randint(1, 20))
                    scheduled_date = scheduled_end_date - timedelta(days=random.randint(1, 7))

                schedule = PPEInspectionSchedule.objects.create(
                    ppe_item=return_obj.ppe_item,
                    ppe_return=return_obj,
                    plant=plant,
                    department=(
                        assigned_user.department
                        if getattr(assigned_user, "department_id", None)
                        else (departments[i % len(departments)] if departments else None)
                    ),
                    assigned_role=assigned_role,
                    assigned_user=assigned_user,
                    assigned_by=users[(i + 6) % len(users)],
                    scheduled_date=scheduled_date,
                    scheduled_end_date=scheduled_end_date,
                    assignment_notes="Demo PPE inspection assignment.",
                    status=status,
                )
                schedule_records.append(schedule)
                created_schedules += 1

            # ------------------------------------------------------------
            # 5. Completed inspections and assessments
            # ------------------------------------------------------------
            reusable = ["REUSABLE", "REPAIR", "SCRAP"]

            for i, schedule in enumerate(
                [s for s in schedule_records if s.status == "COMPLETED"]
            ):
                inspection_status = reusable[i % len(reusable)]

                inspection = PPEInspection.objects.create(
                    schedule=schedule,
                    status=inspection_status,
                    remarks={
                        "REUSABLE": "PPE inspected and found suitable for reuse.",
                        "REPAIR": "PPE requires minor repair before reuse.",
                        "SCRAP": "PPE is damaged and recommended for disposal.",
                    }[inspection_status],
                    inspected_by=schedule.assigned_user,
                )
                created_inspections += 1

                PPEInspectionAssessment.objects.create(
                    inspection=inspection,
                    return_item=schedule.ppe_return,
                    status=inspection_status,
                    remarks={
                        "REUSABLE": "No critical defect observed.",
                        "REPAIR": "Minor wear observed during inspection.",
                        "SCRAP": "Critical damage observed during inspection.",
                    }[inspection_status],
                )
                created_assessments += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("PPE demo data created successfully."))
        self.stdout.write(f"Categories available: {PPECategory.objects.count()}")
        self.stdout.write(f"PPE Items available: {PPEItem.objects.count()}")
        self.stdout.write(f"Stock transactions created: {created_stock}")
        self.stdout.write(f"Issue transactions created: {created_issues}")
        self.stdout.write(f"Return transactions created: {created_returns}")
        self.stdout.write(f"Inspection schedules created: {created_schedules}")
        self.stdout.write(f"Completed inspections created: {created_inspections}")
        self.stdout.write(f"Inspection assessments created: {created_assessments}")
        self.stdout.write(
            f"Financial year range: {fy_start.strftime('%d-%m-%Y')} "
            f"to {today.strftime('%d-%m-%Y')}"
        )
