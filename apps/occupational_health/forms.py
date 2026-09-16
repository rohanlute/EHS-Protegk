from django import forms
from .models import (
    ExaminationType,MedicalTest,ExposureType,HealthCondition,FitnessStatus,Restriction,
    Vaccination, MedicalProfessional,MedicalFacility,
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