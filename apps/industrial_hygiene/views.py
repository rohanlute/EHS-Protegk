from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.urls import reverse
from datetime import date,timedelta
from django.db.models import Count,Q
from django.db.models.functions import TruncMonth
from django.views.generic import TemplateView,ListView,CreateView,UpdateView,DeleteView,DetailView
from .models import (HazardMaster,HazardCategoryMaster,ExposureTypeMaster,ExposureGroupMaster,
                     MonitoringTypeMaster,MonitoringParameterMaster,UnitMaster,ExposureLimitMaster,
                     InstrumentMaster,LaboratoryMaster,IHProgramMaster,MonitoringPlan,MonitoringSchedule,
                     SamplingManagement,MeasurementEntry,LaboratoryResult,ExposureAssessment,
                     ComplianceRecord,ExceedanceAction,ReMonitoring)
from .forms import (HazardMasterForm,HazardCategoryMasterForm,ExposureTypeMasterForm,
                    ExposureGroupMasterForm,MonitoringTypeMasterForm,MonitoringParameterMasterForm,
                    UnitMasterForm,ExposureLimitMasterForm,InstrumentMasterForm,LaboratoryMasterForm,
                    IHProgramMasterForm,MonitoringPlanForm,MonitoringScheduleForm,SamplingManagementForm,
                    MeasurementEntryForm,LaboratoryResultForm,ExposureAssessmentForm,ComplianceRecordForm,
                    ExceedanceActionForm,ReMonitoringForm)




# =============================================
# IndustrialHygieneDashboardView - Displays Industrial Hygiene analytical dashboard.
# =============================================
class IndustrialHygieneDashboardView(LoginRequiredMixin,TemplateView):
    template_name = "industrial_hygiene/dashboard/industrial_hygiene_dashboard.html"

    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        today = date.today()
        current_year = today.year
        thirty_days = today + timedelta(days=30)

        schedules = MonitoringSchedule.objects.filter(is_active=True)
        samples = SamplingManagement.objects.filter(is_active=True)
        measurements = MeasurementEntry.objects.filter(is_active=True)
        laboratory_results = LaboratoryResult.objects.filter(is_active=True)
        assessments = ExposureAssessment.objects.filter(is_active=True)
        compliance_records = ComplianceRecord.objects.filter(is_active=True)
        exceedance_actions = ExceedanceAction.objects.filter(is_active=True)
        re_monitoring = ReMonitoring.objects.filter(is_active=True)

        context["current_year"] = current_year

        context["total_monitoring"] = schedules.count()
        context["completed_monitoring"] = schedules.filter(status="COMPLETED").count()
        context["pending_monitoring"] = schedules.filter(
            status__in=["SCHEDULED","IN_PROGRESS"]
        ).count()
        context["overdue_monitoring"] = schedules.filter(
            Q(status="OVERDUE") |
            Q(planned_date__lt=today,status__in=["SCHEDULED","IN_PROGRESS"])
        ).count()

        context["total_samples"] = samples.count()
        context["total_measurements"] = measurements.count()
        context["total_laboratory_results"] = laboratory_results.count()
        context["total_exposure_assessments"] = assessments.count()

        context["compliant_results"] = compliance_records.filter(
            compliance_status="WITHIN_LIMIT"
        ).count()

        context["non_compliant_results"] = compliance_records.filter(
            compliance_status="EXCEEDS_LIMIT"
        ).count()

        context["open_exceedances"] = exceedance_actions.filter(
            status__in=[
                "OPEN",
                "UNDER_INVESTIGATION",
                "ACTION_IN_PROGRESS",
                "PENDING_VERIFICATION",
            ]
        ).count()

        context["closed_exceedances"] = exceedance_actions.filter(
            status="CLOSED"
        ).count()

        context["high_risk_exposures"] = assessments.filter(
            risk_level__in=["HIGH","CRITICAL"]
        ).count()

        context["critical_risk_exposures"] = assessments.filter(
            risk_level="CRITICAL"
        ).count()

        context["re_monitoring_due"] = re_monitoring.filter(
            is_active=True,
            status__in=["PLANNED","SCHEDULED"],
            planned_date__isnull=False,
            planned_date__lte=thirty_days
        ).count()

        context["overdue_actions"] = exceedance_actions.filter(
            due_date__lt=today,
            due_date__isnull=False,
            status__in=[
                "OPEN",
                "UNDER_INVESTIGATION",
                "ACTION_IN_PROGRESS",
                "PENDING_VERIFICATION",
            ]
        ).count()

        context["monitoring_status_distribution"] = [
            {
                "label":"Scheduled",
                "value":schedules.filter(status="SCHEDULED").count(),
            },
            {
                "label":"In Progress",
                "value":schedules.filter(status="IN_PROGRESS").count(),
            },
            {
                "label":"Completed",
                "value":schedules.filter(status="COMPLETED").count(),
            },
            {
                "label":"Overdue",
                "value":schedules.filter(status="OVERDUE").count(),
            },
            {
                "label":"Cancelled",
                "value":schedules.filter(status="CANCELLED").count(),
            },
        ]

        context["compliance_distribution"] = [
            {
                "label":"Within Limit",
                "value":compliance_records.filter(
                    compliance_status="WITHIN_LIMIT"
                ).count(),
            },
            {
                "label":"Exceeds Limit",
                "value":compliance_records.filter(
                    compliance_status="EXCEEDS_LIMIT"
                ).count(),
            },
            {
                "label":"Not Assessed",
                "value":compliance_records.filter(
                    compliance_status="NOT_ASSESSED"
                ).count(),
            },
        ]

        context["risk_distribution"] = [
            {
                "label":"Low",
                "value":assessments.filter(risk_level="LOW").count(),
            },
            {
                "label":"Medium",
                "value":assessments.filter(risk_level="MEDIUM").count(),
            },
            {
                "label":"High",
                "value":assessments.filter(risk_level="HIGH").count(),
            },
            {
                "label":"Critical",
                "value":assessments.filter(risk_level="CRITICAL").count(),
            },
            {
                "label":"Not Assessed",
                "value":assessments.filter(
                    risk_level="NOT_ASSESSED"
                ).count(),
            },
        ]

        monthly_monitoring = schedules.filter(
            planned_date__year=current_year
        ).annotate(
            month=TruncMonth("planned_date")
        ).values(
            "month"
        ).annotate(
            total=Count("id")
        ).order_by("month")

        context["monitoring_trend"] = [
            {
                "month":item["month"].strftime("%b"),
                "value":item["total"],
            }
            for item in monthly_monitoring
        ]

        monthly_samples = samples.filter(
            sampling_date__year=current_year
        ).annotate(
            month=TruncMonth("sampling_date")
        ).values(
            "month"
        ).annotate(
            total=Count("id")
        ).order_by("month")

        context["sampling_trend"] = [
            {
                "month":item["month"].strftime("%b"),
                "value":item["total"],
            }
            for item in monthly_samples
        ]

        monthly_compliance = compliance_records.filter(
            assessment_date__year=current_year
        ).annotate(
            month=TruncMonth("assessment_date")
        ).values(
            "month"
        ).annotate(
            total=Count("id"),
            exceeded=Count(
                "id",
               filter=Q(compliance_status="EXCEEDS_LIMIT")
            ),
        ).order_by("month")

        context["compliance_trend"] = [
            {
                "month":item["month"].strftime("%b"),
                "total":item["total"],
                "exceeded":item["exceeded"],
            }
            for item in monthly_compliance
        ]

        context["monitoring_by_hazard"] = list(
            schedules.filter(
                is_active=True
            ).values(
                "monitoring_plan__hazard__hazard"
            ).annotate(
                total=Count("id")
            ).order_by("-total")[:10]
        )

        context["monitoring_by_department"] = list(
            samples.filter(
                is_active=True
            ).values(
                "department"
            ).exclude(
                department__isnull=True
            ).exclude(
                department=""
            ).annotate(
                total=Count("id")
            ).order_by("-total")[:10]
        )

        context["monitoring_by_exposure_group"] = list(
            samples.filter(
                is_active=True,
                exposure_group__isnull=False
            ).values(
                "exposure_group__exposure_group"
            ).annotate(
                total=Count("id")
            ).order_by("-total")[:10]
        )

        context["upcoming_monitoring"] = schedules.filter(
            is_active=True,
            planned_date__gte=today,
            planned_date__lte=thirty_days,
            status__in=["SCHEDULED","IN_PROGRESS"]
        ).select_related(
            "monitoring_plan",
            "monitoring_plan__plant",
            "responsible_person",
            "assigned_to",
        ).order_by(
            "planned_date"
        )[:10]

        context["overdue_monitoring_list"] = schedules.filter(
            is_active=True
        ).filter(
            Q(status="OVERDUE") |
            Q(
                planned_date__lt=today,
                status__in=["SCHEDULED","IN_PROGRESS"]
            )
        ).select_related(
            "monitoring_plan",
            "monitoring_plan__plant",
            "responsible_person",
            "assigned_to",
        ).order_by(
            "planned_date"
        )[:10]

        context["high_risk_exposure_list"] = assessments.filter(
            is_active=True,
            risk_level__in=["HIGH","CRITICAL"]
        ).select_related(
            "sampling",
            "hazard",
            "exposure_group",
            "monitoring_parameter",
            "unit",
            "assessor",
        ).order_by(
            "-assessment_date"
        )[:10]

        context["open_exceedance_list"] = exceedance_actions.filter(
            is_active=True,
            status__in=[
                "OPEN",
                "UNDER_INVESTIGATION",
                "ACTION_IN_PROGRESS",
                "PENDING_VERIFICATION",
            ]
        ).select_related(
            "compliance_record",
            "hazard",
            "exposure_group",
            "responsible_person",
        ).order_by(
            "due_date",
            "-created_at"
        )[:10]

        context["re_monitoring_list"] = re_monitoring.filter(
            is_active=True,
            status__in=["PLANNED","SCHEDULED"],
            planned_date__isnull=False,
            planned_date__lte=thirty_days
        ).select_related(
            "exceedance_action",
            "hazard",
            "exposure_group",
            "monitoring_parameter",
            "unit",
            "conducted_by",
        ).order_by(
            "planned_date"
        )[:10]

        return context



