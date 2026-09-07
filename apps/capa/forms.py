import json

from django import forms

from apps.accounts.models import *
from apps.capa.models import (
    CAPA,
    CAPAAttachment,
    CAPAAction,
    CAPAActionCompletion,
    CAPAActionVerification,
    CAPAComment,
    CAPAEffectivenessReview,
    CAPAInvestigation,
)
from apps.organizations.models import Department, Location, Plant, SubLocation, Zone


class BaseEHSForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-control")
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class FlexibleJSONField(forms.CharField):
    """Keep JSON storage while allowing investigators to enter normal text."""

    def __init__(self, *, empty_value, **kwargs):
        self.json_empty_value = empty_value
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def prepare_value(self, value):
        if value in (None, "", [], {}):
            return ""
        if isinstance(value, (list, dict)):
            return json.dumps(value, indent=2, ensure_ascii=False)
        return value

    def to_python(self, value):
        value = super().to_python(value)
        if not value or not value.strip():
            return self.json_empty_value
        try:
            parsed = json.loads(value)
            if isinstance(parsed, type(self.json_empty_value)):
                return parsed
        except (TypeError, ValueError):
            pass

        # Plain text is intentionally accepted for a user-friendly form.
        if isinstance(self.json_empty_value, list):
            return [line.strip() for line in value.splitlines() if line.strip()]
        return {"details": value.strip()}


