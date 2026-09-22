from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.chemicals.models import Chemical
from .models import (SDS, SDSVersion, SDSReview, SDSSection1, SDSSection2, SDSSection3,
    SDSSection3Ingredient, SDSSection4, SDSSection5, SDSSection6, SDSSection7, SDSSection8,
    SDSSection9, SDSSection10, SDSSection11, SDSSection12, SDSSection13, SDSSection14, 
    SDSSection15, SDSSection16)
from apps.organizations.models import Plant, Zone, Location, SubLocation


class SDSForm(forms.ModelForm):
    """
    Form for creating and updating the main SDS record.
    """

    class Meta:
        model = SDS
        fields = [
            'chemical',
            'product_name',
            'product_identifier',
            'sds_type',

            'manufacturer_name',
            'manufacturer_address',
            'manufacturer_phone',
            'manufacturer_email',

            'supplier_name',
            'supplier_address',
            'supplier_phone',
            'supplier_email',

            'plant',
            'zone',
            'location',
            'sublocation',

            'document',
            'document_name',
            'document_language',

            'issue_date',
            'revision_date',
            'next_review_date',

            'status',
            'is_active',
            'remarks',
        ]

        widgets = {
            'chemical': forms.Select(attrs={
                'class': 'form-control',
            }),

            'product_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter chemical / product name',
            }),

            'product_identifier': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product identifier / code',
            }),

            'sds_type': forms.Select(attrs={
                'class': 'form-control',
            }),

            'manufacturer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter manufacturer name',
            }),

            'manufacturer_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter manufacturer address',
            }),

            'manufacturer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter manufacturer phone',
            }),

            'manufacturer_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter manufacturer email',
            }),

            'supplier_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter supplier name',
            }),

            'supplier_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter supplier address',
            }),

            'supplier_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter supplier phone',
            }),

            'supplier_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter supplier email',
            }),

            'plant': forms.Select(attrs={
                'class': 'form-control',
            }),

            'zone': forms.Select(attrs={
                'class': 'form-control',
            }),

            'location': forms.Select(attrs={
                'class': 'form-control',
            }),

            'sublocation': forms.Select(attrs={
                'class': 'form-control',
            }),

            'document': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf',
            }),

            'document_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional document display name',
            }),

            'document_language': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. English',
            }),

            'issue_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),

            'revision_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),

            'next_review_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),

            'status': forms.Select(attrs={
                'class': 'form-control',
            }),

            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),

            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter remarks',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)

        super().__init__(*args, **kwargs)
        self.fields['chemical'].queryset = Chemical.objects.all().order_by('chemical_name')
        self.fields['chemical'].empty_label = 'Select Chemical'

        # ------------------------------------------------------
        # Empty labels
        # ------------------------------------------------------

        self.fields['plant'].empty_label = 'Select Plant'
        self.fields['zone'].empty_label = 'Select Zone'
        self.fields['location'].empty_label = 'Select Location'
        self.fields['sublocation'].empty_label = 'Select Sub-Location'

        # ------------------------------------------------------
        # Location querysets
        # ------------------------------------------------------

        if self.user:

            assigned_plants = self.user.assigned_plants.filter(
                is_active=True
            )

            # If the user has assigned plants,
            # only show those plants.
            if assigned_plants.exists():

                self.fields['plant'].queryset = assigned_plants

                self.fields['zone'].queryset = Zone.objects.filter(
                    plant__in=assigned_plants,
                    is_active=True
                ).distinct().order_by('name')

                self.fields['location'].queryset = Location.objects.filter(
                    zone__plant__in=assigned_plants,
                    is_active=True
                ).distinct().order_by('name')

                self.fields['sublocation'].queryset = SubLocation.objects.filter(
                    location__zone__plant__in=assigned_plants,
                    is_active=True
                ).distinct().order_by('name')

            else:
                # User has no restricted plant assignment.
                self.fields['plant'].queryset = Plant.objects.filter(
                    is_active=True
                ).order_by('name')

                self.fields['zone'].queryset = Zone.objects.filter(
                    is_active=True
                ).order_by('name')

                self.fields['location'].queryset = Location.objects.filter(
                    is_active=True
                ).order_by('name')

                self.fields['sublocation'].queryset = SubLocation.objects.filter(
                    is_active=True
                ).order_by('name')

        else:
            self.fields['plant'].queryset = Plant.objects.filter(
                is_active=True
            ).order_by('name')

            self.fields['zone'].queryset = Zone.objects.filter(
                is_active=True
            ).order_by('name')

            self.fields['location'].queryset = Location.objects.filter(
                is_active=True
            ).order_by('name')

            self.fields['sublocation'].queryset = SubLocation.objects.filter(
                is_active=True
            ).order_by('name')

        # ------------------------------------------------------
        # Cascading dropdowns during POST
        # ------------------------------------------------------

        if self.data:

            try:
                plant_id = int(self.data.get('plant'))

                self.fields['zone'].queryset = Zone.objects.filter(
                    plant_id=plant_id,
                    is_active=True
                ).order_by('name')

            except (ValueError, TypeError):
                pass

            try:
                zone_id = int(self.data.get('zone'))

                self.fields['location'].queryset = Location.objects.filter(
                    zone_id=zone_id,
                    is_active=True
                ).order_by('name')

            except (ValueError, TypeError):
                pass

            try:
                location_id = int(self.data.get('location'))

                self.fields['sublocation'].queryset = SubLocation.objects.filter(
                    location_id=location_id,
                    is_active=True
                ).order_by('name')

            except (ValueError, TypeError):
                pass

        # ------------------------------------------------------
        # Populate dropdowns when editing
        # ------------------------------------------------------

        elif self.instance and self.instance.pk:

            if self.instance.plant:
                self.fields['zone'].queryset = Zone.objects.filter(
                    plant=self.instance.plant,
                    is_active=True
                ).order_by('name')

            if self.instance.zone:
                self.fields['location'].queryset = Location.objects.filter(
                    zone=self.instance.zone,
                    is_active=True
                ).order_by('name')

            if self.instance.location:
                self.fields['sublocation'].queryset = SubLocation.objects.filter(
                    location=self.instance.location,
                    is_active=True
                ).order_by('name')

        # ------------------------------------------------------
        # Automatically select user's only plant
        # ------------------------------------------------------

        elif self.user:

            assigned_plants = self.user.assigned_plants.filter(
                is_active=True
            )

            if assigned_plants.count() == 1:
                self.initial['plant'] = assigned_plants.first().pk

    # ==========================================================
    # VALIDATION
    # ==========================================================

    def clean(self):
        cleaned_data = super().clean()

        issue_date = cleaned_data.get('issue_date')
        revision_date = cleaned_data.get('revision_date')
        next_review_date = cleaned_data.get('next_review_date')

        # ------------------------------------------------------
        # Date validation
        # ------------------------------------------------------

        if issue_date and issue_date > timezone.now().date():
            self.add_error(
                'issue_date',
                'Issue date cannot be in the future.'
            )

        if revision_date and revision_date > timezone.now().date():
            self.add_error(
                'revision_date',
                'Revision date cannot be in the future.'
            )

        if issue_date and revision_date:
            if revision_date < issue_date:
                self.add_error(
                    'revision_date',
                    'Revision date cannot be before the issue date.'
                )

        if next_review_date and revision_date:
            if next_review_date <= revision_date:
                self.add_error(
                    'next_review_date',
                    'Next review date must be after the revision date.'
                )

        # ------------------------------------------------------
        # Location hierarchy validation
        # ------------------------------------------------------

        plant = cleaned_data.get('plant')
        zone = cleaned_data.get('zone')
        location = cleaned_data.get('location')
        sublocation = cleaned_data.get('sublocation')

        if zone and plant and zone.plant_id != plant.id:
            self.add_error(
                'zone',
                'Selected zone does not belong to the selected plant.'
            )

        if location and zone and location.zone_id != zone.id:
            self.add_error(
                'location',
                'Selected location does not belong to the selected zone.'
            )

        if sublocation and location and sublocation.location_id != location.id:
            self.add_error(
                'sublocation',
                'Selected sub-location does not belong to the selected location.'
            )

        return cleaned_data


