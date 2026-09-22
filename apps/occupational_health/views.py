from datetime import timedelta
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models import Q
from django.db.models.aggregates import Count
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic import DeleteView, DetailView, View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView
from django.http import JsonResponse
from .services import (create_medical_examination_follow_up,create_medical_test_follow_up,
    create_fitness_follow_up, create_health_surveillance_follow_up, create_exposure_follow_up
)
from .models import (
    ExaminationType, MedicalTest, ExposureType, HealthCondition, FitnessStatus,
    Restriction, Vaccination, MedicalProfessional, MedicalFacility, EmployeeHealthProfile,
    MedicalExamination, MedicalTestResult, FitnessToWork, HealthSurveillance, EmployeeExposure,
    MedicalFollowUp, EmployeeVaccination, EmployeeOccupationalDisease, HealthIncident,
    ReturnToWork, MedicalRecord, HealthCamp, HealthCampParticipation
)
from .forms import (
    ExaminationTypeForm,MedicalTestForm,ExposureTypeForm,HealthConditionForm,
    FitnessStatusForm,RestrictionForm,VaccinationForm, MedicalProfessionalForm, MedicalFacilityForm,
    EmployeeHealthProfileForm, MedicalExaminationForm, MedicalTestResultForm, FitnessToWorkForm,
    HealthSurveillanceForm, EmployeeExposureForm, MedicalFollowUpForm, EmployeeVaccinationForm,
    EmployeeOccupationalDiseaseForm, HealthIncidentForm, ReturnToWorkForm, MedicalRecordForm, 
    HealthCampForm, HealthCampParticipationForm
)


# =============================================
# OccupationalHealthDashboardView - Displays the main Occupational Health dashboard.
# =============================================
class OccupationalHealthDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'occupational_health/dashboard.html'


