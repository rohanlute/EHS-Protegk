from django.db import models


class HazardCategoryMaster(models.Model):
    category_name = models.CharField(max_length=100)
    description = models.TextField(blank=True,null=True)
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_hazard_category_master"
        ordering = ["category_name"]

    def __str__(self):
        return self.category_name


class HazardMaster(models.Model):
    hazard_category = models.ForeignKey(
        HazardCategoryMaster,
        on_delete=models.PROTECT,
        related_name="hazards"
    )
    hazard = models.CharField(max_length=150)
    description = models.TextField(blank=True,null=True)
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_hazard_master"
        ordering = ["hazard_category","hazard"]

    def __str__(self):
        return self.hazard



class ExposureTypeMaster(models.Model):
    exposure_type = models.CharField(max_length=100)
    description = models.TextField(blank=True,null=True)
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_exposure_type_master"
        ordering = ["exposure_type"]

    def __str__(self):
        return self.exposure_type


# =============================================
# ExposureGroupMaster - Stores Similar Exposure Groups (SEG) used for exposure assessment.
# =============================================
class ExposureGroupMaster(models.Model):
    exposure_group = models.CharField(max_length=150)
    description = models.TextField(blank=True,null=True)
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_exposure_group_master"
        ordering = ["exposure_group"]

    def __str__(self):
        return self.exposure_group



# =============================================
# MonitoringTypeMaster - Stores Industrial Hygiene monitoring types.
# =============================================
class MonitoringTypeMaster(models.Model):
    monitoring_type = models.CharField(max_length=100)
    description = models.TextField(blank=True,null=True)
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_monitoring_type_master"
        ordering = ["monitoring_type"]

    def __str__(self):
        return self.monitoring_type




# =============================================
# MonitoringParameterMaster - Stores parameters measured during Industrial Hygiene monitoring.
# =============================================
class MonitoringParameterMaster(models.Model):
    parameter_name = models.CharField(max_length=150)
    description = models.TextField(blank=True,null=True)
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_monitoring_parameter_master"
        ordering = ["parameter_name"]

    def __str__(self):
        return self.parameter_name



# =============================================
# UnitMaster - Stores measurement units used in Industrial Hygiene monitoring.
# =============================================
class UnitMaster(models.Model):
    unit_name = models.CharField(max_length=100)
    unit_symbol = models.CharField(max_length=50)
    description = models.TextField(blank=True,null=True)
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_unit_master"
        ordering = ["unit_name"]

    def __str__(self):
        return f"{self.unit_name} ({self.unit_symbol})"




# =============================================
# ExposureLimitMaster - Stores occupational exposure limits used for Industrial Hygiene compliance assessment.
# =============================================
class ExposureLimitMaster(models.Model):
    hazard = models.ForeignKey(
        HazardMaster,
        on_delete=models.PROTECT,
        related_name="exposure_limits"
    )
    monitoring_parameter = models.ForeignKey(
        MonitoringParameterMaster,
        on_delete=models.PROTECT,
        related_name="exposure_limits"
    )
    unit = models.ForeignKey(
        UnitMaster,
        on_delete=models.PROTECT,
        related_name="exposure_limits"
    )
    exposure_limit_type = models.CharField(max_length=100)
    limit_value = models.DecimalField(max_digits=12,decimal_places=4)
    applicable_standard = models.CharField(max_length=200)
    source_reference = models.CharField(max_length=300,blank=True,null=True)
    effective_from = models.DateField(blank=True,null=True)
    effective_to = models.DateField(blank=True,null=True)
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_exposure_limit_master"
        ordering = ["hazard__hazard","monitoring_parameter__parameter_name"]

    def __str__(self):
        return f"{self.hazard} - {self.monitoring_parameter} - {self.limit_value} {self.unit}"