# ============================================================
# SDS VERSION FORM
# ============================================================
class SDSVersionForm(forms.ModelForm):
    class Meta:
        model = SDSVersion
        fields = [
            'version_number',
            'revision_number',
            'version_title',
            'document',
            'issue_date',
            'revision_date',
            'effective_date',
            'status',
            'change_summary',
        ]
        widgets = {
            'version_number': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'readonly': 'readonly',
                }
            ),
            'revision_number': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter revision number',
                }
            ),
            'version_title': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter version title',
                }
            ),
            'document': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control',
                    'accept': '.pdf',
                }
            ),
            'issue_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),
            'revision_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),
            'effective_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),
            'status': forms.Select(
                attrs={
                    'class': 'form-control',
                }
            ),
            'change_summary': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Describe what changed in this version...',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.sds = kwargs.pop('sds', None)
        super().__init__(*args, **kwargs)

        if self.sds:
            latest_version = self.sds.versions.order_by(
                '-version_number'
            ).first()

            if latest_version:
                next_version_number = latest_version.version_number + 1
            else:
                next_version_number = 1

            self.fields['version_number'].initial = next_version_number
            self.fields['version_number'].disabled = True

        self.fields['status'].initial = 'DRAFT'
        self.fields['status'].disabled = True

    def clean_version_number(self):
        version_number = self.cleaned_data.get(
            'version_number'
        )

        if not self.sds:
            raise forms.ValidationError(
                'SDS record is required to create a version.'
            )

        latest_version = self.sds.versions.order_by(
            '-version_number'
        ).first()

        expected_version_number = (
            latest_version.version_number + 1
            if latest_version
            else 1
        )

        if version_number != expected_version_number:
            raise forms.ValidationError(
                f'The next version number must be {expected_version_number}.'
            )

        if self.sds.versions.filter(
            version_number=version_number
        ).exists():
            raise forms.ValidationError(
                'This version number already exists for this SDS.'
            )

        return version_number

    def clean(self):
        cleaned_data = super().clean()

        issue_date = cleaned_data.get('issue_date')
        revision_date = cleaned_data.get('revision_date')
        effective_date = cleaned_data.get('effective_date')

        if issue_date and revision_date:
            if revision_date < issue_date:
                self.add_error(
                    'revision_date',
                    'Revision date cannot be earlier than issue date.'
                )

        if issue_date and effective_date:
            if effective_date < issue_date:
                self.add_error(
                    'effective_date',
                    'Effective date cannot be earlier than issue date.'
                )

        if revision_date and effective_date:
            if effective_date < revision_date:
                self.add_error(
                    'effective_date',
                    'Effective date cannot be earlier than revision date.'
                )

        return cleaned_data




