from django import forms
from apps.organizations.models import Plant
from .models import (
    ExaminationType,MedicalTest,ExposureType,HealthCondition,FitnessStatus,Restriction,
    Vaccination, MedicalProfessional,MedicalFacility,EmployeeHealthProfile, MedicalExamination,
    MedicalTestResult, FitnessToWork, HealthSurveillance, EmployeeExposure, MedicalFollowUp,
    EmployeeVaccination, EmployeeOccupationalDisease, HealthIncident, ReturnToWork, MedicalRecord,
    HealthCamp, HealthCampParticipation
)


# =============================================
# ExaminationTypeForm - Form for creating and updating examination types.
# =============================================
class ExaminationTypeForm(forms.ModelForm):
    class Meta:
        model = ExaminationType
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter examination type'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter code'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


# =============================================
# MedicalTestForm - Form for creating and updating medical test masters.
# =============================================
class MedicalTestForm(forms.ModelForm):
    class Meta:
        model = MedicalTest
        fields = [
            'name',
            'code',
            'test_type',
            'description',
            'unit',
            'normal_range',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter medical test'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter code'
            }),
            'test_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description'
            }),
            'unit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. mg/dL'
            }),
            'normal_range': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 70-100'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


# =============================================
# ExposureTypeForm - Form for creating and updating occupational exposure types.
# =============================================
class ExposureTypeForm(forms.ModelForm):
    class Meta:
        model = ExposureType
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter exposure type'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter code'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }




# =============================================
# HealthConditionForm - Form for creating and updating standardized health conditions
# =============================================
class HealthConditionForm(forms.ModelForm):
    class Meta:
        model = HealthCondition
        fields = [
            'name',
            'code',
            'category',
            'description',
            'is_occupational',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter health condition'
                }
            ),
            'code': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter code'
                }
            ),
            'category': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Enter description'
                }
            ),
            'is_occupational': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input'
                }
            ),
            'is_active': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input'
                }
            ),
        }



class FitnessStatusForm(forms.ModelForm):
    class Meta:
        model = FitnessStatus
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter fitness status'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter code'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }




# =============================================
# RestrictionForm - Form for creating and updating occupational health work restrictions
# =============================================
class RestrictionForm(forms.ModelForm):
    class Meta:
        model = Restriction
        fields = [
            'name',
            'code',
            'description',
            'is_active',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter restriction name',
                'autocomplete': 'off',
            }),

            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter restriction code',
                'autocomplete': 'off',
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter restriction description',
                'rows': 4,
            }),

            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

        labels = {
            'name': 'Restriction Name',
            'code': 'Restriction Code',
            'description': 'Description',
            'is_active': 'Active',
        }

        help_texts = {
            'name': 'Enter the name of the occupational health or work restriction.',
            'code': 'Use a short unique code for this restriction.',
            'description': 'Describe when and why this restriction is applicable.',
        }




class VaccinationForm(forms.ModelForm):

    class Meta:
        model = Vaccination

        fields = [
            'name',
            'code',
            'description',
            'recommended_doses',
            'validity_months',
            'is_active',
        ]

        widgets = {

            'name': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter vaccination name',
            }),

            'code': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter vaccination code',
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter vaccination description...',
                'rows': 4,
            }),

            'recommended_doses': forms.NumberInput(attrs={
                'class': 'form-control-custom',
                'min': 1,
                'placeholder': 'Enter recommended doses',
            }),

            'validity_months': forms.NumberInput(attrs={
                'class': 'form-control-custom',
                'min': 1,
                'placeholder': 'Enter validity in months',
            }),

            'is_active': forms.CheckboxInput(attrs={
                'class': 'custom-checkbox',
            }),
        }



class MedicalProfessionalForm(forms.ModelForm):

    class Meta:
        model = MedicalProfessional

        fields = [
            'name',
            'code',
            'professional_type',
            'qualification',
            'specialization',
            'registration_number',
            'contact_number',
            'email',
            'description',
            'is_active',
        ]

        widgets = {

            'name': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter professional name',
            }),

            'code': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter professional code',
            }),

            'professional_type': forms.Select(attrs={
                'class': 'form-control-custom',
            }),

            'qualification': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter qualification',
            }),

            'specialization': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter specialization',
            }),

            'registration_number': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter registration number',
            }),

            'contact_number': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter contact number',
            }),

            'email': forms.EmailInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter email address',
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter additional information...',
                'rows': 4,
            }),

            'is_active': forms.CheckboxInput(attrs={
                'class': 'custom-checkbox',
            }),
        }



class MedicalFacilityForm(forms.ModelForm):

    class Meta:
        model = MedicalFacility

        fields = [
            'name',
            'code',
            'facility_type',
            'address',
            'contact_person',
            'contact_number',
            'email',
            'registration_number',
            'description',
            'is_active',
        ]

        widgets = {

            'name': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter facility name',
            }),

            'code': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter facility code',
            }),

            'facility_type': forms.Select(attrs={
                'class': 'form-control-custom',
            }),

            'address': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter facility address...',
                'rows': 4,
            }),

            'contact_person': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter contact person',
            }),

            'contact_number': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter contact number',
            }),

            'email': forms.EmailInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter email address',
            }),

            'registration_number': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter registration number',
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter additional information...',
                'rows': 4,
            }),

            'is_active': forms.CheckboxInput(attrs={
                'class': 'custom-checkbox',
            }),
        }


# =============================================
# EmployeeHealthProfileForm - Captures employee personal, employment and occupational health profile information
# =============================================
class EmployeeHealthProfileForm(forms.ModelForm):

    class Meta:
        model = EmployeeHealthProfile

        fields = [
            'employee',
            'date_of_birth',
            'gender',
            'blood_group',
            'emergency_contact_name',
            'emergency_contact_number',
            'date_of_joining',
            'work_shift',
            'employment_type',
            'job_role',
            'work_area',
            'health_profile_status',
            'is_under_health_surveillance',
            'is_active',
        ]

        widgets = {
            'employee': forms.Select(
                attrs={
                    'class': 'form-control-custom',
                }
            ),
            'date_of_birth': forms.DateInput(
                attrs={
                    'class': 'form-control-custom',
                    'type': 'date',
                }
            ),
            'gender': forms.Select(
                attrs={
                    'class': 'form-control-custom',
                }
            ),
            'blood_group': forms.Select(
                attrs={
                    'class': 'form-control-custom',
                }
            ),
            'emergency_contact_name': forms.TextInput(
                attrs={
                    'class': 'form-control-custom',
                    'placeholder': 'Enter emergency contact name',
                }
            ),
            'emergency_contact_number': forms.TextInput(
                attrs={
                    'class': 'form-control-custom',
                    'placeholder': 'Enter emergency contact number',
                }
            ),
            'date_of_joining': forms.DateInput(
                attrs={
                    'class': 'form-control-custom',
                    'type': 'date',
                }
            ),
            'work_shift': forms.TextInput(
                attrs={
                    'class': 'form-control-custom',
                    'placeholder': 'Enter work shift',
                }
            ),
            'employment_type': forms.Select(
                attrs={
                    'class': 'form-control-custom',
                }
            ),
            'job_role': forms.TextInput(
                attrs={
                    'class': 'form-control-custom',
                    'placeholder': 'Enter job role',
                }
            ),
            'work_area': forms.TextInput(
                attrs={
                    'class': 'form-control-custom',
                    'placeholder': 'Enter work area',
                }
            ),
            'health_profile_status': forms.Select(
                attrs={
                    'class': 'form-control-custom',
                }
            ),
            'is_under_health_surveillance': forms.CheckboxInput(
                attrs={
                    'class': 'custom-checkbox',
                }
            ),
            'is_active': forms.CheckboxInput(
                attrs={
                    'class': 'custom-checkbox',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['employee'].queryset = (
            self.fields['employee']
            .queryset
            .filter(is_active_employee=True)
            .order_by('employee_id')
        )

        self.fields['employee'].label = 'Employee'

        self.fields['employee'].empty_label = 'Select Employee'

    def clean_emergency_contact_number(self):
        number = self.cleaned_data.get('emergency_contact_number')

        if number:
            number = number.strip()

            if len(number) < 7:
                raise forms.ValidationError(
                    'Please enter a valid emergency contact number.'
                )

        return number

    def clean(self):
        cleaned_data = super().clean()

        employee = cleaned_data.get('employee')
        date_of_birth = cleaned_data.get('date_of_birth')
        date_of_joining = cleaned_data.get('date_of_joining')

        if date_of_birth and date_of_joining:
            if date_of_joining <= date_of_birth:
                raise forms.ValidationError(
                    'Date of Joining must be after Date of Birth.'
                )

        # Prevent duplicate health profiles for the same employee.
        if employee:
            existing_profile = EmployeeHealthProfile.objects.filter(
                employee=employee
            )

            if self.instance.pk:
                existing_profile = existing_profile.exclude(
                    pk=self.instance.pk
                )

            if existing_profile.exists():
                raise forms.ValidationError(
                    'An Employee Health Profile already exists for this employee.'
                )

        return cleaned_data




# =============================================
# MedicalExaminationForm - Captures employee medical examination details, findings and follow-up information
# =============================================
class MedicalExaminationForm(forms.ModelForm):
    class Meta:
        model = MedicalExamination
        fields = [
            'employee_health_profile',
            'examination_type',
            'examination_date',
            'purpose',
            'medical_professional',
            'medical_facility',
            'job_role',
            'work_area',
            'general_findings',
            'abnormal_findings',
            'recommendations',
            'follow_up_required',
            'follow_up_date',
            'status',
        ]
        widgets = {
            'employee_health_profile': forms.Select(attrs={
                'class': 'form-control-custom',
                'id': 'id_employee_health_profile'
            }),
            'examination_type': forms.Select(attrs={
                'class': 'form-control-custom'
            }),
            'examination_date': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date'
            }),
            'purpose': forms.Select(attrs={
                'class': 'form-control-custom'
            }),
            'medical_professional': forms.Select(attrs={
                'class': 'form-control-custom'
            }),
            'medical_facility': forms.Select(attrs={
                'class': 'form-control-custom'
            }),
            'job_role': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'id': 'id_job_role',
                'placeholder': 'Enter job role'
            }),
            'work_area': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'id': 'id_work_area',
                'placeholder': 'Enter work area'
            }),
            'general_findings': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 4,
                'placeholder': 'Enter general medical findings'
            }),
            'abnormal_findings': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 4,
                'placeholder': 'Enter abnormal findings, if any'
            }),
            'recommendations': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 4,
                'placeholder': 'Enter medical recommendations'
            }),
            'follow_up_required': forms.CheckboxInput(attrs={
                'class': 'custom-checkbox',
                'id': 'followUpRequired'
            }),
            'follow_up_date': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control-custom'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['employee_health_profile'].queryset = (
            EmployeeHealthProfile.objects
            .select_related('employee')
            .filter(is_active=True)
            .order_by('employee__employee_id')
        )

        self.fields['employee_health_profile'].label = 'Employee'
        self.fields['employee_health_profile'].empty_label = 'Select Employee'

        self.fields['employee_health_profile'].label_from_instance = (
            lambda profile:
            f"{profile.employee.employee_id} - "
            f"{profile.employee.get_full_name() or profile.employee.username}"
        )

        self.fields['examination_type'].queryset = (
            ExaminationType.objects
            .filter(is_active=True)
            .order_by('name')
        )

        self.fields['medical_professional'].queryset = (
            MedicalProfessional.objects
            .filter(is_active=True)
            .order_by('name')
        )

        self.fields['medical_facility'].queryset = (
            MedicalFacility.objects
            .filter(is_active=True)
            .order_by('name')
        )


    def clean(self):
        cleaned_data = super().clean()

        follow_up_required = cleaned_data.get('follow_up_required')
        follow_up_date = cleaned_data.get('follow_up_date')
        examination_date = cleaned_data.get('examination_date')
        employee_health_profile = cleaned_data.get('employee_health_profile')

        if follow_up_required and not follow_up_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date is required when Follow-up is required.'
            )

        if not follow_up_required and follow_up_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date should be empty when Follow-up is not required.'
            )

        if examination_date and follow_up_date:
            if follow_up_date < examination_date:
                self.add_error(
                    'follow_up_date',
                    'Follow-up Date cannot be before the Examination Date.'
                )

        if employee_health_profile and not employee_health_profile.is_active:
            self.add_error(
                'employee_health_profile',
                'The selected Employee Health Profile is inactive.'
            )

        if employee_health_profile:
            if not cleaned_data.get('job_role'):
                cleaned_data['job_role'] = employee_health_profile.job_role

            if not cleaned_data.get('work_area'):
                cleaned_data['work_area'] = employee_health_profile.work_area

        return cleaned_data



