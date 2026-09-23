# ============================================================
## run to generate data:
## python manage.py demo_data_industrial_hygiene
## Or explicitly for related to employees available:
## python manage.py demo_data_industrial_hygiene --count 13 --records 100
# ============================================================
# ============================================================
# Industrial hygiene Demo Data Seeder
# Creates realistic demo data using existing users and
# existing organization assignments.
# ============================================================

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.industrial_hygiene.models import (
    HazardCategoryMaster,
    HazardMaster,
    ExposureTypeMaster,
    ExposureGroupMaster,
    MonitoringTypeMaster,
    MonitoringParameterMaster,
    UnitMaster,
    ExposureLimitMaster,
    InstrumentMaster,
    LaboratoryMaster,
    IHProgramMaster,
    MonitoringPlan,
    MonitoringSchedule,
    SamplingManagement,
    MeasurementEntry,
    LaboratoryResult,
    ExposureAssessment,
    ComplianceRecord,
    ExceedanceAction,
    ReMonitoring,
)


class Command(BaseCommand):
    help = "Create current-FY demo data for the Industrial Hygiene module."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=None,
            help="Number of existing active employees/users to use for distribution. Default: all available users.",
        )
        parser.add_argument(
            "--records",
            type=int,
            default=100,
            help="Number of Industrial Hygiene transaction records to create. Default: 100.",
        )

    def handle(self, *args, **options):
        requested_count = options.get("count")
        records = options["records"]

        if records <= 0:
            raise CommandError("--records must be greater than 0.")
        if requested_count is not None and requested_count <= 0:
            raise CommandError("--count must be greater than 0.")

        today = timezone.localdate()
        fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
        self.today = today
        self.fy_start = fy_start
        self.records = records
        self.prefix = timezone.now().strftime("%Y%m%d%H%M%S")

        from apps.accounts.models import User
        from apps.organizations.models import Plant

        users = list(User.objects.filter(is_active=True).order_by("id"))
        if not users:
            raise CommandError("No active users found. Existing users are required.")

        if requested_count is not None:
            users = users[:requested_count]
        if not users:
            raise CommandError("No users available after applying --count.")

        plants = list(Plant.objects.all().order_by("id"))
        if not plants:
            raise CommandError("No existing Plant records found. The seeder does not create organization records.")

        self.users = users
        self.plants = plants

        self.stdout.write(self.style.NOTICE(
            f"Industrial Hygiene demo data: {fy_start} to {today}"
        ))
        self.stdout.write(
            f"Using {len(users)} existing users and {len(plants)} existing plants; creating {records} transaction records."
        )

        with transaction.atomic():
            masters = self.seed_masters()
            program = self.seed_program(masters)
            plans = self.seed_monitoring_plans(program, masters)
            schedules = self.seed_schedules(plans)
            samplings = self.seed_sampling(schedules, masters)
            measurements = self.seed_measurements(samplings, masters)
            lab_results = self.seed_lab_results(samplings, measurements, masters)
            assessments = self.seed_assessments(
                samplings, measurements, lab_results, masters
            )
            compliance_records = self.seed_compliance(
                assessments, samplings, measurements, lab_results, masters
            )
            exceedances = self.seed_exceedances(
                compliance_records, assessments, samplings, measurements, lab_results, masters
            )
            remonitoring = self.seed_remonitoring(
                exceedances, samplings, measurements, masters
            )

        self.stdout.write(self.style.SUCCESS("Industrial Hygiene demo data created successfully."))
        self.stdout.write("")
        self.stdout.write("Current Financial Year:")
        self.stdout.write(f"  {fy_start} to {today}")
        self.stdout.write("")
        self.stdout.write("Created / reused masters:")
        for name, value in masters.items():
            self.stdout.write(f"  {name}: {value}")
        self.stdout.write("")
        self.stdout.write("Transaction summary:")
        self.stdout.write(f"  Monitoring Plans : {len(plans)}")
        self.stdout.write(f"  Monitoring Schedules : {len(schedules)}")
        self.stdout.write(f"  Sampling Records : {len(samplings)}")
        self.stdout.write(f"  Measurement Entries : {len(measurements)}")
        self.stdout.write(f"  Laboratory Results : {len(lab_results)}")
        self.stdout.write(f"  Exposure Assessments : {len(assessments)}")
        self.stdout.write(f"  Compliance Records : {len(compliance_records)}")
        self.stdout.write(f"  Exceedance Actions : {len(exceedances)}")
        self.stdout.write(f"  Re-Monitoring Records : {len(remonitoring)}")

    # ------------------------------------------------------------------
    # Common helpers
    # ------------------------------------------------------------------

    def demo_date(self, index, offset_days=0):
        """Spread demo records across the current FY without creating future dates."""
        total_days = max((self.today - self.fy_start).days, 0)
        if self.records <= 1:
            base = self.fy_start
        else:
            base = self.fy_start + timedelta(
                days=(index * total_days) // (self.records - 1)
            )
        return min(base + timedelta(days=offset_days), self.today)

    def user_for(self, index):
        return self.users[index % len(self.users)]

    def plant_for(self, index):
        return self.plants[index % len(self.plants)]

    def unique_code(self, prefix, index):
        return f"{prefix}-{self.prefix}-{index + 1:04d}"

    def get_or_create_by_fields(self, model, lookup, defaults=None):
        defaults = defaults or {}
        obj = model.objects.filter(**lookup).first()
        if obj:
            return obj, False
        return model.objects.create(**lookup, **defaults), True

    # ------------------------------------------------------------------
    # Master data
    # ------------------------------------------------------------------

    def seed_masters(self):
        masters = {}

        categories = [
            ("Chemical", "Chemical exposure hazards"),
            ("Physical", "Physical agents such as noise, heat and radiation"),
            ("Dust", "Particulate and airborne dust hazards"),
            ("Biological", "Biological exposure hazards"),
            ("Ergonomic", "Ergonomic exposure-related hazards"),
        ]
        category_objs = []
        for name, description in categories:
            obj, _ = self.get_or_create_by_fields(
                HazardCategoryMaster,
                {"category_name": name},
                {"description": description, "is_active": True},
            )
            category_objs.append(obj)
        masters["Hazard Categories"] = len(category_objs)

        hazards = [
            ("Chemical", "Solvent Vapour", "Organic solvent vapour exposure"),
            ("Chemical", "Welding Fume", "Metal fume generated during welding"),
            ("Physical", "Noise", "Occupational noise exposure"),
            ("Physical", "Heat Stress", "Thermal stress in hot work areas"),
            ("Dust", "Respirable Dust", "Respirable airborne particulate"),
            ("Dust", "Silica Dust", "Crystalline silica exposure"),
            ("Biological", "Bioaerosol", "Airborne biological contaminants"),
        ]
        hazard_objs = []
        for cat_name, name, description in hazards:
            category = next(x for x in category_objs if x.category_name == cat_name)
            obj, _ = self.get_or_create_by_fields(
                HazardMaster,
                {"hazard_category": category, "hazard": name},
                {"description": description, "is_active": True},
            )
            hazard_objs.append(obj)
        masters["Hazards"] = len(hazard_objs)

        exposure_types = [
            ("Inhalation", "Inhalation exposure"),
            ("Dermal", "Skin contact exposure"),
            ("Noise", "Noise exposure"),
            ("Thermal", "Heat exposure"),
            ("Particulate", "Particulate exposure"),
        ]
        exposure_type_objs = []
        for name, description in exposure_types:
            obj, _ = self.get_or_create_by_fields(
                ExposureTypeMaster,
                {"exposure_type": name},
                {"description": description, "is_active": True},
            )
            exposure_type_objs.append(obj)
        masters["Exposure Types"] = len(exposure_type_objs)

        groups = [
            ("Welders", "Welding personnel"),
            ("Paint Shop Operators", "Paint and solvent handling personnel"),
            ("Production Operators", "General production personnel"),
            ("Maintenance Team", "Maintenance and utility personnel"),
            ("Material Handling Team", "Material handling personnel"),
        ]
        group_objs = []
        for name, description in groups:
            obj, _ = self.get_or_create_by_fields(
                ExposureGroupMaster,
                {"exposure_group": name},
                {"description": description, "is_active": True},
            )
            group_objs.append(obj)
        masters["Exposure Groups"] = len(group_objs)

        monitoring_types = [
            ("Personal Monitoring", "Personal exposure monitoring"),
            ("Area Monitoring", "Fixed area monitoring"),
            ("Source Monitoring", "Source or process monitoring"),
            ("Environmental Monitoring", "Workplace environmental monitoring"),
        ]
        monitoring_type_objs = []
        for name, description in monitoring_types:
            obj, _ = self.get_or_create_by_fields(
                MonitoringTypeMaster,
                {"monitoring_type": name},
                {"description": description, "is_active": True},
            )
            monitoring_type_objs.append(obj)
        masters["Monitoring Types"] = len(monitoring_type_objs)

        parameters = [
            ("Noise Level", "Occupational noise level"),
            ("Respirable Dust", "Respirable particulate concentration"),
            ("Silica", "Crystalline silica concentration"),
            ("VOC", "Volatile organic compound concentration"),
            ("Heat Stress WBGT", "Wet bulb globe temperature"),
        ]
        parameter_objs = []
        for name, description in parameters:
            obj, _ = self.get_or_create_by_fields(
                MonitoringParameterMaster,
                {"parameter_name": name},
                {"description": description, "is_active": True},
            )
            parameter_objs.append(obj)
        masters["Monitoring Parameters"] = len(parameter_objs)

        units = [
            ("Decibel", "dB"),
            ("Milligram per Cubic Meter", "mg/m3"),
            ("Parts per Million", "ppm"),
            ("Degree Celsius", "°C"),
        ]
        unit_objs = []
        for name, symbol in units:
            obj, _ = self.get_or_create_by_fields(
                UnitMaster,
                {"unit_name": name, "unit_symbol": symbol},
                {"description": f"Industrial Hygiene unit: {symbol}", "is_active": True},
            )
            unit_objs.append(obj)
        masters["Units"] = len(unit_objs)

        # Map parameters to suitable units and OEL values.
        parameter_map = {
            "Noise Level": next(x for x in unit_objs if x.unit_symbol == "dB"),
            "Respirable Dust": next(x for x in unit_objs if x.unit_symbol == "mg/m3"),
            "Silica": next(x for x in unit_objs if x.unit_symbol == "mg/m3"),
            "VOC": next(x for x in unit_objs if x.unit_symbol == "ppm"),
            "Heat Stress WBGT": next(x for x in unit_objs if x.unit_symbol == "°C"),
        }
        limit_values = {
            "Noise Level": Decimal("85.0000"),
            "Respirable Dust": Decimal("3.0000"),
            "Silica": Decimal("0.0500"),
            "VOC": Decimal("50.0000"),
            "Heat Stress WBGT": Decimal("30.0000"),
        }

        oel_objs = []
        for hazard_index, hazard in enumerate(hazard_objs):
            for parameter in parameter_objs:
                unit = parameter_map[parameter.parameter_name]
                value = limit_values[parameter.parameter_name]
                obj, _ = self.get_or_create_by_fields(
                    ExposureLimitMaster,
                    {
                        "hazard": hazard,
                        "monitoring_parameter": parameter,
                        "unit": unit,
                        "exposure_limit_type": "OEL",
                        "applicable_standard": "Applicable Occupational Exposure Limit",
                    },
                    {
                        "limit_value": value,
                        "source_reference": "Demo reference - configure organization standard",
                        "effective_from": self.fy_start,
                        "effective_to": None,
                        "is_active": True,
                    },
                )
                oel_objs.append(obj)

        masters["Exposure Limits"] = len(oel_objs)

        instruments = [
            ("Sound Level Meter", "Noise Level"),
            ("Personal Noise Dosimeter", "Noise Level"),
            ("Respirable Dust Monitor", "Respirable Dust"),
            ("VOC Monitor", "VOC"),
            ("WBGT Meter", "Heat Stress WBGT"),
        ]
        instrument_objs = []
        for index, (name, parameter_name) in enumerate(instruments):
            parameter = next(x for x in parameter_objs if x.parameter_name == parameter_name)
            code = f"IH-INST-{index + 1:03d}"
            obj = InstrumentMaster.objects.filter(instrument_code=code).first()
            if not obj:
                obj = InstrumentMaster.objects.create(
                    instrument_name=name,
                    instrument_code=code,
                    instrument_type="Industrial Hygiene Instrument",
                    manufacturer="Demo Instruments",
                    model_number=f"MODEL-{index + 1:03d}",
                    serial_number=f"SN-IH-{index + 1:05d}",
                    measurement_parameter=parameter,
                    calibration_frequency="6 Months",
                    last_calibration_date=self.fy_start,
                    next_calibration_date=min(self.fy_start + timedelta(days=180), self.today),
                    description="Demo Industrial Hygiene monitoring instrument",
                    is_active=True,
                )
            instrument_objs.append(obj)
        masters["Instruments"] = len(instrument_objs)

        labs = [
            ("Central Occupational Hygiene Laboratory", "LAB-IH-001"),
            ("Environmental Testing Laboratory", "LAB-IH-002"),
        ]
        lab_objs = []
        for name, code in labs:
            obj = LaboratoryMaster.objects.filter(laboratory_code=code).first()
            if not obj:
                obj = LaboratoryMaster.objects.create(
                    laboratory_name=name,
                    laboratory_code=code,
                    accreditation="NABL / Equivalent Demo Accreditation",
                    contact_person="IH Laboratory Team",
                    contact_number="9000000000",
                    email=f"{code.lower()}@example.com",
                    address="Demo Industrial Area",
                    description="Demo laboratory for Industrial Hygiene sample analysis",
                    is_active=True,
                )
            lab_objs.append(obj)
        masters["Laboratories"] = len(lab_objs)

        masters["_hazards"] = hazard_objs
        masters["_exposure_types"] = exposure_type_objs
        masters["_exposure_groups"] = group_objs
        masters["_monitoring_types"] = monitoring_type_objs
        masters["_parameters"] = parameter_objs
        masters["_units"] = unit_objs
        masters["_oels"] = oel_objs
        masters["_instruments"] = instrument_objs
        masters["_labs"] = lab_objs
        return masters

    # ------------------------------------------------------------------
    # Program and planning
    # ------------------------------------------------------------------

    def seed_program(self, masters):
        plant = self.plant_for(0)
        responsible = self.user_for(0)
        obj = IHProgramMaster.objects.filter(program_code="IH-DEMO-2026-001").first()
        if obj:
            return obj

        return IHProgramMaster.objects.create(
            program_name="Industrial Hygiene Monitoring Program",
            program_code="IH-DEMO-2026-001",
            plant=plant,
            description="Demo Industrial Hygiene program for the current financial year.",
            objectives="Identify, monitor and control workplace exposure risks.",
            scope="Production, maintenance, utility and support areas.",
            responsible_person=responsible,
            start_date=self.fy_start,
            end_date=self.today,
            review_frequency="Half Yearly",
            last_review_date=self.today,
            next_review_date=self.today,
            status="ACTIVE",
            is_active=True,
        )

    def seed_monitoring_plans(self, program, masters):
        plans = []
        for index in range(self.records):
            user = self.user_for(index)
            plant = self.plant_for(index)
            hazard = masters["_hazards"][index % len(masters["_hazards"])]
            exposure_type = masters["_exposure_types"][index % len(masters["_exposure_types"])]
            group = masters["_exposure_groups"][index % len(masters["_exposure_groups"])]
            mtype = masters["_monitoring_types"][index % len(masters["_monitoring_types"])]
            parameter = masters["_parameters"][index % len(masters["_parameters"])]
            unit = next(
                u for u in masters["_units"]
                if u.unit_symbol == {
                    "Noise Level": "dB",
                    "Respirable Dust": "mg/m3",
                    "Silica": "mg/m3",
                    "VOC": "ppm",
                    "Heat Stress WBGT": "°C",
                }[parameter.parameter_name]
            )
            oel = next(
                o for o in masters["_oels"]
                if o.monitoring_parameter_id == parameter.id
                and o.unit_id == unit.id
            )

            status = (
                "COMPLETED" if index % 10 in (0, 1, 2, 3) else
                "CLOSED" if index % 10 == 8 else
                "DRAFT" if index % 10 == 9 else
                "ACTIVE"
            )
            start = self.demo_date(index)
            obj = MonitoringPlan.objects.create(
                plan_name=f"{parameter.parameter_name} Monitoring Plan {index + 1}",
                plan_code=self.unique_code("IH-PLAN", index),
                ih_program=program,
                plant=plant,
                hazard=hazard,
                exposure_type=exposure_type,
                exposure_group=group,
                monitoring_type=mtype,
                monitoring_parameter=parameter,
                unit=unit,
                exposure_limit=oel,
                monitoring_frequency=["Monthly", "Quarterly", "Half Yearly"][index % 3],
                planned_start_date=start,
                planned_end_date=start,
                sample_count=1 + (index % 5),
                area_or_location=f"Production Area {1 + (index % 8)}",
                department=f"Department {1 + (index % 6)}",
                responsible_person=user,
                remarks="Demo monitoring plan for current FY.",
                status=status,
                is_active=status != "CLOSED",
            )
            plans.append(obj)
        return plans

    def seed_schedules(self, plans):
        schedules = []
        for index, plan in enumerate(plans):
            status = (
                "COMPLETED" if index % 10 in (0, 1, 2, 3) else
                "CANCELLED" if index % 10 == 9 else
                "OVERDUE" if index % 10 in (4, 5) else
                "IN_PROGRESS" if index % 10 in (6, 7) else
                "SCHEDULED"
            )
            planned = self.demo_date(index)
            schedules.append(
                MonitoringSchedule.objects.create(
                    schedule_name=f"{plan.plan_name} Schedule",
                    schedule_code=self.unique_code("IH-SCH", index),
                    monitoring_plan=plan,
                    planned_date=planned,
                    scheduled_start_date=planned,
                    scheduled_end_date=planned,
                    frequency=plan.monitoring_frequency,
                    sample_count=plan.sample_count,
                    responsible_person=plan.responsible_person,
                    assigned_to=self.user_for(index + 1),
                    status=status,
                    remarks="Demo monitoring schedule.",
                    is_active=status != "CANCELLED",
                )
            )
        return schedules

    # ------------------------------------------------------------------
    # Sampling and measurement
    # ------------------------------------------------------------------

    def seed_sampling(self, schedules, masters):
        records = []
        for index, schedule in enumerate(schedules):
            status_map = {
                "COMPLETED": "RESULT_RECEIVED",
                "IN_PROGRESS": "SAMPLED",
                "OVERDUE": "PLANNED",
                "SCHEDULED": "PLANNED",
                "CANCELLED": "CANCELLED",
            }
            status = status_map[schedule.status]
            sample_date = schedule.planned_date
            start_time = time(9 + (index % 3), 0)
            end_time = time(10 + (index % 3), 0)

            parameter = schedule.monitoring_plan.monitoring_parameter
            hazard = schedule.monitoring_plan.hazard
            exposure_type = schedule.monitoring_plan.exposure_type
            group = schedule.monitoring_plan.exposure_group
            unit = schedule.monitoring_plan.unit
            instrument = masters["_instruments"][index % len(masters["_instruments"])]
            lab = masters["_labs"][index % len(masters["_labs"])]

            sent_to_lab = (
                min(sample_date + timedelta(days=1), self.today)
                if status in ("SENT_TO_LAB", "RESULT_RECEIVED")
                else None
            )
            records.append(
                SamplingManagement.objects.create(
                    sampling_code=self.unique_code("IH-SAMP", index),
                    monitoring_schedule=schedule,
                    sample_number=f"SAMPLE-{self.prefix}-{index + 1:04d}",
                    sampling_date=sample_date,
                    sampling_start_time=start_time,
                    sampling_end_time=end_time,
                    hazard=hazard,
                    exposure_type=exposure_type,
                    exposure_group=group,
                    area_or_location=f"Production Area {1 + (index % 8)}",
                    department=f"Department {1 + (index % 6)}",
                    monitoring_parameter=parameter,
                    unit=unit,
                    instrument=instrument,
                    laboratory=lab,
                    sample_type="Personal Sample" if index % 2 == 0 else "Area Sample",
                    sample_quantity=Decimal("1.0000"),
                    sampling_method="Standard manual industrial hygiene sampling method",
                    collected_by=self.user_for(index),
                    sent_to_lab_date=sent_to_lab,
                    laboratory_reference=f"LABREF-{self.prefix}-{index + 1:04d}" if sent_to_lab else None,
                    status=status,
                    remarks="Manual sample collection demo record.",
                    is_active=status != "CANCELLED",
                )
            )
        return records

    def measurement_value(self, index, parameter):
        normal_values = {
            "Noise Level": Decimal("78.000000"),
            "Respirable Dust": Decimal("1.800000"),
            "Silica": Decimal("0.030000"),
            "VOC": Decimal("32.000000"),
            "Heat Stress WBGT": Decimal("27.500000"),
        }
        exceed_values = {
            "Noise Level": Decimal("92.000000"),
            "Respirable Dust": Decimal("4.800000"),
            "Silica": Decimal("0.090000"),
            "VOC": Decimal("72.000000"),
            "Heat Stress WBGT": Decimal("32.500000"),
        }
        return exceed_values[parameter.parameter_name] if index % 5 == 0 else normal_values[parameter.parameter_name]

    def seed_measurements(self, samplings, masters):
        entries = []
        for index, sampling in enumerate(samplings):
            status = (
                "VERIFIED" if sampling.status == "RESULT_RECEIVED" and index % 5 != 0 else
                "ENTERED" if sampling.status in ("RESULT_RECEIVED", "SAMPLED") else
                "CANCELLED" if sampling.status == "CANCELLED" else
                "DRAFT"
            )
            parameter = sampling.monitoring_parameter
            value = self.measurement_value(index, parameter)
            entered_by = self.user_for(index)
            verified_by = self.user_for(index + 1) if status == "VERIFIED" else None
            entries.append(
                MeasurementEntry.objects.create(
                    sampling=sampling,
                    measurement_code=self.unique_code("IH-MEAS", index),
                    measurement_date=sampling.sampling_date,
                    monitoring_parameter=parameter,
                    unit=sampling.unit,
                    measured_value=value,
                    detection_limit=Decimal("0.001000"),
                    result_remarks="Above indicative limit." if index % 5 == 0 else "Within indicative limit.",
                    entered_by=entered_by,
                    verified_by=verified_by,
                    verification_date=sampling.sampling_date if status == "VERIFIED" else None,
                    status=status,
                    is_active=status != "CANCELLED",
                )
            )
        return entries

    def seed_lab_results(self, samplings, measurements, masters):
        results = []
        for index, (sampling, measurement) in enumerate(zip(samplings, measurements)):
            if sampling.status not in ("RESULT_RECEIVED", "SENT_TO_LAB"):
                continue

            status = (
                "VERIFIED" if index % 4 != 0 else
                "UNDER_REVIEW" if index % 4 == 0 else
                "RECEIVED"
            )
            if index % 17 == 0:
                status = "REJECTED"

            result_date = min(sampling.sampling_date + timedelta(days=2), self.today)
            results.append(
                LaboratoryResult.objects.create(
                    sampling=sampling,
                    laboratory=sampling.laboratory,
                    measurement=measurement,
                    result_code=self.unique_code("IH-LAB", index),
                    laboratory_reference=sampling.laboratory_reference,
                    result_date=result_date,
                    monitoring_parameter=sampling.monitoring_parameter,
                    unit=sampling.unit,
                    result_value=measurement.measured_value,
                    detection_limit=Decimal("0.001000"),
                    test_method="Laboratory analytical method - Demo",
                    certificate_number=f"CERT-{self.prefix}-{index + 1:04d}",
                    certificate_date=result_date,
                    remarks="Demo laboratory result.",
                    received_by=self.user_for(index),
                    verified_by=self.user_for(index + 1) if status == "VERIFIED" else None,
                    verification_date=result_date if status == "VERIFIED" else None,
                    status=status,
                    is_active=status != "REJECTED",
                )
            )
        return results

    # ------------------------------------------------------------------
    # Exposure assessment and compliance
    # ------------------------------------------------------------------

    def find_lab_result(self, lab_results, sampling_id):
        for result in lab_results:
            if result.sampling_id == sampling_id:
                return result
        return None

    def seed_assessments(self, samplings, measurements, lab_results, masters):
        assessments = []
        for index, (sampling, measurement) in enumerate(zip(samplings, measurements)):
            lab = self.find_lab_result(lab_results, sampling.id)
            parameter = sampling.monitoring_parameter
            oel = ExposureLimitMaster.objects.filter(
                hazard=sampling.hazard,
                monitoring_parameter=parameter,
                unit=sampling.unit,
            ).first()

            exceeds = index % 5 == 0
            compliance = "EXCEEDS_LIMIT" if exceeds else "WITHIN_LIMIT"
            risk = ["LOW", "MEDIUM", "HIGH", "CRITICAL"][index % 4] if exceeds else ["LOW", "MEDIUM"][index % 2]
            status = (
                "APPROVED" if index % 10 in (0, 1, 2, 3) else
                "CLOSED" if index % 10 == 8 else
                "UNDER_REVIEW" if index % 10 in (4, 5) else
                "ASSESSED"
            )
            limit_value = oel.limit_value if oel else None

            assessments.append(
                ExposureAssessment.objects.create(
                    assessment_code=self.unique_code("IH-ASMT", index),
                    sampling=sampling,
                    measurement=measurement,
                    laboratory_result=lab,
                    hazard=sampling.hazard,
                    exposure_type=sampling.exposure_type,
                    exposure_group=sampling.exposure_group,
                    area_or_location=sampling.area_or_location,
                    department=sampling.department,
                    employee_name=self.user_for(index).get_full_name() or self.user_for(index).username,
                    monitoring_parameter=parameter,
                    unit=sampling.unit,
                    measured_value=measurement.measured_value,
                    applicable_oel=oel,
                    exposure_limit_value=limit_value,
                    compliance_status=compliance,
                    risk_level=risk,
                    existing_controls="Local exhaust ventilation, PPE and administrative controls.",
                    assessment_remarks="Exposure exceeds indicative OEL." if exceeds else "Exposure is within indicative OEL.",
                    assessment_date=sampling.sampling_date,
                    assessor=self.user_for(index),
                    status=status,
                    is_active=status != "CLOSED",
                )
            )
        return assessments

    def seed_compliance(self, assessments, samplings, measurements, lab_results, masters):
        records = []
        for index, assessment in enumerate(assessments):
            oel = assessment.applicable_oel
            limit = assessment.exposure_limit_value
            value = assessment.measured_value
            exceeds = assessment.compliance_status == "EXCEEDS_LIMIT"

            exceedance = (value - limit) if (exceeds and limit is not None) else None
            percentage = (
                ((value - limit) / limit * Decimal("100.0000"))
                if exceeds and limit and limit > 0
                else None
            )
            status = (
                "NON_COMPLIANT" if exceeds and index % 7 != 0 else
                "COMPLIANT" if not exceeds and index % 10 not in (4, 5) else
                "UNDER_REVIEW" if index % 10 in (4, 5) else
                "CLOSED"
            )
            if index % 11 == 0:
                status = "ASSESSED"

            records.append(
                ComplianceRecord.objects.create(
                    compliance_code=self.unique_code("IH-COMP", index),
                    exposure_assessment=assessment,
                    sampling=assessment.sampling,
                    measurement=assessment.measurement,
                    laboratory_result=assessment.laboratory_result,
                    hazard=assessment.hazard,
                    exposure_group=assessment.exposure_group,
                    area_or_location=assessment.area_or_location,
                    department=assessment.department,
                    employee_name=assessment.employee_name,
                    monitoring_parameter=assessment.monitoring_parameter,
                    unit=assessment.unit,
                    measured_value=value,
                    applicable_oel=oel,
                    exposure_limit_value=limit,
                    exceedance_value=exceedance,
                    exceedance_percentage=percentage,
                    compliance_status=assessment.compliance_status,
                    risk_level=assessment.risk_level,
                    investigation_required=exceeds,
                    investigation_details="Investigation initiated for exposure exceedance." if exceeds else None,
                    remarks="Demo compliance evaluation.",
                    assessment_date=assessment.assessment_date,
                    assessed_by=self.user_for(index),
                    status=status,
                    is_active=status != "CLOSED",
                )
            )
        return records

    # ------------------------------------------------------------------
    # Corrective action and re-monitoring
    # ------------------------------------------------------------------

    def seed_exceedances(self, compliance_records, assessments, samplings, measurements, lab_results, masters):
        actions = []
        for index, compliance in enumerate(compliance_records):
            if compliance.compliance_status != "EXCEEDS_LIMIT":
                continue

            status = (
                "CLOSED" if index % 5 == 0 else
                "PENDING_VERIFICATION" if index % 5 == 1 else
                "ACTION_IN_PROGRESS" if index % 5 in (2, 3) else
                "UNDER_INVESTIGATION"
            )
            due_date = min(compliance.assessment_date + timedelta(days=15), self.today)
            closed = status == "CLOSED"
            actions.append(
                ExceedanceAction.objects.create(
                    exceedance_code=self.unique_code("IH-EXC", index),
                    compliance_record=compliance,
                    exposure_assessment=compliance.exposure_assessment,
                    sampling=compliance.sampling,
                    measurement=compliance.measurement,
                    laboratory_result=compliance.laboratory_result,
                    hazard=compliance.hazard,
                    exposure_group=compliance.exposure_group,
                    area_or_location=compliance.area_or_location,
                    department=compliance.department,
                    employee_name=compliance.employee_name,
                    measured_value=compliance.measured_value,
                    applicable_limit=compliance.exposure_limit_value,
                    exceedance_value=compliance.exceedance_value,
                    exceedance_percentage=compliance.exceedance_percentage,
                    risk_level=compliance.risk_level,
                    priority=["MEDIUM", "HIGH", "CRITICAL"][index % 3],
                    investigation_required=True,
                    investigation_details="Root cause investigation for exposure exceedance.",
                    root_cause="Process variation / inadequate exposure control - demo.",
                    immediate_action="Review work practice and reinforce PPE/control measures.",
                    corrective_action="Improve engineering and administrative controls and repeat monitoring.",
                    responsible_person=self.user_for(index + 1),
                    due_date=due_date,
                    evidence="Demo corrective action evidence.",
                    verification_details="Corrective action verified." if closed else None,
                    verified_by=self.user_for(index + 2) if closed else None,
                    verification_date=due_date if closed else None,
                    closure_remarks="Closed after verification." if closed else None,
                    closure_date=due_date if closed else None,
                    status=status,
                    is_active=not status == "CANCELLED",
                )
            )
        return actions

    def seed_remonitoring(self, exceedances, samplings, measurements, masters):
        records = []
        for index, action in enumerate(exceedances):
            if index % 2 != 0:
                continue

            status = (
                "CLOSED" if index % 6 == 0 else
                "COMPLIANT" if index % 6 in (1, 2) else
                "NON_COMPLIANT" if index % 6 == 3 else
                "RESULT_RECEIVED"
            )
            effective = (
                "EFFECTIVE" if status in ("CLOSED", "COMPLIANT") else
                "NOT_EFFECTIVE" if status == "NON_COMPLIANT" else
                "PARTIALLY_EFFECTIVE"
            )
            planned = min(action.due_date or self.today, self.today)
            actual = min(planned + timedelta(days=1), self.today) if status not in ("PLANNED", "SCHEDULED") else None
            new_value = (
                action.applicable_limit * Decimal("0.80")
                if action.applicable_limit and status in ("CLOSED", "COMPLIANT")
                else action.applicable_limit * Decimal("1.20")
                if action.applicable_limit and status == "NON_COMPLIANT"
                else action.measured_value
            )

            records.append(
                ReMonitoring.objects.create(
                    re_monitoring_code=self.unique_code("IH-REMON", index),
                    exceedance_action=action,
                    original_sampling=action.sampling,
                    original_measurement=action.measurement,
                    original_result_value=action.measured_value,
                    original_limit_value=action.applicable_limit,
                    reason="Re-monitor after exposure exceedance corrective action.",
                    re_monitoring_required=True,
                    planned_date=planned,
                    actual_sampling_date=actual,
                    hazard=action.hazard,
                    exposure_group=action.exposure_group,
                    area_or_location=action.area_or_location,
                    department=action.department,
                    employee_name=action.employee_name,
                    monitoring_parameter=action.sampling.monitoring_parameter,
                    unit=action.sampling.unit,
                    new_sampling=action.sampling if status not in ("PLANNED", "SCHEDULED") else None,
                    new_measurement=action.measurement if status not in ("PLANNED", "SCHEDULED") else None,
                    new_result_value=new_value,
                    applicable_limit=action.applicable_limit,
                    comparison_with_previous="Exposure reduced after corrective action." if status in ("CLOSED", "COMPLIANT") else "Further control improvement required.",
                    compliance_status=(
                        "WITHIN_LIMIT" if status in ("CLOSED", "COMPLIANT") else
                        "EXCEEDS_LIMIT" if status == "NON_COMPLIANT" else
                        "NOT_ASSESSED"
                    ),
                    effectiveness=effective,
                    effectiveness_remarks="Controls effective." if effective == "EFFECTIVE" else "Additional controls required.",
                    conducted_by=self.user_for(index),
                    verified_by=self.user_for(index + 1) if status == "CLOSED" else None,
                    verification_date=actual if status == "CLOSED" else None,
                    closure_remarks="Re-monitoring closed." if status == "CLOSED" else None,
                    closure_date=actual if status == "CLOSED" else None,
                    status=status,
                    is_active=status != "CANCELLED",
                )
            )
        return records