# =========================================================
# SDS REVIEW FORM
# =========================================================
class SDSReviewForm(forms.ModelForm):
    class Meta:
        model = SDSReview
        fields = [
            'review_type',
            'status',
            'reviewer',
            'review_remarks',
            'rejection_reason',
        ]
        widgets = {
            'review_type': forms.Select(attrs={
                'class': 'form-control',
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
            }),
            'reviewer': forms.Select(attrs={
                'class': 'form-control',
            }),
            'review_remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter review remarks',
            }),
            'rejection_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter rejection reason',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.sds = kwargs.pop('sds', None)
        self.version = kwargs.pop('version', None)
        super().__init__(*args, **kwargs)

        if self.sds:
            self.instance.sds = self.sds

        if self.version:
            self.instance.version = self.version

        self.fields['status'].choices = [
            ('IN_REVIEW', 'In Review'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
        ]

        self.fields['reviewer'].queryset = self.fields['reviewer'].queryset.filter(
            is_active=True
        )

        self.fields['reviewer'].required = True

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        rejection_reason = cleaned_data.get('rejection_reason')

        if status == 'REJECTED' and not rejection_reason:
            self.add_error(
                'rejection_reason',
                'Rejection reason is required when rejecting an SDS version.'
            )

        return cleaned_data


# =============================================
# SDS Section 1 - Identification Form
# =============================================
class SDSSection1Form(forms.ModelForm):
    class Meta:
        model = SDSSection1
        fields = [
            'product_identifier',
            'recommended_use',
            'restrictions_on_use',
            'manufacturer_name',
            'manufacturer_address',
            'manufacturer_phone',
            'manufacturer_email',
            'manufacturer_website',
            'emergency_contact_name',
            'emergency_contact_number',
            'emergency_contact_email',
            'emergency_contact_available',
            'additional_information',
        ]
        widgets = {
            'product_identifier': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product identifier'
            }),
            'recommended_use': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter recommended use'
            }),
            'restrictions_on_use': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter restrictions on use'
            }),
            'manufacturer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter manufacturer name'
            }),
            'manufacturer_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter manufacturer address'
            }),
            'manufacturer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter manufacturer phone number'
            }),
            'manufacturer_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter manufacturer email'
            }),
            'manufacturer_website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter emergency contact name'
            }),
            'emergency_contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter emergency contact number'
            }),
            'emergency_contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter emergency contact email'
            }),
            'emergency_contact_available': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: 24 Hours / Monday-Friday'
            }),
            'additional_information': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter any additional information'
            }),
        }




