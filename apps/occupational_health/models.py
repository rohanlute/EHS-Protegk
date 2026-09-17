from django.db import models
from django.conf import settings
from django.utils import timezone


class ExaminationType(models.Model):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_oh_examination_types'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Examination Type'
        verbose_name_plural = 'Examination Types'

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        if self.code:
            self.code = self.code.upper()



class MedicalTest(models.Model):
    TEST_TYPE_CHOICES = [
        ('LABORATORY', 'Laboratory'),
        ('DIAGNOSTIC', 'Diagnostic'),
        ('PHYSICAL', 'Physical Examination'),
        ('FUNCTIONAL', 'Functional'),
        ('SPECIALIST', 'Specialist'),
        ('OTHER', 'Other'),
    ]

    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)
    test_type = models.CharField(max_length=30, choices=TEST_TYPE_CHOICES, default='OTHER')
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=50, blank=True)
    normal_range = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_oh_medical_tests'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Medical Test'
        verbose_name_plural = 'Medical Tests'

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        if self.code:
            self.code = self.code.upper()




class ExposureType(models.Model):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_oh_exposure_types'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Exposure Type'
        verbose_name_plural = 'Exposure Types'

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        if self.code:
            self.code = self.code.upper()



# =============================================
# HealthCondition - Stores standardized employee health conditions for Occupational Health records, surveillance and disease tracking
# =============================================
class HealthCondition(models.Model):
    CATEGORY_CHOICES = [
        ('GENERAL', 'General'),
        ('OCCUPATIONAL', 'Occupational'),
        ('RESPIRATORY', 'Respiratory'),
        ('MUSCULOSKELETAL', 'Musculoskeletal'),
        ('DERMATOLOGICAL', 'Dermatological'),
        ('CARDIOVASCULAR', 'Cardiovascular'),
        ('HEARING', 'Hearing'),
        ('VISION', 'Vision'),
        ('MENTAL_HEALTH', 'Mental Health'),
        ('INFECTIOUS_DISEASE', 'Infectious Disease'),
        ('OTHER', 'Other'),
    ]

    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default='GENERAL'
    )
    description = models.TextField(blank=True)
    is_occupational = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_oh_health_conditions'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Health Condition'
        verbose_name_plural = 'Health Conditions'

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        if self.code:
            self.code = self.code.upper()



# =============================================
# FitnessStatus - Stores standardized medical fitness outcomes used for employee fitness-to-work decisions
# =============================================
class FitnessStatus(models.Model):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_oh_fitness_statuses'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Fitness Status'
        verbose_name_plural = 'Fitness Statuses'

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        if self.code:
            self.code = self.code.upper()




# =============================================
# Restriction - Stores standardized medical/work restrictions applicable to employees
# =============================================
class Restriction(models.Model):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_oh_restrictions'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Restriction'
        verbose_name_plural = 'Restrictions'

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        if self.code:
            self.code = self.code.upper()





# =============================================
# Vaccination - Stores standardized vaccination types used for Occupational Health vaccination records
# =============================================
class Vaccination(models.Model):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    recommended_doses = models.PositiveIntegerField(default=1)
    validity_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Validity period in months, if applicable.'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_oh_vaccinations'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Vaccination'
        verbose_name_plural = 'Vaccinations'

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        if self.code:
            self.code = self.code.upper()