class CAPAForm(BaseEHSForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["owner"].queryset = User.objects.filter(is_active=True, is_superuser=False)

    def clean(self):
        cleaned_data = super().clean()
        source_type = cleaned_data.get("source_type")
        source_reference = (cleaned_data.get("source_reference") or "").strip()

        if source_type != CAPA.SourceType.MANUAL and not source_reference:
            self.add_error("source_reference", "Select a source record.")

        if source_type == CAPA.SourceType.INCIDENT and source_reference:
            from apps.accidents.models import Incident
            if not Incident.objects.filter(report_number=source_reference).exists():
                self.add_error("source_reference", "Select a valid incident from the list.")
        elif source_type == CAPA.SourceType.HAZARD and source_reference:
            from apps.hazards.models import Hazard
            if not Hazard.objects.filter(report_number=source_reference).exists():
                self.add_error("source_reference", "Select a valid hazard from the list.")

        cleaned_data["source_reference"] = source_reference
        return cleaned_data

    class Meta:
        model = CAPA
        fields = [
            "title",
            "description",
            "source_type",
            "source_reference",
            "plant",
            "zone",
            "location",
            "sublocation",
            "department",
            "category",
            "severity",
            "priority",
            "owner",
            "target_date",
            "reason_required",
            "capa_recommended",
            "capa_reason",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "reason_required": forms.Textarea(attrs={"rows": 3}),
            "capa_reason": forms.Textarea(attrs={"rows": 3}),
            "target_date": forms.DateInput(attrs={"type": "date"}),
        }


class CAPAInvestigationForm(BaseEHSForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["lead_investigator"].queryset = User.objects.filter(is_active=True, is_superuser=False)
        self.fields["contributing_factors"] = FlexibleJSONField(
            empty_value=[],
            label="Contributing factors",
            widget=forms.Textarea(attrs={"rows": 4, "class": "form-control", "placeholder": "Enter each factor on a new line"}),
        )
        self.fields["extent_analysis"] = FlexibleJSONField(
            empty_value={},
            label="Extent analysis",
            widget=forms.Textarea(attrs={"rows": 4, "class": "form-control", "placeholder": "Describe the extent of the issue"}),
        )

    class Meta:
        model = CAPAInvestigation
        fields = [
            "investigation_date",
            "lead_investigator",
            "investigation_team",
            "investigation_method",
            "problem_statement",
            "what_happened",
            "impact_consequence",
            "what_was_affected",
            "sequence_of_events",
            "findings",
            "evidence_collected",
            "witness_statements",
            "existing_controls",
            "existing_control_in_place",
            "existing_control_followed",
            "existing_control_adequate",
            "control_failure_reason",
            "control_gap_identified",
            "why1",
            "why2",
            "why3",
            "why4",
            "why5",
            "final_root_cause",
            "root_cause_category",
            "root_cause_details",
            "contributing_factors",
            "extent_analysis",
            "affected_plants",
            "affected_departments",
            "affected_locations",
            "related_references",
            "initial_likelihood",
            "initial_severity",
            "initial_risk_score",
            "existing_controls_summary",
            "residual_likelihood",
            "residual_severity",
            "residual_risk_score",
            "risk_assessment_update_required",
            "risk_assessment_remarks",
            "procedure_sop_revision_required",
            "training_required",
            "risk_assessment_revision_required",
            "engineering_modification_required",
            "moc_required",
            "legal_compliance_review_required",
            "document_control_update_required",
            "management_system_impact_details",
            "investigation_conclusion",
            "root_cause_confirmed",
            "additional_investigation_required",
            "systemic_issue_identified",
            "extent_analysis_required",
            "action_plan_required",
            "investigator_recommendation",
        ]
        widgets = {
            "investigation_date": forms.DateInput(attrs={"type": "date"}),
            "problem_statement": forms.Textarea(attrs={"rows": 3}),
            "what_happened": forms.Textarea(attrs={"rows": 3}),
            "impact_consequence": forms.Textarea(attrs={"rows": 3}),
            "what_was_affected": forms.Textarea(attrs={"rows": 3}),
            "sequence_of_events": forms.Textarea(attrs={"rows": 3}),
            "findings": forms.Textarea(attrs={"rows": 3}),
            "evidence_collected": forms.Textarea(attrs={"rows": 3}),
            "witness_statements": forms.Textarea(attrs={"rows": 3}),
            "existing_controls": forms.Textarea(attrs={"rows": 3}),
            "control_failure_reason": forms.Textarea(attrs={"rows": 3}),
            "control_gap_identified": forms.Textarea(attrs={"rows": 3}),
            "why1": forms.Textarea(attrs={"rows": 2}),
            "why2": forms.Textarea(attrs={"rows": 2}),
            "why3": forms.Textarea(attrs={"rows": 2}),
            "why4": forms.Textarea(attrs={"rows": 2}),
            "why5": forms.Textarea(attrs={"rows": 2}),
            "final_root_cause": forms.Textarea(attrs={"rows": 2}),
            "root_cause_details": forms.Textarea(attrs={"rows": 3}),
            "related_references": forms.Textarea(attrs={"rows": 3}),
            "existing_controls_summary": forms.Textarea(attrs={"rows": 3}),
            "risk_assessment_remarks": forms.Textarea(attrs={"rows": 3}),
            "management_system_impact_details": forms.Textarea(attrs={"rows": 3}),
            "investigation_conclusion": forms.Textarea(attrs={"rows": 3}),
            "investigator_recommendation": forms.Textarea(attrs={"rows": 3}),
            "reviewer_comments": forms.Textarea(attrs={"rows": 3}),
            "completed_date": forms.DateInput(attrs={"type": "date"}),
            "review_date": forms.DateInput(attrs={"type": "date"}),
        }


class CAPAActionForm(BaseEHSForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Every action needs an accountable owner before completion.
        self.fields["assigned_to"].required = True
        self.fields["assigned_to"].queryset = User.objects.filter(is_active=True, is_superuser=False)

    class Meta:
        model = CAPAAction
        exclude = (
            "capa",
            "created_by",
            "completion_remarks",
            "verified_remarks",
            "status",
            "source_action_content_type",
            "source_action_object_id",
        )
        widgets = {
            "target_date": forms.DateInput(attrs={"type": "date"}),
            "action_description": forms.Textarea(attrs={"rows": 3}),
        }


class CAPAActionCompletionForm(BaseEHSForm):
    class Meta:
        model = CAPAActionCompletion
        exclude = ("action", "completed_by", "submitted_for_verification")
        widgets = {
            "completion_date": forms.DateInput(attrs={"type": "date"}),
            "completion_remarks": forms.Textarea(attrs={"rows": 3}),
        }


class CAPAActionVerificationForm(BaseEHSForm):
    class Meta:
        model = CAPAActionVerification
        exclude = ("action", "verified_by")
        widgets = {
            "verification_date": forms.DateInput(attrs={"type": "date"}),
            "verification_findings": forms.Textarea(attrs={"rows": 3}),
            "deviation_deficiency": forms.Textarea(attrs={"rows": 3}),
            "additional_evidence_remarks": forms.Textarea(attrs={"rows": 3}),
            "rejection_reason": forms.Textarea(attrs={"rows": 3}),
            "additional_action_required": forms.Textarea(attrs={"rows": 3}),
            "reverification_due_date": forms.DateInput(attrs={"type": "date"}),
        }


class CAPAEffectivenessReviewForm(BaseEHSForm):
    class Meta:
        model = CAPAEffectivenessReview
        exclude = ("capa", "reviewed_by")
        widgets = {
            "review_date": forms.DateInput(attrs={"type": "date"}),
            "effectiveness_evidence": forms.Textarea(attrs={"rows": 3}),
            "evidence_description": forms.Textarea(attrs={"rows": 3}),
            "review_findings": forms.Textarea(attrs={"rows": 3}),
            "observed_improvement": forms.Textarea(attrs={"rows": 3}),
            "remaining_risk_gap": forms.Textarea(attrs={"rows": 3}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }


class CAPAClosureForm(BaseEHSForm):
    class Meta:
        model = CAPA
        fields = [
            "closure_remarks",
            "lessons_learned",
            "final_recommendations",
        ]
        widgets = {
            "closure_remarks": forms.Textarea(attrs={"rows": 3}),
            "lessons_learned": forms.Textarea(attrs={"rows": 3}),
            "final_recommendations": forms.Textarea(attrs={"rows": 3}),
        }


class CAPAAttachmentForm(BaseEHSForm):
    class Meta:
        model = CAPAAttachment
        fields = ["file", "title", "description", "action"]


class CAPACommentForm(BaseEHSForm):
    class Meta:
        model = CAPAComment
        fields = ["comment"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 3})}


class CAPAReopenForm(forms.Form):
    reason = forms.CharField(
        label="Reason for reopening",
        required=True,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "class": "form-control",
                "placeholder": "Explain why this CAPA needs to be reopened",
            }
        ),
    )


class CAPAFilterForm(forms.Form):
    plant = forms.ModelChoiceField(queryset=Plant.objects.filter(is_active=True), required=False, empty_label="All")
    department = forms.ModelChoiceField(queryset=Department.objects.filter(is_active=True), required=False, empty_label="All")
    owner = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True, is_superuser=False), required=False, empty_label="All")
    source_type = forms.ChoiceField(choices=[("", "All")] + list(CAPA.SourceType.choices), required=False)
    severity = forms.ChoiceField(choices=[("", "All")] + list(CAPA.Severity.choices), required=False)
    priority = forms.ChoiceField(choices=[("", "All")] + list(CAPA.Priority.choices), required=False)
    status = forms.ChoiceField(choices=[("", "All")] + list(CAPA.Status.choices), required=False)