# =============================================
# MedicalTestResultForm - Captures medical test results, findings, recommendations and follow-up information
# =============================================
class MedicalTestResultForm(forms.ModelForm):
    class Meta:
        model = MedicalTestResult
        fields = [
            'medical_examination',
            'medical_test',
            'test_date',
            'result_value',
            'unit',
            'reference_range',
            'result_status',
            'findings',
            'recommendations',
            'doctor_comments',
            'attachment',
            'follow_up_required',
            'follow_up_date',
        ]
        widgets = {
            'medical_examination': forms.Select(attrs={
                'class': 'form-control-custom',
                'id': 'id_medical_examination'
            }),
            'medical_test': forms.Select(attrs={
                'class': 'form-control-custom'
            }),
            'test_date': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date'
            }),
            'result_value': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter test result value'
            }),
            'unit': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'e.g. mg/dL, mmHg, dB'
            }),
            'reference_range': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter reference range'
            }),
            'result_status': forms.Select(attrs={
                'class': 'form-control-custom'
            }),
            'findings': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 4,
                'placeholder': 'Enter test findings'
            }),
            'recommendations': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 4,
                'placeholder': 'Enter recommendations'
            }),
            'doctor_comments': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 4,
                'placeholder': 'Enter doctor comments'
            }),
            'attachment': forms.ClearableFileInput(attrs={
                'class': 'form-control-custom'
            }),
            'follow_up_required': forms.CheckboxInput(attrs={
                'class': 'custom-checkbox',
                'id': 'followUpRequired'
            }),
            'follow_up_date': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['medical_examination'].queryset = (
            MedicalExamination.objects
            .select_related(
                'employee_health_profile',
                'employee_health_profile__employee',
                'examination_type'
            )
            .order_by('-examination_date', '-id')
        )

        self.fields['medical_examination'].label = 'Medical Examination'
        self.fields['medical_examination'].empty_label = 'Select Medical Examination'

        self.fields['medical_examination'].label_from_instance = (
            lambda examination:
            f"{examination.employee_health_profile.employee.employee_id} - "
            f"{examination.employee_health_profile.employee.get_full_name() or examination.employee_health_profile.employee.username} - "
            f"{examination.examination_type.name} - "
            f"{examination.examination_date}"
        )

        self.fields['medical_test'].queryset = (
            MedicalTest.objects
            .filter(is_active=True)
            .order_by('name')
        )

    def clean(self):
        cleaned_data = super().clean()

        test_date = cleaned_data.get('test_date')
        follow_up_required = cleaned_data.get('follow_up_required')
        follow_up_date = cleaned_data.get('follow_up_date')
        medical_examination = cleaned_data.get('medical_examination')

        if follow_up_required and not follow_up_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date is required when Follow-up is required.'
            )

        if not follow_up_required and follow_up_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date should be empty when Follow-up is not required.'
            )

        if test_date and follow_up_date and follow_up_date < test_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date cannot be before the Test Date.'
            )

        if medical_examination:
            if medical_examination.status == 'CANCELLED':
                self.add_error(
                    'medical_examination',
                    'Test results cannot be added to a cancelled medical examination.'
                )

        return cleaned_data




# =============================================
# FitnessToWorkForm - Captures employee fitness assessment, validity, restrictions and follow-up information
# =============================================
class FitnessToWorkForm(forms.ModelForm):
    class Meta:
        model = FitnessToWork
        fields = [
            'medical_examination',
            'assessment_type',
            'assessment_date',
            'fitness_status',
            'valid_from',
            'valid_until',
            'restrictions',
            'medical_findings',
            'work_recommendations',
            'doctor_comments',
            'follow_up_required',
            'follow_up_date',
            'status',
        ]
        widgets = {
            'medical_examination': forms.Select(attrs={
                'class': 'form-control-custom',
                'id': 'id_medical_examination'
            }),
            'assessment_type': forms.Select(attrs={
                'class': 'form-control-custom',
                'id': 'id_assessment_type'
            }),
            'assessment_date': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date',
                'id': 'id_assessment_date'
            }),
            'fitness_status': forms.Select(attrs={
                'class': 'form-control-custom',
                'id': 'id_fitness_status'
            }),
            'valid_from': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date',
                'id': 'id_valid_from'
            }),
            'valid_until': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date',
                'id': 'id_valid_until'
            }),
            'restrictions': forms.SelectMultiple(attrs={
                'class': 'form-control-custom',
                'id': 'id_restrictions',
                'size': '5'
            }),
            'medical_findings': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 4,
                'placeholder': 'Enter relevant medical findings'
            }),
            'work_recommendations': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 4,
                'placeholder': 'Enter work recommendations'
            }),
            'doctor_comments': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 4,
                'placeholder': 'Enter doctor comments'
            }),
            'follow_up_required': forms.CheckboxInput(attrs={
                'class': 'custom-checkbox',
                'id': 'followUpRequired'
            }),
            'follow_up_date': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date',
                'id': 'id_follow_up_date'
            }),
            'status': forms.CheckboxInput(attrs={
                'class': 'custom-checkbox',
                'id': 'id_status'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['medical_examination'].queryset = (
            MedicalExamination.objects
            .select_related(
                'employee_health_profile',
                'employee_health_profile__employee',
                'examination_type',
                'medical_professional',
                'medical_facility'
            )
            .exclude(status='CANCELLED')
            .order_by('-examination_date', '-id')
        )

        self.fields['medical_examination'].label = 'Medical Examination'
        self.fields['medical_examination'].empty_label = 'Select Medical Examination'
        self.fields['medical_examination'].label_from_instance = (
            lambda examination:
            f"{examination.employee_health_profile.employee.employee_id} - "
            f"{examination.employee_health_profile.employee.get_full_name() or examination.employee_health_profile.employee.username} - "
            f"{examination.examination_type.name} - "
            f"{examination.examination_date}"
        )

        self.fields['restrictions'].queryset = (
            Restriction.objects
            .filter(is_active=True)
            .order_by('name')
        )

    # =============================================
    # FitnessToWorkForm - Validates fitness assessment and synchronizes employee profile from medical examination
    # =============================================
    def clean(self):
        cleaned_data = super().clean()

        medical_examination = cleaned_data.get('medical_examination')
        assessment_date = cleaned_data.get('assessment_date')
        valid_from = cleaned_data.get('valid_from')
        valid_until = cleaned_data.get('valid_until')
        fitness_status = cleaned_data.get('fitness_status')
        restrictions = cleaned_data.get('restrictions')
        follow_up_required = cleaned_data.get('follow_up_required')
        follow_up_date = cleaned_data.get('follow_up_date')

        if medical_examination:
            if medical_examination.status == 'CANCELLED':
                self.add_error(
                    'medical_examination',
                    'Fitness assessment cannot be created for a cancelled medical examination.'
                )

            existing_assessment = FitnessToWork.objects.filter(
                medical_examination=medical_examination
            )

            if self.instance.pk:
                existing_assessment = existing_assessment.exclude(
                    pk=self.instance.pk
                )

            if existing_assessment.exists():
                self.add_error(
                    'medical_examination',
                    'A Fitness to Work assessment already exists for this medical examination.'
                )

        if assessment_date and valid_from:
            if valid_from < assessment_date:
                self.add_error(
                    'valid_from',
                    'Valid From date cannot be before the Assessment Date.'
                )

        if valid_from and valid_until:
            if valid_until < valid_from:
                self.add_error(
                    'valid_until',
                    'Valid Until date cannot be before the Valid From date.'
                )

        if fitness_status == 'FIT_WITH_RESTRICTIONS' and not restrictions:
            self.add_error(
                'restrictions',
                'At least one restriction is required when the employee is Fit With Restrictions.'
            )

        if follow_up_required and not follow_up_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date is required when Follow-up is required.'
            )

        if not follow_up_required and follow_up_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date should be empty when Follow-up is not required.'
            )

        if assessment_date and follow_up_date:
            if follow_up_date < assessment_date:
                self.add_error(
                    'follow_up_date',
                    'Follow-up Date cannot be before the Assessment Date.'
                )

        return cleaned_data

    # =============================================
    # FitnessToWorkForm - Assigns employee health profile before Django model validation
    # =============================================
    def _post_clean(self):
        medical_examination = self.cleaned_data.get('medical_examination')

        if medical_examination:
            self.instance.employee_health_profile = (
                medical_examination.employee_health_profile
            )

        super()._post_clean()

    # =============================================
    # FitnessToWorkForm - Saves fitness assessment with synchronized employee health profile
    # =============================================
    def save(self, commit=True):
        instance = super().save(commit=False)

        if instance.medical_examination_id:
            instance.employee_health_profile_id = (
                instance.medical_examination.employee_health_profile_id
            )

        if commit:
            instance.save()
            self.save_m2m()

        return instance
    



