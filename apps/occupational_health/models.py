from django.db import models
from django.conf import settings


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