# =============================================
# ExaminationTypeListView - Displays and searches examination types with Occupational Health statistics
# =============================================
class ExaminationTypeListView(LoginRequiredMixin, ListView):
    model = ExaminationType
    template_name = 'occupational_health/masters/examination_type_list.html'
    context_object_name = 'examination_types'
    paginate_by = 15

    def get_queryset(self):
        qs = ExaminationType.objects.all()

        search_query = self.request.GET.get('search', '').strip()

        if search_query:
            qs = qs.filter(
                models.Q(name__icontains=search_query) |
                models.Q(code__icontains=search_query) |
                models.Q(description__icontains=search_query)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_types'] = ExaminationType.objects.count()
        context['active_types'] = ExaminationType.objects.filter(
            is_active=True
        ).count()
        context['inactive_types'] = ExaminationType.objects.filter(
            is_active=False
        ).count()

        # Examination transaction model is not created yet.
        # This will be connected when the Medical Examinations module is developed.
        context['total_examinations'] = 0

        context['search_query'] = self.request.GET.get(
            'search', ''
        ).strip()

        return context


# =============================================
# ExaminationTypeCreateView - Creates a new examination type master.
# =============================================
class ExaminationTypeCreateView(LoginRequiredMixin, CreateView):
    model = ExaminationType
    form_class = ExaminationTypeForm
    template_name = 'occupational_health/masters/examination_type_form.html'
    success_url = reverse_lazy('occupational_health:examination_type_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Examination Type created successfully.')
        return super().form_valid(form)


# =============================================
# ExaminationTypeUpdateView - Updates an existing examination type master.
# =============================================
class ExaminationTypeUpdateView(LoginRequiredMixin, UpdateView):
    model = ExaminationType
    form_class = ExaminationTypeForm
    template_name = 'occupational_health/masters/examination_type_form.html'
    success_url = reverse_lazy('occupational_health:examination_type_list')

    def form_valid(self, form):
        messages.success(self.request, 'Examination Type updated successfully.')
        return super().form_valid(form)



# =============================================
# ExaminationTypeDeleteView - Confirms and deletes examination types when they are not in use
# =============================================
class ExaminationTypeDeleteView(LoginRequiredMixin, DeleteView):
    model = ExaminationType
    template_name = 'occupational_health/masters/examination_type_delete.html'
    context_object_name = 'examination_type'
    success_url = reverse_lazy('occupational_health:examination_type_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Medical Examination transaction model is not created yet.
        # This will be connected when the Medical Examinations module is developed.
        context['examination_count'] = 0

        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Medical Examination transaction model is not created yet.
        # Therefore, deletion is currently allowed when no transaction exists.
        examination_count = 0

        if examination_count > 0:
            messages.error(
                request,
                'This examination type cannot be deleted because it is currently in use.'
            )
            return redirect('occupational_health:examination_type_list')

        messages.success(
            request,
            f'Examination Type "{self.object.name}" was deleted successfully.'
        )

        return super().delete(request, *args, **kwargs)


# =============================================
# MedicalTestListView - Displays and searches all medical test masters.
# =============================================
class MedicalTestListView(LoginRequiredMixin, ListView):
    model = MedicalTest
    template_name = 'occupational_health/masters/medical_test_list.html'
    context_object_name = 'medical_tests'
    paginate_by = 15

    def get_queryset(self):
        queryset = MedicalTest.objects.all()
        search = self.request.GET.get('search', '').strip()

        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(code__icontains=search) |
                models.Q(test_type__icontains=search)
            )

        return queryset


# =============================================
# MedicalTestCreateView - Creates a new medical test master.
# =============================================
class MedicalTestCreateView(LoginRequiredMixin, CreateView):
    model = MedicalTest
    form_class = MedicalTestForm
    template_name = 'occupational_health/masters/medical_test_form.html'
    success_url = reverse_lazy('occupational_health:medical_test_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Medical Test created successfully.')
        return super().form_valid(form)


# =============================================
# MedicalTestUpdateView - Updates an existing medical test master.
# =============================================
class MedicalTestUpdateView(LoginRequiredMixin, UpdateView):
    model = MedicalTest
    form_class = MedicalTestForm
    template_name = 'occupational_health/masters/medical_test_form.html'
    success_url = reverse_lazy('occupational_health:medical_test_list')

    def form_valid(self, form):
        messages.success(self.request, 'Medical Test updated successfully.')
        return super().form_valid(form)

# =============================================
# MedicalTestDeleteView - Confirms and deletes medical tests when they are not in use
# =============================================
class MedicalTestDeleteView(LoginRequiredMixin, DeleteView):
    model = MedicalTest
    template_name = 'occupational_health/masters/medical_test_delete.html'
    context_object_name = 'medical_test'
    success_url = reverse_lazy('occupational_health:medical_test_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Medical examination transaction model is not created yet.
        # This will be connected when the Medical Examinations module is developed.
        context['test_usage_count'] = 0

        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Medical examination transaction model is not created yet.
        # Therefore, deletion is currently allowed when no transaction exists.
        test_usage_count = 0

        if test_usage_count > 0:
            messages.error(
                request,
                'This medical test cannot be deleted because it is currently in use.'
            )
            return redirect(
                'occupational_health:medical_test_list'
            )

        messages.success(
            request,
            f'Medical Test "{self.object.name}" was deleted successfully.'
        )

        return super().delete(request, *args, **kwargs)

# =============================================
# ExposureTypeListView - Displays and searches all occupational exposure masters.
# =============================================
class ExposureTypeListView(LoginRequiredMixin, ListView):
    model = ExposureType
    template_name = 'occupational_health/masters/exposure_type_list.html'
    context_object_name = 'exposure_types'
    paginate_by = 15

    def get_queryset(self):
        queryset = ExposureType.objects.all()
        search = self.request.GET.get('search', '').strip()

        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(code__icontains=search)
            )

        return queryset


# =============================================
# ExposureTypeCreateView - Creates a new occupational exposure type master.
# =============================================
class ExposureTypeCreateView(LoginRequiredMixin, CreateView):
    model = ExposureType
    form_class = ExposureTypeForm
    template_name = 'occupational_health/masters/exposure_type_form.html'
    success_url = reverse_lazy('occupational_health:exposure_type_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Exposure Type created successfully.')
        return super().form_valid(form)


# =============================================
# ExposureTypeUpdateView - Updates an existing occupational exposure type master.
# =============================================
class ExposureTypeUpdateView(LoginRequiredMixin, UpdateView):
    model = ExposureType
    form_class = ExposureTypeForm
    template_name = 'occupational_health/masters/exposure_type_form.html'
    success_url = reverse_lazy('occupational_health:exposure_type_list')

    def form_valid(self, form):
        messages.success(self.request, 'Exposure Type updated successfully.')
        return super().form_valid(form)


# =============================================
# ExposureTypeDeleteView - Confirms and deletes exposure types when they are not in use
# =============================================
class ExposureTypeDeleteView(LoginRequiredMixin, DeleteView):
    model = ExposureType
    template_name = 'occupational_health/masters/exposure_type_delete.html'
    context_object_name = 'exposure_type'
    success_url = reverse_lazy('occupational_health:exposure_type_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Health Surveillance / Exposure transaction models are not created yet.
        # This will be connected when the Exposure Tracking / Health Surveillance
        # module is developed.
        context['exposure_usage_count'] = 0

        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Exposure transaction model is not created yet.
        # Therefore, deletion is currently allowed when no transaction exists.
        exposure_usage_count = 0

        if exposure_usage_count > 0:
            messages.error(
                request,
                'This exposure type cannot be deleted because it is currently in use.'
            )
            return redirect(
                'occupational_health:exposure_type_list'
            )

        messages.success(
            request,
            f'Exposure Type "{self.object.name}" was deleted successfully.'
        )

        return super().delete(request, *args, **kwargs)

# =============================================
# HealthConditionListView - Displays and searches all configured health conditions
# =============================================
class HealthConditionListView(LoginRequiredMixin, ListView):
    model = HealthCondition
    template_name = 'occupational_health/masters/health_condition_list.html'
    context_object_name = 'health_conditions'
    paginate_by = 15

    def get_queryset(self):
        queryset = HealthCondition.objects.all()

        search = self.request.GET.get('search', '').strip()

        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(code__icontains=search) |
                models.Q(category__icontains=search)
            )

        return queryset


# =============================================
# HealthConditionCreateView - Creates a new standardized health condition
# =============================================
class HealthConditionCreateView(LoginRequiredMixin, CreateView):
    model = HealthCondition
    form_class = HealthConditionForm
    template_name = 'occupational_health/masters/health_condition_form.html'
    success_url = reverse_lazy('occupational_health:health_condition_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        response = super().form_valid(form)

        messages.success(
            self.request,
            'Health condition has been created successfully.'
        )

        return response


# =============================================
# HealthConditionUpdateView - Updates an existing standardized health condition
# =============================================
class HealthConditionUpdateView(LoginRequiredMixin, UpdateView):
    model = HealthCondition
    form_class = HealthConditionForm
    template_name = 'occupational_health/masters/health_condition_form.html'
    success_url = reverse_lazy('occupational_health:health_condition_list')

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            'Health condition has been updated successfully.'
        )

        return response
    

# =============================================
# HealthConditionDeleteView - Confirms and deletes health conditions when they are not in use
# =============================================
class HealthConditionDeleteView(LoginRequiredMixin, DeleteView):
    model = HealthCondition
    template_name = 'occupational_health/masters/health_condition_delete.html'
    context_object_name = 'health_condition'
    success_url = reverse_lazy('occupational_health:health_condition_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Health condition transaction models are not created yet.
        # This will be connected when the Employee Health Profile /
        # Medical Examination / Occupational Disease modules are developed.
        context['condition_usage_count'] = 0

        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Health condition transaction model is not created yet.
        # Therefore, deletion is currently allowed.
        condition_usage_count = 0

        if condition_usage_count > 0:
            messages.error(
                request,
                'This health condition cannot be deleted because it is currently in use.'
            )
            return redirect(
                'occupational_health:health_condition_list'
            )

        messages.success(
            request,
            f'Health Condition "{self.object.name}" was deleted successfully.'
        )

        return super().delete(request, *args, **kwargs)


# =============================================
# FitnessStatusListView - Displays and searches all Occupational Health fitness statuses
# =============================================
# =============================================
# FitnessStatusListView - Displays and searches all fitness status master records
# =============================================
class FitnessStatusListView(LoginRequiredMixin, ListView):
    model = FitnessStatus
    template_name = 'occupational_health/masters/fitness_status_list.html'
    context_object_name = 'fitness_statuses'
    paginate_by = 15

    def get_queryset(self):
        qs = FitnessStatus.objects.all()

        q = self.request.GET.get('q', '').strip()

        if q:
            qs = qs.filter(
                models.Q(name__icontains=q) |
                models.Q(code__icontains=q) |
                models.Q(description__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_statuses'] = FitnessStatus.objects.count()
        context['active_statuses'] = FitnessStatus.objects.filter(
            is_active=True
        ).count()
        context['inactive_statuses'] = FitnessStatus.objects.filter(
            is_active=False
        ).count()

        context['search_query'] = self.request.GET.get('q', '').strip()

        return context


# =============================================
# FitnessStatusCreateView - Creates a new Occupational Health fitness status
# =============================================
class FitnessStatusCreateView(LoginRequiredMixin, CreateView):
    model = FitnessStatus
    form_class = FitnessStatusForm
    template_name = 'occupational_health/masters/fitness_status_form.html'
    success_url = reverse_lazy('occupational_health:fitness_status_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(
            self.request,
            'Fitness status created successfully.'
        )
        return super().form_valid(form)


# =============================================
# FitnessStatusUpdateView - Updates an existing Occupational Health fitness status
# =============================================
class FitnessStatusUpdateView(LoginRequiredMixin, UpdateView):
    model = FitnessStatus
    form_class = FitnessStatusForm
    template_name = 'occupational_health/masters/fitness_status_form.html'
    success_url = reverse_lazy('occupational_health:fitness_status_list')

    def form_valid(self, form):
        messages.success(
            self.request,
            'Fitness status updated successfully.'
        )
        return super().form_valid(form)


# =============================================
# FitnessStatusDeleteView - Confirms and deletes fitness statuses when they are not in use
# =============================================
class FitnessStatusDeleteView(LoginRequiredMixin, DeleteView):
    model = FitnessStatus
    template_name = 'occupational_health/masters/fitness_status_delete.html'
    context_object_name = 'fitness_status'
    success_url = reverse_lazy('occupational_health:fitness_status_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Fitness transaction models are not created yet.
        # This will be connected when the Fitness to Work module is developed.
        context['fitness_usage_count'] = 0

        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Fitness transaction model is not created yet.
        # Therefore, deletion is currently allowed.
        fitness_usage_count = 0

        if fitness_usage_count > 0:
            messages.error(
                request,
                'This fitness status cannot be deleted because it is currently in use.'
            )
            return redirect(
                'occupational_health:fitness_status_list'
            )

        messages.success(
            request,
            f'Fitness Status "{self.object.name}" was deleted successfully.'
        )

        return super().delete(request, *args, **kwargs)




# =============================================
# RestrictionListView - Displays and searches all restriction master records
# =============================================
class RestrictionListView(LoginRequiredMixin, ListView):
    model = Restriction
    template_name = 'occupational_health/masters/restriction_list.html'
    context_object_name = 'restrictions'
    paginate_by = 15

    def get_queryset(self):
        qs = Restriction.objects.all()

        q = self.request.GET.get('q', '').strip()

        if q:
            qs = qs.filter(
                models.Q(name__icontains=q) |
                models.Q(code__icontains=q) |
                models.Q(description__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_restrictions'] = Restriction.objects.count()
        context['active_restrictions'] = Restriction.objects.filter(
            is_active=True
        ).count()
        context['inactive_restrictions'] = Restriction.objects.filter(
            is_active=False
        ).count()

        # Transaction models are not created yet.
        # This will be connected when Fitness to Work / Health Surveillance
        # transaction models are developed.
        context['total_assignments'] = 0

        context['search_query'] = self.request.GET.get('q', '').strip()

        return context


# =============================================
# RestrictionCreateView - Creates a new restriction master record
# =============================================
class RestrictionCreateView(LoginRequiredMixin, CreateView):
    model = Restriction
    form_class = RestrictionForm
    template_name = 'occupational_health/masters/restriction_form.html'
    success_url = reverse_lazy('occupational_health:restriction_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        messages.success(
            self.request,
            f'Restriction "{form.instance.name}" was created successfully.'
        )

        return super().form_valid(form)


# =============================================
# RestrictionUpdateView - Updates an existing restriction master record
# =============================================
class RestrictionUpdateView(LoginRequiredMixin, UpdateView):
    model = Restriction
    form_class = RestrictionForm
    template_name = 'occupational_health/masters/restriction_form.html'
    success_url = reverse_lazy('occupational_health:restriction_list')

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Restriction "{form.instance.name}" was updated successfully.'
        )

        return super().form_valid(form)


# =============================================
# RestrictionDeleteView - Confirms and deletes restrictions when they are not in use
# =============================================
class RestrictionDeleteView(LoginRequiredMixin, DeleteView):
    model = Restriction
    template_name = 'occupational_health/masters/restriction_delete.html'
    context_object_name = 'restriction'
    success_url = reverse_lazy('occupational_health:restriction_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Fitness / restriction transaction models are not created yet.
        # This will be connected when the Fitness to Work module is developed.
        context['restriction_usage_count'] = 0

        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        restriction_usage_count = 0

        if restriction_usage_count > 0:
            messages.error(
                request,
                'This restriction cannot be deleted because it is currently in use.'
            )

            return redirect(
                'occupational_health:restriction_list'
            )

        messages.success(
            request,
            f'Restriction "{self.object.name}" was deleted successfully.'
        )

        return super().delete(request, *args, **kwargs)


# =============================================
# VaccinationListView - Displays and searches all vaccination master records
# =============================================
class VaccinationListView(LoginRequiredMixin, ListView):
    model = Vaccination
    template_name = 'occupational_health/masters/vaccination_list.html'
    context_object_name = 'vaccinations'
    paginate_by = 15

    def get_queryset(self):
        qs = Vaccination.objects.all()

        q = self.request.GET.get('q', '').strip()

        if q:
            qs = qs.filter(
                models.Q(name__icontains=q) |
                models.Q(code__icontains=q) |
                models.Q(description__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_vaccinations'] = Vaccination.objects.count()

        context['active_vaccinations'] = Vaccination.objects.filter(
            is_active=True
        ).count()

        context['inactive_vaccinations'] = Vaccination.objects.filter(
            is_active=False
        ).count()

        # Vaccination transaction model will be connected later.
        context['total_vaccination_records'] = 0

        context['search_query'] = self.request.GET.get(
            'q', ''
        ).strip()

        return context


# =============================================
# VaccinationCreateView - Creates new vaccination master records
# =============================================
class VaccinationCreateView(LoginRequiredMixin, CreateView):
    model = Vaccination
    form_class = VaccinationForm
    template_name = 'occupational_health/masters/vaccination_form.html'
    success_url = reverse_lazy('occupational_health:vaccination_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        messages.success(
            self.request,
            f'Vaccination "{form.instance.name}" was created successfully.'
        )

        return super().form_valid(form)


# =============================================
# VaccinationUpdateView - Updates existing vaccination master records
# =============================================
class VaccinationUpdateView(LoginRequiredMixin, UpdateView):
    model = Vaccination
    form_class = VaccinationForm
    template_name = 'occupational_health/masters/vaccination_form.html'
    success_url = reverse_lazy('occupational_health:vaccination_list')

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Vaccination "{form.instance.name}" was updated successfully.'
        )

        return super().form_valid(form)


# =============================================
# VaccinationDeleteView - Confirms and deletes vaccinations when they are not in use
# =============================================
class VaccinationDeleteView(LoginRequiredMixin, DeleteView):
    model = Vaccination
    template_name = 'occupational_health/masters/vaccination_delete.html'
    context_object_name = 'vaccination'
    success_url = reverse_lazy('occupational_health:vaccination_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Vaccination transaction model is not created yet.
        # This will be connected when the Vaccination module is developed.
        context['vaccination_usage_count'] = 0

        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        vaccination_usage_count = 0

        if vaccination_usage_count > 0:

            messages.error(
                request,
                'This vaccination cannot be deleted because it is currently in use.'
            )

            return redirect(
                'occupational_health:vaccination_list'
            )

        messages.success(
            request,
            f'Vaccination "{self.object.name}" was deleted successfully.'
        )

        return super().delete(request, *args, **kwargs)



# =============================================
# MedicalProfessionalListView - Displays and searches all medical professional master records
# =============================================
class MedicalProfessionalListView(LoginRequiredMixin, ListView):
    model = MedicalProfessional
    template_name = 'occupational_health/masters/medical_professional_list.html'
    context_object_name = 'medical_professionals'
    paginate_by = 15

    def get_queryset(self):
        qs = MedicalProfessional.objects.all()

        q = self.request.GET.get('q', '').strip()

        if q:
            qs = qs.filter(
                models.Q(name__icontains=q) |
                models.Q(code__icontains=q) |
                models.Q(professional_type__icontains=q) |
                models.Q(qualification__icontains=q) |
                models.Q(specialization__icontains=q) |
                models.Q(registration_number__icontains=q) |
                models.Q(contact_number__icontains=q) |
                models.Q(email__icontains=q) |
                models.Q(description__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_professionals'] = MedicalProfessional.objects.count()

        context['active_professionals'] = MedicalProfessional.objects.filter(
            is_active=True
        ).count()

        context['inactive_professionals'] = MedicalProfessional.objects.filter(
            is_active=False
        ).count()

        # Medical examination transaction model will be connected later.
        context['total_medical_assessments'] = 0

        context['search_query'] = self.request.GET.get(
            'q', ''
        ).strip()

        return context


# =============================================
# MedicalProfessionalCreateView - Creates new medical professional master records
# =============================================
class MedicalProfessionalCreateView(LoginRequiredMixin, CreateView):
    model = MedicalProfessional
    form_class = MedicalProfessionalForm
    template_name = 'occupational_health/masters/medical_professional_form.html'
    success_url = reverse_lazy('occupational_health:medical_professional_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        messages.success(
            self.request,
            f'Medical Professional "{form.instance.name}" was created successfully.'
        )

        return super().form_valid(form)


# =============================================
# MedicalProfessionalUpdateView - Updates existing medical professional master records
# =============================================
class MedicalProfessionalUpdateView(LoginRequiredMixin, UpdateView):
    model = MedicalProfessional
    form_class = MedicalProfessionalForm
    template_name = 'occupational_health/masters/medical_professional_form.html'
    success_url = reverse_lazy('occupational_health:medical_professional_list')

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Medical Professional "{form.instance.name}" was updated successfully.'
        )

        return super().form_valid(form)


# =============================================
# MedicalProfessionalDeleteView - Confirms and deletes medical professionals when they are not in use
# =============================================
class MedicalProfessionalDeleteView(LoginRequiredMixin, DeleteView):
    model = MedicalProfessional
    template_name = 'occupational_health/masters/medical_professional_delete.html'
    context_object_name = 'medical_professional'
    success_url = reverse_lazy('occupational_health:medical_professional_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Medical examination transaction model is not created yet.
        # This will be connected when the Medical Examination module is developed.
        context['professional_usage_count'] = 0

        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        professional_usage_count = 0

        if professional_usage_count > 0:

            messages.error(
                request,
                'This medical professional cannot be deleted because it is currently in use.'
            )

            return redirect(
                'occupational_health:medical_professional_list'
            )

        messages.success(
            request,
            f'Medical Professional "{self.object.name}" was deleted successfully.'
        )

        return super().delete(request, *args, **kwargs)    



# =============================================
# MedicalFacilityListView - Displays and searches all medical facility master records
# =============================================
class MedicalFacilityListView(LoginRequiredMixin, ListView):
    model = MedicalFacility
    template_name = 'occupational_health/masters/medical_facility_list.html'
    context_object_name = 'medical_facilities'
    paginate_by = 15

    def get_queryset(self):
        qs = MedicalFacility.objects.all()

        q = self.request.GET.get('q', '').strip()

        if q:
            qs = qs.filter(
                models.Q(name__icontains=q) |
                models.Q(code__icontains=q) |
                models.Q(facility_type__icontains=q) |
                models.Q(address__icontains=q) |
                models.Q(contact_person__icontains=q) |
                models.Q(contact_number__icontains=q) |
                models.Q(email__icontains=q) |
                models.Q(registration_number__icontains=q) |
                models.Q(description__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_facilities'] = MedicalFacility.objects.count()

        context['active_facilities'] = MedicalFacility.objects.filter(
            is_active=True
        ).count()

        context['inactive_facilities'] = MedicalFacility.objects.filter(
            is_active=False
        ).count()

        # Medical examination transaction model will be connected later.
        context['total_medical_records'] = 0

        context['search_query'] = self.request.GET.get(
            'q', ''
        ).strip()

        return context


# =============================================
# MedicalFacilityCreateView - Creates new medical facility master records
# =============================================
class MedicalFacilityCreateView(LoginRequiredMixin, CreateView):
    model = MedicalFacility
    form_class = MedicalFacilityForm
    template_name = 'occupational_health/masters/medical_facility_form.html'
    success_url = reverse_lazy('occupational_health:medical_facility_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        messages.success(
            self.request,
            f'Medical Facility "{form.instance.name}" was created successfully.'
        )

        return super().form_valid(form)


# =============================================
# MedicalFacilityUpdateView - Updates existing medical facility master records
# =============================================
class MedicalFacilityUpdateView(LoginRequiredMixin, UpdateView):
    model = MedicalFacility
    form_class = MedicalFacilityForm
    template_name = 'occupational_health/masters/medical_facility_form.html'
    success_url = reverse_lazy('occupational_health:medical_facility_list')

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Medical Facility "{form.instance.name}" was updated successfully.'
        )

        return super().form_valid(form)


# =============================================
# MedicalFacilityDeleteView - Confirms and deletes medical facilities when they are not in use
# =============================================
class MedicalFacilityDeleteView(LoginRequiredMixin, DeleteView):
    model = MedicalFacility
    template_name = 'occupational_health/masters/medical_facility_delete.html'
    context_object_name = 'medical_facility'
    success_url = reverse_lazy('occupational_health:medical_facility_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Medical examination transaction model is not created yet.
        # This will be connected when the Medical Examination module is developed.
        context['facility_usage_count'] = 0

        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        facility_usage_count = 0

        if facility_usage_count > 0:

            messages.error(
                request,
                'This medical facility cannot be deleted because it is currently in use.'
            )

            return redirect(
                'occupational_health:medical_facility_list'
            )

        messages.success(
            request,
            f'Medical Facility "{self.object.name}" was deleted successfully.'
        )

        return super().delete(request, *args, **kwargs)
    

# =============================================
# EmployeeHealthProfileListView - Displays and searches employee occupational health profiles
# =============================================
class EmployeeHealthProfileListView(LoginRequiredMixin, ListView):
    model = EmployeeHealthProfile
    template_name = 'occupational_health/management/employee_health_profile_list.html'
    context_object_name = 'health_profiles'
    paginate_by = 15

    def get_queryset(self):
        qs = EmployeeHealthProfile.objects.select_related('employee').all()

        q = self.request.GET.get('q', '').strip()

        if q:
            qs = qs.filter(
                models.Q(employee__employee_id__icontains=q) |
                models.Q(employee__first_name__icontains=q) |
                models.Q(employee__last_name__icontains=q) |
                models.Q(employee__username__icontains=q) |
                models.Q(employee__job_title__icontains=q) |
                models.Q(job_role__icontains=q) |
                models.Q(work_area__icontains=q) |
                models.Q(work_shift__icontains=q)
            )

        return qs.order_by('employee__employee_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_profiles'] = EmployeeHealthProfile.objects.count()

        context['active_profiles'] = EmployeeHealthProfile.objects.filter(
            is_active=True
        ).count()

        context['inactive_profiles'] = EmployeeHealthProfile.objects.filter(
            is_active=False
        ).count()

        context['surveillance_profiles'] = EmployeeHealthProfile.objects.filter(
            is_under_health_surveillance=True,
            is_active=True
        ).count()

        context['search_query'] = self.request.GET.get('q', '').strip()

        return context

# =============================================
# EmployeeHealthProfileCreateView - Creates a new employee occupational health profile
# =============================================
class EmployeeHealthProfileCreateView(LoginRequiredMixin, CreateView):
    model = EmployeeHealthProfile
    form_class = EmployeeHealthProfileForm
    template_name = 'occupational_health/management/employee_health_profile_form.html'
    success_url = reverse_lazy('occupational_health:employee_health_profile_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        messages.success(
            self.request,
            f'Employee Health Profile for "{form.instance.employee}" was created successfully.'
        )

        return super().form_valid(form)


# =============================================
# EmployeeHealthProfileUpdateView - Updates an existing employee occupational health profile
# =============================================
class EmployeeHealthProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = EmployeeHealthProfile
    form_class = EmployeeHealthProfileForm
    template_name = 'occupational_health/management/employee_health_profile_form.html'
    success_url = reverse_lazy('occupational_health:employee_health_profile_list')

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Employee Health Profile for "{form.instance.employee}" was updated successfully.'
        )

        return super().form_valid(form)


# =============================================
# EmployeeHealthProfileDetailView - Displays the complete occupational health profile of an employee
# =============================================
class EmployeeHealthProfileDetailView(LoginRequiredMixin, DetailView):
    model = EmployeeHealthProfile
    template_name = 'occupational_health/management/employee_health_profile_detail.html'
    context_object_name = 'health_profile'

    def get_queryset(self):
        return EmployeeHealthProfile.objects.select_related(
            'employee'
        ).all()



# =============================================
# MedicalExaminationListView - Displays, searches and filters employee medical examination records
# =============================================
class MedicalExaminationListView(LoginRequiredMixin, ListView):
    model = MedicalExamination
    template_name = 'occupational_health/management/medical_examination_list.html'
    context_object_name = 'medical_examinations'
    paginate_by = 15

    def get_queryset(self):
        qs = MedicalExamination.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'examination_type',
            'medical_professional',
            'medical_facility'
        ).all()

        q = self.request.GET.get('q', '').strip()

        if q:
            qs = qs.filter(
                models.Q(
                    employee_health_profile__employee__employee_id__icontains=q
                ) |
                models.Q(
                    employee_health_profile__employee__first_name__icontains=q
                ) |
                models.Q(
                    employee_health_profile__employee__last_name__icontains=q
                ) |
                models.Q(
                    employee_health_profile__employee__username__icontains=q
                ) |
                models.Q(
                    examination_type__name__icontains=q
                ) |
                models.Q(
                    medical_professional__name__icontains=q
                ) |
                models.Q(
                    medical_facility__name__icontains=q
                ) |
                models.Q(
                    job_role__icontains=q
                ) |
                models.Q(
                    work_area__icontains=q
                )
            )

        return qs.order_by('-examination_date', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_examinations'] = MedicalExamination.objects.count()

        context['scheduled_examinations'] = MedicalExamination.objects.filter(
            status='SCHEDULED'
        ).count()

        context['completed_examinations'] = MedicalExamination.objects.filter(
            status='COMPLETED'
        ).count()

        context['cancelled_examinations'] = MedicalExamination.objects.filter(
            status='CANCELLED'
        ).count()

        context['follow_up_examinations'] = MedicalExamination.objects.filter(
            follow_up_required=True
        ).count()

        context['search_query'] = self.request.GET.get('q', '').strip()

        return context



# =============================================
# MedicalExaminationCreateView - Creates a new employee medical examination record
# =============================================
class MedicalExaminationCreateView(LoginRequiredMixin, CreateView):
    model = MedicalExamination
    form_class = MedicalExaminationForm
    template_name = 'occupational_health/management/medical_examination_form.html'
    success_url = reverse_lazy('occupational_health:medical_examination_list')

    def form_valid(self,form):
        form.instance.created_by=self.request.user
        response=super().form_valid(form)
        follow_up=create_medical_examination_follow_up(
            self.object,
            created_by=self.request.user
        )
        if follow_up:
            messages.success(
                self.request,
                f'Medical Examination was created successfully. Medical Follow-up "{follow_up.title}" was also created.'
            )
        else:
            messages.success(
                self.request,
                'Medical Examination was created successfully.'
            )
        return response


# =============================================
# MedicalExaminationUpdateView - Updates an existing employee medical examination record
# =============================================
class MedicalExaminationUpdateView(LoginRequiredMixin, UpdateView):
    model = MedicalExamination
    form_class = MedicalExaminationForm
    template_name = 'occupational_health/management/medical_examination_form.html'
    success_url = reverse_lazy('occupational_health:medical_examination_list')

    def form_valid(self,form):
        response=super().form_valid(form)
        follow_up=create_medical_examination_follow_up(
            self.object,
            created_by=self.request.user
        )
        if follow_up:
            messages.success(
                self.request,
                f'Medical Examination was updated successfully. Medical Follow-up "{follow_up.title}" is available.'
            )
        else:
            messages.success(
                self.request,
                'Medical Examination was updated successfully.'
            )
        return response


# =============================================
# MedicalExaminationDetailView - Displays the complete details of an employee medical examination
# =============================================
class MedicalExaminationDetailView(LoginRequiredMixin, DetailView):
    model = MedicalExamination
    template_name = 'occupational_health/management/medical_examination_detail.html'
    context_object_name = 'medical_examination'

    def get_queryset(self):
        return MedicalExamination.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'employee_health_profile__employee__department',
            'employee_health_profile__employee__plant',
            'employee_health_profile__employee__zone',
            'employee_health_profile__employee__location',
            'employee_health_profile__employee__sublocation',
            'examination_type',
            'medical_professional',
            'medical_facility',
            'created_by'
        ).all()



# =============================================
# EmployeeHealthProfileDataView - Returns employee health profile information for medical examination forms
# =============================================
class EmployeeHealthProfileDataView(LoginRequiredMixin, DetailView):
    model = EmployeeHealthProfile

    def get(self, request, *args, **kwargs):
        profile = self.get_object()

        employee = profile.employee

        return JsonResponse({
            'employee_id': employee.employee_id or '',
            'employee_name': employee.get_full_name() or employee.username,
            'job_title': employee.job_title or '',
            'job_role': profile.job_role or '',
            'work_area': profile.work_area or '',
            'department': str(employee.department) if employee.department else '',
            'plant': str(employee.plant) if employee.plant else '',
            'zone': str(employee.zone) if employee.zone else '',
            'location': str(employee.location) if employee.location else '',
            'sublocation': str(employee.sublocation) if employee.sublocation else '',
        })




# =============================================
# MedicalTestResultListView - Displays, searches and filters employee medical test results
# =============================================
class MedicalTestResultListView(LoginRequiredMixin, ListView):
    model = MedicalTestResult
    template_name = 'occupational_health/management/medical_test_result_list.html'
    context_object_name = 'medical_test_results'
    paginate_by = 15

    def get_queryset(self):
        qs = MedicalTestResult.objects.select_related(
            'medical_examination',
            'medical_examination__employee_health_profile',
            'medical_examination__employee_health_profile__employee',
            'medical_test',
            'created_by'
        ).all()

        q = self.request.GET.get('q', '').strip()

        if q:
            qs = qs.filter(
                models.Q(
                    medical_examination__employee_health_profile__employee__employee_id__icontains=q
                ) |
                models.Q(
                    medical_examination__employee_health_profile__employee__first_name__icontains=q
                ) |
                models.Q(
                    medical_examination__employee_health_profile__employee__last_name__icontains=q
                ) |
                models.Q(
                    medical_examination__employee_health_profile__employee__username__icontains=q
                ) |
                models.Q(medical_test__name__icontains=q) |
                models.Q(result_value__icontains=q) |
                models.Q(result_status__icontains=q) |
                models.Q(findings__icontains=q)
            )

        return qs.order_by('-test_date', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_test_results'] = MedicalTestResult.objects.count()
        context['normal_results'] = MedicalTestResult.objects.filter(
            result_status='NORMAL'
        ).count()
        context['abnormal_results'] = MedicalTestResult.objects.filter(
            result_status='ABNORMAL'
        ).count()
        context['borderline_results'] = MedicalTestResult.objects.filter(
            result_status='BORDERLINE'
        ).count()
        context['follow_up_results'] = MedicalTestResult.objects.filter(
            follow_up_required=True
        ).count()

        context['search_query'] = self.request.GET.get('q', '').strip()

        return context


# =============================================
# MedicalTestResultCreateView - Creates a new medical test result record
# =============================================
class MedicalTestResultCreateView(LoginRequiredMixin, CreateView):
    model = MedicalTestResult
    form_class = MedicalTestResultForm
    template_name = 'occupational_health/management/medical_test_result_form.html'
    success_url = reverse_lazy(
        'occupational_health:medical_test_result_list'
    )

    def form_valid(self,form):
        form.instance.created_by=self.request.user
        response=super().form_valid(form)
        follow_up=create_medical_test_follow_up(
            self.object,
            created_by=self.request.user
        )
        if follow_up:
            messages.success(
                self.request,
                f'Medical Test Result was created successfully. Medical Follow-up "{follow_up.title}" was also created.'
            )
        else:
            messages.success(
                self.request,
                'Medical Test Result was created successfully.'
            )
        return response


# =============================================
# MedicalTestResultUpdateView - Updates an existing medical test result record
# =============================================
class MedicalTestResultUpdateView(LoginRequiredMixin, UpdateView):
    model = MedicalTestResult
    form_class = MedicalTestResultForm
    template_name = 'occupational_health/management/medical_test_result_form.html'
    success_url = reverse_lazy(
        'occupational_health:medical_test_result_list'
    )

    def form_valid(self,form):
        response=super().form_valid(form)
        follow_up=create_medical_test_follow_up(
            self.object,
            created_by=self.request.user
        )
        if follow_up:
            messages.success(
                self.request,
                f'Medical Test Result was updated successfully. Medical Follow-up "{follow_up.title}" is available.'
            )
        else:
            messages.success(
                self.request,
                'Medical Test Result was updated successfully.'
            )
        return response


# =============================================
# MedicalTestResultDetailView - Displays the complete details of an employee medical test result
# =============================================
class MedicalTestResultDetailView(LoginRequiredMixin, DetailView):
    model = MedicalTestResult
    template_name = 'occupational_health/management/medical_test_result_detail.html'
    context_object_name = 'medical_test_result'

    def get_queryset(self):
        return MedicalTestResult.objects.select_related(
            'medical_examination',
            'medical_examination__employee_health_profile',
            'medical_examination__employee_health_profile__employee',
            'medical_examination__employee_health_profile__employee__department',
            'medical_examination__employee_health_profile__employee__plant',
            'medical_examination__employee_health_profile__employee__zone',
            'medical_examination__employee_health_profile__employee__location',
            'medical_examination__employee_health_profile__employee__sublocation',
            'medical_test',
            'created_by'
        ).all()




# =============================================
# FitnessToWorkListView - Displays, searches and filters employee fitness assessments
# =============================================
class FitnessToWorkListView(LoginRequiredMixin, ListView):
    model = FitnessToWork
    template_name = 'occupational_health/management/fitness_to_work_list.html'
    context_object_name = 'fitness_assessments'
    paginate_by = 15

    def get_queryset(self):
        qs = FitnessToWork.objects.select_related(
            'medical_examination',
            'employee_health_profile',
            'employee_health_profile__employee',
            'medical_examination__examination_type',
            'created_by'
        ).prefetch_related('restrictions').all()

        q = self.request.GET.get('q', '').strip()

        if q:
            qs = qs.filter(
                models.Q(employee_health_profile__employee__employee_id__icontains=q) |
                models.Q(employee_health_profile__employee__first_name__icontains=q) |
                models.Q(employee_health_profile__employee__last_name__icontains=q) |
                models.Q(employee_health_profile__employee__username__icontains=q) |
                models.Q(fitness_status__icontains=q) |
                models.Q(assessment_type__icontains=q) |
                models.Q(medical_findings__icontains=q) |
                models.Q(work_recommendations__icontains=q)
            )

        return qs.order_by('-assessment_date', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_assessments'] = FitnessToWork.objects.count()
        context['fit_assessments'] = FitnessToWork.objects.filter(
            fitness_status='FIT'
        ).count()
        context['restricted_assessments'] = FitnessToWork.objects.filter(
            fitness_status='FIT_WITH_RESTRICTIONS'
        ).count()
        context['temporarily_unfit_assessments'] = FitnessToWork.objects.filter(
            fitness_status='TEMPORARILY_UNFIT'
        ).count()
        context['unfit_assessments'] = FitnessToWork.objects.filter(
            fitness_status='UNFIT'
        ).count()
        context['search_query'] = self.request.GET.get('q', '').strip()

        return context


# =============================================
# FitnessToWorkCreateView - Creates a new employee fitness assessment
# =============================================
class FitnessToWorkCreateView(LoginRequiredMixin, CreateView):
    model = FitnessToWork
    form_class = FitnessToWorkForm
    template_name = 'occupational_health/management/fitness_to_work_form.html'
    success_url = reverse_lazy('occupational_health:fitness_to_work_list')

    def form_valid(self,form):
        response=super().form_valid(form)
        follow_up=create_fitness_follow_up(self.object,created_by=self.request.user)
        if follow_up:
            messages.success(
                self.request,
                f'Fitness Assessment was created successfully. Medical Follow-up "{follow_up.title}" was also created.'
            )
        else:
            messages.success(self.request,'Fitness Assessment was created successfully.')
        return response


# =============================================
# FitnessToWorkUpdateView - Updates an existing employee fitness assessment
# =============================================
class FitnessToWorkUpdateView(LoginRequiredMixin, UpdateView):
    model = FitnessToWork
    form_class = FitnessToWorkForm
    template_name = 'occupational_health/management/fitness_to_work_form.html'
    success_url = reverse_lazy('occupational_health:fitness_to_work_list')

    def form_valid(self,form):
        response=super().form_valid(form)
        follow_up=create_fitness_follow_up(self.object,created_by=self.request.user)
        if follow_up:
            messages.success(
                self.request,
                f'Fitness Assessment was updated successfully. Medical Follow-up "{follow_up.title}" is available.'
            )
        else:
            messages.success(self.request,'Fitness Assessment was updated successfully.')
        return response


# =============================================
# FitnessToWorkDetailView - Displays the complete details of an employee fitness assessment
# =============================================
class FitnessToWorkDetailView(LoginRequiredMixin, DetailView):
    model = FitnessToWork
    template_name = 'occupational_health/management/fitness_to_work_detail.html'
    context_object_name = 'fitness_assessment'

    def get_queryset(self):
        return FitnessToWork.objects.select_related(
            'medical_examination',
            'medical_examination__employee_health_profile',
            'medical_examination__employee_health_profile__employee',
            'medical_examination__employee_health_profile__employee__department',
            'medical_examination__employee_health_profile__employee__plant',
            'medical_examination__employee_health_profile__employee__zone',
            'medical_examination__employee_health_profile__employee__location',
            'medical_examination__employee_health_profile__employee__sublocation',
            'employee_health_profile',
            'employee_health_profile__employee',
            'employee_health_profile__employee__department',
            'employee_health_profile__employee__plant',
            'employee_health_profile__employee__zone',
            'employee_health_profile__employee__location',
            'employee_health_profile__employee__sublocation',
            'created_by'
        ).prefetch_related(
            'restrictions'
        ).all()

# =============================================
# MedicalExaminationFitnessDataView - Returns employee and examination information for fitness assessment
# =============================================
class MedicalExaminationFitnessDataView(LoginRequiredMixin, DetailView):
    model = MedicalExamination

    def get(self, request, *args, **kwargs):
        examination = self.get_object()
        profile = examination.employee_health_profile
        employee = profile.employee

        return JsonResponse({
            'medical_examination_id': examination.id,
            'employee_health_profile_id': profile.id,
            'employee_id': employee.employee_id or '',
            'employee_name': employee.get_full_name() or employee.username,
            'job_title': employee.job_title or '',
            'job_role': profile.job_role or '',
            'work_area': profile.work_area or '',
            'department': str(employee.department) if employee.department else '',
            'plant': str(employee.plant) if employee.plant else '',
            'zone': str(employee.zone) if employee.zone else '',
            'location': str(employee.location) if employee.location else '',
            'sublocation': str(employee.sublocation) if employee.sublocation else '',
            'examination_date': examination.examination_date.strftime('%Y-%m-%d'),
            'examination_type': examination.examination_type.name,
            'medical_professional': examination.medical_professional.name,
            'medical_facility': examination.medical_facility.name,
        })


    



# =============================================
# HealthSurveillanceListView - Displays, searches and filters employee health surveillance records
# =============================================
class HealthSurveillanceListView(LoginRequiredMixin, ListView):
    model = HealthSurveillance
    template_name = 'occupational_health/management/health_surveillance_list.html'
    context_object_name = 'health_surveillance_records'
    paginate_by = 15

    def get_queryset(self):
        qs = HealthSurveillance.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'exposure_type',
            'responsible_medical_professional',
            'medical_facility',
            'created_by'
        ).prefetch_related('required_tests').all()

        q = self.request.GET.get('q', '').strip()

        if q:
            qs = qs.filter(
                models.Q(employee_health_profile__employee__employee_id__icontains=q) |
                models.Q(employee_health_profile__employee__first_name__icontains=q) |
                models.Q(employee_health_profile__employee__last_name__icontains=q) |
                models.Q(employee_health_profile__employee__username__icontains=q) |
                models.Q(surveillance_name__icontains=q) |
                models.Q(exposure_type__name__icontains=q) |
                models.Q(status__icontains=q)
            )

        return qs.order_by('-start_date', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_surveillance'] = HealthSurveillance.objects.count()
        context['active_surveillance'] = HealthSurveillance.objects.filter(
            status='ACTIVE',
            is_active=True
        ).count()
        context['suspended_surveillance'] = HealthSurveillance.objects.filter(
            status='SUSPENDED'
        ).count()
        context['completed_surveillance'] = HealthSurveillance.objects.filter(
            status='COMPLETED'
        ).count()
        context['closed_surveillance'] = HealthSurveillance.objects.filter(
            status='CLOSED'
        ).count()

        context['search_query'] = self.request.GET.get('q', '').strip()
        context['overdue_surveillance'] = sum(
            1 for record in HealthSurveillance.objects.all()
            if record.due_status == 'OVERDUE'
        )

        context['due_today_surveillance'] = sum(
            1 for record in HealthSurveillance.objects.all()
            if record.due_status == 'DUE_TODAY'
        )

        context['due_soon_surveillance'] = sum(
            1 for record in HealthSurveillance.objects.all()
            if record.due_status == 'DUE_SOON'
        )

        return context


# =============================================
# HealthSurveillanceCreateView - Creates a new employee health surveillance record
# =============================================
class HealthSurveillanceCreateView(LoginRequiredMixin, CreateView):
    model = HealthSurveillance
    form_class = HealthSurveillanceForm
    template_name = 'occupational_health/management/health_surveillance_form.html'
    success_url = reverse_lazy(
        'occupational_health:health_surveillance_list'
    )

    def form_valid(self,form):
        form.instance.created_by=self.request.user
        response=super().form_valid(form)
        follow_up=create_health_surveillance_follow_up(self.object,created_by=self.request.user)
        if follow_up:
            messages.success(
                self.request,
                f'Health Surveillance was created successfully. Medical Follow-up "{follow_up.title}" was also created.'
            )
        else:
            messages.success(self.request,'Health Surveillance was created successfully.')
        return response


# =============================================
# HealthSurveillanceUpdateView - Updates an existing employee health surveillance record
# =============================================
class HealthSurveillanceUpdateView(LoginRequiredMixin, UpdateView):
    model = HealthSurveillance
    form_class = HealthSurveillanceForm
    template_name = 'occupational_health/management/health_surveillance_form.html'
    success_url = reverse_lazy(
        'occupational_health:health_surveillance_list'
    )

    def form_valid(self,form):
        response=super().form_valid(form)
        follow_up=create_health_surveillance_follow_up(self.object,created_by=self.request.user)
        if follow_up:
            messages.success(
                self.request,
                f'Health Surveillance was updated successfully. Medical Follow-up "{follow_up.title}" is available.'
            )
        else:
            messages.success(self.request,'Health Surveillance was updated successfully.')
        return response


# =============================================
# HealthSurveillanceDetailView - Displays complete employee health surveillance information
# =============================================
class HealthSurveillanceDetailView(LoginRequiredMixin, DetailView):
    model = HealthSurveillance
    template_name = 'occupational_health/management/health_surveillance_detail.html'
    context_object_name = 'health_surveillance'

    def get_queryset(self):
        return HealthSurveillance.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'employee_health_profile__employee__department',
            'employee_health_profile__employee__plant',
            'employee_health_profile__employee__zone',
            'employee_health_profile__employee__location',
            'employee_health_profile__employee__sublocation',
            'exposure_type',
            'responsible_medical_professional',
            'medical_facility',
            'created_by'
        ).prefetch_related(
            'required_tests'
        ).all()





# =============================================
# EmployeeExposureListView - Displays, searches and filters employee occupational exposure records
# =============================================
class EmployeeExposureListView(LoginRequiredMixin, ListView):
    model = EmployeeExposure
    template_name = 'occupational_health/management/employee_exposure_list.html'
    context_object_name = 'employee_exposures'
    paginate_by = 15

    def get_queryset(self):
        qs = EmployeeExposure.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'exposure_type',
            'health_surveillance',
            'created_by'
        ).all()

        q = self.request.GET.get('q', '').strip()

        if q:
            qs = qs.filter(
                models.Q(
                    employee_health_profile__employee__employee_id__icontains=q
                ) |
                models.Q(
                    employee_health_profile__employee__first_name__icontains=q
                ) |
                models.Q(
                    employee_health_profile__employee__last_name__icontains=q
                ) |
                models.Q(
                    employee_health_profile__employee__username__icontains=q
                ) |
                models.Q(exposure_name__icontains=q) |
                models.Q(exposure_source__icontains=q) |
                models.Q(work_area__icontains=q) |
                models.Q(job_role__icontains=q) |
                models.Q(exposure_type__name__icontains=q) |
                models.Q(status__icontains=q)
            )

        return qs.order_by('-exposure_start_date', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_exposures'] = EmployeeExposure.objects.count()

        context['active_exposures'] = EmployeeExposure.objects.filter(
            status='ACTIVE',
            is_active=True
        ).count()

        context['inactive_exposures'] = EmployeeExposure.objects.filter(
            status='INACTIVE'
        ).count()

        context['closed_exposures'] = EmployeeExposure.objects.filter(
            status='CLOSED'
        ).count()

        context['surveillance_required_exposures'] = EmployeeExposure.objects.filter(
            health_surveillance_required=True
        ).count()

        context['search_query'] = self.request.GET.get(
            'q',
            ''
        ).strip()

        return context


# =============================================
# EmployeeExposureCreateView - Creates a new employee occupational exposure record
# =============================================
class EmployeeExposureCreateView(LoginRequiredMixin, CreateView):
    model = EmployeeExposure
    form_class = EmployeeExposureForm
    template_name = 'occupational_health/management/employee_exposure_form.html'
    success_url = reverse_lazy(
        'occupational_health:employee_exposure_list'
    )

    def form_valid(self,form):
        form.instance.created_by=self.request.user
        response=super().form_valid(form)
        follow_up=create_exposure_follow_up(self.object,created_by=self.request.user)
        if follow_up:
            messages.success(
                self.request,
                f'Employee Exposure was created successfully. Medical Follow-up "{follow_up.title}" was also created.'
            )
        else:
            messages.success(self.request,'Employee Exposure was created successfully.')
        return response


# =============================================
# EmployeeExposureUpdateView - Updates an existing employee occupational exposure record
# =============================================
class EmployeeExposureUpdateView(LoginRequiredMixin, UpdateView):
    model = EmployeeExposure
    form_class = EmployeeExposureForm
    template_name = 'occupational_health/management/employee_exposure_form.html'
    success_url = reverse_lazy(
        'occupational_health:employee_exposure_list'
    )

    def form_valid(self,form):
        response=super().form_valid(form)
        follow_up=create_exposure_follow_up(self.object,created_by=self.request.user)
        if follow_up:
            messages.success(
                self.request,
                f'Employee Exposure was updated successfully. Medical Follow-up "{follow_up.title}" is available.'
            )
        else:
            messages.success(self.request,'Employee Exposure was updated successfully.')
        return response


# =============================================
# EmployeeExposureDetailView - Displays complete employee occupational exposure information
# =============================================
class EmployeeExposureDetailView(LoginRequiredMixin, DetailView):
    model = EmployeeExposure
    template_name = 'occupational_health/management/employee_exposure_detail.html'
    context_object_name = 'employee_exposure'

    def get_queryset(self):
        return EmployeeExposure.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'employee_health_profile__employee__department',
            'employee_health_profile__employee__plant',
            'employee_health_profile__employee__zone',
            'employee_health_profile__employee__location',
            'employee_health_profile__employee__sublocation',
            'exposure_type',
            'health_surveillance',
            'created_by'
        ).all()



# =============================================
# EmployeeHealthSurveillanceDataView - Returns active health surveillance programs for a selected employee
# =============================================
class EmployeeHealthSurveillanceDataView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        employee_health_profile_id = request.GET.get(
            'employee_health_profile_id'
        )

        if not employee_health_profile_id:
            return JsonResponse({
                'success': True,
                'surveillance': []
            })

        surveillance_records = HealthSurveillance.objects.filter(
            employee_health_profile_id=employee_health_profile_id,
            is_active=True,
            status='ACTIVE'
        ).select_related(
            'exposure_type'
        ).order_by(
            '-start_date',
            '-id'
        )

        data = []

        for surveillance in surveillance_records:
            data.append({
                'id': surveillance.id,
                'name': surveillance.surveillance_name,
                'exposure_type': surveillance.exposure_type.name,
                'frequency': surveillance.get_surveillance_frequency_display(),
                'start_date': surveillance.start_date.strftime('%d %b %Y'),
                'next_due_date': (
                    surveillance.next_due_date.strftime('%d %b %Y')
                    if surveillance.next_due_date
                    else ''
                ),
            })

        return JsonResponse({
            'success': True,
            'surveillance': data
        })

    

class EmployeeExposureDashboardView(LoginRequiredMixin,TemplateView):
    template_name='occupational_health/management/employee_exposure_dashboard.html'

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)
        context['total_exposures']=EmployeeExposure.objects.count()
        context['active_exposures']=EmployeeExposure.objects.filter(status='ACTIVE',is_active=True).count()
        context['inactive_exposures']=EmployeeExposure.objects.filter(status='INACTIVE').count()
        context['closed_exposures']=EmployeeExposure.objects.filter(status='CLOSED').count()
        context['surveillance_required']=EmployeeExposure.objects.filter(health_surveillance_required=True).count()
        context['surveillance_linked']=EmployeeExposure.objects.filter(health_surveillance_required=True,health_surveillance__isnull=False).count()
        context['surveillance_missing']=EmployeeExposure.objects.filter(health_surveillance_required=True,health_surveillance__isnull=True).count()
        context['active_without_surveillance']=EmployeeExposure.objects.filter(status='ACTIVE',is_active=True,health_surveillance_required=True,health_surveillance__isnull=True).count()
        context['exposure_types']=ExposureType.objects.filter(is_active=True).annotate(
            exposure_count=models.Count('employee_exposures')
        ).order_by('-exposure_count','name')
        context['recent_exposures']=EmployeeExposure.objects.select_related(
            'employee_health_profile__employee',
            'exposure_type'
        ).order_by('-exposure_start_date','-id')[:10]
        context['search_query']=self.request.GET.get('q','').strip()
        return context





class MedicalFollowUpListView(LoginRequiredMixin,ListView):
    model=MedicalFollowUp
    template_name='occupational_health/management/medical_follow_up_list.html'
    context_object_name='medical_follow_ups'
    paginate_by=15

    def get_queryset(self):
        qs=MedicalFollowUp.objects.select_related(
            'employee_health_profile__employee',
            'medical_examination',
            'medical_test_result',
            'fitness_assessment',
            'health_surveillance',
            'exposure',
            'assigned_medical_professional',
            'medical_facility',
            'created_by'
        ).all()
        q=self.request.GET.get('q','').strip()
        if q:
            qs=qs.filter(
                models.Q(employee_health_profile__employee__employee_id__icontains=q) |
                models.Q(employee_health_profile__employee__first_name__icontains=q) |
                models.Q(employee_health_profile__employee__last_name__icontains=q) |
                models.Q(employee_health_profile__employee__username__icontains=q) |
                models.Q(title__icontains=q) |
                models.Q(follow_up_type__icontains=q) |
                models.Q(priority__icontains=q) |
                models.Q(status__icontains=q)
            )
        return qs.order_by('-scheduled_date','-id')

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)
        from django.utils import timezone
        today=timezone.localdate()
        context['total_follow_ups']=MedicalFollowUp.objects.count()
        context['pending_follow_ups']=MedicalFollowUp.objects.filter(status='PENDING',scheduled_date__gte=today).count()
        context['scheduled_follow_ups']=MedicalFollowUp.objects.filter(status='SCHEDULED',scheduled_date__gte=today).count()
        context['completed_follow_ups']=MedicalFollowUp.objects.filter(status='COMPLETED').count()
        context['overdue_follow_ups']=MedicalFollowUp.objects.filter(
            models.Q(status='OVERDUE') |
            (models.Q(scheduled_date__lt=today) & ~models.Q(status__in=['COMPLETED','CANCELLED']))
        ).distinct().count()
        context['search_query']=self.request.GET.get('q','').strip()
        return context


class MedicalFollowUpCreateView(LoginRequiredMixin,CreateView):
    model=MedicalFollowUp
    form_class=MedicalFollowUpForm
    template_name='occupational_health/management/medical_follow_up_form.html'
    success_url=reverse_lazy('occupational_health:medical_follow_up_list')

    def form_valid(self,form):
        form.instance.created_by=self.request.user
        messages.success(self.request,f'Medical Follow-up "{form.instance.title}" was created successfully.')
        return super().form_valid(form)


class MedicalFollowUpUpdateView(LoginRequiredMixin,UpdateView):
    model=MedicalFollowUp
    form_class=MedicalFollowUpForm
    template_name='occupational_health/management/medical_follow_up_form.html'
    success_url=reverse_lazy('occupational_health:medical_follow_up_list')

    def form_valid(self,form):
        messages.success(self.request,f'Medical Follow-up "{form.instance.title}" was updated successfully.')
        return super().form_valid(form)


class MedicalFollowUpDetailView(LoginRequiredMixin,DetailView):
    model=MedicalFollowUp
    template_name='occupational_health/management/medical_follow_up_detail.html'
    context_object_name='medical_follow_up'

    def get_queryset(self):
        return MedicalFollowUp.objects.select_related(
            'employee_health_profile__employee',
            'employee_health_profile__employee__department',
            'employee_health_profile__employee__plant',
            'employee_health_profile__employee__zone',
            'employee_health_profile__employee__location',
            'employee_health_profile__employee__sublocation',
            'medical_examination',
            'medical_test_result',
            'fitness_assessment',
            'health_surveillance',
            'exposure',
            'assigned_medical_professional',
            'medical_facility',
            'created_by'
        ).all()



class MedicalFollowUpEmployeeRecordsDataView(LoginRequiredMixin,View):
    def get(self,request,*args,**kwargs):
        employee_health_profile_id=request.GET.get('employee_health_profile_id')
        if not employee_health_profile_id:
            return JsonResponse({
                'success':True,
                'examinations':[],
                'test_results':[],
                'fitness_assessments':[],
                'surveillance':[],
                'exposures':[]
            })
        examinations=MedicalExamination.objects.filter(
            employee_health_profile_id=employee_health_profile_id
        ).select_related('examination_type').order_by('-examination_date','-id')
        test_results=MedicalTestResult.objects.filter(
            medical_examination__employee_health_profile_id=employee_health_profile_id
        ).select_related('medical_test','medical_examination').order_by('-test_date','-id')
        fitness_assessments=FitnessToWork.objects.filter(
            employee_health_profile_id=employee_health_profile_id
        ).order_by('-assessment_date','-id')
        surveillance=HealthSurveillance.objects.filter(
            employee_health_profile_id=employee_health_profile_id,
            is_active=True
        ).select_related('exposure_type').order_by('-start_date','-id')
        exposures=EmployeeExposure.objects.filter(
            employee_health_profile_id=employee_health_profile_id
        ).select_related('exposure_type').order_by('-exposure_start_date','-id')
        examination_data=[]
        for item in examinations:
            examination_data.append({
                'id':item.id,
                'label':f'{item.examination_type.name} - {item.examination_date.strftime("%d %b %Y")}'
            })
        test_result_data=[]
        for item in test_results:
            test_result_data.append({
                'id':item.id,
                'label':f'{item.medical_test.name} - {item.test_date.strftime("%d %b %Y")}'
            })
        fitness_data=[]
        for item in fitness_assessments:
            fitness_data.append({
                'id':item.id,
                'label':f'{item.get_fitness_status_display()} - {item.assessment_date.strftime("%d %b %Y")}'
            })
        surveillance_data=[]
        for item in surveillance:
            surveillance_data.append({
                'id':item.id,
                'label':f'{item.surveillance_name} - {item.exposure_type.name}'
            })
        exposure_data=[]
        for item in exposures:
            exposure_data.append({
                'id':item.id,
                'label':f'{item.exposure_name} - {item.exposure_type.name}'
            })
        return JsonResponse({
            'success':True,
            'examinations':examination_data,
            'test_results':test_result_data,
            'fitness_assessments':fitness_data,
            'surveillance':surveillance_data,
            'exposures':exposure_data
        })




class MedicalFollowUpDashboardView(LoginRequiredMixin,TemplateView):
    template_name='occupational_health/management/medical_follow_up_dashboard.html'

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)
        from django.utils import timezone
        from django.db.models import Count,Q
        today=timezone.localdate()
        due_soon_date=today+timezone.timedelta(days=7)
        active_qs=MedicalFollowUp.objects.filter(is_active=True).exclude(status='CANCELLED')
        context['total_follow_ups']=MedicalFollowUp.objects.count()
        context['pending_follow_ups']=active_qs.filter(
            status='PENDING',
            scheduled_date__gte=today
        ).count()
        context['scheduled_follow_ups']=active_qs.filter(
            status='SCHEDULED',
            scheduled_date__gte=today
        ).count()
        context['in_progress_follow_ups']=active_qs.filter(
            status='IN_PROGRESS'
        ).count()
        context['completed_follow_ups']=MedicalFollowUp.objects.filter(
            status='COMPLETED'
        ).count()
        context['overdue_follow_ups']=active_qs.filter(
            scheduled_date__lt=today
        ).count()
        context['due_today_follow_ups']=active_qs.filter(
            scheduled_date=today
        ).count()
        context['due_soon_follow_ups']=active_qs.filter(
            scheduled_date__gt=today,
            scheduled_date__lte=due_soon_date
        ).count()
        context['high_priority_follow_ups']=active_qs.filter(
            priority='HIGH'
        ).count()
        context['urgent_follow_ups']=active_qs.filter(
            priority='URGENT'
        ).count()
        context['follow_up_types']=MedicalFollowUp.objects.filter(
            is_active=True
        ).exclude(
            status='CANCELLED'
        ).values(
            'follow_up_type'
        ).annotate(
            total=Count('id')
        ).order_by('-total')
        context['priority_summary']=MedicalFollowUp.objects.filter(
            is_active=True
        ).exclude(
            status='CANCELLED'
        ).values(
            'priority'
        ).annotate(
            total=Count('id')
        ).order_by('-total')
        context['recent_follow_ups']=MedicalFollowUp.objects.select_related(
            'employee_health_profile__employee',
            'assigned_medical_professional',
            'medical_facility'
        ).filter(
            is_active=True
        ).order_by('-created_at','-id')[:10]
        context['upcoming_follow_ups']=MedicalFollowUp.objects.select_related(
            'employee_health_profile__employee',
            'assigned_medical_professional',
            'medical_facility'
        ).filter(
            is_active=True,
            scheduled_date__gte=today
        ).exclude(
            status='CANCELLED'
        ).order_by('scheduled_date','-id')[:10]
        context['overdue_records']=MedicalFollowUp.objects.select_related(
            'employee_health_profile__employee',
            'assigned_medical_professional'
        ).filter(
            is_active=True,
            scheduled_date__lt=today
        ).exclude(
            status__in=['COMPLETED','CANCELLED']
        ).order_by('scheduled_date','-id')[:10]
        return context


    

class EmployeeVaccinationListView(LoginRequiredMixin,ListView):
    model=EmployeeVaccination
    template_name='occupational_health/management/employee_vaccination_list.html'
    context_object_name='vaccinations'
    paginate_by=15
    def get_queryset(self):
        qs=EmployeeVaccination.objects.select_related(
            'employee_health_profile__employee',
            'vaccination',
            'medical_professional',
            'medical_facility',
            'created_by'
        )
        q=self.request.GET.get('q','').strip()
        if q:
            qs=qs.filter(
                models.Q(employee_health_profile__employee__employee_id__icontains=q) |
                models.Q(employee_health_profile__employee__first_name__icontains=q) |
                models.Q(employee_health_profile__employee__last_name__icontains=q) |
                models.Q(employee_health_profile__employee__username__icontains=q) |
                models.Q(vaccination__name__icontains=q) |
                models.Q(batch_number__icontains=q) |
                models.Q(certificate_number__icontains=q)
            )
        return qs.order_by('-vaccination_date','-id')
    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)
        context['total_vaccinations']=EmployeeVaccination.objects.count()
        context['completed_doses']=EmployeeVaccination.objects.filter(dose_status='COMPLETED').count()
        context['active_vaccinations']=EmployeeVaccination.objects.filter(vaccination_status='ACTIVE').count()
        context['expired_vaccinations']=EmployeeVaccination.objects.filter(vaccination_status='EXPIRED').count()
        context['scheduled_doses']=EmployeeVaccination.objects.filter(dose_status='SCHEDULED').count()
        context['search_query']=self.request.GET.get('q','').strip()
        return context

class EmployeeVaccinationCreateView(LoginRequiredMixin,CreateView):
    model=EmployeeVaccination
    form_class=EmployeeVaccinationForm
    template_name='occupational_health/management/employee_vaccination_form.html'
    success_url=reverse_lazy('occupational_health:employee_vaccination_list')
    def form_valid(self,form):
        form.instance.created_by=self.request.user
        messages.success(self.request,f'Employee vaccination record was created successfully.')
        return super().form_valid(form)

class EmployeeVaccinationUpdateView(LoginRequiredMixin,UpdateView):
    model=EmployeeVaccination
    form_class=EmployeeVaccinationForm
    template_name='occupational_health/management/employee_vaccination_form.html'
    success_url=reverse_lazy('occupational_health:employee_vaccination_list')
    def form_valid(self,form):
        messages.success(self.request,f'Employee vaccination record was updated successfully.')
        return super().form_valid(form)

class EmployeeVaccinationDetailView(LoginRequiredMixin,DetailView):
    model=EmployeeVaccination
    template_name='occupational_health/management/employee_vaccination_detail.html'
    context_object_name='vaccination_record'
    def get_queryset(self):
        return EmployeeVaccination.objects.select_related(
            'employee_health_profile__employee',
            'vaccination',
            'medical_professional',
            'medical_facility',
            'created_by'
        )




class EmployeeVaccinationDashboardView(LoginRequiredMixin,TemplateView):
    template_name='occupational_health/management/employee_vaccination_dashboard.html'
    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)
        from django.utils import timezone
        from django.db.models import Count
        from datetime import timedelta
        today=timezone.localdate()
        due_soon_date=today+timedelta(days=7)
        active_qs=EmployeeVaccination.objects.exclude(vaccination_status='CANCELLED')
        context['total_vaccinations']=EmployeeVaccination.objects.count()
        context['completed_doses']=active_qs.filter(dose_status='COMPLETED').count()
        context['scheduled_doses']=active_qs.filter(dose_status='SCHEDULED').count()
        context['partial_doses']=active_qs.filter(dose_status='PARTIAL').count()
        context['missed_doses']=active_qs.filter(dose_status='MISSED').count()
        context['active_vaccinations']=active_qs.filter(vaccination_status='ACTIVE').count()
        context['completed_vaccinations']=active_qs.filter(vaccination_status='COMPLETED').count()
        context['expired_vaccinations']=active_qs.filter(vaccination_status='EXPIRED').count()
        context['cancelled_vaccinations']=EmployeeVaccination.objects.filter(vaccination_status='CANCELLED').count()
        context['due_today']=active_qs.filter(next_due_date=today).count()
        context['due_soon']=active_qs.filter(
            next_due_date__gt=today,
            next_due_date__lte=due_soon_date
        ).count()
        context['overdue']=active_qs.filter(
            next_due_date__lt=today
        ).exclude(
            dose_status='COMPLETED'
        ).count()
        context['adverse_reactions']=active_qs.filter(adverse_reaction=True).count()
        context['vaccination_summary']=active_qs.values(
            'vaccination__name'
        ).annotate(
            total=Count('id')
        ).order_by('-total','vaccination__name')
        context['dose_status_summary']=active_qs.values(
            'dose_status'
        ).annotate(
            total=Count('id')
        ).order_by('-total')
        context['status_summary']=active_qs.values(
            'vaccination_status'
        ).annotate(
            total=Count('id')
        ).order_by('-total')
        context['recent_vaccinations']=EmployeeVaccination.objects.select_related(
            'employee_health_profile__employee',
            'vaccination',
            'medical_professional',
            'medical_facility'
        ).exclude(
            vaccination_status='CANCELLED'
        ).order_by(
            '-vaccination_date',
            '-id'
        )[:10]
        context['upcoming_vaccinations']=EmployeeVaccination.objects.select_related(
            'employee_health_profile__employee',
            'vaccination'
        ).filter(
            next_due_date__gte=today
        ).exclude(
            vaccination_status='CANCELLED'
        ).order_by(
            'next_due_date',
            '-id'
        )[:10]
        context['overdue_vaccinations']=EmployeeVaccination.objects.select_related(
            'employee_health_profile__employee',
            'vaccination'
        ).filter(
            next_due_date__lt=today
        ).exclude(
            vaccination_status__in=['COMPLETED','CANCELLED']
        ).order_by(
            'next_due_date',
            '-id'
        )[:10]
        return context

    


class EmployeeOccupationalDiseaseListView(LoginRequiredMixin,ListView):
    model=EmployeeOccupationalDisease
    template_name='occupational_health/management/employee_occupational_disease_list.html'
    context_object_name='diseases'
    paginate_by=15

    def get_queryset(self):
        qs=EmployeeOccupationalDisease.objects.select_related(
            'employee_health_profile__employee',
            'health_condition',
            'exposure',
            'medical_professional',
            'medical_facility',
            'created_by'
        )
        q=self.request.GET.get('q','').strip()
        if q:
            qs=qs.filter(
                models.Q(employee_health_profile__employee__employee_id__icontains=q) |
                models.Q(employee_health_profile__employee__first_name__icontains=q) |
                models.Q(employee_health_profile__employee__last_name__icontains=q) |
                models.Q(employee_health_profile__employee__username__icontains=q) |
                models.Q(health_condition__name__icontains=q) |
                models.Q(work_area__icontains=q) |
                models.Q(job_role__icontains=q)
            )
        return qs.order_by('-reported_date','-id')

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)
        context['total_diseases']=EmployeeOccupationalDisease.objects.count()
        context['suspected_diseases']=EmployeeOccupationalDisease.objects.filter(
            disease_status='SUSPECTED'
        ).count()
        context['confirmed_diseases']=EmployeeOccupationalDisease.objects.filter(
            disease_status='CONFIRMED'
        ).count()
        context['under_investigation']=EmployeeOccupationalDisease.objects.filter(
            status='UNDER_INVESTIGATION'
        ).count()
        context['follow_up_required']=EmployeeOccupationalDisease.objects.filter(
            follow_up_required=True
        ).count()
        context['search_query']=self.request.GET.get('q','').strip()
        return context


class EmployeeOccupationalDiseaseCreateView(LoginRequiredMixin,CreateView):
    model=EmployeeOccupationalDisease
    form_class=EmployeeOccupationalDiseaseForm
    template_name='occupational_health/management/employee_occupational_disease_form.html'
    success_url=reverse_lazy('occupational_health:employee_occupational_disease_list')

    def form_valid(self,form):
        form.instance.created_by=self.request.user
        messages.success(
            self.request,
            'Occupational disease record was created successfully.'
        )
        return super().form_valid(form)


class EmployeeOccupationalDiseaseUpdateView(LoginRequiredMixin,UpdateView):
    model=EmployeeOccupationalDisease
    form_class=EmployeeOccupationalDiseaseForm
    template_name='occupational_health/management/employee_occupational_disease_form.html'
    success_url=reverse_lazy('occupational_health:employee_occupational_disease_list')

    def form_valid(self,form):
        messages.success(
            self.request,
            'Occupational disease record was updated successfully.'
        )
        return super().form_valid(form)


class EmployeeOccupationalDiseaseDetailView(LoginRequiredMixin,DetailView):
    model=EmployeeOccupationalDisease
    template_name='occupational_health/management/employee_occupational_disease_detail.html'
    context_object_name='disease_record'

    def get_queryset(self):
        return EmployeeOccupationalDisease.objects.select_related(
            'employee_health_profile__employee',
            'health_condition',
            'exposure',
            'medical_professional',
            'medical_facility',
            'created_by'
        )



class EmployeeOccupationalDiseaseDashboardView(LoginRequiredMixin,TemplateView):
    template_name='occupational_health/management/employee_occupational_disease_dashboard.html'

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)
        from django.utils import timezone
        from django.db.models import Count

        today=timezone.localdate()

        qs=EmployeeOccupationalDisease.objects.select_related(
            'employee_health_profile__employee',
            'health_condition',
            'exposure',
            'medical_professional',
            'medical_facility'
        )

        context['total_diseases']=qs.count()
        context['suspected_diseases']=qs.filter(disease_status='SUSPECTED').count()
        context['confirmed_diseases']=qs.filter(disease_status='CONFIRMED').count()
        context['under_review']=qs.filter(disease_status='UNDER_REVIEW').count()
        context['under_investigation']=qs.filter(status='UNDER_INVESTIGATION').count()
        context['under_treatment']=qs.filter(status='TREATMENT').count()
        context['follow_up_required']=qs.filter(follow_up_required=True).count()
        context['exposure_related']=qs.filter(exposure_related=True).count()
        context['investigation_required']=qs.filter(investigation_required=True).count()

        context['mild_cases']=qs.filter(severity='MILD').count()
        context['moderate_cases']=qs.filter(severity='MODERATE').count()
        context['severe_cases']=qs.filter(severity='SEVERE').count()
        context['critical_cases']=qs.filter(severity='CRITICAL').count()

        context['upcoming_follow_ups']=qs.filter(
            follow_up_required=True,
            follow_up_date__gte=today
        ).order_by('follow_up_date','-id')[:10]

        context['overdue_follow_ups']=qs.filter(
            follow_up_required=True,
            follow_up_date__lt=today
        ).order_by('follow_up_date','-id')[:10]

        context['recent_diseases']=qs.order_by(
            '-reported_date','-id'
        )[:10]

        context['condition_summary']=qs.values(
            'health_condition__name'
        ).annotate(
            total=Count('id')
        ).order_by('-total','health_condition__name')

        context['severity_summary']=qs.values(
            'severity'
        ).annotate(
            total=Count('id')
        ).order_by('-total')

        context['disease_status_summary']=qs.values(
            'disease_status'
        ).annotate(
            total=Count('id')
        ).order_by('-total')

        context['record_status_summary']=qs.values(
            'status'
        ).annotate(
            total=Count('id')
        ).order_by('-total')

        return context





class HealthIncidentListView(LoginRequiredMixin,ListView):
    model=HealthIncident
    template_name='occupational_health/management/health_incident_list.html'
    context_object_name='incidents'
    paginate_by=15

    def get_queryset(self):
        qs=HealthIncident.objects.select_related(
            'employee_health_profile__employee',
            'occupational_disease',
            'exposure',
            'medical_professional',
            'medical_facility',
            'created_by'
        )

        q=self.request.GET.get('q','').strip()

        if q:
            qs=qs.filter(
                models.Q(employee_health_profile__employee__employee_id__icontains=q) |
                models.Q(employee_health_profile__employee__first_name__icontains=q) |
                models.Q(employee_health_profile__employee__last_name__icontains=q) |
                models.Q(employee_health_profile__employee__username__icontains=q) |
                models.Q(incident_type__icontains=q) |
                models.Q(incident_location__icontains=q) |
                models.Q(work_area__icontains=q) |
                models.Q(job_role__icontains=q) |
                models.Q(incident_description__icontains=q)
            )

        return qs.order_by('-incident_date','-id')

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)

        context['total_incidents']=HealthIncident.objects.count()
        context['reported_incidents']=HealthIncident.objects.filter(status='REPORTED').count()
        context['under_review']=HealthIncident.objects.filter(status='UNDER_REVIEW').count()
        context['under_investigation']=HealthIncident.objects.filter(status='UNDER_INVESTIGATION').count()
        context['follow_up_required']=HealthIncident.objects.filter(follow_up_required=True).count()

        context['search_query']=self.request.GET.get('q','').strip()

        return context


class HealthIncidentCreateView(LoginRequiredMixin,CreateView):
    model=HealthIncident
    form_class=HealthIncidentForm
    template_name='occupational_health/management/health_incident_form.html'
    success_url=reverse_lazy('occupational_health:health_incident_list')

    def form_valid(self,form):
        form.instance.created_by=self.request.user

        messages.success(
            self.request,
            'Health incident record was created successfully.'
        )

        return super().form_valid(form)


class HealthIncidentUpdateView(LoginRequiredMixin,UpdateView):
    model=HealthIncident
    form_class=HealthIncidentForm
    template_name='occupational_health/management/health_incident_form.html'
    success_url=reverse_lazy('occupational_health:health_incident_list')

    def form_valid(self,form):
        messages.success(
            self.request,
            'Health incident record was updated successfully.'
        )

        return super().form_valid(form)


class HealthIncidentDetailView(LoginRequiredMixin,DetailView):
    model=HealthIncident
    template_name='occupational_health/management/health_incident_detail.html'
    context_object_name='incident'

    def get_queryset(self):
        return HealthIncident.objects.select_related(
            'employee_health_profile__employee',
            'occupational_disease',
            'exposure',
            'medical_professional',
            'medical_facility',
            'created_by'
        )



class HealthIncidentDashboardView(LoginRequiredMixin,TemplateView):
    template_name='occupational_health/management/health_incident_dashboard.html'

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)

        from django.utils import timezone
        from django.db.models import Count
        from datetime import timedelta

        today=timezone.localdate()
        month_start=today.replace(day=1)

        qs=HealthIncident.objects.select_related(
            'employee_health_profile__employee',
            'occupational_disease',
            'exposure',
            'medical_professional',
            'medical_facility'
        )

        context['total_incidents']=qs.count()

        context['reported_incidents']=qs.filter(
            status='REPORTED'
        ).count()

        context['under_review']=qs.filter(
            status='UNDER_REVIEW'
        ).count()

        context['under_investigation']=qs.filter(
            status='UNDER_INVESTIGATION'
        ).count()

        context['treated_incidents']=qs.filter(
            status='TREATED'
        ).count()

        context['closed_incidents']=qs.filter(
            status='CLOSED'
        ).count()

        context['follow_up_required']=qs.filter(
            follow_up_required=True
        ).count()

        context['investigation_required']=qs.filter(
            investigation_required=True
        ).count()

        context['hospitalization_required']=qs.filter(
            hospitalization_required=True
        ).count()

        context['work_restrictions']=qs.filter(
            work_restriction_required=True
        ).count()

        context['critical_incidents']=qs.filter(
            severity='CRITICAL'
        ).count()

        context['serious_incidents']=qs.filter(
            severity='SERIOUS'
        ).count()

        context['moderate_incidents']=qs.filter(
            severity='MODERATE'
        ).count()

        context['minor_incidents']=qs.filter(
            severity='MINOR'
        ).count()

        context['current_month_incidents']=qs.filter(
            incident_date__gte=month_start,
            incident_date__lte=today
        ).count()

        context['upcoming_follow_ups']=qs.filter(
            follow_up_required=True,
            follow_up_date__gte=today
        ).order_by(
            'follow_up_date',
            '-id'
        )[:10]

        context['overdue_follow_ups']=qs.filter(
            follow_up_required=True,
            follow_up_date__lt=today
        ).order_by(
            'follow_up_date',
            '-id'
        )[:10]

        context['recent_incidents']=qs.order_by(
            '-incident_date',
            '-id'
        )[:10]

        context['incident_type_summary']=qs.values(
            'incident_type'
        ).annotate(
            total=Count('id')
        ).order_by(
            '-total'
        )

        context['severity_summary']=qs.values(
            'severity'
        ).annotate(
            total=Count('id')
        ).order_by(
            '-total'
        )

        context['status_summary']=qs.values(
            'status'
        ).annotate(
            total=Count('id')
        ).order_by(
            '-total'
        )

        context['monthly_summary']=qs.filter(
            incident_date__year=today.year
        ).values(
            'incident_date__month'
        ).annotate(
            total=Count('id')
        ).order_by(
            'incident_date__month'
        )

        return context




class ReturnToWorkListView(LoginRequiredMixin,ListView):
    model=ReturnToWork
    template_name='occupational_health/management/return_to_work_list.html'
    context_object_name='return_to_work_records'
    paginate_by=15

    def get_queryset(self):
        qs=ReturnToWork.objects.select_related(
            'employee_health_profile__employee',
            'medical_examination',
            'fitness_assessment',
            'health_incident',
            'occupational_disease',
            'medical_professional',
            'medical_facility',
            'created_by'
        ).prefetch_related(
            'work_restrictions'
        )

        q=self.request.GET.get('q','').strip()

        if q:
            qs=qs.filter(
                models.Q(
                    employee_health_profile__employee__employee_id__icontains=q
                ) |
                models.Q(
                    employee_health_profile__employee__first_name__icontains=q
                ) |
                models.Q(
                    employee_health_profile__employee__last_name__icontains=q
                ) |
                models.Q(
                    employee_health_profile__employee__username__icontains=q
                ) |
                models.Q(
                    return_reason__icontains=q
                ) |
                models.Q(
                    job_role__icontains=q
                ) |
                models.Q(
                    work_area__icontains=q
                ) |
                models.Q(
                    reason_details__icontains=q
                )
            )

        return qs.order_by(
            '-expected_return_date',
            '-id'
        )

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)

        context['total_return_to_work']=ReturnToWork.objects.count()

        context['pending_records']=ReturnToWork.objects.filter(
            status='PENDING'
        ).count()

        context['medical_assessment']=ReturnToWork.objects.filter(
            status='MEDICAL_ASSESSMENT'
        ).count()

        context['approved_records']=ReturnToWork.objects.filter(
            status='APPROVED'
        ).count()

        context['restricted_records']=ReturnToWork.objects.filter(
            status='APPROVED_WITH_RESTRICTIONS'
        ).count()

        context['not_approved_records']=ReturnToWork.objects.filter(
            status='NOT_APPROVED'
        ).count()

        context['completed_records']=ReturnToWork.objects.filter(
            status='COMPLETED'
        ).count()

        context['follow_up_required']=ReturnToWork.objects.filter(
            follow_up_required=True
        ).count()

        context['search_query']=self.request.GET.get(
            'q',
            ''
        ).strip()

        return context


class ReturnToWorkCreateView(LoginRequiredMixin,CreateView):
    model=ReturnToWork
    form_class=ReturnToWorkForm
    template_name='occupational_health/management/return_to_work_form.html'
    success_url=reverse_lazy(
        'occupational_health:return_to_work_list'
    )

    def form_valid(self,form):
        form.instance.created_by=self.request.user

        messages.success(
            self.request,
            'Return to Work record was created successfully.'
        )

        return super().form_valid(form)


class ReturnToWorkUpdateView(LoginRequiredMixin,UpdateView):
    model=ReturnToWork
    form_class=ReturnToWorkForm
    template_name='occupational_health/management/return_to_work_form.html'
    success_url=reverse_lazy(
        'occupational_health:return_to_work_list'
    )

    def form_valid(self,form):
        messages.success(
            self.request,
            'Return to Work record was updated successfully.'
        )

        return super().form_valid(form)


class ReturnToWorkDetailView(LoginRequiredMixin,DetailView):
    model=ReturnToWork
    template_name='occupational_health/management/return_to_work_detail.html'
    context_object_name='return_to_work'

    def get_queryset(self):
        return ReturnToWork.objects.select_related(
            'employee_health_profile__employee',
            'medical_examination',
            'fitness_assessment',
            'health_incident',
            'occupational_disease',
            'medical_professional',
            'medical_facility',
            'created_by'
        ).prefetch_related(
            'work_restrictions'
        )



class ReturnToWorkDashboardView(LoginRequiredMixin,TemplateView):
    template_name='occupational_health/management/return_to_work_dashboard.html'

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)
        today=timezone.localdate()

        qs=ReturnToWork.objects.select_related(
            'employee_health_profile__employee',
            'medical_examination',
            'fitness_assessment',
            'health_incident',
            'occupational_disease',
            'medical_professional',
            'medical_facility'
        ).prefetch_related('work_restrictions')

        context['total_records']=qs.count()
        context['pending_records']=qs.filter(status='PENDING').count()
        context['medical_assessment_records']=qs.filter(status='MEDICAL_ASSESSMENT').count()
        context['approved_records']=qs.filter(status='APPROVED').count()
        context['restricted_records']=qs.filter(status='APPROVED_WITH_RESTRICTIONS').count()
        context['not_approved_records']=qs.filter(status='NOT_APPROVED').count()
        context['completed_records']=qs.filter(status='COMPLETED').count()
        context['cancelled_records']=qs.filter(status='CANCELLED').count()

        context['follow_up_required']=qs.filter(
            follow_up_required=True
        ).count()

        context['overdue_returns']=qs.filter(
            expected_return_date__lt=today
        ).exclude(
            status__in=['COMPLETED','CANCELLED']
        ).count()

        context['upcoming_returns']=qs.filter(
            expected_return_date__gte=today
        ).exclude(
            status__in=['COMPLETED','CANCELLED']
        ).order_by(
            'expected_return_date'
        )[:10]

        context['overdue_return_records']=qs.filter(
            expected_return_date__lt=today
        ).exclude(
            status__in=['COMPLETED','CANCELLED']
        ).order_by(
            'expected_return_date'
        )[:10]

        context['follow_up_records']=qs.filter(
            follow_up_required=True,
            follow_up_date__isnull=False
        ).exclude(
            status__in=['COMPLETED','CANCELLED']
        ).order_by(
            'follow_up_date'
        )[:10]

        context['reason_summary']=qs.values(
            'return_reason'
        ).annotate(
            total=Count('id')
        ).order_by('-total')

        context['fitness_summary']=qs.exclude(
            fitness_status=''
        ).values(
            'fitness_status'
        ).annotate(
            total=Count('id')
        ).order_by('-total')

        return context
    