# =============================================
# IndustrialHygieneReportsView - Displays Industrial Hygiene report categories.
# =============================================
class IndustrialHygieneReportsView(LoginRequiredMixin,TemplateView):
    template_name = "industrial_hygiene/reports/industrial_hygiene_reports.html"

    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        context["report_categories"] = [
            {
                "title":"Monitoring Reports",
                "icon":"fa-calendar-check",
                "reports":[
                    {"name":"Monitoring Plan Report","url":reverse("industrial_hygiene:monitoring_plan_list")},
                    {"name":"Monitoring Schedule Report","url":reverse("industrial_hygiene:monitoring_schedule_list")},
                    {"name":"Sampling Report","url":reverse("industrial_hygiene:sampling_management_list")},
                    {"name":"Monitoring Result Report","url":reverse("industrial_hygiene:measurement_entry_list")},
                ],
            },
            {
                "title":"Exposure Reports",
                "icon":"fa-user-shield",
                "reports":[
                    {"name":"Exposure Assessment Report","url":reverse("industrial_hygiene:exposure_assessment_list")},
                    {"name":"Employee Exposure Report","url":reverse("industrial_hygiene:exposure_assessment_list")},
                    {"name":"Exposure Group / SEG Report","url":reverse("industrial_hygiene:exposure_assessment_list")},
                    {"name":"Hazard Exposure Report","url":reverse("industrial_hygiene:exposure_assessment_list")},
                    {"name":"Area Exposure Report","url":reverse("industrial_hygiene:exposure_assessment_list")},
                ],
            },
            {
                "title":"Compliance Reports",
                "icon":"fa-clipboard-check",
                "reports":[
                    {"name":"Compliance Report","url":reverse("industrial_hygiene:compliance_list")},
                    {"name":"Non-Compliant Results Report","url":reverse("industrial_hygiene:compliance_list")},
                    {"name":"Exceedance Report","url":reverse("industrial_hygiene:compliance_list")},
                    {"name":"Overdue Monitoring Report","url":reverse("industrial_hygiene:monitoring_schedule_list")},
                ],
            },
            {
                "title":"Action Reports",
                "icon":"fa-tasks",
                "reports":[
                    {"name":"Exceedance Action Report","url":reverse("industrial_hygiene:exceedance_action_list")},
                    {"name":"Open Action Report","url":reverse("industrial_hygiene:exceedance_action_list")},
                    {"name":"Overdue Action Report","url":reverse("industrial_hygiene:exceedance_action_list")},
                    {"name":"Closed Action Report","url":reverse("industrial_hygiene:exceedance_action_list")},
                    {"name":"Re-Monitoring Report","url":reverse("industrial_hygiene:re_monitoring_list")},
                ],
            },
            {
                "title":"Trend Reports",
                "icon":"fa-chart-line",
                "reports":[
                    {"name":"Monthly Industrial Hygiene Report","url":reverse("industrial_hygiene:reports")},
                    {"name":"Quarterly Industrial Hygiene Report","url":reverse("industrial_hygiene:reports")},
                    {"name":"Annual Industrial Hygiene Report","url":reverse("industrial_hygiene:reports")},
                    {"name":"Hazard-wise Exposure Trend","url":reverse("industrial_hygiene:reports")},
                    {"name":"Department-wise Exposure Trend","url":reverse("industrial_hygiene:reports")},
                    {"name":"Plant-wise Monitoring Report","url":reverse("industrial_hygiene:reports")},
                ],
            },
        ]
        return context

# =============================================
# HazardMasterListView - Displays and searches Hazard Master records.
# =============================================
class HazardMasterListView(LoginRequiredMixin,ListView):
    model = HazardMaster
    template_name = "industrial_hygiene/master/hazard_list.html"
    context_object_name = "hazards"
    paginate_by = 20

    def get_queryset(self):
        # Load the related category efficiently for the Hazard Master list.
        queryset = HazardMaster.objects.select_related("hazard_category").order_by(
            "hazard_category__category_name","hazard"
        )
        search = self.request.GET.get("search","").strip()
        if search:
            # Search hazards using hazard name, category name, or description.
            queryset = queryset.filter(
                Q(hazard__icontains=search)
                | Q(hazard_category__category_name__icontains=search)
                | Q(description__icontains=search)
            )
        return queryset


# =============================================
# HazardMasterCreateView - Creates a new Hazard Master record.
# =============================================
class HazardMasterCreateView(LoginRequiredMixin,CreateView):
    model = HazardMaster
    form_class = HazardMasterForm
    template_name = "industrial_hygiene/master/hazard_form.html"
    success_url = reverse_lazy("industrial_hygiene:hazard_list")

    def form_valid(self,form):
        # Display a success message after creating the Hazard Master record.
        messages.success(self.request,"Hazard created successfully.")
        return super().form_valid(form)


# =============================================
# HazardMasterUpdateView - Updates an existing Hazard Master record.
# =============================================
class HazardMasterUpdateView(LoginRequiredMixin,UpdateView):
    model = HazardMaster
    form_class = HazardMasterForm
    template_name = "industrial_hygiene/master/hazard_form.html"
    success_url = reverse_lazy("industrial_hygiene:hazard_list")

    def form_valid(self,form):
        # Display a success message after updating the Hazard Master record.
        messages.success(self.request,"Hazard updated successfully.")
        return super().form_valid(form)


# =============================================
# HazardMasterDeleteView - Deletes an existing Hazard Master record.
# =============================================
class HazardMasterDeleteView(LoginRequiredMixin,DeleteView):
    model = HazardMaster
    template_name = "industrial_hygiene/master/hazard_confirm_delete.html"
    success_url = reverse_lazy("industrial_hygiene:hazard_list")

    def form_valid(self,form):
        # Display a success message after deleting the Hazard Master record.
        messages.success(self.request,"Hazard deleted successfully.")
        return super().form_valid(form)


# =============================================
# HazardCategoryMasterListView - Displays and searches Hazard Category records.
# =============================================
class HazardCategoryMasterListView(LoginRequiredMixin,ListView):
    model = HazardCategoryMaster
    template_name = "industrial_hygiene/master/hazard_category_list.html"
    context_object_name = "hazard_categories"
    paginate_by = 20

    def get_queryset(self):
        # Load Hazard Categories alphabetically for the master list.
        queryset = HazardCategoryMaster.objects.all().order_by("category_name")
        search = self.request.GET.get("search","").strip()
        if search:
            # Search categories using category name or description.
            queryset = queryset.filter(
                Q(category_name__icontains=search)
                | Q(description__icontains=search)
            )
        return queryset


# =============================================
# HazardCategoryMasterCreateView - Creates a new Hazard Category Master record.
# =============================================
class HazardCategoryMasterCreateView(LoginRequiredMixin,CreateView):
    model = HazardCategoryMaster
    form_class = HazardCategoryMasterForm
    template_name = "industrial_hygiene/master/hazard_category_form.html"
    success_url = reverse_lazy("industrial_hygiene:hazard_category_list")

    def form_valid(self,form):
        # Display a success message after creating the Hazard Category.
        messages.success(self.request,"Hazard Category created successfully.")
        return super().form_valid(form)


# =============================================
# HazardCategoryMasterUpdateView - Updates an existing Hazard Category Master record.
# =============================================
class HazardCategoryMasterUpdateView(LoginRequiredMixin,UpdateView):
    model = HazardCategoryMaster
    form_class = HazardCategoryMasterForm
    template_name = "industrial_hygiene/master/hazard_category_form.html"
    success_url = reverse_lazy("industrial_hygiene:hazard_category_list")

    def form_valid(self,form):
        # Display a success message after updating the Hazard Category.
        messages.success(self.request,"Hazard Category updated successfully.")
        return super().form_valid(form)