# =============================================
# SDS Section 2 - Hazard(s) Identification Form
# =============================================
class SDSSection2Form(forms.ModelForm):
    class Meta:
        model = SDSSection2
        fields = [
            'hazard_classification',
            'signal_word',
            'hazard_statements',
            'precautionary_statements',
            'ghs_pictograms',
            'other_hazards',
            'additional_information',
        ]
        widgets = {
            'hazard_classification': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': (
                        'Enter the classification of the substance '
                        'or mixture.'
                    ),
                }
            ),
            'signal_word': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Example: Danger or Warning',
                }
            ),
            'hazard_statements': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': (
                        'Enter applicable GHS hazard statements.'
                    ),
                }
            ),
            'precautionary_statements': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': (
                        'Enter applicable precautionary statements.'
                    ),
                }
            ),
            'ghs_pictograms': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': (
                        'Enter applicable GHS pictograms or their '
                        'identification.'
                    ),
                }
            ),
            'other_hazards': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': (
                        'Enter hazards not otherwise classified, '
                        'if applicable.'
                    ),
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': (
                        'Enter any additional hazard identification '
                        'information.'
                    ),
                }
            ),
        }



# =============================================
# SDS Section 3 - Composition Form
# =============================================
class SDSSection3Form(forms.ModelForm):
    class Meta:
        model = SDSSection3
        fields = [
            'composition_notes',
            'trade_secret_information',
            'additional_information',
        ]
        widgets = {
            'composition_notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': (
                        'Enter general composition information '
                        'for this SDS.'
                    ),
                }
            ),
            'trade_secret_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': (
                        'Enter trade secret or confidential '
                        'composition information, if applicable.'
                    ),
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': (
                        'Enter any additional composition information.'
                    ),
                }
            ),
        }


# =============================================
# SDS Section 3 - Ingredient / Component Form
# =============================================
class SDSSection3IngredientForm(forms.ModelForm):
    ingredient_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Ingredient / component name',
            }
        )
    )

    display_order = forms.IntegerField(
        required=False,
        initial=1,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': '1',
            }
        )
    )

    class Meta:
        model = SDSSection3Ingredient
        fields = [
            'ingredient_name',
            'cas_number',
            'ec_number',
            'concentration',
            'concentration_range',
            'hazard_classification',
            'notes',
            'display_order',
        ]
        widgets = {
            'cas_number': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Example: 67-64-1',
                }
            ),
            'ec_number': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'EC number, if applicable',
                }
            ),
            'concentration': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Example: 25%',
                }
            ),
            'concentration_range': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Example: 20-30%',
                }
            ),
            'hazard_classification': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': (
                        'Enter the hazard classification '
                        'of this ingredient.'
                    ),
                }
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': (
                        'Enter any additional information '
                        'about this ingredient.'
                    ),
                }
            ),
            'display_order': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': 1,
                    'placeholder': '1',
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        ingredient_name = cleaned_data.get('ingredient_name')
        cas_number = cleaned_data.get('cas_number')
        ec_number = cleaned_data.get('ec_number')
        concentration = cleaned_data.get('concentration')
        concentration_range = cleaned_data.get(
            'concentration_range'
        )
        hazard_classification = cleaned_data.get(
            'hazard_classification'
        )
        notes = cleaned_data.get('notes')

        has_other_data = any([
            cas_number,
            ec_number,
            concentration,
            concentration_range,
            hazard_classification,
            notes,
        ])

        if has_other_data and not ingredient_name:
            self.add_error(
                'ingredient_name',
                'Ingredient / component name is required.'
            )

        return cleaned_data
    

# =============================================
# SDS Section 3 - Ingredient Formset
# =============================================
SDSSection3IngredientFormSet = forms.inlineformset_factory(
    SDSSection3,
    SDSSection3Ingredient,
    form=SDSSection3IngredientForm,
    extra=1,
    can_delete=True,
)


# =============================================
# SDS Section 4 Form - First-Aid Measures
# =============================================
class SDSSection4Form(forms.ModelForm):
    class Meta:
        model = SDSSection4
        fields = [
            'general_first_aid',
            'inhalation',
            'skin_contact',
            'eye_contact',
            'ingestion',
            'most_important_symptoms',
            'medical_attention',
            'first_responder_notes',
            'additional_information',
        ]
        widgets = {
            'general_first_aid': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter general first-aid information...'
                }
            ),
            'inhalation': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter first-aid measures for inhalation exposure...'
                }
            ),
            'skin_contact': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter first-aid measures for skin contact...'
                }
            ),
            'eye_contact': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter first-aid measures for eye contact...'
                }
            ),
            'ingestion': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter first-aid measures for ingestion...'
                }
            ),
            'most_important_symptoms': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter the most important symptoms and effects...'
                }
            ),
            'medical_attention': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter information about immediate medical attention or special treatment...'
                }
            ),
            'first_responder_notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter special notes and precautions for first responders...'
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter any additional first-aid information...'
                }
            ),
        }