class MedicalRecordListView(LoginRequiredMixin,ListView):
    model=MedicalRecord
    template_name='occupational_health/management/medical_record_list.html'
    context_object_name='medical_records'
    paginate_by=15

    def get_queryset(self):
        qs=MedicalRecord.objects.select_related(
            'employee_health_profile__employee',
            'medical_examination',
            'medical_test_result',
            'fitness_assessment',
            'vaccination',
            'occupational_disease',
            'health_incident',
            'return_to_work',
            'medical_professional',
            'medical_facility',
            'created_by'
        )

        search_query=self.request.GET.get('q','').strip()

        if search_query:
            qs=qs.filter(
                Q(record_title__icontains=search_query) |
                Q(document_number__icontains=search_query) |
                Q(employee_health_profile__employee__employee_id__icontains=search_query) |
                Q(employee_health_profile__employee__first_name__icontains=search_query) |
                Q(employee_health_profile__employee__last_name__icontains=search_query) |
                Q(employee_health_profile__employee__username__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        return qs.order_by('-record_date','-id')

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)

        qs=MedicalRecord.objects.all()

        context['total_records']=qs.count()

        context['active_records']=qs.filter(
            record_status='ACTIVE'
        ).count()

        context['archived_records']=qs.filter(
            record_status='ARCHIVED'
        ).count()

        context['cancelled_records']=qs.filter(
            record_status='CANCELLED'
        ).count()

        context['confidential_records']=qs.filter(
            confidential=True
        ).count()

        context['search_query']=self.request.GET.get('q','').strip()

        return context
    




class MedicalRecordCreateView(LoginRequiredMixin,CreateView):
    model=MedicalRecord
    form_class=MedicalRecordForm
    template_name='occupational_health/management/medical_record_form.html'
    success_url=reverse_lazy('occupational_health:medical_record_list')

    def form_valid(self,form):
        form.instance.created_by=self.request.user

        messages.success(
            self.request,
            'Medical Record was created successfully.'
        )

        return super().form_valid(form)
    



class MedicalRecordUpdateView(LoginRequiredMixin,UpdateView):
    model=MedicalRecord
    form_class=MedicalRecordForm
    template_name='occupational_health/management/medical_record_form.html'
    success_url=reverse_lazy('occupational_health:medical_record_list')

    def form_valid(self,form):
        messages.success(
            self.request,
            'Medical Record was updated successfully.'
        )

        return super().form_valid(form)




class MedicalRecordDetailView(LoginRequiredMixin, DetailView):
    model = MedicalRecord
    template_name = 'occupational_health/management/medical_record_detail.html'
    context_object_name = 'medical_record'

    def get_queryset(self):
        return MedicalRecord.objects.select_related(
            'employee_health_profile__employee',
            'medical_examination',
            'medical_test_result',
            'fitness_assessment',
            'vaccination',
            'occupational_disease',
            'health_incident',
            'return_to_work',
            'medical_professional',
            'medical_facility',
            'created_by'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = timezone.localdate()
        return context
    



class MedicalRecordDashboardView(LoginRequiredMixin,TemplateView):
    template_name='occupational_health/management/medical_record_dashboard.html'

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)

        today=timezone.localdate()

        qs=MedicalRecord.objects.select_related(
            'employee_health_profile__employee',
            'medical_examination',
            'medical_test_result',
            'fitness_assessment',
            'vaccination',
            'occupational_disease',
            'health_incident',
            'return_to_work',
            'medical_professional',
            'medical_facility',
            'created_by'
        )

        active_qs=qs.filter(record_status='ACTIVE')

        context['today']=today

        context['total_records']=qs.count()

        context['active_records']=active_qs.count()

        context['archived_records']=qs.filter(
            record_status='ARCHIVED'
        ).count()

        context['cancelled_records']=qs.filter(
            record_status='CANCELLED'
        ).count()

        context['confidential_records']=qs.filter(
            confidential=True
        ).count()

        context['expired_records']=active_qs.filter(
            expiry_date__lt=today
        ).count()

        context['expiring_soon_records']=active_qs.filter(
            expiry_date__gte=today,
            expiry_date__lte=today+timedelta(days=30)
        ).count()

        context['records_without_document']=qs.filter(
            document=''
        ).count()

        context['record_type_summary']=list(
            qs.values(
                'record_type'
            ).annotate(
                total=Count('id')
            ).order_by('-total')
        )

        context['recent_records']=qs.order_by(
            '-record_date',
            '-id'
        )[:10]

        context['expiring_records']=active_qs.filter(
            expiry_date__gte=today,
            expiry_date__lte=today+timedelta(days=30)
        ).order_by(
            'expiry_date',
            '-id'
        )[:10]

        context['expired_record_list']=active_qs.filter(
            expiry_date__lt=today
        ).order_by(
            'expiry_date',
            '-id'
        )[:10]

        return context





class HealthCampListView(LoginRequiredMixin,ListView):
    model=HealthCamp
    template_name='occupational_health/management/health_camp_list.html'
    context_object_name='health_camps'
    paginate_by=15

    def get_queryset(self):
        queryset=HealthCamp.objects.select_related(
            'plant',
            'medical_facility',
            'lead_medical_professional',
            'created_by'
        ).order_by('-camp_date','-id')

        search_query=self.request.GET.get('q','').strip()

        if search_query:
            queryset=queryset.filter(
                Q(camp_code__icontains=search_query) |
                Q(camp_name__icontains=search_query) |
                Q(camp_type__icontains=search_query) |
                Q(camp_mode__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(organizer__icontains=search_query)
            )

        return queryset

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)

        queryset=self.get_queryset()
        today=timezone.localdate()

        context['total_camps']=queryset.count()

        context['completed_camps']=queryset.filter(
            status='COMPLETED'
        ).count()

        context['upcoming_camps']=queryset.filter(
            camp_date__gte=today
        ).exclude(
            status__in=['COMPLETED','CANCELLED']
        ).count()

        context['total_attendees']=queryset.aggregate(
            total=Sum('attended_employee_count')
        )['total'] or 0

        context['total_referrals']=queryset.aggregate(
            total=Sum('referral_count')
        )['total'] or 0

        context['search_query']=self.request.GET.get(
            'q',''
        ).strip()

        return context


class HealthCampCreateView(LoginRequiredMixin,CreateView):
    model=HealthCamp
    form_class=HealthCampForm
    template_name='occupational_health/management/health_camp_form.html'

    def form_valid(self,form):
        form.instance.created_by=self.request.user

        messages.success(
            self.request,
            'Health Camp has been added successfully.'
        )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'occupational_health:health_camp_list'
        )


