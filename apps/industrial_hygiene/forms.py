from django import forms
from django.contrib.auth import get_user_model
from apps.organizations.models import Plant
from .models import (HazardMaster,HazardCategoryMaster,ExposureTypeMaster,ExposureGroupMaster,
                     MonitoringTypeMaster,MonitoringParameterMaster,UnitMaster,ExposureLimitMaster,
                     InstrumentMaster,LaboratoryMaster,IHProgramMaster,MonitoringPlan,MonitoringSchedule,
                     SamplingManagement,MeasurementEntry,LaboratoryResult,ExposureAssessment,
                     ComplianceRecord,ExceedanceAction,ReMonitoring)

User = get_user_model()

# =============================================
# HazardMasterForm - Handles Hazard Master creation and updates.
# =============================================
class HazardMasterForm(forms.ModelForm):
    class Meta:
        model = HazardMaster
        fields = ["hazard_category","hazard","description","is_active"]
        widgets = {
            "hazard_category": forms.Select(attrs={
                "class": "form-control",
            }),
            "hazard": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter hazard",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter hazard description",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "hazard-status-checkbox",
            }),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["hazard_category"].queryset = HazardCategoryMaster.objects.filter(
            is_active=True
        ).order_by("category_name")
        self.fields["hazard_category"].empty_label = "Select Hazard Category"


# =============================================
# HazardCategoryMasterForm - Handles Hazard Category Master creation and updates.
# =============================================
class HazardCategoryMasterForm(forms.ModelForm):
    class Meta:
        model = HazardCategoryMaster
        fields = ["category_name","description","is_active"]
        widgets = {
            "category_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter hazard category"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter hazard category description"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "hazard-status-checkbox"
            }),
        }


# =============================================
# ExposureTypeMasterForm - Handles Exposure Type Master creation and updates.
# =============================================
class ExposureTypeMasterForm(forms.ModelForm):
    class Meta:
        model = ExposureTypeMaster
        fields = ["exposure_type","description","is_active"]
        widgets = {
            "exposure_type": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter exposure type"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter exposure type description"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "hazard-status-checkbox"
            }),
        }


# =============================================
# ExposureGroupMasterForm - Handles Exposure Group / SEG Master creation and updates.
# =============================================
class ExposureGroupMasterForm(forms.ModelForm):
    class Meta:
        model = ExposureGroupMaster
        fields = ["exposure_group","description","is_active"]
        widgets = {
            "exposure_group": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter exposure group / SEG"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter exposure group description"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "hazard-status-checkbox"
            }),
        }


# =============================================
# MonitoringTypeMasterForm - Handles Monitoring Type Master creation and updates.
# =============================================
class MonitoringTypeMasterForm(forms.ModelForm):
    class Meta:
        model = MonitoringTypeMaster
        fields = ["monitoring_type","description","is_active"]
        widgets = {
            "monitoring_type": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter monitoring type"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter monitoring type description"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "hazard-status-checkbox"
            }),
        }



# =============================================
# MonitoringParameterMasterForm - Handles Monitoring Parameter Master creation and updates.
# =============================================
class MonitoringParameterMasterForm(forms.ModelForm):
    class Meta:
        model = MonitoringParameterMaster
        fields = ["parameter_name","description","is_active"]
        widgets = {
            "parameter_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter monitoring parameter"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter monitoring parameter description"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "hazard-status-checkbox"
            }),
        }



# =============================================
# UnitMasterForm - Handles Unit Master creation and updates.
# =============================================
class UnitMasterForm(forms.ModelForm):
    class Meta:
        model = UnitMaster
        fields = ["unit_name","unit_symbol","description","is_active"]
        widgets = {
            "unit_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter unit name"
            }),
            "unit_symbol": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter unit symbol"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter unit description"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "hazard-status-checkbox"
            }),
        }





# =============================================
# ExposureLimitMasterForm - Handles Exposure Limit / OEL Master creation and updates.
# =============================================
class ExposureLimitMasterForm(forms.ModelForm):
    class Meta:
        model = ExposureLimitMaster
        fields = [
            "hazard",
            "monitoring_parameter",
            "unit",
            "exposure_limit_type",
            "limit_value",
            "applicable_standard",
            "source_reference",
            "effective_from",
            "effective_to",
            "is_active",
        ]
        widgets = {
            "hazard": forms.Select(attrs={
                "class": "form-control",
            }),
            "monitoring_parameter": forms.Select(attrs={
                "class": "form-control",
            }),
            "unit": forms.Select(attrs={
                "class": "form-control",
            }),
            "exposure_limit_type": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: TWA, STEL, Ceiling"
            }),
            "limit_value": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Enter exposure limit value",
                "step": "0.0001",
                "min": "0"
            }),
            "applicable_standard": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: OSHA, ACGIH, IS Standard"
            }),
            "source_reference": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter source or reference"
            }),
            "effective_from": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "effective_to": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "hazard-status-checkbox"
            }),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.fields["hazard"].queryset = HazardMaster.objects.filter(
            is_active=True
        ).select_related("hazard_category").order_by(
            "hazard_category__category_name",
            "hazard"
        )
        self.fields["hazard"].empty_label = "Select Hazard"

        self.fields["monitoring_parameter"].queryset = MonitoringParameterMaster.objects.filter(
            is_active=True
        ).order_by("parameter_name")
        self.fields["monitoring_parameter"].empty_label = "Select Monitoring Parameter"

        self.fields["unit"].queryset = UnitMaster.objects.filter(
            is_active=True
        ).order_by("unit_name")
        self.fields["unit"].empty_label = "Select Unit"