# =============================================
# MedicalProfessional - Stores doctors and medical professionals involved in Occupational Health activities
# =============================================
class MedicalProfessional(models.Model):
    PROFESSIONAL_TYPE_CHOICES = [
        ('OCCUPATIONAL_PHYSICIAN', 'Occupational Physician'),
        ('MEDICAL_OFFICER', 'Medical Officer'),
        ('GENERAL_PHYSICIAN', 'General Physician'),
        ('SPECIALIST', 'Specialist'),
        ('NURSE', 'Nurse'),
        ('PARAMEDIC', 'Paramedic'),
        ('OTHER', 'Other'),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    professional_type = models.CharField(
        max_length=40,
        choices=PROFESSIONAL_TYPE_CHOICES,
        default='MEDICAL_OFFICER'
    )
    qualification = models.CharField(max_length=200, blank=True)
    specialization = models.CharField(max_length=200, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_oh_medical_professionals'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Medical Professional'
        verbose_name_plural = 'Medical Professionals'

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        if self.code:
            self.code = self.code.upper()



# =============================================
# MedicalFacility - Stores hospitals, clinics, diagnostic centers and other facilities used for Occupational Health activities
# =============================================
class MedicalFacility(models.Model):
    FACILITY_TYPE_CHOICES = [
        ('HOSPITAL', 'Hospital'),
        ('CLINIC', 'Clinic'),
        ('DIAGNOSTIC_CENTER', 'Diagnostic Center'),
        ('OCCUPATIONAL_HEALTH_CENTER', 'Occupational Health Center'),
        ('PHARMACY', 'Pharmacy'),
        ('OTHER', 'Other'),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    facility_type = models.CharField(
        max_length=40,
        choices=FACILITY_TYPE_CHOICES,
        default='CLINIC'
    )
    address = models.TextField(blank=True)
    contact_person = models.CharField(max_length=200, blank=True)
    contact_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_oh_medical_facilities'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Medical Facility'
        verbose_name_plural = 'Medical Facilities'

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        if self.code:
            self.code = self.code.upper()


# =============================================
# EmployeeHealthProfile - Stores the occupational health profile and work-related health information of an employee
# =============================================
class EmployeeHealthProfile(models.Model):

    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
        ('NOT_SPECIFIED', 'Not Specified'),
    ]

    BLOOD_GROUP_CHOICES = [
        ('A_POSITIVE', 'A+'),
        ('A_NEGATIVE', 'A-'),
        ('B_POSITIVE', 'B+'),
        ('B_NEGATIVE', 'B-'),
        ('AB_POSITIVE', 'AB+'),
        ('AB_NEGATIVE', 'AB-'),
        ('O_POSITIVE', 'O+'),
        ('O_NEGATIVE', 'O-'),
        ('UNKNOWN', 'Unknown'),
    ]

    EMPLOYMENT_TYPE_CHOICES = [
        ('PERMANENT', 'Permanent'),
        ('CONTRACT', 'Contract'),
        ('TEMPORARY', 'Temporary'),
        ('TRAINEE', 'Trainee'),
        ('APPRENTICE', 'Apprentice'),
        ('OTHER', 'Other'),
    ]

    PROFILE_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    ]

    employee = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='occupational_health_profile'
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True
    )

    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        blank=True
    )

    blood_group = models.CharField(
        max_length=20,
        choices=BLOOD_GROUP_CHOICES,
        blank=True
    )

    emergency_contact_name = models.CharField(
        max_length=200,
        blank=True
    )

    emergency_contact_number = models.CharField(
        max_length=30,
        blank=True
    )

    date_of_joining = models.DateField(
        null=True,
        blank=True
    )

    work_shift = models.CharField(
        max_length=100,
        blank=True
    )

    employment_type = models.CharField(
        max_length=30,
        choices=EMPLOYMENT_TYPE_CHOICES,
        blank=True
    )

    job_role = models.CharField(
        max_length=200,
        blank=True
    )

    work_area = models.CharField(
        max_length=200,
        blank=True
    )

    health_profile_status = models.CharField(
        max_length=20,
        choices=PROFILE_STATUS_CHOICES,
        default='ACTIVE'
    )

    is_under_health_surveillance = models.BooleanField(
        default=False
    )

    is_active = models.BooleanField(
        default=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_employee_health_profiles'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['employee']
        verbose_name = 'Employee Health Profile'
        verbose_name_plural = 'Employee Health Profiles'


    def clean(self):
        if self.date_of_birth and self.date_of_joining:
            if self.date_of_joining <= self.date_of_birth:
                from django.core.exceptions import ValidationError

                raise ValidationError({
                    'date_of_joining': 'Date of Joining must be after Date of Birth.'
                })


    def __str__(self):
        employee_name = self.employee.get_full_name() or self.employee.username
        return f"{employee_name} - Health Profile"



# =============================================
# MedicalExamination - Stores medical examination records performed for an employee
# =============================================
class MedicalExamination(models.Model):
    PURPOSE_CHOICES = [
        ('PRE_EMPLOYMENT', 'Pre-Employment'),
        ('PERIODIC', 'Periodic'),
        ('ANNUAL', 'Annual'),
        ('RETURN_TO_WORK', 'Return to Work'),
        ('SPECIAL', 'Special'),
        ('EXIT', 'Exit'),
    ]

    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    employee_health_profile = models.ForeignKey(
        'EmployeeHealthProfile',
        on_delete=models.CASCADE,
        related_name='medical_examinations'
    )

    examination_type = models.ForeignKey(
        'ExaminationType',
        on_delete=models.PROTECT,
        related_name='medical_examinations'
    )

    examination_date = models.DateField()

    purpose = models.CharField(
        max_length=30,
        choices=PURPOSE_CHOICES
    )

    medical_professional = models.ForeignKey(
        'MedicalProfessional',
        on_delete=models.PROTECT,
        related_name='medical_examinations'
    )

    medical_facility = models.ForeignKey(
        'MedicalFacility',
        on_delete=models.PROTECT,
        related_name='medical_examinations'
    )

    job_role = models.CharField(
        max_length=200,
        blank=True
    )

    work_area = models.CharField(
        max_length=200,
        blank=True
    )

    general_findings = models.TextField(
        blank=True
    )

    abnormal_findings = models.TextField(
        blank=True
    )

    recommendations = models.TextField(
        blank=True
    )

    follow_up_required = models.BooleanField(
        default=False
    )

    follow_up_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SCHEDULED'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_medical_examinations'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['-examination_date', '-id']
        verbose_name = 'Medical Examination'
        verbose_name_plural = 'Medical Examinations'

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.follow_up_required and not self.follow_up_date:
            raise ValidationError({
                'follow_up_date': 'Follow-up Date is required when Follow-up is required.'
            })

        if not self.follow_up_required and self.follow_up_date:
            raise ValidationError({
                'follow_up_date': 'Follow-up Date should be empty when Follow-up is not required.'
            })

    def __str__(self):
        employee_name = (
            self.employee_health_profile.employee.get_full_name()
            or self.employee_health_profile.employee.username
        )
        return f"{employee_name} - {self.examination_type.name} - {self.examination_date}"




# =============================================
# MedicalTestResult - Stores the result and clinical findings of a medical test performed for an employee
# =============================================
class MedicalTestResult(models.Model):
    RESULT_STATUS_CHOICES = [
        ('NORMAL', 'Normal'),
        ('ABNORMAL', 'Abnormal'),
        ('BORDERLINE', 'Borderline'),
        ('NOT_CONDUCTED', 'Not Conducted'),
        ('PENDING', 'Pending'),
    ]

    medical_examination = models.ForeignKey(
        'MedicalExamination',
        on_delete=models.CASCADE,
        related_name='test_results'
    )
    medical_test = models.ForeignKey(
        'MedicalTest',
        on_delete=models.PROTECT,
        related_name='test_results'
    )
    test_date = models.DateField()
    result_value = models.CharField(max_length=500, blank=True)
    unit = models.CharField(max_length=100, blank=True)
    reference_range = models.CharField(max_length=200, blank=True)
    result_status = models.CharField(
        max_length=30,
        choices=RESULT_STATUS_CHOICES,
        default='PENDING'
    )
    findings = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    doctor_comments = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to='occupational_health/medical_test_results/',
        null=True,
        blank=True
    )
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_medical_test_results'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-test_date', '-id']
        verbose_name = 'Medical Test Result'
        verbose_name_plural = 'Medical Test Results'

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.follow_up_required and not self.follow_up_date:
            raise ValidationError({
                'follow_up_date': 'Follow-up Date is required when Follow-up is required.'
            })

        if not self.follow_up_required and self.follow_up_date:
            raise ValidationError({
                'follow_up_date': 'Follow-up Date should be empty when Follow-up is not required.'
            })

        if (
            self.test_date
            and self.follow_up_date
            and self.follow_up_date < self.test_date
        ):
            raise ValidationError({
                'follow_up_date': 'Follow-up Date cannot be before the Test Date.'
            })

    def __str__(self):
        employee_name = (
            self.medical_examination.employee_health_profile.employee.get_full_name()
            or self.medical_examination.employee_health_profile.employee.username
        )
        return f"{employee_name} - {self.medical_test.name} - {self.test_date}"