# =============================================
# HealthSurveillanceForm - Captures employee health surveillance program, exposure, frequency, required tests and follow-up information
# =============================================
class HealthSurveillanceForm(forms.ModelForm):
    class Meta:
        model = HealthSurveillance
        fields = [
            'employee_health_profile',
            'exposure_type',
            'surveillance_name',
            'surveillance_frequency',
            'start_date',
            'next_due_date',
            'end_date',
            'responsible_medical_professional',
            'medical_facility',
            'health_objectives',
            'required_tests',
            'remarks',
            'status',
            'is_active',
        ]
        widgets = {
            'employee_health_profile': forms.Select(attrs={
                'class': 'form-control-custom',
                'id': 'id_employee_health_profile'
            }),
            'exposure_type': forms.Select(attrs={
                'class': 'form-control-custom',
                'id': 'id_exposure_type'
            }),
            'surveillance_name': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter surveillance program name'
            }),
            'surveillance_frequency': forms.Select(attrs={
                'class': 'form-control-custom',
                'id': 'id_surveillance_frequency'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date',
                'id': 'id_start_date'
            }),
            'next_due_date': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date',
                'id': 'id_next_due_date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date',
                'id': 'id_end_date'
            }),
            'responsible_medical_professional': forms.Select(attrs={
                'class': 'form-control-custom'
            }),
            'medical_facility': forms.Select(attrs={
                'class': 'form-control-custom'
            }),
            'health_objectives': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 4,
                'placeholder': 'Enter health surveillance objectives'
            }),
            'required_tests': forms.SelectMultiple(attrs={
                'class': 'form-control-custom',
                'size': '6'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 4,
                'placeholder': 'Enter additional remarks'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control-custom',
                'id': 'id_status'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'custom-checkbox',
                'id': 'id_is_active'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['employee_health_profile'].queryset = (
            EmployeeHealthProfile.objects
            .select_related('employee')
            .filter(is_active=True)
            .order_by('employee__employee_id')
        )

        self.fields['employee_health_profile'].label = 'Employee'
        self.fields['employee_health_profile'].empty_label = 'Select Employee'
        self.fields['employee_health_profile'].label_from_instance = (
            lambda profile:
            f"{profile.employee.employee_id} - "
            f"{profile.employee.get_full_name() or profile.employee.username}"
        )

        self.fields['exposure_type'].queryset = (
            ExposureType.objects
            .filter(is_active=True)
            .order_by('name')
        )

        self.fields['responsible_medical_professional'].queryset = (
            MedicalProfessional.objects
            .filter(is_active=True)
            .order_by('name')
        )

        self.fields['medical_facility'].queryset = (
            MedicalFacility.objects
            .filter(is_active=True)
            .order_by('name')
        )

        self.fields['required_tests'].queryset = (
            MedicalTest.objects
            .filter(is_active=True)
            .order_by('name')
        )

        self.fields['exposure_type'].label = 'Exposure Type'
        self.fields['responsible_medical_professional'].label = 'Responsible Medical Professional'
        self.fields['medical_facility'].label = 'Medical Facility'
        self.fields['required_tests'].label = 'Required Medical Tests'

    # =============================================
    # HealthSurveillanceForm - Validates surveillance dates and employee health profile
    # =============================================
    def clean(self):
        cleaned_data = super().clean()

        employee_health_profile = cleaned_data.get('employee_health_profile')
        start_date = cleaned_data.get('start_date')
        next_due_date = cleaned_data.get('next_due_date')
        end_date = cleaned_data.get('end_date')

        if employee_health_profile and not employee_health_profile.is_active:
            self.add_error(
                'employee_health_profile',
                'The selected Employee Health Profile is inactive.'
            )

        if start_date and next_due_date:
            if next_due_date < start_date:
                self.add_error(
                    'next_due_date',
                    'Next Due Date cannot be before the Start Date.'
                )

        if start_date and end_date:
            if end_date < start_date:
                self.add_error(
                    'end_date',
                    'End Date cannot be before the Start Date.'
                )

        if end_date and next_due_date:
            if next_due_date > end_date:
                self.add_error(
                    'next_due_date',
                    'Next Due Date cannot be after the End Date.'
                )

        return cleaned_data




# =============================================
# EmployeeExposureForm - Captures employee occupational exposure details
# =============================================
class EmployeeExposureForm(forms.ModelForm):
    class Meta:
        model = EmployeeExposure
        fields = [
            'employee_health_profile',
            'exposure_type',
            'exposure_name',
            'exposure_source',
            'work_area',
            'job_role',
            'exposure_start_date',
            'exposure_end_date',
            'exposure_frequency',
            'exposure_duration',
            'exposure_level',
            'control_measures',
            'ppe_used',
            'health_surveillance_required',
            'health_surveillance',
            'remarks',
            'status',
            'is_active',
        ]
        widgets = {
            'employee_health_profile': forms.Select(attrs={
                'class': 'form-control-custom',
                'id': 'id_employee_health_profile'
            }),
            'exposure_type': forms.Select(attrs={
                'class': 'form-control-custom',
                'id': 'id_exposure_type'
            }),
            'exposure_name': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter exposure name'
            }),
            'exposure_source': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'e.g. Press Machine, Welding Process, Chemical Storage'
            }),
            'work_area': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter work area'
            }),
            'job_role': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter job role'
            }),
            'exposure_start_date': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date'
            }),
            'exposure_end_date': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date'
            }),
            'exposure_frequency': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'e.g. Daily, Weekly, Occasional'
            }),
            'exposure_duration': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'e.g. 7 Hours/Shift'
            }),
            'exposure_level': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'e.g. 92 dB(A), 5 mg/m³'
            }),
            'control_measures': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 4,
                'placeholder': 'Enter engineering, administrative or other control measures'
            }),
            'ppe_used': forms.TextInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'e.g. Ear Plug, Respirator, Gloves'
            }),
            'health_surveillance_required': forms.CheckboxInput(attrs={
                'class': 'custom-checkbox',
                'id': 'id_health_surveillance_required'
            }),
            'health_surveillance': forms.Select(attrs={
                'class': 'form-control-custom',
                'id': 'id_health_surveillance'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 4,
                'placeholder': 'Enter additional remarks'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control-custom'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'custom-checkbox'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['employee_health_profile'].queryset = (
            EmployeeHealthProfile.objects
            .select_related('employee')
            .filter(is_active=True)
            .order_by('employee__employee_id')
        )

        self.fields['employee_health_profile'].label = 'Employee'
        self.fields['employee_health_profile'].empty_label = 'Select Employee'

        self.fields['employee_health_profile'].label_from_instance = (
            lambda profile:
            f"{profile.employee.employee_id} - "
            f"{profile.employee.get_full_name() or profile.employee.username}"
        )

        self.fields['exposure_type'].queryset = (
            ExposureType.objects
            .filter(is_active=True)
            .order_by('name')
        )

        self.fields['exposure_type'].label = 'Exposure Type'
        self.fields['exposure_type'].empty_label = 'Select Exposure Type'

        self.fields['health_surveillance'].queryset = (
            HealthSurveillance.objects
            .none()
        )

        if self.instance.pk and self.instance.employee_health_profile_id:
            self.fields['health_surveillance'].queryset = (
                HealthSurveillance.objects
                .select_related('exposure_type')
                .filter(
                    employee_health_profile_id=self.instance.employee_health_profile_id,
                    is_active=True,
                    status='ACTIVE'
                )
                .order_by('-start_date', '-id')
            )

        self.fields['health_surveillance'].label = 'Health Surveillance'
        self.fields['health_surveillance'].required = False
        self.fields['health_surveillance'].empty_label = 'Select Health Surveillance'

        self.fields['health_surveillance'].label_from_instance = (
            lambda surveillance:
            f"{surveillance.employee_health_profile.employee.employee_id} - "
            f"{surveillance.surveillance_name} - "
            f"{surveillance.exposure_type.name}"
        )

    # =============================================
    # EmployeeExposureForm - Validates exposure and surveillance relationship
    # =============================================
    def clean(self):
        cleaned_data = super().clean()

        employee_health_profile = cleaned_data.get(
            'employee_health_profile'
        )
        exposure_start_date = cleaned_data.get(
            'exposure_start_date'
        )
        exposure_end_date = cleaned_data.get(
            'exposure_end_date'
        )
        health_surveillance_required = cleaned_data.get(
            'health_surveillance_required'
        )
        health_surveillance = cleaned_data.get(
            'health_surveillance'
        )

        if employee_health_profile and not employee_health_profile.is_active:
            self.add_error(
                'employee_health_profile',
                'The selected Employee Health Profile is inactive.'
            )

        if exposure_start_date and exposure_end_date:
            if exposure_end_date < exposure_start_date:
                self.add_error(
                    'exposure_end_date',
                    'Exposure End Date cannot be before the Exposure Start Date.'
                )

        if health_surveillance_required and not health_surveillance:
            self.add_error(
                'health_surveillance',
                'Health Surveillance is required when surveillance is marked as required.'
            )

        if health_surveillance and employee_health_profile:
            if (
                health_surveillance.employee_health_profile_id
                != employee_health_profile.id
            ):
                self.add_error(
                    'health_surveillance',
                    'Selected Health Surveillance must belong to the same employee.'
                )

        return cleaned_data





class MedicalFollowUpForm(forms.ModelForm):
    class Meta:
        model=MedicalFollowUp
        fields=[
            'employee_health_profile',
            'medical_examination',
            'medical_test_result',
            'fitness_assessment',
            'health_surveillance',
            'exposure',
            'follow_up_type',
            'title',
            'description',
            'scheduled_date',
            'completed_date',
            'priority',
            'assigned_medical_professional',
            'medical_facility',
            'outcome',
            'recommendations',
            'remarks',
            'status',
            'is_active',
        ]
        widgets={
            'employee_health_profile':forms.Select(attrs={'class':'form-control-custom','id':'id_employee_health_profile'}),
            'medical_examination':forms.Select(attrs={'class':'form-control-custom','id':'id_medical_examination'}),
            'medical_test_result':forms.Select(attrs={'class':'form-control-custom','id':'id_medical_test_result'}),
            'fitness_assessment':forms.Select(attrs={'class':'form-control-custom','id':'id_fitness_assessment'}),
            'health_surveillance':forms.Select(attrs={'class':'form-control-custom','id':'id_health_surveillance'}),
            'exposure':forms.Select(attrs={'class':'form-control-custom','id':'id_exposure'}),
            'follow_up_type':forms.Select(attrs={'class':'form-control-custom'}),
            'title':forms.TextInput(attrs={'class':'form-control-custom','placeholder':'Enter follow-up title'}),
            'description':forms.Textarea(attrs={'class':'form-control-custom','rows':4,'placeholder':'Enter follow-up description'}),
            'scheduled_date':forms.DateInput(attrs={'class':'form-control-custom','type':'date'}),
            'completed_date':forms.DateInput(attrs={'class':'form-control-custom','type':'date'}),
            'priority':forms.Select(attrs={'class':'form-control-custom'}),
            'assigned_medical_professional':forms.Select(attrs={'class':'form-control-custom'}),
            'medical_facility':forms.Select(attrs={'class':'form-control-custom'}),
            'outcome':forms.Textarea(attrs={'class':'form-control-custom','rows':4,'placeholder':'Enter follow-up outcome'}),
            'recommendations':forms.Textarea(attrs={'class':'form-control-custom','rows':4,'placeholder':'Enter medical recommendations'}),
            'remarks':forms.Textarea(attrs={'class':'form-control-custom','rows':4,'placeholder':'Enter additional remarks'}),
            'status':forms.Select(attrs={'class':'form-control-custom'}),
            'is_active':forms.CheckboxInput(attrs={'class':'custom-checkbox'}),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['employee_health_profile'].queryset=EmployeeHealthProfile.objects.select_related('employee').filter(is_active=True).order_by('employee__employee_id')
        self.fields['employee_health_profile'].label='Employee'
        self.fields['employee_health_profile'].empty_label='Select Employee'
        self.fields['employee_health_profile'].label_from_instance=lambda profile:f"{profile.employee.employee_id} - {profile.employee.get_full_name() or profile.employee.username}"
        self.fields['medical_examination'].queryset=MedicalExamination.objects.select_related('employee_health_profile__employee').order_by('-examination_date','-id')
        self.fields['medical_test_result'].queryset=MedicalTestResult.objects.select_related('medical_examination__employee_health_profile__employee','medical_test').order_by('-test_date','-id')
        self.fields['fitness_assessment'].queryset=FitnessToWork.objects.select_related('employee_health_profile__employee').order_by('-assessment_date','-id')
        self.fields['health_surveillance'].queryset=HealthSurveillance.objects.select_related('employee_health_profile__employee','exposure_type').filter(is_active=True).order_by('-start_date','-id')
        self.fields['exposure'].queryset=EmployeeExposure.objects.select_related('employee_health_profile__employee','exposure_type').order_by('-exposure_start_date','-id')
        self.fields['assigned_medical_professional'].queryset=MedicalProfessional.objects.filter(is_active=True).order_by('name')
        self.fields['assigned_medical_professional'].empty_label='Select Medical Professional'
        self.fields['medical_facility'].queryset=MedicalFacility.objects.filter(is_active=True).order_by('name')
        self.fields['medical_facility'].empty_label='Select Medical Facility'

    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get('employee_health_profile')
        scheduled_date = cleaned_data.get('scheduled_date')
        completed_date = cleaned_data.get('completed_date')
        status = cleaned_data.get('status')
        outcome = cleaned_data.get('outcome')
        if employee and not employee.is_active:
            self.add_error(
                'employee_health_profile',
                'The selected Employee Health Profile is inactive.'
            )
        if scheduled_date and completed_date and completed_date < scheduled_date:
            self.add_error(
                'completed_date',
                'Completed Date cannot be before the Scheduled Date.'
            )
        if status == 'COMPLETED' and not completed_date:
            self.add_error(
                'completed_date',
                'Completed Date is required when the follow-up is marked as Completed.'
            )
        if status == 'COMPLETED' and not outcome:
            self.add_error(
                'outcome',
                'Outcome is required when the follow-up is marked as Completed.'
            )
        references = [
            ('medical_examination', 'Medical Examination'),
            ('medical_test_result', 'Medical Test Result'),
            ('fitness_assessment', 'Fitness Assessment'),
            ('health_surveillance', 'Health Surveillance'),
            ('exposure', 'Exposure'),
        ]
        for field_name, label in references:
            obj = cleaned_data.get(field_name)
            if obj and employee:
                profile_id = None
                if field_name == 'medical_test_result':
                    profile_id = obj.medical_examination.employee_health_profile_id
                elif field_name == 'medical_examination':
                    profile_id = obj.employee_health_profile_id
                else:
                    profile_id = obj.employee_health_profile_id
                if profile_id != employee.id:
                    self.add_error(
                        field_name,
                        f'{label} must belong to the selected employee.'
                    )
        return cleaned_data




class EmployeeVaccinationForm(forms.ModelForm):
    class Meta:
        model=EmployeeVaccination
        fields=[
            'employee_health_profile',
            'vaccination',
            'dose_number',
            'vaccination_date',
            'next_due_date',
            'expiry_date',
            'dose_status',
            'vaccination_status',
            'medical_professional',
            'medical_facility',
            'batch_number',
            'manufacturer',
            'certificate_number',
            'attachment',
            'adverse_reaction',
            'adverse_reaction_details',
            'remarks',
        ]
        widgets={
            'employee_health_profile':forms.Select(attrs={'class':'form-control-custom','id':'id_employee_health_profile'}),
            'vaccination':forms.Select(attrs={'class':'form-control-custom','id':'id_vaccination'}),
            'dose_number':forms.NumberInput(attrs={'class':'form-control-custom','min':'1','placeholder':'Enter dose number'}),
            'vaccination_date':forms.DateInput(attrs={'class':'form-control-custom','type':'date'}),
            'next_due_date':forms.DateInput(attrs={'class':'form-control-custom','type':'date'}),
            'expiry_date':forms.DateInput(attrs={'class':'form-control-custom','type':'date'}),
            'dose_status':forms.Select(attrs={'class':'form-control-custom'}),
            'vaccination_status':forms.Select(attrs={'class':'form-control-custom'}),
            'medical_professional':forms.Select(attrs={'class':'form-control-custom'}),
            'medical_facility':forms.Select(attrs={'class':'form-control-custom'}),
            'batch_number':forms.TextInput(attrs={'class':'form-control-custom','placeholder':'Enter batch number'}),
            'manufacturer':forms.TextInput(attrs={'class':'form-control-custom','placeholder':'Enter manufacturer'}),
            'certificate_number':forms.TextInput(attrs={'class':'form-control-custom','placeholder':'Enter certificate number'}),
            'attachment':forms.ClearableFileInput(attrs={'class':'form-control-custom'}),
            'adverse_reaction':forms.CheckboxInput(attrs={'class':'custom-checkbox','id':'id_adverse_reaction'}),
            'adverse_reaction_details':forms.Textarea(attrs={'class':'form-control-custom','rows':3,'placeholder':'Enter adverse reaction details'}),
            'remarks':forms.Textarea(attrs={'class':'form-control-custom','rows':4,'placeholder':'Enter additional remarks'}),
        }
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['employee_health_profile'].queryset=EmployeeHealthProfile.objects.select_related('employee').filter(is_active=True).order_by('employee__employee_id')
        self.fields['employee_health_profile'].label='Employee'
        self.fields['employee_health_profile'].empty_label='Select Employee'
        self.fields['employee_health_profile'].label_from_instance=lambda profile:f"{profile.employee.employee_id} - {profile.employee.get_full_name() or profile.employee.username}"
        self.fields['vaccination'].queryset=Vaccination.objects.filter(is_active=True).order_by('name')
        self.fields['vaccination'].label='Vaccination'
        self.fields['vaccination'].empty_label='Select Vaccination'
        self.fields['medical_professional'].queryset=MedicalProfessional.objects.filter(is_active=True).order_by('name')
        self.fields['medical_professional'].empty_label='Select Medical Professional'
        self.fields['medical_facility'].queryset=MedicalFacility.objects.filter(is_active=True).order_by('name')
        self.fields['medical_facility'].empty_label='Select Medical Facility'
    def clean(self):
        cleaned_data=super().clean()
        employee=cleaned_data.get('employee_health_profile')
        vaccination=cleaned_data.get('vaccination')
        vaccination_date=cleaned_data.get('vaccination_date')
        next_due_date=cleaned_data.get('next_due_date')
        expiry_date=cleaned_data.get('expiry_date')
        dose_number=cleaned_data.get('dose_number')
        adverse_reaction=cleaned_data.get('adverse_reaction')
        adverse_reaction_details=cleaned_data.get('adverse_reaction_details')
        if employee and not employee.is_active:
            self.add_error('employee_health_profile','The selected Employee Health Profile is inactive.')
        if vaccination_date and next_due_date and next_due_date < vaccination_date:
            self.add_error('next_due_date','Next Due Date cannot be before the Vaccination Date.')
        if vaccination_date and expiry_date and expiry_date < vaccination_date:
            self.add_error('expiry_date','Expiry Date cannot be before the Vaccination Date.')
        if vaccination and dose_number:
            recommended_doses=vaccination.recommended_doses
            if recommended_doses and dose_number > recommended_doses:
                self.add_error('dose_number',f'Dose Number cannot be greater than the recommended {recommended_doses} dose(s).')
        if adverse_reaction and not adverse_reaction_details:
            self.add_error('adverse_reaction_details','Please provide details when an adverse reaction is reported.')
        if not adverse_reaction and adverse_reaction_details:
            self.add_error('adverse_reaction_details','Adverse reaction details should be empty when no adverse reaction is reported.')
        return cleaned_data



class EmployeeOccupationalDiseaseForm(forms.ModelForm):
    class Meta:
        model=EmployeeOccupationalDisease
        fields=[
            'employee_health_profile',
            'health_condition',
            'reported_date',
            'diagnosis_date',
            'disease_status',
            'severity',
            'symptoms',
            'diagnosis_details',
            'exposure_related',
            'exposure',
            'medical_professional',
            'medical_facility',
            'work_area',
            'job_role',
            'treatment_details',
            'work_restrictions',
            'follow_up_required',
            'follow_up_date',
            'investigation_required',
            'investigation_findings',
            'corrective_actions',
            'remarks',
            'attachment',
            'status',
        ]
        widgets={
            'employee_health_profile':forms.Select(attrs={
                'class':'form-control-custom',
                'id':'id_employee_health_profile'
            }),
            'health_condition':forms.Select(attrs={
                'class':'form-control-custom',
                'id':'id_health_condition'
            }),
            'reported_date':forms.DateInput(attrs={
                'class':'form-control-custom',
                'type':'date'
            }),
            'diagnosis_date':forms.DateInput(attrs={
                'class':'form-control-custom',
                'type':'date'
            }),
            'disease_status':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'severity':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'symptoms':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':4,
                'placeholder':'Enter reported symptoms'
            }),
            'diagnosis_details':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':4,
                'placeholder':'Enter diagnosis details'
            }),
            'exposure_related':forms.CheckboxInput(attrs={
                'class':'custom-checkbox',
                'id':'id_exposure_related'
            }),
            'exposure':forms.Select(attrs={
                'class':'form-control-custom',
                'id':'id_exposure'
            }),
            'medical_professional':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'medical_facility':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'work_area':forms.TextInput(attrs={
                'class':'form-control-custom',
                'placeholder':'Enter work area'
            }),
            'job_role':forms.TextInput(attrs={
                'class':'form-control-custom',
                'placeholder':'Enter job role'
            }),
            'treatment_details':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':4,
                'placeholder':'Enter treatment details'
            }),
            'work_restrictions':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':4,
                'placeholder':'Enter work restrictions'
            }),
            'follow_up_required':forms.CheckboxInput(attrs={
                'class':'custom-checkbox',
                'id':'id_follow_up_required'
            }),
            'follow_up_date':forms.DateInput(attrs={
                'class':'form-control-custom',
                'type':'date'
            }),
            'investigation_required':forms.CheckboxInput(attrs={
                'class':'custom-checkbox',
                'id':'id_investigation_required'
            }),
            'investigation_findings':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':4,
                'placeholder':'Enter investigation findings'
            }),
            'corrective_actions':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':4,
                'placeholder':'Enter corrective actions'
            }),
            'remarks':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':4,
                'placeholder':'Enter additional remarks'
            }),
            'attachment':forms.ClearableFileInput(attrs={
                'class':'form-control-custom'
            }),
            'status':forms.Select(attrs={
                'class':'form-control-custom'
            }),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.fields['employee_health_profile'].queryset=EmployeeHealthProfile.objects.select_related(
            'employee'
        ).filter(
            is_active=True
        ).order_by(
            'employee__employee_id'
        )

        self.fields['employee_health_profile'].label='Employee'
        self.fields['employee_health_profile'].empty_label='Select Employee'
        self.fields['employee_health_profile'].label_from_instance=lambda profile:f"{profile.employee.employee_id} - {profile.employee.get_full_name() or profile.employee.username}"

        self.fields['health_condition'].queryset=HealthCondition.objects.filter(
            is_active=True
        ).order_by('name')
        self.fields['health_condition'].label='Health Condition'
        self.fields['health_condition'].empty_label='Select Health Condition'

        self.fields['exposure'].queryset=EmployeeExposure.objects.select_related(
            'employee_health_profile__employee',
            'exposure_type'
        ).filter(
            is_active=True
        ).order_by('-exposure_start_date')
        self.fields['exposure'].label='Exposure Record'
        self.fields['exposure'].required=False
        self.fields['exposure'].empty_label='Select Exposure Record'

        self.fields['medical_professional'].queryset=MedicalProfessional.objects.filter(
            is_active=True
        ).order_by('name')
        self.fields['medical_professional'].label='Medical Professional'
        self.fields['medical_professional'].required=False
        self.fields['medical_professional'].empty_label='Select Medical Professional'

        self.fields['medical_facility'].queryset=MedicalFacility.objects.filter(
            is_active=True
        ).order_by('name')
        self.fields['medical_facility'].label='Medical Facility'
        self.fields['medical_facility'].required=False
        self.fields['medical_facility'].empty_label='Select Medical Facility'

        self.fields['reported_date'].label='Reported Date'
        self.fields['diagnosis_date'].label='Diagnosis Date'
        self.fields['disease_status'].label='Disease Status'
        self.fields['severity'].label='Severity'
        self.fields['symptoms'].label='Symptoms'
        self.fields['diagnosis_details'].label='Diagnosis Details'
        self.fields['exposure_related'].label='Exposure Related'
        self.fields['work_area'].label='Work Area'
        self.fields['job_role'].label='Job Role'
        self.fields['treatment_details'].label='Treatment Details'
        self.fields['work_restrictions'].label='Work Restrictions'
        self.fields['follow_up_required'].label='Follow-up Required'
        self.fields['follow_up_date'].label='Follow-up Date'
        self.fields['investigation_required'].label='Investigation Required'
        self.fields['investigation_findings'].label='Investigation Findings'
        self.fields['corrective_actions'].label='Corrective Actions'
        self.fields['remarks'].label='Remarks'
        self.fields['attachment'].label='Medical / Supporting Document'
        self.fields['status'].label='Record Status'

    def clean(self):
        cleaned_data=super().clean()

        employee=cleaned_data.get('employee_health_profile')
        reported_date=cleaned_data.get('reported_date')
        diagnosis_date=cleaned_data.get('diagnosis_date')
        exposure_related=cleaned_data.get('exposure_related')
        exposure=cleaned_data.get('exposure')
        follow_up_required=cleaned_data.get('follow_up_required')
        follow_up_date=cleaned_data.get('follow_up_date')

        if employee and not employee.is_active:
            self.add_error(
                'employee_health_profile',
                'The selected Employee Health Profile is inactive.'
            )

        if diagnosis_date and reported_date and diagnosis_date < reported_date:
            self.add_error(
                'diagnosis_date',
                'Diagnosis Date cannot be before the Reported Date.'
            )

        if follow_up_required and not follow_up_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date is required when Follow-up is required.'
            )

        if not follow_up_required and follow_up_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date should be empty when Follow-up is not required.'
            )

        if follow_up_date and reported_date and follow_up_date < reported_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date cannot be before the Reported Date.'
            )

        if exposure_related and not exposure:
            self.add_error(
                'exposure',
                'Exposure Record is required when Exposure Related is selected.'
            )

        if not exposure_related and exposure:
            self.add_error(
                'exposure',
                'Exposure Record should be empty when Exposure Related is not selected.'
            )

        if employee and exposure:
            if exposure.employee_health_profile_id != employee.id:
                self.add_error(
                    'exposure',
                    'Selected Exposure must belong to the same employee.'
                )

        return cleaned_data




