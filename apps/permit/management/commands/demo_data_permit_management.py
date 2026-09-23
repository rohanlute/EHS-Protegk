# ============================================================
## run to generate data:
## python manage.py demo_data_permit_management
## Or explicitly for related to employees available:
## python manage.py demo_data_permit_management --count 13 --records 100
# ============================================================
# ============================================================
# Permit Demo Data Seeder
# Creates realistic demo data using existing users and
# existing organization assignments.
# ============================================================

from datetime import datetime, time, timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Plant, Zone, Location, SubLocation, Department
from apps.permit.models import (
    Permit,
    PermitType,
    PermitContractor,
    PermitApprovalLog,
    PermitExtension,
    PermitClosure,
    PermitAttachment,
)


class Command(BaseCommand):
    help = "Create realistic Permit Management demo data for the current financial year."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of Permit records to create. Default: 100.",
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
            tzinfo=timezone.get_current_timezone(),
        ).date()
        fy_end = today

        # Reuse existing active users; no demo users are created.
        users = list(User.objects.filter(is_active=True).order_by("id"))

        # Reuse existing organization hierarchy; no demo organization records
        # are created by this command.
        plants = list(Plant.objects.all().order_by("id"))
        zones = list(Zone.objects.all().order_by("id"))
        locations = list(Location.objects.all().order_by("id"))
        sublocations = list(SubLocation.objects.all().order_by("id"))
        departments = list(Department.objects.all().order_by("id"))

        if not users:
            raise CommandError(
                "No active User records found. Create/import users first."
            )

        if not plants:
            raise CommandError(
                "No Plant records found. Create/import Plant master data first."
            )

        # Permit Type is a functional master. Reuse existing records and only
        # create standard Permit Types if the master is completely empty.
        permit_types = list(PermitType.objects.filter(is_active=True).order_by("id"))

        if not permit_types:
            standard_types = [
                ("Hot Work Permit", "HOT-WORK", "Permit for welding, cutting, grinding and other hot work."),
                ("Work at Height Permit", "HEIGHT", "Permit for work at height requiring fall protection."),
                ("Confined Space Entry Permit", "CONFINED", "Permit for entry into confined spaces."),
                ("Electrical Work Permit", "ELECTRICAL", "Permit for electrical isolation and electrical work."),
                ("Excavation Permit", "EXCAVATION", "Permit for excavation and ground disturbance work."),
                ("General Work Permit", "GENERAL", "Permit for general maintenance and non-routine work."),
                ("Line Breaking Permit", "LINE-BREAK", "Permit for opening or breaking process lines/equipment."),
                ("Lifting Work Permit", "LIFTING", "Permit for critical lifting and material handling work."),
            ]

            for name, code, description in standard_types:
                PermitType.objects.create(
                    name=name,
                    code=code,
                    description=description,
                    is_active=True,
                    created_by=users[0],
                )

            permit_types = list(PermitType.objects.filter(is_active=True).order_by("id"))

        # Build only valid Plant -> Zone -> Location combinations because the
        # Permit model validates the organization hierarchy.
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

        valid_location_ids = {location.id for _, _, location in valid_locations}

        priority_values = ["low", "medium", "medium", "high", "emergency"]
        risk_values = ["minor", "moderate", "major", "critical"]

        status_cycle = [
            "draft",
            "pending",
            "approved",
            "active",
            "closed",
            "rejected",
            "approved",
            "active",
            "closed",
            "pending",
        ]

        work_by_type = {
            "HOT-WORK": (
                "Welding and cutting work for equipment maintenance",
                ["Fire", "Burn injury", "Hot metal", "Sparks"],
                "Fire extinguisher, fire watch, welding PPE and spark containment.",
            ),
            "HEIGHT": (
                "Maintenance work on elevated platform and structural access",
                ["Fall from height", "Falling objects", "Unstable access"],
                "Full body harness, lifeline, barricading and inspected access equipment.",
            ),
            "CONFINED": (
                "Inspection and maintenance inside a confined space",
                ["Oxygen deficiency", "Toxic atmosphere", "Engulfment"],
                "Gas testing, ventilation, standby person, rescue arrangement and PPE.",
            ),
            "ELECTRICAL": (
                "Electrical maintenance and isolation work",
                ["Electric shock", "Arc flash", "Unexpected energization"],
                "LOTO, electrical PPE, test-before-touch and authorized electrician.",
            ),
            "EXCAVATION": (
                "Civil excavation and underground service work",
                ["Cave-in", "Underground utility", "Vehicle movement"],
                "Barricading, utility verification, safe slope and access control.",
            ),
            "GENERAL": (
                "Routine maintenance and non-routine mechanical work",
                ["Mechanical injury", "Stored energy", "Slip and trip"],
                "Isolation, tools inspection, housekeeping and required PPE.",
            ),
            "LINE-BREAK": (
                "Process line opening and maintenance activity",
                ["Chemical exposure", "Pressure release", "Residual material"],
                "Isolation, draining, depressurization, PPE and spill control.",
            ),
            "LIFTING": (
                "Lifting and shifting of equipment using lifting equipment",
                ["Dropped load", "Crushing", "Rigging failure"],
                "Certified lifting equipment, trained riggers and exclusion zone.",
            ),
        }

        trades = [
            "Welder",
            "Fitter",
            "Electrician",
            "Rigger",
            "Scaffolder",
            "Mechanical Technician",
            "Instrument Technician",
            "Civil Technician",
        ]

        contractor_companies = [
            "Apex Engineering Solutions Pvt Ltd",
            "SafeWorks Industrial Services",
            "Prime Maintenance Contractors",
            "Shree Engineering Services",
            "TechnoFab Industrial Solutions",
            "Universal Plant Services",
        ]

        created = 0
        skipped = 0

        self.stdout.write(
            self.style.NOTICE(
                f"Permit Management demo data: {fy_start} to {fy_end}"
            )
        )
        self.stdout.write(
            self.style.NOTICE(
                f"Using {len(users)} existing users, {len(plants)} existing plants "
                f"and {len(valid_locations)} valid organization locations."
            )
        )

        # Existing permits are not modified. New permit records are appended.
        for index in range(count):
            user = users[index % len(users)]
            approver = users[(index + 1) % len(users)]

            plant, zone, location = valid_locations[index % len(valid_locations)]

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
                department
                for department in departments
                if getattr(department, "plant_id", None) == plant.id
            ]
            department = (
                plant_departments[index % len(plant_departments)]
                if plant_departments
                else None
            )

            permit_type = permit_types[index % len(permit_types)]
            status = status_cycle[index % len(status_cycle)]
            priority = priority_values[index % len(priority_values)]
            risk = risk_values[index % len(risk_values)]

            work_description, hazards, safety_measures = work_by_type.get(
                permit_type.code,
                work_by_type["GENERAL"],
            )

            # Keep permit dates inside the requested FY and never after today.
            fy_days = (fy_end - fy_start).days
            start_offset = (index * 3) % (fy_days + 1)
            start_date = fy_start + timedelta(days=start_offset)

            duration_days = 1 + (index % 3)
            end_date = min(start_date + timedelta(days=duration_days), fy_end)

            if end_date < start_date:
                end_date = start_date

            start_dt = timezone.make_aware(
                datetime.combine(start_date, time(hour=8 + (index % 3))),
                timezone.get_current_timezone(),
            )
            end_hour = min(20, start_dt.hour + 4 + (index % 4))
            end_dt = timezone.make_aware(
                datetime.combine(end_date, time(hour=end_hour)),
                timezone.get_current_timezone(),
            )

            # Use a small set of meaningful checklist answers.
            checklist_yes = {
                "plant_running": "yes" if index % 3 else "no",
                "equipment_isolated": "yes",
                "valves_closed": "yes",
                "equipment_drained": "yes" if index % 2 == 0 else "na",
                "equipment_disconnected": "yes" if permit_type.code == "ELECTRICAL" else "na",
                "pipeline_depressurized": "yes" if permit_type.code == "LINE-BREAK" else "na",
                "pipeline_drained": "yes" if permit_type.code == "LINE-BREAK" else "na",
                "pipeline_purged": "yes" if permit_type.code in ("LINE-BREAK", "CONFINED") else "na",
                "pipeline_ventilated": "yes" if permit_type.code == "CONFINED" else "na",
                "electrical_earthing": "yes" if permit_type.code == "ELECTRICAL" else "na",
                "area_protected": "yes",
                "gas_test": "yes" if permit_type.code in ("HOT-WORK", "CONFINED", "LINE-BREAK") else "na",
                "spillage_removed": "yes",
                "ppe_safety_shoe": "yes",
                "ppe_helmet": "yes",
                "ppe_safety_belt": "yes" if permit_type.code == "HEIGHT" else "na",
                "ppe_gloves": "yes",
                "ppe_respiratory": "yes" if permit_type.code in ("CONFINED", "LINE-BREAK") else "na",
                "ppe_ear": "yes" if permit_type.code in ("HOT-WORK", "GENERAL") else "na",
                "ppe_eye": "yes",
                "ppe_other": "yes" if permit_type.code in ("CONFINED", "ELECTRICAL") else "na",
                "electrical_clearance": "yes" if permit_type.code == "ELECTRICAL" else "na",
                "ventilation_adequate": "yes",
                "fire_extinguishers": "yes" if permit_type.code == "HOT-WORK" else "na",
                "grinder_guard": "yes" if permit_type.code == "HOT-WORK" else "na",
                "welding_elcb": "yes" if permit_type.code == "HOT-WORK" else "na",
                "gas_cutting_fba": "yes" if permit_type.code == "HOT-WORK" else "na",
                "gas_hosepipe": "yes" if permit_type.code == "HOT-WORK" else "na",
                "cylinder_key": "yes" if permit_type.code == "HOT-WORK" else "na",
                "esi_insurance": "yes",
            }

            gas_test_value = (
                round(2.0 + (index % 5) * 0.7, 2)
                if checklist_yes["gas_test"] == "yes"
                else None
            )

            permit = Permit(
                permit_type=permit_type,
                status=status,
                requester_user=user,
                requester_name=user.get_full_name() or user.username,
                plant=plant,
                zone=zone,
                location=location,
                sublocation=sublocation,
                department=department,
                job_description=work_description,
                contractor_company=contractor_companies[index % len(contractor_companies)],
                reporting_engineer=approver.get_full_name() or approver.username,
                supervisor_name=f"Supervisor {index + 1:03d}",
                contact_number=f"98{(10000000 + index):08d}",
                start_date=start_dt,
                end_date=end_dt,
                priority=priority,
                hazard_risk_level=risk,
                hazards=hazards,
                safety_measures=safety_measures,
                gas_test_value=gas_test_value,
                approver=approver if status in ("approved", "active", "closed") else None,
                security_checked_in=status in ("active", "closed"),
                security_checkin_time=(
                    min(start_dt + timedelta(minutes=30), timezone.now())
                    if status in ("active", "closed")
                    else None
                ),
                security_comments=(
                    "Security verification completed."
                    if status in ("active", "closed")
                    else None
                ),
                security_esi_insurance="Verified"
                if status in ("active", "closed")
                else None,
                employees_count=5 + (index % 16)
                if status in ("active", "closed")
                else 0,
                **checklist_yes,
                ppe_other_specify=(
                    "Face shield and fall arrest lanyard"
                    if permit_type.code in ("HEIGHT", "HOT-WORK")
                    else None
                ),
                fire_extinguishers_details=(
                    "ABC dry powder extinguisher available at work location."
                    if permit_type.code == "HOT-WORK"
                    else None
                ),
            )

            if status == "rejected":
                permit.rejection_reason = (
                    "Required safety controls were incomplete during review."
                )

            if status == "closed":
                permit.close_out_notes = "Work completed and area restored safely."

            permit.full_clean()
            permit.save()

            # Add contractors to every permit so the permit detail page has
            # realistic manpower/contractor data.
            contractor_count = 2 + (index % 3)
            for contractor_index in range(contractor_count):
                contractor_name = (
                    f"Contractor Worker {index + 1:03d}-{contractor_index + 1:02d}"
                )
                PermitContractor.objects.create(
                    permit=permit,
                    name=contractor_name,
                    trade=trades[
                        (index + contractor_index) % len(trades)
                    ],
                    id_number=f"CTR-{index + 1:04d}-{contractor_index + 1:02d}",
                    esi_number=f"ESI-{index + 1:06d}{contractor_index + 1:02d}",
                    contact_number=f"97{(20000000 + index * 10 + contractor_index):08d}",
                )

            # Create an approval trail matching the final status.
            PermitApprovalLog.objects.create(
                permit=permit,
                action="created",
                performed_by=user,
                comments="Permit created in Permit Management.",
                from_status=None,
                to_status="draft",
            )

            if status != "draft":
                PermitApprovalLog.objects.create(
                    permit=permit,
                    action="submitted",
                    performed_by=user,
                    comments="Permit submitted for EHS approval.",
                    from_status="draft",
                    to_status="pending",
                )

            if status == "approved":
                PermitApprovalLog.objects.create(
                    permit=permit,
                    action="approved",
                    performed_by=approver,
                    comments="Permit approved after safety control review.",
                    from_status="pending",
                    to_status="approved",
                )

            elif status == "active":
                PermitApprovalLog.objects.create(
                    permit=permit,
                    action="approved",
                    performed_by=approver,
                    comments="Permit approved after safety control review.",
                    from_status="pending",
                    to_status="approved",
                )
                PermitApprovalLog.objects.create(
                    permit=permit,
                    action="activated",
                    performed_by=approver,
                    comments="Permit activated for execution.",
                    from_status="approved",
                    to_status="active",
                )

            elif status == "closed":
                PermitApprovalLog.objects.create(
                    permit=permit,
                    action="approved",
                    performed_by=approver,
                    comments="Permit approved after safety control review.",
                    from_status="pending",
                    to_status="approved",
                )
                PermitApprovalLog.objects.create(
                    permit=permit,
                    action="activated",
                    performed_by=approver,
                    comments="Permit activated for execution.",
                    from_status="approved",
                    to_status="active",
                )
                PermitApprovalLog.objects.create(
                    permit=permit,
                    action="closed",
                    performed_by=approver,
                    comments="Permit closed after completion of work.",
                    from_status="active",
                    to_status="closed",
                )

            elif status == "rejected":
                PermitApprovalLog.objects.create(
                    permit=permit,
                    action="rejected",
                    performed_by=approver,
                    comments="Permit rejected because required controls were incomplete.",
                    from_status="pending",
                    to_status="rejected",
                )

            # Create a closure only for permits whose final status is closed.
            if status == "closed":
                actual_end = min(
                    end_dt,
                    timezone.now() - timedelta(hours=index % 6),
                )
                if actual_end < start_dt:
                    actual_end = start_dt

                work_status = [
                    "completed",
                    "completed_with_issues",
                    "partially_completed",
                ][index % 3]

                PermitClosure.objects.create(
                    permit=permit,
                    actual_end_date=actual_end,
                    work_status=work_status,
                    work_summary=(
                        "Work completed as planned. Equipment and work area "
                        "were inspected before permit closure."
                    ),
                    issues_encountered=(
                        "Minor housekeeping observations corrected before closure."
                        if work_status == "completed_with_issues"
                        else ""
                    ),
                    area_inspected=True,
                    fire_watch_completed=permit_type.code == "HOT-WORK",
                    equipment_isolated=True,
                    hazards_removed=True,
                    barriers_removed=True,
                    no_incidents=True,
                    area_clean=True,
                    systems_operational=True,
                    contractor_signature=(
                        f"Contractor Supervisor - {index + 1:03d}"
                    ),
                    safety_signature=(
                        f"EHS Officer - {approver.get_full_name() or approver.username}"
                    ),
                    closure_comments="Permit closure verification completed.",
                    closed_by=approver,
                )

            # Add extension requests to selected permits. New end dates remain
            # within the current date range and are always after original end.
            if index % 10 == 0 and end_dt < timezone.now():
                original_end = end_dt
                proposed_end = min(
                    original_end + timedelta(hours=8),
                    timezone.now(),
                )

                if proposed_end > original_end:
                    extension_status = (
                        "approved" if index % 20 == 0 else "rejected"
                    )

                    PermitExtension.objects.create(
                        permit=permit,
                        requested_by=user,
                        original_end_date=original_end,
                        new_end_date=proposed_end,
                        reason=(
                            "Additional time required to complete the maintenance "
                            "activity safely."
                        ),
                        status=extension_status,
                        reviewed_by=approver,
                        review_comments=(
                            "Extension approved after review."
                            if extension_status == "approved"
                            else "Extension rejected; work to be completed within original window."
                        ),
                        reviewed_at=timezone.now(),
                    )

            # PermitAttachment is optional, but realistic permit records benefit
            # from a supporting document. Use a small PDF placeholder.
            attachment_content = (
                b"%PDF-1.4\n"
                b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
                b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
                b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Contents 4 0 R >>endobj\n"
                b"4 0 obj<< /Length 49 >>stream\n"
                b"BT /F1 12 Tf 72 720 Td (Demo Permit Attachment) Tj ET\n"
                b"endstream endobj\n"
                b"xref\n0 5\n0000000000 65535 f \n"
                b"trailer<< /Size 5 /Root 1 0 R >>\n"
                b"startxref\n0\n%%EOF"
            )

            attachment = PermitAttachment(
                permit=permit,
                original_filename=f"permit_attachment_{permit.id}.pdf",
                description="Demo permit supporting document.",
                uploaded_by=user,
            )
            attachment.file.save(
                f"permit_attachment_{permit.id}.pdf",
                ContentFile(attachment_content),
                save=False,
            )
            attachment.save()

            created += 1

            if created % 25 == 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created {created}/{count} permits..."
                    )
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Permit demo data completed. Created: {created}, Skipped: {skipped}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Permit records: {Permit.objects.count()}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Permit contractors: {PermitContractor.objects.count()}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Approval logs: {PermitApprovalLog.objects.count()}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Closures: {PermitClosure.objects.count()}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Extensions: {PermitExtension.objects.count()}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Attachments: {PermitAttachment.objects.count()}"
            )
        )