# =============================================
# FitnessToWork - Stores the employee's medical fitness assessment and work restrictions
# =============================================
class FitnessToWork(models.Model):
    FITNESS_STATUS_CHOICES = [
        ('FIT', 'Fit'),
        ('FIT_WITH_RESTRICTIONS', 'Fit With Restrictions'),
        ('TEMPORARILY_UNFIT', 'Temporarily Unfit'),
        ('UNFIT', 'Unfit'),
    ]

    ASSESSMENT_TYPE_CHOICES = [
        ('PRE_EMPLOYMENT', 'Pre-Employment'),
        ('PERIODIC', 'Periodic'),
        ('ANNUAL', 'Annual'),
        ('RETURN_TO_WORK', 'Return to Work'),
        ('SPECIAL', 'Special'),
        ('EXIT', 'Exit'),
    ]

    medical_examination = models.ForeignKey(
        'MedicalExamination',
        on_delete=models.CASCADE,
        related_name='fitness_assessments'
    )
    employee_health_profile = models.ForeignKey(
        'EmployeeHealthProfile',
        on_delete=models.CASCADE,
        related_name='fitness_assessments'
    )
    assessment_date = models.DateField()
    assessment_type = models.CharField(
        max_length=30,
        choices=ASSESSMENT_TYPE_CHOICES
    )
    fitness_status = models.CharField(
        max_length=30,
        choices=FITNESS_STATUS_CHOICES
    )
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    restrictions = models.ManyToManyField(
        'Restriction',
        blank=True,
        related_name='fitness_assessments'
    )
    medical_findings = models.TextField(blank=True)
    work_recommendations = models.TextField(blank=True)
    doctor_comments = models.TextField(blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    status = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_fitness_assessments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-assessment_date', '-id']
        verbose_name = 'Fitness to Work'
        verbose_name_plural = 'Fitness to Work Assessments'

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.valid_until and self.valid_until < self.valid_from:
            raise ValidationError({
                'valid_until': 'Valid Until date cannot be before Valid From date.'
            })

        if self.follow_up_required and not self.follow_up_date:
            raise ValidationError({
                'follow_up_date': 'Follow-up Date is required when Follow-up is required.'
            })

        if not self.follow_up_required and self.follow_up_date:
            raise ValidationError({
                'follow_up_date': 'Follow-up Date should be empty when Follow-up is not required.'
            })

        if self.assessment_date and self.follow_up_date:
            if self.follow_up_date < self.assessment_date:
                raise ValidationError({
                    'follow_up_date': 'Follow-up Date cannot be before the Assessment Date.'
                })

        if self.medical_examination_id and self.employee_health_profile_id:
            if self.employee_health_profile_id != self.medical_examination.employee_health_profile_id:
                raise ValidationError({
                    'employee_health_profile': 'Employee Health Profile must match the selected Medical Examination.'
                })

    def __str__(self):
        employee_name = (
            self.employee_health_profile.employee.get_full_name()
            or self.employee_health_profile.employee.username
        )
        return f"{employee_name} - {self.get_fitness_status_display()} - {self.assessment_date}"




# =============================================
# HealthSurveillance - Stores occupational health surveillance programs assigned to employees based on workplace health risks and exposures
# =============================================
class HealthSurveillance(models.Model):
    FREQUENCY_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('HALF_YEARLY', 'Half Yearly'),
        ('YEARLY', 'Yearly'),
        ('BIENNIAL', 'Every 2 Years'),
        ('AS_REQUIRED', 'As Required'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
        ('COMPLETED', 'Completed'),
        ('CLOSED', 'Closed'),
    ]

    employee_health_profile = models.ForeignKey(
        'EmployeeHealthProfile',
        on_delete=models.CASCADE,
        related_name='health_surveillance_records'
    )
    exposure_type = models.ForeignKey(
        'ExposureType',
        on_delete=models.PROTECT,
        related_name='health_surveillance_records'
    )
    surveillance_name = models.CharField(max_length=200)
    surveillance_frequency = models.CharField(
        max_length=30,
        choices=FREQUENCY_CHOICES
    )
    start_date = models.DateField()
    next_due_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    responsible_medical_professional = models.ForeignKey(
        'MedicalProfessional',
        on_delete=models.PROTECT,
        related_name='health_surveillance_records'
    )
    medical_facility = models.ForeignKey(
        'MedicalFacility',
        on_delete=models.PROTECT,
        related_name='health_surveillance_records'
    )
    health_objectives = models.TextField(blank=True)
    required_tests = models.ManyToManyField(
        'MedicalTest',
        blank=True,
        related_name='health_surveillance_programs'
    )
    remarks = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_health_surveillance_records'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', '-id']
        verbose_name = 'Health Surveillance'
        verbose_name_plural = 'Health Surveillance Records'

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({
                'end_date': 'End Date cannot be before the Start Date.'
            })

        if self.next_due_date and self.next_due_date < self.start_date:
            raise ValidationError({
                'next_due_date': 'Next Due Date cannot be before the Start Date.'
            })

    # =============================================
    # HealthSurveillance - Determines the current due status of the surveillance program
    # =============================================
    @property
    def due_status(self):
        from django.utils import timezone

        if not self.next_due_date:
            return 'NOT_SET'

        if self.status != 'ACTIVE' or not self.is_active:
            return 'INACTIVE'

        today = timezone.localdate()
        days_remaining = (self.next_due_date - today).days

        if days_remaining < 0:
            return 'OVERDUE'

        if days_remaining == 0:
            return 'DUE_TODAY'

        if days_remaining <= 30:
            return 'DUE_SOON'

        return 'UPCOMING'

    # =============================================
    # HealthSurveillance - Returns the number of days remaining until the next surveillance is due
    # =============================================
    @property
    def days_until_due(self):
        from django.utils import timezone

        if not self.next_due_date:
            return None

        return (self.next_due_date - timezone.localdate()).days

    # =============================================
    # HealthSurveillance - Returns a human-readable description of the surveillance due status
    # =============================================
    @property
    def due_status_display(self):
        status_map = {
            'OVERDUE': 'Overdue',
            'DUE_TODAY': 'Due Today',
            'DUE_SOON': 'Due Soon',
            'UPCOMING': 'Upcoming',
            'NOT_SET': 'Not Set',
            'INACTIVE': 'Inactive',
        }

        return status_map.get(self.due_status, 'Unknown')

    def __str__(self):
        employee_name = (
            self.employee_health_profile.employee.get_full_name()
            or self.employee_health_profile.employee.username
        )
        return f"{employee_name} - {self.surveillance_name}"





# =============================================
# EmployeeExposure - Stores occupational exposure experienced by an employee
# =============================================
class EmployeeExposure(models.Model):
    EXPOSURE_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('CLOSED', 'Closed'),
    ]

    employee_health_profile = models.ForeignKey(
        'EmployeeHealthProfile',
        on_delete=models.CASCADE,
        related_name='exposure_records'
    )
    exposure_type = models.ForeignKey(
        'ExposureType',
        on_delete=models.PROTECT,
        related_name='employee_exposures'
    )
    exposure_name = models.CharField(
        max_length=200
    )
    exposure_source = models.CharField(
        max_length=250,
        blank=True
    )
    work_area = models.CharField(
        max_length=200,
        blank=True
    )
    job_role = models.CharField(
        max_length=200,
        blank=True
    )
    exposure_start_date = models.DateField()
    exposure_end_date = models.DateField(
        null=True,
        blank=True
    )
    exposure_frequency = models.CharField(
        max_length=100,
        blank=True
    )
    exposure_duration = models.CharField(
        max_length=100,
        blank=True
    )
    exposure_level = models.CharField(
        max_length=100,
        blank=True
    )
    control_measures = models.TextField(
        blank=True
    )
    ppe_used = models.CharField(
        max_length=250,
        blank=True
    )
    health_surveillance_required = models.BooleanField(
        default=False
    )
    health_surveillance = models.ForeignKey(
        'HealthSurveillance',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exposure_records'
    )
    remarks = models.TextField(
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=EXPOSURE_STATUS_CHOICES,
        default='ACTIVE'
    )
    is_active = models.BooleanField(
        default=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_employee_exposures'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['-exposure_start_date', '-id']
        verbose_name = 'Employee Exposure'
        verbose_name_plural = 'Employee Exposures'

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.exposure_end_date and self.exposure_end_date < self.exposure_start_date:
            raise ValidationError({
                'exposure_end_date': 'Exposure End Date cannot be before the Exposure Start Date.'
            })

        if self.employee_health_profile_id:
            if not self.employee_health_profile.is_active:
                raise ValidationError({
                    'employee_health_profile': 'The selected Employee Health Profile is inactive.'
                })

        if self.health_surveillance_id:
            if self.health_surveillance.employee_health_profile_id != self.employee_health_profile_id:
                raise ValidationError({
                    'health_surveillance': 'Selected Health Surveillance must belong to the same employee.'
                })

    @property
    def exposure_status_display(self):
        return self.get_status_display()

    def __str__(self):
        employee_name = (
            self.employee_health_profile.employee.get_full_name()
            or self.employee_health_profile.employee.username
        )
        return f"{employee_name} - {self.exposure_name}"




class MedicalFollowUp(models.Model):
    FOLLOW_UP_TYPE_CHOICES = [
        ('EXAMINATION', 'Medical Examination'),
        ('TEST', 'Medical Test'),
        ('FITNESS', 'Fitness Assessment'),
        ('SURVEILLANCE', 'Health Surveillance'),
        ('EXPOSURE', 'Exposure Review'),
        ('OTHER', 'Other'),
    ]
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('OVERDUE', 'Overdue'),
    ]
    STATUS_TRANSITIONS = {
        'PENDING': ['SCHEDULED', 'OVERDUE', 'CANCELLED'],
        'SCHEDULED': ['IN_PROGRESS', 'OVERDUE', 'CANCELLED'],
        'IN_PROGRESS': ['COMPLETED', 'OVERDUE', 'CANCELLED'],
        'OVERDUE': ['SCHEDULED', 'IN_PROGRESS', 'CANCELLED'],
        'COMPLETED': [],
        'CANCELLED': [],
    }
    employee_health_profile = models.ForeignKey(
        'EmployeeHealthProfile',
        on_delete=models.CASCADE,
        related_name='medical_follow_ups'
    )
    medical_examination = models.ForeignKey(
        'MedicalExamination',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_follow_ups'
    )
    medical_test_result = models.ForeignKey(
        'MedicalTestResult',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_follow_ups'
    )
    fitness_assessment = models.ForeignKey(
        'FitnessToWork',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_follow_ups'
    )
    health_surveillance = models.ForeignKey(
        'HealthSurveillance',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_follow_ups'
    )
    exposure = models.ForeignKey(
        'EmployeeExposure',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_follow_ups'
    )
    follow_up_type = models.CharField(
        max_length=30,
        choices=FOLLOW_UP_TYPE_CHOICES
    )
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='MEDIUM'
    )
    assigned_medical_professional = models.ForeignKey(
        'MedicalProfessional',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='assigned_medical_follow_ups'
    )
    medical_facility = models.ForeignKey(
        'MedicalFacility',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='medical_follow_ups'
    )
    outcome = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_medical_follow_ups'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_date', '-id']
        verbose_name = 'Medical Follow-up'
        verbose_name_plural = 'Medical Follow-ups'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.completed_date and self.scheduled_date and self.completed_date < self.scheduled_date:
            raise ValidationError({
                'completed_date': 'Completed Date cannot be before the Scheduled Date.'
            })
        if self.employee_health_profile_id and not self.employee_health_profile.is_active:
            raise ValidationError({
                'employee_health_profile': 'The selected Employee Health Profile is inactive.'
            })
        if self.medical_examination_id and self.medical_examination.employee_health_profile_id != self.employee_health_profile_id:
            raise ValidationError({
                'medical_examination': 'Medical Examination must belong to the selected employee.'
            })
        if self.medical_test_result_id and self.medical_test_result.medical_examination.employee_health_profile_id != self.employee_health_profile_id:
            raise ValidationError({
                'medical_test_result': 'Medical Test Result must belong to the selected employee.'
            })
        if self.fitness_assessment_id and self.fitness_assessment.employee_health_profile_id != self.employee_health_profile_id:
            raise ValidationError({
                'fitness_assessment': 'Fitness Assessment must belong to the selected employee.'
            })
        if self.health_surveillance_id and self.health_surveillance.employee_health_profile_id != self.employee_health_profile_id:
            raise ValidationError({
                'health_surveillance': 'Health Surveillance must belong to the selected employee.'
            })
        if self.exposure_id and self.exposure.employee_health_profile_id != self.employee_health_profile_id:
            raise ValidationError({
                'exposure': 'Exposure must belong to the selected employee.'
            })
        if self.status == 'COMPLETED' and not self.outcome.strip():
            raise ValidationError({
                'outcome': 'Outcome is required when the follow-up is marked as Completed.'
            })
        if self.status == 'COMPLETED' and not self.completed_date:
            raise ValidationError({
                'completed_date': 'Completed Date is required when the follow-up is marked as Completed.'
            })
        if self.pk:
            try:
                previous = MedicalFollowUp.objects.get(pk=self.pk)
                if previous.status != self.status:
                    allowed_statuses = self.STATUS_TRANSITIONS.get(previous.status, [])
                    if self.status not in allowed_statuses:
                        raise ValidationError({
                            'status': f'Invalid status transition from {previous.get_status_display()} to {self.get_status_display()}.'
                        })
            except MedicalFollowUp.DoesNotExist:
                pass

    @property
    def effective_status(self):
        from django.utils import timezone
        if (
            self.status not in ['COMPLETED', 'CANCELLED']
            and self.scheduled_date
            and self.scheduled_date < timezone.localdate()
        ):
            return 'OVERDUE'
        return self.status

    @property
    def effective_status_display(self):
        return dict(self.STATUS_CHOICES).get(
            self.effective_status,
            self.get_status_display()
        )

    def can_transition_to(self, new_status):
        if new_status == self.status:
            return True
        return new_status in self.STATUS_TRANSITIONS.get(self.status, [])

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if self.scheduled_date and self.status not in ['COMPLETED', 'CANCELLED']:
            if self.scheduled_date < timezone.localdate():
                self.status = 'OVERDUE'
            elif self.status == 'OVERDUE':
                self.status = 'SCHEDULED'
        super().save(*args, **kwargs)

    def __str__(self):
        employee_name = (
            self.employee_health_profile.employee.get_full_name()
            or self.employee_health_profile.employee.username
        )
        return f"{employee_name} - {self.title}"