class HealthIncidentForm(forms.ModelForm):
    class Meta:
        model=HealthIncident
        fields=[
            'employee_health_profile','incident_date','incident_time',
            'incident_type','severity','incident_location','work_area',
            'job_role','incident_description','symptoms','immediate_action',
            'treatment_provided','medical_professional','medical_facility',
            'occupational_disease','exposure','hospitalization_required',
            'hospitalization_details','work_restriction_required',
            'work_restriction_details','follow_up_required','follow_up_date',
            'investigation_required','investigation_findings',
            'corrective_actions','attachment','status','remarks',
        ]
        widgets={
            'employee_health_profile':forms.Select(attrs={'class':'form-control-custom'}),
            'incident_date':forms.DateInput(attrs={'class':'form-control-custom','type':'date'}),
            'incident_time':forms.TimeInput(attrs={'class':'form-control-custom','type':'time'}),
            'incident_type':forms.Select(attrs={'class':'form-control-custom'}),
            'severity':forms.Select(attrs={'class':'form-control-custom'}),
            'incident_location':forms.TextInput(attrs={'class':'form-control-custom','placeholder':'Enter incident location'}),
            'work_area':forms.TextInput(attrs={'class':'form-control-custom','placeholder':'Enter work area'}),
            'job_role':forms.TextInput(attrs={'class':'form-control-custom','placeholder':'Enter job role'}),
            'incident_description':forms.Textarea(attrs={'class':'form-control-custom','rows':4,'placeholder':'Describe the health incident...'}),
            'symptoms':forms.Textarea(attrs={'class':'form-control-custom','rows':3,'placeholder':'Enter symptoms observed/reported...'}),
            'immediate_action':forms.Textarea(attrs={'class':'form-control-custom','rows':3,'placeholder':'Enter immediate action taken...'}),
            'treatment_provided':forms.Textarea(attrs={'class':'form-control-custom','rows':3,'placeholder':'Enter treatment provided...'}),
            'medical_professional':forms.Select(attrs={'class':'form-control-custom'}),
            'medical_facility':forms.Select(attrs={'class':'form-control-custom'}),
            'occupational_disease':forms.Select(attrs={'class':'form-control-custom'}),
            'exposure':forms.Select(attrs={'class':'form-control-custom'}),
            'hospitalization_required':forms.CheckboxInput(attrs={'class':'custom-checkbox'}),
            'hospitalization_details':forms.Textarea(attrs={'class':'form-control-custom','rows':3,'placeholder':'Enter hospitalization details...'}),
            'work_restriction_required':forms.CheckboxInput(attrs={'class':'custom-checkbox'}),
            'work_restriction_details':forms.Textarea(attrs={'class':'form-control-custom','rows':3,'placeholder':'Enter work restriction details...'}),
            'follow_up_required':forms.CheckboxInput(attrs={'class':'custom-checkbox'}),
            'follow_up_date':forms.DateInput(attrs={'class':'form-control-custom','type':'date'}),
            'investigation_required':forms.CheckboxInput(attrs={'class':'custom-checkbox'}),
            'investigation_findings':forms.Textarea(attrs={'class':'form-control-custom','rows':4,'placeholder':'Enter investigation findings...'}),
            'corrective_actions':forms.Textarea(attrs={'class':'form-control-custom','rows':4,'placeholder':'Enter corrective actions...'}),
            'attachment':forms.ClearableFileInput(attrs={'class':'form-control-custom'}),
            'status':forms.Select(attrs={'class':'form-control-custom'}),
            'remarks':forms.Textarea(attrs={'class':'form-control-custom','rows':3,'placeholder':'Enter remarks...'}),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.fields['employee_health_profile'].queryset=EmployeeHealthProfile.objects.filter(
            is_active=True
        ).select_related(
            'employee'
        ).order_by(
            'employee__employee_id'
        )

        self.fields['employee_health_profile'].label='Employee'

        self.fields['employee_health_profile'].label_from_instance=lambda obj: (
            f"{obj.employee.employee_id or obj.employee.username} - "
            f"{obj.employee.get_full_name() or obj.employee.username}"
        )

        self.fields['medical_professional'].queryset=MedicalProfessional.objects.filter(
            is_active=True
        ).order_by('name')

        self.fields['medical_facility'].queryset=MedicalFacility.objects.filter(
            is_active=True
        ).order_by('name')

        self.fields['occupational_disease'].queryset=EmployeeOccupationalDisease.objects.select_related(
            'employee_health_profile__employee',
            'health_condition'
        ).order_by('-reported_date','-id')

        self.fields['exposure'].queryset=EmployeeExposure.objects.filter(
            is_active=True
        ).select_related(
            'employee_health_profile__employee',
            'exposure_type'
        ).order_by('-exposure_start_date','-id')

        self.fields['occupational_disease'].label='Occupational Disease'
        self.fields['exposure'].label='Exposure Record'
        self.fields['medical_professional'].label='Medical Professional'
        self.fields['medical_facility'].label='Medical Facility'

        self.fields['occupational_disease'].label_from_instance=lambda obj: (
            f"{obj.employee_health_profile.employee.employee_id or obj.employee_health_profile.employee.username} - "
            f"{obj.health_condition.name} - "
            f"{obj.reported_date.strftime('%d %b %Y')}"
        )

        self.fields['exposure'].label_from_instance=lambda obj: (
            f"{obj.employee_health_profile.employee.employee_id or obj.employee_health_profile.employee.username} - "
            f"{obj.exposure_name}"
        )

    def clean(self):
        cleaned_data=super().clean()

        employee_profile=cleaned_data.get('employee_health_profile')
        incident_date=cleaned_data.get('incident_date')
        follow_up_required=cleaned_data.get('follow_up_required')
        follow_up_date=cleaned_data.get('follow_up_date')
        hospitalization_required=cleaned_data.get('hospitalization_required')
        hospitalization_details=cleaned_data.get('hospitalization_details')
        work_restriction_required=cleaned_data.get('work_restriction_required')
        work_restriction_details=cleaned_data.get('work_restriction_details')
        investigation_required=cleaned_data.get('investigation_required')
        investigation_findings=cleaned_data.get('investigation_findings')
        corrective_actions=cleaned_data.get('corrective_actions')
        occupational_disease=cleaned_data.get('occupational_disease')
        exposure=cleaned_data.get('exposure')

        if employee_profile and not employee_profile.is_active:
            self.add_error(
                'employee_health_profile',
                'The selected Employee Health Profile is inactive.'
            )

        if incident_date and follow_up_date and follow_up_date < incident_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date cannot be before the Incident Date.'
            )

        if follow_up_required and not follow_up_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date is required when Follow-up is required.'
            )

        if not follow_up_required and follow_up_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date should be empty when Follow-up is not required.'
            )

        if hospitalization_required and not hospitalization_details.strip():
            self.add_error(
                'hospitalization_details',
                'Hospitalization details are required when hospitalization is selected.'
            )

        if not hospitalization_required and hospitalization_details:
            self.add_error(
                'hospitalization_details',
                'Hospitalization details should be empty when hospitalization is not required.'
            )

        if work_restriction_required and not work_restriction_details.strip():
            self.add_error(
                'work_restriction_details',
                'Work restriction details are required when work restriction is selected.'
            )

        if not work_restriction_required and work_restriction_details:
            self.add_error(
                'work_restriction_details',
                'Work restriction details should be empty when work restriction is not required.'
            )

        if investigation_required and not investigation_findings.strip():
            self.add_error(
                'investigation_findings',
                'Investigation Findings are required when investigation is selected.'
            )

        if investigation_required and not corrective_actions.strip():
            self.add_error(
                'corrective_actions',
                'Corrective Actions are required when investigation is selected.'
            )

        if not investigation_required and (investigation_findings or corrective_actions):
            self.add_error(
                'investigation_findings',
                'Investigation details should be empty when investigation is not required.'
            )

        if employee_profile and occupational_disease:
            if occupational_disease.employee_health_profile_id != employee_profile.id:
                self.add_error(
                    'occupational_disease',
                    'Selected Occupational Disease must belong to the same employee.'
                )

        if employee_profile and exposure:
            if exposure.employee_health_profile_id != employee_profile.id:
                self.add_error(
                    'exposure',
                    'Selected Exposure must belong to the same employee.'
                )

        return cleaned_data