# =============================================
# SDS Section 5 Form - Fire-Fighting Measures
# =============================================
class SDSSection5Form(forms.ModelForm):
    class Meta:
        model = SDSSection5
        fields = [
            'suitable_extinguishing_media',
            'unsuitable_extinguishing_media',
            'specific_hazards',
            'hazardous_combustion_products',
            'special_protective_equipment',
            'special_fire_fighting_procedures',
            'additional_information',
        ]
        widgets = {
            'suitable_extinguishing_media': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter suitable extinguishing media...'
                }
            ),
            'unsuitable_extinguishing_media': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter extinguishing media that should not be used...'
                }
            ),
            'specific_hazards': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter specific hazards arising from the chemical during fire...'
                }
            ),
            'hazardous_combustion_products': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter hazardous combustion products...'
                }
            ),
            'special_protective_equipment': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter special protective equipment for firefighters...'
                }
            ),
            'special_fire_fighting_procedures': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter special fire-fighting procedures and precautions...'
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter any additional fire-fighting information...'
                }
            ),
        }


# =============================================
# SDS Section 6 Form - Accidental Release Measures
# =============================================
class SDSSection6Form(forms.ModelForm):
    class Meta:
        model = SDSSection6
        fields = [
            'personal_precautions',
            'emergency_procedures',
            'environmental_precautions',
            'containment_methods',
            'cleanup_methods',
            'other_section_references',
            'additional_information',
        ]
        widgets = {
            'personal_precautions': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter personal precautions for personnel during an accidental release...'
                }
            ),
            'emergency_procedures': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter emergency procedures to be followed during an accidental release...'
                }
            ),
            'environmental_precautions': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter precautions to prevent environmental contamination...'
                }
            ),
            'containment_methods': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter methods and materials for containment...'
                }
            ),
            'cleanup_methods': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter methods and materials for cleanup...'
                }
            ),
            'other_section_references': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter references to other relevant SDS sections...'
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter any additional accidental release information...'
                }
            ),
        }


# =============================================
# SDS Section 7 Form - Handling and Storage
# =============================================
class SDSSection7Form(forms.ModelForm):
    class Meta:
        model = SDSSection7
        fields = [
            'precautions_for_safe_handling',
            'conditions_for_safe_storage',
            'incompatible_materials',
            'storage_temperature',
            'ventilation_requirements',
            'specific_end_use',
            'additional_information',
        ]
        widgets = {
            'precautions_for_safe_handling': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter precautions for safe handling of the chemical...'
                }
            ),
            'conditions_for_safe_storage': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter conditions required for safe storage...'
                }
            ),
            'incompatible_materials': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter materials or substances that should be kept away from the chemical...'
                }
            ),
            'storage_temperature': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter recommended storage temperature or temperature conditions...'
                }
            ),
            'ventilation_requirements': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter ventilation requirements for safe handling and storage...'
                }
            ),
            'specific_end_use': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter any specific end use or use-related requirements...'
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter any additional handling and storage information...'
                }
            ),
        }



# =============================================
# SDS Section 8 Form - Exposure Controls / Personal Protection
# =============================================
class SDSSection8Form(forms.ModelForm):
    class Meta:
        model = SDSSection8
        fields = [
            'occupational_exposure_limits',
            'biological_exposure_limits',
            'appropriate_engineering_controls',
            'ventilation_requirements',
            'respiratory_protection',
            'hand_protection',
            'eye_face_protection',
            'skin_body_protection',
            'thermal_hazards_protection',
            'hygiene_measures',
            'environmental_exposure_controls',
            'additional_information',
        ]
        widgets = {
            'occupational_exposure_limits': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter applicable occupational exposure limits such as TWA, STEL, ceiling limits, etc...'
                }
            ),
            'biological_exposure_limits': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter applicable biological exposure limits or biological monitoring requirements...'
                }
            ),
            'appropriate_engineering_controls': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter appropriate engineering controls such as enclosure, isolation, local exhaust ventilation, etc...'
                }
            ),
            'ventilation_requirements': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter ventilation requirements for safe handling and use...'
                }
            ),
            'respiratory_protection': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter respiratory protection requirements and recommended respirator type...'
                }
            ),
            'hand_protection': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter recommended gloves and hand protection requirements...'
                }
            ),
            'eye_face_protection': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter eye and face protection requirements such as safety goggles or face shield...'
                }
            ),
            'skin_body_protection': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter skin and body protection requirements such as protective clothing, apron, footwear, etc...'
                }
            ),
            'thermal_hazards_protection': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter protection requirements related to thermal hazards...'
                }
            ),
            'hygiene_measures': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter hygiene measures such as washing requirements, contaminated clothing handling, etc...'
                }
            ),
            'environmental_exposure_controls': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter measures for controlling environmental exposure and preventing releases...'
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter any additional exposure control or personal protection information...'
                }
            ),
        }