class HealthCampUpdateView(LoginRequiredMixin,UpdateView):
    model=HealthCamp
    form_class=HealthCampForm
    template_name='occupational_health/management/health_camp_form.html'

    def form_valid(self,form):
        messages.success(
            self.request,
            'Health Camp has been updated successfully.'
        )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'occupational_health:health_camp_list'
        )


class HealthCampDetailView(LoginRequiredMixin,DetailView):
    model=HealthCamp
    template_name='occupational_health/management/health_camp_detail.html'
    context_object_name='health_camp'

    def get_queryset(self):
        return HealthCamp.objects.select_related(
            'plant',
            'medical_facility',
            'lead_medical_professional',
            'created_by'
        )




class HealthCampParticipationListView(LoginRequiredMixin,ListView):
    model=HealthCampParticipation
    template_name='occupational_health/management/health_camp_participation_list.html'
    context_object_name='participations'
    paginate_by=15

    def get_queryset(self):
        queryset=HealthCampParticipation.objects.select_related(
            'health_camp',
            'employee_health_profile__employee',
            'medical_professional',
            'medical_record'
        ).order_by('-registration_date','-id')

        search_query=self.request.GET.get('q','').strip()

        if search_query:
            queryset=queryset.filter(
                Q(health_camp__camp_code__icontains=search_query) |
                Q(health_camp__camp_name__icontains=search_query) |
                Q(employee_health_profile__employee__employee_id__icontains=search_query) |
                Q(employee_health_profile__employee__first_name__icontains=search_query) |
                Q(employee_health_profile__employee__last_name__icontains=search_query) |
                Q(employee_health_profile__employee__username__icontains=search_query)
            )

        return queryset

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)

        queryset=self.get_queryset()

        context['total_participations']=queryset.count()
        context['attended_count']=queryset.filter(
            attendance_status='ATTENDED'
        ).count()
        context['abnormal_count']=queryset.filter(
            screening_status__in=['ABNORMAL','REFERRED','FOLLOW_UP_REQUIRED']
        ).count()
        context['referral_count']=queryset.filter(
            referral_required=True
        ).count()
        context['follow_up_count']=queryset.filter(
            follow_up_required=True
        ).count()
        context['search_query']=self.request.GET.get('q','').strip()

        return context


