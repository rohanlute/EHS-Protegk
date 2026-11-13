# apps/five_s/forms.py
from django import forms
from django.utils import timezone
from apps.accounts.models import User
from .models import (
    FiveSQuestion,
    FiveSTemplate,
    FiveSTemplateQuestion,
    FiveSSchedule,
    FREQUENCY_CHOICES,
    CorrectiveAction,
)


# ===========================================================================
# QUESTION — master library
# ===========================================================================

class FiveSQuestionForm(forms.ModelForm):
    """
    Create / edit a 5S question.
    question_code is auto-generated in the model and NOT editable.

    NOTE: All questions behave identically during inspection.
      - Rating 1 (Poor) or 2 (Fair) → remarks + photo evidence are MANDATORY
      - Rating 3, 4, 5, or N/A      → remarks + photo evidence are OPTIONAL
    """

    class Meta:
        model = FiveSQuestion
        fields = [
            'pillar',
            'question_text',
            'reference_standard',
            'guidance_notes',
            'is_active',
        ]
        widgets = {
            'question_text': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': "Phrase as an observable standard, e.g. "
                               "'Are tools stored in labelled locations?'",
            }),
            'guidance_notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': "Additional guidance for inspectors on how to evaluate this question",
            }),
            'reference_standard': forms.TextInput(attrs={
                'placeholder': "e.g., OSHA 1910.157, IS 2309",
            }),
            'pillar': forms.RadioSelect(),  # Handled via custom UI in template
        }
        labels = {
            'question_text': 'Question Text',
            'reference_standard': 'Reference Standard',
            'guidance_notes': 'Guidance Notes',
        }


# ===========================================================================
# TEMPLATE
# ===========================================================================

class FiveSTemplateForm(forms.ModelForm):
    class Meta:
        model = FiveSTemplate
        fields = [
            'template_name',
            'template_code',
            'description',
            'min_compliance_score',
            'is_active',
        ]
        widgets = {
            'template_name': forms.TextInput(attrs={
                'placeholder': 'e.g. Production Line Monthly 5S Audit',
            }),
            'template_code': forms.TextInput(attrs={
                'placeholder': 'e.g. 5S-PROD-LINE',
            }),
            'description': forms.Textarea(attrs={'rows': 3}),
            'min_compliance_score': forms.NumberInput(attrs={
                'step': '0.01', 'min': '0', 'max': '100',
            }),
        }
        labels = {
            'template_name': 'Template Name',
            'template_code': 'Template Code',
            'min_compliance_score': 'Minimum Compliance Score (%)',
        }

    def clean_template_code(self):
        code = self.cleaned_data.get('template_code', '').strip()
        if not code:
            raise forms.ValidationError('Template code is required.')

        qs = FiveSTemplate.objects.filter(template_code=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                f'A template with the code "{code}" already exists. '
                'Please use a different code.'
            )

        return code


# ===========================================================================
# TEMPLATE ↔ QUESTION (order / mandatory / section)
# ===========================================================================

