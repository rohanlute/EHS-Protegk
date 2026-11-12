from django import forms
from django.core.exceptions import ValidationError
from .models import *
from datetime import date
from apps.organizations.models import *
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from .related_records import RELATED_RECORD_MODELS

User = get_user_model()

def _set_select_placeholder(form, field_name, label):
    field = form.fields[field_name]
    if isinstance(field, forms.ModelChoiceField):
        field.empty_label = label
    elif isinstance(field, forms.ChoiceField):
        choices = list(field.choices)
        if choices and choices[0][0] == '':
            choices = choices[1:]
        field.choices = [('', label), *choices]
    elif isinstance(field.widget, forms.Select):
        choices = list(field.widget.choices)
        if choices and choices[0][0] == '':
            choices = choices[1:]
        field.widget.choices = [('', label), *choices]
    else:
        raise TypeError(
            f'{field_name} does not use a select field or widget.'
        )

    if not form.is_bound and not getattr(form.instance, 'pk', None):
        form.initial[field_name] = ''


class KaizenCategoryForm(forms.ModelForm):
    class Meta:
        model = KaizenCategory
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Occupational Health & Ergonomics'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., OHE',
                'maxlength': '20'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})


# MAIN KAIZEN FORM
class KaizenForm(forms.ModelForm):
    zone = forms.ModelChoiceField(
        queryset=Zone.objects.none(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    location_record = forms.ModelChoiceField(
        queryset=Location.objects.none(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    sublocation = forms.ModelChoiceField(
        queryset=SubLocation.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    additional_location_details = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Specific area, equipment, or landmark near the improvement',
        }),
    )

    class Meta:
        model = Kaizen
        fields = [
            'title',
            'description',
            'category',
            'plant',
            'department',
            'zone',
            'location_record',
            'sublocation',
            'additional_location_details',
            'problem_statement',
            'proposed_solution',
            'expected_benefits',
            'benefit_type',
            'priority',
            'estimated_cost',

            # Related source record
            'has_related_record',
            'related_module',
            'related_content_type',
            'related_object_id',
            'manual_source_reference',

            # Attachment
            'related_attachment',
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Kaizen title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'plant': forms.Select(attrs={
                'class': 'form-select'
            }),
            'department': forms.Select(attrs={
                'class': 'form-select'
            }),
            'zone': forms.Select(attrs={'class': 'form-select'}),
            'location_record': forms.Select(attrs={'class': 'form-select'}),
            'sublocation': forms.Select(attrs={'class': 'form-select'}),
            'problem_statement': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the existing problem'
            }),
            'proposed_solution': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your proposed improvement'
            }),
            'expected_benefits': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'benefit_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Enter estimated cost'
            }),
            'has_related_record': forms.Select(
                choices=[
                    (True, 'Yes'),
                    (False, 'No')
                ],
                attrs={
                    'class': 'form-select',
                    'id': 'id_has_related_record'
                }
            ),
            'related_module': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_related_module'
            }),
            'related_content_type': forms.HiddenInput(attrs={
                'id': 'id_related_content_type'
            }),
            'related_object_id': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Select source record ID'
            }),
            'manual_source_reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a manual source reference'
            }),
            'related_attachment': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['category'].queryset = KaizenCategory.objects.filter(
            is_active=True
        )
        allowed_types = [
            (app_label, model_name)
            for app_label, model_name in RELATED_RECORD_MODELS.values()
        ]
        self.fields['related_content_type'].queryset = ContentType.objects.filter(
            app_label__in=[app for app, _ in allowed_types],
            model__in=[model for _, model in allowed_types],
        )

        self.fields['related_module'].required = False
        self.fields['related_content_type'].required = False
        self.fields['related_object_id'].required = False
        self.fields['manual_source_reference'].required = False

        self.fields['plant'].queryset = Plant.objects.filter(is_active=True).order_by('name')
        if self.user:
            assigned_plants = self.user.assigned_plants.filter(is_active=True)
            if assigned_plants.exists():
                self.fields['plant'].queryset = assigned_plants.order_by('name')

        self.fields['zone'].queryset = Zone.objects.none()
        self.fields['location_record'].queryset = Location.objects.none()
        self.fields['sublocation'].queryset = SubLocation.objects.none()
        self.fields['plant'].required = True
        self.fields['plant'].empty_label = 'Select Plant'
        self.fields['zone'].empty_label = 'Select Plant First'
        self.fields['location_record'].empty_label = 'Select Zone First'
        self.fields['sublocation'].empty_label = 'Select Location First'
        self.fields['department'].queryset = Department.objects.filter(is_active=True).order_by('name')
        self.fields['department'].empty_label = '-- Select Department --'

        self.fields['zone'].label_from_instance = lambda obj: f'{obj.name} ({obj.code})'
        self.fields['location_record'].label_from_instance = lambda obj: f'{obj.name} ({obj.code})'
        self.fields['sublocation'].label_from_instance = lambda obj: (
            f'{obj.name} ({obj.code})' if obj.code else obj.name
        )
        for field_name, label in (
            ('category', '-- Select Category --'),
            ('plant', '-- Select Plant --'),
            ('department', '-- Select Department --'),
            ('zone', '-- Select Zone --'),
            ('location_record', '-- Select Location --'),
            ('sublocation', '-- Select Sub-Location --'),
            ('benefit_type', '-- Select Benefit Type --'),
            ('priority', '-- Select Priority --'),
            ('has_related_record', '-- Select Has Related Record --'),
            ('related_module', '-- Select Related Module --'),
        ):
            _set_select_placeholder(self, field_name, label)

        if self.is_bound:
            plant_id = self.data.get(self.add_prefix('plant'))
            zone_id = self.data.get(self.add_prefix('zone'))
            location_id = self.data.get(self.add_prefix('location_record'))
            if plant_id and str(plant_id).isdigit():
                self.fields['zone'].queryset = Zone.objects.filter(
                    plant_id=plant_id, is_active=True
                ).order_by('name')
            if zone_id and str(zone_id).isdigit():
                self.fields['location_record'].queryset = Location.objects.filter(
                    zone_id=zone_id, is_active=True
                ).order_by('name')
            if location_id and str(location_id).isdigit():
                self.fields['sublocation'].queryset = SubLocation.objects.filter(
                    location_id=location_id, is_active=True
                ).order_by('name')
        elif self.instance and self.instance.pk:
            if self.instance.plant_id:
                self.fields['zone'].queryset = Zone.objects.filter(
                    plant_id=self.instance.plant_id, is_active=True
                ).order_by('name')
            if self.instance.zone_id:
                self.fields['location_record'].queryset = Location.objects.filter(
                    zone_id=self.instance.zone_id, is_active=True
                ).order_by('name')
            if self.instance.location_record_id:
                self.fields['sublocation'].queryset = SubLocation.objects.filter(
                    location_id=self.instance.location_record_id, is_active=True
                ).order_by('name')
            elif self.instance.plant_id and self.instance.location:
                legacy_location = Location.objects.filter(
                    zone__plant_id=self.instance.plant_id,
                    name=self.instance.location,
                    is_active=True,
                ).first()
                if legacy_location:
                    self.initial['zone'] = legacy_location.zone_id
                    self.initial['location_record'] = legacy_location.pk
                    self.fields['location_record'].queryset = Location.objects.filter(
                        zone=legacy_location.zone, is_active=True
                    )

        if self.user and not self.is_bound and not self.instance.pk:
            assigned_plants = self.user.assigned_plants.filter(is_active=True)
            if assigned_plants.count() == 1:
                self.initial['plant'] = assigned_plants.first().pk

        for field_name in ('plant', 'zone', 'location_record', 'sublocation'):
            current_value = (
                self.data.get(self.add_prefix(field_name), '')
                if self.is_bound else self.initial.get(field_name, '')
            )
            self.fields[field_name].widget.attrs['data-initial-value'] = str(current_value or '')

    def clean(self):
        cleaned_data = super().clean()
        plant = cleaned_data.get('plant')
        zone = cleaned_data.get('zone')
        location = cleaned_data.get('location_record')
        sublocation = cleaned_data.get('sublocation')

        if zone and plant and zone.plant_id != plant.pk:
            self.add_error('zone', 'Select a zone within the chosen plant.')
        if location and zone and location.zone_id != zone.pk:
            self.add_error('location_record', 'Select a location within the chosen zone.')
        if sublocation and location and sublocation.location_id != location.pk:
            self.add_error('sublocation', 'Select a sub-location within the chosen location.')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        selected_location = self.cleaned_data.get('location_record')
        instance.location = selected_location.name if selected_location else ''
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def clean(self):
        cleaned_data = super().clean()

        has_related_record = cleaned_data.get('has_related_record')
        related_module = cleaned_data.get('related_module')
        content_type = cleaned_data.get('related_content_type')
        object_id = cleaned_data.get('related_object_id')
        manual_reference = cleaned_data.get('manual_source_reference')

        if has_related_record:
            if not related_module:
                self.add_error(
                    'related_module',
                    'Please select a related module.'
                )

            if not content_type:
                self.add_error(
                    'related_content_type',
                    'Please select the source record type.'
                )

            if not object_id:
                self.add_error(
                    'related_object_id',
                    'Please select a source record.'
                )

            if manual_reference:
                self.add_error(
                    'manual_source_reference',
                    'Manual reference is not required when linking an existing record.'
                )

            if related_module and content_type:
                expected_type = RELATED_RECORD_MODELS.get(related_module)
                if expected_type != (content_type.app_label, content_type.model):
                    self.add_error(
                        'related_content_type',
                        'Selected source record type does not match the related module.'
                    )

                elif object_id and not content_type.model_class().objects.filter(
                    pk=object_id
                ).exists():
                    self.add_error(
                        'related_object_id',
                        'Select a valid record from the chosen module.'
                    )

        else:
            cleaned_data['related_module'] = ''
            cleaned_data['related_content_type'] = None
            cleaned_data['related_object_id'] = None

            if not manual_reference:
                self.add_error(
                    'manual_source_reference',
                    'Please enter a manual source reference.'
                )
        return cleaned_data