class HealthCampParticipationCreateView(LoginRequiredMixin,CreateView):
    model=HealthCampParticipation
    form_class=HealthCampParticipationForm
    template_name='occupational_health/management/health_camp_participation_form.html'

    def form_valid(self,form):
        form.instance.created_by=self.request.user
        messages.success(
            self.request,
            'Health Camp Participation has been added successfully.'
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'occupational_health:health_camp_participation_list'
        )


class HealthCampParticipationUpdateView(LoginRequiredMixin,UpdateView):
    model=HealthCampParticipation
    form_class=HealthCampParticipationForm
    template_name='occupational_health/management/health_camp_participation_form.html'

    def form_valid(self,form):
        messages.success(
            self.request,
            'Health Camp Participation has been updated successfully.'
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'occupational_health:health_camp_participation_list'
        )



class HealthCampParticipationDetailView(LoginRequiredMixin,DetailView):
    model=HealthCampParticipation
    template_name='occupational_health/management/health_camp_participation_detail.html'
    context_object_name='participation'

    def get_queryset(self):
        return HealthCampParticipation.objects.select_related(
            'health_camp__plant',
            'employee_health_profile__employee',
            'medical_professional',
            'medical_record',
            'created_by'
        )




class HealthCampDashboardView(LoginRequiredMixin,TemplateView):
    template_name='occupational_health/management/health_camp_dashboard.html'

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)

        today=timezone.localdate()
        soon_date=today+timedelta(days=30)

        camps=HealthCamp.objects.select_related(
            'plant',
            'medical_facility',
            'lead_medical_professional'
        )

        participations=HealthCampParticipation.objects.select_related(
            'health_camp',
            'employee_health_profile__employee',
            'medical_professional',
            'medical_record'
        )

        active_camps=camps.filter(is_active=True)

        active_participations=participations.exclude(
            attendance_status='CANCELLED'
        )

        # ==========================================
        # HEALTH CAMP KPIs
        # ==========================================

        context['total_camps']=active_camps.count()

        context['planned_camps']=active_camps.filter(
            status='PLANNED'
        ).count()

        context['scheduled_camps']=active_camps.filter(
            status='SCHEDULED'
        ).count()

        context['in_progress_camps']=active_camps.filter(
            status='IN_PROGRESS'
        ).count()

        context['completed_camps']=active_camps.filter(
            status='COMPLETED'
        ).count()

        context['cancelled_camps']=camps.filter(
            status='CANCELLED'
        ).count()

        context['upcoming_camps']=active_camps.filter(
            camp_date__gte=today,
            camp_date__lte=soon_date
        ).exclude(
            status__in=['COMPLETED','CANCELLED']
        ).count()

        # ==========================================
        # PARTICIPATION KPIs
        # ==========================================

        context['total_registered']=active_participations.count()

        context['total_attended']=active_participations.filter(
            attendance_status='ATTENDED'
        ).count()

        context['total_not_attended']=active_participations.filter(
            attendance_status='NOT_ATTENDED'
        ).count()

        context['total_screened']=active_participations.exclude(
            screening_status='NOT_SCREENED'
        ).count()

        context['abnormal_screenings']=active_participations.filter(
            screening_status__in=[
                'ABNORMAL',
                'REFERRED',
                'FOLLOW_UP_REQUIRED'
            ]
        ).count()

        context['referrals']=active_participations.filter(
            referral_required=True
        ).count()

        context['follow_ups']=active_participations.filter(
            follow_up_required=True
        ).count()

        # ==========================================
        # ATTENDANCE PERCENTAGE
        # ==========================================

        total_registered=context['total_registered']
        total_attended=context['total_attended']

        if total_registered:
            context['attendance_percentage']=round(
                (total_attended/total_registered)*100,
                1
            )
        else:
            context['attendance_percentage']=0

        # ==========================================
        # SCREENING PERCENTAGE
        # ==========================================

        total_screened=context['total_screened']

        if total_attended:
            context['screening_percentage']=round(
                (total_screened/total_attended)*100,
                1
            )
        else:
            context['screening_percentage']=0

        # ==========================================
        # CAMP STATUS SUMMARY
        # ==========================================

        context['camp_status_summary']=[
            {
                'label':'Planned',
                'value':active_camps.filter(status='PLANNED').count()
            },
            {
                'label':'Scheduled',
                'value':active_camps.filter(status='SCHEDULED').count()
            },
            {
                'label':'In Progress',
                'value':active_camps.filter(status='IN_PROGRESS').count()
            },
            {
                'label':'Completed',
                'value':active_camps.filter(status='COMPLETED').count()
            },
            {
                'label':'Cancelled',
                'value':camps.filter(status='CANCELLED').count()
            }
        ]

        # ==========================================
        # CAMP TYPE SUMMARY
        # ==========================================

        camp_type_summary=[]

        camp_types=active_camps.values(
            'camp_type'
        ).annotate(
            total=Count('id')
        ).order_by('-total')

        for item in camp_types:
            camp_type_summary.append({
                'label':dict(
                    HealthCamp.CAMP_TYPE_CHOICES
                ).get(
                    item['camp_type'],
                    item['camp_type']
                ),
                'value':item['total']
            })

        context['camp_type_summary']=camp_type_summary

        # ==========================================
        # SCREENING SUMMARY
        # ==========================================

        screening_summary=[]

        screening_statuses=active_participations.values(
            'screening_status'
        ).annotate(
            total=Count('id')
        ).order_by('-total')

        for item in screening_statuses:
            screening_summary.append({
                'label':dict(
                    HealthCampParticipation.SCREENING_STATUS_CHOICES
                ).get(
                    item['screening_status'],
                    item['screening_status']
                ),
                'value':item['total']
            })

        context['screening_summary']=screening_summary

        # ==========================================
        # UPCOMING CAMPS
        # ==========================================

        context['upcoming_camps_list']=active_camps.filter(
            camp_date__gte=today
        ).exclude(
            status__in=['COMPLETED','CANCELLED']
        ).order_by(
            'camp_date',
            'start_time'
        )[:10]

        # ==========================================
        # RECENT COMPLETED CAMPS
        # ==========================================

        context['recent_completed_camps']=active_camps.filter(
            status='COMPLETED'
        ).order_by(
            '-camp_date'
        )[:10]

        # ==========================================
        # FOLLOW-UP EMPLOYEES
        # ==========================================

        context['follow_up_participations']=active_participations.filter(
            follow_up_required=True
        ).select_related(
            'health_camp',
            'employee_health_profile__employee',
            'medical_professional'
        ).order_by(
            'follow_up_date'
        )[:10]

        # ==========================================
        # REFERRAL EMPLOYEES
        # ==========================================

        context['referral_participations']=active_participations.filter(
            referral_required=True
        ).select_related(
            'health_camp',
            'employee_health_profile__employee',
            'medical_professional'
        ).order_by(
            '-health_camp__camp_date'
        )[:10]

        # ==========================================
        # RECENT PARTICIPATION
        # ==========================================

        context['recent_participations']=active_participations.select_related(
            'health_camp',
            'employee_health_profile__employee',
            'medical_professional'
        ).order_by(
            '-registration_date',
            '-id'
        )[:10]

        # ==========================================
        # CAMP ATTENDANCE SUMMARY
        # ==========================================

        context['camp_attendance_summary']=active_camps.order_by(
            '-camp_date'
        )[:10]

        # ==========================================
        # OVERDUE FOLLOW-UPS
        # ==========================================

        context['overdue_follow_ups']=active_participations.filter(
            follow_up_required=True,
            follow_up_date__lt=today
        ).exclude(
            attendance_status='CANCELLED'
        ).order_by(
            'follow_up_date'
        )[:10]

        context['overdue_follow_up_count']=active_participations.filter(
            follow_up_required=True,
            follow_up_date__lt=today
        ).exclude(
            attendance_status='CANCELLED'
        ).count()

        # ==========================================
        # CAMPS BY PLANT
        # ==========================================

        context['plant_summary']=active_camps.values(
            'plant__name'
        ).annotate(
            total=Count('id')
        ).order_by('-total')[:10]

        # ==========================================
        # DASHBOARD DATE
        # ==========================================

        context['today']=today
        context['soon_date']=soon_date

        return context


    



