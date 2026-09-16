from django import forms
from django.contrib.auth import get_user_model
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.organizations.models import Department, Plant
from apps.training.models import TrainingSession

from .models import HIRA, HIRAAction, HIRAHazard, HIRAModule, HazardRiskMaster, RiskMatrix, RiskMatrixLevel
from .source_adapters import adapter_choices, get_adapter

User = get_user_model()

TEXT_INPUT = {"class": "form-control"}
SELECT = {"class": "form-control"}
TEXTAREA = {"class": "form-control", "rows": 3}
DATE_INPUT = {"class": "form-control", "type": "date"}
CHECKBOX = {"class": "form-check-input"}


class HIRAForm(forms.ModelForm):
    class Meta:
        model = HIRA
        fields = [
            "plant",
            "department",
            "module",
            "process",
            "assessment_date",
            "assessment_type",
            "review_date",
            "revision_number",
            "revision_description",
            "remarks",
        ]
        widgets = {
            "plant": forms.Select(attrs=SELECT),
            "department": forms.Select(attrs=SELECT),
            "module": forms.Select(attrs=SELECT),
            "process": forms.TextInput(attrs=TEXT_INPUT),
            "assessment_date": forms.DateInput(attrs=DATE_INPUT),
            "assessment_type": forms.Select(attrs=SELECT),
            "review_date": forms.DateInput(attrs=DATE_INPUT),
            "revision_number": forms.NumberInput(attrs={**TEXT_INPUT, "min": 0}),
            "revision_description": forms.Textarea(attrs=TEXTAREA),
            "remarks": forms.Textarea(attrs=TEXTAREA),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["module"].queryset = HIRAModule.objects.filter(is_active=True)
        self.fields["plant"].queryset = Plant.objects.filter(is_active=True)
        self.fields["department"].queryset = Department.objects.filter(is_active=True)
        if self.user and not self.user.is_superuser and hasattr(self.user, "get_all_plants"):
            plants = self.user.get_all_plants()
            if plants:
                self.fields["plant"].queryset = Plant.objects.filter(id__in=[p.id for p in plants])


class HIRAHazardForm(forms.ModelForm):
    linked_training_session = forms.ModelChoiceField(
        queryset=TrainingSession.objects.none(),
        required=False,
        label="Related Training Session",
        widget=forms.Select(attrs=SELECT),
    )

    class Meta:
        model = HIRAHazard
        fields = [
            "master_rule",
            "activity",
            "hazard_category",
            "hazard",
            "unsafe_act",
            "unsafe_condition",
            "potential_consequence",
            "persons_exposed",
            "existing_controls",
            "control_hierarchy",
            "likelihood",
            "severity",
            "additional_controls",
            "additional_control_hierarchy",
            "action_required",
            "responsible_person",
            "target_date",
            "residual_likelihood",
            "residual_severity",
            "linked_training_session",
            "evidence_remarks",
        ]
        widgets = {
            "master_rule": forms.HiddenInput(),
            "activity": forms.TextInput(attrs=TEXT_INPUT),
            "hazard_category": forms.Select(attrs=SELECT),
            "hazard": forms.Textarea(attrs=TEXTAREA),
            "unsafe_act": forms.Textarea(attrs=TEXTAREA),
            "unsafe_condition": forms.Textarea(attrs=TEXTAREA),
            "potential_consequence": forms.Textarea(attrs=TEXTAREA),
            "persons_exposed": forms.TextInput(attrs=TEXT_INPUT),
            "existing_controls": forms.Textarea(attrs=TEXTAREA),
            "control_hierarchy": forms.TextInput(attrs=TEXT_INPUT),
            "likelihood": forms.NumberInput(attrs={**TEXT_INPUT, "min": 1, "max": 5}),
            "severity": forms.NumberInput(attrs={**TEXT_INPUT, "min": 1, "max": 5}),
            "additional_controls": forms.Textarea(attrs=TEXTAREA),
            "additional_control_hierarchy": forms.TextInput(attrs=TEXT_INPUT),
            "action_required": forms.CheckboxInput(attrs=CHECKBOX),
            "responsible_person": forms.Select(attrs=SELECT),
            "target_date": forms.DateInput(attrs=DATE_INPUT),
            "residual_likelihood": forms.NumberInput(attrs={**TEXT_INPUT, "min": 1, "max": 5}),
            "residual_severity": forms.NumberInput(attrs={**TEXT_INPUT, "min": 1, "max": 5}),
            "evidence_remarks": forms.Textarea(attrs=TEXTAREA),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["responsible_person"].queryset = User.objects.filter(is_active=True).order_by("first_name", "last_name")
        self.fields["master_rule"].queryset = HazardRiskMaster.objects.filter(is_active=True)
        qs = TrainingSession.objects.select_related("topic", "plant").order_by("-scheduled_date")
        if user and not user.is_superuser and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            if plants:
                qs = qs.filter(plant__in=plants)
        self.fields["linked_training_session"].queryset = qs

    def save(self, commit=True):
        instance = super().save(commit=False)
        linked_session = self.cleaned_data.get("linked_training_session")
        if linked_session:
            from django.contrib.contenttypes.models import ContentType

            instance.related_content_type = ContentType.objects.get_for_model(linked_session)
            instance.related_object_id = linked_session.pk
        if commit:
            instance.save()
        return instance


class HIRAActionForm(forms.ModelForm):
    class Meta:
        model = HIRAAction
        fields = [
            "action_description",
            "responsible_person",
            "target_date",
            "priority",
            "status",
            "completion_date",
            "verification",
            "verified_by",
            "remarks",
        ]
        widgets = {
            "action_description": forms.Textarea(attrs=TEXTAREA),
            "responsible_person": forms.Select(attrs=SELECT),
            "target_date": forms.DateInput(attrs=DATE_INPUT),
            "priority": forms.Select(attrs=SELECT),
            "status": forms.Select(attrs=SELECT),
            "completion_date": forms.DateInput(attrs=DATE_INPUT),
            "verification": forms.Textarea(attrs=TEXTAREA),
            "verified_by": forms.Select(attrs=SELECT),
            "remarks": forms.Textarea(attrs=TEXTAREA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        users = User.objects.filter(is_active=True).order_by("first_name", "last_name")
        self.fields["responsible_person"].queryset = users
        self.fields["verified_by"].queryset = users


class HazardRiskMasterForm(forms.ModelForm):
    class Meta:
        model = HazardRiskMaster
        fields = [
            "module",
            "process",
            "activity",
            "hazard_category",
            "hazard",
            "unsafe_act",
            "unsafe_condition",
            "consequence",
            "existing_controls",
            "suggested_additional_controls",
            "default_likelihood",
            "default_severity",
            "is_active",
        ]
        widgets = {
            "module": forms.Select(attrs=SELECT),
            "process": forms.TextInput(attrs=TEXT_INPUT),
            "activity": forms.TextInput(attrs=TEXT_INPUT),
            "hazard_category": forms.Select(attrs=SELECT),
            "hazard": forms.Textarea(attrs=TEXTAREA),
            "unsafe_act": forms.Textarea(attrs=TEXTAREA),
            "unsafe_condition": forms.Textarea(attrs=TEXTAREA),
            "consequence": forms.Textarea(attrs=TEXTAREA),
            "existing_controls": forms.Textarea(attrs=TEXTAREA),
            "suggested_additional_controls": forms.Textarea(attrs=TEXTAREA),
            "default_likelihood": forms.NumberInput(attrs={**TEXT_INPUT, "min": 1, "max": 5}),
            "default_severity": forms.NumberInput(attrs={**TEXT_INPUT, "min": 1, "max": 5}),
            "is_active": forms.CheckboxInput(attrs=CHECKBOX),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["module"].queryset = HIRAModule.objects.filter(is_active=True)
        self.fields["module"].empty_label = "All Modules"


class RiskMatrixForm(forms.ModelForm):
    class Meta:
        model = RiskMatrix
        fields = [
            "name",
            "description",
            "min_likelihood",
            "max_likelihood",
            "min_severity",
            "max_severity",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs=TEXT_INPUT),
            "description": forms.Textarea(attrs=TEXTAREA),
            "min_likelihood": forms.NumberInput(attrs={**TEXT_INPUT, "min": 1, "max": 5}),
            "max_likelihood": forms.NumberInput(attrs={**TEXT_INPUT, "min": 1, "max": 5}),
            "min_severity": forms.NumberInput(attrs={**TEXT_INPUT, "min": 1, "max": 5}),
            "max_severity": forms.NumberInput(attrs={**TEXT_INPUT, "min": 1, "max": 5}),
            "is_active": forms.CheckboxInput(attrs=CHECKBOX),
        }


class RiskMatrixLevelForm(forms.ModelForm):
    class Meta:
        model = RiskMatrixLevel
        fields = [
            "risk_matrix",
            "min_score",
            "max_score",
            "risk_level",
            "display_order",
            "description",
            "is_active",
        ]
        widgets = {
            "risk_matrix": forms.Select(attrs=SELECT),
            "min_score": forms.NumberInput(attrs={**TEXT_INPUT, "min": 1, "max": 25}),
            "max_score": forms.NumberInput(attrs={**TEXT_INPUT, "min": 1, "max": 25}),
            "risk_level": forms.Select(attrs=SELECT),
            "display_order": forms.NumberInput(attrs={**TEXT_INPUT, "min": 1}),
            "description": forms.Textarea(attrs=TEXTAREA),
            "is_active": forms.CheckboxInput(attrs=CHECKBOX),
        }


class BaseHIRAHazardFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs["user"] = self.user
        return super()._construct_form(i, **kwargs)


HIRAHazardFormSet = inlineformset_factory(
    HIRA,
    HIRAHazard,
    form=HIRAHazardForm,
    formset=BaseHIRAHazardFormSet,
    extra=1,
    can_delete=True,
)


class HIRAReportFilterForm(forms.Form):
    plant = forms.ModelChoiceField(queryset=Plant.objects.none(), required=False, widget=forms.Select(attrs=SELECT))
    department = forms.ModelChoiceField(queryset=Department.objects.none(), required=False, widget=forms.Select(attrs=SELECT))
    module = forms.ModelChoiceField(queryset=HIRAModule.objects.none(), required=False, widget=forms.Select(attrs=SELECT))
    process = forms.CharField(required=False, widget=forms.TextInput(attrs=TEXT_INPUT))
    activity = forms.CharField(required=False, widget=forms.TextInput(attrs=TEXT_INPUT))
    risk_level = forms.ChoiceField(
        required=False,
        choices=[("", "All Risk Levels"), ("Low", "Low"), ("Medium", "Medium"), ("High", "High"), ("Critical", "Critical")],
        widget=forms.Select(attrs=SELECT),
    )
    status = forms.ChoiceField(required=False, choices=[("", "All Status")] + HIRA.STATUS_CHOICES, widget=forms.Select(attrs=SELECT))
    source_module = forms.ChoiceField(required=False, choices=[("", "All Source Modules")] + adapter_choices(), widget=forms.Select(attrs=SELECT))
    from_date = forms.DateField(required=False, widget=forms.DateInput(attrs=DATE_INPUT))
    to_date = forms.DateField(required=False, widget=forms.DateInput(attrs=DATE_INPUT))
    financial_year = forms.CharField(required=False, widget=forms.TextInput(attrs={**TEXT_INPUT, "placeholder": "2026-27"}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        plant_qs = Plant.objects.filter(is_active=True)
        if user and not user.is_superuser and hasattr(user, "get_all_plants"):
            plants = user.get_all_plants()
            if plants:
                plant_qs = plant_qs.filter(id__in=[p.id for p in plants])
        self.fields["plant"].queryset = plant_qs
        self.fields["department"].queryset = Department.objects.filter(is_active=True)
        self.fields["module"].queryset = HIRAModule.objects.filter(is_active=True)
        self.fields["plant"].empty_label = "All Plants"
        self.fields["department"].empty_label = "All Departments"
        self.fields["module"].empty_label = "All Modules"


class HIRASourceSelectForm(forms.Form):
    source_module = forms.ChoiceField(
        required=True,
        choices=[("", "Select Source Module")] + adapter_choices(),
        widget=forms.Select(attrs={**SELECT, "id": "id_source_module"}),
    )
    source_record = forms.ChoiceField(
        required=True,
        choices=[("", "Select Source Record")],
        widget=forms.Select(attrs=SELECT),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        source_module = None
        if self.data:
            source_module = self.data.get("source_module")
        elif self.initial:
            source_module = self.initial.get("source_module")
        adapter = get_adapter(source_module)
        if adapter:
            self.fields["source_record"].choices = [("", "Select Source Record")] + adapter.choices(user=user)