# =============================================
# HazardCategoryMasterDeleteView - Deletes an existing Hazard Category Master record.
# =============================================
class HazardCategoryMasterDeleteView(LoginRequiredMixin,DeleteView):
    model = HazardCategoryMaster
    template_name = "industrial_hygiene/master/hazard_category_confirm_delete.html"
    success_url = reverse_lazy("industrial_hygiene:hazard_category_list")

    def form_valid(self,form):
        # Display a success message after deleting the Hazard Category.
        messages.success(self.request,"Hazard Category deleted successfully.")
        return super().form_valid(form)


# =============================================
# ExposureTypeMasterListView - Displays and searches Exposure Type records.
# =============================================
class ExposureTypeMasterListView(LoginRequiredMixin,ListView):
    model = ExposureTypeMaster
    template_name = "industrial_hygiene/master/exposure_type_list.html"
    context_object_name = "exposure_types"
    paginate_by = 20

    def get_queryset(self):
        # Load Exposure Types alphabetically for the master list.
        queryset = ExposureTypeMaster.objects.all().order_by("exposure_type")
        search = self.request.GET.get("search","").strip()
        if search:
            # Search exposure types using name or description.
            queryset = queryset.filter(
                Q(exposure_type__icontains=search)
                | Q(description__icontains=search)
            )
        return queryset


# =============================================
# ExposureTypeMasterCreateView - Creates a new Exposure Type Master record.
# =============================================
class ExposureTypeMasterCreateView(LoginRequiredMixin,CreateView):
    model = ExposureTypeMaster
    form_class = ExposureTypeMasterForm
    template_name = "industrial_hygiene/master/exposure_type_form.html"
    success_url = reverse_lazy("industrial_hygiene:exposure_type_list")

    def form_valid(self,form):
        # Display a success message after creating the Exposure Type.
        messages.success(self.request,"Exposure Type created successfully.")
        return super().form_valid(form)


# =============================================
# ExposureTypeMasterUpdateView - Updates an existing Exposure Type Master record.
# =============================================
class ExposureTypeMasterUpdateView(LoginRequiredMixin,UpdateView):
    model = ExposureTypeMaster
    form_class = ExposureTypeMasterForm
    template_name = "industrial_hygiene/master/exposure_type_form.html"
    success_url = reverse_lazy("industrial_hygiene:exposure_type_list")

    def form_valid(self,form):
        # Display a success message after updating the Exposure Type.
        messages.success(self.request,"Exposure Type updated successfully.")
        return super().form_valid(form)


# =============================================
# ExposureTypeMasterDeleteView - Deletes an existing Exposure Type Master record.
# =============================================
class ExposureTypeMasterDeleteView(LoginRequiredMixin,DeleteView):
    model = ExposureTypeMaster
    template_name = "industrial_hygiene/master/exposure_type_confirm_delete.html"
    success_url = reverse_lazy("industrial_hygiene:exposure_type_list")

    def form_valid(self,form):
        # Display a success message after deleting the Exposure Type.
        messages.success(self.request,"Exposure Type deleted successfully.")
        return super().form_valid(form)



# =============================================
# ExposureGroupMasterListView - Displays and searches Exposure Group / SEG records.
# =============================================
class ExposureGroupMasterListView(LoginRequiredMixin,ListView):
    model = ExposureGroupMaster
    template_name = "industrial_hygiene/master/exposure_group_list.html"
    context_object_name = "exposure_groups"
    paginate_by = 20

    def get_queryset(self):
        queryset = ExposureGroupMaster.objects.all().order_by("exposure_group")
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(exposure_group__icontains=search)
                | Q(description__icontains=search)
            )
        return queryset


# =============================================
# ExposureGroupMasterCreateView - Creates a new Exposure Group / SEG record.
# =============================================
class ExposureGroupMasterCreateView(LoginRequiredMixin,CreateView):
    model = ExposureGroupMaster
    form_class = ExposureGroupMasterForm
    template_name = "industrial_hygiene/master/exposure_group_form.html"
    success_url = reverse_lazy("industrial_hygiene:exposure_group_list")

    def form_valid(self,form):
        messages.success(self.request,"Exposure Group created successfully.")
        return super().form_valid(form)


# =============================================
# ExposureGroupMasterUpdateView - Updates an existing Exposure Group / SEG record.
# =============================================
class ExposureGroupMasterUpdateView(LoginRequiredMixin,UpdateView):
    model = ExposureGroupMaster
    form_class = ExposureGroupMasterForm
    template_name = "industrial_hygiene/master/exposure_group_form.html"
    success_url = reverse_lazy("industrial_hygiene:exposure_group_list")

    def form_valid(self,form):
        messages.success(self.request,"Exposure Group updated successfully.")
        return super().form_valid(form)


# =============================================
# ExposureGroupMasterDeleteView - Deletes an existing Exposure Group / SEG record.
# =============================================
class ExposureGroupMasterDeleteView(LoginRequiredMixin,DeleteView):
    model = ExposureGroupMaster
    template_name = "industrial_hygiene/master/exposure_group_confirm_delete.html"
    success_url = reverse_lazy("industrial_hygiene:exposure_group_list")

    def form_valid(self,form):
        messages.success(self.request,"Exposure Group deleted successfully.")
        return super().form_valid(form)



# =============================================
# MonitoringTypeMasterListView - Displays and searches Monitoring Type Master records.
# =============================================
class MonitoringTypeMasterListView(LoginRequiredMixin,ListView):
    model = MonitoringTypeMaster
    template_name = "industrial_hygiene/master/monitoring_type_list.html"
    context_object_name = "monitoring_types"
    paginate_by = 20

    def get_queryset(self):
        queryset = MonitoringTypeMaster.objects.all().order_by("monitoring_type")
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(monitoring_type__icontains=search)
                | Q(description__icontains=search)
            )
        return queryset


# =============================================
# MonitoringTypeMasterCreateView - Creates a new Monitoring Type Master record.
# =============================================
class MonitoringTypeMasterCreateView(LoginRequiredMixin,CreateView):
    model = MonitoringTypeMaster
    form_class = MonitoringTypeMasterForm
    template_name = "industrial_hygiene/master/monitoring_type_form.html"
    success_url = reverse_lazy("industrial_hygiene:monitoring_type_list")

    def form_valid(self,form):
        messages.success(self.request,"Monitoring Type created successfully.")
        return super().form_valid(form)


# =============================================
# MonitoringTypeMasterUpdateView - Updates an existing Monitoring Type Master record.
# =============================================
class MonitoringTypeMasterUpdateView(LoginRequiredMixin,UpdateView):
    model = MonitoringTypeMaster
    form_class = MonitoringTypeMasterForm
    template_name = "industrial_hygiene/master/monitoring_type_form.html"
    success_url = reverse_lazy("industrial_hygiene:monitoring_type_list")

    def form_valid(self,form):
        messages.success(self.request,"Monitoring Type updated successfully.")
        return super().form_valid(form)


# =============================================
# MonitoringTypeMasterDeleteView - Deletes an existing Monitoring Type Master record.
# =============================================
class MonitoringTypeMasterDeleteView(LoginRequiredMixin,DeleteView):
    model = MonitoringTypeMaster
    template_name = "industrial_hygiene/master/monitoring_type_confirm_delete.html"
    success_url = reverse_lazy("industrial_hygiene:monitoring_type_list")

    def form_valid(self,form):
        messages.success(self.request,"Monitoring Type deleted successfully.")
        return super().form_valid(form)




# =============================================
# MonitoringParameterMasterListView - Displays and searches Monitoring Parameter Master records.
# =============================================
class MonitoringParameterMasterListView(LoginRequiredMixin,ListView):
    model = MonitoringParameterMaster
    template_name = "industrial_hygiene/master/monitoring_parameter_list.html"
    context_object_name = "monitoring_parameters"
    paginate_by = 20

    def get_queryset(self):
        queryset = MonitoringParameterMaster.objects.all().order_by("parameter_name")
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(parameter_name__icontains=search)
                | Q(description__icontains=search)
            )
        return queryset


# =============================================
# MonitoringParameterMasterCreateView - Creates a new Monitoring Parameter Master record.
# =============================================
class MonitoringParameterMasterCreateView(LoginRequiredMixin,CreateView):
    model = MonitoringParameterMaster
    form_class = MonitoringParameterMasterForm
    template_name = "industrial_hygiene/master/monitoring_parameter_form.html"
    success_url = reverse_lazy("industrial_hygiene:monitoring_parameter_list")

    def form_valid(self,form):
        messages.success(self.request,"Monitoring Parameter created successfully.")
        return super().form_valid(form)


