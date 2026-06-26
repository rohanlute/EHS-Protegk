from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone
from apps.organizations.models import Department, Location, Plant, SubLocation, Zone
from .models import *

User = get_user_model()

TEXT_INPUT = {"class": "form-control"}
SELECT = {"class": "form-control"}
TEXTAREA = {"class": "form-control", "rows": 3}
DATE_INPUT = {"class": "form-control", "type": "date"}
TIME_INPUT = {"class": "form-control", "type": "time"}
NUMBER_INPUT = {"class": "form-control"}
FILE_INPUT = {"class": "form-control-file"}
CHECKBOX = {"class": "form-check-input"}

def set_default_location_hierarchy(self):
    """
    Auto select first assigned plant -> zone -> location -> sublocation
    """

    if not self.user:
        return
    assigned_plants = self.fields["plant"].queryset
    first_plant = assigned_plants.order_by("name").first()

    if first_plant:
        self.initial.setdefault("plant", first_plant.pk)
        self.fields["zone"].queryset = Zone.objects.filter(
            plant=first_plant,
            is_active=True,
        ).order_by("name")

    assigned_zones = self.user.assigned_zones.filter(
        is_active=True,
        plant=first_plant if first_plant else None,
    )

    first_zone = assigned_zones.order_by("name").first()

    if first_zone:
        self.initial.setdefault("zone", first_zone.pk)
        self.fields["location"].queryset = Location.objects.filter(
            zone=first_zone,
            is_active=True,
        ).order_by("name")

    assigned_locations = self.user.assigned_locations.filter(
        is_active=True,
        zone=first_zone if first_zone else None,
    )
    first_location = assigned_locations.order_by("name").first()
    if first_location:
        self.initial.setdefault("location", first_location.pk)
        self.fields["sublocation"].queryset = SubLocation.objects.filter(
            location=first_location,
            is_active=True,
        ).order_by("name")
    assigned_sublocations = self.user.assigned_sublocations.filter(
        is_active=True,
        location=first_location if first_location else None,
    )
    first_sublocation = assigned_sublocations.order_by("name").first()

    if first_sublocation:
        self.initial.setdefault("sublocation", first_sublocation.pk)


class EmergencyTopicForm(forms.ModelForm):
    class Meta:
        model = EmergencyTopic
        fields = [
            "name",
            "code",
            "category",
            "description",
            "validity_period_days",
            "passing_score",
            "is_mandatory",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={**TEXT_INPUT, "placeholder": "e.g. Fire Drill Readiness"}),
            "code": forms.TextInput(
                attrs={**TEXT_INPUT, "placeholder": "e.g. FIRE-01", "style": "text-transform:uppercase;"}
            ),
            "category": forms.Select(attrs=SELECT),
            "description": forms.Textarea(
                attrs={**TEXTAREA, "placeholder": "Describe what this emergency topic covers..."}
            ),
            "validity_period_days": forms.NumberInput(attrs={**NUMBER_INPUT, "min": 1, "max": 3650}),
            "passing_score": forms.NumberInput(attrs={**NUMBER_INPUT, "min": 0, "max": 100}),
            "is_mandatory": forms.CheckboxInput(attrs=CHECKBOX),
            "is_active": forms.CheckboxInput(attrs=CHECKBOX),
        }

    def clean_code(self):
        return self.cleaned_data.get("code", "").strip().upper()


class EmergencySessionForm(forms.ModelForm):
    class Meta:
        model = EmergencySession
        fields = [
            "topic",
            "drill_type",
            "scheduled_date",
            "scheduled_time",
            "end_time",
            "duration_hours",
            "plant",
            "zone",
            "location",
            "sublocation",
            "venue_details",
            "agenda",
            "max_participants",
            "remarks",
            "attachment",
        ]
        widgets = {
            "topic": forms.Select(attrs=SELECT),
            "drill_type": forms.Select(attrs=SELECT),
            "scheduled_date": forms.DateInput(attrs=DATE_INPUT),
            "scheduled_time": forms.TimeInput(attrs=TIME_INPUT),
            "end_time": forms.TimeInput(attrs=TIME_INPUT),
            "duration_hours": forms.NumberInput(attrs={**NUMBER_INPUT, "step": "0.5", "min": "0.5"}),
            "plant": forms.Select(attrs=SELECT),
            "zone": forms.Select(attrs=SELECT),
            "location": forms.Select(attrs=SELECT),
            "sublocation": forms.Select(attrs=SELECT),
            "venue_details": forms.TextInput(
                attrs={**TEXT_INPUT, "placeholder": "e.g. Assembly Point A, Main Yard"}
            ),
            "agenda": forms.Textarea(
                attrs={**TEXTAREA, "rows": 4, "placeholder": "List the drill agenda and emergency actions..."}
            ),
            "max_participants": forms.NumberInput(attrs={**NUMBER_INPUT, "min": 1}),
            "remarks": forms.Textarea(
                attrs={**TEXTAREA, "placeholder": "Any additional notes or special instructions..."}
            ),
            "attachment": forms.FileInput(attrs=FILE_INPUT),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user:
            assigned_plants = self.user.assigned_plants.filter(is_active=True)
            self.fields["plant"].queryset = assigned_plants
            if assigned_plants.count() == 1:
                self.fields["zone"].queryset = self.user.assigned_zones.filter(
                    is_active=True,
                    plant=assigned_plants.first(),
                )
            else:
                self.fields["zone"].queryset = Zone.objects.filter(
                    plant__in=assigned_plants,
                    is_active=True,
                )
            self.fields["location"].queryset = self.user.assigned_locations.filter(is_active=True)
            self.fields["sublocation"].queryset = self.user.assigned_sublocations.filter(is_active=True)
        else:
            self.fields["plant"].queryset = Plant.objects.filter(is_active=True)
            self.fields["zone"].queryset = Zone.objects.filter(is_active=True)
            self.fields["location"].queryset = Location.objects.filter(is_active=True)
            self.fields["sublocation"].queryset = SubLocation.objects.filter(is_active=True)

        self.fields["topic"].queryset = EmergencyTopic.objects.filter(is_active=True).order_by("name")
        self.fields["topic"].empty_label = "-- Select Emergency Topic --"
        self.fields["plant"].empty_label = "-- Select Plant --"
        self.fields["zone"].empty_label = "-- Select Zone --"
        self.fields["location"].empty_label = "-- Select Location --"
        self.fields["sublocation"].empty_label = "-- Select Sub-Location --"

        self.fields["drill_type"].choices = [("", "-- Select Drill Type --"), *EmergencySession.DRILL_TYPE_CHOICES]

    def clean(self):
        cleaned_data = super().clean()
        scheduled_date = cleaned_data.get("scheduled_date")
        scheduled_time = cleaned_data.get("scheduled_time")
        end_time = cleaned_data.get("end_time")

        if not self.instance.pk and scheduled_date and scheduled_date < timezone.now().date():
            self.add_error("scheduled_date", "Scheduled date cannot be in the past.")

        if scheduled_time and end_time and end_time <= scheduled_time:
            self.add_error("end_time", "End time must be after scheduled start time.")

        return cleaned_data


class EmergencySessionTrainerForm(forms.ModelForm):
    class Meta:
        model = EmergencySessionTrainer
        fields = [
            "trainer_department",
            "trainer_user",
        ]
        widgets = {
            "trainer_department": forms.Select(attrs=SELECT),
            "trainer_user": forms.Select(attrs=SELECT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["trainer_department"].queryset = Department.objects.filter(is_active=True).order_by("name")
        self.fields["trainer_department"].required = False
        self.fields["trainer_department"].empty_label = "-- Select Department --"
        self.fields["trainer_department"].label = "Department"
        self.fields["trainer_user"].queryset = User.objects.filter(
            is_active=True,
            is_active_employee=True,
            department__isnull=False,
            department__is_active=True,
        ).select_related("department").order_by("first_name", "last_name", "username")
        self.fields["trainer_user"].required = False
        self.fields["trainer_user"].empty_label = "-- Select Trainer --"
        self.fields["trainer_user"].label = "Trainer Name"

        if self.data:
            try:
                department_id = int(self.data.get(self.add_prefix("trainer_department")))
                self.fields["trainer_user"].queryset = self.fields["trainer_user"].queryset.filter(
                    department_id=department_id
                )
            except (TypeError, ValueError):
                self.fields["trainer_user"].queryset = self.fields["trainer_user"].queryset.none()
        elif self.instance.pk:
            department = self.instance.display_department
            if department:
                self.fields["trainer_department"].initial = department.id
                self.fields["trainer_user"].queryset = self.fields["trainer_user"].queryset.filter(
                    department=department
                )
            else:
                self.fields["trainer_user"].queryset = self.fields["trainer_user"].queryset.none()
        else:
            self.fields["trainer_user"].queryset = self.fields["trainer_user"].queryset.none()

    def clean(self):
        cleaned_data = super().clean()
        trainer_user = cleaned_data.get("trainer_user")
        trainer_department = cleaned_data.get("trainer_department")

        if not trainer_user:
            return cleaned_data

        if not trainer_user.department_id:
            self.add_error("trainer_user", "Selected trainer does not have a department assigned.")
            return cleaned_data

        if trainer_department and trainer_department.id != trainer_user.department_id:
            self.add_error("trainer_user", "Selected trainer does not belong to the chosen department.")

        cleaned_data["trainer_department"] = trainer_user.department

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        trainer_user = self.cleaned_data.get("trainer_user")
        if trainer_user:
            instance.trainer_user = trainer_user
            instance.trainer_name = trainer_user.get_full_name() or trainer_user.username
            instance.trainer_department = trainer_user.department
            instance.trainer_designation = ""
            instance.trainer_is_external = False
            instance.trainer_organization = ""
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class BaseEmergencySessionTrainerFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        active_forms = 0
        selected_trainers = set()
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
                trainer_user = form.cleaned_data.get("trainer_user")
                if trainer_user:
                    active_forms += 1
                    if trainer_user.pk in selected_trainers:
                        form.add_error("trainer_user", "This trainer is already added.")
                    selected_trainers.add(trainer_user.pk)
        if active_forms == 0:
            raise forms.ValidationError("Please add at least one trainer.")


EmergencySessionTrainerFormSet = inlineformset_factory(
    EmergencySession,
    EmergencySessionTrainer,
    form=EmergencySessionTrainerForm,
    formset=BaseEmergencySessionTrainerFormSet,
    extra=1,
    can_delete=True,
)


class ERTDepartmentQuestionForm(forms.ModelForm):
    class Meta:
        model = ERTDepartmentQuestion
        fields = [
            "department",
            "topics",
            "question_text",
            "question_type",
            "is_remarks_mandatory",
            "is_photo_required",
            "is_critical",
            "auto_generate_finding",
            "weightage",
            "reference_standard",
            "guidance_notes",
            "is_active",
        ]
        widgets = {
            "department": forms.Select(attrs={"class": "form-control"}),
            "topics": forms.SelectMultiple(attrs={"class": "form-control", "size": "6"}),
            "question_text": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Enter the ERT question"}
            ),
            "question_type": forms.Select(attrs={"class": "form-control"}),
            "weightage": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "max": "100", "step": "0.01", "value": "1.00"}
            ),
            "reference_standard": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., SOP, ERP standard, legal reference"}
            ),
            "guidance_notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 2, "placeholder": "Additional guidance for reviewers"}
            ),
            "is_remarks_mandatory": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_photo_required": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_critical": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "auto_generate_finding": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True).order_by("name")
        self.fields["topics"].queryset = EmergencyTopic.objects.filter(is_active=True).order_by("name")
        self.fields["department"].empty_label = "Select Department"
        self.fields["question_type"].choices = [("", "Select Question Type"), *ERTDepartmentQuestion.QUESTION_TYPE_CHOICES]


