# ============================================================
## run to generate data:
## python manage.py demo_data_toolbox_talk
## Or explicitly for related to employees available:
## python manage.py demo_data_toolbox_talk --count 13 --records 100
# ============================================================
# ============================================================
# Toolbox Talk Demo Data Seeder
# Creates realistic demo data using existing users and
# existing organization assignments.
# ============================================================


from datetime import date, datetime, time, timedelta
from itertools import cycle

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Plant, Zone, Location, SubLocation, Department


class Command(BaseCommand):
    help = "Create current financial year demo data for the Toolbox Talk module."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of Toolbox Talk session plans to create (default: 100).",
        )

    def get_model(self, model_name):
        """Find a Toolbox Talk model without assuming the Django app label."""
        try:
            return apps.get_model("toolbox_talk", model_name)
        except LookupError:
            for model in apps.get_models():
                if model.__name__ == model_name:
                    return model
        raise CommandError(f"Could not find model: {model_name}")

    def add_days(self, start_date, end_date, index):
        span = max((end_date - start_date).days, 0)
        return start_date + timedelta(days=(index * 3) % (span + 1))

    def make_pdf(self, title):
        content = (
            "%PDF-1.4\n"
            "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Contents 4 0 R /Resources << >> >>\nendobj\n"
            "4 0 obj\n<< /Length 0 >>\nstream\n\nendstream\nendobj\n"
            "xref\n0 5\n0000000000 65535 f \n"
            "trailer\n<< /Root 1 0 R /Size 5 >>\nstartxref\n0\n%%EOF\n"
        ).encode("utf-8")
        return ContentFile(content, name=f"{title}.pdf")

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        if count < 1:
            raise CommandError("--count must be at least 1.")

        Category = self.get_model("ToolboxTalkCategory")
        Topic = self.get_model("ToolboxTalkTopic")
        TopicDetail = self.get_model("ToolboxTalkTopicDetail")
        Session = self.get_model("ToolboxTalkSessionPlan")
        Assignment = self.get_model("ToolboxSessionAssignment")
        Conduct = self.get_model("ToolboxTalkConduct")
        ConductDetail = self.get_model("ToolboxTalkConductDetail")
        Attendance = self.get_model("ToolboxTalkAttendance")
        AttendanceDetail = self.get_model("ToolboxTalkAttendanceDetail")
        Evidence = self.get_model("ToolboxTalkEvidence")

        today = timezone.localdate()
        fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
        fy_end = date(today.year + 1 if today.month >= 4 else today.year, 3, 31)

        users = list(User.objects.filter(is_active=True).order_by("id"))
        plants = list(Plant.objects.all().order_by("id"))
        departments = list(Department.objects.all().order_by("id"))
        locations = list(Location.objects.select_related("zone__plant").order_by("id"))
        valid_locations = [
            loc for loc in locations
            if getattr(loc, "zone_id", None)
            and getattr(loc.zone, "plant_id", None)
        ]
        sublocations = list(SubLocation.objects.select_related("location").order_by("id"))

        if not users:
            raise CommandError("No active users found. Create users first.")
        if not departments:
            raise CommandError("No Department records found. Create departments first.")
        if not plants:
            raise CommandError("No Plant records found. Create plants first.")
        if not valid_locations:
            raise CommandError("No valid Location -> Zone -> Plant hierarchy found.")
        if not sublocations:
            self.stdout.write(self.style.WARNING(
                "No SubLocation records found. Sessions will be created without sublocations."
            ))

        creator_cycle = cycle(users)

        category_seed = [
            ("General Safety", "GEN"),
            ("PPE & Personal Safety", "PPE"),
            ("Fire Safety", "FIRE"),
            ("Emergency Response", "EMR"),
            ("Chemical Safety", "CHEM"),
            ("Electrical Safety", "ELEC"),
            ("Work at Height", "WAH"),
            ("Machine Safety", "MACH"),
            ("Material Handling", "MAT"),
            ("Environmental Safety", "ENV"),
        ]

        categories = []
        for name, code in category_seed:
            category = Category.objects.filter(short_code=code).first()
            if not category:
                category = Category.objects.filter(category_name=name).first()
            if not category:
                category = Category.objects.create(
                    category_name=name,
                    short_code=code,
                    description=f"Demo Toolbox Talk category for {name}.",
                    is_active=True,
                    created_by=next(creator_cycle),
                )
            categories.append(category)

        topic_seed = [
            ("PPE Selection and Correct Use", 0),
            ("Slip, Trip and Fall Prevention", 0),
            ("Safe Material Handling", 8),
            ("Fire Extinguisher Awareness", 2),
            ("Emergency Evacuation Procedure", 3),
            ("Chemical Handling and Storage", 4),
            ("Electrical Safety at Workplace", 5),
            ("Working at Height Safety", 6),
            ("Machine Guarding and Safe Operation", 7),
            ("Environmental Waste Segregation", 9),
            ("Lockout Tagout Awareness", 5),
            ("Hand Tool Safety", 7),
            ("Heat Stress Prevention", 0),
            ("Housekeeping and 5S Safety", 0),
            ("Safe Lifting Techniques", 8),
            ("Confined Space Awareness", 0),
        ]

        topics = []
        for title, category_index in topic_seed:
            topic = Topic.objects.filter(topic_title=title).first()
            if not topic:
                topic = Topic(
                    topic_title=title,
                    category=categories[category_index % len(categories)],
                    description=f"Demo Toolbox Talk topic: {title}.",
                    is_active=True,
                    created_by=next(creator_cycle),
                )
                topic.save()
            topics.append(topic)

        # Ensure every topic has usable detail records for conduct tracking.
        detail_by_topic = {}
        for topic in topics:
            details = list(TopicDetail.objects.filter(topic=topic).order_by("display_order", "id"))
            if not details:
                details = [
                    TopicDetail.objects.create(
                        topic=topic,
                        safety_point=f"Discuss key safety controls for {topic.topic_title}.",
                        learning_objective=f"Employees understand the main risks and safe practices related to {topic.topic_title}.",
                        reference_document="EHS-360 Demo Reference",
                        display_order=1,
                    ),
                    TopicDetail.objects.create(
                        topic=topic,
                        safety_point=f"Explain required precautions, reporting and emergency actions for {topic.topic_title}.",
                        learning_objective="Employees can explain the expected safe behaviour after the toolbox talk.",
                        reference_document="EHS-360 Demo Reference",
                        display_order=2,
                    ),
                ]
            detail_by_topic[topic.id] = details

        user_cycle = cycle(users)
        session_statuses = ["COMPLETED", "COMPLETED", "PLANNED", "CANCELLED", "COMPLETED", "PLANNED"]
        assignment_statuses = ["COMPLETED", "ACCEPTED", "PENDING", "REJECTED", "IN_PROGRESS"]

        created_sessions = 0
        created_assignments = 0
        created_conducts = 0
        created_attendance = 0
        created_evidence = 0

        for i in range(count):
            topic = topics[i % len(topics)]
            category = topic.category
            location = valid_locations[i % len(valid_locations)]
            plant = location.zone.plant
            zone = location.zone
            department = departments[i % len(departments)]

            status = session_statuses[i % len(session_statuses)]

            if status == "COMPLETED":
                planned_date = fy_start + timedelta(days=(i * 2) % max((today - fy_start).days + 1, 1))
            elif status == "CANCELLED":
                planned_date = self.add_days(fy_start, fy_end, i)
            else:
                future_start = max(today + timedelta(days=1), fy_start)
                planned_date = self.add_days(future_start, fy_end, i)

            session = Session(
                category=category,
                topic=topic,
                department=department,
                planned_date=planned_date,
                planned_time=time(hour=9 + (i % 4), minute=(i % 2) * 30),
                expected_participants=10 + (i % 6) * 5,
                remarks=f"Demo Toolbox Talk session {i + 1:03d} for {topic.topic_title}.",
                status=status,
                created_by=next(user_cycle),
            )
            session.save()

            # Keep the organization hierarchy internally consistent.
            session.plants.add(plant)
            session.zones.add(zone)
            session.locations.add(location)
            sub = next(
                (
                    s for s in sublocations
                    if getattr(s, "location_id", None) == location.id
                ),
                None,
            )
            if sub:
                session.sublocations.add(sub)

            trainer = users[i % len(users)]
            incharge = users[(i + 1) % len(users)]
            session.trainers.add(trainer)
            if incharge.id != trainer.id:
                session.incharges.add(incharge)

            created_sessions += 1

            # Create trainer and incharge assignments with varied statuses.
            assignment_specs = [
                (trainer, "TRAINER"),
                (incharge, "INCHARGE"),
            ]
            for assignment_index, (assigned_user, role) in enumerate(assignment_specs):
                assignment_status = assignment_statuses[
                    (i + assignment_index) % len(assignment_statuses)
                ]

                if status == "COMPLETED":
                    assignment_status = "COMPLETED"
                elif status == "CANCELLED":
                    assignment_status = "REJECTED"

                accepted_at = None
                completed_at = None
                if assignment_status in {"ACCEPTED", "IN_PROGRESS", "COMPLETED"}:
                    accepted_at = timezone.make_aware(
                        datetime.combine(
                            planned_date if planned_date <= today else today,
                            time(8, 30),
                        )
                    )
                if assignment_status == "COMPLETED":
                    completed_at = timezone.make_aware(
                        datetime.combine(
                            planned_date if planned_date <= today else today,
                            time(16, 30),
                        )
                    )

                Assignment.objects.create(
                    session=session,
                    user=assigned_user,
                    role=role,
                    status=assignment_status,
                    remarks=f"Demo {role.lower()} assignment.",
                    accepted_at=accepted_at,
                    completed_at=completed_at,
                    assigned_by=next(user_cycle),
                )
                created_assignments += 1

            if status != "COMPLETED":
                continue

            trainer_assignment = session.assignments.filter(role="TRAINER").first()
            if not trainer_assignment:
                continue

            conduct = Conduct.objects.create(
                session=session,
                assignment=trainer_assignment,
                overall_remark=f"Toolbox Talk conducted successfully for {topic.topic_title}.",
            )
            created_conducts += 1

            for detail in detail_by_topic[topic.id]:
                ConductDetail.objects.create(
                    conduct=conduct,
                    topic_detail=detail,
                    trainer_remark="Topic explained and participant questions discussed.",
                )

            attendance = Attendance.objects.create(
                session=session,
                overall_remark="Attendance recorded for completed Toolbox Talk.",
                created_by=next(user_cycle),
            )
            created_attendance += 1

            # Vary attendance while ensuring each session has attendees.
            attendee_count = min(len(users), max(5, session.expected_participants // 2))
            selected_users = [users[(i + j) % len(users)] for j in range(attendee_count)]
            seen_ids = set()
            for j, attendee in enumerate(selected_users):
                if attendee.id in seen_ids:
                    continue
                seen_ids.add(attendee.id)
                AttendanceDetail.objects.create(
                    attendance=attendance,
                    user=attendee,
                    present=(j % 5 != 4),
                    marked_by=next(user_cycle),
                )

            evidence = Evidence(
                session=session,
                uploaded_by=next(user_cycle),
                evidence_type="PHOTO" if i % 2 == 0 else "DOCUMENT",
                description=f"Demo evidence for {session.session_no}.",
            )
            evidence.file = self.make_pdf(f"toolbox_talk_evidence_{i + 1:04d}")
            evidence.save()
            created_evidence += 1

        self.stdout.write(self.style.SUCCESS(
            f"Toolbox Talk demo data created for FY {fy_start} to {today}."
        ))
        self.stdout.write(
            f"Sessions: {created_sessions} | Assignments: {created_assignments} | "
            f"Conducts: {created_conducts} | Attendance: {created_attendance} | "
            f"Evidence: {created_evidence}"
        )
        self.stdout.write(
            f"Reused {len(users)} existing users, {len(plants)} existing plants and "
            f"{len(departments)} existing departments. No users or organization records were created."
        )