# =============================================
# InstrumentMaster - Stores Industrial Hygiene monitoring instruments and equipment.
# =============================================
class InstrumentMaster(models.Model):
    instrument_name = models.CharField(max_length=150)
    instrument_code = models.CharField(max_length=100,unique=True)
    instrument_type = models.CharField(max_length=100)
    manufacturer = models.CharField(max_length=150,blank=True,null=True)
    model_number = models.CharField(max_length=100,blank=True,null=True)
    serial_number = models.CharField(max_length=100,blank=True,null=True)
    measurement_parameter = models.ForeignKey(
        MonitoringParameterMaster,
        on_delete=models.PROTECT,
        related_name="instruments",
        blank=True,
        null=True
    )
    calibration_frequency = models.CharField(max_length=100,blank=True,null=True)
    last_calibration_date = models.DateField(blank=True,null=True)
    next_calibration_date = models.DateField(blank=True,null=True)
    description = models.TextField(blank=True,null=True)
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_instrument_master"
        ordering = ["instrument_name"]

    def __str__(self):
        return f"{self.instrument_name} ({self.instrument_code})"



# =============================================
# LaboratoryMaster - Stores laboratories used for Industrial Hygiene sample testing and analysis.
# =============================================
class LaboratoryMaster(models.Model):
    laboratory_name = models.CharField(max_length=200)
    laboratory_code = models.CharField(max_length=100,unique=True)
    accreditation = models.CharField(max_length=200,blank=True,null=True)
    contact_person = models.CharField(max_length=150,blank=True,null=True)
    contact_number = models.CharField(max_length=50,blank=True,null=True)
    email = models.EmailField(blank=True,null=True)
    address = models.TextField(blank=True,null=True)
    description = models.TextField(blank=True,null=True)
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_laboratory_master"
        ordering = ["laboratory_name"]

    def __str__(self):
        return f"{self.laboratory_name} ({self.laboratory_code})"







# =============================================
# IHProgramMaster - Stores Industrial Hygiene program details and management information.
# =============================================
class IHProgramMaster(models.Model):
    program_name = models.CharField(max_length=200)
    program_code = models.CharField(max_length=100,unique=True)
    plant = models.ForeignKey(
        "organizations.Plant",
        on_delete=models.PROTECT,
        related_name="industrial_hygiene_programs"
    )
    description = models.TextField(blank=True,null=True)
    objectives = models.TextField(blank=True,null=True)
    scope = models.TextField(blank=True,null=True)
    responsible_person = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="industrial_hygiene_programs_responsible",
        blank=True,
        null=True
    )
    start_date = models.DateField(blank=True,null=True)
    end_date = models.DateField(blank=True,null=True)
    review_frequency = models.CharField(max_length=100,blank=True,null=True)
    last_review_date = models.DateField(blank=True,null=True)
    next_review_date = models.DateField(blank=True,null=True)
    status = models.CharField(
        max_length=30,
        choices=[
            ("DRAFT","Draft"),
            ("ACTIVE","Active"),
            ("UNDER_REVIEW","Under Review"),
            ("CLOSED","Closed"),
        ],
        default="DRAFT"
    )
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_program_master"
        ordering = ["program_name"]

    def __str__(self):
        return f"{self.program_name} ({self.program_code})"