class ReturnToWorkForm(forms.ModelForm):
    class Meta:
        model=ReturnToWork
        fields=[
            'employee_health_profile',
            'absence_start_date',
            'absence_end_date',
            'expected_return_date',
            'actual_return_date',
            'return_reason',
            'reason_details',
            'medical_examination',
            'fitness_assessment',
            'health_incident',
            'occupational_disease',
            'medical_professional',
            'medical_facility',
            'fitness_status',
            'work_restrictions',
            'restriction_details',
            'temporary_restriction_until',
            'job_role',
            'work_area',
            'supervisor_comments',
            'employee_comments',
            'medical_recommendations',
            'follow_up_required',
            'follow_up_date',
            'status',
            'remarks',
            'attachment',
        ]
        widgets={
            'employee_health_profile':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'absence_start_date':forms.DateInput(attrs={
                'class':'form-control-custom',
                'type':'date'
            }),
            'absence_end_date':forms.DateInput(attrs={
                'class':'form-control-custom',
                'type':'date'
            }),
            'expected_return_date':forms.DateInput(attrs={
                'class':'form-control-custom',
                'type':'date'
            }),
            'actual_return_date':forms.DateInput(attrs={
                'class':'form-control-custom',
                'type':'date'
            }),
            'return_reason':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'reason_details':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':3,
                'placeholder':'Enter details about the reason for absence...'
            }),
            'medical_examination':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'fitness_assessment':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'health_incident':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'occupational_disease':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'medical_professional':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'medical_facility':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'fitness_status':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'work_restrictions':forms.SelectMultiple(attrs={
                'class':'form-control-custom',
                'size':'5'
            }),
            'restriction_details':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':3,
                'placeholder':'Enter work restriction details...'
            }),
            'temporary_restriction_until':forms.DateInput(attrs={
                'class':'form-control-custom',
                'type':'date'
            }),
            'job_role':forms.TextInput(attrs={
                'class':'form-control-custom',
                'placeholder':'Enter job role'
            }),
            'work_area':forms.TextInput(attrs={
                'class':'form-control-custom',
                'placeholder':'Enter work area'
            }),
            'supervisor_comments':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':3,
                'placeholder':'Enter supervisor comments...'
            }),
            'employee_comments':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':3,
                'placeholder':'Enter employee comments...'
            }),
            'medical_recommendations':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':3,
                'placeholder':'Enter medical recommendations...'
            }),
            'follow_up_required':forms.CheckboxInput(attrs={
                'class':'custom-checkbox'
            }),
            'follow_up_date':forms.DateInput(attrs={
                'class':'form-control-custom',
                'type':'date'
            }),
            'status':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'remarks':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':3,
                'placeholder':'Enter remarks...'
            }),
            'attachment':forms.ClearableFileInput(attrs={
                'class':'form-control-custom'
            }),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.fields['employee_health_profile'].queryset=EmployeeHealthProfile.objects.filter(
            is_active=True
        ).select_related(
            'employee'
        ).order_by(
            'employee__employee_id'
        )

        self.fields['employee_health_profile'].label='Employee'

        self.fields['employee_health_profile'].label_from_instance=lambda obj: (
            f"{obj.employee.employee_id or obj.employee.username} - "
            f"{obj.employee.get_full_name() or obj.employee.username}"
        )

        self.fields['medical_professional'].queryset=MedicalProfessional.objects.filter(
            is_active=True
        ).order_by('name')

        self.fields['medical_facility'].queryset=MedicalFacility.objects.filter(
            is_active=True
        ).order_by('name')

        self.fields['medical_examination'].queryset=MedicalExamination.objects.select_related(
            'employee_health_profile__employee',
            'examination_type'
        ).order_by(
            '-examination_date',
            '-id'
        )

        self.fields['fitness_assessment'].queryset=FitnessToWork.objects.select_related(
            'employee_health_profile__employee'
        ).order_by(
            '-assessment_date',
            '-id'
        )

        self.fields['health_incident'].queryset=HealthIncident.objects.select_related(
            'employee_health_profile__employee'
        ).order_by(
            '-incident_date',
            '-id'
        )

        self.fields['occupational_disease'].queryset=EmployeeOccupationalDisease.objects.select_related(
            'employee_health_profile__employee',
            'health_condition'
        ).order_by(
            '-reported_date',
            '-id'
        )

        self.fields['medical_examination'].label='Medical Examination'
        self.fields['fitness_assessment'].label='Fitness Assessment'
        self.fields['health_incident'].label='Health Incident'
        self.fields['occupational_disease'].label='Occupational Disease'
        self.fields['medical_professional'].label='Medical Professional'
        self.fields['medical_facility'].label='Medical Facility'
        self.fields['work_restrictions'].label='Work Restrictions'

        self.fields['medical_examination'].label_from_instance=lambda obj: (
            f"{obj.employee_health_profile.employee.employee_id or obj.employee_health_profile.employee.username} - "
            f"{obj.examination_type.name} - "
            f"{obj.examination_date.strftime('%d %b %Y')}"
        )

        self.fields['fitness_assessment'].label_from_instance=lambda obj: (
            f"{obj.employee_health_profile.employee.employee_id or obj.employee_health_profile.employee.username} - "
            f"{obj.get_fitness_status_display()} - "
            f"{obj.assessment_date.strftime('%d %b %Y')}"
        )

        self.fields['health_incident'].label_from_instance=lambda obj: (
            f"{obj.employee_health_profile.employee.employee_id or obj.employee_health_profile.employee.username} - "
            f"{obj.get_incident_type_display()} - "
            f"{obj.incident_date.strftime('%d %b %Y')}"
        )

        self.fields['occupational_disease'].label_from_instance=lambda obj: (
            f"{obj.employee_health_profile.employee.employee_id or obj.employee_health_profile.employee.username} - "
            f"{obj.health_condition.name} - "
            f"{obj.reported_date.strftime('%d %b %Y')}"
        )

    def clean(self):
        cleaned_data=super().clean()

        employee_profile=cleaned_data.get('employee_health_profile')
        absence_start_date=cleaned_data.get('absence_start_date')
        absence_end_date=cleaned_data.get('absence_end_date')
        expected_return_date=cleaned_data.get('expected_return_date')
        actual_return_date=cleaned_data.get('actual_return_date')
        medical_examination=cleaned_data.get('medical_examination')
        fitness_assessment=cleaned_data.get('fitness_assessment')
        health_incident=cleaned_data.get('health_incident')
        occupational_disease=cleaned_data.get('occupational_disease')
        fitness_status=cleaned_data.get('fitness_status')
        work_restrictions=cleaned_data.get('work_restrictions')
        restriction_details=cleaned_data.get('restriction_details')
        temporary_restriction_until=cleaned_data.get('temporary_restriction_until')
        follow_up_required=cleaned_data.get('follow_up_required')
        follow_up_date=cleaned_data.get('follow_up_date')
        status=cleaned_data.get('status')

        if employee_profile and not employee_profile.is_active:
            self.add_error(
                'employee_health_profile',
                'The selected Employee Health Profile is inactive.'
            )

        if absence_start_date and absence_end_date:
            if absence_end_date < absence_start_date:
                self.add_error(
                    'absence_end_date',
                    'Absence End Date cannot be before Absence Start Date.'
                )

        if absence_start_date and expected_return_date:
            if expected_return_date < absence_start_date:
                self.add_error(
                    'expected_return_date',
                    'Expected Return Date cannot be before Absence Start Date.'
                )

        if absence_start_date and actual_return_date:
            if actual_return_date < absence_start_date:
                self.add_error(
                    'actual_return_date',
                    'Actual Return Date cannot be before Absence Start Date.'
                )

        if expected_return_date and actual_return_date:
            if actual_return_date < expected_return_date:
                self.add_error(
                    'actual_return_date',
                    'Actual Return Date cannot be before Expected Return Date.'
                )

        if follow_up_required and not follow_up_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date is required when Follow-up is required.'
            )

        if not follow_up_required and follow_up_date:
            self.add_error(
                'follow_up_date',
                'Follow-up Date should be empty when Follow-up is not required.'
            )

        if follow_up_date and expected_return_date:
            if follow_up_date < expected_return_date:
                self.add_error(
                    'follow_up_date',
                    'Follow-up Date cannot be before Expected Return Date.'
                )

        if temporary_restriction_until and actual_return_date:
            if temporary_restriction_until < actual_return_date:
                self.add_error(
                    'temporary_restriction_until',
                    'Restriction end date cannot be before Actual Return Date.'
                )

        if medical_examination and employee_profile:
            if medical_examination.employee_health_profile_id != employee_profile.id:
                self.add_error(
                    'medical_examination',
                    'Medical Examination must belong to the selected employee.'
                )

        if fitness_assessment and employee_profile:
            if fitness_assessment.employee_health_profile_id != employee_profile.id:
                self.add_error(
                    'fitness_assessment',
                    'Fitness Assessment must belong to the selected employee.'
                )

        if health_incident and employee_profile:
            if health_incident.employee_health_profile_id != employee_profile.id:
                self.add_error(
                    'health_incident',
                    'Health Incident must belong to the selected employee.'
                )

        if occupational_disease and employee_profile:
            if occupational_disease.employee_health_profile_id != employee_profile.id:
                self.add_error(
                    'occupational_disease',
                    'Occupational Disease must belong to the selected employee.'
                )

        if status == 'APPROVED_WITH_RESTRICTIONS':

            if not work_restrictions and not restriction_details.strip():
                self.add_error(
                    'restriction_details',
                    'Work restrictions are required when Return to Work is approved with restrictions.'
                )

            if not fitness_status:
                self.add_error(
                    'fitness_status',
                    'Fitness Status is required when Return to Work is approved with restrictions.'
                )

        if status == 'APPROVED' and fitness_status == 'UNFIT':
            self.add_error(
                'fitness_status',
                'An Unfit fitness status cannot be used with an Approved Return to Work status.'
            )

        if status == 'APPROVED_WITH_RESTRICTIONS' and fitness_status == 'UNFIT':
            self.add_error(
                'fitness_status',
                'Fitness Status cannot be Unfit when Return to Work is approved with restrictions.'
            )

        if status == 'COMPLETED' and not actual_return_date:
            self.add_error(
                'actual_return_date',
                'Actual Return Date is required when the Return to Work record is completed.'
            )

        return cleaned_data