class EmployeeVaccination(models.Model):
    DOSE_STATUS_CHOICES=[
        ('COMPLETED','Completed'),
        ('PARTIAL','Partial'),
        ('MISSED','Missed'),
        ('SCHEDULED','Scheduled'),
        ('CANCELLED','Cancelled'),
    ]
    VACCINATION_STATUS_CHOICES=[
        ('ACTIVE','Active'),
        ('COMPLETED','Completed'),
        ('EXPIRED','Expired'),
        ('CANCELLED','Cancelled'),
    ]
    employee_health_profile=models.ForeignKey('EmployeeHealthProfile',on_delete=models.CASCADE,related_name='vaccinations')
    vaccination=models.ForeignKey('Vaccination',on_delete=models.PROTECT,related_name='employee_vaccinations')
    dose_number=models.PositiveIntegerField(default=1)
    vaccination_date=models.DateField()
    next_due_date=models.DateField(null=True,blank=True)
    expiry_date=models.DateField(null=True,blank=True)
    dose_status=models.CharField(max_length=20,choices=DOSE_STATUS_CHOICES,default='COMPLETED')
    vaccination_status=models.CharField(max_length=20,choices=VACCINATION_STATUS_CHOICES,default='ACTIVE')
    medical_professional=models.ForeignKey('MedicalProfessional',on_delete=models.PROTECT,null=True,blank=True,related_name='employee_vaccinations')
    medical_facility=models.ForeignKey('MedicalFacility',on_delete=models.PROTECT,null=True,blank=True,related_name='employee_vaccinations')
    batch_number=models.CharField(max_length=100,blank=True)
    manufacturer=models.CharField(max_length=200,blank=True)
    certificate_number=models.CharField(max_length=150,blank=True)
    attachment=models.FileField(upload_to='occupational_health/vaccinations/',null=True,blank=True)
    adverse_reaction=models.BooleanField(default=False)
    adverse_reaction_details=models.TextField(blank=True)
    remarks=models.TextField(blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='created_employee_vaccinations')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['-vaccination_date','-id']
        verbose_name='Employee Vaccination'
        verbose_name_plural='Employee Vaccinations'
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.employee_health_profile_id and not self.employee_health_profile.is_active:
            raise ValidationError({'employee_health_profile':'The selected Employee Health Profile is inactive.'})
        if self.next_due_date and self.vaccination_date and self.next_due_date < self.vaccination_date:
            raise ValidationError({'next_due_date':'Next Due Date cannot be before the Vaccination Date.'})
        if self.expiry_date and self.vaccination_date and self.expiry_date < self.vaccination_date:
            raise ValidationError({'expiry_date':'Expiry Date cannot be before the Vaccination Date.'})
        if self.adverse_reaction and not self.adverse_reaction_details.strip():
            raise ValidationError({'adverse_reaction_details':'Please provide details when an adverse reaction is reported.'})
        if not self.adverse_reaction and self.adverse_reaction_details:
            raise ValidationError({'adverse_reaction_details':'Adverse reaction details should be empty when no adverse reaction is reported.'})
        if self.vaccination_id and self.dose_number:
            max_doses=self.vaccination.recommended_doses
            if max_doses and self.dose_number > max_doses:
                raise ValidationError({'dose_number':f'Dose Number cannot be greater than the recommended {max_doses} dose(s).'})


    def save(self,*args,**kwargs):
        from dateutil.relativedelta import relativedelta
        from django.utils import timezone
        if self.vaccination_id and self.vaccination_date:
            validity_months=self.vaccination.validity_months
            if not self.expiry_date and validity_months:
                self.expiry_date=self.vaccination_date+relativedelta(months=validity_months)
            if not self.next_due_date and self.dose_number:
                recommended_doses=self.vaccination.recommended_doses
                if recommended_doses and self.dose_number<recommended_doses:
                    self.next_due_date=self.vaccination_date+relativedelta(months=1)
        if self.expiry_date and self.vaccination_status=='ACTIVE':
            if self.expiry_date<timezone.localdate():
                self.vaccination_status='EXPIRED'
        if self.dose_status=='COMPLETED' and self.vaccination.recommended_doses:
            if self.dose_number>=self.vaccination.recommended_doses and self.vaccination_status=='ACTIVE':
                self.vaccination_status='COMPLETED'
        super().save(*args,**kwargs)
    
    def __str__(self):
        employee=self.employee_health_profile.employee
        employee_name=employee.get_full_name() or employee.username
        return f'{employee_name} - {self.vaccination.name} - Dose {self.dose_number}'