class FiveSTemplateQuestionForm(forms.ModelForm):
    """
    Add / edit one question inside a template.
    """

    class Meta:
        model = FiveSTemplateQuestion
        fields = [
            'question',
            'is_mandatory',
            'display_order',
            'section_name',
        ]
        widgets = {
            'display_order': forms.NumberInput(attrs={'min': '0'}),
            'question': forms.Select(attrs={'class': 'form-select'}),
            'section_name': forms.TextInput(attrs={
                'placeholder': 'Optional, e.g. "Workbench area"',
            }),
        }
        labels = {
            'is_mandatory': 'Mandatory',
            'display_order': 'Display Order',
            'section_name': 'Section Name',
        }
        help_texts = {
            'display_order': "Lower numbers appear first in the audit form.",
        }

    def __init__(self, *args, template=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = template

        if template:
            taken = template.template_questions.values_list(
                'question_id', flat=True
            )
            qs = FiveSQuestion.objects.filter(is_active=True)

            if self.instance.pk:
                # On edit: allow the current question, block the others.
                qs = qs.exclude(
                    id__in=taken.exclude(question_id=self.instance.question_id)
                )
            else:
                qs = qs.exclude(id__in=taken)

            self.fields['question'].queryset = qs.order_by(
                'pillar', 'question_code',
            )
            self.fields['question'].label_from_instance = (
                lambda obj: f"{obj.question_code} · {obj.get_pillar_display()} · {obj.question_text[:60]}"
            )

    def clean(self):
        cleaned = super().clean()
        question = cleaned.get('question')
        if question and self.template:
            qs = FiveSTemplateQuestion.objects.filter(
                template=self.template, question=question,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    'question',
                    'This question is already in the template.',
                )
        return cleaned


# ===========================================================================
# BULK ADD
# ===========================================================================

class FiveSTemplateBulkAddForm(forms.Form):
    """
    Used by template_bulk_add_questions to validate the POST payload.
    """

    questions = forms.ModelMultipleChoiceField(
        queryset=FiveSQuestion.objects.none(),   # replaced in __init__
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label='Questions',
    )
    section_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Optional section name applied to all selected',
        }),
        label='Section name',
    )

    def __init__(self, *args, template=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = template
        if template:
            taken = template.template_questions.values_list(
                'question_id', flat=True
            )
            self.fields['questions'].queryset = (
                FiveSQuestion.objects
                .filter(is_active=True)
                .exclude(id__in=taken)
                .order_by('pillar', 'question_code')
            )


# ===========================================================================
# SCHEDULE (Stage 2)
# ===========================================================================

class FiveSScheduleForm(forms.ModelForm):
    class Meta:
        model = FiveSSchedule
        fields = [
            'schedule_name',
            'template',
            'start_date',
            'end_date',
            'enable_auto_schedule',
            'frequency',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'schedule_name': forms.TextInput(attrs={
                'placeholder': 'e.g. Line 1 Monthly 5S Walk'
            }),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['template'].queryset = FiveSTemplate.objects.filter(is_active=True)

        self.fields['frequency'].choices = [
            ('', '-- Select Frequency --')
        ] + list(FREQUENCY_CHOICES)

        # frequency and end_date are conditionally required → not enforced by default
        self.fields['frequency'].required = False
        self.fields['end_date'].required = False
        self.fields['enable_auto_schedule'].required = False

        for name, field in self.fields.items():
            if name == 'enable_auto_schedule':
                continue
            if name in ('template', 'frequency'):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

        if not self.initial.get('start_date') and not self.instance.pk:
            self.initial['start_date'] = timezone.now().date()

    def clean(self):
        cleaned = super().clean()
        auto = cleaned.get('enable_auto_schedule')
        frequency = cleaned.get('frequency')
        end_date = cleaned.get('end_date')
        start_date = cleaned.get('start_date')

        if auto:
            if not frequency:
                self.add_error(
                    'frequency',
                    'Frequency is required when auto-schedule is enabled.'
                )
            if not end_date:
                self.add_error(
                    'end_date',
                    'End date is required when auto-schedule is enabled.'
                )
        else:
            if not frequency:
                cleaned['frequency'] = 'MONTHLY'
                self.instance.frequency = 'MONTHLY'

        if end_date and start_date and end_date < start_date:
            self.add_error('end_date', 'End date must be on or after the start date.')

        return cleaned


# ===========================================================================
# INSPECTION — per-answer validation
# ===========================================================================

class InspectionAnswerForm(forms.Form):
    """
    Validates a single question's answer + remark + evidence during inspection.

    Rules (universal — no per-question settings):
      - Rating 1 (Poor) or 2 (Fair): remark AND evidence are REQUIRED.
      - Rating 3, 4, 5, or N/A: remark and evidence are OPTIONAL.
    """

    answer = forms.ChoiceField(
        choices=[
            ('1', 'Poor'),
            ('2', 'Fair'),
            ('3', 'Good'),
            ('4', 'V. Good'),
            ('5', 'Excellent'),
            ('NA', 'N/A'),
        ],
        required=True,
    )
    remarks = forms.CharField(required=False)
    evidence = forms.FileField(required=False)

    def __init__(self, *args, question=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.question = question

    def clean(self):
        cleaned = super().clean()
        answer = cleaned.get('answer')
        remarks = (cleaned.get('remarks') or '').strip()
        evidence = cleaned.get('evidence')

        if answer in ('1', '2'):
            label = 'Poor' if answer == '1' else 'Fair'

            if not remarks:
                self.add_error(
                    'remarks',
                    f'A remark is required when rating as "{label}". '
                    f'Please describe the finding.'
                )

            if not evidence:
                self.add_error(
                    'evidence',
                    f'Photo evidence is required when rating as "{label}". '
                    f'This photo will serve as the "before" image for the '
                    f'corrective action.'
                )

        return cleaned


# ===========================================================================
# CORRECTIVE ACTION — assignee completion
# ===========================================================================

class ActionCompleteForm(forms.ModelForm):
    """Form for the Assignee to submit their completion details."""
    class Meta:
        model = CorrectiveAction
        fields = ['completion_date', 'completion_remarks', 'completion_evidence']
        widgets = {
            'completion_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'completion_remarks': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'What did you do to fix this?'}),
            'completion_evidence': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'completion_date': 'Completion Date',
            'completion_remarks': 'Your Remarks',
            'completion_evidence': 'Evidence (Photo)',
        }

    def clean_completion_remarks(self):
        remarks = self.cleaned_data.get('completion_remarks')
        if not remarks:
            raise forms.ValidationError("Remarks are required.")
        return remarks


class ActionApprovalForm(forms.ModelForm):
    """Form for the Safety Manager to Approve or Reject."""
    decision = forms.ChoiceField(
        choices=[('approve', 'Approve'), ('reject', 'Reject')],
        widget=forms.HiddenInput()
    )

    class Meta:
        model = CorrectiveAction
        fields = ['approval_remarks']
        widgets = {
            'approval_remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Feedback for the assignee...'}),
        }
        labels = {
            'approval_remarks': 'Approval Remarks (Optional)',
        }