from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from datetime import date, time

from apps.organizations.models import Department, Location, Plant, Zone
from apps.training.models import TrainingSession, TrainingTopic

from .models import HIRA, HIRAHazard, HIRAModule, HazardRiskMaster, RiskMatrix, RiskMatrixLevel
from .reports import build_hira_workbook, build_source_first_hira_workbook
from .source_adapters import get_adapter


class HIRAModelAndReportTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="safety",
            email="safety@example.com",
            password="testpass123",
            first_name="Safety",
            last_name="Officer",
        )
        self.plant = Plant.objects.create(
            name="Plant A",
            code="PLA",
            address="Industrial Area",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            created_by=self.user,
        )
        self.user.assigned_plants.add(self.plant)
        self.zone = Zone.objects.create(plant=self.plant, name="Zone 1", code="Z1")
        self.location = Location.objects.create(zone=self.zone, name="Training Room", code="TRN")
        self.department = Department.objects.create(name="Production", code="PROD")
        self.module = HIRAModule.objects.get(code="training-management")
        self.hira = HIRA.objects.create(
            plant=self.plant,
            department=self.department,
            module=self.module,
            process="Safety Training",
            prepared_by=self.user,
            created_by=self.user,
        )

    def test_risk_scores_and_action_are_calculated_from_hazard_data(self):
        hazard = HIRAHazard.objects.create(
            hira=self.hira,
            activity="Practical safety demonstration",
            hazard_category="Mechanical",
            hazard="Unsafe practical demonstration",
            potential_consequence="Hand injury",
            persons_exposed="Participants",
            existing_controls="Trainer supervision",
            likelihood=4,
            severity=5,
            additional_controls="Use guarded demo kit and pre-brief participants",
            action_required=True,
            responsible_person=self.user,
            residual_likelihood=2,
            residual_severity=4,
        )

        self.assertEqual(hazard.initial_risk_score, 20)
        self.assertEqual(hazard.initial_risk_level, "Critical")
        self.assertEqual(hazard.residual_risk_score, 8)
        self.assertEqual(hazard.residual_risk_level, "Medium")
        self.assertEqual(hazard.actions.count(), 1)

    def test_hira_workbook_uses_sample_sheet_structure_and_database_values(self):
        HIRAHazard.objects.create(
            hira=self.hira,
            activity="Training delivery",
            hazard_category="Physical",
            hazard="Heat stress during outdoor training",
            potential_consequence="Heat exhaustion",
            persons_exposed="Participants",
            existing_controls="Drinking water",
            likelihood=3,
            severity=4,
            residual_likelihood=2,
            residual_severity=3,
        )

        wb = build_hira_workbook(HIRA.objects.filter(pk=self.hira.pk))

        self.assertEqual(
            wb.sheetnames,
            [
                "HIRA Dashboard",
                "HIRA Register",
                "Risk Matrix",
                "Risk Levels",
                "Hierarchy of Controls",
                "Action Register",
                "Approval & Revision",
                "Review Triggers",
                "Industry Activity Master",
                "Hazard Master",
            ],
        )
        register = wb["HIRA Register"]
        self.assertEqual(register["A2"].value, self.hira.hira_number)
        self.assertEqual(register["D2"].value, "Training Management")
        self.assertEqual(register["J2"].value, "Training delivery")
        self.assertEqual(register["M2"].value, "Heat stress during outdoor training")
        self.assertEqual(register["V2"].value, 12)
        self.assertEqual(register["W2"].value, "High")

    def test_workbook_reads_latest_linked_training_source_data(self):
        topic = TrainingTopic.objects.create(
            name="Machine Safety",
            code="MS-01",
            created_by=self.user,
        )
        session = TrainingSession.objects.create(
            topic=topic,
            training_mode="CLASSROOM",
            plant=self.plant,
            zone=self.zone,
            location=self.location,
            scheduled_date=date(2026, 9, 10),
            scheduled_time=time(10, 0),
            trainer_name="Safety Trainer",
            created_by=self.user,
            status="SCHEDULED",
        )
        content_type = ContentType.objects.get_for_model(session)
        self.hira.source_content_type = content_type
        self.hira.source_object_id = session.pk
        self.hira.save()
        HIRAHazard.objects.create(
            hira=self.hira,
            activity="Classroom training",
            hazard_category="Physical",
            hazard="Poor emergency briefing",
            potential_consequence="Delayed evacuation",
            likelihood=2,
            severity=3,
            related_content_type=content_type,
            related_object_id=session.pk,
        )

        first_wb = build_hira_workbook(HIRA.objects.filter(pk=self.hira.pk))
        self.assertEqual(first_wb["HIRA Register"]["H2"].value, "Scheduled")

        session.status = "COMPLETED"
        session.actual_date = date(2026, 9, 11)
        session.save()

        second_wb = build_hira_workbook(HIRA.objects.filter(pk=self.hira.pk))
        self.assertEqual(second_wb["HIRA Register"]["H2"].value, "Completed")

    def test_empty_workbook_clearly_states_no_matching_records(self):
        wb = build_hira_workbook([])

        self.assertEqual(
            wb["HIRA Register"]["A2"].value,
            "No HIRA records found for the selected filters.",
        )

    def test_risk_level_uses_configured_risk_matrix(self):
        RiskMatrix.objects.update(is_active=False)
        matrix = RiskMatrix.objects.create(name="Test Matrix", is_active=True)
        RiskMatrixLevel.objects.create(
            risk_matrix=matrix,
            min_score=20,
            max_score=25,
            risk_level="High",
            display_order=1,
            is_active=True,
        )

        hazard = HIRAHazard.objects.create(
            hira=self.hira,
            activity="Configured matrix activity",
            hazard_category="Mechanical",
            hazard="Configured matrix hazard",
            potential_consequence="Injury",
            likelihood=4,
            severity=5,
        )

        self.assertEqual(hazard.initial_risk_score, 20)
        self.assertEqual(hazard.initial_risk_level, "High")

    def test_hazard_preserves_master_snapshot_when_rule_changes(self):
        rule = HazardRiskMaster.objects.create(
            module=self.module,
            process="Safety Training",
            activity="Machine demonstration",
            hazard_category="Mechanical",
            hazard="Moving machinery exposure",
            consequence="Hand injury",
            existing_controls="Trainer supervision",
            suggested_additional_controls="Guarded demonstration kit",
            default_likelihood=3,
            default_severity=4,
            created_by=self.user,
        )
        hazard = HIRAHazard.objects.create(
            hira=self.hira,
            master_rule=rule,
            activity=rule.activity,
            hazard_category=rule.hazard_category,
            hazard=rule.hazard,
            potential_consequence=rule.consequence,
            likelihood=rule.default_likelihood,
            severity=rule.default_severity,
        )

        rule.hazard = "Edited future master hazard"
        rule.save()
        hazard.refresh_from_db()

        self.assertEqual(hazard.master_snapshot["hazard"], "Moving machinery exposure")
        self.assertEqual(hazard.master_rule.hazard, "Edited future master hazard")

    def test_master_pages_render_for_authorized_user(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)
        HazardRiskMaster.objects.create(
            module=self.module,
            process="Safety Training",
            activity="Machine demonstration",
            hazard_category="Mechanical",
            hazard="Moving machinery exposure",
            consequence="Hand injury",
            default_likelihood=3,
            default_severity=4,
            created_by=self.user,
        )

        hazard_response = self.client.get(reverse("hira:hazard_master"))
        matrix_response = self.client.get(reverse("hira:risk_matrix_master"))

        self.assertEqual(hazard_response.status_code, 200)
        self.assertEqual(matrix_response.status_code, 200)

    def test_source_first_workbook_includes_all_current_training_records(self):
        topic = TrainingTopic.objects.create(
            name="Machine Safety",
            code="MS-02",
            created_by=self.user,
        )
        assessed_session = TrainingSession.objects.create(
            topic=topic,
            training_mode="CLASSROOM",
            plant=self.plant,
            zone=self.zone,
            location=self.location,
            scheduled_date=date(2026, 9, 10),
            scheduled_time=time(10, 0),
            trainer_name="Safety Trainer",
            created_by=self.user,
            status="COMPLETED",
        )
        unassessed_session = TrainingSession.objects.create(
            topic=topic,
            training_mode="PRACTICAL",
            plant=self.plant,
            zone=self.zone,
            location=self.location,
            scheduled_date=date(2026, 9, 11),
            scheduled_time=time(11, 0),
            trainer_name="Safety Trainer",
            created_by=self.user,
            status="SCHEDULED",
        )
        content_type = ContentType.objects.get_for_model(assessed_session)
        self.hira.source_content_type = content_type
        self.hira.source_object_id = assessed_session.pk
        self.hira.save()
        HIRAHazard.objects.create(
            hira=self.hira,
            activity="Classroom training",
            hazard_category="Physical",
            hazard="Poor emergency briefing",
            potential_consequence="Delayed evacuation",
            likelihood=2,
            severity=3,
            related_content_type=content_type,
            related_object_id=assessed_session.pk,
        )

        adapter = get_adapter("training")
        records = adapter.filtered_queryset({"plant": self.plant.pk}, user=self.user)
        wb = build_source_first_hira_workbook(adapter, records)
        register = wb["HIRA Register"]
        source_records = {register.cell(row=row, column=6).value for row in range(2, register.max_row + 1)}

        self.assertEqual(source_records, {assessed_session.session_number, unassessed_session.session_number})
        unassessed_row = next(
            row for row in range(2, register.max_row + 1)
            if register.cell(row=row, column=6).value == unassessed_session.session_number
        )
        self.assertEqual(register.cell(row=unassessed_row, column=24).value, "Not Assessed")
        self.assertEqual(register.cell(row=unassessed_row, column=36).value, "Not Assessed")