class OccupationalHealthAnalyticsDashboardView(LoginRequiredMixin,TemplateView):
    template_name='occupational_health/management/occupational_health_analytics_dashboard.html'

    def get_context_data(self,**kwargs):
        context=super().get_context_data(**kwargs)

        today=timezone.localdate()
        current_year=today.year
        current_month=today.month
        month_start=today.replace(day=1)
        next_month=(month_start+timedelta(days=32)).replace(day=1)

        # ==========================================================
        # BASE QUERYSETS
        # ==========================================================

        profiles=EmployeeHealthProfile.objects.select_related(
            'employee'
        )

        examinations=MedicalExamination.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'examination_type'
        )

        test_results=MedicalTestResult.objects.select_related(
            'medical_examination',
            'medical_examination__employee_health_profile',
            'medical_examination__employee_health_profile__employee',
            'medical_test'
        )

        fitness=FitnessToWork.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'medical_examination'
        )

        surveillance=HealthSurveillance.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'exposure_type'
        )

        exposures=EmployeeExposure.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'exposure_type',
            'health_surveillance'
        )

        follow_ups=MedicalFollowUp.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee'
        )

        vaccinations=EmployeeVaccination.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'vaccination'
        )

        diseases=EmployeeOccupationalDisease.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'health_condition'
        )

        incidents=HealthIncident.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'occupational_disease',
            'exposure'
        )

        return_to_work=ReturnToWork.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee',
            'fitness_assessment'
        )

        medical_records=MedicalRecord.objects.select_related(
            'employee_health_profile',
            'employee_health_profile__employee'
        )

        camps=HealthCamp.objects.select_related(
            'plant',
            'medical_facility',
            'lead_medical_professional'
        )

        participation=HealthCampParticipation.objects.select_related(
            'health_camp',
            'employee_health_profile',
            'employee_health_profile__employee',
            'medical_professional'
        )

        # ==========================================================
        # EMPLOYEE HEALTH PROFILE
        # ==========================================================

        context['total_employees']=profiles.filter(
            is_active=True
        ).count()

        context['employees_under_surveillance']=profiles.filter(
            is_active=True,
            is_under_health_surveillance=True
        ).count()

        context['active_health_profiles']=profiles.filter(
            health_profile_status='ACTIVE',
            is_active=True
        ).count()

        # ==========================================================
        # MEDICAL EXAMINATIONS
        # ==========================================================

        context['total_examinations']=examinations.count()

        context['completed_examinations']=examinations.filter(
            status='COMPLETED'
        ).count()

        context['scheduled_examinations']=examinations.filter(
            status='SCHEDULED'
        ).count()

        context['cancelled_examinations']=examinations.filter(
            status='CANCELLED'
        ).count()

        context['examinations_this_month']=examinations.filter(
            examination_date__gte=month_start,
            examination_date__lt=next_month
        ).count()

        # ==========================================================
        # MEDICAL TEST RESULTS
        # ==========================================================

        context['total_test_results']=test_results.count()

        context['abnormal_test_results']=test_results.filter(
            result_status='ABNORMAL'
        ).count()

        context['borderline_test_results']=test_results.filter(
            result_status='BORDERLINE'
        ).count()

        context['pending_test_results']=test_results.filter(
            result_status='PENDING'
        ).count()

        context['test_abnormal_percentage']=round(
            (
                context['abnormal_test_results']
                / context['total_test_results']
                * 100
            ),
            1
        ) if context['total_test_results'] else 0

        # ==========================================================
        # FITNESS TO WORK
        # ==========================================================

        context['total_fitness_assessments']=fitness.count()

        context['fit_employees']=fitness.filter(
            fitness_status='FIT'
        ).count()

        context['fit_with_restrictions']=fitness.filter(
            fitness_status='FIT_WITH_RESTRICTIONS'
        ).count()

        context['temporarily_unfit']=fitness.filter(
            fitness_status='TEMPORARILY_UNFIT'
        ).count()

        context['unfit_employees']=fitness.filter(
            fitness_status='UNFIT'
        ).count()

        context['fitness_restriction_percentage']=round(
            (
                context['fit_with_restrictions']
                / context['total_fitness_assessments']
                * 100
            ),
            1
        ) if context['total_fitness_assessments'] else 0

        # ==========================================================
        # HEALTH SURVEILLANCE
        # ==========================================================

        context['total_surveillance']=surveillance.count()

        context['active_surveillance']=surveillance.filter(
            status='ACTIVE',
            is_active=True
        ).count()

        context['surveillance_due']=surveillance.filter(
            next_due_date__lte=today,
            status='ACTIVE',
            is_active=True
        ).count()

        context['surveillance_due_30_days']=surveillance.filter(
            next_due_date__gt=today,
            next_due_date__lte=today+timedelta(days=30),
            status='ACTIVE',
            is_active=True
        ).count()

        # ==========================================================
        # EXPOSURE TRACKING
        # ==========================================================

        context['total_exposures']=exposures.count()

        context['active_exposures']=exposures.filter(
            status='ACTIVE',
            is_active=True
        ).count()

        context['high_risk_exposures']=exposures.filter(
            exposure_level='HIGH'
        ).count()

        context['surveillance_required_exposures']=exposures.filter(
            health_surveillance_required=True,
            status='ACTIVE'
        ).count()

        # ==========================================================
        # MEDICAL FOLLOW-UPS
        # ==========================================================

        context['total_follow_ups']=follow_ups.count()

        context['pending_follow_ups']=follow_ups.filter(
            status='PENDING'
        ).count()

        context['scheduled_follow_ups']=follow_ups.filter(
            status='SCHEDULED'
        ).count()

        context['completed_follow_ups']=follow_ups.filter(
            status='COMPLETED'
        ).count()

        context['overdue_follow_ups']=follow_ups.filter(
            status='OVERDUE'
        ).count()

        context['urgent_follow_ups']=follow_ups.filter(
            priority='URGENT'
        ).exclude(
            status__in=['COMPLETED','CANCELLED']
        ).count()

        # ==========================================================
        # VACCINATION
        # ==========================================================

        active_vaccinations=vaccinations.exclude(
            vaccination_status='CANCELLED'
        )

        context['total_vaccinations']=active_vaccinations.count()

        context['completed_vaccinations']=active_vaccinations.filter(
            dose_status='COMPLETED'
        ).count()

        context['scheduled_vaccinations']=active_vaccinations.filter(
            dose_status='SCHEDULED'
        ).count()

        context['missed_vaccinations']=active_vaccinations.filter(
            dose_status='MISSED'
        ).count()

        context['expired_vaccinations']=active_vaccinations.filter(
            vaccination_status='EXPIRED'
        ).count()

        context['vaccination_adverse_reactions']=active_vaccinations.filter(
            adverse_reaction=True
        ).count()

        # ==========================================================
        # OCCUPATIONAL DISEASES
        # ==========================================================

        context['total_diseases']=diseases.count()

        context['suspected_diseases']=diseases.filter(
            disease_status='SUSPECTED'
        ).count()

        context['confirmed_diseases']=diseases.filter(
            disease_status='CONFIRMED'
        ).count()

        context['diseases_under_investigation']=diseases.filter(
            status='UNDER_INVESTIGATION'
        ).count()

        context['disease_follow_ups']=diseases.filter(
            follow_up_required=True
        ).count()

        # ==========================================================
        # HEALTH INCIDENTS
        # ==========================================================

        context['total_health_incidents']=incidents.count()

        context['work_related_illness']=incidents.filter(
            incident_type='WORK_RELATED_ILLNESS'
        ).count()

        context['occupational_exposure_incidents']=incidents.filter(
            incident_type='OCCUPATIONAL_EXPOSURE'
        ).count()

        context['medical_emergencies']=incidents.filter(
            incident_type='MEDICAL_EMERGENCY'
        ).count()

        context['serious_incidents']=incidents.filter(
            severity__in=['SERIOUS','CRITICAL']
        ).count()

        context['open_incidents']=incidents.exclude(
            status='CLOSED'
        ).count()

        # ==========================================================
        # RETURN TO WORK
        # ==========================================================

        context['total_return_to_work']=return_to_work.count()

        context['rtw_pending']=return_to_work.filter(
            status='PENDING'
        ).count()

        context['rtw_medical_assessment']=return_to_work.filter(
            status='MEDICAL_ASSESSMENT'
        ).count()

        context['rtw_approved']=return_to_work.filter(
            status='APPROVED'
        ).count()

        context['rtw_restricted']=return_to_work.filter(
            status='APPROVED_WITH_RESTRICTIONS'
        ).count()

        context['rtw_not_approved']=return_to_work.filter(
            status='NOT_APPROVED'
        ).count()

        context['rtw_completed']=return_to_work.filter(
            status='COMPLETED'
        ).count()

        # ==========================================================
        # MEDICAL RECORDS
        # ==========================================================

        context['total_medical_records']=medical_records.count()

        context['active_medical_records']=medical_records.filter(
            record_status='ACTIVE'
        ).count()

        context['confidential_records']=medical_records.filter(
            confidential=True
        ).count()

        context['expired_records']=medical_records.filter(
            expiry_date__lt=today
        ).count()

        context['records_without_document']=medical_records.filter(
            document=''
        ).count()

        # ==========================================================
        # HEALTH CAMPS
        # ==========================================================

        active_camps=camps.filter(
            is_active=True
        )

        context['total_health_camps']=active_camps.count()

        context['completed_health_camps']=active_camps.filter(
            status='COMPLETED'
        ).count()

        context['upcoming_health_camps']=active_camps.filter(
            camp_date__gte=today
        ).exclude(
            status__in=['COMPLETED','CANCELLED']
        ).count()

        context['camp_attendees']=active_camps.aggregate(
            total=Sum('attended_employee_count')
        )['total'] or 0

        context['camp_referrals']=active_camps.aggregate(
            total=Sum('referral_count')
        )['total'] or 0

        context['camp_follow_ups']=active_camps.aggregate(
            total=Sum('follow_up_required_count')
        )['total'] or 0

        # ==========================================================
        # HEALTH CAMP PARTICIPATION
        # ==========================================================

        active_participation=participation.exclude(
            attendance_status='CANCELLED'
        )

        context['total_camp_participation']=active_participation.count()

        context['camp_attended']=active_participation.filter(
            attendance_status='ATTENDED'
        ).count()

        context['camp_not_attended']=active_participation.filter(
            attendance_status='NOT_ATTENDED'
        ).count()

        context['camp_abnormal_screenings']=active_participation.filter(
            screening_status__in=[
                'ABNORMAL',
                'REFERRED',
                'FOLLOW_UP_REQUIRED'
            ]
        ).count()

        context['camp_participation_referrals']=active_participation.filter(
            referral_required=True
        ).count()

        context['camp_participation_followups']=active_participation.filter(
            follow_up_required=True
        ).count()

        context['camp_attendance_percentage']=round(
            (
                context['camp_attended']
                / context['total_camp_participation']
                * 100
            ),
            1
        ) if context['total_camp_participation'] else 0

        # ==========================================================
        # OVERALL HEALTH RISK INDICATORS
        # ==========================================================

        context['total_health_risk_indicators']=(
            context['abnormal_test_results']
            + context['temporarily_unfit']
            + context['unfit_employees']
            + context['high_risk_exposures']
            + context['confirmed_diseases']
            + context['serious_incidents']
            + context['overdue_follow_ups']
        )

        # ==========================================================
        # MONTHLY MEDICAL EXAMINATION TREND
        # ==========================================================

        examination_trend=(
            examinations
            .filter(examination_date__year=current_year)
            .annotate(month=TruncMonth('examination_date'))
            .values('month')
            .annotate(total=Count('id'))
            .order_by('month')
        )

        context['examination_trend']=[
            {
                'month':item['month'].strftime('%b'),
                'value':item['total']
            }
            for item in examination_trend
        ]

        # ==========================================================
        # MONTHLY TEST RESULT TREND
        # ==========================================================

        test_trend=(
            test_results
            .filter(test_date__year=current_year)
            .annotate(month=TruncMonth('test_date'))
            .values('month')
            .annotate(
                total=Count('id'),
                abnormal=Count(
                    'id',
                    filter=Q(result_status='ABNORMAL')
                )
            )
            .order_by('month')
        )

        context['test_result_trend']=[
            {
                'month':item['month'].strftime('%b'),
                'total':item['total'],
                'abnormal':item['abnormal']
            }
            for item in test_trend
        ]

        # ==========================================================
        # MONTHLY HEALTH INCIDENT TREND
        # ==========================================================

        incident_trend=(
            incidents
            .filter(incident_date__year=current_year)
            .annotate(month=TruncMonth('incident_date'))
            .values('month')
            .annotate(
                total=Count('id'),
                serious=Count(
                    'id',
                    filter=Q(
                        severity__in=['SERIOUS','CRITICAL']
                    )
                )
            )
            .order_by('month')
        )

        context['health_incident_trend']=[
            {
                'month':item['month'].strftime('%b'),
                'total':item['total'],
                'serious':item['serious']
            }
            for item in incident_trend
        ]

        # ==========================================================
        # MONTHLY OCCUPATIONAL DISEASE TREND
        # ==========================================================

        disease_trend=(
            diseases
            .filter(reported_date__year=current_year)
            .annotate(month=TruncMonth('reported_date'))
            .values('month')
            .annotate(total=Count('id'))
            .order_by('month')
        )

        context['disease_trend']=[
            {
                'month':item['month'].strftime('%b'),
                'value':item['total']
            }
            for item in disease_trend
        ]

        # ==========================================================
        # MONTHLY HEALTH CAMP TREND
        # ==========================================================

        camp_trend=(
            active_camps
            .filter(camp_date__year=current_year)
            .annotate(month=TruncMonth('camp_date'))
            .values('month')
            .annotate(
                camps=Count('id'),
                attendees=Sum('attended_employee_count')
            )
            .order_by('month')
        )

        context['health_camp_trend']=[
            {
                'month':item['month'].strftime('%b'),
                'camps':item['camps'],
                'attendees':item['attendees'] or 0
            }
            for item in camp_trend
        ]

        # ==========================================================
        # FITNESS DISTRIBUTION
        # ==========================================================

        context['fitness_distribution']=[
            {
                'label':'Fit',
                'value':context['fit_employees']
            },
            {
                'label':'Fit With Restrictions',
                'value':context['fit_with_restrictions']
            },
            {
                'label':'Temporarily Unfit',
                'value':context['temporarily_unfit']
            },
            {
                'label':'Unfit',
                'value':context['unfit_employees']
            }
        ]

        # ==========================================================
        # EXPOSURE DISTRIBUTION
        # ==========================================================

        exposure_distribution=(
            exposures
            .filter(is_active=True)
            .values('exposure_level')
            .annotate(total=Count('id'))
            .order_by('-total')
        )

        context['exposure_distribution']=[
            {
                'label':item['exposure_level'] or 'Not Specified',
                'value':item['total']
            }
            for item in exposure_distribution
        ]

        # ==========================================================
        # DISEASE SEVERITY DISTRIBUTION
        # ==========================================================

        disease_severity=(
            diseases
            .values('severity')
            .annotate(total=Count('id'))
            .order_by('-total')
        )

        context['disease_severity_distribution']=[
            {
                'label':item['severity'],
                'value':item['total']
            }
            for item in disease_severity
        ]

        # ==========================================================
        # INCIDENT SEVERITY DISTRIBUTION
        # ==========================================================

        incident_severity=(
            incidents
            .values('severity')
            .annotate(total=Count('id'))
            .order_by('-total')
        )

        context['incident_severity_distribution']=[
            {
                'label':item['severity'],
                'value':item['total']
            }
            for item in incident_severity
        ]

        # ==========================================================
        # FOLLOW-UP STATUS DISTRIBUTION
        # ==========================================================

        follow_up_status=(
            follow_ups
            .values('status')
            .annotate(total=Count('id'))
            .order_by('-total')
        )

        context['follow_up_status_distribution']=[
            {
                'label':item['status'],
                'value':item['total']
            }
            for item in follow_up_status
        ]

        # ==========================================================
        # HEALTH CAMP SCREENING DISTRIBUTION
        # ==========================================================

        camp_screening=(
            active_participation
            .values('screening_status')
            .annotate(total=Count('id'))
            .order_by('-total')
        )

        context['camp_screening_distribution']=[
            {
                'label':item['screening_status'],
                'value':item['total']
            }
            for item in camp_screening
        ]

        # ==========================================================
        # UPCOMING SURVEILLANCE
        # ==========================================================

        context['upcoming_surveillance']=surveillance.filter(
            status='ACTIVE',
            is_active=True,
            next_due_date__gte=today,
            next_due_date__lte=today+timedelta(days=30)
        ).order_by(
            'next_due_date'
        )[:10]

        # ==========================================================
        # OVERDUE FOLLOW-UPS
        # ==========================================================

        context['overdue_follow_up_list']=follow_ups.filter(
            status='OVERDUE'
        ).order_by(
            'scheduled_date'
        )[:10]

        # ==========================================================
        # HIGH RISK EXPOSURES
        # ==========================================================

        context['high_risk_exposure_list']=exposures.filter(
            exposure_level='HIGH',
            status='ACTIVE',
            is_active=True
        ).order_by(
            '-exposure_start_date'
        )[:10]

        # ==========================================================
        # RECENT DISEASES
        # ==========================================================

        context['recent_diseases']=diseases.order_by(
            '-reported_date',
            '-id'
        )[:10]

        # ==========================================================
        # RECENT INCIDENTS
        # ==========================================================

        context['recent_health_incidents']=incidents.order_by(
            '-incident_date',
            '-id'
        )[:10]

        # ==========================================================
        # UPCOMING HEALTH CAMPS
        # ==========================================================

        context['upcoming_health_camp_list']=active_camps.filter(
            camp_date__gte=today
        ).exclude(
            status__in=['COMPLETED','CANCELLED']
        ).order_by(
            'camp_date',
            'start_time'
        )[:10]

        # ==========================================================
        # CURRENT YEAR
        # ==========================================================

        context['current_year']=current_year
        context['today']=today

        return context