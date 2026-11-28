
from django import forms

from .models import (
    HAZOPStudy,
    HAZOPNode,
    HAZOPStudyType,
    HAZOPStudyStatus,
    HAZOPParameter,
    HAZOPGuideWord,
    HAZOPDeviationTemplate,
    HAZOPStudyMethodology,
    HAZOPStudyPriority,
    HAZOPProcessType,
    HAZOPNodeType,
    HAZOPEquipmentType,
    HAZOPCauseCategory,
    HAZOPConsequenceCategory,
    HAZOPSafeguardCategory,
    HAZOPRecommendationCategory,
    HAZOPSeverity,
    HAZOPLikelihood,
    HAZOPReviewFrequency,
    HAZOPParameterGuideWordMapping,
    HAZOPWorksheetEntry,
    HAZOPCause,
    HAZOPConsequence,
    HAZOPSafeguard,
    HAZOPRiskMatrix,
    HAZOPRiskRating,
    HAZOPRiskLevel,
    HAZOPRiskAssessment,
    HAZOPAction,
    HAZOPRecommendation,
)

from apps.organizations.models import (
    Plant,
    Zone,
    Location,
    SubLocation,
    Department,
)

from django.contrib.auth import get_user_model

User = get_user_model()

class HAZOPBaseModelForm(forms.ModelForm):
    """
    Common styling for HAZOP configuration forms.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    "class": "form-control",
                })
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    "class": "form-check-input",
                })
            else:
                field.widget.attrs.update({
                    "class": "form-control",
                })


class HAZOPStudyTypeForm(HAZOPBaseModelForm):
    class Meta:
        model = HAZOPStudyType
        fields = [
            "code",
            "name",
            "description",
            "is_active",
        ]


class HAZOPStudyStatusForm(HAZOPBaseModelForm):
    class Meta:
        model = HAZOPStudyStatus
        fields = [
            "code",
            "name",
            "description",
            "sequence",
            "is_terminal",
            "is_active",
        ]


class HAZOPParameterForm(HAZOPBaseModelForm):
    class Meta:
        model = HAZOPParameter
        fields = [
            "code",
            "name",
            "description",
            "is_active",
        ]


class HAZOPGuideWordForm(HAZOPBaseModelForm):
    class Meta:
        model = HAZOPGuideWord
        fields = [
            "code",
            "name",
            "description",
            "is_active",
        ]


class HAZOPDeviationTemplateForm(HAZOPBaseModelForm):
    class Meta:
        model = HAZOPDeviationTemplate
        fields = [
            "code",
            "parameter",
            "guide_word",
            "deviation_text",
            "description",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["parameter"].queryset = (
            HAZOPParameter.objects.filter(is_active=True).order_by("name")
        )

        self.fields["guide_word"].queryset = (
            HAZOPGuideWord.objects.filter(is_active=True).order_by("name")
        )



# ============================================================
# COMMON HAZOP CONFIGURATION FORM
# ============================================================

class HAZOPConfigMasterForm(forms.ModelForm):
    """
    Common form for HAZOP configuration masters.
    """

    class Meta:
        fields = [
            "code",
            "name",
            "description",
            "is_active",
        ]

        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter code",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter description",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }



# ============================================================
# HAZOP CONFIGURATION MASTER FORMS
# ============================================================

class HAZOPStudyMethodologyForm(HAZOPConfigMasterForm):
    class Meta(HAZOPConfigMasterForm.Meta):
        model = HAZOPStudyMethodology


class HAZOPStudyPriorityForm(HAZOPConfigMasterForm):
    class Meta(HAZOPConfigMasterForm.Meta):
        model = HAZOPStudyPriority
        fields = HAZOPConfigMasterForm.Meta.fields + [
            "priority_order",
        ]

        widgets = {
            **HAZOPConfigMasterForm.Meta.widgets,
            "priority_order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "placeholder": "Enter priority order",
                }
            ),
        }


class HAZOPProcessTypeForm(HAZOPConfigMasterForm):
    class Meta(HAZOPConfigMasterForm.Meta):
        model = HAZOPProcessType


class HAZOPNodeTypeForm(HAZOPConfigMasterForm):
    class Meta(HAZOPConfigMasterForm.Meta):
        model = HAZOPNodeType


class HAZOPEquipmentTypeForm(HAZOPConfigMasterForm):
    class Meta(HAZOPConfigMasterForm.Meta):
        model = HAZOPEquipmentType


class HAZOPCauseCategoryForm(HAZOPConfigMasterForm):
    class Meta(HAZOPConfigMasterForm.Meta):
        model = HAZOPCauseCategory


class HAZOPConsequenceCategoryForm(HAZOPConfigMasterForm):
    class Meta(HAZOPConfigMasterForm.Meta):
        model = HAZOPConsequenceCategory


class HAZOPSafeguardCategoryForm(HAZOPConfigMasterForm):
    class Meta(HAZOPConfigMasterForm.Meta):
        model = HAZOPSafeguardCategory


class HAZOPRecommendationCategoryForm(HAZOPConfigMasterForm):
    class Meta(HAZOPConfigMasterForm.Meta):
        model = HAZOPRecommendationCategory


class HAZOPSeverityForm(HAZOPConfigMasterForm):
    class Meta(HAZOPConfigMasterForm.Meta):
        model = HAZOPSeverity
        fields = HAZOPConfigMasterForm.Meta.fields + [
            "severity_score",
        ]

        widgets = {
            **HAZOPConfigMasterForm.Meta.widgets,
            "severity_score": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "placeholder": "Enter severity score",
                }
            ),
        }


class HAZOPLikelihoodForm(HAZOPConfigMasterForm):
    class Meta(HAZOPConfigMasterForm.Meta):
        model = HAZOPLikelihood
        fields = HAZOPConfigMasterForm.Meta.fields + [
            "likelihood_score",
        ]

        widgets = {
            **HAZOPConfigMasterForm.Meta.widgets,
            "likelihood_score": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "placeholder": "Enter likelihood score",
                }
            ),
        }


class HAZOPReviewFrequencyForm(HAZOPConfigMasterForm):
    class Meta(HAZOPConfigMasterForm.Meta):
        model = HAZOPReviewFrequency
        fields = HAZOPConfigMasterForm.Meta.fields + [
            "interval_days",
        ]

        widgets = {
            **HAZOPConfigMasterForm.Meta.widgets,
            "interval_days": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "placeholder": "Enter review interval in days",
                }
            ),
        }



# ============================================================
# PARAMETER-GUIDEWORD MAPPING FORM
# ============================================================

class HAZOPParameterGuideWordMappingForm(forms.ModelForm):
    class Meta:
        model = HAZOPParameterGuideWordMapping

        fields = [
            "parameter",
            "guide_word",
            "is_active",
        ]

        widgets = {
            "parameter": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "guide_word": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["parameter"].queryset = (
            HAZOPParameter.objects.filter(is_active=True).order_by("name")
        )

        self.fields["guide_word"].queryset = (
            HAZOPGuideWord.objects.filter(is_active=True).order_by("name")
        )




# ============================================================
# HAZOP STUDY REGISTER FORM
# ============================================================

class HAZOPStudyForm(forms.ModelForm):
    """
    Form for creating and updating HAZOP studies.
    Supports dependent organization dropdowns:
    Plant -> Zone -> Location -> Sub-Location
    """

    class Meta:
        model = HAZOPStudy

        fields = [
            "study_title",
            "study_type",
            "methodology",
            "process_type",
            "priority",
            "status",

            "plant",
            "zone",
            "location",
            "sub_location",
            "department",

            "study_leader",
            "team_members",

            "planned_start_date",
            "planned_end_date",
            "actual_start_date",
            "actual_end_date",

            "review_frequency",
            "next_review_date",

            "study_scope",
            "study_objective",
            "reference_documents",
            "remarks",
        ]

        widgets = {
            "study_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter HAZOP study title",
            }),

            "study_type": forms.Select(attrs={
                "class": "form-control",
            }),

            "methodology": forms.Select(attrs={
                "class": "form-control",
            }),

            "process_type": forms.Select(attrs={
                "class": "form-control",
            }),

            "priority": forms.Select(attrs={
                "class": "form-control",
            }),

            "status": forms.Select(attrs={
                "class": "form-control",
            }),

            "plant": forms.Select(attrs={
                "class": "form-control",
            }),

            "zone": forms.Select(attrs={
                "class": "form-control",
            }),

            "location": forms.Select(attrs={
                "class": "form-control",
            }),

            "sub_location": forms.Select(attrs={
                "class": "form-control",
            }),

            "department": forms.Select(attrs={
                "class": "form-control",
            }),

            "study_leader": forms.Select(attrs={
                "class": "form-control",
            }),

            "team_members": forms.SelectMultiple(attrs={
                "class": "form-control",
                "size": 5,
            }),

            "planned_start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),

            "planned_end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),

            "actual_start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),

            "actual_end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),

            "review_frequency": forms.Select(attrs={
                "class": "form-control",
            }),

            "next_review_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),

            "study_scope": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Define the process boundaries and study scope",
            }),

            "study_objective": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter the objective of this HAZOP study",
            }),

            "reference_documents": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter P&ID numbers, drawings and reference documents",
            }),

            "remarks": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Additional remarks",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ----------------------------------------------------
        # ACTIVE CONFIGURATION MASTER FILTERS
        # ----------------------------------------------------

        self.fields["study_type"].queryset = (
            HAZOPStudyType.objects
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["methodology"].queryset = (
            HAZOPStudyMethodology.objects
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["process_type"].queryset = (
            HAZOPProcessType.objects
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["priority"].queryset = (
            HAZOPStudyPriority.objects
            .filter(is_active=True)
            .order_by("priority_order", "name")
        )

        self.fields["status"].queryset = (
            HAZOPStudyStatus.objects
            .filter(is_active=True)
            .order_by("sequence", "name")
        )

        self.fields["review_frequency"].queryset = (
            HAZOPReviewFrequency.objects
            .filter(is_active=True)
            .order_by("interval_days")
        )

        # ----------------------------------------------------
        # ORGANIZATION DROPDOWNS
        # ----------------------------------------------------

        self.fields["plant"].queryset = (
            Plant.objects
            .filter(is_active=True)
            .order_by("name")
        )

        # Start with empty dependent dropdowns.
        self.fields["zone"].queryset = Zone.objects.none()
        self.fields["location"].queryset = Location.objects.none()
        self.fields["sub_location"].queryset = SubLocation.objects.none()

        # ----------------------------------------------------
        # GET SELECTED VALUES
        # ----------------------------------------------------
        # On POST, use submitted values.
        # On GET/edit, use existing instance values.
        # This block must NOT be nested inside the instance check.

        if self.is_bound:
            plant_id = self.data.get(self.add_prefix("plant"))
            zone_id = self.data.get(self.add_prefix("zone"))
            location_id = self.data.get(self.add_prefix("location"))

        elif self.instance and self.instance.pk:
            plant_id = self.instance.plant_id
            zone_id = self.instance.zone_id
            location_id = self.instance.location_id

        else:
            plant_id = None
            zone_id = None
            location_id = None

        # ----------------------------------------------------
        # PLANT -> ZONE
        # ----------------------------------------------------

        if plant_id:
            try:
                plant_id = int(plant_id)

                self.fields["zone"].queryset = (
                    Zone.objects
                    .filter(
                        plant_id=plant_id,
                        is_active=True,
                    )
                    .order_by("name")
                )

            except (ValueError, TypeError):
                self.fields["zone"].queryset = Zone.objects.none()

        # ----------------------------------------------------
        # ZONE -> LOCATION
        # ----------------------------------------------------

        if zone_id:
            try:
                zone_id = int(zone_id)

                self.fields["location"].queryset = (
                    Location.objects
                    .filter(
                        zone_id=zone_id,
                        is_active=True,
                    )
                    .order_by("name")
                )

            except (ValueError, TypeError):
                self.fields["location"].queryset = Location.objects.none()

        # ----------------------------------------------------
        # LOCATION -> SUB-LOCATION
        # ----------------------------------------------------

        if location_id:
            try:
                location_id = int(location_id)

                self.fields["sub_location"].queryset = (
                    SubLocation.objects
                    .filter(
                        location_id=location_id,
                        is_active=True,
                    )
                    .order_by("name")
                )

            except (ValueError, TypeError):
                self.fields["sub_location"].queryset = (
                    SubLocation.objects.none()
                )

        # ----------------------------------------------------
        # DEPARTMENT
        # ----------------------------------------------------

        self.fields["department"].queryset = (
            Department.objects
            .filter(is_active=True)
            .order_by("name")
        )

        # ----------------------------------------------------
        # STUDY LEADER AND TEAM MEMBERS
        # ----------------------------------------------------

        self.fields["study_leader"].queryset = (
            User.objects
            .filter(is_active=True)
            .order_by("username")
        )

        self.fields["team_members"].queryset = (
            User.objects
            .filter(is_active=True)
            .order_by("username")
        )

        # ----------------------------------------------------
        # FIELD LABELS
        # ----------------------------------------------------

        self.fields["study_title"].label = "Study Title"
        self.fields["study_type"].label = "Study Type"
        self.fields["methodology"].label = "Study Methodology"
        self.fields["process_type"].label = "Process Type"
        self.fields["priority"].label = "Study Priority"
        self.fields["status"].label = "Study Status"

        self.fields["plant"].label = "Plant"
        self.fields["zone"].label = "Zone"
        self.fields["location"].label = "Location"
        self.fields["sub_location"].label = "Sub-Location"
        self.fields["department"].label = "Department"

        self.fields["study_leader"].label = "Study Leader"
        self.fields["team_members"].label = "Study Team Members"

        self.fields["planned_start_date"].label = "Planned Start Date"
        self.fields["planned_end_date"].label = "Planned End Date"
        self.fields["actual_start_date"].label = "Actual Start Date"
        self.fields["actual_end_date"].label = "Actual End Date"

        self.fields["review_frequency"].label = "Review Frequency"
        self.fields["next_review_date"].label = "Next Review Date"

        # ----------------------------------------------------
        # REQUIRED FIELDS
        # ----------------------------------------------------

        required_fields = [
            "study_title",
            "study_type",
            "methodology",
            "process_type",
            "priority",
            "status",
            "plant",
            "study_leader",
        ]

        for field_name in required_fields:
            self.fields[field_name].required = True

        # ----------------------------------------------------
        # OPTIONAL FIELDS
        # ----------------------------------------------------

        optional_fields = [
            "zone",
            "location",
            "sub_location",
            "department",
            "team_members",
            "planned_start_date",
            "planned_end_date",
            "actual_start_date",
            "actual_end_date",
            "review_frequency",
            "next_review_date",
            "study_scope",
            "study_objective",
            "reference_documents",
            "remarks",
        ]

        for field_name in optional_fields:
            self.fields[field_name].required = False

    # ========================================================
    # FORM VALIDATION
    # ========================================================

    def clean(self):
        cleaned_data = super().clean()

        plant = cleaned_data.get("plant")
        zone = cleaned_data.get("zone")
        location = cleaned_data.get("location")
        sub_location = cleaned_data.get("sub_location")

        planned_start = cleaned_data.get("planned_start_date")
        planned_end = cleaned_data.get("planned_end_date")

        actual_start = cleaned_data.get("actual_start_date")
        actual_end = cleaned_data.get("actual_end_date")

        # ----------------------------------------------------
        # PLANT AND ZONE VALIDATION
        # ----------------------------------------------------

        if zone and not plant:
            self.add_error(
                "plant",
                "Please select a plant before selecting a zone.",
            )

        elif zone and plant and zone.plant_id != plant.id:
            self.add_error(
                "zone",
                "Selected zone does not belong to the selected plant.",
            )

        # ----------------------------------------------------
        # ZONE AND LOCATION VALIDATION
        # ----------------------------------------------------

        if location and not zone:
            self.add_error(
                "zone",
                "Please select a zone before selecting a location.",
            )

        elif location and zone and location.zone_id != zone.id:
            self.add_error(
                "location",
                "Selected location does not belong to the selected zone.",
            )

        # ----------------------------------------------------
        # LOCATION AND SUB-LOCATION VALIDATION
        # ----------------------------------------------------

        if sub_location and not location:
            self.add_error(
                "location",
                "Please select a location before selecting a sub-location.",
            )

        elif (
            sub_location
            and location
            and sub_location.location_id != location.id
        ):
            self.add_error(
                "sub_location",
                "Selected sub-location does not belong to the selected location.",
            )

        # ----------------------------------------------------
        # PLANNED DATE VALIDATION
        # ----------------------------------------------------

        if planned_start and planned_end:
            if planned_end < planned_start:
                self.add_error(
                    "planned_end_date",
                    "Planned end date cannot be earlier than planned start date.",
                )

        # ----------------------------------------------------
        # ACTUAL DATE VALIDATION
        # ----------------------------------------------------

        if actual_start and actual_end:
            if actual_end < actual_start:
                self.add_error(
                    "actual_end_date",
                    "Actual end date cannot be earlier than actual start date.",
                )

        return cleaned_data




# ============================================================
# HAZOP NODE REGISTER FORM
# ============================================================

class HAZOPNodeForm(forms.ModelForm):
    """
    Form for creating and updating HAZOP process nodes.
    The study is assigned from the Study Register view.
    """

    class Meta:
        model = HAZOPNode

        fields = [
            "node_name",
            "node_type",
            "equipment_type",
            "equipment_tag",
            "description",
            "design_intent",
            "operating_conditions",
            "drawing_reference",
            "boundary_description",
            "is_active",
        ]

        widgets = {
            "node_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter node name",
            }),

            "node_type": forms.Select(attrs={
                "class": "form-control",
            }),

            "equipment_type": forms.Select(attrs={
                "class": "form-control",
            }),

            "equipment_tag": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: P-101, V-201",
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Describe the process node",
            }),

            "design_intent": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Describe the intended function of this node",
            }),

            "operating_conditions": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter normal operating conditions",
            }),

            "drawing_reference": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: P&ID-101",
            }),

            "boundary_description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Define node boundaries, inlet and outlet",
            }),

            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["node_type"].queryset = (
            HAZOPNodeType.objects
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["equipment_type"].queryset = (
            HAZOPEquipmentType.objects
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["equipment_type"].required = False
        self.fields["equipment_tag"].required = False
        self.fields["description"].required = False
        self.fields["design_intent"].required = False
        self.fields["operating_conditions"].required = False
        self.fields["drawing_reference"].required = False
        self.fields["boundary_description"].required = False
        self.fields["is_active"].required = False

        self.fields["node_name"].label = "Node Name"
        self.fields["node_type"].label = "Node Type"
        self.fields["equipment_type"].label = "Equipment Type"
        self.fields["equipment_tag"].label = "Equipment Tag"
        self.fields["design_intent"].label = "Design Intent"
        self.fields["operating_conditions"].label = "Operating Conditions"
        self.fields["drawing_reference"].label = "Drawing / P&ID Reference"
        self.fields["boundary_description"].label = "Node Boundaries"





class HAZOPWorksheetEntryForm(forms.ModelForm):
    """
    Form for creating and updating a HAZOP worksheet entry.
    The parent Node and Entry Number are managed by the system.
    """

    class Meta:
        model = HAZOPWorksheetEntry

        fields = [
            "parameter",
            "guide_word",
            "deviation_template",
            "deviation_description",
            "possible_causes",
            "operating_condition",
            "initial_severity",
            "initial_likelihood",
            "residual_severity",
            "residual_likelihood",
            "remarks",
            "is_active",
        ]

        widgets = {
            "parameter": forms.Select(
                attrs={"class": "form-control"}
            ),
            "guide_word": forms.Select(
                attrs={"class": "form-control"}
            ),
            "deviation_template": forms.Select(
                attrs={"class": "form-control"}
            ),
            "deviation_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe the deviation",
                }
            ),
            "possible_causes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe possible causes of the deviation",
                }
            ),
            "operating_condition": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe the operating condition",
                }
            ),
            "initial_severity": forms.Select(
                attrs={"class": "form-control"}
            ),
            "initial_likelihood": forms.Select(
                attrs={"class": "form-control"}
            ),
            "residual_severity": forms.Select(
                attrs={"class": "form-control"}
            ),
            "residual_likelihood": forms.Select(
                attrs={"class": "form-control"}
            ),
            "remarks": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter additional remarks",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["parameter"].queryset = (
            HAZOPParameter.objects
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["guide_word"].queryset = (
            HAZOPGuideWord.objects
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["deviation_template"].queryset = (
            HAZOPDeviationTemplate.objects
            .filter(is_active=True)
            .select_related("parameter", "guide_word")
            .order_by("parameter__name", "guide_word__name")
        )

        self.fields["initial_severity"].queryset = (
            HAZOPSeverity.objects
            .filter(is_active=True)
            .order_by("severity_score")
        )

        self.fields["initial_likelihood"].queryset = (
            HAZOPLikelihood.objects
            .filter(is_active=True)
            .order_by("likelihood_score")
        )

        self.fields["residual_severity"].queryset = (
            HAZOPSeverity.objects
            .filter(is_active=True)
            .order_by("severity_score")
        )

        self.fields["residual_likelihood"].queryset = (
            HAZOPLikelihood.objects
            .filter(is_active=True)
            .order_by("likelihood_score")
        )

        self.fields["deviation_template"].required = False
        self.fields["residual_severity"].required = False
        self.fields["residual_likelihood"].required = False
        self.fields["remarks"].required = False

    def clean(self):
        cleaned_data = super().clean()

        parameter = cleaned_data.get("parameter")
        guide_word = cleaned_data.get("guide_word")
        deviation_template = cleaned_data.get("deviation_template")

        # Validate Parameter and Guide Word mapping
        if parameter and guide_word:
            mapping_exists = (
                HAZOPParameterGuideWordMapping.objects
                .filter(
                    parameter=parameter,
                    guide_word=guide_word,
                    is_active=True,
                )
                .exists()
            )

            if not mapping_exists:
                self.add_error(
                    "guide_word",
                    "This Guide Word is not mapped to the selected Parameter.",
                )

        # Ensure the selected deviation template matches
        # the selected Parameter and Guide Word.
        if deviation_template and parameter and guide_word:
            if (
                deviation_template.parameter_id != parameter.id
                or deviation_template.guide_word_id != guide_word.id
            ):
                self.add_error(
                    "deviation_template",
                    "The selected deviation template does not match "
                    "the selected Parameter and Guide Word.",
                )

        # Residual risk should have both ratings or neither.
        residual_severity = cleaned_data.get("residual_severity")
        residual_likelihood = cleaned_data.get("residual_likelihood")

        if bool(residual_severity) != bool(residual_likelihood):
            self.add_error(
                "residual_severity",
                "Select both Residual Severity and Residual Likelihood, "
                "or leave both blank.",
            )

        return cleaned_data




class HAZOPCauseForm(forms.ModelForm):
    class Meta:
        model = HAZOPCause
        fields = [
            "category",
            "cause_description",
            "is_active",
        ]

        widgets = {
            "category": forms.Select(
                attrs={"class": "form-control"}
            ),
            "cause_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the possible cause of this deviation...",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }


class HAZOPConsequenceForm(forms.ModelForm):
    class Meta:
        model = HAZOPConsequence
        fields = [
            "category",
            "consequence_description",
            "is_active",
        ]

        widgets = {
            "category": forms.Select(
                attrs={"class": "form-control"}
            ),
            "consequence_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the possible consequence...",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }


class HAZOPSafeguardForm(forms.ModelForm):
    class Meta:
        model = HAZOPSafeguard
        fields = [
            "category",
            "safeguard_description",
            "is_active",
        ]

        widgets = {
            "category": forms.Select(
                attrs={"class": "form-control"}
            ),
            "safeguard_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the existing safeguard or control...",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }




class HAZOPRiskMatrixForm(forms.ModelForm):

    class Meta:
        model = HAZOPRiskMatrix
        fields = [
            "name",
            "description",
            "likelihood_scale",
            "severity_scale",
            "is_default",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter Risk Matrix Name",
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter description",
            }),

            "likelihood_scale": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
            }),

            "severity_scale": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
            }),

            "is_default": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),

            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        likelihood = cleaned_data.get("likelihood_scale")
        severity = cleaned_data.get("severity_scale")

        if likelihood and likelihood < 1:
            self.add_error(
                "likelihood_scale",
                "Likelihood scale must be at least 1."
            )

        if severity and severity < 1:
            self.add_error(
                "severity_scale",
                "Severity scale must be at least 1."
            )

        return cleaned_data



class HAZOPRiskRatingForm(forms.ModelForm):

    class Meta:
        model = HAZOPRiskRating
        fields = [
            "rating_type",
            "score",
            "name",
            "description",
            "is_active",
        ]

        widgets = {
            "rating_type": forms.Select(attrs={
                "class": "form-select",
            }),

            "score": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
            }),

            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: Almost Certain",
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
            }),

            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }



class HAZOPRiskLevelForm(forms.ModelForm):

    class Meta:
        model = HAZOPRiskLevel
        fields = [
            "name",
            "minimum_score",
            "maximum_score",
            "color",
            "requires_action",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: High",
            }),

            "minimum_score": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
            }),

            "maximum_score": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
            }),

            "color": forms.TextInput(attrs={
                "class": "form-control",
                type: "color",
            }),

            "requires_action": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),

            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        minimum = cleaned_data.get("minimum_score")
        maximum = cleaned_data.get("maximum_score")

        if minimum is not None and maximum is not None:
            if minimum > maximum:
                self.add_error(
                    "maximum_score",
                    "Maximum score must be greater than or equal to minimum score."
                )

        return cleaned_data
    


class HAZOPRiskAssessmentForm(forms.ModelForm):

    initial_likelihood = forms.TypedChoiceField(
    coerce=int,
    choices=[],
    widget=forms.Select(attrs={"class": "form-select"}))

    initial_severity = forms.TypedChoiceField(
        coerce=int,
        choices=[],
        widget=forms.Select(attrs={"class": "form-select"})
    )

    residual_likelihood = forms.TypedChoiceField(
        coerce=int,
        choices=[],
        required=False,
        empty_value=None,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    residual_severity = forms.TypedChoiceField(
        coerce=int,
        choices=[],
        required=False,
        empty_value=None,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    class Meta:
        model = HAZOPRiskAssessment

        fields = [
            "matrix",
            "hazard_title",
            "hazard_description",
            "potential_consequence",
            "persons_exposed",
            "existing_controls",

            "initial_likelihood",
            "initial_severity",

            "additional_controls",
            "control_hierarchy",
            "action_required",
            "action_responsible",
            "action_due_date",

            "residual_likelihood",
            "residual_severity",

            # Review and approval assignment
            "reviewer",
            "approver",
        ]

        widgets = {
            "matrix": forms.Select(attrs={
                "class": "form-select",
            }),

            "hazard_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter hazard title",
            }),

            "hazard_description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Describe the hazard",
            }),

            "potential_consequence": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Describe potential consequences",
            }),

            "persons_exposed": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Employees, contractors, visitors, etc.",
            }),

            "existing_controls": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Describe existing control measures",
            }),

            "initial_likelihood": forms.Select(attrs={
                "class": "form-select",
            }),

            "initial_severity": forms.Select(attrs={
                "class": "form-select",
            }),

            "additional_controls": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter additional control measures",
            }),

            "control_hierarchy": forms.Select(attrs={
                "class": "form-select",
            }),

            "action_required": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),

            "action_responsible": forms.Select(attrs={
                "class": "form-select",
            }),

            "action_due_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),

            "residual_likelihood": forms.Select(attrs={
                "class": "form-select",
            }),

            "residual_severity": forms.Select(attrs={
                "class": "form-select",
            }),
            "reviewer": forms.Select(attrs={
                "class": "form-select",
            }),

            "approver": forms.Select(attrs={
                "class": "form-select",
            }),
        }

    def __init__(self, *args, **kwargs):
        matrix = kwargs.pop("matrix", None)

        super().__init__(*args, **kwargs)

        if not matrix and self.instance.pk:
            matrix = self.instance.matrix

        if matrix:
            self.fields["matrix"].initial = matrix.pk
            self.fields["matrix"].disabled = True

            likelihood_ratings = matrix.ratings.filter(
                rating_type="LIKELIHOOD",
                is_active=True
            ).order_by("score")

            severity_ratings = matrix.ratings.filter(
                rating_type="SEVERITY",
                is_active=True
            ).order_by("score")

            likelihood_choices = [
                ("", "Select Likelihood")
            ] + [
                (rating.score, f"{rating.score} - {rating.name}")
                for rating in likelihood_ratings
            ]

            severity_choices = [
                ("", "Select Severity")
            ] + [
                (rating.score, f"{rating.score} - {rating.name}")
                for rating in severity_ratings
            ]

            self.fields["initial_likelihood"].choices = (
                likelihood_choices
            )

            self.fields["residual_likelihood"].choices = (
                likelihood_choices
            )

            self.fields["initial_severity"].choices = (
                severity_choices
            )

            self.fields["residual_severity"].choices = (
                severity_choices
            )

            # ----------------------------------------------------
            # REVIEWER AND APPROVER
            # ----------------------------------------------------

            self.fields["reviewer"].queryset = (
                User.objects
                .filter(is_active=True)
                .order_by("username")
            )

            self.fields["approver"].queryset = (
                User.objects
                .filter(is_active=True)
                .order_by("username")
            )

            self.fields["reviewer"].required = False
            self.fields["approver"].required = False

            self.fields["reviewer"].label = "Assigned Reviewer"
            self.fields["approver"].label = "Assigned Approver"




class HAZOPActionForm(forms.ModelForm):

    class Meta:
        model = HAZOPAction

        fields = [
            "recommendation",
            "action_description",
            "department",
            "assigned_to",
            "priority",
            "due_date",
        ]

        widgets = {
            "recommendation": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "action_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the corrective or preventive action",
                }
            ),

            "department": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "assigned_to": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "priority": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "due_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["assigned_to"].queryset = (
            User.objects
            .filter(is_active=True)
            .order_by("username")
        )

        self.fields["department"].queryset = (
            Department.objects
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["recommendation"].queryset = (
            HAZOPRecommendation.objects
            .filter(is_active=True)
            .select_related("worksheet_entry")
            .order_by("-created_at")
        )

        self.fields["recommendation"].empty_label = (
            "Select a HAZOP recommendation"
        )

        self.fields["recommendation"].label_from_instance = (
            lambda obj: f"REC-{obj.pk} | {obj.recommendation_description[:100]}"
        )