class EmployeeOccupationalDisease(models.Model):
    DISEASE_STATUS_CHOICES=[
        ('SUSPECTED','Suspected'),
        ('CONFIRMED','Confirmed'),
        ('UNDER_REVIEW','Under Review'),
        ('CLOSED','Closed'),
    ]
    SEVERITY_CHOICES=[
        ('MILD','Mild'),
        ('MODERATE','Moderate'),
        ('SEVERE','Severe'),
        ('CRITICAL','Critical'),
    ]
    RECORD_STATUS_CHOICES=[
        ('ACTIVE','Active'),
        ('UNDER_INVESTIGATION','Under Investigation'),
        ('TREATMENT','Under Treatment'),
        ('FOLLOW_UP','Follow-up Required'),
        ('CLOSED','Closed'),
    ]
    employee_health_profile=models.ForeignKey(
        'EmployeeHealthProfile',
        on_delete=models.CASCADE,
        related_name='occupational_diseases'
    )
    health_condition=models.ForeignKey(
        'HealthCondition',
        on_delete=models.PROTECT,
        related_name='occupational_diseases'
    )
    reported_date=models.DateField()
    diagnosis_date=models.DateField(null=True,blank=True)
    disease_status=models.CharField(
        max_length=20,
        choices=DISEASE_STATUS_CHOICES,
        default='SUSPECTED'
    )
    severity=models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='MILD'
    )
    symptoms=models.TextField(blank=True)
    diagnosis_details=models.TextField(blank=True)
    exposure_related=models.BooleanField(default=False)
    exposure=models.ForeignKey(
        'EmployeeExposure',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='occupational_diseases'
    )
    medical_professional=models.ForeignKey(
        'MedicalProfessional',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='occupational_diseases'
    )
    medical_facility=models.ForeignKey(
        'MedicalFacility',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='occupational_diseases'
    )
    work_area=models.CharField(max_length=200,blank=True)
    job_role=models.CharField(max_length=200,blank=True)
    treatment_details=models.TextField(blank=True)
    work_restrictions=models.TextField(blank=True)
    follow_up_required=models.BooleanField(default=False)
    follow_up_date=models.DateField(null=True,blank=True)
    investigation_required=models.BooleanField(default=False)
    investigation_findings=models.TextField(blank=True)
    corrective_actions=models.TextField(blank=True)
    remarks=models.TextField(blank=True)
    attachment=models.FileField(
        upload_to='occupational_health/diseases/',
        null=True,
        blank=True
    )
    status=models.CharField(
        max_length=30,
        choices=RECORD_STATUS_CHOICES,
        default='ACTIVE'
    )
    created_by=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_occupational_diseases'
    )
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        ordering=['-reported_date','-id']
        verbose_name='Occupational Disease'
        verbose_name_plural='Occupational Diseases'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.employee_health_profile_id and not self.employee_health_profile.is_active:
            raise ValidationError({
                'employee_health_profile':'The selected Employee Health Profile is inactive.'
            })
        if self.diagnosis_date and self.reported_date:
            if self.diagnosis_date < self.reported_date:
                raise ValidationError({
                    'diagnosis_date':'Diagnosis Date cannot be before the Reported Date.'
                })
        if self.follow_up_required and not self.follow_up_date:
            raise ValidationError({
                'follow_up_date':'Follow-up Date is required when Follow-up is required.'
            })
        if not self.follow_up_required and self.follow_up_date:
            raise ValidationError({
                'follow_up_date':'Follow-up Date should be empty when Follow-up is not required.'
            })
        if self.follow_up_date and self.reported_date:
            if self.follow_up_date < self.reported_date:
                raise ValidationError({
                    'follow_up_date':'Follow-up Date cannot be before the Reported Date.'
                })
        if self.exposure_related and not self.exposure_id:
            raise ValidationError({
                'exposure':'Exposure record is required when Exposure Related is selected.'
            })
        if not self.exposure_related and self.exposure_id:
            raise ValidationError({
                'exposure':'Exposure record should be empty when Exposure Related is not selected.'
            })
        if self.exposure_id and self.employee_health_profile_id:
            if self.exposure.employee_health_profile_id != self.employee_health_profile_id:
                raise ValidationError({
                    'exposure':'Selected Exposure must belong to the same employee.'
                })

    def __str__(self):
        employee=self.employee_health_profile.employee
        employee_name=employee.get_full_name() or employee.username
        return f'{employee_name} - {self.health_condition.name}'