# =============================================
# MonitoringPlan - Defines planned Industrial Hygiene monitoring activities under an IH program.
# =============================================
class MonitoringPlan(models.Model):
    plan_name = models.CharField(max_length=200)
    plan_code = models.CharField(max_length=100,unique=True)
    ih_program = models.ForeignKey(
        IHProgramMaster,
        on_delete=models.PROTECT,
        related_name="monitoring_plans"
    )
    plant = models.ForeignKey(
        "organizations.Plant",
        on_delete=models.PROTECT,
        related_name="industrial_hygiene_monitoring_plans"
    )
    hazard = models.ForeignKey(
        HazardMaster,
        on_delete=models.PROTECT,
        related_name="monitoring_plans"
    )
    exposure_type = models.ForeignKey(
        ExposureTypeMaster,
        on_delete=models.PROTECT,
        related_name="monitoring_plans"
    )
    exposure_group = models.ForeignKey(
        ExposureGroupMaster,
        on_delete=models.PROTECT,
        related_name="monitoring_plans",
        blank=True,
        null=True
    )
    monitoring_type = models.ForeignKey(
        MonitoringTypeMaster,
        on_delete=models.PROTECT,
        related_name="monitoring_plans"
    )
    monitoring_parameter = models.ForeignKey(
        MonitoringParameterMaster,
        on_delete=models.PROTECT,
        related_name="monitoring_plans"
    )
    unit = models.ForeignKey(
        UnitMaster,
        on_delete=models.PROTECT,
        related_name="monitoring_plans"
    )
    exposure_limit = models.ForeignKey(
        ExposureLimitMaster,
        on_delete=models.PROTECT,
        related_name="monitoring_plans",
        blank=True,
        null=True
    )
    monitoring_frequency = models.CharField(max_length=100)
    planned_start_date = models.DateField(blank=True,null=True)
    planned_end_date = models.DateField(blank=True,null=True)
    sample_count = models.PositiveIntegerField(default=1)
    area_or_location = models.CharField(max_length=200,blank=True,null=True)
    department = models.CharField(max_length=150,blank=True,null=True)
    responsible_person = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="industrial_hygiene_monitoring_plans_responsible",
        blank=True,
        null=True
    )
    remarks = models.TextField(blank=True,null=True)
    status = models.CharField(
        max_length=30,
        choices=[
            ("DRAFT","Draft"),
            ("ACTIVE","Active"),
            ("COMPLETED","Completed"),
            ("CLOSED","Closed"),
        ],
        default="DRAFT"
    )
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_monitoring_plan"
        ordering = ["plan_name"]

    def __str__(self):
        return f"{self.plan_name} ({self.plan_code})"





# =============================================
# MonitoringSchedule - Stores scheduled Industrial Hygiene monitoring activities.
# =============================================
class MonitoringSchedule(models.Model):
    STATUS_CHOICES = [
        ("SCHEDULED","Scheduled"),
        ("IN_PROGRESS","In Progress"),
        ("COMPLETED","Completed"),
        ("OVERDUE","Overdue"),
        ("CANCELLED","Cancelled"),
    ]

    schedule_name = models.CharField(max_length=200)
    schedule_code = models.CharField(max_length=100,unique=True)
    monitoring_plan = models.ForeignKey(
        MonitoringPlan,
        on_delete=models.PROTECT,
        related_name="monitoring_schedules"
    )
    planned_date = models.DateField()
    scheduled_start_date = models.DateField(blank=True,null=True)
    scheduled_end_date = models.DateField(blank=True,null=True)
    frequency = models.CharField(max_length=100,blank=True,null=True)
    sample_count = models.PositiveIntegerField(default=1)
    responsible_person = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="industrial_hygiene_monitoring_schedules",
        blank=True,
        null=True
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="industrial_hygiene_monitoring_schedule_assignments",
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="SCHEDULED"
    )
    remarks = models.TextField(blank=True,null=True)
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_monitoring_schedule"
        ordering = ["planned_date","schedule_name"]

    def __str__(self):
        return f"{self.schedule_name} ({self.schedule_code})"