class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model=MedicalRecord
        fields=[
            'employee_health_profile',
            'record_title',
            'record_type',
            'record_date',
            'medical_examination',
            'medical_test_result',
            'fitness_assessment',
            'vaccination',
            'occupational_disease',
            'health_incident',
            'return_to_work',
            'medical_professional',
            'medical_facility',
            'document',
            'document_number',
            'description',
            'confidential',
            'record_status',
            'expiry_date',
            'remarks',
        ]
        widgets={
            'employee_health_profile':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'record_title':forms.TextInput(attrs={
                'class':'form-control-custom',
                'placeholder':'Enter medical record title'
            }),
            'record_type':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'record_date':forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class':'form-control-custom',
                    'type':'date'
                }
            ),
            'medical_examination':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'medical_test_result':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'fitness_assessment':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'vaccination':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'occupational_disease':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'health_incident':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'return_to_work':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'medical_professional':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'medical_facility':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'document':forms.ClearableFileInput(attrs={
                'class':'form-control-custom'
            }),
            'document_number':forms.TextInput(attrs={
                'class':'form-control-custom',
                'placeholder':'Enter document number'
            }),
            'description':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':4,
                'placeholder':'Enter document description'
            }),
            'confidential':forms.CheckboxInput(attrs={
                'class':'custom-checkbox'
            }),
            'record_status':forms.Select(attrs={
                'class':'form-control-custom'
            }),
            'expiry_date':forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class':'form-control-custom',
                    'type':'date'
                }
            ),
            'remarks':forms.Textarea(attrs={
                'class':'form-control-custom',
                'rows':4,
                'placeholder':'Enter remarks'
            }),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.fields['employee_health_profile'].queryset=(
            EmployeeHealthProfile.objects
            .filter(is_active=True)
            .select_related('employee')
            .order_by('employee__employee_id','employee__username')
        )

        self.fields['medical_examination'].queryset=(
            MedicalExamination.objects
            .select_related(
                'employee_health_profile__employee',
                'examination_type'
            )
            .order_by('-examination_date','-id')
        )

        self.fields['medical_test_result'].queryset=(
            MedicalTestResult.objects
            .select_related(
                'medical_examination__employee_health_profile__employee',
                'medical_test'
            )
            .order_by('-test_date','-id')
        )

        self.fields['fitness_assessment'].queryset=(
            FitnessToWork.objects
            .select_related(
                'employee_health_profile__employee'
            )
            .order_by('-assessment_date','-id')
        )

        self.fields['vaccination'].queryset=(
            EmployeeVaccination.objects
            .select_related(
                'employee_health_profile__employee',
                'vaccination'
            )
            .exclude(
                vaccination_status='CANCELLED'
            )
            .order_by('-vaccination_date','-id')
        )

        self.fields['occupational_disease'].queryset=(
            EmployeeOccupationalDisease.objects
            .select_related(
                'employee_health_profile__employee',
                'health_condition'
            )
            .order_by('-reported_date','-id')
        )

        self.fields['health_incident'].queryset=(
            HealthIncident.objects
            .select_related(
                'employee_health_profile__employee'
            )
            .order_by('-incident_date','-id')
        )

        self.fields['return_to_work'].queryset=(
            ReturnToWork.objects
            .select_related(
                'employee_health_profile__employee'
            )
            .order_by('-expected_return_date','-id')
        )

        self.fields['medical_professional'].queryset=(
            MedicalProfessional.objects
            .filter(is_active=True)
            .order_by('name')
        )

        self.fields['medical_facility'].queryset=(
            MedicalFacility.objects
            .filter(is_active=True)
            .order_by('name')
        )

        self.fields['employee_health_profile'].label='Employee'
        self.fields['record_title'].label='Record Title'
        self.fields['record_type'].label='Record Type'
        self.fields['record_date'].label='Record Date'
        self.fields['medical_examination'].label='Medical Examination'
        self.fields['medical_test_result'].label='Medical Test Result'
        self.fields['fitness_assessment'].label='Fitness Assessment'
        self.fields['vaccination'].label='Vaccination'
        self.fields['occupational_disease'].label='Occupational Disease'
        self.fields['health_incident'].label='Health Incident'
        self.fields['return_to_work'].label='Return to Work'
        self.fields['medical_professional'].label='Medical Professional'
        self.fields['medical_facility'].label='Medical Facility'
        self.fields['document'].label='Medical Document'
        self.fields['document_number'].label='Document Number'
        self.fields['description'].label='Description'
        self.fields['confidential'].label='Confidential'
        self.fields['record_status'].label='Record Status'
        self.fields['expiry_date'].label='Expiry Date'
        self.fields['remarks'].label='Remarks'

        self.fields['employee_health_profile'].empty_label='Select Employee'
        self.fields['record_type'].empty_label='Select Record Type'
        self.fields['medical_examination'].empty_label='Select Medical Examination'
        self.fields['medical_test_result'].empty_label='Select Medical Test Result'
        self.fields['fitness_assessment'].empty_label='Select Fitness Assessment'
        self.fields['vaccination'].empty_label='Select Vaccination'
        self.fields['occupational_disease'].empty_label='Select Occupational Disease'
        self.fields['health_incident'].empty_label='Select Health Incident'
        self.fields['return_to_work'].empty_label='Select Return to Work'
        self.fields['medical_professional'].empty_label='Select Medical Professional'
        self.fields['medical_facility'].empty_label='Select Medical Facility'

        def employee_label(obj):
            employee=obj.employee
            employee_id=employee.employee_id or employee.username
            name=employee.get_full_name() or employee.username
            return f'{employee_id} - {name}'

        self.fields['employee_health_profile'].label_from_instance=employee_label

        def examination_label(obj):
            employee=obj.employee_health_profile.employee
            employee_id=employee.employee_id or employee.username
            name=employee.get_full_name() or employee.username
            return f'{employee_id} - {obj.examination_type.name} - {obj.examination_date}'

        self.fields['medical_examination'].label_from_instance=examination_label

        def test_result_label(obj):
            if not obj.medical_examination_id:
                return f'{obj.medical_test.name} - {obj.test_date} - {obj.get_result_status_display()}'

            employee=obj.medical_examination.employee_health_profile.employee
            employee_id=employee.employee_id or employee.username
            return f'{employee_id} - {obj.medical_test.name} - {obj.test_date} - {obj.get_result_status_display()}'

        self.fields['medical_test_result'].label_from_instance=test_result_label

        def fitness_label(obj):
            employee=obj.employee_health_profile.employee
            employee_id=employee.employee_id or employee.username
            return f'{employee_id} - {obj.get_fitness_status_display()} - {obj.assessment_date}'

        self.fields['fitness_assessment'].label_from_instance=fitness_label

        def vaccination_label(obj):
            employee=obj.employee_health_profile.employee
            employee_id=employee.employee_id or employee.username
            return f'{employee_id} - {obj.vaccination.name} - Dose {obj.dose_number}'

        self.fields['vaccination'].label_from_instance=vaccination_label

        def disease_label(obj):
            employee=obj.employee_health_profile.employee
            employee_id=employee.employee_id or employee.username
            return f'{employee_id} - {obj.health_condition.name} - {obj.reported_date}'

        self.fields['occupational_disease'].label_from_instance=disease_label

        def incident_label(obj):
            employee=obj.employee_health_profile.employee
            employee_id=employee.employee_id or employee.username
            return f'{employee_id} - {obj.get_incident_type_display()} - {obj.incident_date}'

        self.fields['health_incident'].label_from_instance=incident_label

        def return_to_work_label(obj):
            employee=obj.employee_health_profile.employee
            employee_id=employee.employee_id or employee.username
            return f'{employee_id} - {obj.get_return_reason_display()} - {obj.expected_return_date}'

        self.fields['return_to_work'].label_from_instance=return_to_work_label

    def clean(self):
        cleaned_data = super().clean()

        employee_profile = cleaned_data.get('employee_health_profile')
        record_date = cleaned_data.get('record_date')
        expiry_date = cleaned_data.get('expiry_date')

        if employee_profile and not employee_profile.is_active:
            self.add_error(
                'employee_health_profile',
                'Only active employee health profiles can be selected.'
            )

        if record_date and expiry_date and expiry_date < record_date:
            self.add_error(
                'expiry_date',
                'Expiry date cannot be earlier than the record date.'
            )

        linked_records = [
            ('medical_examination', cleaned_data.get('medical_examination')),
            ('medical_test_result', cleaned_data.get('medical_test_result')),
            ('fitness_assessment', cleaned_data.get('fitness_assessment')),
            ('vaccination', cleaned_data.get('vaccination')),
            ('occupational_disease', cleaned_data.get('occupational_disease')),
            ('health_incident', cleaned_data.get('health_incident')),
            ('return_to_work', cleaned_data.get('return_to_work')),
        ]

        if employee_profile:
            for field_name, linked_record in linked_records:
                if not linked_record:
                    continue

                linked_employee_id = None

                if field_name == 'medical_test_result':
                    if linked_record.medical_examination_id:
                        linked_employee_id = (
                            linked_record.medical_examination.employee_health_profile_id
                        )

                elif field_name == 'medical_examination':
                    linked_employee_id = (
                        linked_record.employee_health_profile_id
                    )

                elif field_name == 'fitness_assessment':
                    linked_employee_id = (
                        linked_record.employee_health_profile_id
                    )

                elif field_name == 'vaccination':
                    linked_employee_id = (
                        linked_record.employee_health_profile_id
                    )

                elif field_name == 'occupational_disease':
                    linked_employee_id = (
                        linked_record.employee_health_profile_id
                    )

                elif field_name == 'health_incident':
                    linked_employee_id = (
                        linked_record.employee_health_profile_id
                    )

                elif field_name == 'return_to_work':
                    linked_employee_id = (
                        linked_record.employee_health_profile_id
                    )

                if linked_employee_id and linked_employee_id != employee_profile.id:
                    self.add_error(
                        field_name,
                        'This record belongs to a different employee.'
                    )

        return cleaned_data



