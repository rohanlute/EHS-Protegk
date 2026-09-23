# ============================================================
## run to generate data:
## python manage.py demo_data_occupational_health
## Or explicitly for related to employees available:
## python manage.py demo_data_occupational_health --count 13 --records 100
# ============================================================
# ============================================================
# Occupational Health Demo Data Seeder
# Creates realistic demo data using existing users and
# existing organization assignments.
# ============================================================

from datetime import date, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from apps.accounts.models import User
from apps.occupational_health.models import (
    ExaminationType,
    MedicalTest,
    ExposureType,
    HealthCondition,
    FitnessStatus,
    Restriction,
    Vaccination,
    MedicalProfessional,
    MedicalFacility,
    EmployeeHealthProfile,
    MedicalExamination,
    MedicalTestResult,
    FitnessToWork,
    HealthSurveillance,
    EmployeeExposure,
    MedicalFollowUp,
    EmployeeVaccination,
    EmployeeOccupationalDisease,
    HealthIncident,
    ReturnToWork,
    MedicalRecord,
    HealthCamp,
    HealthCampParticipation,
)


class Command(BaseCommand):
    help = (
        "Create realistic Occupational Health demo data using "
        "existing employees and existing organization structure."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=None,
            help="Number of existing employees to use. If omitted, all eligible employees are used.",
        )
        parser.add_argument(
            "--records",
            type=int,
            default=100,
            help="Number of Occupational Health transaction records to generate.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        records = options["records"]

        if records < 1:
            raise CommandError("Records must be greater than 0.")

        if count is not None and count < 1:
            raise CommandError("Employee count must be greater than 0.")

        # Current Indian financial year: 1 April 2026 to today (23 September 2026).
        # The end date automatically follows the server date when the command is run.
        today = timezone.localdate()
        current_fy_start = date(
            today.year if today.month >= 4 else today.year - 1,
            4,
            1,
        )
        current_fy_end = today

        self.fy_start = current_fy_start
        self.fy_end = current_fy_end
        self.demo_records = records

        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "Starting Occupational Health demo data creation..."
            )
        )
        self.stdout.write("")

        # ============================================================
        # 1. Get existing users only
        # ============================================================

        users = list(
            User.objects.filter(
                is_active=True,
                is_active_employee=True,
            )
            .exclude(is_superuser=True)
            .select_related(
                "department",
                "plant",
                "zone",
                "location",
                "sublocation",
            )
            .order_by("id")
        )

        if not users:
            raise CommandError("No active employees are available for demo data.")

        if count is None:
            selected_users = users
        else:
            if len(users) < count:
                self.stdout.write(
                    self.style.WARNING(
                        f"Requested {count} employees, but only {len(users)} "
                        "active employees are available. Using all {len(users)} employees."
                    )
                )
                selected_users = users
            else:
                selected_users = users[:count]

        self.stdout.write(
            self.style.SUCCESS(
                f"Using {len(selected_users)} existing employees."
            )
        )

        # ============================================================
        # 2. Display existing organization structure being reused
        # ============================================================

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Existing Organization Assignments"
            )
        )

        for user in selected_users:
            department = (
                user.department.name
                if user.department
                else "Not Assigned"
            )
            plant = (
                user.plant.name
                if user.plant
                else "Not Assigned"
            )
            zone = (
                user.zone.name
                if user.zone
                else "Not Assigned"
            )
            location = (
                user.location.name
                if user.location
                else "Not Assigned"
            )
            sublocation = (
                user.sublocation.name
                if user.sublocation
                else "Not Assigned"
            )

            self.stdout.write(
                f"  {user.username} | "
                f"Department: {department} | "
                f"Plant: {plant} | "
                f"Zone: {zone} | "
                f"Location: {location} | "
                f"SubLocation: {sublocation}"
            )

        # ============================================================
        # 3. Create Occupational Health master data
        # ============================================================

        masters = self.create_master_data(selected_users[0])

        # ============================================================
        # 4. Create Employee Health Profiles
        # ============================================================

        profiles = []

        for index, user in enumerate(selected_users):
            profile, _ = EmployeeHealthProfile.objects.update_or_create(
                employee=user,
                defaults={
                    "date_of_birth": (
                        user.date_of_birth
                        or date(1990 + (index % 8), 3 + (index % 8), 10 + (index % 15))
                    ),
                    "gender": (
                        user.gender
                        if user.gender in dict(EmployeeHealthProfile.GENDER_CHOICES)
                        else "NOT_SPECIFIED"
                    ),
                    "blood_group": [
                        "A_POSITIVE",
                        "B_POSITIVE",
                        "O_POSITIVE",
                        "AB_POSITIVE",
                        "A_NEGATIVE",
                    ][index % 5],
                    "emergency_contact_name": "Emergency Contact",
                    "emergency_contact_number": f"98{10000000 + index:08d}",
                    "date_of_joining": (
                        user.date_joined_company
                        or date(2020 + (index % 5), 1 + (index % 10), 5 + (index % 20))
                    ),
                    "work_shift": [
                        "General Shift",
                        "Morning Shift",
                        "Evening Shift",
                        "Night Shift",
                    ][index % 4],
                    "employment_type": (
                        user.employment_type
                        if user.employment_type
                        in dict(EmployeeHealthProfile.EMPLOYMENT_TYPE_CHOICES)
                        else "PERMANENT"
                    ),
                    "job_role": user.job_title or "Production Employee",
                    "work_area": (
                        user.location.name
                        if user.location
                        else "Production Area"
                    ),
                    "health_profile_status": "ACTIVE",
                    "is_under_health_surveillance": True,
                    "is_active": True,
                    "created_by": user,
                },
            )

            profiles.append(profile)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created/updated {len(profiles)} Employee Health Profiles."
            )
        )

        # ============================================================
        # 5. Create Medical Examinations and Test Results
        # ============================================================

        examinations = []
        test_results = []

        for index in range(records):
            profile = profiles[index % len(profiles)]
            user = profile.employee

            examination_date = self.demo_date(index)

            follow_up_required = index % 3 == 0
            follow_up_date = (
                examination_date + timedelta(days=30)
                if follow_up_required
                else None
            )

            examination = MedicalExamination.objects.create(
                employee_health_profile=profile,
                examination_type=masters["examination_types"][
                    index % len(masters["examination_types"])
                ],
                examination_date=examination_date,
                purpose=[
                    "PERIODIC",
                    "ANNUAL",
                    "SPECIAL",
                    "PERIODIC",
                    "ANNUAL",
                ][index % 5],
                medical_professional=masters["professionals"][
                    index % len(masters["professionals"])
                ],
                medical_facility=masters["facilities"][
                    index % len(masters["facilities"])
                ],
                job_role=profile.job_role,
                work_area=profile.work_area,
                general_findings=(
                    "General health examination completed. "
                    "Employee is clinically stable."
                ),
                abnormal_findings=(
                    "No significant abnormal findings."
                    if index % 3
                    else "Mild elevated blood pressure noted."
                ),
                recommendations=(
                    "Maintain healthy lifestyle and attend periodic "
                    "occupational health examination."
                ),
                follow_up_required=follow_up_required,
                follow_up_date=follow_up_date,
                status=(
                    "COMPLETED"
                    if index % 10 not in [7, 8]
                    else ("SCHEDULED" if index % 10 == 7 else "CANCELLED")
                ),
                created_by=user,
            )

            examinations.append(examination)

            # --------------------------------------------------------
            # Medical Test 1
            # --------------------------------------------------------

            result1 = MedicalTestResult.objects.create(
                medical_examination=examination,
                medical_test=masters["tests"][0],
                test_date=examination_date,
                result_value=str(118 + index),
                unit="mmHg",
                reference_range="100-140 mmHg",
                result_status=(
                    "BORDERLINE"
                    if index % 5 == 0
                    else (
                        "ABNORMAL"
                        if index % 17 == 0
                        else ("PENDING" if index % 11 == 0 else "NORMAL")
                    )
                ),
                findings=(
                    "Blood pressure within acceptable range."
                    if index % 4
                    else "Blood pressure reading normal."
                ),
                recommendations="Continue routine monitoring.",
                doctor_comments="No immediate medical concern.",
                follow_up_required=False,
                follow_up_date=None,
                created_by=user,
            )

            test_results.append(result1)

            # --------------------------------------------------------
            # Medical Test 2
            # --------------------------------------------------------

            result2 = MedicalTestResult.objects.create(
                medical_examination=examination,
                medical_test=masters["tests"][1],
                test_date=examination_date,
                result_value=str(96 - (index % 3)),
                unit="%",
                reference_range="95-100%",
                result_status=(
                    "NORMAL"
                    if index % 12 != 0
                    else "PENDING"
                ),
                findings=(
                    "Oxygen saturation within normal range."
                    if index % 12 != 0
                    else "Test result is awaiting final review."
                ),
                recommendations="No specific action required.",
                doctor_comments="Normal screening result.",
                follow_up_required=False,
                follow_up_date=None,
                created_by=user,
            )

            test_results.append(result2)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(examinations)} Medical Examinations."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(test_results)} Medical Test Results."
            )
        )

        # ============================================================
        # 6. Fitness To Work
        # ============================================================

        fitness_records = []

        for index in range(records):
            profile = profiles[index % len(profiles)]
            assessment_date = self.demo_date(index)

            is_restricted = index % 5 == 0
            is_temporarily_unfit = index % 23 == 0
            is_unfit = index % 47 == 0

            fitness = FitnessToWork.objects.create(
                medical_examination=examinations[index],
                employee_health_profile=profile,
                assessment_date=assessment_date,
                assessment_type="PERIODIC",
                fitness_status=(
                    "UNFIT"
                    if is_unfit
                    else (
                        "TEMPORARILY_UNFIT"
                        if is_temporarily_unfit
                        else (
                            "FIT_WITH_RESTRICTIONS"
                            if is_restricted
                            else "FIT"
                        )
                    )
                ),
                valid_from=assessment_date,
                valid_until=assessment_date + relativedelta(months=12),
                medical_findings=(
                    "Employee medically fit for assigned duties."
                ),
                work_recommendations=(
                    "Employee temporarily not fit for assigned duties."
                    if is_unfit or is_temporarily_unfit
                    else (
                        "Avoid prolonged heavy lifting."
                        if is_restricted
                        else "Normal work permitted."
                    )
                ),
                doctor_comments="Fitness assessment completed.",
                follow_up_required=False,
                follow_up_date=None,
                status=True,
                created_by=profile.employee,
            )

            if is_restricted:
                fitness.restrictions.add(
                    masters["restrictions"][0]
                )
            elif is_temporarily_unfit:
                fitness.restrictions.add(
                    masters["restrictions"][2]
                )

            fitness_records.append(fitness)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(fitness_records)} Fitness To Work records."
            )
        )

        # ============================================================
        # 7. Health Surveillance
        # ============================================================

        surveillance_records = []

        for index in range(records):
            profile = profiles[index % len(profiles)]
            start_date = self.demo_date(index)

            surveillance = HealthSurveillance.objects.create(
                employee_health_profile=profile,
                exposure_type=masters["exposure_types"][
                    index % len(masters["exposure_types"])
                ],
                surveillance_name=(
                    f"Occupational Health Surveillance - "
                    f"{profile.employee.get_full_name() or profile.employee.username}"
                ),
                surveillance_frequency=[
                    "YEARLY",
                    "HALF_YEARLY",
                    "QUARTERLY",
                    "YEARLY",
                ][index % 4],
                start_date=start_date,
                next_due_date=(
                    self.fy_end - timedelta(days=5)
                    if index % 11 == 0
                    else (
                        self.fy_end - timedelta(days=15)
                        if index % 7 == 0
                        else self.fy_end + timedelta(days=45 + (index % 60))
                    )
                ),
                end_date=(
                    self.demo_date(index)
                    if index % 19 == 0
                    else None
                ),
                responsible_medical_professional=masters["professionals"][
                    index % len(masters["professionals"])
                ],
                medical_facility=masters["facilities"][
                    index % len(masters["facilities"])
                ],
                health_objectives=(
                    "Monitor employee health in relation to workplace "
                    "exposure and occupational risks."
                ),
                remarks="Demo surveillance record.",
                status=(
                    "COMPLETED"
                    if index % 19 == 0
                    else (
                        "SUSPENDED"
                        if index % 13 == 0
                        else (
                            "CLOSED"
                            if index % 29 == 0
                            else "ACTIVE"
                        )
                    )
                ),
                is_active=(index % 19 != 0 and index % 29 != 0),
                created_by=profile.employee,
            )

            surveillance.required_tests.set(
                masters["tests"][:2]
            )

            surveillance_records.append(surveillance)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(surveillance_records)} Health Surveillance records."
            )
        )

        # ============================================================
        # 8. Employee Exposure
        # ============================================================

        exposures = []

        for index in range(records):
            profile = profiles[index % len(profiles)]
            exposure = EmployeeExposure.objects.create(
                employee_health_profile=profile,
                exposure_type=masters["exposure_types"][
                    index % len(masters["exposure_types"])
                ],
                exposure_name=[
                    "Industrial Noise Exposure",
                    "Welding Fume Exposure",
                    "Chemical Handling Exposure",
                    "Dust Exposure",
                    "Heat Stress Exposure",
                ][index % 5],
                exposure_source=[
                    "Production Machinery",
                    "Welding Operations",
                    "Chemical Handling Area",
                    "Material Handling Area",
                    "Furnace Area",
                ][index % 5],
                work_area=profile.work_area,
                job_role=profile.job_role,
                exposure_start_date=self.demo_date(index),
                exposure_end_date=(
                    min(self.demo_date(index) + timedelta(days=20), self.fy_end)
                    if index % 13 == 0
                    else None
                ),
                exposure_frequency="Daily",
                exposure_duration="4-6 hours/day",
                exposure_level=[
                    "Moderate",
                    "Moderate",
                    "Low",
                    "Moderate",
                    "High",
                ][index % 5],
                control_measures=(
                    "Engineering controls, administrative controls and "
                    "appropriate PPE are implemented."
                ),
                ppe_used="Safety shoes, helmet, gloves and hearing protection",
                health_surveillance_required=True,
                health_surveillance=surveillance_records[index],
                remarks="Demo occupational exposure record.",
                status=(
                    "CLOSED"
                    if index % 13 == 0
                    else ("INACTIVE" if index % 17 == 0 else "ACTIVE")
                ),
                is_active=(index % 17 != 0),
                created_by=profile.employee,
            )

            exposures.append(exposure)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(exposures)} Employee Exposure records."
            )
        )

        # ============================================================
        # 9. Medical Follow-up
        # ============================================================

        follow_ups = []

        for index in range(records):
            profile = profiles[index % len(profiles)]
            follow_up = MedicalFollowUp.objects.create(
                employee_health_profile=profile,
                medical_examination=examinations[index],
                medical_test_result=test_results[index * 2],
                fitness_assessment=fitness_records[index],
                health_surveillance=surveillance_records[index],
                exposure=exposures[index],
                follow_up_type="EXAMINATION",
                title="Periodic Occupational Health Follow-up",
                description=(
                    "Routine follow-up for occupational health assessment."
                ),
                scheduled_date=(
                    self.fy_end - timedelta(days=5)
                    if index % 9 == 0
                    else self.fy_end + timedelta(days=5 + (index % 20))
                ),
                completed_date=(
                    self.fy_end - timedelta(days=2)
                    if index % 9 == 0
                    else None
                ),
                priority=[
                    "LOW",
                    "MEDIUM",
                    "HIGH",
                    "MEDIUM",
                ][index % 4],
                assigned_medical_professional=masters["professionals"][
                    index % len(masters["professionals"])
                ],
                medical_facility=masters["facilities"][
                    index % len(masters["facilities"])
                ],
                status=(
                    "COMPLETED"
                    if index % 9 == 0
                    else "SCHEDULED"
                ),
                outcome=(
                    "Follow-up completed and employee advised to continue routine monitoring."
                    if index % 9 == 0
                    else ""
                ),
                remarks="Demo follow-up record.",
                created_by=profile.employee,
            )

            follow_ups.append(follow_up)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(follow_ups)} Medical Follow-up records."
            )
        )

        # ============================================================
        # 10. Employee Vaccinations
        # ============================================================

        vaccinations = []

        for index in range(records):
            profile = profiles[index % len(profiles)]
            vaccination = EmployeeVaccination.objects.create(
                employee_health_profile=profile,
                vaccination=masters["vaccinations"][
                    index % len(masters["vaccinations"])
                ],
                dose_number=(
                    2 if index % 5 == 0 and masters["vaccinations"][index % len(masters["vaccinations"])].recommended_doses >= 2
                    else 1
                ),
                vaccination_date=self.demo_date(index),
                dose_status=(
                    "CANCELLED"
                    if index % 23 == 0
                    else ("MISSED" if index % 17 == 0 else "COMPLETED")
                ),
                vaccination_status=(
                    "CANCELLED"
                    if index % 23 == 0
                    else "ACTIVE"
                ),
                medical_professional=masters["professionals"][
                    index % len(masters["professionals"])
                ],
                medical_facility=masters["facilities"][
                    index % len(masters["facilities"])
                ],
                batch_number=f"DEMO-BATCH-{index + 1:03d}",
                manufacturer="Demo Healthcare Manufacturer",
                certificate_number=f"VAX-DEMO-{index + 1:05d}",
                adverse_reaction=False,
                adverse_reaction_details="",
                remarks="Demo vaccination record.",
                created_by=profile.employee,
            )

            vaccinations.append(vaccination)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(vaccinations)} Employee Vaccination records."
            )
        )

        # ============================================================
        # 11. Occupational Diseases
        # ============================================================

        diseases = []

        for index in range(records):
            profile = profiles[index % len(profiles)]
            # Create disease records for approximately half the transaction records.
            if index % 2 != 0:
                continue

            reported_date = timezone.localdate() - timedelta(
                days=60 + index
            )
            diagnosis_date = reported_date + timedelta(days=3)

            disease = EmployeeOccupationalDisease.objects.create(
                employee_health_profile=profile,
                health_condition=masters["health_conditions"][
                    index % len(masters["health_conditions"])
                ],
                reported_date=reported_date,
                diagnosis_date=diagnosis_date,
                disease_status=[
                    "SUSPECTED",
                    "UNDER_REVIEW",
                    "CONFIRMED",
                    "CLOSED",
                ][index % 4],
                severity=[
                    "MILD",
                    "MODERATE",
                    "SEVERE",
                    "MILD",
                ][index % 4],
                symptoms="Mild occupational health symptoms reported.",
                diagnosis_details=(
                    "Preliminary assessment indicates a condition "
                    "requiring routine occupational health monitoring."
                ),
                exposure_related=True,
                exposure=exposures[index],
                medical_professional=masters["professionals"][
                    index % len(masters["professionals"])
                ],
                medical_facility=masters["facilities"][
                    index % len(masters["facilities"])
                ],
                work_area=profile.work_area,
                job_role=profile.job_role,
                treatment_details="Routine medical monitoring advised.",
                work_restrictions="Avoid prolonged exposure where applicable.",
                follow_up_required=(index % 4 != 3),
                follow_up_date=(
                    min(reported_date + timedelta(days=30), self.fy_end)
                    if index % 4 != 3
                    else None
                ),
                investigation_required=(index % 3 == 0),
                investigation_findings=(
                    "Workplace exposure and medical history reviewed."
                    if index % 3 == 0
                    else ""
                ),
                corrective_actions=(
                    "Continue exposure controls and periodic medical surveillance."
                    if index % 3 == 0
                    else ""
                ),
                remarks="Demo occupational disease record.",
                status=(
                    "CLOSED"
                    if index % 4 == 3
                    else ("UNDER_INVESTIGATION" if index % 3 == 0 else "FOLLOW_UP")
                ),
                created_by=profile.employee,
            )

            diseases.append(disease)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(diseases)} Occupational Disease records."
            )
        )

        # ============================================================
        # 12. Health Incidents
        # ============================================================

        incidents = []

        for index in range(records):
            profile = profiles[index % len(profiles)]
            incident_date = self.demo_date(index)

            incident = HealthIncident.objects.create(
                employee_health_profile=profile,
                incident_date=incident_date,
                incident_time=time(10, 30),
                incident_type=[
                    "HEALTH_COMPLAINT",
                    "FIRST_AID",
                    "OCCUPATIONAL_EXPOSURE",
                    "MEDICAL_EMERGENCY",
                ][index % 4],
                severity=[
                    "MINOR",
                    "MINOR",
                    "MODERATE",
                    "SERIOUS",
                ][index % 4],
                incident_location=profile.work_area,
                work_area=profile.work_area,
                job_role=profile.job_role,
                incident_description=(
                    "Employee reported a minor health-related incident "
                    "during normal work activities."
                ),
                symptoms="Temporary discomfort reported.",
                immediate_action="Employee was moved to the occupational health facility.",
                treatment_provided="First aid and medical assessment provided.",
                medical_professional=masters["professionals"][
                    index % len(masters["professionals"])
                ],
                medical_facility=masters["facilities"][
                    index % len(masters["facilities"])
                ],
                occupational_disease=(
                    diseases[0]
                    if diseases and index == 0
                    else None
                ),
                exposure=exposures[index],
                hospitalization_required=(index % 31 == 0),
                hospitalization_details=(
                    "Employee was admitted for observation and discharged after medical clearance."
                    if index % 31 == 0
                    else ""
                ),
                work_restriction_required=(index % 11 == 0),
                work_restriction_details=(
                    "Temporary restriction from the affected work area."
                    if index % 11 == 0
                    else ""
                ),
                follow_up_required=(index % 6 != 5),
                follow_up_date=(
                    min(incident_date + timedelta(days=14), self.fy_end)
                    if index % 6 != 5
                    else None
                ),
                investigation_required=(index % 8 == 0),
                investigation_findings=(
                    "Incident reviewed by EHS and Occupational Health team."
                    if index % 8 == 0
                    else ""
                ),
                corrective_actions=(
                    "Reinforce workplace controls and employee awareness."
                    if index % 8 == 0
                    else ""
                ),
                status=[
                    "REPORTED",
                    "UNDER_REVIEW",
                    "UNDER_INVESTIGATION",
                    "TREATED",
                    "CLOSED",
                ][index % 5],
                remarks="Demo health incident record.",
                created_by=profile.employee,
            )

            incidents.append(incident)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(incidents)} Health Incident records."
            )
        )

        # ============================================================
        # 13. Return To Work
        # ============================================================

        return_to_work_records = []

        for index in range(records):
            profile = profiles[index % len(profiles)]
            if index % 2 != 0:
                continue

            absence_start = max(
                self.fy_start,
                self.demo_date(index) - timedelta(days=6)
            )
            absence_end = absence_start + timedelta(days=5)
            expected_return = min(absence_end + timedelta(days=1), self.fy_end)

            rtw = ReturnToWork.objects.create(
                employee_health_profile=profile,
                absence_start_date=absence_start,
                absence_end_date=absence_end,
                expected_return_date=expected_return,
                actual_return_date=(
                    expected_return
                    if index % 4 in [0, 1, 3]
                    else None
                ),
                return_reason="ILLNESS",
                reason_details="Medical leave due to temporary illness.",
                medical_examination=examinations[index],
                fitness_assessment=fitness_records[index],
                health_incident=incidents[index],
                occupational_disease=(
                    diseases[0]
                    if diseases and index == 0
                    else None
                ),
                medical_professional=masters["professionals"][
                    index % len(masters["professionals"])
                ],
                medical_facility=masters["facilities"][
                    index % len(masters["facilities"])
                ],
                fitness_status=fitness_records[index].fitness_status,
                restriction_details="",
                job_role=profile.job_role,
                work_area=profile.work_area,
                supervisor_comments="Employee returned after medical clearance.",
                employee_comments="Employee fit to resume assigned duties.",
                medical_recommendations="Continue routine health surveillance.",
                follow_up_required=False,
                follow_up_date=None,
                status=[
                    "COMPLETED",
                    "APPROVED",
                    "APPROVED_WITH_RESTRICTIONS",
                    "MEDICAL_ASSESSMENT",
                    "PENDING",
                ][index % 5],
                remarks="Demo return-to-work record.",
                created_by=profile.employee,
            )

            if fitness_records[index].fitness_status == "FIT_WITH_RESTRICTIONS":
                rtw.work_restrictions.add(
                    masters["restrictions"][0]
                )

            return_to_work_records.append(rtw)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(return_to_work_records)} Return To Work records."
            )
        )

        # ============================================================
        # 14. Medical Records
        # ============================================================

        medical_records = []

        for index in range(records):
            profile = profiles[index % len(profiles)]
            employee = profile.employee

            record = MedicalRecord(
                employee_health_profile=profile,
                record_title="Occupational Health Medical Examination Report",
                record_type="EXAMINATION",
                record_date=examinations[index].examination_date,
                medical_examination=examinations[index],
                medical_test_result=test_results[index * 2],
                fitness_assessment=fitness_records[index],
                medical_professional=masters["professionals"][
                    index % len(masters["professionals"])
                ],
                medical_facility=masters["facilities"][
                    index % len(masters["facilities"])
                ],
                document_number=f"OH-DEMO-{index + 1:05d}",
                description=(
                    "Demo occupational health medical examination "
                    "document generated for testing."
                ),
                confidential=True,
                record_status=[
                    "ACTIVE",
                    "ARCHIVED",
                    "ACTIVE",
                    "CANCELLED",
                ][index % 4],
                remarks="Demo medical record.",
                created_by=employee,
            )

            record.document.save(
                f"oh_demo_medical_record_{index + 1}.txt",
                ContentFile(
                    (
                        "Occupational Health Demo Medical Record\n"
                        "========================================\n"
                        f"Employee: {employee.get_full_name() or employee.username}\n"
                        f"Employee ID: {employee.employee_id or 'N/A'}\n"
                        f"Document Number: OH-DEMO-{index + 1:05d}\n"
                        "This document is generated only for demo/testing purposes.\n"
                    ).encode("utf-8")
                ),
                save=False,
            )

            record.save()
            medical_records.append(record)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(medical_records)} Medical Records."
            )
        )

        # ============================================================
        # 15. Health Camps
        # ============================================================

        health_camps = []

        plants = list(
            {
                user.plant_id: user.plant
                for user in selected_users
                if user.plant_id and user.plant
            }.values()
        )

        if plants:
            camp_count = min(2, len(plants))

            for index in range(camp_count):
                plant = plants[index]

                camp = HealthCamp.objects.create(
                    camp_name=(
                        "Annual Occupational Health Screening Camp "
                        f"- {plant.name}"
                    ),
                    camp_type=[
                        "GENERAL_HEALTH",
                        "EYE_CHECKUP",
                    ][index % 2],
                    camp_mode="ON_SITE",
                    plant=plant,
                    location=plant.name,
                    camp_date=(self.demo_date(0) if index == 0 else self.fy_end),
                    start_time=time(9, 30),
                    end_time=time(16, 30),
                    organizer="EHS Department",
                    medical_facility=masters["facilities"][
                        index % len(masters["facilities"])
                    ],
                    lead_medical_professional=masters["professionals"][
                        index % len(masters["professionals"])
                    ],
                    objectives=(
                        "Conduct preventive occupational health screening "
                        "for employees."
                    ),
                    services_provided=(
                        "General health screening, vital signs and "
                        "occupational health consultation."
                    ),
                    target_employee_count=len(selected_users),
                    registered_employee_count=0,
                    attended_employee_count=0,
                    findings_count=0,
                    referral_count=0,
                    follow_up_required_count=0,
                    status=(
                        "COMPLETED"
                        if index % 3 == 0
                        else ("IN_PROGRESS" if index % 3 == 1 else "SCHEDULED")
                    ),
                    remarks="Demo health camp.",
                    created_by=selected_users[0],
                )

                health_camps.append(camp)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(health_camps)} Health Camps."
            )
        )

        # ============================================================
        # 16. Health Camp Participation
        # ============================================================

        participation_count = 0

        for camp in health_camps:
            camp_users = [
                user
                for user in selected_users
                if user.plant_id == camp.plant_id
            ]

            for index, user in enumerate(camp_users):
                profile = profiles[
                    selected_users.index(user)
                ]

                participation = HealthCampParticipation.objects.create(
                    health_camp=camp,
                    employee_health_profile=profile,
                    registration_date=camp.camp_date,
                    attendance_status=(
                        "ATTENDED"
                        if camp.status in ["COMPLETED", "IN_PROGRESS"]
                        else "REGISTERED"
                    ),
                    attendance_time=(
                        time(10, 15)
                        if camp.status in ["COMPLETED", "IN_PROGRESS"]
                        else None
                    ),
                    screening_status=(
                        "ABNORMAL"
                        if camp.status in ["COMPLETED", "IN_PROGRESS"] and index % 5 == 0
                        else (
                            "NORMAL"
                            if camp.status in ["COMPLETED", "IN_PROGRESS"]
                            else "NOT_SCREENED"
                        )
                    ),
                    screening_findings=(
                        "Routine health screening completed."
                    ),
                    abnormal_findings=(
                        "Mild elevated blood pressure noted."
                        if index % 5 == 0
                        else ""
                    ),
                    services_received=(
                        "General health screening and medical consultation."
                    ),
                    medical_advice=(
                        "Continue routine health monitoring."
                    ),
                    referral_required=False,
                    referral_details="",
                    follow_up_required=(
                        camp.status in ["COMPLETED", "IN_PROGRESS"] and index % 5 == 0
                    ),
                    follow_up_date=(
                        min(camp.camp_date + timedelta(days=30), self.fy_end)
                        if camp.status in ["COMPLETED", "IN_PROGRESS"] and index % 5 == 0
                        else None
                    ),
                    follow_up_notes=(
                        "Repeat health assessment after 30 days."
                        if index % 5 == 0
                        else ""
                    ),
                    medical_professional=masters["professionals"][
                        index % len(masters["professionals"])
                    ],
                    remarks="Demo health camp participation.",
                    created_by=user,
                )

                participation_count += 1

            # Update camp statistics after participation creation.
            camp.registered_employee_count = camp.participations.count()
            camp.attended_employee_count = camp.participations.filter(
                attendance_status="ATTENDED"
            ).count()
            camp.findings_count = camp.participations.exclude(
                screening_status="NORMAL"
            ).count()
            camp.referral_count = camp.participations.filter(
                referral_required=True
            ).count()
            camp.follow_up_required_count = camp.participations.filter(
                follow_up_required=True
            ).count()

            camp.save(
                update_fields=[
                    "registered_employee_count",
                    "attended_employee_count",
                    "findings_count",
                    "referral_count",
                    "follow_up_required_count",
                    "updated_at",
                ]
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {participation_count} Health Camp Participation records."
            )
        )

        # ============================================================
        # FY-wise Summary
        # ============================================================

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"FY-wise Demo Data: FY {self.fy_start.year}-{str(self.fy_end.year)[-2:]}"
            )
        )
        self.stdout.write(
            f"  Date Range: {self.fy_start.strftime('%d %b %Y')} to "
            f"{self.fy_end.strftime('%d %b %Y')}"
        )
        self.stdout.write(f"  Medical Examinations: {len(examinations)}")
        self.stdout.write(f"  Medical Test Results: {len(test_results)}")
        self.stdout.write(f"  Fitness To Work: {len(fitness_records)}")
        self.stdout.write(f"  Health Surveillance: {len(surveillance_records)}")
        self.stdout.write(f"  Employee Exposure: {len(exposures)}")
        self.stdout.write(f"  Medical Follow-up: {len(follow_ups)}")
        self.stdout.write(f"  Employee Vaccinations: {len(vaccinations)}")
        self.stdout.write(f"  Occupational Diseases: {len(diseases)}")
        self.stdout.write(f"  Health Incidents: {len(incidents)}")
        self.stdout.write(f"  Return To Work: {len(return_to_work_records)}")
        self.stdout.write(f"  Medical Records: {len(medical_records)}")
        self.stdout.write(f"  Health Camps: {len(health_camps)}")
        self.stdout.write(f"  Health Camp Participation: {participation_count}")

        # ============================================================
        # Final Summary
        # ============================================================

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "============================================================"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Occupational Health demo data created successfully."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Employees used: {len(selected_users)}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Requested transaction records: {records}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Financial Year: FY {self.fy_start.year}-{str(self.fy_end.year)[-2:]} "
                f"({self.fy_start.strftime('%d %b %Y')} to {self.fy_end.strftime('%d %b %Y')})"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Existing organization records were reused."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "No Users, Departments, Plants, Zones, Locations or "
                "SubLocations were created."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "============================================================"
            )
        )
        self.stdout.write("")


    # ============================================================
    # Demo Date Helper
    # Generates dates only inside the current financial year.
    # ============================================================

    def demo_date(self, index, offset_days=0):
        total_days = (self.fy_end - self.fy_start).days
        if total_days <= 0:
            return self.fy_start

        if self.demo_records <= 1:
            base_date = self.fy_start
        else:
            base_date = self.fy_start + timedelta(
                days=(index * total_days) // (self.demo_records - 1)
            )

        return min(base_date + timedelta(days=offset_days), self.fy_end)

    # ============================================================
    # Reusable Master Data Helper
    # Reuses existing master records instead of creating duplicates.
    # ============================================================

    def get_or_create_master(self, model, name, code, defaults):
        # First try to find an existing record by its unique name.
        obj = model.objects.filter(name=name).first()

        if obj:
            return obj

        # If name is not found, check whether the code already exists.
        obj = model.objects.filter(code=code).first()

        if obj:
            return obj

        # Create a new master only when neither name nor code exists.
        create_data = {
            "name": name,
            "code": code,
            **defaults,
        }

        return model.objects.create(**create_data)

    # ============================================================
    # Master Data Creation
    # ============================================================

    def create_master_data(self, created_by):
        examination_types_data = [
            (
                "Periodic Medical Examination",
                "PERIODIC",
                "Routine periodic occupational health examination.",
            ),
            (
                "Annual Health Examination",
                "ANNUAL",
                "Annual employee health assessment.",
            ),
            (
                "Pre-Employment Medical Examination",
                "PRE_EMP",
                "Medical examination before employment.",
            ),
        ]

        examination_types = []

        for name, code, description in examination_types_data:
            obj = self.get_or_create_master(
                ExaminationType,
                name=name,
                code=code,
                defaults={
                    "description": description,
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            examination_types.append(obj)

        # ------------------------------------------------------------
        # Medical Tests
        # ------------------------------------------------------------

        tests_data = [
            (
                "Blood Pressure",
                "BP",
                "PHYSICAL",
                "mmHg",
                "100-140 mmHg",
            ),
            (
                "Oxygen Saturation",
                "SPO2",
                "PHYSICAL",
                "%",
                "95-100%",
            ),
            (
                "Complete Blood Count",
                "CBC",
                "LABORATORY",
                "Various",
                "Laboratory reference range",
            ),
            (
                "Audiometry",
                "AUD",
                "DIAGNOSTIC",
                "dB",
                "Occupational reference range",
            ),
            (
                "Vision Screening",
                "VISION",
                "PHYSICAL",
                "Decimal",
                "6/6 normal",
            ),
        ]

        tests = []

        for name, code, test_type, unit, normal_range in tests_data:
            obj = self.get_or_create_master(
                MedicalTest,
                name=name,
                code=code,
                defaults={
                    "test_type": test_type,
                    "description": f"Occupational health test for {name}.",
                    "unit": unit,
                    "normal_range": normal_range,
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            tests.append(obj)

        # ------------------------------------------------------------
        # Exposure Types
        # ------------------------------------------------------------

        exposure_data = [
            (
                "Noise",
                "NOISE",
                "Occupational exposure to elevated workplace noise.",
            ),
            (
                "Welding Fumes",
                "WELD_FUME",
                "Exposure to welding fumes and metal particulates.",
            ),
            (
                "Chemical",
                "CHEMICAL",
                "Exposure to workplace chemicals.",
            ),
            (
                "Dust",
                "DUST",
                "Exposure to airborne dust and particulates.",
            ),
            (
                "Heat",
                "HEAT",
                "Exposure to elevated workplace temperatures.",
            ),
        ]

        exposure_types = []

        for name, code, description in exposure_data:
            obj = self.get_or_create_master(
                ExposureType,
                name=name,
                code=code,
                defaults={
                    "description": description,
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            exposure_types.append(obj)

        # ------------------------------------------------------------
        # Health Conditions
        # ------------------------------------------------------------

        condition_data = [
            (
                "Occupational Hearing Loss",
                "OHL",
                "HEARING",
                True,
            ),
            (
                "Occupational Dermatitis",
                "ODERM",
                "DERMATOLOGICAL",
                True,
            ),
            (
                "Low Back Pain",
                "LBP",
                "MUSCULOSKELETAL",
                True,
            ),
            (
                "Respiratory Irritation",
                "RESP",
                "RESPIRATORY",
                True,
            ),
            (
                "Hypertension",
                "HTN",
                "CARDIOVASCULAR",
                False,
            ),
        ]

        health_conditions = []

        for name, code, category, occupational in condition_data:
            obj = self.get_or_create_master(
                HealthCondition,
                name=name,
                code=code,
                defaults={
                    "category": category,
                    "description": f"Demo health condition: {name}.",
                    "is_occupational": occupational,
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            health_conditions.append(obj)

        # ------------------------------------------------------------
        # Fitness Status Masters
        # ------------------------------------------------------------

        fitness_status_data = [
            ("Fit", "FIT", "Employee fit for assigned work."),
            (
                "Fit With Restrictions",
                "FIT_RESTRICTED",
                "Employee fit with defined work restrictions.",
            ),
            (
                "Temporarily Unfit",
                "TEMP_UNFIT",
                "Employee temporarily unfit for work.",
            ),
            (
                "Unfit",
                "UNFIT",
                "Employee unfit for assigned work.",
            ),
        ]

        fitness_statuses = []

        for name, code, description in fitness_status_data:
            obj = self.get_or_create_master(
                FitnessStatus,
                name=name,
                code=code,
                defaults={
                    "description": description,
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            fitness_statuses.append(obj)

        # ------------------------------------------------------------
        # Restrictions
        # ------------------------------------------------------------

        restriction_data = [
            (
                "No Heavy Lifting",
                "NO_HEAVY_LIFT",
                "Avoid heavy manual lifting activities.",
            ),
            (
                "Noise Exposure Restriction",
                "NOISE_RESTRICT",
                "Avoid prolonged exposure to high noise.",
            ),
            (
                "Chemical Exposure Restriction",
                "CHEM_RESTRICT",
                "Avoid specified chemical exposure.",
            ),
            (
                "Night Shift Restriction",
                "NO_NIGHT_SHIFT",
                "Employee should not be assigned night shifts.",
            ),
        ]

        restrictions = []

        for name, code, description in restriction_data:
            obj = self.get_or_create_master(
                Restriction,
                name=name,
                code=code,
                defaults={
                    "description": description,
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            restrictions.append(obj)

        # ------------------------------------------------------------
        # Vaccinations
        # ------------------------------------------------------------

        vaccination_data = [
            (
                "Tetanus",
                "TETANUS",
                "Tetanus vaccination for occupational risk.",
                2,
                60,
            ),
            (
                "Hepatitis B",
                "HEPB",
                "Hepatitis B vaccination for occupational exposure risk.",
                3,
                60,
            ),
            (
                "Influenza",
                "FLU",
                "Seasonal influenza vaccination.",
                1,
                12,
            ),
        ]

        vaccinations = []

        for name, code, description, doses, validity in vaccination_data:
            obj = self.get_or_create_master(
                Vaccination,
                name=name,
                code=code,
                defaults={
                    "description": description,
                    "recommended_doses": doses,
                    "validity_months": validity,
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            vaccinations.append(obj)

        # ------------------------------------------------------------
        # Medical Professionals
        # ------------------------------------------------------------

        professionals_data = [
            (
                "Dr. Amit Sharma",
                "MP001",
                "OCCUPATIONAL_PHYSICIAN",
                "MBBS, AFIH",
                "Occupational Medicine",
            ),
            (
                "Dr. Neha Patil",
                "MP002",
                "GENERAL_PHYSICIAN",
                "MBBS, MD",
                "General Medicine",
            ),
            (
                "Dr. Rahul Joshi",
                "MP003",
                "MEDICAL_OFFICER",
                "MBBS",
                "Occupational Health",
            ),
        ]

        professionals = []

        for name, code, professional_type, qualification, specialization in professionals_data:
            obj = self.get_or_create_master(
                MedicalProfessional,
                name=name,
                code=code,
                defaults={
                    "professional_type": professional_type,
                    "qualification": qualification,
                    "specialization": specialization,
                    "registration_number": f"REG-{code}",
                    "contact_number": "9876543210",
                    "email": f"{code.lower()}@demohealth.com",
                    "description": "Demo medical professional.",
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            professionals.append(obj)

        # ------------------------------------------------------------
        # Medical Facilities
        # ------------------------------------------------------------

        facilities_data = [
            (
                "EHS Occupational Health Centre",
                "OHFC001",
                "OCCUPATIONAL_HEALTH_CENTER",
            ),
            (
                "City Diagnostic Centre",
                "DIAG001",
                "DIAGNOSTIC_CENTER",
            ),
            (
                "Industrial Medical Clinic",
                "CLINIC001",
                "CLINIC",
            ),
        ]

        facilities = []

        for name, code, facility_type in facilities_data:
            obj = self.get_or_create_master(
                MedicalFacility,
                name=name,
                code=code,
                defaults={
                    "facility_type": facility_type,
                    "address": "Industrial Area, Maharashtra",
                    "contact_person": "Occupational Health Desk",
                    "contact_number": "9876500000",
                    "email": f"{code.lower()}@demohealth.com",
                    "registration_number": f"FAC-{code}",
                    "description": "Demo medical facility.",
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            facilities.append(obj)

        return {
            "examination_types": examination_types,
            "tests": tests,
            "exposure_types": exposure_types,
            "health_conditions": health_conditions,
            "fitness_statuses": fitness_statuses,
            "restrictions": restrictions,
            "vaccinations": vaccinations,
            "professionals": professionals,
            "facilities": facilities,
        }