# =============================================
# SamplingManagement - Stores manual Industrial Hygiene sample collection details.
# =============================================
class SamplingManagement(models.Model):
    STATUS_CHOICES = [
        ("PLANNED","Planned"),
        ("SAMPLED","Sampled"),
        ("SENT_TO_LAB","Sent to Lab"),
        ("RESULT_RECEIVED","Result Received"),
        ("CANCELLED","Cancelled"),
    ]
    sampling_code = models.CharField(max_length=100,unique=True)
    monitoring_schedule = models.ForeignKey(
        MonitoringSchedule,
        on_delete=models.PROTECT,
        related_name="sampling_records"
    )
    sample_number = models.CharField(max_length=100)
    sampling_date = models.DateField()
    sampling_start_time = models.TimeField(blank=True,null=True)
    sampling_end_time = models.TimeField(blank=True,null=True)
    hazard = models.ForeignKey(
        HazardMaster,
        on_delete=models.PROTECT,
        related_name="sampling_records"
    )
    exposure_type = models.ForeignKey(
        ExposureTypeMaster,
        on_delete=models.PROTECT,
        related_name="sampling_records",
        blank=True,
        null=True
    )
    exposure_group = models.ForeignKey(
        ExposureGroupMaster,
        on_delete=models.PROTECT,
        related_name="sampling_records",
        blank=True,
        null=True
    )
    area_or_location = models.CharField(max_length=200,blank=True,null=True)
    department = models.CharField(max_length=150,blank=True,null=True)
    monitoring_parameter = models.ForeignKey(
        MonitoringParameterMaster,
        on_delete=models.PROTECT,
        related_name="sampling_records"
    )
    unit = models.ForeignKey(
        UnitMaster,
        on_delete=models.PROTECT,
        related_name="sampling_records"
    )
    instrument = models.ForeignKey(
        InstrumentMaster,
        on_delete=models.PROTECT,
        related_name="sampling_records",
        blank=True,
        null=True
    )
    laboratory = models.ForeignKey(
        LaboratoryMaster,
        on_delete=models.PROTECT,
        related_name="sampling_records",
        blank=True,
        null=True
    )
    sample_type = models.CharField(max_length=100,blank=True,null=True)
    sample_quantity = models.DecimalField(max_digits=12,decimal_places=4,blank=True,null=True)
    sampling_method = models.CharField(max_length=200,blank=True,null=True)
    collected_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="industrial_hygiene_samples_collected",
        blank=True,
        null=True
    )
    sent_to_lab_date = models.DateField(blank=True,null=True)
    laboratory_reference = models.CharField(max_length=150,blank=True,null=True)
    status = models.CharField(max_length=30,choices=STATUS_CHOICES,default="PLANNED")
    remarks = models.TextField(blank=True,null=True)
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_sampling_management"
        ordering = ["-sampling_date","sampling_code"]

    def __str__(self):
        return f"{self.sampling_code} - {self.sample_number}"





# =============================================
# MeasurementEntry - Stores manual Industrial Hygiene measurement results against collected samples.
# =============================================
class MeasurementEntry(models.Model):
    STATUS_CHOICES = [
        ("DRAFT","Draft"),
        ("ENTERED","Entered"),
        ("VERIFIED","Verified"),
        ("CANCELLED","Cancelled"),
    ]
    sampling = models.ForeignKey(
        SamplingManagement,
        on_delete=models.PROTECT,
        related_name="measurement_entries"
    )
    measurement_code = models.CharField(max_length=100,unique=True)
    measurement_date = models.DateField()
    monitoring_parameter = models.ForeignKey(
        MonitoringParameterMaster,
        on_delete=models.PROTECT,
        related_name="measurement_entries"
    )
    unit = models.ForeignKey(
        UnitMaster,
        on_delete=models.PROTECT,
        related_name="measurement_entries"
    )
    measured_value = models.DecimalField(max_digits=15,decimal_places=6)
    detection_limit = models.DecimalField(max_digits=15,decimal_places=6,blank=True,null=True)
    result_remarks = models.TextField(blank=True,null=True)
    entered_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="industrial_hygiene_measurements_entered",
        blank=True,
        null=True
    )
    verified_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="industrial_hygiene_measurements_verified",
        blank=True,
        null=True
    )
    verification_date = models.DateField(blank=True,null=True)
    status = models.CharField(max_length=30,choices=STATUS_CHOICES,default="DRAFT")
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_measurement_entry"
        ordering = ["-measurement_date","measurement_code"]

    def __str__(self):
        return f"{self.measurement_code} - {self.sampling.sample_number}"