# INITIAL REVIEW FORM
class KaizenInitialReviewForm(forms.ModelForm):

    class Meta:
        model = KaizenInitialReview
        fields = [
            'decision',
            'review_comments',
            'clarification_required',
        ]

        widgets = {
            'decision': forms.Select(attrs={
                'class': 'form-select'
            }),
            'review_comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter review comments'
            }),
            'clarification_required': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Specify the clarification required'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        _set_select_placeholder(self, 'decision', '-- Select Decision --')

    def clean(self):
        cleaned_data = super().clean()

        decision = cleaned_data.get('decision')
        clarification = cleaned_data.get('clarification_required')

        if (
            decision == KaizenInitialReview.DecisionChoices.CLARIFICATION
            and not clarification
        ):
            self.add_error(
                'clarification_required',
                'Please specify the clarification required.'
            )

        return cleaned_data


# TECHNICAL EVALUATION FORM
class KaizenTechnicalEvaluationForm(forms.ModelForm):

    class Meta:
        model = KaizenTechnicalEvaluation
        fields = [
            'decision',
            'feasibility',
            'technical_comments',
            'safety_impact',
            'operational_impact',
            'resource_requirements',
            'estimated_implementation_cost',
            'estimated_completion_date',
            'recommendation',
        ]

        widgets = {
            'decision': forms.Select(attrs={
                'class': 'form-select'
            }),
            'feasibility': forms.Select(attrs={
                'class': 'form-select'
            }),
            'technical_comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'safety_impact': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'operational_impact': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'resource_requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'estimated_implementation_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'estimated_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'recommendation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter technical recommendation'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        _set_select_placeholder(self, 'decision', '-- Select Decision --')
        _set_select_placeholder(self, 'feasibility', '-- Select Feasibility --')

        self.fields['feasibility'].required = True

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        feasibility = cleaned_data.get('feasibility')
        rationale = cleaned_data.get('technical_comments') or cleaned_data.get('recommendation')

        if (
            feasibility == KaizenTechnicalEvaluation.FeasibilityChoices.NOT_FEASIBLE
            and decision == KaizenTechnicalEvaluation.DecisionChoices.RECOMMEND_APPROVAL
        ):
            self.add_error(
                'decision',
                'A not feasible idea cannot be recommended for approval.'
            )

        if (
            decision in [
                KaizenTechnicalEvaluation.DecisionChoices.CLARIFICATION,
                KaizenTechnicalEvaluation.DecisionChoices.REJECTED,
            ]
            and not rationale
        ):
            self.add_error(
                'technical_comments',
                'Enter the reason for requesting clarification or recommending rejection.'
            )
        return cleaned_data


# APPROVAL FORM
class KaizenApprovalForm(forms.ModelForm):

    class Meta:
        model = KaizenApproval
        fields = [
            'decision',
            'approval_comments',
        ]

        widgets = {
            'decision': forms.Select(attrs={
                'class': 'form-select'
            }),
            'approval_comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter approval comments'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        _set_select_placeholder(self, 'decision', '-- Select Decision --')
        self.fields['decision'].required = True

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        comments = cleaned_data.get('approval_comments')
        if (
            decision in [
                KaizenApproval.DecisionChoices.REJECTED,
                KaizenApproval.DecisionChoices.REVISION,
            ]
            and not comments
        ):
            self.add_error(
                'approval_comments',
                'Comments are required when rejecting or returning an idea for revision.'
            )
        return cleaned_data


# IMPLEMENTATION FORM
class KaizenImplementationForm(forms.ModelForm):

    def __init__(self, *args, plant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Implementation owners must belong to the selected plant,
        # either through their primary plant or assigned plants.
        self.fields['implementation_owner'].queryset = User.objects.none()

        if plant is not None:
            self.fields['implementation_owner'].queryset = (
                User.objects.filter(
                    is_active=True,
                ).filter(
                    Q(plant=plant) | Q(assigned_plants=plant)
                ).distinct().order_by(
                    'first_name', 'last_name', 'username'
                )
            )

        # Exclude the currently logged-in user from the dropdown.
        if user:
            self.fields['implementation_owner'].queryset = (
                self.fields['implementation_owner'].queryset.exclude(
                    pk=user.pk
                )
            )
        _set_select_placeholder(
            self, 'implementation_owner', '-- Select Implementation Owner --'
        )

        self.fields['implementation_status'].choices = [
            *[
                choice
                for choice in self.fields['implementation_status'].choices
                if choice[0] != KaizenImplementation.ImplementationStatusChoices.COMPLETED
            ],
        ]
        _set_select_placeholder(
            self, 'implementation_status', '-- Select Implementation Status --'
        )

    class Meta:
        model = KaizenImplementation
        fields = [
            'implementation_owner',
            'implementation_status',
            'planned_start_date',
            'planned_end_date',
            'actual_start_date',
            'actual_end_date',
            'implementation_actions',
            'resources_used',
            'actual_cost',
            'implementation_remarks',
        ]

        widgets = {
            'implementation_owner': forms.Select(attrs={
                'class': 'form-select'
            }),
            'implementation_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'planned_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'planned_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'actual_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'actual_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'implementation_actions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'resources_used': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'actual_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'implementation_remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        planned_start = cleaned_data.get('planned_start_date')
        planned_end = cleaned_data.get('planned_end_date')
        actual_start = cleaned_data.get('actual_start_date')
        actual_end = cleaned_data.get('actual_end_date')

        if planned_start and planned_end and planned_end < planned_start:
            self.add_error(
                'planned_end_date',
                'Planned end date cannot be before planned start date.'
            )

        if actual_start and actual_end and actual_end < actual_start:
            self.add_error(
                'actual_end_date',
                'Actual end date cannot be before actual start date.'
            )

        return cleaned_data


class KaizenImplementationCompletionForm(forms.Form):
    completion_date = forms.DateField(
        label='Completion Date',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    completion_remarks = forms.CharField(
        label='Completion Remarks',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Describe the work completed and the result achieved.',
        }),
    )
    evidence = forms.FileField(
        label='Upload Proof / Attachment (Optional)',
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
    )


# VERIFICATION FORM
class KaizenVerificationForm(forms.ModelForm):
    rework_required = forms.TypedChoiceField(
        label='Rework required',
        choices=(('', 'Select whether rework is required'), ('1', 'Yes'), ('0', 'No')),
        coerce=lambda value: None if value == '' else value == '1',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Select Yes to return the Kaizen to implementation. Select No to proceed to closure.',
    )

    class Meta:
        model = KaizenVerification
        fields = [
            'result',
            'rework_required',
            'verification_method',
            'before_improvement',
            'after_improvement',
            'actual_benefits',
            'evidence_details',
            'verification_comments',
        ]

        widgets = {
            'result': forms.Select(attrs={
                'class': 'form-select'
            }),
            'verification_method': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'before_improvement': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'after_improvement': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'actual_benefits': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'evidence_details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'verification_comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _set_select_placeholder(self, 'result', '-- Select Result --')
        _set_select_placeholder(
            self, 'rework_required', '-- Select Rework Required --'
        )
        if self.instance and self.instance.pk and self.instance.rework_required is not None:
            self.initial['rework_required'] = '1' if self.instance.rework_required else '0'

    def clean(self):
        cleaned_data = super().clean()
        result = cleaned_data.get('result')
        rework_required = cleaned_data.get('rework_required')
        comments = cleaned_data.get('verification_comments')
        if result == KaizenVerification.ResultChoices.PARTIAL and rework_required is None:
            self.add_error('rework_required', 'Select whether rework is required for a partially successful result.')
        elif result != KaizenVerification.ResultChoices.PARTIAL:
            cleaned_data['rework_required'] = None
        if (
            result in [
                KaizenVerification.ResultChoices.PARTIAL,
                KaizenVerification.ResultChoices.FAILED,
            ]
            and not comments
        ):
            self.add_error(
                'verification_comments',
                'Explain why the change is not yet effective and what rework is required.'
            )
        return cleaned_data


# KAIZEN ATTACHMENT FORM
class KaizenAttachmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _set_select_placeholder(
            self, 'attachment_type', '-- Select Attachment Type --'
        )

    class Meta:
        model = KaizenAttachment
        fields = [
            'file',
            'attachment_type',
            'description',
        ]

        widgets = {
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'attachment_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter attachment description'
            }),
        }


# CLOSURE FORM

class KaizenClosureForm(forms.ModelForm):

    class Meta:
        model = KaizenClosure
        fields = [
            'final_outcome',
            'actual_benefits',
            'actual_implementation_cost',
            'lessons_learned',
            'closure_comments',
        ]

        widgets = {
            'final_outcome': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Summarize the final improvement outcome'
            }),
            'actual_benefits': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the actual benefits achieved'
            }),
            'actual_implementation_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'lessons_learned': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'closure_comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }