from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic import DeleteView
from django.views.generic import TemplateView, ListView, CreateView, UpdateView

from .models import (
    ExaminationType, MedicalTest, ExposureType, HealthCondition, FitnessStatus,
    Restriction, Vaccination, MedicalProfessional, MedicalFacility
)
from .forms import (
    ExaminationTypeForm,MedicalTestForm,ExposureTypeForm,HealthConditionForm,
    FitnessStatusForm,RestrictionForm,VaccinationForm, MedicalProfessionalForm, MedicalFacilityForm
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