# =============================================
# LaboratoryResult - Stores laboratory analysis results for Industrial Hygiene samples.
# =============================================
class LaboratoryResult(models.Model):
    STATUS_CHOICES = [
        ("RECEIVED","Received"),
        ("UNDER_REVIEW","Under Review"),
        ("VERIFIED","Verified"),
        ("REJECTED","Rejected"),
    ]
    sampling = models.ForeignKey(
        SamplingManagement,
        on_delete=models.PROTECT,
        related_name="laboratory_results"
    )
    laboratory = models.ForeignKey(
        LaboratoryMaster,
        on_delete=models.PROTECT,
        related_name="laboratory_results"
    )
    measurement = models.ForeignKey(
        MeasurementEntry,
        on_delete=models.PROTECT,
        related_name="laboratory_results",
        blank=True,
        null=True
    )
    result_code = models.CharField(max_length=100,unique=True)
    laboratory_reference = models.CharField(max_length=150,blank=True,null=True)
    result_date = models.DateField()
    monitoring_parameter = models.ForeignKey(
        MonitoringParameterMaster,
        on_delete=models.PROTECT,
        related_name="laboratory_results"
    )
    unit = models.ForeignKey(
        UnitMaster,
        on_delete=models.PROTECT,
        related_name="laboratory_results"
    )
    result_value = models.DecimalField(max_digits=15,decimal_places=6)
    detection_limit = models.DecimalField(max_digits=15,decimal_places=6,blank=True,null=True)
    test_method = models.CharField(max_length=200,blank=True,null=True)
    certificate_number = models.CharField(max_length=150,blank=True,null=True)
    certificate_date = models.DateField(blank=True,null=True)
    remarks = models.TextField(blank=True,null=True)
    received_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="industrial_hygiene_lab_results_received",
        blank=True,
        null=True
    )
    verified_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="industrial_hygiene_lab_results_verified",
        blank=True,
        null=True
    )
    verification_date = models.DateField(blank=True,null=True)
    status = models.CharField(max_length=30,choices=STATUS_CHOICES,default="RECEIVED")
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_laboratory_result"
        ordering = ["-result_date","result_code"]

    def __str__(self):
        return f"{self.result_code} - {self.sampling.sample_number}"




# =============================================
# ExposureAssessment - Stores Industrial Hygiene exposure assessment details and compliance evaluation.
# =============================================
class ExposureAssessment(models.Model):
    STATUS_CHOICES = [
        ("DRAFT","Draft"),
        ("ASSESSED","Assessed"),
        ("UNDER_REVIEW","Under Review"),
        ("APPROVED","Approved"),
        ("CLOSED","Closed"),
    ]
    COMPLIANCE_CHOICES = [
        ("WITHIN_LIMIT","Within Limit"),
        ("EXCEEDS_LIMIT","Exceeds Limit"),
        ("NOT_ASSESSED","Not Assessed"),
    ]
    RISK_LEVEL_CHOICES = [
        ("LOW","Low"),
        ("MEDIUM","Medium"),
        ("HIGH","High"),
        ("CRITICAL","Critical"),
        ("NOT_ASSESSED","Not Assessed"),
    ]
    assessment_code = models.CharField(max_length=100,unique=True)
    sampling = models.ForeignKey(
        SamplingManagement,
        on_delete=models.PROTECT,
        related_name="exposure_assessments"
    )
    measurement = models.ForeignKey(
        MeasurementEntry,
        on_delete=models.PROTECT,
        related_name="exposure_assessments",
        blank=True,
        null=True
    )
    laboratory_result = models.ForeignKey(
        LaboratoryResult,
        on_delete=models.PROTECT,
        related_name="exposure_assessments",
        blank=True,
        null=True
    )
    hazard = models.ForeignKey(
        HazardMaster,
        on_delete=models.PROTECT,
        related_name="exposure_assessments"
    )
    exposure_type = models.ForeignKey(
        ExposureTypeMaster,
        on_delete=models.PROTECT,
        related_name="exposure_assessments",
        blank=True,
        null=True
    )
    exposure_group = models.ForeignKey(
        ExposureGroupMaster,
        on_delete=models.PROTECT,
        related_name="exposure_assessments",
        blank=True,
        null=True
    )
    area_or_location = models.CharField(max_length=200,blank=True,null=True)
    department = models.CharField(max_length=150,blank=True,null=True)
    employee_name = models.CharField(max_length=150,blank=True,null=True)
    monitoring_parameter = models.ForeignKey(
        MonitoringParameterMaster,
        on_delete=models.PROTECT,
        related_name="exposure_assessments"
    )
    unit = models.ForeignKey(
        UnitMaster,
        on_delete=models.PROTECT,
        related_name="exposure_assessments"
    )
    measured_value = models.DecimalField(max_digits=15,decimal_places=6)
    applicable_oel = models.ForeignKey(
        ExposureLimitMaster,
        on_delete=models.PROTECT,
        related_name="exposure_assessments",
        blank=True,
        null=True
    )
    exposure_limit_value = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        blank=True,
        null=True
    )
    compliance_status = models.CharField(
        max_length=30,
        choices=COMPLIANCE_CHOICES,
        default="NOT_ASSESSED"
    )
    risk_level = models.CharField(
        max_length=30,
        choices=RISK_LEVEL_CHOICES,
        default="NOT_ASSESSED"
    )
    existing_controls = models.TextField(blank=True,null=True)
    assessment_remarks = models.TextField(blank=True,null=True)
    assessment_date = models.DateField()
    assessor = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="industrial_hygiene_exposure_assessments",
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="DRAFT"
    )
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ih_exposure_assessment"
        ordering = ["-assessment_date","assessment_code"]

    def __str__(self):
        return f"{self.assessment_code} - {self.hazard}"





