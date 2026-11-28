import os
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction
from django.http import HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from django.core.paginator import Paginator
from django.db.models import (
    Count,
    OuterRef,
    Subquery,
    IntegerField,
    Value,
)
from django.db.models.functions import Coalesce
from apps.organizations.models import (
    Zone,
    Location,
    SubLocation,
)
from .models import (
    HAZOPStudy,
    HAZOPNode,
    HAZOPWorksheetEntry,
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
    HAZOPCause,
    HAZOPConsequence,
    HAZOPSafeguard,
    HAZOPRiskMatrix,
    HAZOPRiskRating,
    HAZOPRiskLevel,
    HAZOPRiskAssessment,
    HAZOPRiskAssessmentReviewHistory,
    HAZOPAction,
    HAZOPActionHistory,
)

from .forms import (
    HAZOPStudyForm,
    HAZOPNodeForm,
    HAZOPWorksheetEntryForm,
    HAZOPStudyTypeForm,
    HAZOPStudyStatusForm,
    HAZOPParameterForm,
    HAZOPGuideWordForm,
    HAZOPDeviationTemplateForm,
    HAZOPStudyMethodologyForm,
    HAZOPStudyPriorityForm,
    HAZOPProcessTypeForm,
    HAZOPNodeTypeForm,
    HAZOPEquipmentTypeForm,
    HAZOPCauseCategoryForm,
    HAZOPConsequenceCategoryForm,
    HAZOPSafeguardCategoryForm,
    HAZOPRecommendationCategoryForm,
    HAZOPSeverityForm,
    HAZOPLikelihoodForm,
    HAZOPReviewFrequencyForm,
    HAZOPParameterGuideWordMappingForm,
    HAZOPCauseForm,
    HAZOPConsequenceForm,
    HAZOPSafeguardForm,
    HAZOPRiskMatrixForm,
    HAZOPRiskRatingForm,
    HAZOPRiskLevelForm,
    HAZOPRiskAssessmentForm,
    HAZOPActionForm
)


# ============================================================
# DASHBOARD
# ============================================================

class HazopDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "hazop/dashboard.html"


class HAZOPConfigurationDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "hazop/configuration/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["study_type_count"] = HAZOPStudyType.objects.count()
        context["study_status_count"] = HAZOPStudyStatus.objects.count()
        context["parameter_count"] = HAZOPParameter.objects.count()
        context["guide_word_count"] = HAZOPGuideWord.objects.count()
        context["deviation_template_count"] = (
            HAZOPDeviationTemplate.objects.count()
        )

        return context


# ============================================================
# COMMON CONFIGURATION LIST VIEW
# ============================================================

class HAZOPConfigListView(LoginRequiredMixin, ListView):
    template_name = "hazop/configuration/list.html"
    context_object_name = "config_records"

    page_title = ""
    create_url_name = ""
    edit_url_name = ""
    toggle_url_name = ""
    config_dashboard_url = "hazop:configuration"
    ordering = ("code",)

    def get_queryset(self):
        return self.model.objects.all().order_by(*self.ordering)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = self.page_title
        context["create_url_name"] = self.create_url_name
        context["edit_url_name"] = self.edit_url_name
        context["toggle_url_name"] = self.toggle_url_name
        context["config_dashboard_url"] = self.config_dashboard_url

        return context


# ============================================================
# COMMON CREATE VIEW
# ============================================================

class HAZOPConfigCreateView(LoginRequiredMixin, CreateView):
    template_name = "hazop/configuration/form.html"

    page_title = ""
    list_url_name = ""

    def form_valid(self, form):
        if hasattr(form.instance, "created_by_id"):
            form.instance.created_by = self.request.user

        response = super().form_valid(form)

        messages.success(
            self.request,
            f"{self.page_title} created successfully.",
        )

        return response

    def get_success_url(self):
        return reverse(self.list_url_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = f"Create {self.page_title}"
        context["list_url_name"] = self.list_url_name

        return context


# ============================================================
# COMMON UPDATE VIEW
# ============================================================

class HAZOPConfigUpdateView(LoginRequiredMixin, UpdateView):
    template_name = "hazop/configuration/form.html"

    page_title = ""
    list_url_name = ""

    def get_success_url(self):
        return reverse(self.list_url_name)

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            f"{self.page_title} updated successfully.",
        )

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = f"Edit {self.page_title}"
        context["list_url_name"] = self.list_url_name

        return context


# ============================================================
# COMMON ACTIVATE / DEACTIVATE VIEW
# ============================================================

class HAZOPConfigToggleActiveView(LoginRequiredMixin, View):
    model = None
    list_url_name = ""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        obj = get_object_or_404(
            self.model,
            pk=kwargs["pk"],
        )

        obj.is_active = not obj.is_active
        obj.save(update_fields=["is_active", "updated_at"])

        status = "activated" if obj.is_active else "deactivated"

        messages.success(
            request,
            f"{obj} has been {status}.",
        )

        return redirect(self.list_url_name)


# ============================================================
# STUDY TYPE
# ============================================================

class HAZOPStudyTypeListView(HAZOPConfigListView):
    model = HAZOPStudyType
    page_title = "Study Types"
    create_url_name = "hazop:study_type_create"
    edit_url_name = "hazop:study_type_edit"
    toggle_url_name = "hazop:study_type_toggle"


class HAZOPStudyTypeCreateView(HAZOPConfigCreateView):
    model = HAZOPStudyType
    form_class = HAZOPStudyTypeForm
    page_title = "Study Type"
    list_url_name = "hazop:study_type_list"


class HAZOPStudyTypeUpdateView(HAZOPConfigUpdateView):
    model = HAZOPStudyType
    form_class = HAZOPStudyTypeForm
    page_title = "Study Type"
    list_url_name = "hazop:study_type_list"


class HAZOPStudyTypeToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPStudyType
    list_url_name = "hazop:study_type_list"


# ============================================================
# STUDY STATUS
# ============================================================

class HAZOPStudyStatusListView(HAZOPConfigListView):
    model = HAZOPStudyStatus
    page_title = "Study Statuses"
    create_url_name = "hazop:study_status_create"
    edit_url_name = "hazop:study_status_edit"
    toggle_url_name = "hazop:study_status_toggle"
    ordering = ("sequence", "name")


class HAZOPStudyStatusCreateView(HAZOPConfigCreateView):
    model = HAZOPStudyStatus
    form_class = HAZOPStudyStatusForm
    page_title = "Study Status"
    list_url_name = "hazop:study_status_list"


class HAZOPStudyStatusUpdateView(HAZOPConfigUpdateView):
    model = HAZOPStudyStatus
    form_class = HAZOPStudyStatusForm
    page_title = "Study Status"
    list_url_name = "hazop:study_status_list"


class HAZOPStudyStatusToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPStudyStatus
    list_url_name = "hazop:study_status_list"


# ============================================================
# PARAMETER
# ============================================================

class HAZOPParameterListView(HAZOPConfigListView):
    model = HAZOPParameter
    page_title = "Parameters"
    create_url_name = "hazop:parameter_create"
    edit_url_name = "hazop:parameter_edit"
    toggle_url_name = "hazop:parameter_toggle"


class HAZOPParameterCreateView(HAZOPConfigCreateView):
    model = HAZOPParameter
    form_class = HAZOPParameterForm
    page_title = "Parameter"
    list_url_name = "hazop:parameter_list"


class HAZOPParameterUpdateView(HAZOPConfigUpdateView):
    model = HAZOPParameter
    form_class = HAZOPParameterForm
    page_title = "Parameter"
    list_url_name = "hazop:parameter_list"


class HAZOPParameterToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPParameter
    list_url_name = "hazop:parameter_list"


# ============================================================
# GUIDE WORD
# ============================================================

class HAZOPGuideWordListView(HAZOPConfigListView):
    model = HAZOPGuideWord
    page_title = "Guide Words"
    create_url_name = "hazop:guide_word_create"
    edit_url_name = "hazop:guide_word_edit"
    toggle_url_name = "hazop:guide_word_toggle"


class HAZOPGuideWordCreateView(HAZOPConfigCreateView):
    model = HAZOPGuideWord
    form_class = HAZOPGuideWordForm
    page_title = "Guide Word"
    list_url_name = "hazop:guide_word_list"


class HAZOPGuideWordUpdateView(HAZOPConfigUpdateView):
    model = HAZOPGuideWord
    form_class = HAZOPGuideWordForm
    page_title = "Guide Word"
    list_url_name = "hazop:guide_word_list"


class HAZOPGuideWordToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPGuideWord
    list_url_name = "hazop:guide_word_list"


# ============================================================
# DEVIATION TEMPLATE
# ============================================================

class HAZOPDeviationTemplateListView(HAZOPConfigListView):
    model = HAZOPDeviationTemplate
    page_title = "Deviation Templates"
    create_url_name = "hazop:deviation_template_create"
    edit_url_name = "hazop:deviation_template_edit"
    toggle_url_name = "hazop:deviation_template_toggle"
    ordering = ("parameter__name", "guide_word__name")


class HAZOPDeviationTemplateCreateView(HAZOPConfigCreateView):
    model = HAZOPDeviationTemplate
    form_class = HAZOPDeviationTemplateForm
    page_title = "Deviation Template"
    list_url_name = "hazop:deviation_template_list"


class HAZOPDeviationTemplateUpdateView(HAZOPConfigUpdateView):
    model = HAZOPDeviationTemplate
    form_class = HAZOPDeviationTemplateForm
    page_title = "Deviation Template"
    list_url_name = "hazop:deviation_template_list"


class HAZOPDeviationTemplateToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPDeviationTemplate
    list_url_name = "hazop:deviation_template_list"


# ============================================================
# STUDY METHODOLOGY
# ============================================================

class StudyMethodologyListView(HAZOPConfigListView):
    model = HAZOPStudyMethodology
    page_title = "Study Methodologies"
    create_url_name = "hazop:study_methodology_create"
    edit_url_name = "hazop:study_methodology_edit"
    toggle_url_name = "hazop:study_methodology_toggle"


class StudyMethodologyCreateView(HAZOPConfigCreateView):
    model = HAZOPStudyMethodology
    form_class = HAZOPStudyMethodologyForm
    page_title = "Study Methodology"
    list_url_name = "hazop:study_methodology_list"


class StudyMethodologyUpdateView(HAZOPConfigUpdateView):
    model = HAZOPStudyMethodology
    form_class = HAZOPStudyMethodologyForm
    page_title = "Study Methodology"
    list_url_name = "hazop:study_methodology_list"


class StudyMethodologyToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPStudyMethodology
    list_url_name = "hazop:study_methodology_list"


# ============================================================
# STUDY PRIORITY
# ============================================================

class StudyPriorityListView(HAZOPConfigListView):
    model = HAZOPStudyPriority
    page_title = "Study Priorities"
    create_url_name = "hazop:study_priority_create"
    edit_url_name = "hazop:study_priority_edit"
    toggle_url_name = "hazop:study_priority_toggle"
    ordering = ("priority_order", "name")


class StudyPriorityCreateView(HAZOPConfigCreateView):
    model = HAZOPStudyPriority
    form_class = HAZOPStudyPriorityForm
    page_title = "Study Priority"
    list_url_name = "hazop:study_priority_list"


class StudyPriorityUpdateView(HAZOPConfigUpdateView):
    model = HAZOPStudyPriority
    form_class = HAZOPStudyPriorityForm
    page_title = "Study Priority"
    list_url_name = "hazop:study_priority_list"


class StudyPriorityToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPStudyPriority
    list_url_name = "hazop:study_priority_list"


# ============================================================
# PROCESS TYPE
# ============================================================

class ProcessTypeListView(HAZOPConfigListView):
    model = HAZOPProcessType
    page_title = "Process Types"
    create_url_name = "hazop:process_type_create"
    edit_url_name = "hazop:process_type_edit"
    toggle_url_name = "hazop:process_type_toggle"


class ProcessTypeCreateView(HAZOPConfigCreateView):
    model = HAZOPProcessType
    form_class = HAZOPProcessTypeForm
    page_title = "Process Type"
    list_url_name = "hazop:process_type_list"


class ProcessTypeUpdateView(HAZOPConfigUpdateView):
    model = HAZOPProcessType
    form_class = HAZOPProcessTypeForm
    page_title = "Process Type"
    list_url_name = "hazop:process_type_list"


class ProcessTypeToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPProcessType
    list_url_name = "hazop:process_type_list"


# ============================================================
# NODE TYPE
# ============================================================

class NodeTypeListView(HAZOPConfigListView):
    model = HAZOPNodeType
    page_title = "Node Types"
    create_url_name = "hazop:node_type_create"
    edit_url_name = "hazop:node_type_edit"
    toggle_url_name = "hazop:node_type_toggle"


class NodeTypeCreateView(HAZOPConfigCreateView):
    model = HAZOPNodeType
    form_class = HAZOPNodeTypeForm
    page_title = "Node Type"
    list_url_name = "hazop:node_type_list"


class NodeTypeUpdateView(HAZOPConfigUpdateView):
    model = HAZOPNodeType
    form_class = HAZOPNodeTypeForm
    page_title = "Node Type"
    list_url_name = "hazop:node_type_list"


class NodeTypeToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPNodeType
    list_url_name = "hazop:node_type_list"


# ============================================================
# EQUIPMENT TYPE
# ============================================================

class EquipmentTypeListView(HAZOPConfigListView):
    model = HAZOPEquipmentType
    page_title = "Equipment Types"
    create_url_name = "hazop:equipment_type_create"
    edit_url_name = "hazop:equipment_type_edit"
    toggle_url_name = "hazop:equipment_type_toggle"


class EquipmentTypeCreateView(HAZOPConfigCreateView):
    model = HAZOPEquipmentType
    form_class = HAZOPEquipmentTypeForm
    page_title = "Equipment Type"
    list_url_name = "hazop:equipment_type_list"


class EquipmentTypeUpdateView(HAZOPConfigUpdateView):
    model = HAZOPEquipmentType
    form_class = HAZOPEquipmentTypeForm
    page_title = "Equipment Type"
    list_url_name = "hazop:equipment_type_list"


class EquipmentTypeToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPEquipmentType
    list_url_name = "hazop:equipment_type_list"


# ============================================================
# CAUSE CATEGORY
# ============================================================

class CauseCategoryListView(HAZOPConfigListView):
    model = HAZOPCauseCategory
    page_title = "Cause Categories"
    create_url_name = "hazop:cause_category_create"
    edit_url_name = "hazop:cause_category_edit"
    toggle_url_name = "hazop:cause_category_toggle"


class CauseCategoryCreateView(HAZOPConfigCreateView):
    model = HAZOPCauseCategory
    form_class = HAZOPCauseCategoryForm
    page_title = "Cause Category"
    list_url_name = "hazop:cause_category_list"


class CauseCategoryUpdateView(HAZOPConfigUpdateView):
    model = HAZOPCauseCategory
    form_class = HAZOPCauseCategoryForm
    page_title = "Cause Category"
    list_url_name = "hazop:cause_category_list"


class CauseCategoryToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPCauseCategory
    list_url_name = "hazop:cause_category_list"


# ============================================================
# CONSEQUENCE CATEGORY
# ============================================================

class ConsequenceCategoryListView(HAZOPConfigListView):
    model = HAZOPConsequenceCategory
    page_title = "Consequence Categories"
    create_url_name = "hazop:consequence_category_create"
    edit_url_name = "hazop:consequence_category_edit"
    toggle_url_name = "hazop:consequence_category_toggle"


class ConsequenceCategoryCreateView(HAZOPConfigCreateView):
    model = HAZOPConsequenceCategory
    form_class = HAZOPConsequenceCategoryForm
    page_title = "Consequence Category"
    list_url_name = "hazop:consequence_category_list"


class ConsequenceCategoryUpdateView(HAZOPConfigUpdateView):
    model = HAZOPConsequenceCategory
    form_class = HAZOPConsequenceCategoryForm
    page_title = "Consequence Category"
    list_url_name = "hazop:consequence_category_list"


class ConsequenceCategoryToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPConsequenceCategory
    list_url_name = "hazop:consequence_category_list"


# ============================================================
# SAFEGUARD CATEGORY
# ============================================================

class SafeguardCategoryListView(HAZOPConfigListView):
    model = HAZOPSafeguardCategory
    page_title = "Safeguard Categories"
    create_url_name = "hazop:safeguard_category_create"
    edit_url_name = "hazop:safeguard_category_edit"
    toggle_url_name = "hazop:safeguard_category_toggle"


class SafeguardCategoryCreateView(HAZOPConfigCreateView):
    model = HAZOPSafeguardCategory
    form_class = HAZOPSafeguardCategoryForm
    page_title = "Safeguard Category"
    list_url_name = "hazop:safeguard_category_list"


class SafeguardCategoryUpdateView(HAZOPConfigUpdateView):
    model = HAZOPSafeguardCategory
    form_class = HAZOPSafeguardCategoryForm
    page_title = "Safeguard Category"
    list_url_name = "hazop:safeguard_category_list"


class SafeguardCategoryToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPSafeguardCategory
    list_url_name = "hazop:safeguard_category_list"


# ============================================================
# RECOMMENDATION CATEGORY
# ============================================================

class RecommendationCategoryListView(HAZOPConfigListView):
    model = HAZOPRecommendationCategory
    page_title = "Recommendation Categories"
    create_url_name = "hazop:recommendation_category_create"
    edit_url_name = "hazop:recommendation_category_edit"
    toggle_url_name = "hazop:recommendation_category_toggle"


class RecommendationCategoryCreateView(HAZOPConfigCreateView):
    model = HAZOPRecommendationCategory
    form_class = HAZOPRecommendationCategoryForm
    page_title = "Recommendation Category"
    list_url_name = "hazop:recommendation_category_list"


class RecommendationCategoryUpdateView(HAZOPConfigUpdateView):
    model = HAZOPRecommendationCategory
    form_class = HAZOPRecommendationCategoryForm
    page_title = "Recommendation Category"
    list_url_name = "hazop:recommendation_category_list"


class RecommendationCategoryToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPRecommendationCategory
    list_url_name = "hazop:recommendation_category_list"


# ============================================================
# SEVERITY
# ============================================================

class SeverityListView(HAZOPConfigListView):
    model = HAZOPSeverity
    page_title = "Severity Levels"
    create_url_name = "hazop:severity_create"
    edit_url_name = "hazop:severity_edit"
    toggle_url_name = "hazop:severity_toggle"
    ordering = ("severity_score",)


class SeverityCreateView(HAZOPConfigCreateView):
    model = HAZOPSeverity
    form_class = HAZOPSeverityForm
    page_title = "Severity"
    list_url_name = "hazop:severity_list"


class SeverityUpdateView(HAZOPConfigUpdateView):
    model = HAZOPSeverity
    form_class = HAZOPSeverityForm
    page_title = "Severity"
    list_url_name = "hazop:severity_list"


class SeverityToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPSeverity
    list_url_name = "hazop:severity_list"


# ============================================================
# LIKELIHOOD
# ============================================================

class LikelihoodListView(HAZOPConfigListView):
    model = HAZOPLikelihood
    page_title = "Likelihood Levels"
    create_url_name = "hazop:likelihood_create"
    edit_url_name = "hazop:likelihood_edit"
    toggle_url_name = "hazop:likelihood_toggle"
    ordering = ("likelihood_score",)


class LikelihoodCreateView(HAZOPConfigCreateView):
    model = HAZOPLikelihood
    form_class = HAZOPLikelihoodForm
    page_title = "Likelihood"
    list_url_name = "hazop:likelihood_list"


class LikelihoodUpdateView(HAZOPConfigUpdateView):
    model = HAZOPLikelihood
    form_class = HAZOPLikelihoodForm
    page_title = "Likelihood"
    list_url_name = "hazop:likelihood_list"


class LikelihoodToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPLikelihood
    list_url_name = "hazop:likelihood_list"


# ============================================================
# REVIEW FREQUENCY
# ============================================================

class ReviewFrequencyListView(HAZOPConfigListView):
    model = HAZOPReviewFrequency
    page_title = "Review Frequencies"
    create_url_name = "hazop:review_frequency_create"
    edit_url_name = "hazop:review_frequency_edit"
    toggle_url_name = "hazop:review_frequency_toggle"
    ordering = ("interval_days",)


class ReviewFrequencyCreateView(HAZOPConfigCreateView):
    model = HAZOPReviewFrequency
    form_class = HAZOPReviewFrequencyForm
    page_title = "Review Frequency"
    list_url_name = "hazop:review_frequency_list"


class ReviewFrequencyUpdateView(HAZOPConfigUpdateView):
    model = HAZOPReviewFrequency
    form_class = HAZOPReviewFrequencyForm
    page_title = "Review Frequency"
    list_url_name = "hazop:review_frequency_list"


class ReviewFrequencyToggleView(HAZOPConfigToggleActiveView):
    model = HAZOPReviewFrequency
    list_url_name = "hazop:review_frequency_list"


# ============================================================
# PARAMETER-GUIDEWORD MAPPING
# ============================================================