# =============================================
# MonitoringParameterMasterUpdateView - Updates an existing Monitoring Parameter Master record.
# =============================================
class MonitoringParameterMasterUpdateView(LoginRequiredMixin,UpdateView):
    model = MonitoringParameterMaster
    form_class = MonitoringParameterMasterForm
    template_name = "industrial_hygiene/master/monitoring_parameter_form.html"
    success_url = reverse_lazy("industrial_hygiene:monitoring_parameter_list")

    def form_valid(self,form):
        messages.success(self.request,"Monitoring Parameter updated successfully.")
        return super().form_valid(form)


# =============================================
# MonitoringParameterMasterDeleteView - Deletes an existing Monitoring Parameter Master record.
# =============================================
class MonitoringParameterMasterDeleteView(LoginRequiredMixin,DeleteView):
    model = MonitoringParameterMaster
    template_name = "industrial_hygiene/master/monitoring_parameter_confirm_delete.html"
    success_url = reverse_lazy("industrial_hygiene:monitoring_parameter_list")

    def form_valid(self,form):
        messages.success(self.request,"Monitoring Parameter deleted successfully.")
        return super().form_valid(form)




# =============================================
# UnitMasterListView - Displays and searches Unit Master records.
# =============================================
class UnitMasterListView(LoginRequiredMixin,ListView):
    model = UnitMaster
    template_name = "industrial_hygiene/master/unit_list.html"
    context_object_name = "units"
    paginate_by = 20

    def get_queryset(self):
        queryset = UnitMaster.objects.all().order_by("unit_name")
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(unit_name__icontains=search)
                | Q(unit_symbol__icontains=search)
                | Q(description__icontains=search)
            )
        return queryset


# =============================================
# UnitMasterCreateView - Creates a new Unit Master record.
# =============================================
class UnitMasterCreateView(LoginRequiredMixin,CreateView):
    model = UnitMaster
    form_class = UnitMasterForm
    template_name = "industrial_hygiene/master/unit_form.html"
    success_url = reverse_lazy("industrial_hygiene:unit_list")

    def form_valid(self,form):
        messages.success(self.request,"Unit created successfully.")
        return super().form_valid(form)


# =============================================
# UnitMasterUpdateView - Updates an existing Unit Master record.
# =============================================
class UnitMasterUpdateView(LoginRequiredMixin,UpdateView):
    model = UnitMaster
    form_class = UnitMasterForm
    template_name = "industrial_hygiene/master/unit_form.html"
    success_url = reverse_lazy("industrial_hygiene:unit_list")

    def form_valid(self,form):
        messages.success(self.request,"Unit updated successfully.")
        return super().form_valid(form)


# =============================================
# UnitMasterDeleteView - Deletes an existing Unit Master record.
# =============================================
class UnitMasterDeleteView(LoginRequiredMixin,DeleteView):
    model = UnitMaster
    template_name = "industrial_hygiene/master/unit_confirm_delete.html"
    success_url = reverse_lazy("industrial_hygiene:unit_list")

    def form_valid(self,form):
        messages.success(self.request,"Unit deleted successfully.")
        return super().form_valid(form)




# =============================================
# ExposureLimitMasterListView - Displays and searches Exposure Limit / OEL Master records.
# =============================================
class ExposureLimitMasterListView(LoginRequiredMixin,ListView):
    model = ExposureLimitMaster
    template_name = "industrial_hygiene/master/exposure_limit_list.html"
    context_object_name = "exposure_limits"
    paginate_by = 20

    def get_queryset(self):
        queryset = ExposureLimitMaster.objects.select_related(
            "hazard",
            "monitoring_parameter",
            "unit"
        ).all().order_by(
            "hazard__hazard",
            "monitoring_parameter__parameter_name"
        )
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(hazard__hazard__icontains=search)
                | Q(monitoring_parameter__parameter_name__icontains=search)
                | Q(unit__unit_name__icontains=search)
                | Q(unit__unit_symbol__icontains=search)
                | Q(exposure_limit_type__icontains=search)
                | Q(applicable_standard__icontains=search)
                | Q(source_reference__icontains=search)
            )
        return queryset


# =============================================
# ExposureLimitMasterCreateView - Creates a new Exposure Limit / OEL Master record.
# =============================================
class ExposureLimitMasterCreateView(LoginRequiredMixin,CreateView):
    model = ExposureLimitMaster
    form_class = ExposureLimitMasterForm
    template_name = "industrial_hygiene/master/exposure_limit_form.html"
    success_url = reverse_lazy("industrial_hygiene:exposure_limit_list")

    def form_valid(self,form):
        messages.success(self.request,"Exposure Limit created successfully.")
        return super().form_valid(form)


# =============================================
# ExposureLimitMasterUpdateView - Updates an existing Exposure Limit / OEL Master record.
# =============================================
class ExposureLimitMasterUpdateView(LoginRequiredMixin,UpdateView):
    model = ExposureLimitMaster
    form_class = ExposureLimitMasterForm
    template_name = "industrial_hygiene/master/exposure_limit_form.html"
    success_url = reverse_lazy("industrial_hygiene:exposure_limit_list")

    def form_valid(self,form):
        messages.success(self.request,"Exposure Limit updated successfully.")
        return super().form_valid(form)


# =============================================
# ExposureLimitMasterDeleteView - Deletes an existing Exposure Limit / OEL Master record.
# =============================================
class ExposureLimitMasterDeleteView(LoginRequiredMixin,DeleteView):
    model = ExposureLimitMaster
    template_name = "industrial_hygiene/master/exposure_limit_confirm_delete.html"
    success_url = reverse_lazy("industrial_hygiene:exposure_limit_list")

    def form_valid(self,form):
        messages.success(self.request,"Exposure Limit deleted successfully.")
        return super().form_valid(form)




# =============================================
# InstrumentMasterListView - Displays and searches Industrial Hygiene instruments.
# =============================================
class InstrumentMasterListView(LoginRequiredMixin,ListView):
    model = InstrumentMaster
    template_name = "industrial_hygiene/master/instrument_list.html"
    context_object_name = "instruments"
    paginate_by = 20

    def get_queryset(self):
        queryset = InstrumentMaster.objects.select_related(
            "measurement_parameter"
        ).all().order_by("instrument_name")

        search = self.request.GET.get("search","").strip()

        if search:
            queryset = queryset.filter(
                Q(instrument_name__icontains=search)
                | Q(instrument_code__icontains=search)
                | Q(instrument_type__icontains=search)
                | Q(manufacturer__icontains=search)
                | Q(model_number__icontains=search)
                | Q(serial_number__icontains=search)
                | Q(measurement_parameter__parameter_name__icontains=search)
                | Q(calibration_frequency__icontains=search)
                | Q(description__icontains=search)
            )

        return queryset


# =============================================
# InstrumentMasterCreateView - Creates a new Industrial Hygiene instrument.
# =============================================
class InstrumentMasterCreateView(LoginRequiredMixin,CreateView):
    model = InstrumentMaster
    form_class = InstrumentMasterForm
    template_name = "industrial_hygiene/master/instrument_form.html"
    success_url = reverse_lazy("industrial_hygiene:instrument_list")

    def form_valid(self,form):
        messages.success(self.request,"Instrument created successfully.")
        return super().form_valid(form)


# =============================================
# InstrumentMasterUpdateView - Updates an existing Industrial Hygiene instrument.
# =============================================
class InstrumentMasterUpdateView(LoginRequiredMixin,UpdateView):
    model = InstrumentMaster
    form_class = InstrumentMasterForm
    template_name = "industrial_hygiene/master/instrument_form.html"
    success_url = reverse_lazy("industrial_hygiene:instrument_list")

    def form_valid(self,form):
        messages.success(self.request,"Instrument updated successfully.")
        return super().form_valid(form)


# =============================================
# InstrumentMasterDeleteView - Deletes an existing Industrial Hygiene instrument.
# =============================================
class InstrumentMasterDeleteView(LoginRequiredMixin,DeleteView):
    model = InstrumentMaster
    template_name = "industrial_hygiene/master/instrument_confirm_delete.html"
    success_url = reverse_lazy("industrial_hygiene:instrument_list")

    def form_valid(self,form):
        messages.success(self.request,"Instrument deleted successfully.")
        return super().form_valid(form)





# =============================================
# LaboratoryMasterListView - Displays and searches Industrial Hygiene laboratory records.
# =============================================
class LaboratoryMasterListView(LoginRequiredMixin,ListView):
    model = LaboratoryMaster
    template_name = "industrial_hygiene/master/laboratory_list.html"
    context_object_name = "laboratories"
    paginate_by = 20

    def get_queryset(self):
        queryset = LaboratoryMaster.objects.all().order_by("laboratory_name")

        search = self.request.GET.get("search","").strip()

        if search:
            queryset = queryset.filter(
                Q(laboratory_name__icontains=search)
                | Q(laboratory_code__icontains=search)
                | Q(accreditation__icontains=search)
                | Q(contact_person__icontains=search)
                | Q(contact_number__icontains=search)
                | Q(email__icontains=search)
                | Q(address__icontains=search)
                | Q(description__icontains=search)
            )

        return queryset