# =============================================
# ComplianceRecord - Stores Industrial Hygiene compliance evaluation against applicable exposure limits.
# =============================================
class ComplianceRecord(models.Model):
    STATUS_CHOICES = [
        ("DRAFT","Draft"),
        ("ASSESSED","Assessed"),
        ("NON_COMPLIANT","Non-Compliant"),
        ("COMPLIANT","Compliant"),
        ("UNDER_REVIEW","Under Review"),
        ("CLOSED","Closed"),
    ]
    COMPLIANCE_CHOICES = [
        ("WITHIN_LIMIT","Within Limit"),
        ("EXCEEDS_LIMIT","Exceeds Limit"),
        ("NOT_ASSESSED","Not Assessed"),
    ]
    compliance_code = models.CharField(max_length=100,unique=True)
    exposure_assessment = models.ForeignKey(ExposureAssessment,on_delete=models.PROTECT,related_name="compliance_records")
    sampling = models.ForeignKey(SamplingManagement,on_delete=models.PROTECT,related_name="compliance_records")
    measurement = models.ForeignKey(MeasurementEntry,on_delete=models.PROTECT,related_name="compliance_records",blank=True,null=True)
    laboratory_result = models.ForeignKey(LaboratoryResult,on_delete=models.PROTECT,related_name="compliance_records",blank=True,null=True)
    hazard = models.ForeignKey(HazardMaster,on_delete=models.PROTECT,related_name="compliance_records")
    exposure_group = models.ForeignKey(ExposureGroupMaster,on_delete=models.PROTECT,related_name="compliance_records",blank=True,null=True)
    area_or_location = models.CharField(max_length=200,blank=True,null=True)
    department = models.CharField(max_length=150,blank=True,null=True)
    employee_name = models.CharField(max_length=150,blank=True,null=True)
    monitoring_parameter = models.ForeignKey(MonitoringParameterMaster,on_delete=models.PROTECT,related_name="compliance_records")
    unit = models.ForeignKey(UnitMaster,on_delete=models.PROTECT,related_name="compliance_records")
    measured_value = models.DecimalField(max_digits=15,decimal_places=6)
    applicable_oel = models.ForeignKey(ExposureLimitMaster,on_delete=models.PROTECT,related_name="compliance_records",blank=True,null=True)
    exposure_limit_value = models.DecimalField(max_digits=15,decimal_places=6,blank=True,null=True)
    exceedance_value = models.DecimalField(max_digits=15,decimal_places=6,blank=True,null=True)
    exceedance_percentage = models.DecimalField(max_digits=10,decimal_places=4,blank=True,null=True)
    compliance_status = models.CharField(max_length=30,choices=COMPLIANCE_CHOICES,default="NOT_ASSESSED")
    risk_level = models.CharField(max_length=30,choices=ExposureAssessment.RISK_LEVEL_CHOICES,default="NOT_ASSESSED")
    investigation_required = models.BooleanField(default=False)
    investigation_details = models.TextField(blank=True,null=True)
    remarks = models.TextField(blank=True,null=True)
    assessment_date = models.DateField()
    assessed_by = models.ForeignKey("accounts.User",on_delete=models.PROTECT,related_name="industrial_hygiene_compliance_assessments",blank=True,null=True)
    status = models.CharField(max_length=30,choices=STATUS_CHOICES,default="DRAFT")
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "ih_compliance_record"
        ordering = ["-assessment_date","compliance_code"]
    def __str__(self):
        return f"{self.compliance_code} - {self.hazard}"