class HealthCampForm(forms.ModelForm):
    class Meta:
        model=HealthCamp
        fields=[
            'camp_name',
            'camp_type',
            'camp_mode',
            'plant',
            'location',
            'camp_date',
            'start_time',
            'end_time',
            'organizer',
            'medical_facility',
            'lead_medical_professional',
            'objectives',
            'services_provided',
            'target_employee_count',
            'registered_employee_count',
            'attended_employee_count',
            'findings_count',
            'referral_count',
            'follow_up_required_count',
            'summary',
            'remarks',
            'status',
            'is_active',
        ]
        widgets={
            'camp_name':forms.TextInput(attrs={
                'class':'form-control form-control-custom'
            }),
            'camp_type':forms.Select(attrs={
                'class':'form-control form-control-custom'
            }),
            'camp_mode':forms.Select(attrs={
                'class':'form-control form-control-custom'
            }),
            'plant':forms.Select(attrs={
                'class':'form-control form-control-custom'
            }),
            'location':forms.TextInput(attrs={
                'class':'form-control form-control-custom'
            }),
            'camp_date':forms.DateInput(attrs={
                'type':'date',
                'class':'form-control form-control-custom'
            }),
            'start_time':forms.TimeInput(attrs={
                'type':'time',
                'class':'form-control form-control-custom'
            }),
            'end_time':forms.TimeInput(attrs={
                'type':'time',
                'class':'form-control form-control-custom'
            }),
            'organizer':forms.TextInput(attrs={
                'class':'form-control form-control-custom'
            }),
            'medical_facility':forms.Select(attrs={
                'class':'form-control form-control-custom'
            }),
            'lead_medical_professional':forms.Select(attrs={
                'class':'form-control form-control-custom'
            }),
            'objectives':forms.Textarea(attrs={
                'class':'form-control form-control-custom',
                'rows':3
            }),
            'services_provided':forms.Textarea(attrs={
                'class':'form-control form-control-custom',
                'rows':3
            }),
            'target_employee_count':forms.NumberInput(attrs={
                'class':'form-control form-control-custom',
                'min':0
            }),
            'registered_employee_count':forms.NumberInput(attrs={
                'class':'form-control form-control-custom',
                'min':0
            }),
            'attended_employee_count':forms.NumberInput(attrs={
                'class':'form-control form-control-custom',
                'min':0
            }),
            'findings_count':forms.NumberInput(attrs={
                'class':'form-control form-control-custom',
                'min':0
            }),
            'referral_count':forms.NumberInput(attrs={
                'class':'form-control form-control-custom',
                'min':0
            }),
            'follow_up_required_count':forms.NumberInput(attrs={
                'class':'form-control form-control-custom',
                'min':0
            }),
            'summary':forms.Textarea(attrs={
                'class':'form-control form-control-custom',
                'rows':4
            }),
            'remarks':forms.Textarea(attrs={
                'class':'form-control form-control-custom',
                'rows':3
            }),
            'status':forms.Select(attrs={
                'class':'form-control form-control-custom'
            }),
            'is_active':forms.CheckboxInput(attrs={
                'class':'custom-checkbox'
            }),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.fields['plant'].queryset=Plant.objects.all().order_by('name')

        self.fields['medical_facility'].queryset=MedicalFacility.objects.filter(
            is_active=True
        ).order_by('name')

        self.fields['lead_medical_professional'].queryset=MedicalProfessional.objects.filter(
            is_active=True
        ).order_by('name')

        self.fields['plant'].label_from_instance=lambda obj: obj.name

        self.fields['medical_facility'].label_from_instance=lambda obj: (
            f'{obj.name} ({obj.get_facility_type_display()})'
        )

        self.fields['lead_medical_professional'].label_from_instance=lambda obj: (
            f'{obj.name} ({obj.get_professional_type_display()})'
        )

    def clean(self):
        cleaned_data=super().clean()

        camp_date=cleaned_data.get('camp_date')
        start_time=cleaned_data.get('start_time')
        end_time=cleaned_data.get('end_time')

        target_employee_count=cleaned_data.get(
            'target_employee_count'
        ) or 0

        registered_employee_count=cleaned_data.get(
            'registered_employee_count'
        ) or 0

        attended_employee_count=cleaned_data.get(
            'attended_employee_count'
        ) or 0

        findings_count=cleaned_data.get(
            'findings_count'
        ) or 0

        referral_count=cleaned_data.get(
            'referral_count'
        ) or 0

        follow_up_required_count=cleaned_data.get(
            'follow_up_required_count'
        ) or 0

        if start_time and end_time:
            if end_time <= start_time:
                self.add_error(
                    'end_time',
                    'End time must be later than start time.'
                )

        if registered_employee_count > target_employee_count and target_employee_count:
            self.add_error(
                'registered_employee_count',
                'Registered employees cannot exceed the target employee count.'
            )

        if attended_employee_count > registered_employee_count:
            self.add_error(
                'attended_employee_count',
                'Attended employees cannot exceed registered employees.'
            )

        if findings_count > attended_employee_count:
            self.add_error(
                'findings_count',
                'Findings count cannot exceed attended employees.'
            )

        if referral_count > findings_count:
            self.add_error(
                'referral_count',
                'Referral count cannot exceed findings count.'
            )

        if follow_up_required_count > findings_count:
            self.add_error(
                'follow_up_required_count',
                'Follow-up count cannot exceed findings count.'
            )

        return cleaned_data


class HealthCampParticipationForm(forms.ModelForm):
    class Meta:
        model=HealthCampParticipation
        fields=[
            'health_camp',
            'employee_health_profile',
            'registration_date',
            'attendance_status',
            'attendance_time',
            'screening_status',
            'screening_findings',
            'abnormal_findings',
            'services_received',
            'medical_advice',
            'referral_required',
            'referral_details',
            'follow_up_required',
            'follow_up_date',
            'follow_up_notes',
            'medical_professional',
            'medical_record',
            'remarks',
        ]
        widgets={
            'health_camp':forms.Select(attrs={'class':'form-control form-control-custom'}),
            'employee_health_profile':forms.Select(attrs={'class':'form-control form-control-custom'}),
            'registration_date':forms.DateInput(attrs={'type':'date','class':'form-control form-control-custom'}),
            'attendance_status':forms.Select(attrs={'class':'form-control form-control-custom'}),
            'attendance_time':forms.TimeInput(attrs={'type':'time','class':'form-control form-control-custom'}),
            'screening_status':forms.Select(attrs={'class':'form-control form-control-custom'}),
            'screening_findings':forms.Textarea(attrs={'class':'form-control form-control-custom','rows':3}),
            'abnormal_findings':forms.Textarea(attrs={'class':'form-control form-control-custom','rows':3}),
            'services_received':forms.Textarea(attrs={'class':'form-control form-control-custom','rows':3}),
            'medical_advice':forms.Textarea(attrs={'class':'form-control form-control-custom','rows':3}),
            'referral_required':forms.CheckboxInput(attrs={'class':'custom-checkbox'}),
            'referral_details':forms.Textarea(attrs={'class':'form-control form-control-custom','rows':3}),
            'follow_up_required':forms.CheckboxInput(attrs={'class':'custom-checkbox'}),
            'follow_up_date':forms.DateInput(attrs={'type':'date','class':'form-control form-control-custom'}),
            'follow_up_notes':forms.Textarea(attrs={'class':'form-control form-control-custom','rows':3}),
            'medical_professional':forms.Select(attrs={'class':'form-control form-control-custom'}),
            'medical_record':forms.Select(attrs={'class':'form-control form-control-custom'}),
            'remarks':forms.Textarea(attrs={'class':'form-control form-control-custom','rows':3}),
        }

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.fields['health_camp'].queryset=HealthCamp.objects.filter(
            is_active=True
        ).order_by('-camp_date')

        self.fields['employee_health_profile'].queryset=EmployeeHealthProfile.objects.filter(
            is_active=True
        ).select_related('employee').order_by(
            'employee__first_name',
            'employee__last_name'
        )

        self.fields['medical_professional'].queryset=MedicalProfessional.objects.filter(
            is_active=True
        ).order_by('name')

        self.fields['medical_record'].queryset=MedicalRecord.objects.select_related(
            'employee_health_profile__employee'
        ).order_by('-record_date','-id')

        self.fields['health_camp'].label_from_instance=lambda obj: (
            f'{obj.camp_code} - {obj.camp_name} - {obj.camp_date}'
        )

        self.fields['employee_health_profile'].label_from_instance=lambda obj: (
            f'{obj.employee.employee_id or obj.employee.username} - '
            f'{obj.employee.get_full_name() or obj.employee.username}'
        )

        self.fields['medical_professional'].label_from_instance=lambda obj: (
            f'{obj.name} ({obj.get_professional_type_display()})'
        )

        self.fields['medical_record'].label_from_instance=lambda obj: (
            f'{obj.record_title} - {obj.record_date} - '
            f'{obj.employee_health_profile.employee.get_full_name() or obj.employee_health_profile.employee.username}'
        )

    def clean(self):
        cleaned_data=super().clean()

        health_camp=cleaned_data.get('health_camp')
        employee_profile=cleaned_data.get('employee_health_profile')
        medical_record=cleaned_data.get('medical_record')

        if health_camp and employee_profile:
            if health_camp.plant_id:
                employee=employee_profile.employee

                if employee.plant_id and employee.plant_id != health_camp.plant_id:
                    self.add_error(
                        'employee_health_profile',
                        'Employee must belong to the selected Health Camp plant.'
                    )

        if medical_record and employee_profile:
            if medical_record.employee_health_profile_id != employee_profile.id:
                self.add_error(
                    'medical_record',
                    'Medical Record must belong to the selected employee.'
                )

        return cleaned_data