class HealthIncident(models.Model):
    INCIDENT_TYPE_CHOICES=[
        ('WORK_RELATED_ILLNESS','Work Related Illness'),
        ('OCCUPATIONAL_EXPOSURE','Occupational Exposure'),
        ('MEDICAL_EMERGENCY','Medical Emergency'),
        ('FIRST_AID','First Aid'),
        ('HEALTH_COMPLAINT','Health Complaint'),
        ('OTHER','Other'),
    ]
    SEVERITY_CHOICES=[
        ('MINOR','Minor'),
        ('MODERATE','Moderate'),
        ('SERIOUS','Serious'),
        ('CRITICAL','Critical'),
    ]
    STATUS_CHOICES=[
        ('REPORTED','Reported'),
        ('UNDER_REVIEW','Under Review'),
        ('UNDER_INVESTIGATION','Under Investigation'),
        ('TREATED','Treated'),
        ('CLOSED','Closed'),
    ]

    employee_health_profile=models.ForeignKey(
        'EmployeeHealthProfile',
        on_delete=models.CASCADE,
        related_name='health_incidents'
    )
    incident_date=models.DateField()
    incident_time=models.TimeField(null=True,blank=True)
    incident_type=models.CharField(max_length=30,choices=INCIDENT_TYPE_CHOICES)
    severity=models.CharField(max_length=20,choices=SEVERITY_CHOICES,default='MINOR')
    incident_location=models.CharField(max_length=250,blank=True)
    work_area=models.CharField(max_length=200,blank=True)
    job_role=models.CharField(max_length=200,blank=True)
    incident_description=models.TextField()
    symptoms=models.TextField(blank=True)
    immediate_action=models.TextField(blank=True)
    treatment_provided=models.TextField(blank=True)
    medical_professional=models.ForeignKey(
        'MedicalProfessional',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='health_incidents'
    )
    medical_facility=models.ForeignKey(
        'MedicalFacility',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='health_incidents'
    )
    occupational_disease=models.ForeignKey(
        'EmployeeOccupationalDisease',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='health_incidents'
    )
    exposure=models.ForeignKey(
        'EmployeeExposure',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='health_incidents'
    )
    hospitalization_required=models.BooleanField(default=False)
    hospitalization_details=models.TextField(blank=True)
    work_restriction_required=models.BooleanField(default=False)
    work_restriction_details=models.TextField(blank=True)
    follow_up_required=models.BooleanField(default=False)
    follow_up_date=models.DateField(null=True,blank=True)
    investigation_required=models.BooleanField(default=False)
    investigation_findings=models.TextField(blank=True)
    corrective_actions=models.TextField(blank=True)
    attachment=models.FileField(
        upload_to='occupational_health/health_incidents/',
        null=True,
        blank=True
    )
    status=models.CharField(max_length=30,choices=STATUS_CHOICES,default='REPORTED')
    remarks=models.TextField(blank=True)
    created_by=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_health_incidents'
    )
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        ordering=['-incident_date','-id']
        verbose_name='Health Incident'
        verbose_name_plural='Health Incidents'

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.employee_health_profile_id and not self.employee_health_profile.is_active:
            raise ValidationError({
                'employee_health_profile':
                'The selected Employee Health Profile is inactive.'
            })

        if self.follow_up_required and not self.follow_up_date:
            raise ValidationError({
                'follow_up_date':
                'Follow-up Date is required when Follow-up is required.'
            })

        if not self.follow_up_required and self.follow_up_date:
            raise ValidationError({
                'follow_up_date':
                'Follow-up Date should be empty when Follow-up is not required.'
            })

        if self.follow_up_date and self.incident_date:
            if self.follow_up_date < self.incident_date:
                raise ValidationError({
                    'follow_up_date':
                    'Follow-up Date cannot be before the Incident Date.'
                })

        if self.hospitalization_required and not self.hospitalization_details.strip():
            raise ValidationError({
                'hospitalization_details':
                'Hospitalization details are required when hospitalization is selected.'
            })

        if not self.hospitalization_required and self.hospitalization_details:
            raise ValidationError({
                'hospitalization_details':
                'Hospitalization details should be empty when hospitalization is not required.'
            })

        if self.work_restriction_required and not self.work_restriction_details.strip():
            raise ValidationError({
                'work_restriction_details':
                'Work restriction details are required when work restriction is selected.'
            })

        if not self.work_restriction_required and self.work_restriction_details:
            raise ValidationError({
                'work_restriction_details':
                'Work restriction details should be empty when work restriction is not required.'
            })

        if self.investigation_required is False:
            if self.investigation_findings or self.corrective_actions:
                raise ValidationError({
                    'investigation_findings':
                    'Investigation details should be empty when investigation is not required.'
                })

        if self.occupational_disease_id:
            if self.occupational_disease.employee_health_profile_id != self.employee_health_profile_id:
                raise ValidationError({
                    'occupational_disease':
                    'Selected Occupational Disease must belong to the same employee.'
                })

        if self.exposure_id:
            if self.exposure.employee_health_profile_id != self.employee_health_profile_id:
                raise ValidationError({
                    'exposure':
                    'Selected Exposure must belong to the same employee.'
                })

    def __str__(self):
        employee=self.employee_health_profile.employee
        employee_name=employee.get_full_name() or employee.username
        return f'{employee_name} - {self.get_incident_type_display()} - {self.incident_date}'




class ReturnToWork(models.Model):
    RTW_REASON_CHOICES=[
        ('ILLNESS','Illness'),
        ('INJURY','Injury'),
        ('HOSPITALIZATION','Hospitalization'),
        ('OCCUPATIONAL_DISEASE','Occupational Disease'),
        ('MEDICAL_LEAVE','Medical Leave'),
        ('WORK_RESTRICTION','Work Restriction'),
        ('OTHER','Other'),
    ]
    RTW_STATUS_CHOICES=[
        ('PENDING','Pending'),
        ('MEDICAL_ASSESSMENT','Medical Assessment'),
        ('APPROVED','Approved'),
        ('APPROVED_WITH_RESTRICTIONS','Approved With Restrictions'),
        ('NOT_APPROVED','Not Approved'),
        ('COMPLETED','Completed'),
        ('CANCELLED','Cancelled'),
    ]
    employee_health_profile=models.ForeignKey(
        'EmployeeHealthProfile',
        on_delete=models.CASCADE,
        related_name='return_to_work_records'
    )
    absence_start_date=models.DateField()
    absence_end_date=models.DateField()
    expected_return_date=models.DateField()
    actual_return_date=models.DateField(null=True,blank=True)
    return_reason=models.CharField(
        max_length=30,
        choices=RTW_REASON_CHOICES
    )
    reason_details=models.TextField(blank=True)
    medical_examination=models.ForeignKey(
        'MedicalExamination',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='return_to_work_records'
    )
    fitness_assessment=models.ForeignKey(
        'FitnessToWork',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='return_to_work_records'
    )
    health_incident=models.ForeignKey(
        'HealthIncident',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='return_to_work_records'
    )
    occupational_disease=models.ForeignKey(
        'EmployeeOccupationalDisease',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='return_to_work_records'
    )
    medical_professional=models.ForeignKey(
        'MedicalProfessional',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='return_to_work_records'
    )
    medical_facility=models.ForeignKey(
        'MedicalFacility',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='return_to_work_records'
    )
    fitness_status=models.CharField(
        max_length=30,
        choices=FitnessToWork.FITNESS_STATUS_CHOICES,
        blank=True
    )
    work_restrictions=models.ManyToManyField(
        'Restriction',
        blank=True,
        related_name='return_to_work_records'
    )
    restriction_details=models.TextField(blank=True)
    temporary_restriction_until=models.DateField(
        null=True,
        blank=True
    )
    job_role=models.CharField(
        max_length=200,
        blank=True
    )
    work_area=models.CharField(
        max_length=200,
        blank=True
    )
    supervisor_comments=models.TextField(blank=True)
    employee_comments=models.TextField(blank=True)
    medical_recommendations=models.TextField(blank=True)
    follow_up_required=models.BooleanField(default=False)
    follow_up_date=models.DateField(null=True,blank=True)
    status=models.CharField(
        max_length=35,
        choices=RTW_STATUS_CHOICES,
        default='PENDING'
    )
    remarks=models.TextField(blank=True)
    attachment=models.FileField(
        upload_to='occupational_health/return_to_work/',
        null=True,
        blank=True
    )
    created_by=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_return_to_work_records'
    )
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        ordering=['-expected_return_date','-id']
        verbose_name='Return to Work'
        verbose_name_plural='Return to Work Records'

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.employee_health_profile_id:
            if not self.employee_health_profile.is_active:
                raise ValidationError({
                    'employee_health_profile':
                    'The selected Employee Health Profile is inactive.'
                })

        if self.absence_end_date and self.absence_start_date:
            if self.absence_end_date < self.absence_start_date:
                raise ValidationError({
                    'absence_end_date':
                    'Absence End Date cannot be before Absence Start Date.'
                })

        if self.expected_return_date and self.absence_start_date:
            if self.expected_return_date < self.absence_start_date:
                raise ValidationError({
                    'expected_return_date':
                    'Expected Return Date cannot be before Absence Start Date.'
                })

        if self.actual_return_date and self.absence_start_date:
            if self.actual_return_date < self.absence_start_date:
                raise ValidationError({
                    'actual_return_date':
                    'Actual Return Date cannot be before Absence Start Date.'
                })

        if self.follow_up_required and not self.follow_up_date:
            raise ValidationError({
                'follow_up_date':
                'Follow-up Date is required when Follow-up is required.'
            })

        if not self.follow_up_required and self.follow_up_date:
            raise ValidationError({
                'follow_up_date':
                'Follow-up Date should be empty when Follow-up is not required.'
            })

        if self.follow_up_date and self.expected_return_date:
            if self.follow_up_date < self.expected_return_date:
                raise ValidationError({
                    'follow_up_date':
                    'Follow-up Date cannot be before the Expected Return Date.'
                })

        if self.temporary_restriction_until and self.actual_return_date:
            if self.temporary_restriction_until < self.actual_return_date:
                raise ValidationError({
                    'temporary_restriction_until':
                    'Restriction end date cannot be before the Actual Return Date.'
                })

        if self.medical_examination_id and self.employee_health_profile_id:
            if self.medical_examination.employee_health_profile_id != self.employee_health_profile_id:
                raise ValidationError({
                    'medical_examination':
                    'Medical Examination must belong to the selected employee.'
                })

        if self.fitness_assessment_id and self.employee_health_profile_id:
            if self.fitness_assessment.employee_health_profile_id != self.employee_health_profile_id:
                raise ValidationError({
                    'fitness_assessment':
                    'Fitness Assessment must belong to the selected employee.'
                })

        if self.health_incident_id and self.employee_health_profile_id:
            if self.health_incident.employee_health_profile_id != self.employee_health_profile_id:
                raise ValidationError({
                    'health_incident':
                    'Health Incident must belong to the selected employee.'
                })

        if self.occupational_disease_id and self.employee_health_profile_id:
            if self.occupational_disease.employee_health_profile_id != self.employee_health_profile_id:
                raise ValidationError({
                    'occupational_disease':
                    'Occupational Disease must belong to the selected employee.'
                })

        if self.status == 'COMPLETED' and not self.actual_return_date:
            raise ValidationError({
                'actual_return_date':
                'Actual Return Date is required when the Return to Work record is completed.'
            })

    def __str__(self):
        employee=self.employee_health_profile.employee
        employee_name=employee.get_full_name() or employee.username
        return f'{employee_name} - Return to Work - {self.expected_return_date}'