# =============================================
# InstrumentMasterForm - Handles Industrial Hygiene instrument creation and updates.
# =============================================
class InstrumentMasterForm(forms.ModelForm):
    class Meta:
        model = InstrumentMaster
        fields = [
            "instrument_name",
            "instrument_code",
            "instrument_type",
            "manufacturer",
            "model_number",
            "serial_number",
            "measurement_parameter",
            "calibration_frequency",
            "last_calibration_date",
            "next_calibration_date",
            "description",
            "is_active",
        ]
        widgets = {
            "instrument_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter instrument name"
            }),
            "instrument_code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter unique instrument code"
            }),
            "instrument_type": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: Noise Dosimeter, Gas Detector, Dust Monitor"
            }),
            "manufacturer": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter manufacturer"
            }),
            "model_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter model number"
            }),
            "serial_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter serial number"
            }),
            "measurement_parameter": forms.Select(attrs={
                "class": "form-control"
            }),
            "calibration_frequency": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: Monthly, Quarterly, Annually"
            }),
            "last_calibration_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "next_calibration_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter instrument description"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "hazard-status-checkbox"
            }),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.fields["measurement_parameter"].queryset = MonitoringParameterMaster.objects.filter(
            is_active=True
        ).order_by("parameter_name")

        self.fields["measurement_parameter"].empty_label = "Select Measurement Parameter"






# =============================================
# LaboratoryMasterForm - Handles Industrial Hygiene laboratory creation and updates.
# =============================================
class LaboratoryMasterForm(forms.ModelForm):
    class Meta:
        model = LaboratoryMaster
        fields = [
            "laboratory_name",
            "laboratory_code",
            "accreditation",
            "contact_person",
            "contact_number",
            "email",
            "address",
            "description",
            "is_active",
        ]
        widgets = {
            "laboratory_name": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Enter laboratory name"
            }),
            "laboratory_code": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Enter unique laboratory code"
            }),
            "accreditation": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Example: NABL, ISO/IEC 17025"
            }),
            "contact_person": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Enter contact person name"
            }),
            "contact_number": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Enter contact number"
            }),
            "email": forms.EmailInput(attrs={
                "class":"form-control",
                "placeholder":"Enter laboratory email"
            }),
            "address": forms.Textarea(attrs={
                "class":"form-control",
                "rows":4,
                "placeholder":"Enter laboratory address"
            }),
            "description": forms.Textarea(attrs={
                "class":"form-control",
                "rows":4,
                "placeholder":"Enter laboratory description"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class":"hazard-status-checkbox"
            }),
        }




