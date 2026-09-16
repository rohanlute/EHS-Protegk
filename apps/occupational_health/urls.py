from django.urls import path
from apps.occupational_health import views

app_name = 'occupational_health'

urlpatterns = [
    path('',views.OccupationalHealthDashboardView.as_view(),name='dashboard'),

    # Examination Types
    path('masters/examination-types/',views.ExaminationTypeListView.as_view(),name='examination_type_list'),
    path('masters/examination-types/add/',views.ExaminationTypeCreateView.as_view(),name='examination_type_add'),
    path('masters/examination-types/<int:pk>/edit/',views.ExaminationTypeUpdateView.as_view(),name='examination_type_edit'),
    path('masters/examination-types/<int:pk>/delete/',views.ExaminationTypeDeleteView.as_view(),name='examination_type_delete'),

    # Medical Tests
    path('masters/medical-tests/',views.MedicalTestListView.as_view(),name='medical_test_list'),
    path('masters/medical-tests/add/',views.MedicalTestCreateView.as_view(),name='medical_test_add'),
    path('masters/medical-tests/<int:pk>/edit/',views.MedicalTestUpdateView.as_view(),name='medical_test_edit'),
    path('masters/medical-tests/<int:pk>/delete/',views.MedicalTestDeleteView.as_view(),name='medical_test_delete'),

    # Exposure Types
    path('masters/exposure-types/',views.ExposureTypeListView.as_view(),name='exposure_type_list'),
    path('masters/exposure-types/add/',views.ExposureTypeCreateView.as_view(),name='exposure_type_add'),
    path('masters/exposure-types/<int:pk>/edit/',views.ExposureTypeUpdateView.as_view(),name='exposure_type_edit'),
    path('masters/exposure-types/<int:pk>/delete/',views.ExposureTypeDeleteView.as_view(),name='exposure_type_delete'),

    # Health Conditions
    path('masters/health-conditions/',views.HealthConditionListView.as_view(),name='health_condition_list'),
    path('masters/health-conditions/add/',views.HealthConditionCreateView.as_view(),name='health_condition_add'),
    path('masters/health-conditions/<int:pk>/edit/',views.HealthConditionUpdateView.as_view(),name='health_condition_edit'),
    path('masters/health-conditions/<int:pk>/delete/',views.HealthConditionDeleteView.as_view(),name='health_condition_delete'),

    # Fitness Status
    path('masters/fitness-status/',views.FitnessStatusListView.as_view(),name='fitness_status_list'),
    path('masters/fitness-status/add/',views.FitnessStatusCreateView.as_view(),name='fitness_status_add'),
    path('masters/fitness-status/<int:pk>/edit/',views.FitnessStatusUpdateView.as_view(),name='fitness_status_edit'),
    path('masters/fitness-status/<int:pk>/delete/',views.FitnessStatusDeleteView.as_view(),name='fitness_status_delete'),

    # Restrictions
    path('masters/restrictions/',views.RestrictionListView.as_view(),name='restriction_list'),
    path('masters/restrictions/add/',views.RestrictionCreateView.as_view(),name='restriction_add'),
    path('masters/restrictions/<int:pk>/edit/',views.RestrictionUpdateView.as_view(),name='restriction_edit'),
    path('masters/restrictions/<int:pk>/delete/',views.RestrictionDeleteView.as_view(),name='restriction_delete'),

    # Vaccinations
    path('masters/vaccinations/',views.VaccinationListView.as_view(),name='vaccination_list'),
    path('masters/vaccinations/add/',views.VaccinationCreateView.as_view(),name='vaccination_add'),
    path('masters/vaccinations/<int:pk>/edit/',views.VaccinationUpdateView.as_view(),name='vaccination_edit'),
    path('masters/vaccinations/<int:pk>/delete/',views.VaccinationDeleteView.as_view(),name='vaccination_delete'),

    # Medical Professionals
    path('masters/medical-professionals/',views.MedicalProfessionalListView.as_view(),name='medical_professional_list'),
    path('masters/medical-professionals/add/',views.MedicalProfessionalCreateView.as_view(),name='medical_professional_add'),
    path('masters/medical-professionals/<int:pk>/edit/',views.MedicalProfessionalUpdateView.as_view(),name='medical_professional_edit'),
    path('masters/medical-professionals/<int:pk>/delete/',views.MedicalProfessionalDeleteView.as_view(),name='medical_professional_delete'),

    # Medical Facilities
    path('masters/medical-facilities/',views.MedicalFacilityListView.as_view(),name='medical_facility_list'),
    path('masters/medical-facilities/add/',views.MedicalFacilityCreateView.as_view(),name='medical_facility_add'),
    path('masters/medical-facilities/<int:pk>/edit/',views.MedicalFacilityUpdateView.as_view(),name='medical_facility_edit'),
    path('masters/medical-facilities/<int:pk>/delete/',views.MedicalFacilityDeleteView.as_view(),name='medical_facility_delete'),
]