# ============================================================
## run to generate data:
## python manage.py demo_data_training
## Or explicitly for related to employees available:
## python manage.py demo_data_training --count 13 --records 100
# ============================================================
# ============================================================
# Training Demo Data Seeder
# Creates realistic demo data using existing users and
# existing organization assignments.
# ============================================================



import datetime
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.organizations.models import Plant, Zone, Location, SubLocation, Department

# Adjust this import only if your Training models are stored in a different app.
from apps.training.models import (
    TrainingTopic,
    TrainingRequirement,
    TrainingSession,
    TrainingParticipant,
    TrainingRecord,
    TrainingNotification,
)


class Command(BaseCommand):
    help = "Create current financial year demo data for Training Management."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of training sessions to create (default: 100).",
        )

    def current_fy(self):
        today = timezone.localdate()
        start = datetime.date(
            today.year if today.month >= 4 else today.year - 1,
            4,
            1,
        )
        return start, today

    def demo_file(self, name, content):
        """Create a small demo document for training attachments/certificates."""
        return ContentFile(
            content.encode("utf-8"),
            name=f"{name.lower().replace(' ', '_')}.pdf",
        )

    def handle(self, *args, **options):
        count = options["count"]
        if count < 1:
            raise CommandError("--count must be at least 1.")

        fy_start, fy_end = self.current_fy()
        User = get_user_model()

        users = list(User.objects.filter(is_active=True).order_by("id"))
        plants = list(Plant.objects.all().order_by("id"))
        zones = list(Zone.objects.all().order_by("id"))
        locations = list(Location.objects.all().order_by("id"))
        sublocations = list(SubLocation.objects.all().order_by("id"))
        departments = list(Department.objects.all().order_by("id"))

        if not users:
            raise CommandError("No active users found. Please create users first.")
        if not plants:
            raise CommandError("No Plant records found. Please create organization master data first.")
        if not locations:
            raise CommandError("No Location records found. Please create organization master data first.")

        # Use only locations that have a valid Zone -> Plant relationship.
        valid_locations = [
            location
            for location in locations
            if getattr(location, "zone_id", None)
            and getattr(location.zone, "plant_id", None)
        ]
        if not valid_locations:
            raise CommandError(
                "No valid Location -> Zone -> Plant hierarchy was found."
            )

        # Prefer sublocations belonging to the selected location.
        self.stdout.write(
            f"Training Management demo data: {fy_start} to {fy_end}"
        )
        self.stdout.write(
            f"Using {len(users)} existing users, {len(plants)} existing plants "
            f"and {len(valid_locations)} valid organization locations."
        )

        with transaction.atomic():
            # ============================================================
            # 1. TRAINING TOPICS
            # ============================================================
            topic_seed = [
                ("Safety Induction", "IND-01", "INDUCTION", 365, 70, True),
                ("EHS Refresher Training", "REF-01", "REFRESHER", 365, 70, True),
                ("Fire Safety", "FIRE-01", "FIRE_SAFETY", 365, 70, True),
                ("PPE Usage", "PPE-01", "PPE", 365, 70, True),
                ("Emergency Response", "EMR-01", "EMERGENCY_RESPONSE", 365, 70, True),
                ("Hazard Awareness", "HAZ-01", "HAZARD_AWARENESS", 365, 70, True),
                ("First Aid", "FA-01", "FIRST_AID", 730, 75, False),
                ("Chemical Handling", "CHM-01", "CHEMICAL_HANDLING", 365, 70, True),
                ("Machine Safety", "MAC-01", "MACHINE_SAFETY", 365, 70, True),
                ("Work at Height", "WAH-01", "WORK_AT_HEIGHT", 365, 75, True),
                ("Electrical Safety", "ELEC-01", "ELECTRICAL_SAFETY", 365, 75, True),
                ("Environmental Awareness", "ENV-01", "ENVIRONMENTAL", 365, 60, False),
                ("Toolbox Talk", "TBT-01", "TOOLBOX_TALK", 180, 60, False),
                ("Mock Emergency Drill", "DRILL-01", "EMERGENCY_RESPONSE", 365, 70, False),
            ]

            topics = []
            for index, (name, code, category, validity, passing, mandatory) in enumerate(topic_seed):
                topic = TrainingTopic.objects.filter(code=code).first()

                if not topic:
                    topic = TrainingTopic.objects.create(
                        name=name,
                        code=code,
                        description=f"Demo training topic for {name}.",
                        category=category,
                        validity_period_days=validity,
                        passing_score=passing,
                        is_mandatory=mandatory,
                        is_active=True,
                        created_by=users[index % len(users)],
                    )

                topics.append(topic)

            # ============================================================
            # 2. TRAINING REQUIREMENTS
            # ============================================================
            requirements = []

            applicable_patterns = ["ALL", "PLANT", "DEPARTMENT", "ROLE"]

            for index, topic in enumerate(topics):
                applicable_to = applicable_patterns[index % len(applicable_patterns)]

                requirement = (
                    TrainingRequirement.objects
                    .filter(topic=topic, applicable_to=applicable_to)
                    .first()
                )

                if not requirement:
                    kwargs = {
                        "topic": topic,
                        "applicable_to": applicable_to,
                        "due_within_days": 15 + (index % 45),
                        "created_by": users[index % len(users)],
                    }

                    if applicable_to == "PLANT":
                        kwargs["plant"] = plants[index % len(plants)]

                    elif applicable_to == "DEPARTMENT":
                        if departments:
                            kwargs["department"] = departments[index % len(departments)]
                        else:
                            kwargs["applicable_to"] = "ALL"

                    elif applicable_to == "ROLE":
                        role = getattr(users[index % len(users)], "role", None)
                        if role:
                            kwargs["role"] = role
                        else:
                            kwargs["applicable_to"] = "ALL"

                    requirement = TrainingRequirement(**kwargs)
                    requirement.full_clean()
                    requirement.save()

                requirements.append(requirement)

            # ============================================================
            # 3. TRAINING SESSIONS + PARTICIPANTS + RECORDS + NOTIFICATIONS
            # ============================================================
            session_statuses = [
                "SCHEDULED",
                "ONGOING",
                "COMPLETED",
                "CANCELLED",
            ]

            training_modes = [
                "CLASSROOM",
                "TOOLBOX_TALK",
                "OJT",
                "ONLINE",
                "MOCK_DRILL",
                "SEMINAR",
            ]

            attendance_statuses = [
                "INVITED",
                "PRESENT",
                "ABSENT",
                "PARTIAL",
            ]

            record_statuses = [
                "ACTIVE",
                "EXPIRED",
                "REVOKED",
            ]

            notification_types = [
                "SESSION_SCHEDULED",
                "SESSION_REMINDER",
                "SESSION_CANCELLED",
                "ATTENDANCE_MARKED",
                "CERTIFICATE_ISSUED",
                "EXPIRY_ALERT_60",
                "EXPIRY_ALERT_30",
                "EXPIRY_ALERT_7",
                "CERTIFICATE_EXPIRED",
                "TRAINING_OVERDUE",
            ]

            created_sessions = 0
            created_participants = 0
            created_records = 0

            for index in range(count):
                topic = topics[index % len(topics)]
                requirement = requirements[index % len(requirements)]
                creator = users[index % len(users)]

                location = valid_locations[index % len(valid_locations)]
                zone = location.zone
                plant = zone.plant

                # Try to select a sublocation belonging to this location.
                location_sublocations = [
                    sub
                    for sub in sublocations
                    if getattr(sub, "location_id", None) == location.id
                ]
                sublocation = (
                    location_sublocations[index % len(location_sublocations)]
                    if location_sublocations
                    else None
                )

                # Keep all demo dates inside the current financial year.
                fy_days = max((fy_end - fy_start).days, 0)
                scheduled_date = fy_start + timedelta(
                    days=(index * 3) % (fy_days + 1)
                )

                # For completed sessions, never use a future actual date.
                status = session_statuses[index % len(session_statuses)]

                if status in ["COMPLETED", "CANCELLED"]:
                    actual_date = scheduled_date
                else:
                    actual_date = None

                session = TrainingSession(
                    topic=topic,
                    training_mode=training_modes[index % len(training_modes)],
                    plant=plant,
                    zone=zone,
                    location=location,
                    sublocation=sublocation,
                    venue_details=(
                        "Training Room A"
                        if index % 3 == 0
                        else "Conference Hall"
                        if index % 3 == 1
                        else "Shop Floor Training Area"
                    ),
                    scheduled_date=scheduled_date,
                    scheduled_time=datetime.time(9 + (index % 4), 30),
                    end_time=datetime.time(11 + (index % 4), 30),
                    duration_hours=2.0 + (index % 3) * 0.5,
                    trainer_name=(
                        "EHS Internal Trainer"
                        if index % 3 != 0
                        else "External Safety Consultant"
                    ),
                    trainer_designation=(
                        "EHS Manager"
                        if index % 3 != 0
                        else "Safety Consultant"
                    ),
                    trainer_is_external=(index % 3 == 0),
                    trainer_organization=(
                        "SafeWork Training Consultants"
                        if index % 3 == 0
                        else ""
                    ),
                    agenda=f"Demo agenda covering {topic.name}, practical requirements and assessment.",
                    max_participants=20 + (index % 4) * 5,
                    remarks="Demo training session created for current FY.",
                    status=status,
                    cancelled_reason=(
                        "Trainer unavailable / session rescheduled."
                        if status == "CANCELLED"
                        else ""
                    ),
                    actual_date=actual_date,
                    completion_remarks=(
                        "Training completed successfully with attendance recorded."
                        if status == "COMPLETED"
                        else ""
                    ),
                    attachment=self.demo_file(
                        "Training Material",
                        f"Training Topic: {topic.name}\n"
                        f"Plant: {plant}\n"
                        f"Financial Year: {fy_start.year}-{fy_end.year}",
                    ),
                    created_by=creator,
                )
                session.save()
                created_sessions += 1

                # --------------------------------------------------------
                # Participants
                # --------------------------------------------------------
                # 5 participants per session gives realistic attendance data
                # while respecting unique_together(session, employee).
                participant_count = min(5, len(users))
                selected_users = [
                    users[(index + offset) % len(users)]
                    for offset in range(participant_count)
                ]

                for p_index, employee in enumerate(selected_users):
                    if status == "CANCELLED":
                        attendance = "INVITED"
                    elif status == "SCHEDULED":
                        attendance = "INVITED" if p_index < 4 else "ABSENT"
                    else:
                        attendance = attendance_statuses[
                            (index + p_index) % len(attendance_statuses)
                        ]

                    assessment_score = None
                    passed = None

                    if attendance in ["PRESENT", "PARTIAL"]:
                        if topic.passing_score > 0:
                            # Alternate passing/failing assessments.
                            if (index + p_index) % 5 == 0:
                                assessment_score = max(topic.passing_score - 10, 0)
                            else:
                                assessment_score = min(
                                    95,
                                    topic.passing_score + 10 + ((index + p_index) % 10),
                                )
                        elif attendance == "PRESENT":
                            assessment_score = None

                    marked_by = (
                        creator
                        if attendance != "INVITED"
                        else None
                    )

                    marked_at = (
                        timezone.now()
                        if marked_by
                        else None
                    )

                    participant = TrainingParticipant(
                        session=session,
                        employee=employee,
                        attendance_status=attendance,
                        assessment_score=assessment_score,
                        passed=passed,
                        remarks=(
                            "Attendance recorded."
                            if attendance != "INVITED"
                            else "Employee invited to the session."
                        ),
                        marked_by=marked_by,
                        marked_at=marked_at,
                    )
                    participant.save()
                    created_participants += 1

                    # ----------------------------------------------------
                    # Training Record
                    # ----------------------------------------------------
                    # Only completed sessions with a present participant
                    # receive a certificate-style training record.
                    if status == "COMPLETED" and attendance == "PRESENT":
                        completed_date = scheduled_date

                        # Create a mixture of active, expired and revoked
                        # records while keeping completed_date in current FY.
                        record_status = record_statuses[
                            (index + p_index) % len(record_statuses)
                        ]

                        if record_status == "EXPIRED":
                            # Make the validity date fall before today while
                            # retaining the completed date in the current FY.
                            if topic.validity_period_days >= 180:
                                completed_date = max(
                                    fy_start,
                                    fy_end - timedelta(
                                        days=topic.validity_period_days + 10
                                    ),
                                )
                            else:
                                completed_date = fy_start

                        certificate = TrainingRecord(
                            employee=employee,
                            topic=topic,
                            session=session,
                            completed_date=completed_date,
                            valid_until=(
                                completed_date
                                + timedelta(days=topic.validity_period_days)
                            ),
                            status=record_status,
                            added_manually=(index % 4 == 0),
                            remarks=(
                                "External / manually uploaded training record."
                                if index % 4 == 0
                                else "Training certificate generated from completed session."
                            ),
                            revoked_reason=(
                                "Training record revoked for demonstration."
                                if record_status == "REVOKED"
                                else ""
                            ),
                            created_by=creator,
                        )
                        certificate.certificate_file = self.demo_file(
                            "Training Certificate",
                            f"Employee: {employee.get_full_name()}\n"
                            f"Topic: {topic.name}\n"
                            f"Completed: {completed_date}\n"
                            f"Status: {record_status}",
                        )
                        certificate.save()
                        created_records += 1

                        notification_type = (
                            "CERTIFICATE_ISSUED"
                            if record_status == "ACTIVE"
                            else "CERTIFICATE_EXPIRED"
                            if record_status == "EXPIRED"
                            else "ATTENDANCE_MARKED"
                        )

                        TrainingNotification.objects.create(
                            recipient=employee,
                            session=session,
                            training_record=certificate,
                            notification_type=notification_type,
                            title=f"Training Certificate - {topic.name}",
                            message=(
                                f"Training record for {topic.name} has been "
                                f"created with status {record_status}."
                            ),
                            is_read=(p_index % 2 == 0),
                            read_at=timezone.now() if p_index % 2 == 0 else None,
                        )

                # --------------------------------------------------------
                # Session notifications
                # --------------------------------------------------------
                recipient = users[(index + 1) % len(users)]

                if status == "SCHEDULED":
                    notification_type = "SESSION_SCHEDULED"
                elif status == "CANCELLED":
                    notification_type = "SESSION_CANCELLED"
                elif status == "COMPLETED":
                    notification_type = "ATTENDANCE_MARKED"
                else:
                    notification_type = "SESSION_REMINDER"

                TrainingNotification.objects.create(
                    recipient=recipient,
                    session=session,
                    notification_type=notification_type,
                    title=f"Training Session - {topic.name}",
                    message=(
                        f"{topic.name} training session is {status.lower()} "
                        f"for {plant}."
                    ),
                    is_read=(index % 3 == 0),
                    read_at=timezone.now() if index % 3 == 0 else None,
                )

                if (index + 1) % 25 == 0:
                    self.stdout.write(
                        f"Created {index + 1}/{count} training sessions..."
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "Training Management demo data completed successfully."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Training sessions created: {created_sessions}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Training participants created: {created_participants}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Training records created: {created_records}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Financial year: {fy_start} to {fy_end}"
            )
        )