# =============================================
# LaboratoryMasterCreateView - Creates a new Industrial Hygiene laboratory.
# =============================================
class LaboratoryMasterCreateView(LoginRequiredMixin,CreateView):
    model = LaboratoryMaster
    form_class = LaboratoryMasterForm
    template_name = "industrial_hygiene/master/laboratory_form.html"
    success_url = reverse_lazy("industrial_hygiene:laboratory_list")

    def form_valid(self,form):
        messages.success(self.request,"Laboratory created successfully.")
        return super().form_valid(form)


# =============================================
# LaboratoryMasterUpdateView - Updates an existing Industrial Hygiene laboratory.
# =============================================
class LaboratoryMasterUpdateView(LoginRequiredMixin,UpdateView):
    model = LaboratoryMaster
    form_class = LaboratoryMasterForm
    template_name = "industrial_hygiene/master/laboratory_form.html"
    success_url = reverse_lazy("industrial_hygiene:laboratory_list")

    def form_valid(self,form):
        messages.success(self.request,"Laboratory updated successfully.")
        return super().form_valid(form)


# =============================================
# LaboratoryMasterDeleteView - Deletes an existing Industrial Hygiene laboratory.
# =============================================
class LaboratoryMasterDeleteView(LoginRequiredMixin,DeleteView):
    model = LaboratoryMaster
    template_name = "industrial_hygiene/master/laboratory_confirm_delete.html"
    success_url = reverse_lazy("industrial_hygiene:laboratory_list")

    def form_valid(self,form):
        messages.success(self.request,"Laboratory deleted successfully.")
        return super().form_valid(form)




# =============================================
# IHProgramMasterListView - Displays and searches Industrial Hygiene programs.
# =============================================
class IHProgramMasterListView(LoginRequiredMixin,ListView):
    model = IHProgramMaster
    template_name = "industrial_hygiene/program/ih_program_list.html"
    context_object_name = "programs"
    paginate_by = 20

    def get_queryset(self):
        queryset = IHProgramMaster.objects.select_related(
            "plant",
            "responsible_person"
        ).all().order_by("program_name")

        search = self.request.GET.get("search","").strip()

        if search:
            queryset = queryset.filter(
                Q(program_name__icontains=search)
                | Q(program_code__icontains=search)
                | Q(plant__name__icontains=search)
                | Q(description__icontains=search)
                | Q(objectives__icontains=search)
                | Q(scope__icontains=search)
                | Q(review_frequency__icontains=search)
                | Q(status__icontains=search)
            )

        return queryset


# =============================================
# IHProgramMasterCreateView - Creates a new Industrial Hygiene program.
# =============================================
class IHProgramMasterCreateView(LoginRequiredMixin,CreateView):
    model = IHProgramMaster
    form_class = IHProgramMasterForm
    template_name = "industrial_hygiene/program/ih_program_form.html"
    success_url = reverse_lazy("industrial_hygiene:ih_program_list")

    def form_valid(self,form):
        messages.success(
            self.request,
            "Industrial Hygiene program created successfully."
        )
        return super().form_valid(form)


# =============================================
# IHProgramMasterUpdateView - Updates an existing Industrial Hygiene program.
# =============================================
class IHProgramMasterUpdateView(LoginRequiredMixin,UpdateView):
    model = IHProgramMaster
    form_class = IHProgramMasterForm
    template_name = "industrial_hygiene/program/ih_program_form.html"
    success_url = reverse_lazy("industrial_hygiene:ih_program_list")

    def form_valid(self,form):
        messages.success(
            self.request,
            "Industrial Hygiene program updated successfully."
        )
        return super().form_valid(form)


# =============================================
# IHProgramMasterDetailView - Displays Industrial Hygiene program details.
# =============================================
class IHProgramMasterDetailView(LoginRequiredMixin,DetailView):
    model = IHProgramMaster
    template_name = "industrial_hygiene/program/ih_program_detail.html"




# =============================================
# MonitoringPlanListView - Displays and searches Industrial Hygiene monitoring plans.
# =============================================
class MonitoringPlanListView(LoginRequiredMixin,ListView):
    model = MonitoringPlan
    template_name = "industrial_hygiene/monitoring_plan/monitoring_plan_list.html"
    context_object_name = "monitoring_plans"
    paginate_by = 20

    def get_queryset(self):
        queryset = MonitoringPlan.objects.select_related(
            "ih_program",
            "plant",
            "hazard",
            "hazard__hazard_category",
            "exposure_type",
            "exposure_group",
            "monitoring_type",
            "monitoring_parameter",
            "unit",
            "exposure_limit",
            "responsible_person"
        ).all().order_by("plan_name")
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(plan_name__icontains=search)
                | Q(plan_code__icontains=search)
                | Q(ih_program__program_name__icontains=search)
                | Q(plant__name__icontains=search)
                | Q(hazard__hazard__icontains=search)
                | Q(exposure_type__exposure_type__icontains=search)
                | Q(exposure_group__exposure_group__icontains=search)
                | Q(monitoring_type__monitoring_type__icontains=search)
                | Q(monitoring_parameter__parameter_name__icontains=search)
                | Q(area_or_location__icontains=search)
                | Q(department__icontains=search)
                | Q(status__icontains=search)
            )
        return queryset

# =============================================
# MonitoringPlanCreateView - Creates a new Industrial Hygiene monitoring plan.
# =============================================
class MonitoringPlanCreateView(LoginRequiredMixin,CreateView):
    model = MonitoringPlan
    form_class = MonitoringPlanForm
    template_name = "industrial_hygiene/monitoring_plan/monitoring_plan_form.html"
    success_url = reverse_lazy("industrial_hygiene:monitoring_plan_list")

    def form_valid(self,form):
        messages.success(
            self.request,
            "Monitoring plan created successfully."
        )
        return super().form_valid(form)

# =============================================
# MonitoringPlanUpdateView - Updates an existing Industrial Hygiene monitoring plan.
# =============================================
class MonitoringPlanUpdateView(LoginRequiredMixin,UpdateView):
    model = MonitoringPlan
    form_class = MonitoringPlanForm
    template_name = "industrial_hygiene/monitoring_plan/monitoring_plan_form.html"
    success_url = reverse_lazy("industrial_hygiene:monitoring_plan_list")

    def form_valid(self,form):
        messages.success(
            self.request,
            "Monitoring plan updated successfully."
        )
        return super().form_valid(form)

# =============================================
# MonitoringPlanDetailView - Displays Industrial Hygiene monitoring plan details.
# =============================================
class MonitoringPlanDetailView(LoginRequiredMixin,DetailView):
    model = MonitoringPlan
    template_name = "industrial_hygiene/monitoring_plan/monitoring_plan_detail.html"






# =============================================
# MonitoringScheduleListView - Displays and searches Industrial Hygiene monitoring schedules.
# =============================================
class MonitoringScheduleListView(LoginRequiredMixin,ListView):
    model = MonitoringSchedule
    template_name = "industrial_hygiene/monitoring_schedule/monitoring_schedule_list.html"
    context_object_name = "monitoring_schedules"
    paginate_by = 20

    def get_queryset(self):
        queryset = MonitoringSchedule.objects.select_related(
            "monitoring_plan",
            "monitoring_plan__ih_program",
            "monitoring_plan__plant",
            "monitoring_plan__hazard",
            "monitoring_plan__exposure_type",
            "monitoring_plan__exposure_group",
            "monitoring_plan__monitoring_type",
            "monitoring_plan__monitoring_parameter",
            "monitoring_plan__unit",
            "responsible_person",
            "assigned_to"
        ).all().order_by("planned_date","schedule_name")
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(schedule_name__icontains=search)
                | Q(schedule_code__icontains=search)
                | Q(monitoring_plan__plan_name__icontains=search)
                | Q(monitoring_plan__plan_code__icontains=search)
                | Q(monitoring_plan__ih_program__program_name__icontains=search)
                | Q(monitoring_plan__plant__name__icontains=search)
                | Q(monitoring_plan__hazard__hazard__icontains=search)
                | Q(monitoring_plan__exposure_type__exposure_type__icontains=search)
                | Q(monitoring_plan__exposure_group__exposure_group__icontains=search)
                | Q(monitoring_plan__monitoring_type__monitoring_type__icontains=search)
                | Q(monitoring_plan__monitoring_parameter__parameter_name__icontains=search)
                | Q(status__icontains=search)
            )
        return queryset