# =============================================
# SDS Section 9 Form - Physical and Chemical Properties
# =============================================
class SDSSection9Form(forms.ModelForm):
    class Meta:
        model = SDSSection9
        fields = [
            'physical_state',
            'appearance',
            'color',
            'odor',
            'odor_threshold',
            'ph',
            'melting_freezing_point',
            'boiling_point',
            'flash_point',
            'evaporation_rate',
            'flammability',
            'explosive_limits',
            'vapor_pressure',
            'vapor_density',
            'relative_density',
            'solubility',
            'partition_coefficient',
            'auto_ignition_temperature',
            'decomposition_temperature',
            'viscosity',
            'particle_characteristics',
            'additional_information',
        ]
        widgets = {
            'physical_state': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g. Solid, Liquid, Gas'
                }
            ),
            'appearance': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Describe the appearance of the chemical...'
                }
            ),
            'color': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter color...'
                }
            ),
            'odor': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter odor characteristics...'
                }
            ),
            'odor_threshold': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter odor threshold and units, if available...'
                }
            ),
            'ph': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter pH and applicable conditions...'
                }
            ),
            'melting_freezing_point': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter melting/freezing point with units...'
                }
            ),
            'boiling_point': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter initial boiling point or boiling range with units...'
                }
            ),
            'flash_point': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter flash point and test method, if available...'
                }
            ),
            'evaporation_rate': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter evaporation rate and reference, if available...'
                }
            ),
            'flammability': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter flammability characteristics...'
                }
            ),
            'explosive_limits': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter upper/lower explosive or flammability limits...'
                }
            ),
            'vapor_pressure': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter vapor pressure with temperature and units...'
                }
            ),
            'vapor_density': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter vapor density and reference, if available...'
                }
            ),
            'relative_density': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter relative density with applicable temperature...'
                }
            ),
            'solubility': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Enter solubility information...'
                }
            ),
            'partition_coefficient': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter partition coefficient and reference conditions...'
                }
            ),
            'auto_ignition_temperature': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter auto-ignition temperature with units...'
                }
            ),
            'decomposition_temperature': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter decomposition temperature with units...'
                }
            ),
            'viscosity': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter viscosity and units...'
                }
            ),
            'particle_characteristics': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Enter particle characteristics such as particle size or other relevant properties...'
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Enter any additional physical or chemical property information...'
                }
            ),
        }




# =============================================
# SDS Section 10 Form - Stability and Reactivity
# =============================================
class SDSSection10Form(forms.ModelForm):
    class Meta:
        model = SDSSection10
        fields = [
            'reactivity',
            'chemical_stability',
            'possibility_of_hazardous_reactions',
            'conditions_to_avoid',
            'incompatible_materials',
            'hazardous_decomposition_products',
            'additional_information',
        ]
        widgets = {
            'reactivity': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter information about the chemical reactivity...'
                }
            ),
            'chemical_stability': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter information about chemical stability under normal conditions...'
                }
            ),
            'possibility_of_hazardous_reactions': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter information about the possibility of hazardous reactions...'
                }
            ),
            'conditions_to_avoid': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter conditions that should be avoided, such as heat, sparks, moisture, pressure, etc...'
                }
            ),
            'incompatible_materials': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter incompatible materials and substances...'
                }
            ),
            'hazardous_decomposition_products': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter hazardous decomposition products that may be generated...'
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter any additional stability and reactivity information...'
                }
            ),
        }




