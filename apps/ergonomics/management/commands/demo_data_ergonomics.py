# ============================================================
# Ergonomics Demo Data Seeder
# Run:
#   python manage.py demo_data_ergonomics
#   python manage.py demo_data_ergonomics --count 10
# ============================================================

import datetime
from decimal import Decimal
from itertools import cycle

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Department, Location, Plant, Zone
from apps.ergonomics.models import (
    ErgonomicAssessmentMethod,
    ErgonomicAssessment,
    ErgonomicRiskFactor,
    RULAAssessment,
    REBAAssessment,
    NIOSHLiftingAssessment,
    OWASAssessment,
    OCRAAssessment,
    StrainIndexAssessment,
    SnookCirielloAssessment,
    ErgonomicControl,
    ErgonomicCorrectiveAction,
    ErgonomicReassessment,
    ErgonomicObservation,
    MSDDiscomfort,
    ErgonomicJobMapping,
    ErgonomicAssessmentSchedule,
    ErgonomicAuditLog,
)


class Command(BaseCommand):
    help = "Create current financial year demo data for the Ergonomics module."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of ergonomic assessment transactions to create (default: 100).",
        )

    def make_file(self, name, content=b"Ergonomics demo evidence"):
        return ContentFile(content, name=name)

    def date_in_fy(self, fy_start, today, index):
        span = max((today - fy_start).days, 0)
        return fy_start + datetime.timedelta(days=(index * 3) % (span + 1))

    def handle(self, *args, **options):
        count = options["count"]
        if count < 1:
            raise CommandError("--count must be at least 1.")

        today = timezone.localdate()
        fy_start = datetime.date(
            today.year if today.month >= 4 else today.year - 1, 4, 1
        )

        users = list(User.objects.filter(is_active=True).order_by("id"))
        plants = list(Plant.objects.all().order_by("id"))
        departments = list(Department.objects.all().order_by("id"))
        locations = list(Location.objects.select_related("zone__plant").order_by("id"))
        zones = list(Zone.objects.select_related("plant").order_by("id"))

        valid_locations = [
            loc for loc in locations
            if getattr(loc, "zone_id", None)
            and getattr(loc.zone, "plant_id", None)
        ]
        if not users:
            raise CommandError("No active users found.")
        if not plants:
            raise CommandError("No Plant records found.")
        if not departments:
            raise CommandError("No Department records found.")

        methods_seed = [
            ("RULA", "RULA", "Rapid Upper Limb Assessment"),
            ("REBA", "REBA", "Rapid Entire Body Assessment"),
            ("NIOSH Lifting Equation", "NIOSH", "NIOSH Lifting Equation"),
            ("OWAS", "OWAS", "Ovako Working Posture Analysing System"),
            ("OCRA", "OCRA", "Occupational Repetitive Actions"),
            ("Strain Index", "STRAIN_INDEX", "Moore and Garg Strain Index"),
            ("Snook & Ciriello", "SNOOK_CIRIELLO", "Snook and Ciriello psychophysical assessment"),
            ("Other Ergonomic Assessment", "OTHER", "Other ergonomic assessment method"),
        ]
        methods = []
        creator_cycle = cycle(users)
        for name, code, description in methods_seed:
            method = ErgonomicAssessmentMethod.objects.filter(code=code).first()
            if not method:
                method = ErgonomicAssessmentMethod.objects.create(
                    name=name,
                    code=code,
                    description=description,
                    is_active=True,
                    created_by=next(creator_cycle),
                )
            methods.append(method)

        tasks = [
            ("Assembly Operator", "Component Assembly"),
            ("Material Handler", "Manual Material Handling"),
            ("Machine Operator", "Machine Loading and Unloading"),
            ("Packing Operator", "Packing and Palletizing"),
            ("Quality Inspector", "Inspection at Workstation"),
            ("Maintenance Technician", "Equipment Maintenance"),
            ("Warehouse Operator", "Material Picking"),
            ("Production Operator", "Repetitive Production Task"),
            ("Office Operator", "Computer Workstation"),
            ("Utility Worker", "Cleaning and Utility Work"),
        ]
        shifts = ["General", "A Shift", "B Shift", "C Shift"]

        created = {
            "assessments": 0,
            "risk_factors": 0,
            "method_scores": 0,
            "controls": 0,
            "actions": 0,
            "reassessments": 0,
            "observations": 0,
            "msd": 0,
            "mappings": 0,
            "schedules": 0,
            "audit_logs": 0,
        }

        with transaction.atomic():
            for i in range(count):
                user = users[i % len(users)]
                assessor = users[(i + 1) % len(users)]
                plant = plants[i % len(plants)]
                department = departments[i % len(departments)]

                location = valid_locations[i % len(valid_locations)] if valid_locations else None
                zone = location.zone if location else (
                    zones[i % len(zones)] if zones else None
                )

                job, task = tasks[i % len(tasks)]
                method = methods[i % len(methods)]
                assessment_date = self.date_in_fy(fy_start, today, i)

                assessment_type = [
                    "INITIAL", "PERIODIC", "REASSESSMENT",
                    "POST_INCIDENT", "POST_MSD", "PROCESS_CHANGE",
                    "CA_VERIFICATION",
                ][i % 7]

                assessment = ErgonomicAssessment(
                    plant=plant,
                    department=department,
                    zone=zone,
                    location=location,
                    area=f"Area {((i % 10) + 1)}",
                    job_role=job,
                    task=task,
                    worker=user,
                    workers_exposed=5 + (i % 26),
                    shift=shifts[i % len(shifts)],
                    assessment_date=assessment_date,
                    assessor=assessor,
                    task_duration=f"{30 + (i % 7) * 15} minutes/cycle",
                    frequency=f"{2 + (i % 6)} cycles/hour",
                    exposure_duration=f"{2 + (i % 7)} hours/shift",
                    assessment_type=assessment_type,
                    assessment_method=method,
                    task_description=f"Ergonomic assessment of {task} performed by {job}.",
                    next_assessment_date=(
                        today + datetime.timedelta(days=30 + (i % 6) * 30)
                    ),
                    created_by=user,
                    updated_by=assessor,
                )
                assessment.save()
                created["assessments"] += 1

                # Risk-factor master data used by the assessment.
                risk_profiles = [
                    ("NORMAL", "LOW", False, False, False, False),
                    ("SLIGHT", "MODERATE", True, False, False, False),
                    ("AWKWARD", "HIGH", True, True, False, False),
                    ("HIGHLY_AWKWARD", "VERY_HIGH", True, True, True, True),
                ]
                posture, force, bending, twisting, reaching, overhead = risk_profiles[i % 4]
                ErgonomicRiskFactor.objects.create(
                    assessment=assessment,
                    neck_posture=posture,
                    shoulder_posture=posture,
                    elbow_posture=posture,
                    wrist_posture=posture,
                    back_posture=posture,
                    hip_posture=posture,
                    knee_posture=posture,
                    ankle_posture=posture,
                    bending=bending,
                    twisting=twisting,
                    reaching=reaching,
                    overhead_work=overhead,
                    kneeling=(i % 5 == 0),
                    squatting=(i % 6 == 0),
                    static_posture=(i % 4 == 1),
                    force_required=force,
                    push_force_n=Decimal(str(20 + (i % 6) * 10)),
                    pull_force_n=Decimal(str(25 + (i % 5) * 10)),
                    grip_force_n=Decimal(str(10 + (i % 5) * 5)),
                    lift_force_kg=Decimal(str(5 + (i % 8) * 3)),
                    repetitions_per_minute=Decimal(str(2 + (i % 8))),
                    repetitions_per_hour=Decimal(str(20 + (i % 8) * 10)),
                    cycle_time_seconds=Decimal(str(30 + (i % 8) * 10)),
                    task_duration_minutes=Decimal(str(30 + (i % 6) * 30)),
                    cycles_per_shift=40 + (i % 8) * 20,
                    object_weight_kg=Decimal(str(5 + (i % 8) * 2)),
                    lifting_frequency=Decimal(str(1 + (i % 6))),
                    lifting_height_cm=Decimal(str(50 + (i % 6) * 10)),
                    starting_height_cm=Decimal(str(20 + (i % 5) * 5)),
                    ending_height_cm=Decimal(str(80 + (i % 5) * 10)),
                    horizontal_reach_cm=Decimal(str(25 + (i % 6) * 5)),
                    carrying_distance_m=Decimal(str(2 + (i % 6))),
                    push_distance_m=Decimal(str(1 + (i % 5))),
                    pull_distance_m=Decimal(str(1 + (i % 5))),
                    handling_type=["FLOOR", "WAIST", "SHOULDER", "OVERHEAD"][i % 4],
                    handling_person="TWO" if i % 5 == 0 else "ONE",
                    mechanical_assistance_available=(i % 3 == 0),
                    hand_arm_vibration=(i % 4 == 0),
                    whole_body_vibration=(i % 7 == 0),
                    vibration_exposure_duration="30-60 minutes" if i % 4 == 0 else "",
                    vibration_tool_used="Demo power tool" if i % 4 == 0 else "",
                    work_surface_height_cm=Decimal(str(70 + (i % 5) * 5)),
                    chair_height_cm=Decimal(str(40 + (i % 4) * 3)),
                    monitor_height_cm=Decimal(str(110 + (i % 5) * 5)),
                    keyboard_position="Neutral wrist position",
                    mouse_position="Within comfortable reach",
                    leg_room_adequate=(i % 4 != 1),
                    reach_distance_cm=Decimal(str(35 + (i % 5) * 5)),
                    lighting_adequate=(i % 5 != 2),
                    workspace_adequate=(i % 4 != 2),
                    adjustable_workstation_available=(i % 3 == 0),
                    workstation_notes="Demo workstation observation.",
                )
                created["risk_factors"] += 1

                # Create the method-specific calculation record. The model save()
                # calculates score/risk/action values on the parent assessment.
                code = method.code
                if code == "RULA":
                    child = RULAAssessment(
                        assessment=assessment,
                        upper_arm_score=1 + (i % 6),
                        lower_arm_score=1 + (i % 3),
                        wrist_score=1 + (i % 4),
                        wrist_twist_score=1 + (i % 2),
                        neck_score=1 + (i % 6),
                        trunk_score=1 + (i % 6),
                        leg_score=1 + (i % 2),
                        muscle_use_score=i % 2,
                        force_load_score=i % 4,
                    )
                elif code == "REBA":
                    child = REBAAssessment(
                        assessment=assessment,
                        trunk_score=1 + (i % 5),
                        neck_score=1 + (i % 3),
                        legs_score=1 + (i % 4),
                        upper_arm_score=1 + (i % 6),
                        lower_arm_score=1 + (i % 2),
                        wrist_score=1 + (i % 3),
                        load_force_score=i % 4,
                        coupling_score=i % 4,
                        activity_score=i % 4,
                    )
                elif code == "NIOSH":
                    child = NIOSHLiftingAssessment(
                        assessment=assessment,
                        load_weight=Decimal(str(5 + (i % 8) * 2)),
                        horizontal_location=Decimal(str(25 + (i % 6) * 5)),
                        vertical_location=Decimal(str(50 + (i % 6) * 5)),
                        vertical_travel_distance=Decimal(str(25 + (i % 5) * 5)),
                        asymmetry_angle=Decimal(str((i % 6) * 15)),
                        frequency_lifts_per_minute=Decimal(str(0.2 + (i % 5) * 0.2)),
                        duration_hours=Decimal(str(1 + (i % 5))),
                        coupling=["GOOD", "FAIR", "POOR"][i % 3],
                    )
                elif code == "OWAS":
                    child = OWASAssessment(
                        assessment=assessment,
                        back_score=1 + (i % 4),
                        arms_score=1 + (i % 3),
                        legs_score=1 + (i % 6),
                        load_score=1 + (i % 3),
                    )
                elif code == "OCRA":
                    child = OCRAAssessment(
                        assessment=assessment,
                        actual_actions=5000 + (i % 10) * 500,
                        constant_frequency=Decimal("30"),
                        posture_multiplier=Decimal(["1.00", "0.80", "0.60", "0.40"][i % 4]),
                        force_multiplier=Decimal(["1.00", "0.85", "0.65", "0.45"][i % 4]),
                        repetitiveness_multiplier=Decimal(["1.00", "0.80", "0.60", "0.40"][i % 4]),
                        additional_multiplier=Decimal("1.00"),
                        recovery_multiplier=Decimal(["1.00", "0.85", "0.70", "0.50"][i % 4]),
                        duration_multiplier=Decimal(["1.00", "0.90", "0.75", "0.60"][i % 4]),
                    )
                elif code == "STRAIN_INDEX":
                    child = StrainIndexAssessment(
                        assessment=assessment,
                        intensity_of_exertion=["LIGHT", "SOMEWHAT_HARD", "HARD", "VERY_HARD", "NEAR_MAXIMAL"][i % 5],
                        duration_of_exertion=["<10", "10-29", "30-49", "50-79", ">=80"][i % 5],
                        efforts_per_minute=["<4", "4-8", "9-14", "15-19", ">=20"][i % 5],
                        hand_wrist_posture=["VERY_GOOD", "GOOD", "FAIR", "BAD", "VERY_BAD"][i % 5],
                        speed_of_work=["VERY_SLOW", "SLOW", "FAIR", "FAST", "VERY_FAST"][i % 5],
                        duration_per_day_hours=["<1", "1-2", "2-4", "4-8", ">=8"][i % 5],
                        daily_duration_hours=["<1", "1-2", "2-4", "4-8", ">=8"][i % 5],
                        efforts_per_hour=["0-1", "2-3", "4-5", "6-7", ">=8"][i % 5],
                    )
                elif code == "SNOOK_CIRIELLO":
                    child = SnookCirielloAssessment(
                        assessment=assessment,
                        task_type=["LIFT", "LOWER", "PUSH", "PULL", "CARRY"][i % 5],
                        gender=["MALE", "FEMALE"][i % 2],
                        position=["FLOOR", "KNUCKLE", "SHOULDER", "CLOSE", "MEDIUM", "FAR"][i % 6],
                        percentile=[10, 25, 50, 75, 90][i % 5],
                        actual_load=Decimal(str(5 + (i % 8) * 2)),
                    )
                else:
                    # OTHER has no method-specific score model.
                    assessment.score = Decimal(str(1 + (i % 10)))
                    assessment.risk_level = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"][i % 4]
                    assessment.action_level = assessment.risk_level
                    assessment.recommended_action = "Review ergonomic controls and monitor the task."
                    assessment.save(update_fields=[
                        "score", "risk_level", "action_level",
                        "recommended_action", "updated_at",
                    ])
                    child = None

                if child is not None:
                    child.save()
                    created["method_scores"] += 1

                # Controls: implementation varies by risk profile.
                control_type = [
                    "ELIMINATION", "SUBSTITUTION", "ENGINEERING",
                    "ADMINISTRATIVE", "PPE"
                ][i % 5]
                control = ErgonomicControl.objects.create(
                    assessment=assessment,
                    control_type=control_type,
                    description=f"Demo {control_type.lower()} control for {task}.",
                    implemented=(i % 3 != 1),
                    implementation_date=assessment_date if i % 3 != 1 else None,
                    created_by=assessor,
                )
                created["controls"] += 1

                # Corrective-action statuses drive the parent assessment status.
                action_pattern = i % 6
                if action_pattern == 0:
                    action_status = "CLOSED"
                elif action_pattern == 1:
                    action_status = "COMPLETED"
                elif action_pattern == 2:
                    action_status = "PENDING_VERIFICATION"
                elif action_pattern == 3:
                    action_status = "IN_PROGRESS"
                elif action_pattern == 4:
                    action_status = "REJECTED"
                else:
                    action_status = "OPEN"

                action = ErgonomicCorrectiveAction(
                    assessment=assessment,
                    action_description=f"Corrective action for {task}: improve ergonomic exposure controls.",
                    root_cause="Demo ergonomic risk identified during assessment.",
                    control_type=control_type,
                    responsible_person=users[(i + 2) % len(users)],
                    department=department,
                    priority=["LOW", "MEDIUM", "HIGH", "VERY_HIGH"][i % 4],
                    target_date=(
                        today - datetime.timedelta(days=5)
                        if action_status == "OVERDUE"
                        else assessment_date + datetime.timedelta(days=15 + (i % 30))
                    ),
                    status=action_status,
                    remarks="Demo corrective action.",
                    created_by=assessor,
                )

                if action_status == "CLOSED":
                    action.evidence = self.make_file(
                        f"ergonomic_action_evidence_{i + 1:04d}.txt"
                    )
                    action.verified_by = users[(i + 3) % len(users)]
                    action.verification = "Control implementation verified during demo closure."
                    action.verification_date = today
                    action.completion_date = assessment_date
                elif action_status == "COMPLETED":
                    action.completion_date = assessment_date
                    action.remarks = "Action completed and awaiting verification."
                elif action_status == "PENDING_VERIFICATION":
                    action.completion_date = assessment_date
                elif action_status == "REJECTED":
                    action.rejection_remark = "Demo verification rejected; corrective action requires revision."
                    action.rejected_by = users[(i + 3) % len(users)]
                    action.rejected_at = timezone.now()

                action.save()
                created["actions"] += 1

                assessment.refresh_status(save=True)

                # Reassessment for completed/closed corrective action cases.
                if action_status in {"CLOSED", "COMPLETED"} and assessment.score is not None:
                    previous_score = Decimal(str(assessment.score))
                    new_score = max(Decimal("0.10"), previous_score * Decimal("0.75"))
                    reassessment = ErgonomicReassessment.objects.create(
                        assessment=assessment,
                        corrective_action=action,
                        reassessment_date=min(
                            today,
                            assessment_date + datetime.timedelta(days=30)
                        ),
                        previous_score=previous_score,
                        new_score=new_score,
                        previous_risk=assessment.risk_level or "MEDIUM",
                        control_effectiveness="EFFECTIVE" if action_status == "CLOSED" else "PARTIAL",
                        additional_action_required=(action_status != "CLOSED"),
                        assessor=assessor,
                        remarks="Demo post-control effectiveness reassessment.",
                    )
                    created["reassessments"] += 1

                # Quick observation associated with the assessment.
                if i % 2 == 0:
                    ErgonomicObservation.objects.create(
                        assessment=assessment,
                        plant=plant,
                        department=department,
                        area=f"Area {((i % 10) + 1)}",
                        task=task,
                        worker=user,
                        observation_date=assessment_date,
                        observer=assessor,
                        risk_factor=["Awkward posture", "Manual handling", "Repetition", "Force", "Vibration"][i % 5],
                        observation=f"Demo observation recorded for {task}.",
                        risk_level=["LOW", "MEDIUM", "HIGH", "VERY_HIGH"][i % 4],
                        immediate_action="Discuss safe work practice and ergonomic controls.",
                        remarks="Demo ergonomic observation.",
                    )
                    created["observations"] += 1

                # MSD/discomfort records for selected cases.
                if i % 4 == 0:
                    MSDDiscomfort.objects.create(
                        worker=user,
                        department=department,
                        job=job,
                        task=task,
                        date_reported=assessment_date,
                        body_part=["NECK", "SHOULDER", "LOWER_BACK", "WRIST", "KNEE"][i % 5],
                        discomfort_type=["Pain", "Stiffness", "Fatigue"][i % 3],
                        severity=["LOW", "MEDIUM", "HIGH", "VERY_HIGH"][i % 4],
                        frequency=["Occasional", "Weekly", "Daily"][i % 3],
                        duration=["Short", "Moderate", "Long"][i % 3],
                        work_relatedness=["Possible", "Likely", "Confirmed"][i % 3],
                        medical_referral=(i % 5 == 0),
                        work_restriction=(i % 7 == 0),
                        related_assessment=assessment,
                        remarks="Demo MSD/discomfort record.",
                        created_by=assessor,
                    )
                    created["msd"] += 1

                # Unique employee/job/task mapping.
                mapping, mapping_created = ErgonomicJobMapping.objects.get_or_create(
                    worker=user,
                    job=job,
                    task=task,
                    defaults={
                        "department": department,
                        "assessment": assessment,
                        "is_active": True,
                    },
                )
                if not mapping_created:
                    mapping.assessment = assessment
                    mapping.department = department
                    mapping.is_active = True
                    mapping.save(update_fields=["assessment", "department", "is_active"])
                created["mappings"] += 1

                # Assessment schedule. Past due dates naturally become OVERDUE in save().
                schedule_due = (
                    assessment_date + datetime.timedelta(days=10 + (i % 30))
                )
                reason = [
                    "PERIODIC", "PROCESS_CHANGE", "NEW_EQUIPMENT",
                    "NEW_WORKSTATION", "ERGONOMIC_INCIDENT", "MSD_CASE",
                    "CORRECTIVE_ACTION", "HIGH_RISK",
                ][i % 8]
                schedule_status = (
                    "COMPLETED" if i % 5 == 0 else
                    "CANCELLED" if i % 17 == 0 else
                    "UPCOMING"
                )
                schedule = ErgonomicAssessmentSchedule(
                    assessment=assessment,
                    plant=plant,
                    department=department,
                    job=job,
                    task=task,
                    due_date=schedule_due,
                    reason=reason,
                    status=schedule_status,
                    assigned_to=user,
                    created_by=assessor,
                )
                schedule.save()
                created["schedules"] += 1

                # Append-only audit trail.
                ErgonomicAuditLog.objects.create(
                    user=assessor,
                    timestamp=timezone.now(),
                    action="CREATE",
                    model_name="ErgonomicAssessment",
                    object_id=str(assessment.pk),
                    object_repr=str(assessment),
                    changes={
                        "status": [None, assessment.status],
                        "risk_level": [None, assessment.risk_level],
                    },
                    message="Demo ergonomic assessment created.",
                )
                created["audit_logs"] += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Ergonomics demo data created for FY {fy_start} to {today}."
            )
        )
        self.stdout.write(
            " | ".join(f"{key}: {value}" for key, value in created.items())
        )
        self.stdout.write(
            f"Reused {len(users)} active users, {len(plants)} plants and "
            f"{len(departments)} departments. No users or organization records were created."
        )