# =============================================
# MonitoringScheduleCreateView - Creates a new Industrial Hygiene monitoring schedule.
# =============================================
class MonitoringScheduleCreateView(LoginRequiredMixin,CreateView):
    model = MonitoringSchedule
    form_class = MonitoringScheduleForm
    template_name = "industrial_hygiene/monitoring_schedule/monitoring_schedule_form.html"
    success_url = reverse_lazy("industrial_hygiene:monitoring_schedule_list")

    def form_valid(self,form):
        messages.success(
            self.request,
            "Monitoring schedule created successfully."
        )
        return super().form_valid(form)

# =============================================
# MonitoringScheduleUpdateView - Updates an existing Industrial Hygiene monitoring schedule.
# =============================================
class MonitoringScheduleUpdateView(LoginRequiredMixin,UpdateView):
    model = MonitoringSchedule
    form_class = MonitoringScheduleForm
    template_name = "industrial_hygiene/monitoring_schedule/monitoring_schedule_form.html"
    success_url = reverse_lazy("industrial_hygiene:monitoring_schedule_list")

    def form_valid(self,form):
        messages.success(
            self.request,
            "Monitoring schedule updated successfully."
        )
        return super().form_valid(form)

# =============================================
# MonitoringScheduleDetailView - Displays Industrial Hygiene monitoring schedule details.
# =============================================
class MonitoringScheduleDetailView(LoginRequiredMixin,DetailView):
    model = MonitoringSchedule
    template_name = "industrial_hygiene/monitoring_schedule/monitoring_schedule_detail.html"






# =============================================
# SamplingManagementListView - Displays and searches Industrial Hygiene sampling records.
# =============================================
class SamplingManagementListView(LoginRequiredMixin,ListView):
    model = SamplingManagement
    template_name = "industrial_hygiene/sampling_management/sampling_management_list.html"
    context_object_name = "sampling_records"
    paginate_by = 20
    def get_queryset(self):
        queryset = SamplingManagement.objects.select_related(
            "monitoring_schedule",
            "monitoring_schedule__monitoring_plan",
            "monitoring_schedule__monitoring_plan__ih_program",
            "monitoring_schedule__monitoring_plan__plant",
            "hazard",
            "hazard__hazard_category",
            "exposure_type",
            "exposure_group",
            "monitoring_parameter",
            "unit",
            "instrument",
            "laboratory",
            "collected_by"
        ).all().order_by("-sampling_date","sampling_code")
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(sampling_code__icontains=search)
                | Q(sample_number__icontains=search)
                | Q(monitoring_schedule__schedule_name__icontains=search)
                | Q(monitoring_schedule__schedule_code__icontains=search)
                | Q(monitoring_schedule__monitoring_plan__plan_name__icontains=search)
                | Q(monitoring_schedule__monitoring_plan__plant__name__icontains=search)
                | Q(hazard__hazard__icontains=search)
                | Q(exposure_type__exposure_type__icontains=search)
                | Q(exposure_group__exposure_group__icontains=search)
                | Q(area_or_location__icontains=search)
                | Q(department__icontains=search)
                | Q(monitoring_parameter__parameter_name__icontains=search)
                | Q(laboratory__laboratory_name__icontains=search)
                | Q(laboratory_reference__icontains=search)
                | Q(status__icontains=search)
            )
        return queryset

# =============================================
# SamplingManagementCreateView - Creates a new Industrial Hygiene sampling record.
# =============================================
class SamplingManagementCreateView(LoginRequiredMixin,CreateView):
    model = SamplingManagement
    form_class = SamplingManagementForm
    template_name = "industrial_hygiene/sampling_management/sampling_management_form.html"
    success_url = reverse_lazy("industrial_hygiene:sampling_management_list")
    def form_valid(self,form):
        messages.success(self.request,"Sampling record created successfully.")
        return super().form_valid(form)

# =============================================
# SamplingManagementUpdateView - Updates an existing Industrial Hygiene sampling record.
# =============================================
class SamplingManagementUpdateView(LoginRequiredMixin,UpdateView):
    model = SamplingManagement
    form_class = SamplingManagementForm
    template_name = "industrial_hygiene/sampling_management/sampling_management_form.html"
    success_url = reverse_lazy("industrial_hygiene:sampling_management_list")
    def form_valid(self,form):
        messages.success(self.request,"Sampling record updated successfully.")
        return super().form_valid(form)

# =============================================
# SamplingManagementDetailView - Displays Industrial Hygiene sampling record details.
# =============================================
class SamplingManagementDetailView(LoginRequiredMixin,DetailView):
    model = SamplingManagement
    template_name = "industrial_hygiene/sampling_management/sampling_management_detail.html"
    context_object_name = "sampling"





# =============================================
# MeasurementEntryListView - Displays and searches Industrial Hygiene measurement entries.
# =============================================
class MeasurementEntryListView(LoginRequiredMixin,ListView):
    model = MeasurementEntry
    template_name = "industrial_hygiene/measurement_entry/measurement_entry_list.html"
    context_object_name = "measurement_entries"
    paginate_by = 20
    def get_queryset(self):
        queryset = MeasurementEntry.objects.select_related(
            "sampling",
            "sampling__monitoring_schedule",
            "sampling__monitoring_schedule__monitoring_plan",
            "sampling__monitoring_schedule__monitoring_plan__ih_program",
            "sampling__monitoring_schedule__monitoring_plan__plant",
            "sampling__hazard",
            "sampling__exposure_type",
            "sampling__exposure_group",
            "sampling__monitoring_parameter",
            "sampling__unit",
            "monitoring_parameter",
            "unit",
            "entered_by",
            "verified_by"
        ).all().order_by("-measurement_date","measurement_code")
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(measurement_code__icontains=search)
                | Q(sampling__sampling_code__icontains=search)
                | Q(sampling__sample_number__icontains=search)
                | Q(sampling__monitoring_schedule__schedule_name__icontains=search)
                | Q(sampling__monitoring_schedule__schedule_code__icontains=search)
                | Q(sampling__monitoring_schedule__monitoring_plan__plan_name__icontains=search)
                | Q(sampling__monitoring_schedule__monitoring_plan__plant__name__icontains=search)
                | Q(sampling__hazard__hazard__icontains=search)
                | Q(sampling__exposure_type__exposure_type__icontains=search)
                | Q(sampling__exposure_group__exposure_group__icontains=search)
                | Q(monitoring_parameter__parameter_name__icontains=search)
                | Q(unit__unit_name__icontains=search)
                | Q(status__icontains=search)
            )
        return queryset

# =============================================
# MeasurementEntryCreateView - Creates a new Industrial Hygiene measurement entry.
# =============================================
class MeasurementEntryCreateView(LoginRequiredMixin,CreateView):
    model = MeasurementEntry
    form_class = MeasurementEntryForm
    template_name = "industrial_hygiene/measurement_entry/measurement_entry_form.html"
    success_url = reverse_lazy("industrial_hygiene:measurement_entry_list")
    def form_valid(self,form):
        messages.success(self.request,"Measurement entry created successfully.")
        return super().form_valid(form)

# =============================================
# MeasurementEntryUpdateView - Updates an existing Industrial Hygiene measurement entry.
# =============================================
class MeasurementEntryUpdateView(LoginRequiredMixin,UpdateView):
    model = MeasurementEntry
    form_class = MeasurementEntryForm
    template_name = "industrial_hygiene/measurement_entry/measurement_entry_form.html"
    success_url = reverse_lazy("industrial_hygiene:measurement_entry_list")
    def form_valid(self,form):
        messages.success(self.request,"Measurement entry updated successfully.")
        return super().form_valid(form)

# =============================================
# MeasurementEntryDetailView - Displays Industrial Hygiene measurement entry details.
# =============================================
class MeasurementEntryDetailView(LoginRequiredMixin,DetailView):
    model = MeasurementEntry
    template_name = "industrial_hygiene/measurement_entry/measurement_entry_detail.html"
    context_object_name = "measurement"





# =============================================
# LaboratoryResultListView - Displays and searches Industrial Hygiene laboratory results.
# =============================================
class LaboratoryResultListView(LoginRequiredMixin,ListView):
    model = LaboratoryResult
    template_name = "industrial_hygiene/laboratory_result/laboratory_result_list.html"
    context_object_name = "laboratory_results"
    paginate_by = 20
    def get_queryset(self):
        queryset = LaboratoryResult.objects.select_related(
            "sampling",
            "sampling__monitoring_schedule",
            "sampling__monitoring_schedule__monitoring_plan",
            "sampling__monitoring_schedule__monitoring_plan__ih_program",
            "sampling__monitoring_schedule__monitoring_plan__plant",
            "sampling__hazard",
            "sampling__exposure_type",
            "sampling__exposure_group",
            "sampling__monitoring_parameter",
            "sampling__unit",
            "laboratory",
            "measurement",
            "monitoring_parameter",
            "unit",
            "received_by",
            "verified_by"
        ).all().order_by("-result_date","result_code")
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(result_code__icontains=search)
                | Q(laboratory_reference__icontains=search)
                | Q(certificate_number__icontains=search)
                | Q(sampling__sampling_code__icontains=search)
                | Q(sampling__sample_number__icontains=search)
                | Q(sampling__monitoring_schedule__schedule_name__icontains=search)
                | Q(sampling__monitoring_schedule__schedule_code__icontains=search)
                | Q(sampling__monitoring_schedule__monitoring_plan__plan_name__icontains=search)
                | Q(sampling__monitoring_schedule__monitoring_plan__plant__name__icontains=search)
                | Q(sampling__hazard__hazard__icontains=search)
                | Q(laboratory__laboratory_name__icontains=search)
                | Q(laboratory__laboratory_code__icontains=search)
                | Q(monitoring_parameter__parameter_name__icontains=search)
                | Q(unit__unit_name__icontains=search)
                | Q(status__icontains=search)
            )
        return queryset