# =============================================
# SDS Section 11 Form - Toxicological Information
# =============================================
class SDSSection11Form(forms.ModelForm):
    class Meta:
        model = SDSSection11
        fields = [
            'likely_routes_of_exposure',
            'acute_toxicity',
            'skin_corrosion_irritation',
            'serious_eye_damage_irritation',
            'respiratory_skin_sensitization',
            'germ_cell_mutagenicity',
            'carcinogenicity',
            'reproductive_toxicity',
            'stot_single_exposure',
            'stot_repeated_exposure',
            'aspiration_hazard',
            'symptoms_related_to_exposure',
            'delayed_immediate_effects',
            'interactive_effects',
            'numerical_measures_of_toxicity',
            'additional_information',
        ]
        widgets = {
            'likely_routes_of_exposure': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter likely routes of exposure such as inhalation, skin contact, eye contact, or ingestion...'
                }
            ),
            'acute_toxicity': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter available acute toxicity information...'
                }
            ),
            'skin_corrosion_irritation': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter information regarding skin corrosion or irritation...'
                }
            ),
            'serious_eye_damage_irritation': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter information regarding serious eye damage or eye irritation...'
                }
            ),
            'respiratory_skin_sensitization': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter respiratory or skin sensitization information...'
                }
            ),
            'germ_cell_mutagenicity': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter information regarding germ cell mutagenicity...'
                }
            ),
            'carcinogenicity': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter carcinogenicity information and applicable classification...'
                }
            ),
            'reproductive_toxicity': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter reproductive toxicity information...'
                }
            ),
            'stot_single_exposure': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter specific target organ toxicity information following a single exposure...'
                }
            ),
            'stot_repeated_exposure': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter specific target organ toxicity information following repeated exposure...'
                }
            ),
            'aspiration_hazard': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter aspiration hazard information...'
                }
            ),
            'symptoms_related_to_exposure': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter symptoms related to physical, chemical and toxicological characteristics...'
                }
            ),
            'delayed_immediate_effects': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter delayed and immediate effects following exposure...'
                }
            ),
            'interactive_effects': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter information about known interactive effects...'
                }
            ),
            'numerical_measures_of_toxicity': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter numerical measures of toxicity such as LD50, LC50, or other available values...'
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter any additional toxicological information...'
                }
            ),
        }



# =============================================
# SDS Section 12 Form - Ecological Information
# =============================================
class SDSSection12Form(forms.ModelForm):
    class Meta:
        model = SDSSection12
        fields = [
            'aquatic_toxicity',
            'acute_aquatic_toxicity',
            'chronic_aquatic_toxicity',
            'persistence_degradability',
            'bioaccumulative_potential',
            'mobility_in_soil',
            'results_of_pbt_vpvb_assessment',
            'endocrine_disrupting_properties',
            'other_adverse_effects',
            'environmental_precautions',
            'additional_information',
        ]
        widgets = {
            'aquatic_toxicity': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter available information regarding aquatic toxicity...'
                }
            ),
            'acute_aquatic_toxicity': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter acute aquatic toxicity information...'
                }
            ),
            'chronic_aquatic_toxicity': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter chronic aquatic toxicity information...'
                }
            ),
            'persistence_degradability': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter information about persistence and degradability...'
                }
            ),
            'bioaccumulative_potential': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter information about bioaccumulative potential...'
                }
            ),
            'mobility_in_soil': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter information about mobility in soil...'
                }
            ),
            'results_of_pbt_vpvb_assessment': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter results of PBT and vPvB assessment, where applicable...'
                }
            ),
            'endocrine_disrupting_properties': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter information about endocrine disrupting properties, where applicable...'
                }
            ),
            'other_adverse_effects': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter other known adverse effects on the environment...'
                }
            ),
            'environmental_precautions': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter precautions to prevent environmental contamination or release...'
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter any additional ecological information...'
                }
            ),
        }



# =============================================
# SDS Section 13 Form - Disposal Considerations
# =============================================
class SDSSection13Form(forms.ModelForm):
    class Meta:
        model = SDSSection13
        fields = [
            'waste_treatment_methods',
            'product_disposal',
            'contaminated_packaging_disposal',
            'disposal_precautions',
            'waste_classification',
            'relevant_waste_regulations',
            'sewer_drain_disposal_restrictions',
            'environmental_disposal_considerations',
            'additional_information',
        ]
        widgets = {
            'waste_treatment_methods': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter appropriate waste treatment and disposal methods...'
                }
            ),
            'product_disposal': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter requirements for disposal of the chemical/product...'
                }
            ),
            'contaminated_packaging_disposal': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter requirements for disposal of contaminated containers and packaging...'
                }
            ),
            'disposal_precautions': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter precautions that must be followed during disposal...'
                }
            ),
            'waste_classification': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter applicable waste classification or waste code, if available...'
                }
            ),
            'relevant_waste_regulations': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter relevant waste disposal laws, regulations, or requirements...'
                }
            ),
            'sewer_drain_disposal_restrictions': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter restrictions or prohibitions regarding disposal into sewers or drains...'
                }
            ),
            'environmental_disposal_considerations': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter environmental considerations associated with disposal...'
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter any additional disposal information...'
                }
            ),
        }