# =============================================
# ExceedanceAction - Stores Industrial Hygiene exposure exceedance investigation and corrective action details.
# =============================================
class ExceedanceAction(models.Model):
    STATUS_CHOICES = [
        ("OPEN","Open"),
        ("UNDER_INVESTIGATION","Under Investigation"),
        ("ACTION_IN_PROGRESS","Action In Progress"),
        ("PENDING_VERIFICATION","Pending Verification"),
        ("CLOSED","Closed"),
        ("CANCELLED","Cancelled"),
    ]
    PRIORITY_CHOICES = [
        ("LOW","Low"),
        ("MEDIUM","Medium"),
        ("HIGH","High"),
        ("CRITICAL","Critical"),
    ]
    exceedance_code = models.CharField(max_length=100,unique=True)
    compliance_record = models.ForeignKey(ComplianceRecord,on_delete=models.PROTECT,related_name="exceedance_actions")
    exposure_assessment = models.ForeignKey(ExposureAssessment,on_delete=models.PROTECT,related_name="exceedance_actions")
    sampling = models.ForeignKey(SamplingManagement,on_delete=models.PROTECT,related_name="exceedance_actions")
    measurement = models.ForeignKey(MeasurementEntry,on_delete=models.PROTECT,related_name="exceedance_actions",blank=True,null=True)
    laboratory_result = models.ForeignKey(LaboratoryResult,on_delete=models.PROTECT,related_name="exceedance_actions",blank=True,null=True)
    hazard = models.ForeignKey(HazardMaster,on_delete=models.PROTECT,related_name="exceedance_actions")
    exposure_group = models.ForeignKey(ExposureGroupMaster,on_delete=models.PROTECT,related_name="exceedance_actions",blank=True,null=True)
    area_or_location = models.CharField(max_length=200,blank=True,null=True)
    department = models.CharField(max_length=150,blank=True,null=True)
    employee_name = models.CharField(max_length=150,blank=True,null=True)
    measured_value = models.DecimalField(max_digits=15,decimal_places=6)
    applicable_limit = models.DecimalField(max_digits=15,decimal_places=6,blank=True,null=True)
    exceedance_value = models.DecimalField(max_digits=15,decimal_places=6,blank=True,null=True)
    exceedance_percentage = models.DecimalField(max_digits=10,decimal_places=4,blank=True,null=True)
    risk_level = models.CharField(max_length=30,choices=ExposureAssessment.RISK_LEVEL_CHOICES,default="NOT_ASSESSED")
    priority = models.CharField(max_length=30,choices=PRIORITY_CHOICES,default="MEDIUM")
    investigation_required = models.BooleanField(default=True)
    investigation_details = models.TextField(blank=True,null=True)
    root_cause = models.TextField(blank=True,null=True)
    immediate_action = models.TextField(blank=True,null=True)
    corrective_action = models.TextField(blank=True,null=True)
    responsible_person = models.ForeignKey("accounts.User",on_delete=models.PROTECT,related_name="industrial_hygiene_exceedance_actions",blank=True,null=True)
    due_date = models.DateField(blank=True,null=True)
    evidence = models.TextField(blank=True,null=True)
    verification_details = models.TextField(blank=True,null=True)
    verified_by = models.ForeignKey("accounts.User",on_delete=models.PROTECT,related_name="industrial_hygiene_exceedance_verifications",blank=True,null=True)
    verification_date = models.DateField(blank=True,null=True)
    closure_remarks = models.TextField(blank=True,null=True)
    closure_date = models.DateField(blank=True,null=True)
    status = models.CharField(max_length=30,choices=STATUS_CHOICES,default="OPEN")
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "ih_exceedance_action"
        ordering = ["-created_at","exceedance_code"]
    def __str__(self):
        return f"{self.exceedance_code} - {self.hazard}"





