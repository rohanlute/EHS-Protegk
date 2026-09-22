from datetime import date, timedelta
from random import choice, randint, sample

from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

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


# =============================================
# Occupational Health Demo Data Seeder
# Creates realistic Occupational Health data using existing users and organization assignments
# =============================================
class Command(BaseCommand):
    help = "Seed Occupational Health demo data using existing users and organization structure."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=10,
            help="Number of existing users to use for demo data. Example: --count 20",
        )

        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete previously generated Occupational Health demo records before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):

        count = options["count"]
        clear = options["clear"]

        if count not in [5, 10, 15, 20]:
            self.stdout.write(
                self.style.ERROR(
                    "Count must be one of: 5, 10, 15 or 20."
                )
            )
            return

        User = get_user_model()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "=================================================="
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Occupational Health Demo Data Seeder"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "=================================================="
            )
        )

        # =============================================
        # Clear previously generated demo data
        # =============================================
        if clear:
            self.clear_demo_data()

        # =============================================
        # Get existing active users
        # Users are NOT created by this command
        # =============================================
        users = list(
            User.objects.filter(
                is_active=True,
                is_active_employee=True
            )
            .exclude(is_superuser=True)
            .order_by("id")
        )

        if len(users) < count:
            self.stdout.write(
                self.style.ERROR(
                    f"Only {len(users)} active employees are available."
                )
            )
            self.stdout.write(
                self.style.ERROR(
                    f"At least {count} existing employees are required."
                )
            )
            return

        selected_users = users[:count]

        self.stdout.write(
            f"Existing users available : {len(users)}"
        )
        self.stdout.write(
            f"Users selected            : {len(selected_users)}"
        )

        # =============================================
        # Create Occupational Health master data
        # =============================================
        examination_types = self.seed_examination_types()
        medical_tests = self.seed_medical_tests()
        exposure_types = self.seed_exposure_types()
        health_conditions = self.seed_health_conditions()
        fitness_statuses = self.seed_fitness_statuses()
        restrictions = self.seed_restrictions()
        vaccinations = self.seed_vaccinations()
        professionals = self.seed_medical_professionals()
        facilities = self.seed_medical_facilities()

        # =============================================
        # Create Employee Health Profiles
        # Existing users are reused
        # =============================================
        profiles = []

        for index, user in enumerate(selected_users, start=1):

            profile, created = EmployeeHealthProfile.objects.get_or_create(
                employee=user,
                defaults={
                    "date_of_birth": user.date_of_birth or date(
                        1990 + (index % 8),
                        (index % 12) + 1,
                        (index % 25) + 1,
                    ),
                    "gender": user.gender or choice(
                        ["MALE", "FEMALE"]
                    ),
                    "blood_group": choice([
                        "A_POSITIVE",
                        "B_POSITIVE",
                        "O_POSITIVE",
                        "AB_POSITIVE",
                        "A_NEGATIVE",
                    ]),
                    "emergency_contact_name": f"Emergency Contact {index}",
                    "emergency_contact_number": f"90000000{index:02d}",
                    "date_of_joining": user.date_joined_company or date(
                        2020 + (index % 5),
                        (index % 12) + 1,
                        (index % 25) + 1,
                    ),
                    "work_shift": choice([
                        "General Shift",
                        "Shift A",
                        "Shift B",
                        "Shift C",
                    ]),
                    "employment_type": (
                        "CONTRACT"
                        if user.employment_type == "CONTRACT"
                        else "PERMANENT"
                    ),
                    "job_role": user.job_title or choice([
                        "Production Engineer",
                        "Maintenance Engineer",
                        "Quality Engineer",
                        "Safety Officer",
                        "Machine Operator",
                        "Technician",
                        "Supervisor",
                    ]),
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
                f"  {'Created' if created else 'Existing'} profile: "
                f"{user.get_full_name() or user.username}"
            )

        # =============================================
        # Create Medical Examinations
        # =============================================
        examinations = []

        for index, profile in enumerate(profiles):

            user = profile.employee

            examination = MedicalExamination.objects.create(
                employee_health_profile=profile,
                examination_type=choice(examination_types),
                examination_date=date.today() - timedelta(days=index * 7),
                purpose=choice([
                    "PERIODIC",
                    "ANNUAL",
                    "PRE_EMPLOYMENT",
                    "SPECIAL",
                ]),
                medical_professional=choice(professionals),
                medical_facility=choice(facilities),
                job_role=profile.job_role,
                work_area=profile.work_area,
                general_findings=choice([
                    "General health condition satisfactory.",
                    "Employee found in stable health condition.",
                    "Routine examination completed.",
                    "No major abnormality observed.",
                ]),
                abnormal_findings=choice([
                    "",
                    "",
                    "Minor abnormality observed and advised for follow-up.",
                ]),
                recommendations=choice([
                    "Continue routine health monitoring.",
                    "Maintain healthy lifestyle and hydration.",
                    "Periodic medical examination recommended.",
                    "Follow prescribed medical advice.",
                ]),
                follow_up_required=(index % 4 == 0),
                follow_up_date=(
                    date.today() + timedelta(days=30)
                    if index % 4 == 0
                    else None
                ),
                status="COMPLETED",
                created_by=user,
            )

            examinations.append(examination)

        # =============================================
        # Create Medical Test Results
        # =============================================
        test_results = []

        for index, examination in enumerate(examinations):

            selected_tests = sample(
                medical_tests,
                min(2, len(medical_tests))
            )

            for test_index, medical_test in enumerate(selected_tests):

                result_status = choice([
                    "NORMAL",
                    "NORMAL",
                    "NORMAL",
                    "BORDERLINE",
                    "ABNORMAL",
                ])

                result = MedicalTestResult.objects.create(
                    medical_examination=examination,
                    medical_test=medical_test,
                    test_date=examination.examination_date,
                    result_value=choice([
                        "Normal",
                        "Within acceptable range",
                        "12.5",
                        "98",
                        "5.6",
                    ]),
                    unit=medical_test.unit,
                    reference_range=medical_test.normal_range,
                    result_status=result_status,
                    findings=(
                        "No significant abnormality detected."
                        if result_status == "NORMAL"
                        else "Follow-up observation recommended."
                    ),
                    recommendations=(
                        "Continue routine monitoring."
                        if result_status == "NORMAL"
                        else "Medical review recommended."
                    ),
                    doctor_comments="Reviewed by medical professional.",
                    follow_up_required=(result_status == "ABNORMAL"),
                    follow_up_date=(
                        date.today() + timedelta(days=30)
                        if result_status == "ABNORMAL"
                        else None
                    ),
                    created_by=examination.created_by,
                )

                test_results.append(result)

        # =============================================
        # Create Fitness To Work
        # =============================================
        fitness_records = []

        for index, profile in enumerate(profiles):

            examination = examinations[index]

            fitness_status = choice([
                "FIT",
                "FIT",
                "FIT",
                "FIT_WITH_RESTRICTIONS",
            ])

            fitness = FitnessToWork.objects.create(
                medical_examination=examination,
                employee_health_profile=profile,
                assessment_date=examination.examination_date,
                assessment_type=choice([
                    "PERIODIC",
                    "ANNUAL",
                    "SPECIAL",
                ]),
                fitness_status=fitness_status,
                valid_from=examination.examination_date,
                valid_until=(
                    examination.examination_date + timedelta(days=365)
                ),
                medical_findings=(
                    "Employee medically fit for assigned duties."
                ),
                work_recommendations=(
                    "Continue routine occupational health monitoring."
                ),
                doctor_comments="Fitness assessment completed.",
                follow_up_required=False,
                status=True,
                created_by=profile.employee,
            )

            if fitness_status == "FIT_WITH_RESTRICTIONS":
                fitness.restrictions.add(
                    choice(restrictions)
                )

            fitness_records.append(fitness)

        # =============================================
        # Create Health Surveillance
        # =============================================
        surveillance_records = []

        for index, profile in enumerate(profiles):

            surveillance = HealthSurveillance.objects.create(
                employee_health_profile=profile,
                exposure_type=choice(exposure_types),
                surveillance_name=choice([
                    "Annual Occupational Health Surveillance",
                    "Respiratory Health Surveillance",
                    "Hearing Conservation Surveillance",
                    "Chemical Exposure Surveillance",
                    "Ergonomic Health Surveillance",
                ]),
                surveillance_frequency=choice([
                    "MONTHLY",
                    "QUARTERLY",
                    "HALF_YEARLY",
                    "YEARLY",
                ]),
                start_date=date.today() - timedelta(days=180),
                next_due_date=date.today() + timedelta(days=30 + index),
                responsible_medical_professional=choice(professionals),
                medical_facility=choice(facilities),
                health_objectives=(
                    "Monitor employee health based on workplace exposure."
                ),
                remarks="Routine occupational health surveillance.",
                status="ACTIVE",
                is_active=True,
                created_by=profile.employee,
            )

            surveillance.required_tests.add(
                choice(medical_tests)
            )

            surveillance_records.append(surveillance)

        # =============================================
        # Create Employee Exposure
        # =============================================
        exposure_records = []

        exposure_names = [
            "Noise Exposure",
            "Dust Exposure",
            "Chemical Exposure",
            "Heat Exposure",
            "Vibration Exposure",
            "Ergonomic Exposure",
        ]

        for index, profile in enumerate(profiles):

            exposure = EmployeeExposure.objects.create(
                employee_health_profile=profile,
                exposure_type=surveillance_records[index].exposure_type,
                exposure_name=choice(exposure_names),
                exposure_source=choice([
                    "Production machinery",
                    "Chemical handling area",
                    "Material handling area",
                    "Process equipment",
                    "Production line",
                ]),
                work_area=profile.work_area,
                job_role=profile.job_role,
                exposure_start_date=date.today() - timedelta(days=365),
                exposure_frequency=choice([
                    "Daily",
                    "Weekly",
                    "Every Shift",
                ]),
                exposure_duration=choice([
                    "2 hours/day",
                    "4 hours/day",
                    "6 hours/day",
                    "8 hours/day",
                ]),
                exposure_level=choice([
                    "Low",
                    "Moderate",
                    "High",
                ]),
                control_measures=(
                    "Engineering controls, administrative controls "
                    "and PPE implemented."
                ),
                ppe_used=choice([
                    "Safety shoes and gloves",
                    "Ear plugs and safety shoes",
                    "Respirator and gloves",
                    "Safety goggles and gloves",
                ]),
                health_surveillance_required=True,
                health_surveillance=surveillance_records[index],
                remarks="Exposure recorded for occupational health monitoring.",
                status="ACTIVE",
                is_active=True,
                created_by=profile.employee,
            )

            exposure_records.append(exposure)

        # =============================================
        # Create Medical Follow-ups
        # =============================================
        follow_ups = []

        for index, profile in enumerate(profiles):

            follow_up = MedicalFollowUp.objects.create(
                employee_health_profile=profile,
                medical_examination=examinations[index],
                follow_up_type="EXAMINATION",
                title="Periodic Medical Examination Follow-up",
                description=(
                    "Follow-up generated from periodic medical examination."
                ),
                scheduled_date=date.today() + timedelta(days=15 + index),
                priority=choice([
                    "LOW",
                    "MEDIUM",
                    "MEDIUM",
                    "HIGH",
                ]),
                assigned_medical_professional=choice(professionals),
                medical_facility=choice(facilities),
                recommendations="Review medical findings and continue monitoring.",
                remarks="Demo follow-up record.",
                status="PENDING",
                is_active=True,
                created_by=profile.employee,
            )

            follow_ups.append(follow_up)

        # =============================================
        # Create Employee Vaccinations
        # =============================================
        vaccination_records = []

        for index, profile in enumerate(profiles):

            vaccination = choice(vaccinations)

            employee_vaccination = EmployeeVaccination.objects.create(
                employee_health_profile=profile,
                vaccination=vaccination,
                dose_number=1,
                vaccination_date=date.today() - timedelta(days=90),
                dose_status="COMPLETED",
                vaccination_status="ACTIVE",
                medical_professional=choice(professionals),
                medical_facility=choice(facilities),
                batch_number=f"BATCH-{2026}{index + 1:03d}",
                manufacturer=choice([
                    "Serum Institute",
                    "Bharat Biotech",
                    "Pfizer",
                    "GSK",
                ]),
                certificate_number=f"VACC-{index + 1:05d}",
                adverse_reaction=False,
                remarks="Vaccination completed successfully.",
                created_by=profile.employee,
            )

            vaccination_records.append(employee_vaccination)

        # =============================================
        # Create Occupational Diseases
        # Created for approximately half of employees
        # =============================================
        disease_records = []

        for index, profile in enumerate(profiles):

            if index % 2 != 0:
                continue

            disease = EmployeeOccupationalDisease.objects.create(
                employee_health_profile=profile,
                health_condition=choice(health_conditions),
                reported_date=date.today() - timedelta(days=60 + index),
                diagnosis_date=date.today() - timedelta(days=45 + index),
                disease_status=choice([
                    "SUSPECTED",
                    "CONFIRMED",
                    "UNDER_REVIEW",
                ]),
                severity=choice([
                    "MILD",
                    "MODERATE",
                ]),
                symptoms=choice([
                    "Mild respiratory discomfort.",
                    "Occasional hearing discomfort.",
                    "Musculoskeletal discomfort.",
                    "Skin irritation.",
                ]),
                diagnosis_details="Initial occupational health assessment completed.",
                exposure_related=True,
                exposure=exposure_records[index],
                medical_professional=choice(professionals),
                medical_facility=choice(facilities),
                work_area=profile.work_area,
                job_role=profile.job_role,
                treatment_details="Routine medical treatment advised.",
                work_restrictions="Avoid prolonged exposure where applicable.",
                follow_up_required=True,
                follow_up_date=date.today() + timedelta(days=30),
                investigation_required=False,
                remarks="Demo occupational disease record.",
                status="FOLLOW_UP",
                created_by=profile.employee,
            )

            disease_records.append(disease)

        # =============================================
        # Create Health Incidents
        # =============================================
        incident_records = []

        for index, profile in enumerate(profiles):

            incident = HealthIncident.objects.create(
                employee_health_profile=profile,
                incident_date=date.today() - timedelta(days=20 + index),
                incident_time=None,
                incident_type=choice([
                    "HEALTH_COMPLAINT",
                    "FIRST_AID",
                    "MEDICAL_EMERGENCY",
                    "OCCUPATIONAL_EXPOSURE",
                ]),
                severity=choice([
                    "MINOR",
                    "MINOR",
                    "MODERATE",
                ]),
                incident_location=(
                    profile.work_area or "Production Area"
                ),
                work_area=profile.work_area,
                job_role=profile.job_role,
                incident_description=choice([
                    "Employee reported minor health discomfort during shift.",
                    "Employee required first aid treatment.",
                    "Employee reported temporary occupational health complaint.",
                    "Employee experienced minor exposure-related symptoms.",
                ]),
                symptoms=choice([
                    "Mild headache.",
                    "Minor dizziness.",
                    "Musculoskeletal discomfort.",
                    "Minor respiratory discomfort.",
                ]),
                immediate_action="First aid provided and employee evaluated.",
                treatment_provided="Basic medical treatment provided.",
                medical_professional=choice(professionals),
                medical_facility=choice(facilities),
                exposure=exposure_records[index],
                hospitalization_required=False,
                work_restriction_required=False,
                follow_up_required=True,
                follow_up_date=date.today() + timedelta(days=15),
                investigation_required=False,
                status=choice([
                    "REPORTED",
                    "UNDER_REVIEW",
                    "TREATED",
                ]),
                remarks="Demo health incident.",
                created_by=profile.employee,
            )

            incident_records.append(incident)

        # =============================================
        # Create Return To Work records
        # =============================================
        return_to_work_records = []

        for index, profile in enumerate(profiles):

            if index % 2 != 0:
                continue

            medical_examination = examinations[index]
            fitness = fitness_records[index]

            rtw = ReturnToWork.objects.create(
                employee_health_profile=profile,
                absence_start_date=date.today() - timedelta(days=20),
                absence_end_date=date.today() - timedelta(days=5),
                expected_return_date=date.today(),
                actual_return_date=date.today(),
                return_reason=choice([
                    "ILLNESS",
                    "MEDICAL_LEAVE",
                    "WORK_RESTRICTION",
                ]),
                reason_details="Employee returned after medical evaluation.",
                medical_examination=medical_examination,
                fitness_assessment=fitness,
                health_incident=incident_records[index],
                medical_professional=choice(professionals),
                medical_facility=choice(facilities),
                fitness_status=fitness.fitness_status,
                job_role=profile.job_role,
                work_area=profile.work_area,
                medical_recommendations="Resume work with routine monitoring.",
                follow_up_required=False,
                status="COMPLETED",
                remarks="Return to work completed.",
                created_by=profile.employee,
            )

            if fitness.fitness_status == "FIT_WITH_RESTRICTIONS":
                rtw.work_restrictions.add(
                    choice(restrictions)
                )

            return_to_work_records.append(rtw)

        # =============================================
        # Create Medical Records
        # =============================================
        medical_records = []

        for index, profile in enumerate(profiles):

            # Create a small text file so the required FileField
            # contains an actual demo document.
            document_content = (
                f"Occupational Health Demo Medical Record\n"
                f"Employee: {profile.employee.get_full_name()}\n"
                f"Generated by EHS-360 demo data seeder.\n"
            )

            medical_record = MedicalRecord(
                employee_health_profile=profile,
                record_title="Periodic Medical Examination Record",
                record_type="MEDICAL_EXAMINATION",
                record_date=examinations[index].examination_date,
                medical_examination=examinations[index],
                medical_test_result=test_results[index * 2]
                if index * 2 < len(test_results)
                else None,
                fitness_assessment=fitness_records[index],
                medical_professional=choice(professionals),
                medical_facility=choice(facilities),
                document_number=f"MED-{date.today().year}-{index + 1:04d}",
                description="Demo occupational health medical record.",
                confidential=True,
                record_status="ACTIVE",
                remarks="Generated for testing/demo purposes.",
                created_by=profile.employee,
            )

            medical_record.document.save(
                f"demo_medical_record_{index + 1}.txt",
                ContentFile(document_content.encode("utf-8")),
                save=False,
            )

            medical_record.save()
            medical_records.append(medical_record)

        # =============================================
        # Create Health Camps
        # =============================================
        camps = []

        # Use existing plants from selected employees.
        plants = []

        for user in selected_users:
            if user.plant and user.plant not in plants:
                plants.append(user.plant)

        for index, plant in enumerate(plants[:5]):

            camp = HealthCamp.objects.create(
                camp_name=choice([
                    "Annual General Health Camp",
                    "Employee Eye Check-up Camp",
                    "Occupational Health Screening Camp",
                    "Preventive Health Camp",
                    "Employee Wellness Camp",
                ]),
                camp_type=choice([
                    "GENERAL_HEALTH",
                    "EYE_CHECKUP",
                    "OCCUPATIONAL_HEALTH",
                    "SPECIALIZED",
                ]),
                camp_mode="ON_SITE",
                plant=plant,
                location=(
                    plant.name
                    if plant
                    else "Main Health Center"
                ),
                camp_date=date.today() + timedelta(days=15 + index),
                organizer="EHS Department",
                medical_facility=choice(facilities),
                lead_medical_professional=choice(professionals),
                objectives=(
                    "Conduct preventive health screening "
                    "and identify employee health concerns."
                ),
                services_provided=(
                    "General examination, basic screening, "
                    "health counselling and referral."
                ),
                target_employee_count=count,
                registered_employee_count=0,
                attended_employee_count=0,
                findings_count=0,
                referral_count=0,
                follow_up_required_count=0,
                status="SCHEDULED",
                is_active=True,
                created_by=selected_users[0],
            )

            camps.append(camp)

        # =============================================
        # Create Health Camp Participations
        # =============================================
        participation_count = 0

        for index, camp in enumerate(camps):

            camp_users = selected_users[:min(5, len(selected_users))]

            for user in camp_users:

                profile = EmployeeHealthProfile.objects.filter(
                    employee=user
                ).first()

                if not profile:
                    continue

                participation, created = (
                    HealthCampParticipation.objects.get_or_create(
                        health_camp=camp,
                        employee_health_profile=profile,
                        defaults={
                            "registration_date": date.today(),
                            "attendance_status": "REGISTERED",
                            "screening_status": "NOT_SCREENED",
                            "referral_required": False,
                            "follow_up_required": False,
                            "medical_professional": camp.lead_medical_professional,
                            "remarks": "Demo health camp participation.",
                            "created_by": user,
                        },
                    )
                )

                if created:
                    participation_count += 1

            # Update camp counts from actual participation records.
            camp.registered_employee_count = camp.participations.count()
            camp.save(
                update_fields=[
                    "registered_employee_count",
                    "updated_at",
                ]
            )

        # =============================================
        # Final Summary
        # =============================================
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "=================================================="
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "OCCUPATIONAL HEALTH SEEDING COMPLETED"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "=================================================="
            )
        )

        self.stdout.write(
            f"Existing Users Used          : {len(selected_users)}"
        )
        self.stdout.write(
            f"Employee Health Profiles     : {len(profiles)}"
        )
        self.stdout.write(
            f"Medical Examinations         : {len(examinations)}"
        )
        self.stdout.write(
            f"Medical Test Results         : {len(test_results)}"
        )
        self.stdout.write(
            f"Fitness Assessments          : {len(fitness_records)}"
        )
        self.stdout.write(
            f"Health Surveillance          : {len(surveillance_records)}"
        )
        self.stdout.write(
            f"Employee Exposures           : {len(exposure_records)}"
        )
        self.stdout.write(
            f"Medical Follow-ups           : {len(follow_ups)}"
        )
        self.stdout.write(
            f"Employee Vaccinations        : {len(vaccination_records)}"
        )
        self.stdout.write(
            f"Occupational Diseases        : {len(disease_records)}"
        )
        self.stdout.write(
            f"Health Incidents             : {len(incident_records)}"
        )
        self.stdout.write(
            f"Return To Work Records       : {len(return_to_work_records)}"
        )
        self.stdout.write(
            f"Medical Records              : {len(medical_records)}"
        )
        self.stdout.write(
            f"Health Camps                 : {len(camps)}"
        )
        self.stdout.write(
            f"Camp Participations          : {participation_count}"
        )

        self.stdout.write(
            self.style.SUCCESS(
                "=================================================="
            )
        )

    # =============================================
    # Create Examination Type Master Data
    # =============================================
    def seed_examination_types(self):

        data = [
            ("Pre-Employment Examination", "PRE_EMP"),
            ("Periodic Medical Examination", "PERIODIC"),
            ("Annual Health Examination", "ANNUAL"),
            ("Return to Work Examination", "RTW"),
            ("Special Medical Examination", "SPECIAL"),
            ("Exit Medical Examination", "EXIT"),
        ]

        records = []

        for name, code in data:
            obj, _ = ExaminationType.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": name,
                    "is_active": True,
                },
            )
            records.append(obj)

        return records

    # =============================================
    # Create Medical Test Master Data
    # =============================================
    def seed_medical_tests(self):

        data = [
            (
                "Complete Blood Count",
                "CBC",
                "LABORATORY",
                "Blood",
                "Hb: 13-17 g/dL",
            ),
            (
                "Blood Sugar",
                "BS",
                "LABORATORY",
                "mg/dL",
                "70-140 mg/dL",
            ),
            (
                "Blood Pressure",
                "BP",
                "PHYSICAL",
                "mmHg",
                "Around 120/80 mmHg",
            ),
            (
                "Vision Test",
                "VISION",
                "FUNCTIONAL",
                "",
                "6/6",
            ),
            (
                "Audiometry",
                "AUDIO",
                "DIAGNOSTIC",
                "dB",
                "Normal hearing range",
            ),
            (
                "Chest X-Ray",
                "CXR",
                "DIAGNOSTIC",
                "",
                "No abnormal finding",
            ),
            (
                "Pulmonary Function Test",
                "PFT",
                "FUNCTIONAL",
                "L/min",
                "Within expected range",
            ),
            (
                "Urine Examination",
                "URINE",
                "LABORATORY",
                "",
                "Normal",
            ),
        ]

        records = []

        for name, code, test_type, unit, normal_range in data:

            obj, _ = MedicalTest.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "test_type": test_type,
                    "unit": unit,
                    "normal_range": normal_range,
                    "description": name,
                    "is_active": True,
                },
            )

            records.append(obj)

        return records

    # =============================================
    # Create Exposure Type Master Data
    # =============================================
    def seed_exposure_types(self):

        data = [
            ("Noise", "NOISE"),
            ("Dust", "DUST"),
            ("Chemical", "CHEMICAL"),
            ("Heat", "HEAT"),
            ("Vibration", "VIBRATION"),
            ("Ergonomic", "ERGONOMIC"),
        ]

        records = []

        for name, code in data:

            obj, _ = ExposureType.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": f"{name} occupational exposure.",
                    "is_active": True,
                },
            )

            records.append(obj)

        return records

    # =============================================
    # Create Health Condition Master Data
    # =============================================
    def seed_health_conditions(self):

        data = [
            ("Respiratory Disorder", "RESP001", "RESPIRATORY", True),
            ("Hearing Loss", "HEAR001", "HEARING", True),
            ("Musculoskeletal Disorder", "MSD001", "MUSCULOSKELETAL", True),
            ("Dermatitis", "DERM001", "DERMATOLOGICAL", True),
            ("Hypertension", "CARD001", "CARDIOVASCULAR", False),
            ("Vision Disorder", "VIS001", "VISION", True),
            ("General Health Condition", "GEN001", "GENERAL", False),
        ]

        records = []

        for name, code, category, occupational in data:

            obj, _ = HealthCondition.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "category": category,
                    "description": name,
                    "is_occupational": occupational,
                    "is_active": True,
                },
            )

            records.append(obj)

        return records

    # =============================================
    # Create Fitness Status Master Data
    # =============================================
    def seed_fitness_statuses(self):

        data = [
            ("Fit", "FIT"),
            ("Fit With Restrictions", "FIT_RESTRICTIONS"),
            ("Temporarily Unfit", "TEMP_UNFIT"),
            ("Unfit", "UNFIT"),
        ]

        records = []

        for name, code in data:

            obj, _ = FitnessStatus.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": name,
                    "is_active": True,
                },
            )

            records.append(obj)

        return records

    # =============================================
    # Create Restriction Master Data
    # =============================================
    def seed_restrictions(self):

        data = [
            ("No Heavy Lifting", "NO_HEAVY_LIFT"),
            ("No Prolonged Standing", "NO_STANDING"),
            ("Noise Exposure Restriction", "NOISE_RESTRICT"),
            ("Chemical Exposure Restriction", "CHEMICAL_RESTRICT"),
            ("Night Shift Restriction", "NIGHT_SHIFT"),
        ]

        records = []

        for name, code in data:

            obj, _ = Restriction.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": name,
                    "is_active": True,
                },
            )

            records.append(obj)

        return records

    # =============================================
    # Create Vaccination Master Data
    # =============================================
    def seed_vaccinations(self):

        data = [
            (
                "Tetanus",
                "TETANUS",
                "Occupational tetanus vaccination.",
                1,
                60,
            ),
            (
                "Hepatitis B",
                "HEPB",
                "Hepatitis B vaccination.",
                3,
                60,
            ),
            (
                "Influenza",
                "INFLUENZA",
                "Annual influenza vaccination.",
                1,
                12,
            ),
            (
                "Typhoid",
                "TYPHOID",
                "Typhoid vaccination.",
                1,
                36,
            ),
        ]

        records = []

        for name, code, description, doses, validity in data:

            obj, _ = Vaccination.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": description,
                    "recommended_doses": doses,
                    "validity_months": validity,
                    "is_active": True,
                },
            )

            records.append(obj)

        return records

    # =============================================
    # Create Medical Professional Master Data
    # =============================================
    def seed_medical_professionals(self):

        data = [
            (
                "Dr. Amit Sharma",
                "DOC001",
                "OCCUPATIONAL_PHYSICIAN",
                "MBBS, AFIH",
                "Occupational Medicine",
            ),
            (
                "Dr. Neha Patil",
                "DOC002",
                "MEDICAL_OFFICER",
                "MBBS",
                "General Medicine",
            ),
            (
                "Dr. Rahul Deshmukh",
                "DOC003",
                "GENERAL_PHYSICIAN",
                "MBBS",
                "General Medicine",
            ),
            (
                "Ms. Priya Joshi",
                "NUR001",
                "NURSE",
                "B.Sc Nursing",
                "Occupational Health Nursing",
            ),
        ]

        records = []

        for name, code, professional_type, qualification, specialization in data:

            obj, _ = MedicalProfessional.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "professional_type": professional_type,
                    "qualification": qualification,
                    "specialization": specialization,
                    "registration_number": f"REG-{code}",
                    "contact_number": "9000000000",
                    "email": f"{code.lower()}@example.com",
                    "is_active": True,
                },
            )

            records.append(obj)

        return records

    # =============================================
    # Create Medical Facility Master Data
    # =============================================
    def seed_medical_facilities(self):

        data = [
            (
                "EHS Occupational Health Center",
                "FAC001",
                "OCCUPATIONAL_HEALTH_CENTER",
            ),
            (
                "City Multispeciality Hospital",
                "FAC002",
                "HOSPITAL",
            ),
            (
                "Prime Diagnostic Center",
                "FAC003",
                "DIAGNOSTIC_CENTER",
            ),
            (
                "EHS Medical Clinic",
                "FAC004",
                "CLINIC",
            ),
        ]

        records = []

        for name, code, facility_type in data:

            obj, _ = MedicalFacility.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "facility_type": facility_type,
                    "address": "Industrial Area",
                    "contact_person": "Medical Administration",
                    "contact_number": "9000000000",
                    "email": f"{code.lower()}@example.com",
                    "registration_number": f"REG-{code}",
                    "description": name,
                    "is_active": True,
                },
            )

            records.append(obj)

        return records

    # =============================================
    # Clear Occupational Health Demo Data
    # =============================================
    def clear_demo_data(self):

        self.stdout.write(
            self.style.WARNING(
                "Clearing Occupational Health transactional data..."
            )
        )

        HealthCampParticipation.objects.all().delete()
        HealthCamp.objects.all().delete()
        MedicalRecord.objects.all().delete()
        ReturnToWork.objects.all().delete()
        HealthIncident.objects.all().delete()
        EmployeeOccupationalDisease.objects.all().delete()
        EmployeeVaccination.objects.all().delete()
        MedicalFollowUp.objects.all().delete()
        EmployeeExposure.objects.all().delete()
        HealthSurveillance.objects.all().delete()
        FitnessToWork.objects.all().delete()
        MedicalTestResult.objects.all().delete()
        MedicalExamination.objects.all().delete()
        EmployeeHealthProfile.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Occupational Health transactional data cleared."
            )
        )