# =============================================
# LaboratoryResultCreateView - Creates a new Industrial Hygiene laboratory result.
# =============================================
class LaboratoryResultCreateView(LoginRequiredMixin,CreateView):
    model = LaboratoryResult
    form_class = LaboratoryResultForm
    template_name = "industrial_hygiene/laboratory_result/laboratory_result_form.html"
    success_url = reverse_lazy("industrial_hygiene:laboratory_result_list")
    def form_valid(self,form):
        messages.success(self.request,"Laboratory result created successfully.")
        return super().form_valid(form)

# =============================================
# LaboratoryResultUpdateView - Updates an existing Industrial Hygiene laboratory result.
# =============================================
class LaboratoryResultUpdateView(LoginRequiredMixin,UpdateView):
    model = LaboratoryResult
    form_class = LaboratoryResultForm
    template_name = "industrial_hygiene/laboratory_result/laboratory_result_form.html"
    success_url = reverse_lazy("industrial_hygiene:laboratory_result_list")
    def form_valid(self,form):
        messages.success(self.request,"Laboratory result updated successfully.")
        return super().form_valid(form)

# =============================================
# LaboratoryResultDetailView - Displays Industrial Hygiene laboratory result details.
# =============================================
class LaboratoryResultDetailView(LoginRequiredMixin,DetailView):
    model = LaboratoryResult
    template_name = "industrial_hygiene/laboratory_result/laboratory_result_detail.html"
    context_object_name = "laboratory_result"





# =============================================
# ExposureAssessmentListView - Displays and searches Industrial Hygiene exposure assessments.
# =============================================
class ExposureAssessmentListView(LoginRequiredMixin,ListView):
    model = ExposureAssessment
    template_name = "industrial_hygiene/exposure_assessment/exposure_assessment_list.html"
    context_object_name = "exposure_assessments"
    paginate_by = 20
    def get_queryset(self):
        queryset = ExposureAssessment.objects.select_related(
            "sampling",
            "sampling__monitoring_schedule",
            "sampling__monitoring_schedule__monitoring_plan",
            "sampling__monitoring_schedule__monitoring_plan__ih_program",
            "sampling__monitoring_schedule__monitoring_plan__plant",
            "sampling__hazard",
            "sampling__exposure_type",
            "sampling__exposure_group",
            "sampling__monitoring_parameter",
            "sampling__unit",
            "measurement",
            "laboratory_result",
            "hazard",
            "exposure_type",
            "exposure_group",
            "monitoring_parameter",
            "unit",
            "applicable_oel",
            "applicable_oel__hazard",
            "applicable_oel__monitoring_parameter",
            "applicable_oel__unit",
            "assessor"
        ).all().order_by("-assessment_date","assessment_code")
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(assessment_code__icontains=search)
                | Q(sampling__sampling_code__icontains=search)
                | Q(sampling__sample_number__icontains=search)
                | Q(sampling__monitoring_schedule__schedule_name__icontains=search)
                | Q(sampling__monitoring_schedule__schedule_code__icontains=search)
                | Q(sampling__monitoring_schedule__monitoring_plan__plan_name__icontains=search)
                | Q(sampling__monitoring_schedule__monitoring_plan__plant__name__icontains=search)
                | Q(hazard__hazard__icontains=search)
                | Q(exposure_type__exposure_type__icontains=search)
                | Q(exposure_group__exposure_group__icontains=search)
                | Q(area_or_location__icontains=search)
                | Q(department__icontains=search)
                | Q(employee_name__icontains=search)
                | Q(monitoring_parameter__parameter_name__icontains=search)
                | Q(unit__unit_name__icontains=search)
                | Q(compliance_status__icontains=search)
                | Q(risk_level__icontains=search)
                | Q(status__icontains=search)
            )
        return queryset

# =============================================
# ExposureAssessmentCreateView - Creates a new Industrial Hygiene exposure assessment.
# =============================================
class ExposureAssessmentCreateView(LoginRequiredMixin,CreateView):
    model = ExposureAssessment
    form_class = ExposureAssessmentForm
    template_name = "industrial_hygiene/exposure_assessment/exposure_assessment_form.html"
    success_url = reverse_lazy("industrial_hygiene:exposure_assessment_list")
    def form_valid(self,form):
        messages.success(self.request,"Exposure assessment created successfully.")
        return super().form_valid(form)

# =============================================
# ExposureAssessmentUpdateView - Updates an existing Industrial Hygiene exposure assessment.
# =============================================
class ExposureAssessmentUpdateView(LoginRequiredMixin,UpdateView):
    model = ExposureAssessment
    form_class = ExposureAssessmentForm
    template_name = "industrial_hygiene/exposure_assessment/exposure_assessment_form.html"
    success_url = reverse_lazy("industrial_hygiene:exposure_assessment_list")
    def form_valid(self,form):
        messages.success(self.request,"Exposure assessment updated successfully.")
        return super().form_valid(form)

# =============================================
# ExposureAssessmentDetailView - Displays Industrial Hygiene exposure assessment details.
# =============================================
class ExposureAssessmentDetailView(LoginRequiredMixin,DetailView):
    model = ExposureAssessment
    template_name = "industrial_hygiene/exposure_assessment/exposure_assessment_detail.html"
    context_object_name = "exposure_assessment"




# =============================================
# ComplianceRecordListView - Displays and searches Industrial Hygiene compliance records.
# =============================================
class ComplianceRecordListView(LoginRequiredMixin,ListView):
    model = ComplianceRecord
    template_name = "industrial_hygiene/compliance/compliance_list.html"
    context_object_name = "compliance_records"
    paginate_by = 20
    def get_queryset(self):
        queryset = ComplianceRecord.objects.select_related(
            "exposure_assessment",
            "exposure_assessment__sampling",
            "exposure_assessment__sampling__monitoring_schedule",
            "exposure_assessment__sampling__monitoring_schedule__monitoring_plan",
            "exposure_assessment__sampling__monitoring_schedule__monitoring_plan__ih_program",
            "exposure_assessment__sampling__monitoring_schedule__monitoring_plan__plant",
            "sampling",
            "sampling__monitoring_schedule",
            "sampling__monitoring_schedule__monitoring_plan",
            "sampling__monitoring_schedule__monitoring_plan__plant",
            "measurement",
            "laboratory_result",
            "hazard",
            "exposure_group",
            "monitoring_parameter",
            "unit",
            "applicable_oel",
            "applicable_oel__hazard",
            "applicable_oel__monitoring_parameter",
            "applicable_oel__unit",
            "assessed_by"
        ).all().order_by("-assessment_date","compliance_code")
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(compliance_code__icontains=search)
                | Q(exposure_assessment__assessment_code__icontains=search)
                | Q(sampling__sampling_code__icontains=search)
                | Q(sampling__sample_number__icontains=search)
                | Q(sampling__monitoring_schedule__schedule_name__icontains=search)
                | Q(sampling__monitoring_schedule__schedule_code__icontains=search)
                | Q(sampling__monitoring_schedule__monitoring_plan__plan_name__icontains=search)
                | Q(sampling__monitoring_schedule__monitoring_plan__plant__name__icontains=search)
                | Q(hazard__hazard__icontains=search)
                | Q(exposure_group__exposure_group__icontains=search)
                | Q(area_or_location__icontains=search)
                | Q(department__icontains=search)
                | Q(employee_name__icontains=search)
                | Q(monitoring_parameter__parameter_name__icontains=search)
                | Q(unit__unit_name__icontains=search)
                | Q(compliance_status__icontains=search)
                | Q(risk_level__icontains=search)
                | Q(status__icontains=search)
            )
        return queryset

# =============================================
# ComplianceRecordCreateView - Creates a new Industrial Hygiene compliance record.
# =============================================
class ComplianceRecordCreateView(LoginRequiredMixin,CreateView):
    model = ComplianceRecord
    form_class = ComplianceRecordForm
    template_name = "industrial_hygiene/compliance/compliance_form.html"
    success_url = reverse_lazy("industrial_hygiene:compliance_list")
    def form_valid(self,form):
        messages.success(self.request,"Compliance record created successfully.")
        return super().form_valid(form)