# =============================================
# IHProgramMasterForm - Handles Industrial Hygiene program creation and updates.
# =============================================
class IHProgramMasterForm(forms.ModelForm):
    class Meta:
        model = IHProgramMaster
        fields = [
            "program_name",
            "program_code",
            "plant",
            "description",
            "objectives",
            "scope",
            "responsible_person",
            "start_date",
            "end_date",
            "review_frequency",
            "last_review_date",
            "next_review_date",
            "status",
            "is_active",
        ]
        widgets = {
            "program_name": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Enter Industrial Hygiene program name"
            }),
            "program_code": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Enter unique program code"
            }),
            "plant": forms.Select(attrs={
                "class":"form-control"
            }),
            "description": forms.Textarea(attrs={
                "class":"form-control",
                "rows":4,
                "placeholder":"Enter program description"
            }),
            "objectives": forms.Textarea(attrs={
                "class":"form-control",
                "rows":4,
                "placeholder":"Enter program objectives"
            }),
            "scope": forms.Textarea(attrs={
                "class":"form-control",
                "rows":4,
                "placeholder":"Define the scope of the Industrial Hygiene program"
            }),
            "responsible_person": forms.Select(attrs={
                "class":"form-control"
            }),
            "start_date": forms.DateInput(attrs={
                "class":"form-control",
                "type":"date"
            }),
            "end_date": forms.DateInput(attrs={
                "class":"form-control",
                "type":"date"
            }),
            "review_frequency": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Example: Monthly, Quarterly, Annually"
            }),
            "last_review_date": forms.DateInput(attrs={
                "class":"form-control",
                "type":"date"
            }),
            "next_review_date": forms.DateInput(attrs={
                "class":"form-control",
                "type":"date"
            }),
            "status": forms.Select(attrs={
                "class":"form-control"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class":"hazard-status-checkbox"
            }),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.fields["plant"].queryset = Plant.objects.filter(
            is_active=True
        ).order_by("name")

        self.fields["plant"].empty_label = "Select Plant"

        self.fields["responsible_person"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")

        self.fields["responsible_person"].empty_label = "Select Responsible Person"




# =============================================
# MonitoringPlanForm - Handles Industrial Hygiene monitoring plan creation and updates.
# =============================================
class MonitoringPlanForm(forms.ModelForm):
    class Meta:
        model = MonitoringPlan
        fields = [
            "plan_name",
            "plan_code",
            "ih_program",
            "plant",
            "hazard",
            "exposure_type",
            "exposure_group",
            "monitoring_type",
            "monitoring_parameter",
            "unit",
            "exposure_limit",
            "monitoring_frequency",
            "planned_start_date",
            "planned_end_date",
            "sample_count",
            "area_or_location",
            "department",
            "responsible_person",
            "remarks",
            "status",
            "is_active",
        ]
        widgets = {
            "plan_name": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Enter monitoring plan name"
            }),
            "plan_code": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Enter unique monitoring plan code"
            }),
            "ih_program": forms.Select(attrs={
                "class":"form-control"
            }),
            "plant": forms.Select(attrs={
                "class":"form-control"
            }),
            "hazard": forms.Select(attrs={
                "class":"form-control"
            }),
            "exposure_type": forms.Select(attrs={
                "class":"form-control"
            }),
            "exposure_group": forms.Select(attrs={
                "class":"form-control"
            }),
            "monitoring_type": forms.Select(attrs={
                "class":"form-control"
            }),
            "monitoring_parameter": forms.Select(attrs={
                "class":"form-control"
            }),
            "unit": forms.Select(attrs={
                "class":"form-control"
            }),
            "exposure_limit": forms.Select(attrs={
                "class":"form-control"
            }),
            "monitoring_frequency": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Example: Monthly, Quarterly, Half-Yearly, Annually"
            }),
            "planned_start_date": forms.DateInput(attrs={
                "class":"form-control",
                "type":"date"
            }),
            "planned_end_date": forms.DateInput(attrs={
                "class":"form-control",
                "type":"date"
            }),
            "sample_count": forms.NumberInput(attrs={
                "class":"form-control",
                "min":"1",
                "placeholder":"Enter planned sample count"
            }),
            "area_or_location": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Enter area or monitoring location"
            }),
            "department": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Enter department"
            }),
            "responsible_person": forms.Select(attrs={
                "class":"form-control"
            }),
            "remarks": forms.Textarea(attrs={
                "class":"form-control",
                "rows":4,
                "placeholder":"Enter additional remarks"
            }),
            "status": forms.Select(attrs={
                "class":"form-control"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class":"hazard-status-checkbox"
            }),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["ih_program"].queryset = IHProgramMaster.objects.filter(
            is_active=True
        ).order_by("program_name")
        self.fields["ih_program"].empty_label = "Select IH Program"
        self.fields["plant"].queryset = Plant.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["plant"].empty_label = "Select Plant"
        self.fields["hazard"].queryset = HazardMaster.objects.filter(
            is_active=True
        ).select_related("hazard_category").order_by(
            "hazard_category__category_name",
            "hazard"
        )
        self.fields["hazard"].empty_label = "Select Hazard"
        self.fields["exposure_type"].queryset = ExposureTypeMaster.objects.filter(
            is_active=True
        ).order_by("exposure_type")
        self.fields["exposure_type"].empty_label = "Select Exposure Type"
        self.fields["exposure_group"].queryset = ExposureGroupMaster.objects.filter(
            is_active=True
        ).order_by("exposure_group")
        self.fields["exposure_group"].empty_label = "Select Exposure Group / SEG"
        self.fields["monitoring_type"].queryset = MonitoringTypeMaster.objects.filter(
            is_active=True
        ).order_by("monitoring_type")
        self.fields["monitoring_type"].empty_label = "Select Monitoring Type"
        self.fields["monitoring_parameter"].queryset = MonitoringParameterMaster.objects.filter(
            is_active=True
        ).order_by("parameter_name")
        self.fields["monitoring_parameter"].empty_label = "Select Monitoring Parameter"
        self.fields["unit"].queryset = UnitMaster.objects.filter(
            is_active=True
        ).order_by("unit_name")
        self.fields["unit"].empty_label = "Select Unit"
        self.fields["exposure_limit"].queryset = ExposureLimitMaster.objects.filter(
            is_active=True
        ).select_related(
            "hazard",
            "monitoring_parameter",
            "unit"
        ).order_by(
            "hazard__hazard",
            "monitoring_parameter__parameter_name"
        )
        self.fields["exposure_limit"].empty_label = "Select Exposure Limit"
        self.fields["responsible_person"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["responsible_person"].empty_label = "Select Responsible Person"




# =============================================
# MonitoringScheduleForm - Handles Industrial Hygiene monitoring schedule creation and updates.
# =============================================
class MonitoringScheduleForm(forms.ModelForm):
    class Meta:
        model = MonitoringSchedule
        fields = [
            "schedule_name",
            "schedule_code",
            "monitoring_plan",
            "planned_date",
            "scheduled_start_date",
            "scheduled_end_date",
            "frequency",
            "sample_count",
            "responsible_person",
            "assigned_to",
            "status",
            "remarks",
            "is_active",
        ]
        widgets = {
            "schedule_name": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Enter monitoring schedule name"
            }),
            "schedule_code": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Enter unique schedule code"
            }),
            "monitoring_plan": forms.Select(attrs={
                "class":"form-control"
            }),
            "planned_date": forms.DateInput(attrs={
                "class":"form-control",
                "type":"date"
            }),
            "scheduled_start_date": forms.DateInput(attrs={
                "class":"form-control",
                "type":"date"
            }),
            "scheduled_end_date": forms.DateInput(attrs={
                "class":"form-control",
                "type":"date"
            }),
            "frequency": forms.TextInput(attrs={
                "class":"form-control",
                "placeholder":"Example: Monthly, Quarterly, Annually"
            }),
            "sample_count": forms.NumberInput(attrs={
                "class":"form-control",
                "min":"1",
                "placeholder":"Enter sample count"
            }),
            "responsible_person": forms.Select(attrs={
                "class":"form-control"
            }),
            "assigned_to": forms.Select(attrs={
                "class":"form-control"
            }),
            "status": forms.Select(attrs={
                "class":"form-control"
            }),
            "remarks": forms.Textarea(attrs={
                "class":"form-control",
                "rows":4,
                "placeholder":"Enter schedule remarks"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class":"hazard-status-checkbox"
            }),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["monitoring_plan"].queryset = MonitoringPlan.objects.filter(
            is_active=True
        ).select_related(
            "ih_program",
            "plant",
            "hazard"
        ).order_by("plan_name")
        self.fields["monitoring_plan"].empty_label = "Select Monitoring Plan"
        self.fields["responsible_person"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["responsible_person"].empty_label = "Select Responsible Person"
        self.fields["assigned_to"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["assigned_to"].empty_label = "Select Assigned Person"




# =============================================
# SamplingManagementForm - Handles Industrial Hygiene sample collection creation and updates.
# =============================================
class SamplingManagementForm(forms.ModelForm):
    class Meta:
        model = SamplingManagement
        fields = [
            "sampling_code",
            "monitoring_schedule",
            "sample_number",
            "sampling_date",
            "sampling_start_time",
            "sampling_end_time",
            "hazard",
            "exposure_type",
            "exposure_group",
            "area_or_location",
            "department",
            "monitoring_parameter",
            "unit",
            "instrument",
            "laboratory",
            "sample_type",
            "sample_quantity",
            "sampling_method",
            "collected_by",
            "sent_to_lab_date",
            "laboratory_reference",
            "status",
            "remarks",
            "is_active",
        ]
        widgets = {
            "sampling_code": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter unique sampling code"}),
            "monitoring_schedule": forms.Select(attrs={"class":"form-control"}),
            "sample_number": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter sample number"}),
            "sampling_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "sampling_start_time": forms.TimeInput(attrs={"class":"form-control","type":"time"}),
            "sampling_end_time": forms.TimeInput(attrs={"class":"form-control","type":"time"}),
            "hazard": forms.Select(attrs={"class":"form-control"}),
            "exposure_type": forms.Select(attrs={"class":"form-control"}),
            "exposure_group": forms.Select(attrs={"class":"form-control"}),
            "area_or_location": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter area or location"}),
            "department": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter department"}),
            "monitoring_parameter": forms.Select(attrs={"class":"form-control"}),
            "unit": forms.Select(attrs={"class":"form-control"}),
            "instrument": forms.Select(attrs={"class":"form-control"}),
            "laboratory": forms.Select(attrs={"class":"form-control"}),
            "sample_type": forms.TextInput(attrs={"class":"form-control","placeholder":"Example: Personal, Area, Grab, Air"}),
            "sample_quantity": forms.NumberInput(attrs={"class":"form-control","step":"0.0001","min":"0","placeholder":"Enter sample quantity"}),
            "sampling_method": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter sampling method"}),
            "collected_by": forms.Select(attrs={"class":"form-control"}),
            "sent_to_lab_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "laboratory_reference": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter laboratory reference"}),
            "status": forms.Select(attrs={"class":"form-control"}),
            "remarks": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter sampling remarks"}),
            "is_active": forms.CheckboxInput(attrs={"class":"hazard-status-checkbox"}),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["monitoring_schedule"].queryset = MonitoringSchedule.objects.filter(
            is_active=True
        ).select_related(
            "monitoring_plan",
            "monitoring_plan__ih_program",
            "monitoring_plan__plant"
        ).order_by("-planned_date","schedule_name")
        self.fields["monitoring_schedule"].empty_label = "Select Monitoring Schedule"
        self.fields["hazard"].queryset = HazardMaster.objects.filter(
            is_active=True
        ).select_related("hazard_category").order_by(
            "hazard_category__category_name","hazard"
        )
        self.fields["hazard"].empty_label = "Select Hazard"
        self.fields["exposure_type"].queryset = ExposureTypeMaster.objects.filter(
            is_active=True
        ).order_by("exposure_type")
        self.fields["exposure_type"].empty_label = "Select Exposure Type"
        self.fields["exposure_group"].queryset = ExposureGroupMaster.objects.filter(
            is_active=True
        ).order_by("exposure_group")
        self.fields["exposure_group"].empty_label = "Select Exposure Group / SEG"
        self.fields["monitoring_parameter"].queryset = MonitoringParameterMaster.objects.filter(
            is_active=True
        ).order_by("parameter_name")
        self.fields["monitoring_parameter"].empty_label = "Select Monitoring Parameter"
        self.fields["unit"].queryset = UnitMaster.objects.filter(
            is_active=True
        ).order_by("unit_name")
        self.fields["unit"].empty_label = "Select Unit"
        self.fields["instrument"].queryset = InstrumentMaster.objects.filter(
            is_active=True
        ).select_related("measurement_parameter").order_by("instrument_name")
        self.fields["instrument"].empty_label = "Select Instrument"
        self.fields["laboratory"].queryset = LaboratoryMaster.objects.filter(
            is_active=True
        ).order_by("laboratory_name")
        self.fields["laboratory"].empty_label = "Select Laboratory"
        self.fields["collected_by"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["collected_by"].empty_label = "Select Collector"




# =============================================
# MeasurementEntryForm - Handles Industrial Hygiene measurement result creation and updates.
# =============================================
class MeasurementEntryForm(forms.ModelForm):
    class Meta:
        model = MeasurementEntry
        fields = [
            "sampling",
            "measurement_code",
            "measurement_date",
            "monitoring_parameter",
            "unit",
            "measured_value",
            "detection_limit",
            "result_remarks",
            "entered_by",
            "verified_by",
            "verification_date",
            "status",
            "is_active",
        ]
        widgets = {
            "sampling": forms.Select(attrs={"class":"form-control"}),
            "measurement_code": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter unique measurement code"}),
            "measurement_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "monitoring_parameter": forms.Select(attrs={"class":"form-control"}),
            "unit": forms.Select(attrs={"class":"form-control"}),
            "measured_value": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter measured value"}),
            "detection_limit": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter detection limit if applicable"}),
            "result_remarks": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter measurement result remarks"}),
            "entered_by": forms.Select(attrs={"class":"form-control"}),
            "verified_by": forms.Select(attrs={"class":"form-control"}),
            "verification_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "status": forms.Select(attrs={"class":"form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class":"hazard-status-checkbox"}),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["sampling"].queryset = SamplingManagement.objects.filter(
            is_active=True
        ).select_related(
            "monitoring_schedule",
            "monitoring_schedule__monitoring_plan",
            "hazard",
            "monitoring_parameter",
            "unit"
        ).order_by("-sampling_date","sampling_code")
        self.fields["sampling"].empty_label = "Select Sampling Record"
        self.fields["monitoring_parameter"].queryset = MonitoringParameterMaster.objects.filter(
            is_active=True
        ).order_by("parameter_name")
        self.fields["monitoring_parameter"].empty_label = "Select Monitoring Parameter"
        self.fields["unit"].queryset = UnitMaster.objects.filter(
            is_active=True
        ).order_by("unit_name")
        self.fields["unit"].empty_label = "Select Unit"
        self.fields["entered_by"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["entered_by"].empty_label = "Select User"
        self.fields["verified_by"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["verified_by"].empty_label = "Select Verifier"





# =============================================
# LaboratoryResultForm - Handles Industrial Hygiene laboratory result creation and updates.
# =============================================
class LaboratoryResultForm(forms.ModelForm):
    class Meta:
        model = LaboratoryResult
        fields = [
            "sampling",
            "laboratory",
            "measurement",
            "result_code",
            "laboratory_reference",
            "result_date",
            "monitoring_parameter",
            "unit",
            "result_value",
            "detection_limit",
            "test_method",
            "certificate_number",
            "certificate_date",
            "remarks",
            "received_by",
            "verified_by",
            "verification_date",
            "status",
            "is_active",
        ]
        widgets = {
            "sampling": forms.Select(attrs={"class":"form-control"}),
            "laboratory": forms.Select(attrs={"class":"form-control"}),
            "measurement": forms.Select(attrs={"class":"form-control"}),
            "result_code": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter unique laboratory result code"}),
            "laboratory_reference": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter laboratory reference number"}),
            "result_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "monitoring_parameter": forms.Select(attrs={"class":"form-control"}),
            "unit": forms.Select(attrs={"class":"form-control"}),
            "result_value": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter laboratory result value"}),
            "detection_limit": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter detection limit if applicable"}),
            "test_method": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter laboratory test method"}),
            "certificate_number": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter certificate number"}),
            "certificate_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "remarks": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter laboratory result remarks"}),
            "received_by": forms.Select(attrs={"class":"form-control"}),
            "verified_by": forms.Select(attrs={"class":"form-control"}),
            "verification_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "status": forms.Select(attrs={"class":"form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class":"hazard-status-checkbox"}),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["sampling"].queryset = SamplingManagement.objects.filter(
            is_active=True
        ).select_related(
            "monitoring_schedule",
            "monitoring_schedule__monitoring_plan",
            "hazard",
            "monitoring_parameter",
            "unit"
        ).order_by("-sampling_date","sampling_code")
        self.fields["sampling"].empty_label = "Select Sampling Record"
        self.fields["laboratory"].queryset = LaboratoryMaster.objects.filter(
            is_active=True
        ).order_by("laboratory_name")
        self.fields["laboratory"].empty_label = "Select Laboratory"
        self.fields["measurement"].queryset = MeasurementEntry.objects.filter(
            is_active=True
        ).select_related(
            "sampling",
            "monitoring_parameter",
            "unit"
        ).order_by("-measurement_date","measurement_code")
        self.fields["measurement"].empty_label = "Select Measurement Entry"
        self.fields["monitoring_parameter"].queryset = MonitoringParameterMaster.objects.filter(
            is_active=True
        ).order_by("parameter_name")
        self.fields["monitoring_parameter"].empty_label = "Select Monitoring Parameter"
        self.fields["unit"].queryset = UnitMaster.objects.filter(
            is_active=True
        ).order_by("unit_name")
        self.fields["unit"].empty_label = "Select Unit"
        self.fields["received_by"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["received_by"].empty_label = "Select User"
        self.fields["verified_by"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["verified_by"].empty_label = "Select Verifier"




# =============================================
# ExposureAssessmentForm - Handles Industrial Hygiene exposure assessment creation and updates.
# =============================================
class ExposureAssessmentForm(forms.ModelForm):
    class Meta:
        model = ExposureAssessment
        fields = [
            "assessment_code","sampling","measurement","laboratory_result","hazard",
            "exposure_type","exposure_group","area_or_location","department",
            "employee_name","monitoring_parameter","unit","measured_value",
            "applicable_oel","exposure_limit_value","compliance_status","risk_level",
            "existing_controls","assessment_remarks","assessment_date","assessor",
            "status","is_active",
        ]
        widgets = {
            "assessment_code": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter unique assessment code"}),
            "sampling": forms.Select(attrs={"class":"form-control"}),
            "measurement": forms.Select(attrs={"class":"form-control"}),
            "laboratory_result": forms.Select(attrs={"class":"form-control"}),
            "hazard": forms.Select(attrs={"class":"form-control"}),
            "exposure_type": forms.Select(attrs={"class":"form-control"}),
            "exposure_group": forms.Select(attrs={"class":"form-control"}),
            "area_or_location": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter area or location"}),
            "department": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter department"}),
            "employee_name": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter employee name if applicable"}),
            "monitoring_parameter": forms.Select(attrs={"class":"form-control"}),
            "unit": forms.Select(attrs={"class":"form-control"}),
            "measured_value": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter measured value"}),
            "applicable_oel": forms.Select(attrs={"class":"form-control"}),
            "exposure_limit_value": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter applicable exposure limit"}),
            "compliance_status": forms.Select(attrs={"class":"form-control"}),
            "risk_level": forms.Select(attrs={"class":"form-control"}),
            "existing_controls": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter existing exposure controls"}),
            "assessment_remarks": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter assessment remarks"}),
            "assessment_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "assessor": forms.Select(attrs={"class":"form-control"}),
            "status": forms.Select(attrs={"class":"form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class":"hazard-status-checkbox"}),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["sampling"].queryset = SamplingManagement.objects.filter(
            is_active=True
        ).select_related(
            "monitoring_schedule",
            "monitoring_schedule__monitoring_plan",
            "hazard",
            "exposure_type",
            "exposure_group",
            "monitoring_parameter",
            "unit"
        ).order_by("-sampling_date","sampling_code")
        self.fields["sampling"].empty_label = "Select Sampling Record"

        self.fields["measurement"].queryset = MeasurementEntry.objects.filter(
            is_active=True
        ).select_related(
            "sampling",
            "monitoring_parameter",
            "unit"
        ).order_by("-measurement_date","measurement_code")
        self.fields["measurement"].empty_label = "Select Measurement Entry"

        self.fields["laboratory_result"].queryset = LaboratoryResult.objects.filter(
            is_active=True
        ).select_related(
            "sampling",
            "laboratory",
            "measurement",
            "monitoring_parameter",
            "unit"
        ).order_by("-result_date","result_code")
        self.fields["laboratory_result"].empty_label = "Select Laboratory Result"

        self.fields["hazard"].queryset = HazardMaster.objects.filter(
            is_active=True
        ).select_related(
            "hazard_category"
        ).order_by("hazard_category__category_name","hazard")
        self.fields["hazard"].empty_label = "Select Hazard"

        self.fields["exposure_type"].queryset = ExposureTypeMaster.objects.filter(
            is_active=True
        ).order_by("exposure_type")
        self.fields["exposure_type"].empty_label = "Select Exposure Type"

        self.fields["exposure_group"].queryset = ExposureGroupMaster.objects.filter(
            is_active=True
        ).order_by("exposure_group")
        self.fields["exposure_group"].empty_label = "Select Exposure Group"

        self.fields["monitoring_parameter"].queryset = MonitoringParameterMaster.objects.filter(
            is_active=True
        ).order_by("parameter_name")
        self.fields["monitoring_parameter"].empty_label = "Select Monitoring Parameter"

        self.fields["unit"].queryset = UnitMaster.objects.filter(
            is_active=True
        ).order_by("unit_name")
        self.fields["unit"].empty_label = "Select Unit"

        self.fields["applicable_oel"].queryset = ExposureLimitMaster.objects.filter(
            is_active=True
        ).select_related(
            "hazard",
            "monitoring_parameter",
            "unit"
        ).order_by(
            "hazard__hazard",
            "monitoring_parameter__parameter_name"
        )
        self.fields["applicable_oel"].empty_label = "Select Applicable Exposure Limit"

        self.fields["assessor"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["assessor"].empty_label = "Select Assessor"





# =============================================
# ComplianceRecordForm - Handles Industrial Hygiene compliance evaluation creation and updates.
# =============================================
class ComplianceRecordForm(forms.ModelForm):
    class Meta:
        model = ComplianceRecord
        fields = [
            "compliance_code","exposure_assessment","sampling","measurement",
            "laboratory_result","hazard","exposure_group","area_or_location",
            "department","employee_name","monitoring_parameter","unit",
            "measured_value","applicable_oel","exposure_limit_value",
            "exceedance_value","exceedance_percentage","compliance_status",
            "risk_level","investigation_required","investigation_details",
            "remarks","assessment_date","assessed_by","status","is_active",
        ]
        widgets = {
            "compliance_code": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter unique compliance code"}),
            "exposure_assessment": forms.Select(attrs={"class":"form-control"}),
            "sampling": forms.Select(attrs={"class":"form-control"}),
            "measurement": forms.Select(attrs={"class":"form-control"}),
            "laboratory_result": forms.Select(attrs={"class":"form-control"}),
            "hazard": forms.Select(attrs={"class":"form-control"}),
            "exposure_group": forms.Select(attrs={"class":"form-control"}),
            "area_or_location": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter area or location"}),
            "department": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter department"}),
            "employee_name": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter employee name if applicable"}),
            "monitoring_parameter": forms.Select(attrs={"class":"form-control"}),
            "unit": forms.Select(attrs={"class":"form-control"}),
            "measured_value": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter measured value"}),
            "applicable_oel": forms.Select(attrs={"class":"form-control"}),
            "exposure_limit_value": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter applicable exposure limit"}),
            "exceedance_value": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter exceedance value"}),
            "exceedance_percentage": forms.NumberInput(attrs={"class":"form-control","step":"0.0001","placeholder":"Enter exceedance percentage"}),
            "compliance_status": forms.Select(attrs={"class":"form-control"}),
            "risk_level": forms.Select(attrs={"class":"form-control"}),
            "investigation_required": forms.CheckboxInput(attrs={"class":"hazard-status-checkbox"}),
            "investigation_details": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter investigation details"}),
            "remarks": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter compliance remarks"}),
            "assessment_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "assessed_by": forms.Select(attrs={"class":"form-control"}),
            "status": forms.Select(attrs={"class":"form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class":"hazard-status-checkbox"}),
        }
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["exposure_assessment"].queryset = ExposureAssessment.objects.filter(
            is_active=True
        ).select_related(
            "sampling","hazard","exposure_type","exposure_group",
            "monitoring_parameter","unit","applicable_oel"
        ).order_by("-assessment_date","assessment_code")
        self.fields["exposure_assessment"].empty_label = "Select Exposure Assessment"
        self.fields["sampling"].queryset = SamplingManagement.objects.filter(
            is_active=True
        ).select_related(
            "monitoring_schedule","hazard","exposure_type",
            "exposure_group","monitoring_parameter","unit"
        ).order_by("-sampling_date","sampling_code")
        self.fields["sampling"].empty_label = "Select Sampling Record"
        self.fields["measurement"].queryset = MeasurementEntry.objects.filter(
            is_active=True
        ).select_related(
            "sampling","monitoring_parameter","unit"
        ).order_by("-measurement_date","measurement_code")
        self.fields["measurement"].empty_label = "Select Measurement Entry"
        self.fields["laboratory_result"].queryset = LaboratoryResult.objects.filter(
            is_active=True
        ).select_related(
            "sampling","laboratory","measurement",
            "monitoring_parameter","unit"
        ).order_by("-result_date","result_code")
        self.fields["laboratory_result"].empty_label = "Select Laboratory Result"
        self.fields["hazard"].queryset = HazardMaster.objects.filter(
            is_active=True
        ).select_related(
            "hazard_category"
        ).order_by("hazard_category__category_name","hazard")
        self.fields["hazard"].empty_label = "Select Hazard"
        self.fields["exposure_group"].queryset = ExposureGroupMaster.objects.filter(
            is_active=True
        ).order_by("exposure_group")
        self.fields["exposure_group"].empty_label = "Select Exposure Group"
        self.fields["monitoring_parameter"].queryset = MonitoringParameterMaster.objects.filter(
            is_active=True
        ).order_by("parameter_name")
        self.fields["monitoring_parameter"].empty_label = "Select Monitoring Parameter"
        self.fields["unit"].queryset = UnitMaster.objects.filter(
            is_active=True
        ).order_by("unit_name")
        self.fields["unit"].empty_label = "Select Unit"
        self.fields["applicable_oel"].queryset = ExposureLimitMaster.objects.filter(
            is_active=True
        ).select_related(
            "hazard","monitoring_parameter","unit"
        ).order_by(
            "hazard__hazard",
            "monitoring_parameter__parameter_name"
        )
        self.fields["applicable_oel"].empty_label = "Select Applicable Exposure Limit"
        self.fields["assessed_by"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["assessed_by"].empty_label = "Select Assessor"




# =============================================
# ExceedanceActionForm - Handles Industrial Hygiene exceedance investigation and corrective action creation and updates.
# =============================================
class ExceedanceActionForm(forms.ModelForm):
    class Meta:
        model = ExceedanceAction
        fields = [
            "exceedance_code","compliance_record","exposure_assessment","sampling",
            "measurement","laboratory_result","hazard","exposure_group",
            "area_or_location","department","employee_name","measured_value",
            "applicable_limit","exceedance_value","exceedance_percentage",
            "risk_level","priority","investigation_required","investigation_details",
            "root_cause","immediate_action","corrective_action","responsible_person",
            "due_date","evidence","verification_details","verified_by",
            "verification_date","closure_remarks","closure_date","status","is_active",
        ]
        widgets = {
            "exceedance_code": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter unique exceedance code"}),
            "compliance_record": forms.Select(attrs={"class":"form-control"}),
            "exposure_assessment": forms.Select(attrs={"class":"form-control"}),
            "sampling": forms.Select(attrs={"class":"form-control"}),
            "measurement": forms.Select(attrs={"class":"form-control"}),
            "laboratory_result": forms.Select(attrs={"class":"form-control"}),
            "hazard": forms.Select(attrs={"class":"form-control"}),
            "exposure_group": forms.Select(attrs={"class":"form-control"}),
            "area_or_location": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter area or location"}),
            "department": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter department"}),
            "employee_name": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter employee name if applicable"}),
            "measured_value": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter measured value"}),
            "applicable_limit": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter applicable exposure limit"}),
            "exceedance_value": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter exceedance value"}),
            "exceedance_percentage": forms.NumberInput(attrs={"class":"form-control","step":"0.0001","placeholder":"Enter exceedance percentage"}),
            "risk_level": forms.Select(attrs={"class":"form-control"}),
            "priority": forms.Select(attrs={"class":"form-control"}),
            "investigation_required": forms.CheckboxInput(attrs={"class":"hazard-status-checkbox"}),
            "investigation_details": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter investigation details"}),
            "root_cause": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter identified root cause"}),
            "immediate_action": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter immediate action taken"}),
            "corrective_action": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter corrective action required"}),
            "responsible_person": forms.Select(attrs={"class":"form-control"}),
            "due_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "evidence": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter evidence or evidence reference"}),
            "verification_details": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter verification details"}),
            "verified_by": forms.Select(attrs={"class":"form-control"}),
            "verification_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "closure_remarks": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter closure remarks"}),
            "closure_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "status": forms.Select(attrs={"class":"form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class":"hazard-status-checkbox"}),
        }
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["compliance_record"].queryset = ComplianceRecord.objects.filter(
            is_active=True
        ).select_related(
            "exposure_assessment","sampling","hazard",
            "exposure_group","monitoring_parameter","unit","applicable_oel"
        ).order_by("-assessment_date","compliance_code")
        self.fields["compliance_record"].empty_label = "Select Compliance Record"
        self.fields["exposure_assessment"].queryset = ExposureAssessment.objects.filter(
            is_active=True
        ).select_related(
            "sampling","hazard","exposure_type",
            "exposure_group","monitoring_parameter","unit","applicable_oel"
        ).order_by("-assessment_date","assessment_code")
        self.fields["exposure_assessment"].empty_label = "Select Exposure Assessment"
        self.fields["sampling"].queryset = SamplingManagement.objects.filter(
            is_active=True
        ).select_related(
            "monitoring_schedule","hazard","exposure_type",
            "exposure_group","monitoring_parameter","unit"
        ).order_by("-sampling_date","sampling_code")
        self.fields["sampling"].empty_label = "Select Sampling Record"
        self.fields["measurement"].queryset = MeasurementEntry.objects.filter(
            is_active=True
        ).select_related(
            "sampling","monitoring_parameter","unit"
        ).order_by("-measurement_date","measurement_code")
        self.fields["measurement"].empty_label = "Select Measurement Entry"
        self.fields["laboratory_result"].queryset = LaboratoryResult.objects.filter(
            is_active=True
        ).select_related(
            "sampling","laboratory","measurement",
            "monitoring_parameter","unit"
        ).order_by("-result_date","result_code")
        self.fields["laboratory_result"].empty_label = "Select Laboratory Result"
        self.fields["hazard"].queryset = HazardMaster.objects.filter(
            is_active=True
        ).select_related(
            "hazard_category"
        ).order_by("hazard_category__category_name","hazard")
        self.fields["hazard"].empty_label = "Select Hazard"
        self.fields["exposure_group"].queryset = ExposureGroupMaster.objects.filter(
            is_active=True
        ).order_by("exposure_group")
        self.fields["exposure_group"].empty_label = "Select Exposure Group"
        self.fields["responsible_person"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["responsible_person"].empty_label = "Select Responsible Person"
        self.fields["verified_by"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["verified_by"].empty_label = "Select Verifier"




# =============================================
# ReMonitoringForm - Handles Industrial Hygiene re-monitoring creation and updates.
# =============================================
class ReMonitoringForm(forms.ModelForm):
    class Meta:
        model = ReMonitoring
        fields = [
            "re_monitoring_code","exceedance_action","original_sampling",
            "original_measurement","original_result_value","original_limit_value",
            "reason","re_monitoring_required","planned_date","actual_sampling_date",
            "hazard","exposure_group","area_or_location","department","employee_name",
            "monitoring_parameter","unit","new_sampling","new_measurement",
            "new_result_value","applicable_limit","comparison_with_previous",
            "compliance_status","effectiveness","effectiveness_remarks","conducted_by",
            "verified_by","verification_date","closure_remarks","closure_date",
            "status","is_active",
        ]
        widgets = {
            "re_monitoring_code": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter unique re-monitoring code"}),
            "exceedance_action": forms.Select(attrs={"class":"form-control"}),
            "original_sampling": forms.Select(attrs={"class":"form-control"}),
            "original_measurement": forms.Select(attrs={"class":"form-control"}),
            "original_result_value": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter original result value"}),
            "original_limit_value": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter original applicable limit"}),
            "reason": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter reason for re-monitoring"}),
            "re_monitoring_required": forms.CheckboxInput(attrs={"class":"hazard-status-checkbox"}),
            "planned_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "actual_sampling_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "hazard": forms.Select(attrs={"class":"form-control"}),
            "exposure_group": forms.Select(attrs={"class":"form-control"}),
            "area_or_location": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter area or location"}),
            "department": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter department"}),
            "employee_name": forms.TextInput(attrs={"class":"form-control","placeholder":"Enter employee name if applicable"}),
            "monitoring_parameter": forms.Select(attrs={"class":"form-control"}),
            "unit": forms.Select(attrs={"class":"form-control"}),
            "new_sampling": forms.Select(attrs={"class":"form-control"}),
            "new_measurement": forms.Select(attrs={"class":"form-control"}),
            "new_result_value": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter new monitoring result"}),
            "applicable_limit": forms.NumberInput(attrs={"class":"form-control","step":"0.000001","placeholder":"Enter applicable exposure limit"}),
            "comparison_with_previous": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter comparison with previous monitoring result"}),
            "compliance_status": forms.Select(attrs={"class":"form-control"}),
            "effectiveness": forms.Select(attrs={"class":"form-control"}),
            "effectiveness_remarks": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter effectiveness evaluation remarks"}),
            "conducted_by": forms.Select(attrs={"class":"form-control"}),
            "verified_by": forms.Select(attrs={"class":"form-control"}),
            "verification_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "closure_remarks": forms.Textarea(attrs={"class":"form-control","rows":4,"placeholder":"Enter closure remarks"}),
            "closure_date": forms.DateInput(attrs={"class":"form-control","type":"date"}),
            "status": forms.Select(attrs={"class":"form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class":"hazard-status-checkbox"}),
        }
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["exceedance_action"].queryset = ExceedanceAction.objects.filter(
            is_active=True
        ).select_related(
            "compliance_record","exposure_assessment","sampling","hazard","exposure_group"
        ).order_by("-created_at","exceedance_code")
        self.fields["exceedance_action"].empty_label = "Select Exceedance Action"
        self.fields["original_sampling"].queryset = SamplingManagement.objects.filter(
            is_active=True
        ).select_related(
            "monitoring_schedule","hazard","exposure_type",
            "exposure_group","monitoring_parameter","unit"
        ).order_by("-sampling_date","sampling_code")
        self.fields["original_sampling"].empty_label = "Select Original Sampling Record"
        self.fields["original_measurement"].queryset = MeasurementEntry.objects.filter(
            is_active=True
        ).select_related(
            "sampling","monitoring_parameter","unit"
        ).order_by("-measurement_date","measurement_code")
        self.fields["original_measurement"].empty_label = "Select Original Measurement"
        self.fields["hazard"].queryset = HazardMaster.objects.filter(
            is_active=True
        ).select_related(
            "hazard_category"
        ).order_by("hazard_category__category_name","hazard")
        self.fields["hazard"].empty_label = "Select Hazard"
        self.fields["exposure_group"].queryset = ExposureGroupMaster.objects.filter(
            is_active=True
        ).order_by("exposure_group")
        self.fields["exposure_group"].empty_label = "Select Exposure Group"
        self.fields["monitoring_parameter"].queryset = MonitoringParameterMaster.objects.filter(
            is_active=True
        ).order_by("parameter_name")
        self.fields["monitoring_parameter"].empty_label = "Select Monitoring Parameter"
        self.fields["unit"].queryset = UnitMaster.objects.filter(
            is_active=True
        ).order_by("unit_name")
        self.fields["unit"].empty_label = "Select Unit"
        self.fields["new_sampling"].queryset = SamplingManagement.objects.filter(
            is_active=True
        ).select_related(
            "monitoring_schedule","hazard","exposure_type",
            "exposure_group","monitoring_parameter","unit"
        ).order_by("-sampling_date","sampling_code")
        self.fields["new_sampling"].empty_label = "Select New Sampling Record"
        self.fields["new_measurement"].queryset = MeasurementEntry.objects.filter(
            is_active=True
        ).select_related(
            "sampling","monitoring_parameter","unit"
        ).order_by("-measurement_date","measurement_code")
        self.fields["new_measurement"].empty_label = "Select New Measurement"
        self.fields["conducted_by"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["conducted_by"].empty_label = "Select User"
        self.fields["verified_by"].queryset = User.objects.filter(
            is_active=True
        ).order_by("first_name","last_name","username")
        self.fields["verified_by"].empty_label = "Select Verifier"