class ParameterGuideWordMappingListView(LoginRequiredMixin, ListView):
    model = HAZOPParameterGuideWordMapping
    template_name = "hazop/configuration/mapping_list.html"
    context_object_name = "config_records"

    def get_queryset(self):
        return (
            self.model.objects
            .select_related("parameter", "guide_word")
            .order_by("parameter__name", "guide_word__name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Parameter-Guideword Mapping"
        context["create_url_name"] = (
            "hazop:parameter_guideword_mapping_create"
        )
        context["edit_url_name"] = (
            "hazop:parameter_guideword_mapping_edit"
        )
        context["toggle_url_name"] = (
            "hazop:parameter_guideword_mapping_toggle"
        )
        context["config_dashboard_url"] = "hazop:configuration"

        return context


class ParameterGuideWordMappingCreateView(
    HAZOPConfigCreateView
):
    model = HAZOPParameterGuideWordMapping
    form_class = HAZOPParameterGuideWordMappingForm
    page_title = "Parameter-Guideword Mapping"
    list_url_name = "hazop:parameter_guideword_mapping_list"


class ParameterGuideWordMappingUpdateView(
    HAZOPConfigUpdateView
):
    model = HAZOPParameterGuideWordMapping
    form_class = HAZOPParameterGuideWordMappingForm
    page_title = "Parameter-Guideword Mapping"
    list_url_name = "hazop:parameter_guideword_mapping_list"


class ParameterGuideWordMappingToggleView(
    HAZOPConfigToggleActiveView
):
    model = HAZOPParameterGuideWordMapping
    list_url_name = "hazop:parameter_guideword_mapping_list"



# ============================================================
# HAZOP ORGANIZATION AJAX DROPDOWNS
# ============================================================
@login_required
@require_GET
def zones_by_plant(request):
    """
    Return active zones belonging to the selected plant.
    """

    plant_id = request.GET.get("plant_id")

    zones = Zone.objects.none()

    if plant_id and plant_id.isdigit():
        zones = Zone.objects.filter(
            plant_id=plant_id,
            is_active=True,
        ).order_by("name")

    data = [
        {
            "id": zone.id,
            "name": zone.name,
        }
        for zone in zones
    ]

    return JsonResponse(data, safe=False)

@login_required
@require_GET
def locations_by_zone(request):
    """
    Return active locations belonging to the selected zone.
    """

    zone_id = request.GET.get("zone_id")

    locations = Location.objects.none()

    if zone_id and zone_id.isdigit():
        locations = Location.objects.filter(
            zone_id=zone_id,
            is_active=True,
        ).order_by("name")

    data = [
        {
            "id": location.id,
            "name": location.name,
        }
        for location in locations
    ]

    return JsonResponse(data, safe=False)

@login_required
@require_GET
def sub_locations_by_location(request):
    """
    Return active sub-locations belonging to the selected location.
    """

    location_id = request.GET.get("location_id")

    sub_locations = SubLocation.objects.none()

    if location_id and location_id.isdigit():
        sub_locations = SubLocation.objects.filter(
            location_id=location_id,
            is_active=True,
        ).order_by("name")

    data = [
        {
            "id": sub_location.id,
            "name": sub_location.name,
        }
        for sub_location in sub_locations
    ]

    return JsonResponse(data, safe=False)



# ============================================================
# HAZOP STUDY REGISTER
# ============================================================

class HAZOPStudyListView(LoginRequiredMixin, ListView):
    model = HAZOPStudy
    template_name = "hazop/study_list.html"
    context_object_name = "studies"
    ordering = ("-created_at",)

    def get_queryset(self):
        return (
            HAZOPStudy.objects.filter(
                is_active=True,
            ).select_related(
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
            )
            .order_by(*self.ordering)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "HAZOP Study Register"
        context["create_url_name"] = "hazop:study_create"
        context["edit_url_name"] = "hazop:study_edit"

        return context


class HAZOPStudyCreateView(LoginRequiredMixin, CreateView):
    model = HAZOPStudy
    form_class = HAZOPStudyForm
    template_name = "hazop/study_form.html"

    def form_valid(self, form):
        if hasattr(form.instance, "created_by_id"):
            form.instance.created_by = self.request.user

        if hasattr(form.instance, "updated_by_id"):
            form.instance.updated_by = self.request.user

        response = super().form_valid(form)

        messages.success(
            self.request,
            "HAZOP Study created successfully.",
        )

        return response

    def get_success_url(self):
        return reverse("hazop:study_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Create HAZOP Study"
        context["list_url_name"] = "hazop:study_list"

        return context


class HAZOPStudyUpdateView(LoginRequiredMixin, UpdateView):
    model = HAZOPStudy
    form_class = HAZOPStudyForm
    template_name = "hazop/study_form.html"

    def form_valid(self, form):
        if hasattr(form.instance, "updated_by_id"):
            form.instance.updated_by = self.request.user

        response = super().form_valid(form)

        messages.success(
            self.request,
            "HAZOP Study updated successfully.",
        )

        return response

    def get_success_url(self):
        return reverse("hazop:study_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Edit HAZOP Study"
        context["list_url_name"] = "hazop:study_list"

        return context




# ============================================================
# HAZOP NODE REGISTER
# ============================================================

class HAZOPNodeListView(LoginRequiredMixin, ListView):
    model = HAZOPNode
    template_name = "hazop/nodes/node_list.html"
    context_object_name = "nodes"

    def dispatch(self, request, *args, **kwargs):
        self.study = get_object_or_404(
            HAZOPStudy,
            pk=kwargs["study_pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            HAZOPNode.objects
            .filter(study=self.study, is_active=True)
            .select_related("node_type", "equipment_type")
            .order_by("created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["study"] = self.study
        context["total_nodes"] = self.get_queryset().count()
        return context


class HAZOPNodeCreateView(LoginRequiredMixin, CreateView):
    model = HAZOPNode
    form_class = HAZOPNodeForm
    template_name = "hazop/nodes/node_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.study = get_object_or_404(
            HAZOPStudy,
            pk=kwargs["study_pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.study = self.study
        form.instance.created_by = self.request.user

        response = super().form_valid(form)

        messages.success(
            self.request,
            "HAZOP Node created successfully.",
        )

        return response

    def get_success_url(self):
        return reverse(
            "hazop:node_list",
            kwargs={"study_pk": self.study.pk},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["study"] = self.study
        context["page_title"] = "Create HAZOP Node"
        return context


class HAZOPNodeUpdateView(LoginRequiredMixin, UpdateView):
    model = HAZOPNode
    form_class = HAZOPNodeForm
    template_name = "hazop/nodes/node_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.study = get_object_or_404(
            HAZOPStudy,
            pk=kwargs["study_pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Prevent editing a node that belongs to another study.
        return HAZOPNode.objects.filter(study=self.study)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user

        response = super().form_valid(form)

        messages.success(
            self.request,
            "HAZOP Node updated successfully.",
        )

        return response

    def get_success_url(self):
        return reverse(
            "hazop:node_list",
            kwargs={"study_pk": self.study.pk},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["study"] = self.study
        context["page_title"] = "Edit HAZOP Node"
        return context





# ==========================================================
# HAZOP WORKSHEET ENTRY REGISTER
# ==========================================================

class HAZOPWorksheetEntryListView(LoginRequiredMixin, ListView):
    model = HAZOPWorksheetEntry
    template_name = "hazop/worksheet/worksheet_list.html"
    context_object_name = "worksheet_entries"

    def dispatch(self, request, *args, **kwargs):
        self.node = get_object_or_404(
            HAZOPNode,
            pk=self.kwargs["node_pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        cause_count_query = (
            HAZOPCause.objects
            .filter(
                worksheet_entry_id=OuterRef("pk"),
                is_active=True,
            )
            .values("worksheet_entry_id")
            .annotate(total=Count("pk"))
            .values("total")
        )

        consequence_count_query = (
            HAZOPConsequence.objects
            .filter(
                worksheet_entry_id=OuterRef("pk"),
                is_active=True,
            )
            .values("worksheet_entry_id")
            .annotate(total=Count("pk"))
            .values("total")
        )

        safeguard_count_query = (
            HAZOPSafeguard.objects
            .filter(
                worksheet_entry_id=OuterRef("pk"),
                is_active=True,
            )
            .values("worksheet_entry_id")
            .annotate(total=Count("pk"))
            .values("total")
        )

        return (
            HAZOPWorksheetEntry.objects
            .filter(node=self.node)
            .select_related(
                "parameter",
                "guide_word",
                "initial_severity",
                "initial_likelihood",
                "residual_severity",
                "residual_likelihood",
            )
            .annotate(
                cause_count=Coalesce(
                    Subquery(
                        cause_count_query,
                        output_field=IntegerField(),
                    ),
                    Value(0),
                ),
                consequence_count=Coalesce(
                    Subquery(
                        consequence_count_query,
                        output_field=IntegerField(),
                    ),
                    Value(0),
                ),
                safeguard_count=Coalesce(
                    Subquery(
                        safeguard_count_query,
                        output_field=IntegerField(),
                    ),
                    Value(0),
                ),
            )
            .order_by("entry_number")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["node"] = self.node
        context["study"] = self.node.study

        worksheet_entries = context["worksheet_entries"]

        for entry in worksheet_entries:
            entry.is_locked = is_worksheet_entry_locked(entry)

        context["is_locked"] = all(
            entry.is_locked for entry in worksheet_entries
        ) if worksheet_entries else False

        return context


# ==========================================================
# CREATE HAZOP WORKSHEET ENTRY
# ==========================================================

class HAZOPWorksheetEntryCreateView(
    LoginRequiredMixin,
    CreateView,
):
    model = HAZOPWorksheetEntry
    form_class = HAZOPWorksheetEntryForm
    template_name = "hazop/worksheet/worksheet_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.node = get_object_or_404(
            HAZOPNode,
            pk=self.kwargs["node_pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.node = self.node

        if hasattr(form.instance, "created_by_id"):
            form.instance.created_by = self.request.user

        response = super().form_valid(form)

        messages.success(
            self.request,
            "Worksheet entry created successfully.",
        )

        return response

    def get_success_url(self):
        return reverse(
            "hazop:worksheet_list",
            kwargs={"node_pk": self.node.pk},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["node"] = self.node
        context["study"] = self.node.study
        context["page_title"] = "Create Worksheet Entry"
        return context


# ==========================================================
# UPDATE HAZOP WORKSHEET ENTRY
# ==========================================================

class HAZOPWorksheetEntryUpdateView(
    LoginRequiredMixin,
    UpdateView,
):
    model = HAZOPWorksheetEntry
    form_class = HAZOPWorksheetEntryForm
    template_name = "hazop/worksheet/worksheet_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.node = get_object_or_404(
            HAZOPNode,
            pk=self.kwargs["node_pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Only entries belonging to this Node can be edited.
        return HAZOPWorksheetEntry.objects.filter(
            node=self.node,
        )

    def get_object(self, queryset=None):
        entry = super().get_object(queryset)

        if is_worksheet_entry_locked(entry):
            raise PermissionDenied(
                "This worksheet has been submitted and is locked for editing."
            )

        return entry


    def form_valid(self, form):
        if is_worksheet_entry_locked(form.instance):
            raise PermissionDenied(
                "This worksheet has been submitted and is locked for editing."
            )

        if hasattr(form.instance, "updated_by_id"):
            form.instance.updated_by = self.request.user

        response = super().form_valid(form)

        messages.success(
            self.request,
            "Worksheet entry updated successfully.",
        )

        return response

    def get_success_url(self):
        return reverse(
            "hazop:worksheet_list",
            kwargs={"node_pk": self.node.pk},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["node"] = self.node
        context["study"] = self.node.study
        context["page_title"] = "Edit Worksheet Entry"
        return context



# ============================================================
# WORKSHEET CAUSES / CONSEQUENCES / SAFEGUARDS
# ============================================================

class WorksheetDetailListView(LoginRequiredMixin, ListView):
    template_name = "hazop/worksheet/details_list.html"
    context_object_name = "details"

    model = None
    detail_type = ""
    description_field = ""

    create_url_name = ""
    edit_url_name = ""
    deactivate_url_name = ""

    def dispatch(self, request, *args, **kwargs):
        self.entry = get_object_or_404(
            HAZOPWorksheetEntry,
            pk=kwargs["entry_pk"],
            is_active=True,
        )

        self.is_locked = is_worksheet_entry_locked(self.entry)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            self.model.objects
            .filter(
                worksheet_entry=self.entry,
                is_active=True,
            )
            .select_related("category")
            .order_by("created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["entry"] = self.entry
        context["detail_type"] = self.detail_type
        context["is_locked"] = self.is_locked

        context["create_url"] = reverse(
            self.create_url_name,
            kwargs={"entry_pk": self.entry.pk},
        )

        context["edit_url_name"] = self.edit_url_name
        context["deactivate_url_name"] = self.deactivate_url_name

        detail_rows = []

        for obj in self.object_list:
            detail_rows.append({
                "object": obj,
                "category": obj.category,
                "description": getattr(
                    obj,
                    self.description_field,
                    "",
                ),
            })

        context["detail_rows"] = detail_rows

        return context


class WorksheetDetailCreateView(LoginRequiredMixin, CreateView):
    template_name = "hazop/worksheet/details_form.html"

    model = None
    form_class = None
    detail_type = ""
    list_url_name = ""

    def dispatch(self, request, *args, **kwargs):
        self.entry = get_object_or_404(
            HAZOPWorksheetEntry,
            pk=kwargs["entry_pk"],
            is_active=True,
        )

        if is_worksheet_entry_locked(self.entry):
            return HttpResponseForbidden(
                "This HAZOP worksheet has been submitted "
                "and is locked for editing."
            )

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Recheck before saving in case the assessment was
        # submitted while the form was open.
        if is_worksheet_entry_locked(self.entry):
            return HttpResponseForbidden(
                "This HAZOP worksheet is locked for editing."
            )

        form.instance.worksheet_entry = self.entry
        form.instance.created_by = self.request.user

        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            self.list_url_name,
            kwargs={"entry_pk": self.entry.pk},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["entry"] = self.entry
        context["detail_type"] = self.detail_type
        context["is_edit"] = False
        context["is_locked"] = False

        return context


class WorksheetDetailUpdateView(LoginRequiredMixin, UpdateView):
    template_name = "hazop/worksheet/details_form.html"

    model = None
    form_class = None
    detail_type = ""
    list_url_name = ""

    def dispatch(self, request, *args, **kwargs):
        self.entry = get_object_or_404(
            HAZOPWorksheetEntry,
            pk=kwargs["entry_pk"],
            is_active=True,
        )

        if is_worksheet_entry_locked(self.entry):
            return HttpResponseForbidden(
                "This HAZOP worksheet has been submitted "
                "and is locked for editing."
            )

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.filter(
            worksheet_entry=self.entry,
            is_active=True,
        )

    def form_valid(self, form):
        # Recheck before saving.
        if is_worksheet_entry_locked(self.entry):
            return HttpResponseForbidden(
                "This HAZOP worksheet is locked for editing."
            )

        form.instance.updated_at = timezone.now()

        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            self.list_url_name,
            kwargs={"entry_pk": self.entry.pk},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["entry"] = self.entry
        context["detail_type"] = self.detail_type
        context["is_edit"] = True
        context["is_locked"] = False

        return context


class WorksheetDetailDeactivateView(LoginRequiredMixin, View):
    model = None
    list_url_name = ""

    http_method_names = ["post"]

    def post(self, request, entry_pk, pk):
        entry = get_object_or_404(
            HAZOPWorksheetEntry,
            pk=entry_pk,
            is_active=True,
        )

        if is_worksheet_entry_locked(entry):
            return HttpResponseForbidden(
                "This HAZOP worksheet has been submitted "
                "and is locked for editing."
            )

        detail = get_object_or_404(
            self.model,
            pk=pk,
            worksheet_entry=entry,
            is_active=True,
        )

        detail.is_active = False
        detail.save(
            update_fields=["is_active", "updated_at"]
        )

        return redirect(
            self.list_url_name,
            entry_pk=entry.pk,
        )


# ============================================================
# CAUSE VIEWS
# ============================================================

class HAZOPCauseListView(WorksheetDetailListView):
    model = HAZOPCause
    detail_type = "Cause"

    description_field = "cause_description"

    create_url_name = "hazop:cause_create"
    edit_url_name = "hazop:cause_edit"
    deactivate_url_name = "hazop:cause_deactivate"


class HAZOPCauseCreateView(WorksheetDetailCreateView):
    model = HAZOPCause
    form_class = HAZOPCauseForm
    detail_type = "Cause"
    list_url_name = "hazop:cause_list"


class HAZOPCauseUpdateView(WorksheetDetailUpdateView):
    model = HAZOPCause
    form_class = HAZOPCauseForm
    detail_type = "Cause"
    list_url_name = "hazop:cause_list"


class HAZOPCauseDeactivateView(WorksheetDetailDeactivateView):
    model = HAZOPCause
    list_url_name = "hazop:cause_list"


# ============================================================
# CONSEQUENCE VIEWS
# ============================================================

class HAZOPConsequenceListView(WorksheetDetailListView):
    model = HAZOPConsequence
    detail_type = "Consequence"

    description_field = "consequence_description"

    create_url_name = "hazop:consequence_create"
    edit_url_name = "hazop:consequence_edit"
    deactivate_url_name = "hazop:consequence_deactivate"


class HAZOPConsequenceCreateView(WorksheetDetailCreateView):
    model = HAZOPConsequence
    form_class = HAZOPConsequenceForm
    detail_type = "Consequence"
    list_url_name = "hazop:consequence_list"


class HAZOPConsequenceUpdateView(WorksheetDetailUpdateView):
    model = HAZOPConsequence
    form_class = HAZOPConsequenceForm
    detail_type = "Consequence"
    list_url_name = "hazop:consequence_list"


class HAZOPConsequenceDeactivateView(WorksheetDetailDeactivateView):
    model = HAZOPConsequence
    list_url_name = "hazop:consequence_list"


# ============================================================
# SAFEGUARD VIEWS
# ============================================================

class HAZOPSafeguardListView(WorksheetDetailListView):
    model = HAZOPSafeguard
    detail_type = "Safeguard"

    description_field = "safeguard_description"

    create_url_name = "hazop:safeguard_create"
    edit_url_name = "hazop:safeguard_edit"
    deactivate_url_name = "hazop:safeguard_deactivate"


class HAZOPSafeguardCreateView(WorksheetDetailCreateView):
    model = HAZOPSafeguard
    form_class = HAZOPSafeguardForm
    detail_type = "Safeguard"
    list_url_name = "hazop:safeguard_list"


class HAZOPSafeguardUpdateView(WorksheetDetailUpdateView):
    model = HAZOPSafeguard
    form_class = HAZOPSafeguardForm
    detail_type = "Safeguard"
    list_url_name = "hazop:safeguard_list"


class HAZOPSafeguardDeactivateView(WorksheetDetailDeactivateView):
    model = HAZOPSafeguard
    list_url_name = "hazop:safeguard_list"




# ============================================================
# WORKSHEET ENTRY LOCK
# ============================================================

WORKSHEET_LOCKED_STATUSES = {
    "SUBMITTED",
    "UNDER_REVIEW",
    "PENDING_APPROVAL",
    "APPROVED",
    "CLOSED",
}


def is_worksheet_entry_locked(entry):
    """
    Lock worksheet causes, consequences, and safeguards
    once any linked risk assessment is submitted.

    The worksheet becomes editable again if the assessment
    is rejected and returned to the assessor.
    """

    return entry.risk_assessments.filter(
        status__in=WORKSHEET_LOCKED_STATUSES
    ).exists()





@login_required
def hazop_risk_matrix_list(request):
    matrices = HAZOPRiskMatrix.objects.all().order_by("-created_at")

    return render(
        request,
        "hazop/risk_assessment/matrix_list.html",
        {
            "matrices": matrices,
        }
    )


@login_required
def hazop_risk_matrix_create(request):
    if request.method == "POST":
        form = HAZOPRiskMatrixForm(request.POST)

        if form.is_valid():
            matrix = form.save(commit=False)
            matrix.created_by = request.user

            if matrix.is_default:
                HAZOPRiskMatrix.objects.exclude(
                    pk=matrix.pk
                ).update(is_default=False)

            matrix.save()

            messages.success(
                request,
                "Risk Matrix created successfully."
            )

            return redirect(
                "hazop:risk_matrix_rating_create",
                matrix_pk=matrix.pk
            )

    else:
        form = HAZOPRiskMatrixForm()

    return render(
        request,
        "hazop/risk_assessment/matrix_form.html",
        {
            "form": form,
            "page_title": "Create Risk Matrix",
        }
    )


@login_required
def hazop_risk_matrix_rating_create(request, matrix_pk):
    matrix = get_object_or_404(
        HAZOPRiskMatrix,
        pk=matrix_pk
    )

    if request.method == "POST":
        form = HAZOPRiskRatingForm(request.POST)

        if form.is_valid():
            rating = form.save(commit=False)
            rating.matrix = matrix

            if rating.score > (
                matrix.likelihood_scale
                if rating.rating_type == "LIKELIHOOD"
                else matrix.severity_scale
            ):
                form.add_error(
                    "score",
                    "Score cannot exceed the configured matrix scale."
                )
            else:
                rating.save()

                messages.success(
                    request,
                    "Risk rating added successfully."
                )

                return redirect(
                    "hazop:risk_matrix_rating_create",
                    matrix_pk=matrix.pk
                )

    else:
        form = HAZOPRiskRatingForm()

    ratings = matrix.ratings.all().order_by(
        "rating_type",
        "score"
    )

    return render(
        request,
        "hazop/risk_assessment/matrix_ratings.html",
        {
            "matrix": matrix,
            "form": form,
            "ratings": ratings,
        }
    )


@login_required
def hazop_risk_level_list(request):
    risk_levels = HAZOPRiskLevel.objects.all().order_by(
        "minimum_score"
    )

    if request.method == "POST":
        form = HAZOPRiskLevelForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Risk Level created successfully."
            )

            return redirect("hazop:risk_level_list")

    else:
        form = HAZOPRiskLevelForm()

    return render(
        request,
        "hazop/risk_assessment/risk_level_list.html",
        {
            "risk_levels": risk_levels,
            "form": form,
        }
    )






@login_required
def hazop_risk_assessment_list(request, node_pk):
    node = get_object_or_404(
        HAZOPNode.objects.select_related("study"),
        pk=node_pk
    )

    assessments = (
        HAZOPRiskAssessment.objects
        .filter(worksheet_entry__node=node)
        .select_related(
            "worksheet_entry",
            "worksheet_entry__node",
            "matrix",
            "assessor",
            "reviewer",
            "approver",
            "action_responsible",
        )
        .order_by("-created_at")
    )

    # Summary: high and critical initial risk assessments
    high_initial_count = 0

    # Summary: assessments with residual risk evaluated
    residual_evaluated_count = 0

    # Summary: assessments still waiting for residual evaluation
    pending_evaluation_count = 0

    for assessment in assessments:
        initial_level = assessment.initial_risk_level

        if initial_level:
            level_name = initial_level.name.strip().lower()

            if level_name in [
                "high",
                "critical",
                "very high",
                "extreme",
            ]:
                high_initial_count += 1

        if assessment.residual_risk_score is not None:
            residual_evaluated_count += 1
        else:
            pending_evaluation_count += 1

    context = {
        "node": node,
        "study": node.study,
        "assessments": assessments,

        "high_initial_count": high_initial_count,
        "residual_evaluated_count": residual_evaluated_count,
        "pending_evaluation_count": pending_evaluation_count,

        "status_choices": HAZOPRiskAssessment.STATUS_CHOICES,
    }

    return render(
        request,
        "hazop/risk_assessment/assessment_list.html",
        context
    )


@login_required
def hazop_risk_assessment_create(request, node_pk, entry_pk):
    node = get_object_or_404(
        HAZOPNode,
        pk=node_pk
    )

    worksheet_entry = get_object_or_404(
        HAZOPWorksheetEntry,
        pk=entry_pk,
        node=node
    )

    matrix = (
        HAZOPRiskMatrix.objects
        .filter(is_active=True, is_default=True)
        .first()
    )

    if not matrix:
        matrix = (
            HAZOPRiskMatrix.objects
            .filter(is_active=True)
            .first()
        )

    if not matrix:
        messages.warning(
            request,
            "Please configure a Risk Matrix before creating an assessment."
        )

        return redirect("hazop:risk_matrix_list")

    if request.method == "POST":
        form = HAZOPRiskAssessmentForm(
            request.POST,
            matrix=matrix
        )

        if form.is_valid():
            assessment = form.save(commit=False)

            assessment.worksheet_entry = worksheet_entry
            assessment.matrix = matrix
            assessment.assessor = request.user

            assessment.save()

            messages.success(
                request,
                "Risk Assessment created successfully."
            )

            return redirect(
                "hazop:risk_assessment_detail",
                assessment_pk=assessment.pk
            )

    else:
        form = HAZOPRiskAssessmentForm(
            matrix=matrix,
            initial={
                "matrix": matrix,
            }
        )

    return render(
        request,
        "hazop/risk_assessment/assessment_form.html",
        {
            "form": form,
            "node": node,
            "study": node.study,
            "worksheet_entry": worksheet_entry,
            "matrix": matrix,
            "page_title": "Create Risk Assessment",
        }
    )


@login_required
def hazop_risk_assessment_detail(request, assessment_pk):
    assessment = get_object_or_404(
        HAZOPRiskAssessment.objects.select_related(
            "worksheet_entry",
            "matrix",
            "assessor",
            "action_responsible",
        ),
        pk=assessment_pk
    )

    review_history = (
        assessment.review_history
        .select_related("performed_by")
        .order_by("-created_at")
    )

    return render(
        request,
        "hazop/risk_assessment/assessment_detail.html",
        {
            "assessment": assessment,
            "node": assessment.worksheet_entry.node,
            "study": assessment.worksheet_entry.node.study,
            "review_history": review_history,
        }
    )


@login_required
def hazop_risk_assessment_edit(request, assessment_pk):
    assessment = get_object_or_404(
        HAZOPRiskAssessment,
        pk=assessment_pk
    )

    if assessment.status in ["APPROVED", "CLOSED"]:
        messages.warning(
            request,
            "Approved or closed assessments cannot be edited."
        )

        return redirect(
            "hazop:risk_assessment_detail",
            assessment_pk=assessment.pk
        )

    matrix = assessment.matrix

    if request.method == "POST":
        form = HAZOPRiskAssessmentForm(
            request.POST,
            instance=assessment,
            matrix=matrix
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Risk Assessment updated successfully."
            )

            return redirect(
                "hazop:risk_assessment_detail",
                assessment_pk=assessment.pk
            )

    else:
        form = HAZOPRiskAssessmentForm(
            instance=assessment,
            matrix=matrix
        )

    return render(
        request,
        "hazop/risk_assessment/assessment_form.html",
        {
            "form": form,
            "assessment": assessment,
            "node": assessment.worksheet_entry.node,
            "study": assessment.worksheet_entry.node.study,
            "worksheet_entry": assessment.worksheet_entry,
            "matrix": matrix,
            "page_title": "Edit Risk Assessment",
        }
    )



def _record_assessment_workflow(
    assessment,
    action,
    from_status,
    to_status,
    user,
    comments="",
):
    """
    Update assessment workflow status and save review history.
    """

    assessment.status = to_status

    if comments:
        assessment.review_comments = comments

    now = timezone.now()

    if action in ["SUBMITTED", "RESUBMITTED"]:
        assessment.submitted_at = now

    elif action == "UNDER_REVIEW":
        assessment.reviewed_at = now

    elif action == "REVIEW_SUBMITTED":
        assessment.reviewed_at = now

    elif action == "APPROVED":
        assessment.approved_at = now

    elif action == "CLOSED":
        assessment.closed_at = now

    assessment.save()

    HAZOPRiskAssessmentReviewHistory.objects.create(
        assessment=assessment,
        action=action,
        from_status=from_status,
        to_status=to_status,
        comments=comments,
        performed_by=user,
    )


@login_required
@require_POST
def risk_assessment_submit(request, assessment_pk):
    """
    Assessor submits a draft or rejected assessment for review.
    """

    assessment = get_object_or_404(
        HAZOPRiskAssessment,
        pk=assessment_pk,
    )

    if assessment.assessor_id != request.user.id:
        return HttpResponseForbidden(
            "Only the assigned assessor can submit this assessment."
        )

    if assessment.status not in ["DRAFT", "REJECTED"]:
        messages.error(
            request,
            "This assessment cannot be submitted in its current status.",
        )
        return redirect(
            "hazop:risk_assessment_detail",
            assessment_pk=assessment.pk,
        )

    if not assessment.reviewer_id:
        messages.error(
            request,
            "Please assign a reviewer before submitting.",
        )
        return redirect(
            "hazop:risk_assessment_edit",
            assessment_pk=assessment.pk,
        )

    if not assessment.approver_id:
        messages.error(
            request,
            "Please assign an approver before submitting.",
        )
        return redirect(
            "hazop:risk_assessment_edit",
            assessment_pk=assessment.pk,
        )

    if not assessment.action_required:
        messages.error(
            request,
            "Please specify the required control action before submitting.",
        )
        return redirect(
            "hazop:risk_assessment_edit",
            assessment_pk=assessment.pk,
        )

    with transaction.atomic():
        old_status = assessment.status

        action = (
            "RESUBMITTED"
            if old_status == "REJECTED"
            else "SUBMITTED"
        )

        _record_assessment_workflow(
            assessment=assessment,
            action=action,
            from_status=old_status,
            to_status="SUBMITTED",
            user=request.user,
            comments="",
        )

    messages.success(
        request,
        "Risk Assessment submitted for review successfully.",
    )

    return redirect(
        "hazop:risk_assessment_detail",
        assessment_pk=assessment.pk,
    )


@login_required
@require_POST
def risk_assessment_start_review(request, assessment_pk):
    """
    Assigned reviewer starts reviewing the assessment.
    """

    assessment = get_object_or_404(
        HAZOPRiskAssessment,
        pk=assessment_pk,
    )

    if assessment.reviewer_id != request.user.id:
        return HttpResponseForbidden(
            "Only the assigned reviewer can start the review."
        )

    if assessment.status != "SUBMITTED":
        messages.error(
            request,
            "Only submitted assessments can be reviewed.",
        )
        return redirect(
            "hazop:risk_assessment_detail",
            assessment_pk=assessment.pk,
        )

    with transaction.atomic():
        old_status = assessment.status

        _record_assessment_workflow(
            assessment=assessment,
            action="UNDER_REVIEW",
            from_status=old_status,
            to_status="UNDER_REVIEW",
            user=request.user,
            comments="Review started.",
        )

    messages.success(
        request,
        "Risk Assessment review started.",
    )

    return redirect(
        "hazop:risk_assessment_detail",
        assessment_pk=assessment.pk,
    )


@login_required
@require_POST
def risk_assessment_reject(request, assessment_pk):
    """
    Assigned reviewer rejects the assessment with mandatory comments.
    """

    assessment = get_object_or_404(
        HAZOPRiskAssessment,
        pk=assessment_pk,
    )

    if assessment.reviewer_id != request.user.id:
        return HttpResponseForbidden(
            "Only the assigned reviewer can reject this assessment."
        )

    if assessment.status != "UNDER_REVIEW":
        messages.error(
            request,
            "Only assessments under review can be rejected.",
        )
        return redirect(
            "hazop:risk_assessment_detail",
            assessment_pk=assessment.pk,
        )

    comments = request.POST.get("comments", "").strip()

    if not comments:
        messages.error(
            request,
            "Please provide rejection comments.",
        )
        return redirect(
            "hazop:risk_assessment_detail",
            assessment_pk=assessment.pk,
        )

    with transaction.atomic():
        old_status = assessment.status

        _record_assessment_workflow(
            assessment=assessment,
            action="REJECTED",
            from_status=old_status,
            to_status="REJECTED",
            user=request.user,
            comments=comments,
        )

    messages.success(
        request,
        "Risk Assessment rejected and returned to the assessor.",
    )

    return redirect(
        "hazop:risk_assessment_detail",
        assessment_pk=assessment.pk,
    )

@login_required
@require_POST
def risk_assessment_submit_review(request, assessment_pk):
    """
    Assigned reviewer submits the completed review
    to the assigned approver.
    """

    assessment = get_object_or_404(
        HAZOPRiskAssessment,
        pk=assessment_pk,
    )

    if assessment.reviewer_id != request.user.id:
        return HttpResponseForbidden(
            "Only the assigned reviewer can submit this review."
        )

    if assessment.status != "UNDER_REVIEW":
        messages.error(
            request,
            "Only assessments under review can be submitted to the approver.",
        )
        return redirect(
            "hazop:risk_assessment_detail",
            assessment_pk=assessment.pk,
        )

    if not assessment.approver_id:
        messages.error(
            request,
            "Please assign an approver before submitting the review.",
        )
        return redirect(
            "hazop:risk_assessment_detail",
            assessment_pk=assessment.pk,
        )

    comments = request.POST.get("comments", "").strip()

    with transaction.atomic():
        old_status = assessment.status

        _record_assessment_workflow(
            assessment=assessment,
            action="REVIEW_SUBMITTED",
            from_status=old_status,
            to_status="PENDING_APPROVAL",
            user=request.user,
            comments=comments,
        )

    messages.success(
        request,
        "Review submitted to the approver successfully.",
    )

    return redirect(
        "hazop:risk_assessment_detail",
        assessment_pk=assessment.pk,
    )

@login_required
@require_POST
def risk_assessment_approve(request, assessment_pk):
    """
    Assigned approver approves the assessment.
    """

    assessment = get_object_or_404(
        HAZOPRiskAssessment,
        pk=assessment_pk,
    )

    if assessment.approver_id != request.user.id:
        return HttpResponseForbidden(
            "Only the assigned approver can approve this assessment."
        )

    if assessment.status != "PENDING_APPROVAL":
        messages.error(
            request,
            "Only assessments pending approval can be approved.",
        )
        return redirect(
            "hazop:risk_assessment_detail",
            assessment_pk=assessment.pk,
        )

    comments = request.POST.get("comments", "").strip()

    with transaction.atomic():
        old_status = assessment.status

        _record_assessment_workflow(
            assessment=assessment,
            action="APPROVED",
            from_status=old_status,
            to_status="APPROVED",
            user=request.user,
            comments=comments,
        )

    messages.success(
        request,
        "Risk Assessment approved successfully.",
    )

    return redirect(
        "hazop:risk_assessment_detail",
        assessment_pk=assessment.pk,
    )


@login_required
@require_POST
def risk_assessment_close(request, assessment_pk):
    """
    Assigned approver closes an approved assessment.
    """

    assessment = get_object_or_404(
        HAZOPRiskAssessment,
        pk=assessment_pk,
    )

    if assessment.approver_id != request.user.id:
        return HttpResponseForbidden(
            "Only the assigned approver can close this assessment."
        )

    if assessment.status != "APPROVED":
        messages.error(
            request,
            "Only approved assessments can be closed.",
        )
        return redirect(
            "hazop:risk_assessment_detail",
            assessment_pk=assessment.pk,
        )

    comments = request.POST.get("comments", "").strip()

    with transaction.atomic():
        old_status = assessment.status

        _record_assessment_workflow(
            assessment=assessment,
            action="CLOSED",
            from_status=old_status,
            to_status="CLOSED",
            user=request.user,
            comments=comments,
        )

    messages.success(
        request,
        "Risk Assessment closed successfully.",
    )

    return redirect(
        "hazop:risk_assessment_detail",
        assessment_pk=assessment.pk,
    )





@login_required
def hazop_action_list(request):

    actions = (
        HAZOPAction.objects
        .select_related(
            "recommendation",
            "department",
            "assigned_to",
        )
        .order_by("due_date", "-created_at")
    )

    paginator = Paginator(actions, 25)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "hazop/action_list.html",
        {
            "actions": page_obj,
            "page_obj": page_obj,
        },
    )


@login_required
def hazop_action_create(request):
    if request.method == "POST":
        form = HAZOPActionForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                action = form.save(commit=False)
                action.created_by = request.user
                action.save()

                record_hazop_action_history(
                    action=action,
                    event="CREATED",
                    user=request.user,
                    previous_status="",
                    new_status=action.status,
                    remarks="HAZOP action created and assigned.",
                )

            messages.success(
                request,
                f"Action {action.action_number} created successfully.",
            )

            return redirect("hazop:hazop_action_list")

    else:
        form = HAZOPActionForm()

    return render(
        request,
        "hazop/action_form.html",
        {
            "form": form,
            "page_title": "Create HAZOP Action",
        },
    )


@login_required
def hazop_action_edit(request, pk):
    action = get_object_or_404(
        HAZOPAction.objects.select_related(
            "recommendation",
            "department",
            "assigned_to",
            "created_by",
        ),
        pk=pk,
    )

    # Only the action creator or admin/staff can edit action details.
    can_edit_action = (
        action.created_by_id == request.user.id
        or request.user.is_staff
        or request.user.is_superuser
    )

    if not can_edit_action:
        messages.error(
            request,
            "You do not have permission to edit this action."
        )
        return redirect(
            "hazop:hazop_action_detail",
            pk=action.pk,
        )

    # Do not allow editing after verification submission or closure.
    locked_statuses = [
        "SUBMITTED_FOR_VERIFICATION",
        "VERIFIED",
        "CANCELLED",
    ]

    if action.status in locked_statuses:
        messages.warning(
            request,
            "This action cannot be edited in its current status."
        )
        return redirect(
            "hazop:hazop_action_detail",
            pk=action.pk,
        )

    if request.method == "POST":
        form = HAZOPActionForm(
            request.POST,
            instance=action,
        )

        if form.is_valid():
            with transaction.atomic():
                updated_action = form.save()

                record_hazop_action_history(
                    action=updated_action,
                    event="UPDATED",
                    user=request.user,
                    previous_status=updated_action.status,
                    new_status=updated_action.status,
                    remarks="Action details updated.",
                )

            messages.success(
                request,
                f"Action {action.action_number} updated successfully."
            )

            return redirect(
                "hazop:hazop_action_detail",
                pk=action.pk,
            )

    else:
        form = HAZOPActionForm(instance=action)

    return render(
        request,
        "hazop/action_form.html",
        {
            "form": form,
            "action": action,
            "is_edit": True,
            "page_title": f"Edit Action {action.action_number}",
        },
    )




@login_required
def hazop_action_detail(request, pk):
    action = get_object_or_404(
        HAZOPAction.objects.select_related(
            "recommendation",
            "recommendation__worksheet_entry",
            "department",
            "assigned_to",
            "created_by",
            "completed_by",
            "verified_by",
        ),
        pk=pk,
    )

    is_action_owner = (
        action.assigned_to_id == request.user.id
    )

    # The action creator or staff/admin can verify.
    # The assigned employee cannot verify their own action.
    can_verify_action = (
        (
            action.created_by_id == request.user.id
            or request.user.is_staff
            or request.user.is_superuser
        )
        and action.assigned_to_id != request.user.id
    )

    return render(
        request,
        "hazop/hazop_action_detail.html",
        {
            "action": action,
            "is_action_owner": is_action_owner,
            "can_verify_action": can_verify_action,
            "action_history": action.history.select_related(
                "performed_by"
            ).all(),
        },
    )


@login_required
@require_POST
def hazop_action_workflow(request, pk):
    with transaction.atomic():
        action = get_object_or_404(
            HAZOPAction.objects.select_for_update(),
            pk=pk,
        )

        workflow_action = request.POST.get(
            "workflow_action",
            "",
        ).strip()

        is_action_owner = (
            action.assigned_to_id == request.user.id
        )

        can_verify_action = (
            (
                action.created_by_id == request.user.id
                or request.user.is_staff
                or request.user.is_superuser
            )
            and action.assigned_to_id != request.user.id
        )

        # --------------------------------------------------
        # START ACTION
        # --------------------------------------------------
        if workflow_action == "start":

            if not is_action_owner:
                return HttpResponseForbidden(
                    "Only the assigned employee can start this action."
                )

            if action.status not in ["OPEN", "REOPENED"]:
                messages.error(
                    request,
                    "This action cannot be started in its current status.",
                )
                return redirect(
                    "hazop:hazop_action_detail",
                    pk=action.pk,
                )

            previous_status = action.status
            action.status = "IN_PROGRESS"

            action.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            record_hazop_action_history(
                action=action,
                event="STARTED",
                user=request.user,
                previous_status=previous_status,
                new_status=action.status,
                remarks="Action started by assigned employee.",
            )

            messages.success(
                request,
                "Action started successfully.",
            )

        # --------------------------------------------------
        # SAVE PROGRESS
        # --------------------------------------------------
        elif workflow_action == "save_progress":

            if not is_action_owner:
                return HttpResponseForbidden(
                    "Only the assigned employee can update this action."
                )

            if action.status != "IN_PROGRESS":
                messages.error(
                    request,
                    "Progress can only be updated while the action is In Progress.",
                )
                return redirect(
                    "hazop:hazop_action_detail",
                    pk=action.pk,
                )

            previous_status = action.status

            action.completion_remarks = request.POST.get(
                "completion_remarks",
                "",
            ).strip()

            uploaded_evidence = request.FILES.get("evidence")

            try:
                validate_hazop_action_evidence(uploaded_evidence)

            except ValidationError as error:
                messages.error(request, error.message)

                return redirect(
                    "hazop:hazop_action_detail",
                    pk=action.pk,
                )

            if uploaded_evidence:
                if uploaded_evidence.size > 10 * 1024 * 1024:
                    messages.error(
                        request,
                        "Evidence file must be 10 MB or smaller.",
                    )
                    return redirect(
                        "hazop:hazop_action_detail",
                        pk=action.pk,
                    )

                action.evidence = uploaded_evidence

            action.save(
                update_fields=[
                    "completion_remarks",
                    "evidence",
                    "updated_at",
                ]
            )

            record_hazop_action_history(
                action=action,
                event="PROGRESS_UPDATED",
                user=request.user,
                previous_status=previous_status,
                new_status=action.status,
                remarks=action.completion_remarks,
                evidence_name=(
                    action.evidence.name
                    if action.evidence
                    else ""
                ),
            )

            messages.success(
                request,
                "Action progress saved successfully.",
            )

        # --------------------------------------------------
        # SUBMIT FOR VERIFICATION
        # --------------------------------------------------
        elif workflow_action == "submit_for_verification":

            if not is_action_owner:
                return HttpResponseForbidden(
                    "Only the assigned employee can submit this action."
                )

            if action.status != "IN_PROGRESS":
                messages.error(
                    request,
                    "Only In Progress actions can be submitted for verification.",
                )
                return redirect(
                    "hazop:hazop_action_detail",
                    pk=action.pk,
                )

            completion_remarks = request.POST.get(
                "completion_remarks",
                "",
            ).strip()

            if not completion_remarks:
                messages.error(
                    request,
                    "Please enter completion remarks before submitting.",
                )
                return redirect(
                    "hazop:hazop_action_detail",
                    pk=action.pk,
                )

            uploaded_evidence = request.FILES.get("evidence")

            try:
                validate_hazop_action_evidence(uploaded_evidence)

            except ValidationError as error:
                messages.error(request, error.message)

                return redirect(
                    "hazop:hazop_action_detail",
                    pk=action.pk,
                )

            if uploaded_evidence:
                if uploaded_evidence.size > 10 * 1024 * 1024:
                    messages.error(
                        request,
                        "Evidence file must be 10 MB or smaller.",
                    )
                    return redirect(
                        "hazop:hazop_action_detail",
                        pk=action.pk,
                    )

                action.evidence = uploaded_evidence

            previous_status = action.status

            action.completion_remarks = completion_remarks
            action.status = "SUBMITTED_FOR_VERIFICATION"
            action.completed_by = request.user
            action.completed_at = timezone.now()

            action.save(
                update_fields=[
                    "completion_remarks",
                    "evidence",
                    "status",
                    "completed_by",
                    "completed_at",
                    "updated_at",
                ]
            )

            record_hazop_action_history(
                action=action,
                event="SUBMITTED",
                user=request.user,
                previous_status=previous_status,
                new_status=action.status,
                remarks=action.completion_remarks,
                evidence_name=(
                    action.evidence.name
                    if action.evidence
                    else ""
                ),
            )

            messages.success(
                request,
                "Action submitted for verification successfully.",
            )

        # --------------------------------------------------
        # VERIFY ACTION
        # --------------------------------------------------
        elif workflow_action == "verify":

            if not can_verify_action:
                return HttpResponseForbidden(
                    "You are not authorized to verify this action."
                )

            if action.status != "SUBMITTED_FOR_VERIFICATION":
                messages.error(
                    request,
                    "Only submitted actions can be verified.",
                )
                return redirect(
                    "hazop:hazop_action_detail",
                    pk=action.pk,
                )

            verification_remarks = request.POST.get(
                "verification_remarks",
                "",
            ).strip()

            if not verification_remarks:
                messages.error(
                    request,
                    "Please enter verification remarks.",
                )
                return redirect(
                    "hazop:hazop_action_detail",
                    pk=action.pk,
                )

            previous_status = action.status

            action.status = "VERIFIED"
            action.verified_by = request.user
            action.verified_at = timezone.now()
            action.verification_remarks = verification_remarks

            action.save(
                update_fields=[
                    "status",
                    "verified_by",
                    "verified_at",
                    "verification_remarks",
                    "updated_at",
                ]
            )

            record_hazop_action_history(
                action=action,
                event="VERIFIED",
                user=request.user,
                previous_status=previous_status,
                new_status=action.status,
                remarks=action.verification_remarks,
            )

            messages.success(
                request,
                "Action verified successfully.",
            )

        # --------------------------------------------------
        # REOPEN ACTION
        # --------------------------------------------------
        elif workflow_action == "reopen":

            if not can_verify_action:
                return HttpResponseForbidden(
                    "You are not authorized to reopen this action."
                )

            if action.status != "SUBMITTED_FOR_VERIFICATION":
                messages.error(
                    request,
                    "Only submitted actions can be reopened.",
                )
                return redirect(
                    "hazop:hazop_action_detail",
                    pk=action.pk,
                )

            verification_remarks = request.POST.get(
                "verification_remarks",
                "",
            ).strip()

            if not verification_remarks:
                messages.error(
                    request,
                    "Please provide remarks explaining why the action is being reopened.",
                )
                return redirect(
                    "hazop:hazop_action_detail",
                    pk=action.pk,
                )

            previous_status = action.status

            action.status = "REOPENED"
            action.verification_remarks = verification_remarks

            # Clear previous completion details
            action.completed_by = None
            action.completed_at = None

            # Clear any stale verification details
            action.verified_by = None
            action.verified_at = None

            action.save(
                update_fields=[
                    "status",
                    "verification_remarks",
                    "completed_by",
                    "completed_at",
                    "verified_by",
                    "verified_at",
                    "updated_at",
                ]
            )

            record_hazop_action_history(
                action=action,
                event="REOPENED",
                user=request.user,
                previous_status=previous_status,
                new_status=action.status,
                remarks=action.verification_remarks,
            )

            messages.success(
                request,
                "Action reopened. The assigned employee can continue working on it.",
            )

        else:
            messages.error(
                request,
                "Invalid workflow action.",
            )

    return redirect(
        "hazop:hazop_action_detail",
        pk=action.pk,
    )


def validate_hazop_action_evidence(uploaded_file):
    """
    Validate HAZOP action evidence file size and extension.
    """

    if not uploaded_file:
        return

    max_size = 10 * 1024 * 1024  # 10 MB

    allowed_extensions = {
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
    }

    if uploaded_file.size > max_size:
        raise ValidationError(
            "Evidence file must be 10 MB or smaller."
        )

    file_extension = os.path.splitext(
        uploaded_file.name
    )[1].lower()

    if file_extension not in allowed_extensions:
        raise ValidationError(
            "Invalid evidence file type. "
            "Allowed files: PDF, JPG, PNG, DOC, DOCX, XLS, XLSX."
        )

    

def record_hazop_action_history(
    action,
    event,
    user,
    previous_status="",
    new_status="",
    remarks="",
    evidence_name="",
):
    HAZOPActionHistory.objects.create(
        action=action,
        event=event,
        previous_status=previous_status,
        new_status=new_status,
        performed_by=user,
        remarks=remarks,
        evidence_name=evidence_name,
    )









@login_required
def risk_assessment_export_excel(request, assessment_pk):
    assessment = get_object_or_404(
        HAZOPRiskAssessment.objects.select_related(
            "worksheet_entry",
            "matrix",
            "assessor",
            "reviewer",
            "approver",
            "action_responsible",
        ),
        pk=assessment_pk,
    )

    workbook = Workbook()

    # =====================================================
    # SHEET 1: RISK ASSESSMENT
    # =====================================================
    ws = workbook.active
    ws.title = "Risk Assessment"

    ws.append(["HAZOP RISK ASSESSMENT REPORT"])
    ws.append(["Assessment Number", assessment.assessment_number or ""])
    ws.append(["Assessment Title", assessment.hazard_title or ""])
    ws.append(["Hazard Description", assessment.hazard_description or ""])
    # Get the consequence value using the actual model field
    consequence_value = ""

    consequence_field_names = [
        "consequence",
        "potential_consequence",
        "potential_consequences",
        "consequence_description",
    ]

    for field_name in consequence_field_names:
        try:
            assessment._meta.get_field(field_name)
            consequence_value = getattr(assessment, field_name, "") or ""
            break
        except Exception:
            continue

    ws.append(["Potential Consequence", consequence_value])
    ws.append(["Persons Exposed", assessment.persons_exposed or ""])
    ws.append(["Existing Controls", assessment.existing_controls or ""])

    ws.append([])
    ws.append(["INITIAL RISK EVALUATION"])
    ws.append(["Initial Likelihood", assessment.initial_likelihood or ""])
    ws.append(["Initial Severity", assessment.initial_severity or ""])

    ws.append([])
    ws.append(["ADDITIONAL RISK CONTROLS"])
    ws.append(["Additional Controls", assessment.additional_controls or ""])
    ws.append(["Control Hierarchy", assessment.control_hierarchy or ""])
    ws.append(["Action Required", assessment.action_required or ""])
    ws.append([
        "Action Responsible",
        str(assessment.action_responsible)
        if assessment.action_responsible else ""
    ])
    ws.append([
        "Action Due Date",
        assessment.action_due_date.strftime("%d-%m-%Y")
        if assessment.action_due_date else ""
    ])

    ws.append([])
    ws.append(["RESIDUAL RISK EVALUATION"])
    ws.append(["Residual Likelihood", assessment.residual_likelihood or ""])
    ws.append(["Residual Severity", assessment.residual_severity or ""])

    ws.append([])
    ws.append(["WORKFLOW DETAILS"])
    ws.append([
        "Current Status",
        assessment.get_status_display()
        if hasattr(assessment, "get_status_display")
        else assessment.status
    ])
    ws.append([
        "Assessor",
        str(assessment.assessor) if assessment.assessor else ""
    ])
    ws.append([
        "Reviewer",
        str(assessment.reviewer) if assessment.reviewer else ""
    ])
    ws.append([
        "Approver",
        str(assessment.approver) if assessment.approver else ""
    ])
    ws.append([
        "Review Comments",
        assessment.review_comments or ""
    ])

    ws.append([
        "Submitted At",
        assessment.submitted_at.strftime("%d-%m-%Y %H:%M")
        if assessment.submitted_at else ""
    ])
    ws.append([
        "Reviewed At",
        assessment.reviewed_at.strftime("%d-%m-%Y %H:%M")
        if assessment.reviewed_at else ""
    ])
    ws.append([
        "Approved At",
        assessment.approved_at.strftime("%d-%m-%Y %H:%M")
        if assessment.approved_at else ""
    ])
    ws.append([
        "Closed At",
        assessment.closed_at.strftime("%d-%m-%Y %H:%M")
        if assessment.closed_at else ""
    ])

    # =====================================================
    # SHEET 2: REVIEW HISTORY
    # =====================================================
    history_ws = workbook.create_sheet("Review History")

    history_ws.append([
        "Action",
        "From Status",
        "To Status",
        "Performed By",
        "Comments",
        "Date & Time",
    ])

    for history in assessment.review_history.all():
        performed_by = (
            history.performed_by.get_full_name()
            or str(history.performed_by)
            if history.performed_by
            else ""
        )

        history_ws.append([
            history.action or "",
            history.from_status or "",
            history.to_status or "",
            performed_by,
            history.comments or "",
            history.created_at.strftime("%d-%m-%Y %H:%M")
            if history.created_at else "",
        ])

    # =====================================================
    # EXCEL FORMATTING
    # =====================================================
    for sheet in workbook.worksheets:
        sheet.freeze_panes = "A2"

        for row in sheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(
                    vertical="top",
                    wrap_text=True,
                )

        # Format first row
        for cell in sheet[1]:
            cell.font = Font(
                bold=True,
                color="FFFFFF",
                size=12,
            )
            cell.fill = PatternFill(
                start_color="1F4E78",
                end_color="1F4E78",
                fill_type="solid",
            )

        # Set column widths
        for column_cells in sheet.columns:
            max_length = 0
            column_letter = get_column_letter(
                column_cells[0].column
            )

            for cell in column_cells:
                if cell.value:
                    max_length = max(
                        max_length,
                        len(str(cell.value))
                    )

            sheet.column_dimensions[column_letter].width = min(
                max_length + 4,
                50,
            )

    # =====================================================
    # DOWNLOAD EXCEL FILE
    # =====================================================
    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    filename = (
        f"HAZOP_Risk_Assessment_"
        f"{assessment.assessment_number or assessment.pk}.xlsx"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )

    workbook.save(response)

    return response