# =============================================
# SDS Section 14 Form - Transport Information
# =============================================
class SDSSection14Form(forms.ModelForm):
    class Meta:
        model = SDSSection14
        fields = [
            'un_number',
            'un_proper_shipping_name',
            'transport_hazard_class',
            'packing_group',
            'environmental_hazards',
            'special_precautions',
            'transport_in_bulk',
            'maritime_transport_information',
            'air_transport_information',
            'road_rail_transport_information',
            'inland_waterway_transport_information',
            'additional_information',
        ]
        widgets = {
            'un_number': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter UN number, e.g. UN 1234...'
                }
            ),
            'un_proper_shipping_name': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Enter the UN proper shipping name...'
                }
            ),
            'transport_hazard_class': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter transport hazard class...'
                }
            ),
            'packing_group': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter packing group, if applicable...'
                }
            ),
            'environmental_hazards': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter environmental hazards relevant to transportation...'
                }
            ),
            'special_precautions': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter special precautions for users during transport...'
                }
            ),
            'transport_in_bulk': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter information regarding transport in bulk, where applicable...'
                }
            ),
            'maritime_transport_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter maritime/sea transport information...'
                }
            ),
            'air_transport_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter air transport information...'
                }
            ),
            'road_rail_transport_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter road and rail transport information...'
                }
            ),
            'inland_waterway_transport_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter inland waterway transport information...'
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter any additional transport information...'
                }
            ),
        }



# =============================================
# SDS Section 15 Form - Regulatory Information
# =============================================
class SDSSection15Form(forms.ModelForm):
    class Meta:
        model = SDSSection15
        fields = [
            'safety_health_environmental_regulations',
            'chemical_specific_regulations',
            'national_regulations',
            'regional_regulations',
            'international_regulations',
            'chemical_inventory_status',
            'restricted_prohibited_use',
            'regulatory_authorities',
            'reporting_notification_requirements',
            'additional_information',
        ]
        widgets = {
            'safety_health_environmental_regulations': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Enter applicable safety, health and environmental regulations...'
                }
            ),
            'chemical_specific_regulations': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Enter chemical-specific regulatory requirements...'
                }
            ),
            'national_regulations': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Enter applicable national regulations...'
                }
            ),
            'regional_regulations': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Enter applicable regional or state regulations...'
                }
            ),
            'international_regulations': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Enter applicable international regulations...'
                }
            ),
            'chemical_inventory_status': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter applicable chemical inventory or registration status...'
                }
            ),
            'restricted_prohibited_use': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter any restricted, prohibited or controlled uses...'
                }
            ),
            'regulatory_authorities': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter applicable regulatory authorities or agencies...'
                }
            ),
            'reporting_notification_requirements': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter reporting, notification or registration requirements...'
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter any additional regulatory information...'
                }
            ),
        }



# =============================================
# SDS Section 16 Form - Other Information
# =============================================
class SDSSection16Form(forms.ModelForm):
    class Meta:
        model = SDSSection16
        fields = [
            'preparation_date',
            'revision_date',
            'revision_summary',
            'key_changes_from_previous_version',
            'abbreviations',
            'references',
            'data_sources',
            'training_information',
            'disclaimer',
            'prepared_by',
            'reviewed_by',
            'additional_information',
        ]
        widgets = {
            'preparation_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
            'revision_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
            'revision_summary': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Enter a summary of the SDS revision...'
                }
            ),
            'key_changes_from_previous_version': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Describe the key changes from the previous SDS version...'
                }
            ),
            'abbreviations': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Enter abbreviations and acronyms used in the SDS...'
                }
            ),
            'references': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Enter references, standards, publications or other sources...'
                }
            ),
            'data_sources': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Enter the sources of technical, toxicological or regulatory data...'
                }
            ),
            'training_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Enter relevant training information or recommendations...'
                }
            ),
            'disclaimer': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Enter applicable disclaimer or limitation of information...'
                }
            ),
            'prepared_by': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter name or department responsible for preparation...'
                }
            ),
            'reviewed_by': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter name or department responsible for review...'
                }
            ),
            'additional_information': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Enter any additional information...'
                }
            ),
        }