# =============================================
# ComplianceRecordUpdateView - Updates an existing Industrial Hygiene compliance record.
# =============================================
class ComplianceRecordUpdateView(LoginRequiredMixin,UpdateView):
    model = ComplianceRecord
    form_class = ComplianceRecordForm
    template_name = "industrial_hygiene/compliance/compliance_form.html"
    success_url = reverse_lazy("industrial_hygiene:compliance_list")
    def form_valid(self,form):
        messages.success(self.request,"Compliance record updated successfully.")
        return super().form_valid(form)

# =============================================
# ComplianceRecordDetailView - Displays Industrial Hygiene compliance record details.
# =============================================
class ComplianceRecordDetailView(LoginRequiredMixin,DetailView):
    model = ComplianceRecord
    template_name = "industrial_hygiene/compliance/compliance_detail.html"
    context_object_name = "compliance_record"





# =============================================
# ExceedanceActionListView - Displays and searches Industrial Hygiene exceedance and corrective action records.
# =============================================
class ExceedanceActionListView(LoginRequiredMixin,ListView):
    model = ExceedanceAction
    template_name = "industrial_hygiene/exceedance_action/exceedance_action_list.html"
    context_object_name = "exceedance_actions"
    paginate_by = 20
    def get_queryset(self):
        queryset = ExceedanceAction.objects.select_related(
            "compliance_record",
            "compliance_record__exposure_assessment",
            "compliance_record__sampling",
            "compliance_record__hazard",
            "compliance_record__applicable_oel",
            "exposure_assessment",
            "exposure_assessment__sampling",
            "exposure_assessment__sampling__monitoring_schedule",
            "exposure_assessment__sampling__monitoring_schedule__monitoring_plan",
            "exposure_assessment__sampling__monitoring_schedule__monitoring_plan__plant",
            "sampling",
            "sampling__monitoring_schedule",
            "sampling__monitoring_schedule__monitoring_plan",
            "sampling__monitoring_schedule__monitoring_plan__plant",
            "measurement",
            "laboratory_result",
            "hazard",
            "exposure_group",
            "responsible_person",
            "verified_by"
        ).all().order_by("-created_at","exceedance_code")
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(exceedance_code__icontains=search)
                | Q(compliance_record__compliance_code__icontains=search)
                | Q(exposure_assessment__assessment_code__icontains=search)
                | Q(sampling__sampling_code__icontains=search)
                | Q(sampling__sample_number__icontains=search)
                | Q(sampling__monitoring_schedule__schedule_name__icontains=search)
                | Q(sampling__monitoring_schedule__schedule_code__icontains=search)
                | Q(sampling__monitoring_schedule__monitoring_plan__plan_name__icontains=search)
                | Q(sampling__monitoring_schedule__monitoring_plan__plant__name__icontains=search)
                | Q(hazard__hazard__icontains=search)
                | Q(exposure_group__exposure_group__icontains=search)
                | Q(area_or_location__icontains=search)
                | Q(department__icontains=search)
                | Q(employee_name__icontains=search)
                | Q(root_cause__icontains=search)
                | Q(corrective_action__icontains=search)
                | Q(responsible_person__first_name__icontains=search)
                | Q(responsible_person__last_name__icontains=search)
                | Q(status__icontains=search)
                | Q(priority__icontains=search)
                | Q(risk_level__icontains=search)
            )
        return queryset

# =============================================
# ExceedanceActionCreateView - Creates a new Industrial Hygiene exceedance and corrective action record.
# =============================================
class ExceedanceActionCreateView(LoginRequiredMixin,CreateView):
    model = ExceedanceAction
    form_class = ExceedanceActionForm
    template_name = "industrial_hygiene/exceedance_action/exceedance_action_form.html"
    success_url = reverse_lazy("industrial_hygiene:exceedance_action_list")
    def form_valid(self,form):
        messages.success(self.request,"Exceedance action created successfully.")
        return super().form_valid(form)

# =============================================
# ExceedanceActionUpdateView - Updates an existing Industrial Hygiene exceedance and corrective action record.
# =============================================
class ExceedanceActionUpdateView(LoginRequiredMixin,UpdateView):
    model = ExceedanceAction
    form_class = ExceedanceActionForm
    template_name = "industrial_hygiene/exceedance_action/exceedance_action_form.html"
    success_url = reverse_lazy("industrial_hygiene:exceedance_action_list")
    def form_valid(self,form):
        messages.success(self.request,"Exceedance action updated successfully.")
        return super().form_valid(form)

# =============================================
# ExceedanceActionDetailView - Displays Industrial Hygiene exceedance and corrective action details.
# =============================================
class ExceedanceActionDetailView(LoginRequiredMixin,DetailView):
    model = ExceedanceAction
    template_name = "industrial_hygiene/exceedance_action/exceedance_action_detail.html"
    context_object_name = "exceedance_action"





# =============================================
# ReMonitoringListView - Displays and searches Industrial Hygiene re-monitoring records.
# =============================================
class ReMonitoringListView(LoginRequiredMixin,ListView):
    model = ReMonitoring
    template_name = "industrial_hygiene/re_monitoring/re_monitoring_list.html"
    context_object_name = "re_monitoring_records"
    paginate_by = 20
    def get_queryset(self):
        queryset = ReMonitoring.objects.select_related(
            "exceedance_action",
            "exceedance_action__compliance_record",
            "exceedance_action__exposure_assessment",
            "exceedance_action__sampling",
            "exceedance_action__hazard",
            "exceedance_action__exposure_group",
            "original_sampling",
            "original_sampling__monitoring_schedule",
            "original_sampling__monitoring_schedule__monitoring_plan",
            "original_sampling__monitoring_schedule__monitoring_plan__plant",
            "original_sampling__hazard",
            "original_sampling__exposure_group",
            "original_measurement",
            "hazard",
            "exposure_group",
            "monitoring_parameter",
            "unit",
            "new_sampling",
            "new_measurement",
            "conducted_by",
            "verified_by"
        ).all().order_by("-created_at","re_monitoring_code")
        search = self.request.GET.get("search","").strip()
        if search:
            queryset = queryset.filter(
                Q(re_monitoring_code__icontains=search)
                | Q(exceedance_action__exceedance_code__icontains=search)
                | Q(exceedance_action__compliance_record__compliance_code__icontains=search)
                | Q(exceedance_action__exposure_assessment__assessment_code__icontains=search)
                | Q(original_sampling__sampling_code__icontains=search)
                | Q(original_sampling__sample_number__icontains=search)
                | Q(original_sampling__monitoring_schedule__schedule_name__icontains=search)
                | Q(original_sampling__monitoring_schedule__schedule_code__icontains=search)
                | Q(original_sampling__monitoring_schedule__monitoring_plan__plan_name__icontains=search)
                | Q(original_sampling__monitoring_schedule__monitoring_plan__plant__name__icontains=search)
                | Q(hazard__hazard__icontains=search)
                | Q(exposure_group__exposure_group__icontains=search)
                | Q(area_or_location__icontains=search)
                | Q(department__icontains=search)
                | Q(employee_name__icontains=search)
                | Q(monitoring_parameter__parameter_name__icontains=search)
                | Q(unit__unit_name__icontains=search)
                | Q(status__icontains=search)
                | Q(compliance_status__icontains=search)
                | Q(effectiveness__icontains=search)
            )
        return queryset

# =============================================
# ReMonitoringCreateView - Creates a new Industrial Hygiene re-monitoring record.
# =============================================
class ReMonitoringCreateView(LoginRequiredMixin,CreateView):
    model = ReMonitoring
    form_class = ReMonitoringForm
    template_name = "industrial_hygiene/re_monitoring/re_monitoring_form.html"
    success_url = reverse_lazy("industrial_hygiene:re_monitoring_list")
    def form_valid(self,form):
        messages.success(self.request,"Re-monitoring record created successfully.")
        return super().form_valid(form)

# =============================================
# ReMonitoringUpdateView - Updates an existing Industrial Hygiene re-monitoring record.
# =============================================
class ReMonitoringUpdateView(LoginRequiredMixin,UpdateView):
    model = ReMonitoring
    form_class = ReMonitoringForm
    template_name = "industrial_hygiene/re_monitoring/re_monitoring_form.html"
    success_url = reverse_lazy("industrial_hygiene:re_monitoring_list")
    def form_valid(self,form):
        messages.success(self.request,"Re-monitoring record updated successfully.")
        return super().form_valid(form)

# =============================================
# ReMonitoringDetailView - Displays Industrial Hygiene re-monitoring details.
# =============================================
class ReMonitoringDetailView(LoginRequiredMixin,DetailView):
    model = ReMonitoring
    template_name = "industrial_hygiene/re_monitoring/re_monitoring_detail.html"
    context_object_name = "re_monitoring"