class MedicalRecord(models.Model):
    RECORD_TYPE_CHOICES=[
        ('MEDICAL_EXAMINATION','Medical Examination'),
        ('MEDICAL_TEST','Medical Test'),
        ('FITNESS_CERTIFICATE','Fitness Certificate'),
        ('VACCINATION','Vaccination'),
        ('OCCUPATIONAL_DISEASE','Occupational Disease'),
        ('HEALTH_INCIDENT','Health Incident'),
        ('RETURN_TO_WORK','Return to Work'),
        ('PRESCRIPTION','Prescription'),
        ('TREATMENT','Treatment Record'),
        ('REFERRAL','Referral'),
        ('OTHER','Other'),
    ]

    RECORD_STATUS_CHOICES=[
        ('ACTIVE','Active'),
        ('ARCHIVED','Archived'),
        ('CANCELLED','Cancelled'),
    ]

    employee_health_profile=models.ForeignKey(
        'EmployeeHealthProfile',
        on_delete=models.CASCADE,
        related_name='medical_records'
    )

    record_title=models.CharField(max_length=255)

    record_type=models.CharField(
        max_length=30,
        choices=RECORD_TYPE_CHOICES
    )

    record_date=models.DateField()

    medical_examination=models.ForeignKey(
        'MedicalExamination',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    medical_test_result=models.ForeignKey(
        'MedicalTestResult',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    fitness_assessment=models.ForeignKey(
        'FitnessToWork',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    vaccination=models.ForeignKey(
        'EmployeeVaccination',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    occupational_disease=models.ForeignKey(
        'EmployeeOccupationalDisease',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    health_incident=models.ForeignKey(
        'HealthIncident',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    return_to_work=models.ForeignKey(
        'ReturnToWork',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    medical_professional=models.ForeignKey(
        'MedicalProfessional',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    medical_facility=models.ForeignKey(
        'MedicalFacility',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    document=models.FileField(
        upload_to='occupational_health/medical_records/'
    )

    document_number=models.CharField(
        max_length=100,
        blank=True
    )

    description=models.TextField(blank=True)

    confidential=models.BooleanField(default=True)

    record_status=models.CharField(
        max_length=20,
        choices=RECORD_STATUS_CHOICES,
        default='ACTIVE'
    )

    expiry_date=models.DateField(
        null=True,
        blank=True
    )

    remarks=models.TextField(blank=True)

    created_by=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_medical_records'
    )

    created_at=models.DateTimeField(auto_now_add=True)

    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        ordering=['-record_date','-id']
        verbose_name='Medical Record'
        verbose_name_plural='Medical Records'

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.employee_health_profile_id:
            if not self.employee_health_profile.is_active:
                raise ValidationError({
                    'employee_health_profile':
                    'The selected Employee Health Profile is inactive.'
                })

        if self.expiry_date and self.record_date:
            if self.expiry_date < self.record_date:
                raise ValidationError({
                    'expiry_date':
                    'Expiry Date cannot be before the Record Date.'
                })

        if not self.employee_health_profile_id:
            return

        if self.medical_examination:
            if (
                self.medical_examination.employee_health_profile_id
                != self.employee_health_profile_id
            ):
                raise ValidationError({
                    'medical_examination':
                    'The selected Medical Examination belongs to a different employee.'
                })

        if self.medical_test_result:
            if self.medical_test_result.medical_examination_id:
                test_employee_id = (
                    self.medical_test_result
                    .medical_examination
                    .employee_health_profile_id
                )

                if test_employee_id != self.employee_health_profile_id:
                    raise ValidationError({
                        'medical_test_result':
                        'The selected Medical Test Result belongs to a different employee.'
                    })

        if self.fitness_assessment:
            if (
                self.fitness_assessment.employee_health_profile_id
                != self.employee_health_profile_id
            ):
                raise ValidationError({
                    'fitness_assessment':
                    'The selected Fitness Assessment belongs to a different employee.'
                })

        if self.vaccination:
            if (
                self.vaccination.employee_health_profile_id
                != self.employee_health_profile_id
            ):
                raise ValidationError({
                    'vaccination':
                    'The selected Vaccination belongs to a different employee.'
                })

        if self.occupational_disease:
            if (
                self.occupational_disease.employee_health_profile_id
                != self.employee_health_profile_id
            ):
                raise ValidationError({
                    'occupational_disease':
                    'The selected Occupational Disease belongs to a different employee.'
                })

        if self.health_incident:
            if (
                self.health_incident.employee_health_profile_id
                != self.employee_health_profile_id
            ):
                raise ValidationError({
                    'health_incident':
                    'The selected Health Incident belongs to a different employee.'
                })

        if self.return_to_work:
            if (
                self.return_to_work.employee_health_profile_id
                != self.employee_health_profile_id
            ):
                raise ValidationError({
                    'return_to_work':
                    'The selected Return to Work record belongs to a different employee.'
                })
    
    def __str__(self):
        employee=self.employee_health_profile.employee
        employee_name=employee.get_full_name() or employee.username
        return f'{employee_name} - {self.record_title}'




class HealthCamp(models.Model):
    CAMP_TYPE_CHOICES=[
        ('GENERAL_HEALTH','General Health'),
        ('EYE_CHECKUP','Eye Check-up'),
        ('DENTAL_CHECKUP','Dental Check-up'),
        ('HEARING_CHECKUP','Hearing Check-up'),
        ('RESPIRATORY','Respiratory Health'),
        ('CARDIAC','Cardiac Health'),
        ('DIABETES','Diabetes Screening'),
        ('WOMEN_HEALTH','Women Health'),
        ('VACCINATION','Vaccination Camp'),
        ('OCCUPATIONAL_HEALTH','Occupational Health'),
        ('SPECIALIZED','Specialized Health Camp'),
        ('OTHER','Other'),
    ]

    STATUS_CHOICES=[
        ('PLANNED','Planned'),
        ('SCHEDULED','Scheduled'),
        ('IN_PROGRESS','In Progress'),
        ('COMPLETED','Completed'),
        ('CANCELLED','Cancelled'),
    ]

    CAMP_MODE_CHOICES=[
        ('ON_SITE','On Site'),
        ('OFF_SITE','Off Site'),
        ('MOBILE','Mobile Camp'),
    ]

    camp_code=models.CharField(
        max_length=50,
        unique=True,
        blank=True
    )

    camp_name=models.CharField(
        max_length=255
    )

    camp_type=models.CharField(
        max_length=30,
        choices=CAMP_TYPE_CHOICES
    )

    camp_mode=models.CharField(
        max_length=20,
        choices=CAMP_MODE_CHOICES,
        default='ON_SITE'
    )

    plant=models.ForeignKey(
        'organizations.Plant',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='occupational_health_camps'
    )

    location=models.CharField(
        max_length=255,
        blank=True
    )

    camp_date=models.DateField()

    start_time=models.TimeField(
        null=True,
        blank=True
    )

    end_time=models.TimeField(
        null=True,
        blank=True
    )

    organizer=models.CharField(
        max_length=255,
        blank=True
    )

    medical_facility=models.ForeignKey(
        'MedicalFacility',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='health_camps'
    )

    lead_medical_professional=models.ForeignKey(
        'MedicalProfessional',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='led_health_camps'
    )

    objectives=models.TextField(
        blank=True
    )

    services_provided=models.TextField(
        blank=True
    )

    target_employee_count=models.PositiveIntegerField(
        default=0
    )

    registered_employee_count=models.PositiveIntegerField(
        default=0
    )

    attended_employee_count=models.PositiveIntegerField(
        default=0
    )

    findings_count=models.PositiveIntegerField(
        default=0
    )

    referral_count=models.PositiveIntegerField(
        default=0
    )

    follow_up_required_count=models.PositiveIntegerField(
        default=0
    )

    summary=models.TextField(
        blank=True
    )

    remarks=models.TextField(
        blank=True
    )

    status=models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PLANNED'
    )

    is_active=models.BooleanField(
        default=True
    )

    created_by=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_health_camps'
    )

    created_at=models.DateTimeField(
        auto_now_add=True
    )

    updated_at=models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering=['-camp_date','-id']
        verbose_name='Health Camp'
        verbose_name_plural='Health Camps'

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError({
                    'end_time':
                    'End time must be later than start time.'
                })

        if self.attended_employee_count > self.registered_employee_count:
            raise ValidationError({
                'attended_employee_count':
                'Attended employees cannot exceed registered employees.'
            })

        if self.registered_employee_count > self.target_employee_count and self.target_employee_count:
            raise ValidationError({
                'registered_employee_count':
                'Registered employees cannot exceed the target employee count.'
            })

        if self.findings_count > self.attended_employee_count:
            raise ValidationError({
                'findings_count':
                'Findings count cannot exceed attended employees.'
            })

        if self.referral_count > self.findings_count:
            raise ValidationError({
                'referral_count':
                'Referral count cannot exceed findings count.'
            })

        if self.follow_up_required_count > self.findings_count:
            raise ValidationError({
                'follow_up_required_count':
                'Follow-up count cannot exceed findings count.'
            })

    def save(self,*args,**kwargs):
        if not self.camp_code:
            last_camp=HealthCamp.objects.order_by('-id').first()

            if last_camp and last_camp.camp_code:
                try:
                    last_number=int(
                        last_camp.camp_code.split('-')[-1]
                    )
                except (ValueError,IndexError):
                    last_number=0
            else:
                last_number=0

            self.camp_code=f'HC-{timezone.now().year}-{last_number+1:04d}'

        super().save(*args,**kwargs)

    def __str__(self):
        return f'{self.camp_code} - {self.camp_name}'




class HealthCampParticipation(models.Model):
    ATTENDANCE_STATUS_CHOICES=[
        ('REGISTERED','Registered'),
        ('ATTENDED','Attended'),
        ('NOT_ATTENDED','Not Attended'),
        ('CANCELLED','Cancelled'),
    ]
    SCREENING_STATUS_CHOICES=[
        ('NOT_SCREENED','Not Screened'),
        ('NORMAL','Normal'),
        ('ABNORMAL','Abnormal'),
        ('REFERRED','Referred'),
        ('FOLLOW_UP_REQUIRED','Follow-up Required'),
    ]

    health_camp=models.ForeignKey(
        'HealthCamp',
        on_delete=models.CASCADE,
        related_name='participations'
    )
    employee_health_profile=models.ForeignKey(
        'EmployeeHealthProfile',
        on_delete=models.CASCADE,
        related_name='health_camp_participations'
    )
    registration_date=models.DateField()
    attendance_status=models.CharField(
        max_length=20,
        choices=ATTENDANCE_STATUS_CHOICES,
        default='REGISTERED'
    )
    attendance_time=models.TimeField(
        null=True,
        blank=True
    )
    screening_status=models.CharField(
        max_length=30,
        choices=SCREENING_STATUS_CHOICES,
        default='NOT_SCREENED'
    )
    screening_findings=models.TextField(
        blank=True
    )
    abnormal_findings=models.TextField(
        blank=True
    )
    services_received=models.TextField(
        blank=True
    )
    medical_advice=models.TextField(
        blank=True
    )
    referral_required=models.BooleanField(
        default=False
    )
    referral_details=models.TextField(
        blank=True
    )
    follow_up_required=models.BooleanField(
        default=False
    )
    follow_up_date=models.DateField(
        null=True,
        blank=True
    )
    follow_up_notes=models.TextField(
        blank=True
    )
    medical_professional=models.ForeignKey(
        'MedicalProfessional',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='health_camp_participations'
    )
    medical_record=models.ForeignKey(
        'MedicalRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='health_camp_participations'
    )
    remarks=models.TextField(
        blank=True
    )
    created_by=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_health_camp_participations'
    )
    created_at=models.DateTimeField(
        auto_now_add=True
    )
    updated_at=models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering=['-registration_date','-id']
        verbose_name='Health Camp Participation'
        verbose_name_plural='Health Camp Participations'
        constraints=[
            models.UniqueConstraint(
                fields=['health_camp','employee_health_profile'],
                name='unique_health_camp_employee'
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.employee_health_profile_id:
            if not self.employee_health_profile.is_active:
                raise ValidationError({
                    'employee_health_profile':
                    'The selected Employee Health Profile is inactive.'
                })

        if self.health_camp_id and self.registration_date:
            if self.registration_date > self.health_camp.camp_date:
                raise ValidationError({
                    'registration_date':
                    'Registration Date cannot be after the Camp Date.'
                })

        if self.attendance_status == 'ATTENDED' and not self.attendance_time:
            raise ValidationError({
                'attendance_time':
                'Attendance Time is required when attendance is marked as Attended.'
            })

        if self.screening_status == 'ABNORMAL' and not self.abnormal_findings.strip():
            raise ValidationError({
                'abnormal_findings':
                'Abnormal Findings are required when Screening Status is Abnormal.'
            })

        if self.screening_status == 'REFERRED' and not self.referral_required:
            raise ValidationError({
                'referral_required':
                'Referral Required must be selected when Screening Status is Referred.'
            })

        if self.referral_required and not self.referral_details.strip():
            raise ValidationError({
                'referral_details':
                'Referral Details are required when referral is required.'
            })

        if not self.referral_required and self.referral_details:
            raise ValidationError({
                'referral_details':
                'Referral Details should be empty when referral is not required.'
            })

        if self.follow_up_required and not self.follow_up_date:
            raise ValidationError({
                'follow_up_date':
                'Follow-up Date is required when follow-up is required.'
            })

        if not self.follow_up_required and self.follow_up_date:
            raise ValidationError({
                'follow_up_date':
                'Follow-up Date should be empty when follow-up is not required.'
            })

        if self.follow_up_date and self.health_camp_id:
            if self.follow_up_date < self.health_camp.camp_date:
                raise ValidationError({
                    'follow_up_date':
                    'Follow-up Date cannot be before the Camp Date.'
                })

    def __str__(self):
        employee=self.employee_health_profile.employee
        employee_name=employee.get_full_name() or employee.username
        return f'{employee_name} - {self.health_camp.camp_name}'