# =============================================
# ReMonitoring - Stores Industrial Hygiene re-monitoring activities and effectiveness evaluation.
# =============================================
class ReMonitoring(models.Model):
    STATUS_CHOICES = [
        ("PLANNED","Planned"),
        ("SCHEDULED","Scheduled"),
        ("SAMPLED","Sampled"),
        ("RESULT_RECEIVED","Result Received"),
        ("COMPLIANT","Compliant"),
        ("NON_COMPLIANT","Non-Compliant"),
        ("CLOSED","Closed"),
        ("CANCELLED","Cancelled"),
    ]
    EFFECTIVENESS_CHOICES = [
        ("NOT_EVALUATED","Not Evaluated"),
        ("EFFECTIVE","Effective"),
        ("PARTIALLY_EFFECTIVE","Partially Effective"),
        ("NOT_EFFECTIVE","Not Effective"),
    ]
    re_monitoring_code = models.CharField(max_length=100,unique=True)
    exceedance_action = models.ForeignKey(ExceedanceAction,on_delete=models.PROTECT,related_name="re_monitoring_records")
    original_sampling = models.ForeignKey(SamplingManagement,on_delete=models.PROTECT,related_name="re_monitoring_records")
    original_measurement = models.ForeignKey(MeasurementEntry,on_delete=models.PROTECT,related_name="re_monitoring_measurements",blank=True,null=True)
    original_result_value = models.DecimalField(max_digits=15,decimal_places=6,blank=True,null=True)
    original_limit_value = models.DecimalField(max_digits=15,decimal_places=6,blank=True,null=True)
    reason = models.TextField()
    re_monitoring_required = models.BooleanField(default=True)
    planned_date = models.DateField(blank=True,null=True)
    actual_sampling_date = models.DateField(blank=True,null=True)
    hazard = models.ForeignKey(HazardMaster,on_delete=models.PROTECT,related_name="re_monitoring_records")
    exposure_group = models.ForeignKey(ExposureGroupMaster,on_delete=models.PROTECT,related_name="re_monitoring_records",blank=True,null=True)
    area_or_location = models.CharField(max_length=200,blank=True,null=True)
    department = models.CharField(max_length=150,blank=True,null=True)
    employee_name = models.CharField(max_length=150,blank=True,null=True)
    monitoring_parameter = models.ForeignKey(MonitoringParameterMaster,on_delete=models.PROTECT,related_name="re_monitoring_records")
    unit = models.ForeignKey(UnitMaster,on_delete=models.PROTECT,related_name="re_monitoring_records")
    new_sampling = models.ForeignKey(SamplingManagement,on_delete=models.PROTECT,related_name="new_re_monitoring_records",blank=True,null=True)
    new_measurement = models.ForeignKey(MeasurementEntry,on_delete=models.PROTECT,related_name="new_re_monitoring_measurements",blank=True,null=True)
    new_result_value = models.DecimalField(max_digits=15,decimal_places=6,blank=True,null=True)
    applicable_limit = models.DecimalField(max_digits=15,decimal_places=6,blank=True,null=True)
    comparison_with_previous = models.TextField(blank=True,null=True)
    compliance_status = models.CharField(max_length=30,choices=[("WITHIN_LIMIT","Within Limit"),("EXCEEDS_LIMIT","Exceeds Limit"),("NOT_ASSESSED","Not Assessed")],default="NOT_ASSESSED")
    effectiveness = models.CharField(max_length=30,choices=EFFECTIVENESS_CHOICES,default="NOT_EVALUATED")
    effectiveness_remarks = models.TextField(blank=True,null=True)
    conducted_by = models.ForeignKey("accounts.User",on_delete=models.PROTECT,related_name="industrial_hygiene_re_monitoring_conducted",blank=True,null=True)
    verified_by = models.ForeignKey("accounts.User",on_delete=models.PROTECT,related_name="industrial_hygiene_re_monitoring_verified",blank=True,null=True)
    verification_date = models.DateField(blank=True,null=True)
    closure_remarks = models.TextField(blank=True,null=True)
    closure_date = models.DateField(blank=True,null=True)
    status = models.CharField(max_length=30,choices=STATUS_CHOICES,default="PLANNED")
    is_active = models.BooleanField(default=True,verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "ih_re_monitoring"
        ordering = ["-created_at","re_monitoring_code"]
    def __str__(self):
        return f"{self.re_monitoring_code} - {self.hazard}"