# ============================================================
# Contractor Management Demo Data Seeder
# Creates realistic current-FY demo data using existing users
# and existing organization records. Contractor module masters
# are created/reused; users and organization records are never created.
#
# Run:
#   python manage.py demo_data_contractor
#   python manage.py demo_data_contractor --count 10
# ============================================================

from datetime import date, datetime, time, timedelta
from itertools import cycle

from django.apps import apps
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Plant, Zone, Location, SubLocation, Department
from apps.contractor.models import (
    Contractor,
    ContractorPortalUser,
    PreQualificationQuestion,
    DocumentType,
    ContractorPreQualification,
    ContractorDocument,
    OnboardingRequest,
    OnboardingDocumentRequirement,
    ContractorAssignment,
    WorkOrder,
    TrainingSignOff,
    ContractorInspectionQuestion,
    ContractorInspection,
    ContractorInspectionResponse,
    ContractorPerformanceMetric,
    PerformanceWeightConfig,
    PerformanceScoreHistory,
    ContractorDashboardSnapshot,
    ContractorReport,
)


class Command(BaseCommand):
    help = "Create current financial year demo data for the Contractor Management module."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Number of contractor demo records to create (default: 100).",
        )

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

    def elapsed_fy_date(self, fy_start, today, index, step=3):
        span = max((today - fy_start).days, 0)
        return fy_start + timedelta(days=(index * step) % (span + 1))

    def get_or_create_master(self, model, lookup, defaults):
        obj = model.objects.filter(**lookup).first()
        if obj:
            return obj
        return model.objects.create(**lookup, **defaults)

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        if count < 1:
            raise CommandError("--count must be at least 1.")

        today = timezone.localdate()
        fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)

        users = list(User.objects.filter(is_active=True).order_by("id"))
        plants = list(Plant.objects.all().order_by("id"))
        departments = list(Department.objects.all().order_by("id"))
        locations = list(
            Location.objects.select_related("zone__plant").order_by("id")
        )
        valid_locations = [
            loc for loc in locations
            if getattr(loc, "zone_id", None)
            and getattr(loc.zone, "plant_id", None)
        ]
        sublocations = list(
            SubLocation.objects.select_related("location").order_by("id")
        )

        if not users:
            raise CommandError("No active users found. Create users first.")
        if not plants:
            raise CommandError("No Plant records found. Create organization data first.")
        if not departments:
            raise CommandError("No Department records found. Create departments first.")
        if not valid_locations:
            raise CommandError("No valid Location -> Zone -> Plant hierarchy found.")

        self.stdout.write(
            self.style.NOTICE(
                f"Contractor Management demo data: {fy_start} to {today}"
            )
        )
        self.stdout.write(
            f"Using {len(users)} existing users, {len(plants)} existing plants, "
            f"{len(departments)} existing departments and "
            f"{len(valid_locations)} valid organization locations."
        )

        creator_cycle = cycle(users)

        # ------------------------------------------------------------
        # Master data used by contractor onboarding/pre-qualification.
        # ------------------------------------------------------------
        document_seed = [
            ("Company Registration", "COMPANY_REGISTRATION", True),
            ("PAN", "PAN", True),
            ("GST", "GST", True),
            ("Contractor License", "CONTRACTOR_LICENSE", False),
            ("PF Registration", "PF", False),
            ("ESIC Registration", "ESIC", False),
            ("Insurance", "INSURANCE", True),
            ("Workmen Compensation", "WORKMEN_COMPENSATION", True),
            ("Public Liability Insurance", "PUBLIC_LIABILITY", False),
            ("Safety Policy", "SAFETY_POLICY", True),
        ]

        document_types = []
        for name, code, mandatory in document_seed:
            document_types.append(
                self.get_or_create_master(
                    DocumentType,
                    {"code": code},
                    {
                        "name": name,
                        "description": f"Demo contractor document type: {name}.",
                        "is_mandatory": mandatory,
                        "is_active": True,
                    },
                )
            )

        question_seed = [
            ("How many years of similar work experience does the contractor have?", "EXPERIENCE", True),
            ("Has the contractor maintained an acceptable EHS performance record?", "EHS_PERFORMANCE", True),
            ("Does the contractor have adequate safety manpower?", "SAFETY_CAPABILITY", True),
            ("Does the contractor have suitable technical capability and equipment?", "TECHNICAL_CAPABILITY", True),
            ("Does the contractor maintain valid insurance coverage?", "INSURANCE", True),
            ("Is the contractor financially capable of completing the assigned work?", "FINANCIAL", False),
            ("Does the contractor have an established emergency preparedness system?", "GENERAL", False),
        ]

        questions = []
        for sequence, (question_text, question_type, mandatory) in enumerate(question_seed, start=1):
            question = PreQualificationQuestion.objects.filter(
                question=question_text
            ).first()
            if not question:
                question = PreQualificationQuestion.objects.create(
                    question=question_text,
                    question_type=question_type,
                    is_active=True,
                    is_mandatory=mandatory,
                    sequence=sequence,
                )
            questions.append(question)

        inspection_question_seed = [
            ("PPE", "Required PPE is available and being used correctly."),
            ("PPE", "Contractor workers are using task-specific PPE."),
            ("SAFETY", "Safe work procedures are available at the work location."),
            ("SAFETY", "Emergency arrangements and contact information are available."),
            ("HOUSEKEEPING", "Work area is clean and free from unsafe obstructions."),
            ("HOUSEKEEPING", "Materials and tools are stored safely."),
            ("CONTRACTOR_MANAGEMENT", "Contractor workers have completed required induction."),
            ("CONTRACTOR_MANAGEMENT", "Required contractor documents are available and valid."),
        ]

        inspection_questions = []
        for order, (category, question_text) in enumerate(inspection_question_seed, start=1):
            question = ContractorInspectionQuestion.objects.filter(
                question_text=question_text
            ).first()
            if not question:
                question = ContractorInspectionQuestion.objects.create(
                    category=category,
                    question_text=question_text,
                    is_active=True,
                    display_order=order,
                )
            inspection_questions.append(question)

        # Reuse or create the active performance weight configuration.
        weight_config = PerformanceWeightConfig.objects.filter(is_active=True).first()
        if not weight_config:
            weight_config = PerformanceWeightConfig.objects.create(
                name="Default Demo Contractor Performance Configuration",
                weight_onboarding_compliance=25,
                weight_training_compliance=25,
                weight_inspection_compliance=30,
                weight_work_order_completion=20,
                is_active=True,
            )

        # Optional Toolbox Talk sessions for TrainingSignOff.
        toolbox_session_model = None
        try:
            toolbox_session_model = apps.get_model(
                "toolbox_talk", "ToolboxTalkSessionPlan"
            )
        except LookupError:
            pass

        toolbox_sessions = []
        if toolbox_session_model:
            toolbox_sessions = list(
                toolbox_session_model.objects.all().order_by("id")
            )

        contractor_types = [
            "ELECTRICAL", "CIVIL", "MECHANICAL", "CONSTRUCTION",
            "HOUSEKEEPING", "SECURITY", "TRANSPORT", "WASTE_MANAGEMENT",
            "FACILITY_MANAGEMENT", "OTHER",
        ]
        work_categories = contractor_types[:]
        risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

        onboarding_statuses = [
            "COMPLETED", "APPROVED", "APPROVED", "PENDING", "REJECTED", "DRAFT"
        ]
        prequal_statuses = [
            "APPROVED", "APPROVED", "UNDER_REVIEW", "SUBMITTED", "REJECTED", "DRAFT"
        ]
        assignment_statuses = [
            "ACTIVE", "ACTIVE", "COMPLETED", "REJECTED", "CANCELLED", "EXPIRED"
        ]
        work_order_statuses = [
            "APPROVED", "APPROVED", "SUBMITTED", "CLOSED", "REJECTED"
        ]
        inspection_statuses = [
            "CLOSED", "CLOSED", "IN_PROGRESS", "SCHEDULED", "OVERDUE", "CANCELLED"
        ]

        created = {
            "contractors": 0,
            "portal_users": 0,
            "prequalifications": 0,
            "documents": 0,
            "onboarding": 0,
            "document_requirements": 0,
            "assignments": 0,
            "work_orders": 0,
            "training_signoffs": 0,
            "inspections": 0,
            "inspection_responses": 0,
            "performance_metrics": 0,
            "performance_history": 0,
            "reports": 0,
        }

        contractor_list = []

        # ------------------------------------------------------------
        # Main contractor records.
        # ------------------------------------------------------------
        for i in range(count):
            contractor_type = contractor_types[i % len(contractor_types)]
            work_category = work_categories[i % len(work_categories)]
            workers = 10 + ((i * 7) % 191)
            active = i % 7 != 5

            contractor = Contractor.objects.create(
                contractor_name=f"Demo {contractor_type.replace('_', ' ').title()} Contractor {i + 1:03d}",
                contractor_type=contractor_type,
                registration_number=f"REG-DEMO-{i + 1:05d}",
                pan_number=f"DEMOX{i + 1:05d}P",
                gstin=f"27DEMO{i + 1:05d}1Z5",
                establishment_year=2000 + (i % 20),
                contact_person=f"Contractor Contact {i + 1:03d}",
                designation="Site Supervisor",
                mobile=f"9{100000000 + i:09d}",
                email=f"contractor{i + 1:03d}@demo.example.com",
                alternate_mobile=f"8{100000000 + i:09d}",
                address_line1=f"Demo Industrial Estate, Plot {i + 1:03d}",
                address_line2="EHS-360 Demo Address",
                country="India",
                state="Maharashtra",
                city="Nagpur",
                pincode=f"{440001 + (i % 20):06d}",
                nature_of_business=f"{work_category.replace('_', ' ').title()} Services",
                work_category=work_category,
                service_description=f"Demo {work_category.replace('_', ' ').lower()} services for EHS-360 contractor management testing.",
                years_of_experience=3 + (i % 18),
                number_of_workers=workers,
                ehs_officer_name=f"EHS Officer {i + 1:03d}",
                ehs_designation="Safety Officer",
                ehs_mobile=f"9{200000000 + i:09d}",
                ehs_email=f"ehs{i + 1:03d}@demo.example.com",
                is_active=active,
                created_by=next(creator_cycle),
            )
            created["contractors"] += 1
            contractor_list.append(contractor)

            # External contractor portal user.
            portal = ContractorPortalUser.objects.create(
                contractor=contractor,
                name=contractor.contact_person,
                email=f"portal{i + 1:03d}@demo.example.com",
                user_type="CONTACT_PERSON" if i % 2 == 0 else "EHS_OFFICER",
                password="",
                is_active=active,
            )
            portal.set_password("Demo@12345")
            portal.save(update_fields=["password"])
            created["portal_users"] += 1

            # Pre-qualification with risk/status variation.
            risk = risk_levels[i % len(risk_levels)]
            prequal_status = prequal_statuses[i % len(prequal_statuses)]
            accident_history = i % 4
            fatality_history = 1 if risk == "CRITICAL" and i % 3 == 0 else 0
            lti = (i * 2) % 5
            violations = i % 3

            prequal = ContractorPreQualification.objects.create(
                contractor=contractor,
                years_of_experience=contractor.years_of_experience or 0,
                similar_work_experience=f"Demo similar work experience for {contractor.contractor_name}.",
                previous_clients="Demo manufacturing clients; demo references available.",
                previous_ehs_performance="Acceptable demo EHS performance with periodic review.",
                accident_history=accident_history,
                fatality_history=fatality_history,
                lost_time_injuries=lti,
                regulatory_violations=violations,
                safety_manpower=max(1, workers // 25),
                total_manpower=workers,
                has_safety_policy=i % 6 != 5,
                has_training_system=i % 5 != 4,
                has_emergency_preparedness=i % 4 != 3,
                equipment_capability="Suitable demo equipment and trained operators.",
                training_capability="Induction, PPE and task safety training available.",
                has_insurance=i % 7 != 5,
                risk_level=risk,
                risk_reason=f"Demo risk classification: {risk}.",
                status=prequal_status,
                reviewer_comments=(
                    "Approved demo pre-qualification."
                    if prequal_status == "APPROVED"
                    else "Demo review pending."
                ),
                approved_by=next(creator_cycle) if prequal_status == "APPROVED" else None,
                approved_at=timezone.now() if prequal_status == "APPROVED" else None,
            )
            created["prequalifications"] += 1

            # Contractor documents.
            for doc_index, document_type in enumerate(document_types[:3]):
                verified = (i + doc_index) % 4 != 3
                document = ContractorDocument(
                    contractor=contractor,
                    document_type=document_type.code,
                    remarks="Demo contractor compliance document.",
                    verified_by=next(creator_cycle) if verified else None,
                    verified_at=timezone.now() if verified else None,
                )
                document.document = self.make_pdf(
                    f"contractor_{i + 1:04d}_{document_type.code.lower()}"
                )
                document.save()
                created["documents"] += 1

            # Onboarding workflow.
            onboarding_status = onboarding_statuses[i % len(onboarding_statuses)]
            submitted = onboarding_status != "DRAFT"
            approved = onboarding_status in {"APPROVED", "COMPLETED"}

            onboarding = OnboardingRequest.objects.create(
                contractor=contractor,
                ehs_officer=next(creator_cycle),
                pre_qualification_answers={
                    str(q.id): ("YES" if (i + q.id) % 5 != 0 else "NO")
                    for q in questions
                },
                question_remarks={
                    str(q.id): "Demo assessment response."
                    for q in questions
                },
                status=onboarding_status,
                notes="Demo contractor onboarding record.",
                submitted_by=next(creator_cycle) if submitted else None,
                submitted_at=timezone.now() if submitted else None,
                approved_by=next(creator_cycle) if approved else None,
                approved_at=timezone.now() if approved else None,
                rejection_reason=(
                    "Demo onboarding rejection for testing workflow."
                    if onboarding_status == "REJECTED"
                    else ""
                ),
            )
            created["onboarding"] += 1

            # Onboarding document requirements.
            for doc_index, document_type in enumerate(document_types[:5]):
                if onboarding_status == "DRAFT":
                    req_status = "PENDING"
                elif onboarding_status == "REJECTED":
                    req_status = "REJECTED" if doc_index == 0 else "UPLOADED"
                elif approved:
                    req_status = "VERIFIED"
                else:
                    req_status = "UPLOADED" if doc_index % 2 == 0 else "PENDING"

                req = OnboardingDocumentRequirement(
                    onboarding=onboarding,
                    document_type=document_type,
                    is_required=document_type.is_mandatory,
                    status=req_status,
                    uploaded_by=next(creator_cycle)
                    if req_status in {"UPLOADED", "VERIFIED", "REJECTED"} else None,
                    uploaded_at=timezone.now()
                    if req_status in {"UPLOADED", "VERIFIED", "REJECTED"} else None,
                    verified_by=next(creator_cycle)
                    if req_status == "VERIFIED" else None,
                    verified_at=timezone.now()
                    if req_status == "VERIFIED" else None,
                    comments="Demo onboarding document requirement.",
                )
                if req_status in {"UPLOADED", "VERIFIED"}:
                    req.document_file = self.make_pdf(
                        f"onboarding_{i + 1:04d}_{document_type.code.lower()}"
                    )
                req.save()
                created["document_requirements"] += 1

            # Contractor assignment only after onboarding exists.
            assignment_status = assignment_statuses[i % len(assignment_statuses)]
            if onboarding_status in {"DRAFT", "PENDING"}:
                assignment_status = "ACTIVE"
            if assignment_status == "ACTIVE":
                is_access_active = active and onboarding_status in {"APPROVED", "COMPLETED"}
            else:
                is_access_active = False

            expires_at = (
                timezone.now() + timedelta(days=30)
                if assignment_status == "ACTIVE"
                else timezone.now() - timedelta(days=5)
                if assignment_status == "EXPIRED"
                else None
            )
            assignment = ContractorAssignment.objects.create(
                onboarding=onboarding,
                portal_user=portal,
                status=assignment_status,
                is_access_active=is_access_active,
                expires_at=expires_at,
                completed_at=timezone.now()
                if assignment_status == "COMPLETED" else None,
            )
            created["assignments"] += 1

            # Only approved onboarding is used for work orders.
            work_order = None
            if approved:
                wo_status = work_order_statuses[i % len(work_order_statuses)]
                work_start = self.elapsed_fy_date(fy_start, today, i, step=2)
                work_end = min(
                    work_start + timedelta(days=15 + (i % 60)),
                    today,
                )
                if work_end < work_start:
                    work_end = work_start

                location = valid_locations[i % len(valid_locations)]
                plant = location.zone.plant
                department = departments[i % len(departments)]

                work_order = WorkOrder.objects.create(
                    contractor=contractor,
                    onboarding=onboarding,
                    work_description=f"Demo {work_category.replace('_', ' ').lower()} work for EHS testing.",
                    work_category=work_category,
                    plant=plant,
                    department=department,
                    location=str(location),
                    contractor_supervisor=contractor.ehs_officer_name,
                    contractor_supervisor_contact=contractor.ehs_mobile,
                    contractor_supervisor_email=contractor.ehs_email,
                    company_representative=next(creator_cycle),
                    number_of_workers=workers,
                    worker_details=f"{workers} demo contractor workers assigned.",
                    start_date=work_start,
                    end_date=work_end,
                    risk_level=risk,
                    status=wo_status,
                    created_by=next(creator_cycle),
                    approved_by=next(creator_cycle)
                    if wo_status in {"APPROVED", "CLOSED"} else None,
                    approved_at=timezone.now()
                    if wo_status in {"APPROVED", "CLOSED"} else None,
                    closed_by=next(creator_cycle)
                    if wo_status == "CLOSED" else None,
                    closed_at=timezone.now()
                    if wo_status == "CLOSED" else None,
                    closure_remarks="Demo work order closed." if wo_status == "CLOSED" else "",
                )
                work_order.attachment = self.make_pdf(
                    f"work_order_{i + 1:04d}"
                )
                work_order.attachment_name = "Demo Work Order Attachment"
                work_order.save()
                created["work_orders"] += 1

            # Contractor inspection.
            location = valid_locations[i % len(valid_locations)]
            plant = location.zone.plant
            zone = location.zone
            sub = next(
                (
                    s for s in sublocations
                    if getattr(s, "location_id", None) == location.id
                ),
                None,
            )

            inspection_status = inspection_statuses[i % len(inspection_statuses)]
            inspection_start = self.elapsed_fy_date(fy_start, today, i, step=4)
            inspection_end = min(
                inspection_start + timedelta(days=1 + (i % 3)),
                today,
            )

            inspection = ContractorInspection.objects.create(
                contractor=contractor,
                work_order=work_order,
                plant=plant,
                zone=zone,
                location=location,
                sublocation=sub,
                department=departments[i % len(departments)],
                assigned_to=next(creator_cycle),
                assigned_by=next(creator_cycle),
                inspection_start_date=inspection_start,
                inspection_end_date=inspection_end,
                status=inspection_status,
                notes=f"Demo contractor inspection for {contractor.contractor_name}.",
                enable_auto_schedule=i % 3 == 0,
                due_date_offset_days=7,
                started_at=(
                    timezone.make_aware(datetime.combine(inspection_start, time(9, 0)))
                    if inspection_status in {"IN_PROGRESS", "CLOSED"}
                    else None
                ),
                closed_at=(
                    timezone.make_aware(datetime.combine(inspection_end, time(17, 0)))
                    if inspection_status == "CLOSED"
                    else None
                ),
            )
            inspection.selected_questions.set(inspection_questions)
            created["inspections"] += 1

            # One response per selected question; unique_together is respected.
            for q_index, question in enumerate(inspection_questions):
                answer = "NO" if (i + q_index) % 6 == 0 else "YES"
                ContractorInspectionResponse.objects.create(
                    inspection=inspection,
                    question=question,
                    answer=answer,
                    remarks=(
                        "Demo observation requiring follow-up."
                        if answer == "NO"
                        else "Demo requirement found satisfactory."
                    ),
                )
                created["inspection_responses"] += 1

            # One monthly performance metric per contractor for the current month.
            month_number = today.month
            metric_year = today.year
            onboarding_score = 100 if onboarding_status in {"APPROVED", "COMPLETED"} else 60 if onboarding_status == "PENDING" else 35
            training_score = 90 if i % 5 != 4 else 55
            inspection_score = 95 if inspection_status == "CLOSED" else 75 if inspection_status == "IN_PROGRESS" else 55
            wo_score = (
                100 if work_order and work_order.status == "CLOSED"
                else 85 if work_order and work_order.status == "APPROVED"
                else 60 if work_order and work_order.status == "SUBMITTED"
                else 35 if work_order else 20
            )

            overall = round(
                onboarding_score * (weight_config.weight_onboarding_compliance / 100)
                + training_score * (weight_config.weight_training_compliance / 100)
                + inspection_score * (weight_config.weight_inspection_compliance / 100)
                + wo_score * (weight_config.weight_work_order_completion / 100),
                2,
            )
            if overall >= 90:
                rating = "Excellent"
            elif overall >= 75:
                rating = "Good"
            elif overall >= 60:
                rating = "Needs Improvement"
            else:
                rating = "Poor"

            metric = ContractorPerformanceMetric.objects.create(
                contractor=contractor,
                period_type="MONTHLY",
                period_month=month_number,
                period_year=metric_year,
                pre_qualification_score=90 if prequal_status == "APPROVED" else 60,
                risk_level=risk,
                document_compliance_score=95 if i % 4 != 3 else 65,
                training_compliance_score=training_score,
                inspection_compliance_score=inspection_score,
                inspections_count=1,
                work_order_completion_score=wo_score,
                work_orders_count=1 if work_order else 0,
                overall_performance_score=overall,
                rating=rating,
            )
            created["performance_metrics"] += 1

            PerformanceScoreHistory.objects.create(
                contractor=contractor,
                metric=metric,
                overall_score=overall,
                rating=rating,
            )
            created["performance_history"] += 1

            # Training sign-off is created only when an approved work order
            # and an existing Toolbox Talk session are available.
            if (
                work_order
                and work_order.status == "APPROVED"
                and toolbox_sessions
                and i % 2 == 0
            ):
                session = toolbox_sessions[i % len(toolbox_sessions)]
                signoff_status = ["COMPLETED", "SUBMITTED", "DRAFT"][i % 3]
                signed = signoff_status == "COMPLETED"

                signoff = TrainingSignOff.objects.create(
                    contractor=contractor,
                    work_order=work_order,
                    session=session,
                    contractor_representative=contractor.contact_person,
                    contractor_representative_designation=contractor.designation,
                    number_of_workers=workers,
                    company_declaration=signed,
                    company_representative=next(creator_cycle) if signed else None,
                    company_representative_designation="EHS Manager" if signed else "",
                    contractor_declaration=signed,
                    contractor_supervisor=contractor.ehs_officer_name,
                    contractor_supervisor_designation=contractor.ehs_designation,
                    signoff_date=self.elapsed_fy_date(fy_start, today, i, step=5),
                    signoff_time=time(11, 0),
                    status=signoff_status,
                    created_by=next(creator_cycle),
                )
                if signed:
                    signoff.company_signature = self.make_pdf(
                        f"company_signature_{i + 1:04d}"
                    )
                    signoff.supporting_documents = self.make_pdf(
                        f"training_signoff_{i + 1:04d}"
                    )
                    signoff.save()
                created["training_signoffs"] += 1

            # A small set of reports gives the report screen usable demo data.
            if i < max(5, min(count, 20)):
                ContractorReport.objects.create(
                    report_type=[
                        "CONTRACTOR_OVERVIEW",
                        "PERFORMANCE_SUMMARY",
                        "DOCUMENT_COMPLIANCE",
                        "TRAINING_COMPLIANCE",
                        "INSPECTION_SUMMARY",
                        "RISK_ASSESSMENT",
                        "WORK_ORDER_SUMMARY",
                    ][i % 7],
                    report_format="PDF",
                    date_from=fy_start,
                    date_to=today,
                    plant=plant,
                    contractor=contractor,
                    generated_by=next(creator_cycle),
                )
                created["reports"] += 1

        # ------------------------------------------------------------
        # Dashboard snapshot based on the contractor data created above.
        # ------------------------------------------------------------
        contractors_qs = Contractor.objects.all()
        active_count = contractors_qs.filter(is_active=True).count()
        inactive_count = contractors_qs.filter(is_active=False).count()
        pending_count = OnboardingRequest.objects.filter(
            status__in=["DRAFT", "PENDING", "UNDER_REVIEW"]
        ).count()
        rejected_count = OnboardingRequest.objects.filter(status="REJECTED").count()

        risk_counts = {
            risk: ContractorPreQualification.objects.filter(risk_level=risk).count()
            for risk in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        }

        metrics = list(
            ContractorPerformanceMetric.objects.filter(
                period_type="MONTHLY",
                period_month=today.month,
                period_year=today.year,
                contractor__in=contractor_list,
            )
        )
        avg_score = (
            round(sum(m.overall_performance_score for m in metrics) / len(metrics), 2)
            if metrics else 0
        )

        ContractorDashboardSnapshot.objects.create(
            snapshot_type="DAILY",
            total_contractors=contractors_qs.count(),
            active_contractors=active_count,
            inactive_contractors=inactive_count,
            pending_approval=pending_count,
            rejected_contractors=rejected_count,
            high_risk_contractors=risk_counts["HIGH"],
            critical_risk_contractors=risk_counts["CRITICAL"],
            medium_risk_contractors=risk_counts["MEDIUM"],
            low_risk_contractors=risk_counts["LOW"],
            expired_documents=0,
            expiring_soon_documents=0,
            valid_documents=ContractorDocument.objects.count(),
            avg_performance_score=avg_score,
            excellent_count=sum(1 for m in metrics if m.rating == "Excellent"),
            good_count=sum(1 for m in metrics if m.rating == "Good"),
            needs_improvement_count=sum(
                1 for m in metrics if m.rating == "Needs Improvement"
            ),
            poor_count=sum(1 for m in metrics if m.rating == "Poor"),
            contractors_requiring_attention=sum(
                1 for m in metrics if m.overall_performance_score < 60
            ),
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Contractor Management demo data created for FY {fy_start} to {today}."
            )
        )
        self.stdout.write(
            " | ".join(f"{key}: {value}" for key, value in created.items())
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Reused {len(users)} existing users, {len(plants)} existing plants, "
                f"{len(departments)} existing departments and {len(valid_locations)} "
                "valid organization locations. No users or organization records were created."
            )
        )