class EmergencySessionReviewForm(forms.Form):
    reviewer_remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Add reviewer remarks before approving or rejecting...",
            }
        ),
    )


class EmergencyParticipantFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Search employee..."}),
    )


class EmergencyParticipantAddForm(forms.Form):
    employee_ids = forms.ModelMultipleChoiceField(
        queryset=EmergencySessionParticipant.objects.none(),
        required=False,
        widget=forms.MultipleHiddenInput,
    )


class EmergencyReportForm(forms.ModelForm):
    class Meta:
        model = EmergencyReport
        fields = [
            "emergency_title",
            "emergency_type",
            "other_emergency_type",
            "severity_level",
            "incident_date",
            "incident_time",
            "plant",
            "zone",
            "location",
            "sublocation",
            "additional_location_details",
            "department",
            "description",
            "immediate_actions_taken",
            "response_team_members",
        ]
        widgets = {
            "emergency_title": forms.TextInput(
                attrs={**TEXT_INPUT, "placeholder": "Enter emergency title"}
            ),
            "emergency_type": forms.Select(attrs=SELECT),
            "other_emergency_type": forms.TextInput(
                attrs={**TEXT_INPUT, "placeholder": "Specify emergency type"}
            ),
            "severity_level": forms.Select(attrs=SELECT),
            "incident_date": forms.DateInput(attrs=DATE_INPUT),
            "incident_time": forms.TimeInput(attrs=TIME_INPUT),
            "plant": forms.Select(attrs=SELECT),
            "zone": forms.Select(attrs=SELECT),
            "location": forms.Select(attrs=SELECT),
            "sublocation": forms.Select(attrs=SELECT),
            "additional_location_details": forms.Textarea(
                attrs={
                    **TEXTAREA,
                    "rows": 2,
                    "placeholder": "Specific area, equipment, or landmark near the incident",
                }
            ),
            "department": forms.Select(attrs=SELECT),
            "description": forms.Textarea(
                attrs={
                    **TEXTAREA,
                    "rows": 4,
                    "placeholder": "Describe the emergency, sequence of events, and impact",
                }
            ),
            "immediate_actions_taken": forms.Textarea(
                attrs={
                    **TEXTAREA,
                    "rows": 3,
                    "placeholder": "Describe immediate actions taken...",
                }
            ),
            "response_team_members": forms.SelectMultiple(
                attrs={
                    "class": "d-none",
                    "id": "id_response_team_members",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if not self.data and not self.instance.pk:
            set_default_location_hierarchy(self)

        now = timezone.localtime()
        if not self.instance.pk:
            self.fields["incident_date"].initial = now.date()
            self.fields["incident_time"].initial = now.strftime("%H:%M")

        self.fields["emergency_type"].choices = [
            ("", "-- Select Emergency Type --"),
            *EmergencyReport.EMERGENCY_TYPE_CHOICES,
        ]
        self.fields["severity_level"].choices = [
            ("", "-- Select Severity Level --"),
            *EmergencyReport.SEVERITY_CHOICES,
        ]

        self.fields["plant"].empty_label = "-- Select Plant --"
        self.fields["zone"].empty_label = "-- Select Zone --"
        self.fields["location"].empty_label = "-- Select Location --"
        self.fields["sublocation"].empty_label = "-- Select Sub-Location --"
        self.fields["department"].empty_label = "-- Select Department --"

        self.fields["zone"].required = False
        self.fields["sublocation"].required = False
        self.fields["other_emergency_type"].required = False
        self.fields["additional_location_details"].required = False
        self.fields["immediate_actions_taken"].required = False

        self.fields["department"].queryset = Department.objects.filter(is_active=True).order_by("name")
        self.fields["response_team_members"].queryset = User.objects.none()
        self.fields["response_team_members"].required = False

        if self.user:
            assigned_plants = self.user.assigned_plants.filter(is_active=True)
            if assigned_plants.exists():
                self.fields["plant"].queryset = assigned_plants.order_by("name")
                self.fields["zone"].queryset = Zone.objects.filter(
                    plant__in=assigned_plants,
                    is_active=True,
                ).distinct().order_by("name")
                self.fields["location"].queryset = Location.objects.filter(
                    zone__plant__in=assigned_plants,
                    is_active=True,
                ).distinct().order_by("name")
                self.fields["sublocation"].queryset = SubLocation.objects.filter(
                    location__zone__plant__in=assigned_plants,
                    is_active=True,
                ).distinct().order_by("name")
            else:
                self.fields["plant"].queryset = Plant.objects.filter(is_active=True).order_by("name")
                self.fields["zone"].queryset = Zone.objects.none()
                self.fields["location"].queryset = Location.objects.none()
                self.fields["sublocation"].queryset = SubLocation.objects.none()
        else:
            self.fields["plant"].queryset = Plant.objects.filter(is_active=True).order_by("name")
            self.fields["zone"].queryset = Zone.objects.filter(is_active=True).order_by("name")
            self.fields["location"].queryset = Location.objects.filter(is_active=True).order_by("name")
            self.fields["sublocation"].queryset = SubLocation.objects.filter(is_active=True).order_by("name")

        if self.data:
            try:
                plant_id = int(self.data.get("plant"))
                self.fields["zone"].queryset = Zone.objects.filter(
                    plant_id=plant_id,
                    is_active=True,
                ).order_by("name")
            except (TypeError, ValueError):
                pass

            try:
                zone_id = int(self.data.get("zone"))
                self.fields["location"].queryset = Location.objects.filter(
                    zone_id=zone_id,
                    is_active=True,
                ).order_by("name")
            except (TypeError, ValueError):
                pass

            try:
                location_id = int(self.data.get("location"))
                self.fields["sublocation"].queryset = SubLocation.objects.filter(
                    location_id=location_id,
                    is_active=True,
                ).order_by("name")
            except (TypeError, ValueError):
                pass

            try:
                department_id = int(self.data.get("department"))
                self.fields["response_team_members"].queryset = User.objects.filter(
                    department_id=department_id,
                    is_active=True,
                    is_active_employee=True,
                ).order_by("first_name", "last_name", "username")
            except (TypeError, ValueError):
                pass
        elif self.instance.pk:
            if self.instance.plant:
                self.fields["zone"].queryset = Zone.objects.filter(
                    plant=self.instance.plant,
                    is_active=True,
                ).order_by("name")
            if self.instance.zone:
                self.fields["location"].queryset = Location.objects.filter(
                    zone=self.instance.zone,
                    is_active=True,
                ).order_by("name")
            if self.instance.location:
                self.fields["sublocation"].queryset = SubLocation.objects.filter(
                    location=self.instance.location,
                    is_active=True,
                ).order_by("name")
            if self.instance.department_id:
                self.fields["response_team_members"].queryset = User.objects.filter(
                    department_id=self.instance.department_id,
                    is_active=True,
                    is_active_employee=True,
                ).order_by("first_name", "last_name", "username")
        elif self.user:
            assigned_plants = self.user.assigned_plants.filter(is_active=True)
            if assigned_plants.count() == 1:
                self.initial["plant"] = assigned_plants.first().pk

    def clean_incident_date(self):
        incident_date = self.cleaned_data.get("incident_date")
        if incident_date and incident_date > timezone.localdate():
            raise forms.ValidationError("Date of incident cannot be in the future.")
        return incident_date

    def clean(self):
        cleaned_data = super().clean()
        emergency_type = cleaned_data.get("emergency_type")
        other_emergency_type = (cleaned_data.get("other_emergency_type") or "").strip()
        plant = cleaned_data.get("plant")
        zone = cleaned_data.get("zone")
        location = cleaned_data.get("location")
        sublocation = cleaned_data.get("sublocation")

        if emergency_type == "OTHER" and not other_emergency_type:
            self.add_error("other_emergency_type", "Please specify the emergency type.")

        if zone and plant and zone.plant_id != plant.id:
            self.add_error("zone", "Selected zone does not belong to the selected plant.")

        if location and zone and location.zone_id != zone.id:
            self.add_error("location", "Selected location does not belong to the selected zone.")

        if sublocation and location and sublocation.location_id != location.id:
            self.add_error("sublocation", "Selected sub-location does not belong to the selected location.")

        return cleaned_data


class EmergencySOSReportForm(forms.ModelForm):
    class Meta:
        model = EmergencyReport
        fields = [
            "emergency_title",
            "emergency_type",
            "other_emergency_type",
            "severity_level",
            "incident_department",
            "plant",
            "zone",
            "location",
            "sublocation",
            "description",
        ]
        widgets = {
            "emergency_title": forms.TextInput(attrs={**TEXT_INPUT, "readonly": "readonly"}),
            "emergency_type": forms.Select(attrs=SELECT),
            "other_emergency_type": forms.TextInput(attrs={**TEXT_INPUT, "placeholder": "Specify emergency type"}),
            "severity_level": forms.Select(attrs=SELECT),
            "incident_department": forms.Select(attrs=SELECT),
            "plant": forms.Select(attrs=SELECT),
            "zone": forms.Select(attrs=SELECT),
            "location": forms.Select(attrs=SELECT),
            "sublocation": forms.Select(attrs=SELECT),
            "description": forms.Textarea(
                attrs={**TEXTAREA, "rows": 5, "placeholder": "Describe the emergency situation clearly..."}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if not self.data and not self.instance.pk:
            set_default_location_hierarchy(self)

        self.fields["emergency_type"].choices = [("", "-- Select Emergency Type --"), *EmergencyReport.EMERGENCY_TYPE_CHOICES]
        self.fields["severity_level"].choices = [("", "-- Select Severity Level --"), *EmergencyReport.SEVERITY_CHOICES]
        self.fields["incident_department"].queryset = Department.objects.filter(is_active=True).order_by("name")
        self.fields["incident_department"].empty_label = "-- Select Incident Department --"
        self.fields["incident_department"].required = True
        self.fields["incident_department"].label = "Incident Department"
        self.fields["plant"].empty_label = "-- Select Plant --"
        self.fields["zone"].empty_label = "-- Select Zone --"
        self.fields["location"].empty_label = "-- Select Location --"
        self.fields["sublocation"].empty_label = "-- Select Sub-Location --"
        self.fields["zone"].required = False
        self.fields["sublocation"].required = False
        self.fields["other_emergency_type"].required = False

        if self.user:
            assigned_plants = self.user.assigned_plants.filter(is_active=True)
            if assigned_plants.exists():
                self.fields["plant"].queryset = assigned_plants.order_by("name")
                self.fields["zone"].queryset = Zone.objects.filter(plant__in=assigned_plants, is_active=True).distinct().order_by("name")
                self.fields["location"].queryset = Location.objects.filter(zone__plant__in=assigned_plants, is_active=True).distinct().order_by("name")
                self.fields["sublocation"].queryset = SubLocation.objects.filter(location__zone__plant__in=assigned_plants, is_active=True).distinct().order_by("name")
            elif self.user.plant_id:
                self.fields["plant"].queryset = Plant.objects.filter(pk=self.user.plant_id, is_active=True)
                self.fields["zone"].queryset = Zone.objects.filter(plant_id=self.user.plant_id, is_active=True).order_by("name")
                self.fields["location"].queryset = Location.objects.filter(zone__plant_id=self.user.plant_id, is_active=True).order_by("name")
                self.fields["sublocation"].queryset = SubLocation.objects.filter(location__zone__plant_id=self.user.plant_id, is_active=True).order_by("name")
            else:
                self.fields["plant"].queryset = Plant.objects.filter(is_active=True).order_by("name")
                self.fields["zone"].queryset = Zone.objects.none()
                self.fields["location"].queryset = Location.objects.none()
                self.fields["sublocation"].queryset = SubLocation.objects.none()
        else:
            self.fields["plant"].queryset = Plant.objects.filter(is_active=True).order_by("name")
            self.fields["zone"].queryset = Zone.objects.filter(is_active=True).order_by("name")
            self.fields["location"].queryset = Location.objects.filter(is_active=True).order_by("name")
            self.fields["sublocation"].queryset = SubLocation.objects.filter(is_active=True).order_by("name")

        if self.data:
            try:
                plant_id = int(self.data.get("plant"))
                self.fields["zone"].queryset = Zone.objects.filter(plant_id=plant_id, is_active=True).order_by("name")
                self.fields["location"].queryset = Location.objects.filter(zone__plant_id=plant_id, is_active=True).order_by("name")
                self.fields["sublocation"].queryset = SubLocation.objects.filter(location__zone__plant_id=plant_id, is_active=True).order_by("name")
            except (TypeError, ValueError):
                pass
            try:
                zone_id = int(self.data.get("zone"))
                self.fields["location"].queryset = Location.objects.filter(zone_id=zone_id, is_active=True).order_by("name")
            except (TypeError, ValueError):
                pass
            try:
                location_id = int(self.data.get("location"))
                self.fields["sublocation"].queryset = SubLocation.objects.filter(location_id=location_id, is_active=True).order_by("name")
            except (TypeError, ValueError):
                pass
        elif self.user:
            assigned_plants = self.user.assigned_plants.filter(is_active=True)
            if assigned_plants.count() == 1:
                self.initial["plant"] = assigned_plants.first().pk
            elif not assigned_plants.exists() and self.user.plant_id:
                self.initial["plant"] = self.user.plant_id

    def clean(self):
        cleaned_data = super().clean()
        emergency_type = cleaned_data.get("emergency_type")
        other_emergency_type = (cleaned_data.get("other_emergency_type") or "").strip()
        plant = cleaned_data.get("plant")
        zone = cleaned_data.get("zone")
        location = cleaned_data.get("location")
        sublocation = cleaned_data.get("sublocation")

        if emergency_type == "OTHER" and not other_emergency_type:
            self.add_error("other_emergency_type", "Please specify the emergency type.")

        if emergency_type:
            emergency_label = dict(EmergencyReport.EMERGENCY_TYPE_CHOICES).get(emergency_type, emergency_type)
            cleaned_data["emergency_title"] = f"SOS-{emergency_label}"

        if zone and plant and zone.plant_id != plant.id:
            self.add_error("zone", "Selected zone does not belong to the selected plant.")
        if location and zone and location.zone_id != zone.id:
            self.add_error("location", "Selected location does not belong to the selected zone.")
        if sublocation and location and sublocation.location_id != location.id:
            self.add_error("sublocation", "Selected sub-location does not belong to the selected location.")

        return cleaned_data


class EmergencyActionItemCompletionForm(forms.ModelForm):
    completion_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                "class": "form-control",
                "type": "datetime-local",
            }
        )
    )

    class Meta:
        model = EmergencyActionItem
        fields = ["completion_datetime", "completion_remarks", "attachment"]
        widgets = {
            "completion_remarks": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe how the emergency action was completed...",
                }
            ),
            "attachment": forms.FileInput(attrs={"class": "form-control-file"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get("completion_datetime"):
            self.fields["completion_datetime"].initial = timezone.localtime().strftime("%Y-%m-%dT%H:%M")


class EmergencyInvestigationReportForm(forms.ModelForm):
    investigation_team = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Enter email(s), separated by commas. e.g. user1@example.com, user2@example.com",
            }
        ),
    )

    class Meta:
        model = EmergencyInvestigationReport
        fields = [
            "investigation_date",
            "investigation_team",
            "sequence_of_events",
            "root_cause_analysis",
            "evidence_collected",
            "witness_statements",
            "immediate_corrective_actions",
            "preventive_measures",
            "completed_date",
        ]
        widgets = {
            "investigation_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "sequence_of_events": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "root_cause_analysis": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "evidence_collected": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "witness_statements": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "immediate_corrective_actions": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "preventive_measures": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "completed_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def clean_investigation_team(self):
        data = self.cleaned_data.get("investigation_team", "")
        emails = [email.strip() for email in data.split(",") if email.strip()]
        if not emails:
            raise ValidationError("At least one email address is required.")
        for email in emails:
            validate_email(email)
        return ", ".join(emails)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            today = timezone.localdate()
            self.fields["investigation_date"].initial = today
            self.fields["completed_date"].initial = today


class EmergencyCAPACreateForm(forms.ModelForm):
    class Meta:
        model = EmergencyCAPA
        fields = ["action_required", "assigned_to", "target_date"]
        widgets = {
            "action_required": forms.Textarea(
                attrs={**TEXTAREA, "rows": 4, "placeholder": "Describe the corrective / preventive action required"}
            ),
            "assigned_to": forms.Select(attrs=SELECT),
            "target_date": forms.DateInput(attrs=DATE_INPUT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = (
            User.objects.filter(is_active=True, is_active_employee=True)
            .exclude(Q(is_superuser=True) | Q(role__name="ADMIN"))
            .order_by("first_name", "username")
        )
        self.fields["assigned_to"].empty_label = "-- Select Assignee --"


class EmergencyCAPAUpdateForm(forms.ModelForm):
    class Meta:
        model = EmergencyCAPA
        fields = ["action_taken", "status", "evidence", "closure_remarks"]
        widgets = {
            "action_taken": forms.Textarea(
                attrs={**TEXTAREA, "rows": 4, "placeholder": "Describe the action taken or implementation progress"}
            ),
            "status": forms.Select(attrs=SELECT),
            "evidence": forms.FileInput(attrs=FILE_INPUT),
            "closure_remarks": forms.Textarea(
                attrs={**TEXTAREA, "rows": 3, "placeholder": "Add remarks when closing the CAPA"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        action_taken = (cleaned_data.get("action_taken") or "").strip()
        closure_remarks = (cleaned_data.get("closure_remarks") or "").strip()

        if status in [EmergencyCAPA.STATUS_IN_PROGRESS, EmergencyCAPA.STATUS_CLOSED] and not action_taken:
            self.add_error("action_taken", "Action taken is required when the CAPA is in progress or closed.")
        if status == EmergencyCAPA.STATUS_CLOSED and not closure_remarks:
            self.add_error("closure_remarks", "Closure remarks are required before closing the CAPA.")
        return cleaned_data


class EmergencyClosureForm(forms.ModelForm):
    class Meta:
        model = EmergencyReport
        fields = [
            "closure_remarks",
            "lessons_learned",
            "preventive_measures",
            "is_recurrence_possible",
        ]
        widgets = {
            "closure_remarks": forms.Textarea(
                attrs={**TEXTAREA, "rows": 4, "placeholder": "Provide final closure remarks"}
            ),
            "lessons_learned": forms.Textarea(
                attrs={**TEXTAREA, "rows": 4, "placeholder": "Document the key lessons learned"}
            ),
            "preventive_measures": forms.Textarea(
                attrs={**TEXTAREA, "rows": 4, "placeholder": "List preventive measures implemented"}
            ),
            "is_recurrence_possible": forms.CheckboxInput(attrs=CHECKBOX),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["closure_remarks"].required = True
        self.fields["lessons_learned"].required = True
        self.fields["preventive_measures"].required = True


class ERTDepartmentQuestionFilterForm(forms.Form):
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True).order_by("name"),
        required=False,
        empty_label="All Departments",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    question_type = forms.ChoiceField(
        choices=[("", "All Types"), *ERTDepartmentQuestion.QUESTION_TYPE_CHOICES],
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    is_critical = forms.ChoiceField(
        choices=[("", "All Questions"), ("true", "Critical Only"), ("false", "Non-Critical")],
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Search questions..."}),
    )
