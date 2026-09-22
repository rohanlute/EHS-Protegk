from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.organizations.models import Department, Location, Plant, Zone

from .models import (
    ErgonomicAssessment,
    ErgonomicAssessmentMethod,
    ErgonomicAssessmentSchedule,
    ErgonomicControl,
    ErgonomicCorrectiveAction,
    ErgonomicJobMapping,
    ErgonomicObservation,
    ErgonomicReassessment,
    SnookCirielloAssessment,
    ErgonomicRiskFactor,
    MSDDiscomfort,
    OWASAssessment,
    OCRAAssessment,
    StrainIndexAssessment,
    NIOSHLiftingAssessment,
    REBAAssessment,
    RULAAssessment,
)

User = get_user_model()

TEXT = {"class": "form-control"}
DATE = {"class": "form-control", "type": "date"}
CHECK = {"class": "form-check-input"}
AREA = {"class": "form-control", "rows": 3}


# =============================================================================
# DATE INPUT WIDGET — ISO format so the browser accepts the value
# =============================================================================
class FormattedDateInput(forms.DateInput):
    """
    Date input that always renders values as YYYY-MM-DD.

    The browser's native <input type="date"> only accepts ISO-format values.
    Without this, Django renders dates in the locale format (e.g. `22/09/2026`)
    and the browser silently clears the field.
    """
    input_type = "date"
    format = "%Y-%m-%d"

    def __init__(self, attrs=None):
        default_attrs = {"class": "form-control", "type": "date"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


# =============================================================================
# BASE STYLED FORM
# =============================================================================
class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update(CHECK)
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update(AREA)
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({"class": "form-control", "type": "date"})
            else:
                field.widget.attrs.update(TEXT)

        if "plant" in self.fields:
            qs = Plant.objects.filter(is_active=True)
            if user and not user.is_superuser and hasattr(user, "get_all_plants"):
                plants = user.get_all_plants()
                qs = qs.filter(id__in=[plant.id for plant in plants]) if plants else qs.none()
            self.fields["plant"].queryset = qs

        if "department" in self.fields:
            self.fields["department"].queryset = Department.objects.filter(is_active=True)

        if "zone" in self.fields:
            self.fields["zone"].queryset = Zone.objects.filter(is_active=True)

        if "location" in self.fields:
            self.fields["location"].queryset = Location.objects.filter(is_active=True)

        if "assessment" in self.fields:
            # Some forms (e.g. Corrective Action) keep "assessment" as a
            # user-editable dropdown rather than having it set by the view
            # from a URL segment. Scope it the same way "plant" is scoped so
            # a user can never link a record to an assessment outside their
            # accessible plants.
            qs = ErgonomicAssessment.objects.select_related("plant")
            if user and not user.is_superuser and hasattr(user, "get_all_plants"):
                plants = user.get_all_plants()
                qs = qs.filter(plant__in=plants) if plants else qs.none()
            self.fields["assessment"].queryset = qs

        for name in ["worker", "assessor", "responsible_person", "verified_by", "assigned_to"]:
            if name in self.fields:
                self.fields[name].queryset = User.objects.filter(is_active=True).order_by(
                    "first_name", "last_name"
                )


# =============================================================================
# ERGONOMIC ASSESSMENT
# =============================================================================
class ErgonomicAssessmentForm(StyledModelForm):
    class Meta:
        model = ErgonomicAssessment
        fields = [
            "plant",
            "department",
            "zone",
            "location",
            "area",
            "job_role",
            "task",
            "worker",
            "workers_exposed",
            "shift",
            "assessment_date",
            "assessor",
            "task_duration",
            "frequency",
            "exposure_duration",
            "assessment_type",
            "assessment_method",
            "task_description",
            "attachment",
            "next_assessment_date",
            # "status",   ← REMOVED — status is now derived from the workflow
        ]
        widgets = {
            "assessment_date": FormattedDateInput(),
            "next_assessment_date": FormattedDateInput(),
            "task_description": forms.Textarea(attrs=AREA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assessment_method"].queryset = ErgonomicAssessmentMethod.objects.filter(
            is_active=True
        )

    def clean(self):
        cleaned = super().clean()

        assessment_date = cleaned.get("assessment_date")
        next_date = cleaned.get("next_assessment_date")

        # Rule: next assessment date cannot be before the assessment date
        if assessment_date and next_date and next_date < assessment_date:
            self.add_error(
                "next_assessment_date",
                "Next assessment date cannot be before the assessment date.",
            )

        # Rule: assessment method is required
        if not cleaned.get("assessment_method"):
            self.add_error("assessment_method", "Assessment method is required.")

        # Rule: workers exposed must be >= 1
        workers = cleaned.get("workers_exposed")
        if workers is not None and workers < 1:
            self.add_error("workers_exposed", "At least 1 worker must be exposed.")

        # Rule: at least one of worker OR workers_exposed should be present
        if not cleaned.get("worker") and not workers:
            self.add_error(
                "worker",
                "Specify either a named worker or the number of workers exposed.",
            )

        return cleaned


# =============================================================================
# RISK FACTORS
# =============================================================================
class ErgonomicRiskFactorForm(StyledModelForm):
    class Meta:
        model = ErgonomicRiskFactor
        exclude = ["assessment"]


# =============================================================================
# METHOD-SPECIFIC SCORING
# =============================================================================
class RULAForm(StyledModelForm):
    class Meta:
        model = RULAAssessment
        exclude = ["assessment"]


class REBAForm(StyledModelForm):
    class Meta:
        model = REBAAssessment
        exclude = ["assessment"]


class NIOSHForm(StyledModelForm):
    class Meta:
        model = NIOSHLiftingAssessment
        exclude = ["assessment", "recommended_weight_limit", "lifting_index"]

    def clean(self):
        cleaned = super().clean()

        for name in [
            "load_weight",
            "horizontal_location",
            "vertical_location",
            "vertical_travel_distance",
            "frequency_lifts_per_minute",
            "duration_hours",
        ]:
            v = cleaned.get(name)
            if v is not None and v < 0:
                self.add_error(name, "Value cannot be negative.")

        asym = cleaned.get("asymmetry_angle")
        if asym is not None and (asym < 0 or asym > 135):
            self.add_error(
                "asymmetry_angle",
                "Asymmetry angle must be between 0 and 135 degrees.",
            )

        return cleaned


class OWASForm(StyledModelForm):
    class Meta:
        model = OWASAssessment
        exclude = ["assessment"]


class OCRAForm(StyledModelForm):
    class Meta:
        model = OCRAAssessment
        exclude = ["assessment", "ocra_index"]


class StrainIndexForm(StyledModelForm):
    class Meta:
        model = StrainIndexAssessment
        exclude = ["assessment"]


class SnookCirielloForm(StyledModelForm):
    class Meta:
        model = SnookCirielloAssessment
        exclude = ["assessment", "max_acceptable_weight", "ratio"]


# =============================================================================
# QUICK OBSERVATION
# =============================================================================
class ErgonomicObservationForm(StyledModelForm):
    class Meta:
        model = ErgonomicObservation
        exclude = ["assessment", "observer"]
        widgets = {"observation_date": FormattedDateInput()}


# =============================================================================
# CORRECTIVE ACTION — CREATE (new action)
# =============================================================================
class ErgonomicCorrectiveActionCreateForm(forms.ModelForm):
    class Meta:
        model = ErgonomicCorrectiveAction
        fields = [
            "assessment",
            "action_description",
            "root_cause",
            "control_type",
            "responsible_person",
            # "department",   ← REMOVE
            "priority",
            "target_date",
        ]
        widgets = {
            "assessment":          forms.Select(attrs={"class": "form-select"}),
            "action_description":  forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "root_cause":          forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "control_type":        forms.Select(attrs={"class": "form-select"}),
            "responsible_person":  forms.Select(attrs={"class": "form-select"}),
            "priority":            forms.Select(attrs={"class": "form-select"}),
            "target_date":         FormattedDateInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user and not self.user.is_superuser:
            try:
                plants = self.user.get_all_plants()
            except Exception:
                plants = None

            if plants is not None:
                self.fields["assessment"].queryset = (
                    ErgonomicAssessment.objects.filter(plant__in=plants)
                )


class ErgonomicCorrectiveActionDefinitionEditForm(StyledModelForm):
    """
    Edit form for the action definition — same fields as create,
    but Status is displayed as a read-only badge in the template.

    Excludes: status, completion_date, evidence, verification,
              verified_by, verification_date, remarks.
    """
    class Meta:
        model = ErgonomicCorrectiveAction
        fields = [
            "assessment",
            "action_description",
            "root_cause",
            "control_type",
            "responsible_person",
            "department",
            "priority",
            "target_date",
        ]
        widgets = {
            "target_date": FormattedDateInput(),
            "action_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "root_cause": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()

        if not cleaned.get("responsible_person"):
            self.add_error("responsible_person", "Responsible person is required.")

        target = cleaned.get("target_date")
        if target and not self.instance.pk and target < timezone.now().date():
            self.add_error("target_date", "Target date cannot be in the past.")

        return cleaned


# =============================================================================
# CORRECTIVE ACTION — FULL EDIT (EHS verify / close)
# =============================================================================
class ErgonomicCorrectiveActionForm(StyledModelForm):
    """
    Full edit form for EHS Officer / EHS Manager.
    All fields editable, with strong validation on close.
    """
    class Meta:
        model = ErgonomicCorrectiveAction
        exclude = ["action_id", "created_by", "created_at", "updated_at"]
        widgets = {
            "target_date": FormattedDateInput(),
            "completion_date": FormattedDateInput(),
            "verification_date": FormattedDateInput(),
            "action_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "root_cause": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "verification": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()

        # Rule: responsible person is required
        if not cleaned.get("responsible_person"):
            self.add_error("responsible_person", "Responsible person is required.")

        # Rule: target date cannot be in the past (new records only)
        target = cleaned.get("target_date")
        if target and not self.instance.pk and target < timezone.now().date():
            self.add_error("target_date", "Target date cannot be in the past.")

        # Rule: closing requires evidence + verification + verifier + date
        status = cleaned.get("status")
        if status == "CLOSED":
            if not cleaned.get("evidence"):
                self.add_error("evidence", "Evidence is required to close this action.")
            if not cleaned.get("verification"):
                self.add_error("verification", "Verification is required to close this action.")
            if not cleaned.get("verified_by"):
                self.add_error("verified_by", "Verifier is required to close this action.")
            if not cleaned.get("verification_date"):
                self.add_error("verification_date", "Verification date is required to close this action.")

            # Rule: must have been PENDING_VERIFICATION first
            if self.instance.pk and self.instance.status not in {
                "PENDING_VERIFICATION", "COMPLETED", "CLOSED"
            }:
                self.add_error(
                    "status",
                    "Action must reach Pending Verification before it can be closed.",
                )

        # Rule: COMPLETED requires evidence
        if status == "COMPLETED":
            if not cleaned.get("evidence"):
                self.add_error("evidence", "Evidence is required before marking this action completed.")

        return cleaned


# =============================================================================
# CORRECTIVE ACTION — REJECTION
# =============================================================================
class CorrectiveActionRejectForm(forms.Form):
    """
    Form for rejecting a corrective action.
    Renders as a modal on the verification detail page.
    """
    rejection_remark = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Explain what needs to be fixed or re-done...",
            }
        ),
        label="Reason for Rejection",
        required=True,
        max_length=1000,
    )

    def clean_rejection_remark(self):
        remark = self.cleaned_data.get("rejection_remark", "").strip()
        if len(remark) < 10:
            raise ValidationError(
                "Please provide a meaningful reason (at least 10 characters)."
            )
        return remark


# =============================================================================
# CORRECTIVE ACTION — RESPONSIBLE PERSON RESTRICTED EDIT
# =============================================================================
class MyActionUpdateForm(StyledModelForm):
    """
    Responsible person's update form.
    Status is NOT included — the view forces PENDING_VERIFICATION on save.
    Evidence and Completion Date are required.
    """
    class Meta:
        model = ErgonomicCorrectiveAction
        fields = ["evidence", "completion_date", "remarks"]
        widgets = {
            "completion_date": FormattedDateInput(),
            "evidence": forms.FileInput(attrs={
                "class": "form-control",
                "accept": "image/*,.pdf,.doc,.docx",
            }),
            "remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        # Inject the completion_date default via the form's `initial` kwarg
        # BEFORE calling super(). This is the only reliable way — assigning
        # to `self.fields["completion_date"].initial` after construction
        # does not always propagate to the rendered widget.
        initial = kwargs.get("initial") or {}
        if "completion_date" not in initial:
            instance = kwargs.get("instance")
            data = kwargs.get("data")
            if not data:  # only on GET, not POST
                if instance is None or not instance.completion_date:
                    initial["completion_date"] = timezone.now().date()
        kwargs["initial"] = initial

        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()

        if not cleaned.get("evidence") and not self.instance.evidence:
            self.add_error(
                "evidence",
                "Please upload evidence before submitting.",
            )

        if not cleaned.get("completion_date"):
            self.add_error(
                "completion_date",
                "Please set the completion date.",
            )

        return cleaned


# =============================================================================
# CONTROLS
# =============================================================================
class ErgonomicControlForm(StyledModelForm):
    class Meta:
        model = ErgonomicControl
        # "assessment" is excluded: the create URL is always
        # assessments/<assessment_pk>/controls/create/, and the view attaches
        # the parent assessment automatically.
        exclude = ["assessment", "created_by", "created_at"]
        widgets = {"implementation_date": FormattedDateInput()}


# =============================================================================
# REASSESSMENT
# =============================================================================
class ErgonomicReassessmentForm(StyledModelForm):
    class Meta:
        model = ErgonomicReassessment
        exclude = ["assessment", "risk_reduction_percent", "created_at"]
        widgets = {"reassessment_date": FormattedDateInput()}

    def clean(self):
        cleaned = super().clean()

        prev = cleaned.get("previous_score")
        new = cleaned.get("new_score")

        if prev is not None and prev < 0:
            self.add_error("previous_score", "Previous score cannot be negative.")
        if new is not None and new < 0:
            self.add_error("new_score", "New score cannot be negative.")

        return cleaned


# =============================================================================
# MSD / DISCOMFORT
# =============================================================================
class MSDDiscomfortForm(StyledModelForm):
    class Meta:
        model = MSDDiscomfort
        exclude = ["created_by", "created_at"]
        widgets = {"date_reported": FormattedDateInput()}


# =============================================================================
# EMPLOYEE / JOB MAPPING
# =============================================================================
class ErgonomicJobMappingForm(StyledModelForm):
    class Meta:
        model = ErgonomicJobMapping
        fields = "__all__"


# =============================================================================
# ASSESSMENT SCHEDULE
# =============================================================================
class ErgonomicAssessmentScheduleForm(StyledModelForm):
    class Meta:
        model = ErgonomicAssessmentSchedule
        exclude = ["created_by", "created_at"]
        widgets = {"due_date": FormattedDateInput()}


# =============================================================================
# ASSESSMENT METHOD MASTER
# =============================================================================
class ErgonomicAssessmentMethodForm(StyledModelForm):
    class Meta:
        model = ErgonomicAssessmentMethod
        exclude = ["created_by", "created_at", "updated_at"]