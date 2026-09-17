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

    # Employee Health Profile
    path('employee-health-profiles/',views.EmployeeHealthProfileListView.as_view(),name='employee_health_profile_list'),
    path('employee-health-profiles/add/',views.EmployeeHealthProfileCreateView.as_view(),name='employee_health_profile_add'),
    path('employee-health-profiles/<int:pk>/',views.EmployeeHealthProfileDetailView.as_view(),name='employee_health_profile_detail'),
    path('employee-health-profiles/<int:pk>/edit/',views.EmployeeHealthProfileUpdateView.as_view(),name='employee_health_profile_edit'),

    # Medical Examinations
    path('medical-examinations/', views.MedicalExaminationListView.as_view(), name='medical_examination_list'),
    path('medical-examinations/add/', views.MedicalExaminationCreateView.as_view(), name='medical_examination_add'),
    path('medical-examinations/<int:pk>/edit/', views.MedicalExaminationUpdateView.as_view(), name='medical_examination_edit'),
    path('medical-examinations/<int:pk>/', views.MedicalExaminationDetailView.as_view(), name='medical_examination_detail'),
    path('api/employee-health-profile/<int:pk>/', views.EmployeeHealthProfileDataView.as_view(), name='employee_health_profile_data'),

    # Medical Test Results
    path('medical-test-results/', views.MedicalTestResultListView.as_view(), name='medical_test_result_list'),
    path('medical-test-results/add/', views.MedicalTestResultCreateView.as_view(), name='medical_test_result_add'),
    path('medical-test-results/<int:pk>/', views.MedicalTestResultDetailView.as_view(), name='medical_test_result_detail'),
    path('medical-test-results/<int:pk>/edit/', views.MedicalTestResultUpdateView.as_view(), name='medical_test_result_edit'),

    # Fitness To Work
    path('fitness-to-work/', views.FitnessToWorkListView.as_view(), name='fitness_to_work_list'),
    path('fitness-to-work/add/', views.FitnessToWorkCreateView.as_view(), name='fitness_to_work_add'),
    path('fitness-to-work/<int:pk>/', views.FitnessToWorkDetailView.as_view(), name='fitness_to_work_detail'),
    path('fitness-to-work/<int:pk>/edit/', views.FitnessToWorkUpdateView.as_view(), name='fitness_to_work_edit'),
    path('api/medical-examination-fitness/<int:pk>/', views.MedicalExaminationFitnessDataView.as_view(), name='medical_examination_fitness_data'),

    # Health Surveillance
    path('health-surveillance/', views.HealthSurveillanceListView.as_view(), name='health_surveillance_list'),
    path('health-surveillance/add/', views.HealthSurveillanceCreateView.as_view(), name='health_surveillance_add'),
    path('health-surveillance/<int:pk>/', views.HealthSurveillanceDetailView.as_view(), name='health_surveillance_detail'),
    path('health-surveillance/<int:pk>/edit/', views.HealthSurveillanceUpdateView.as_view(), name='health_surveillance_edit'),

    # Employee Exposure Tracking
    path('employee-exposures/',views.EmployeeExposureListView.as_view(),name='employee_exposure_list'),
    path('employee-exposures/add/',views.EmployeeExposureCreateView.as_view(),name='employee_exposure_add'),
    path('employee-exposures/<int:pk>/',views.EmployeeExposureDetailView.as_view(),name='employee_exposure_detail'),
    path('employee-exposures/<int:pk>/edit/',views.EmployeeExposureUpdateView.as_view(),name='employee_exposure_edit'),
    path('api/employee-health-surveillance/',views.EmployeeHealthSurveillanceDataView.as_view(),name='employee_health_surveillance_data'),
    # Employee Exposures Dashboards
    path('employee-exposures/dashboard/',views.EmployeeExposureDashboardView.as_view(),name='employee_exposure_dashboard'),

    # Medical Follow Ups
    path('medical-follow-ups/',views.MedicalFollowUpListView.as_view(),name='medical_follow_up_list'),
    path('medical-follow-ups/add/',views.MedicalFollowUpCreateView.as_view(),name='medical_follow_up_add'),
    path('medical-follow-ups/<int:pk>/',views.MedicalFollowUpDetailView.as_view(),name='medical_follow_up_detail'),
    path('medical-follow-ups/<int:pk>/edit/',views.MedicalFollowUpUpdateView.as_view(),name='medical_follow_up_edit'),
    path('api/medical-follow-up/employee-records/',views.MedicalFollowUpEmployeeRecordsDataView.as_view(),name='medical_follow_up_employee_records'),
    # Medical follow Ups Dashboards
    path('medical-follow-ups/dashboard/',views.MedicalFollowUpDashboardView.as_view(),name='medical_follow_up_dashboard'),

    # Vaccinations
    path('vaccinations/',views.EmployeeVaccinationListView.as_view(),name='employee_vaccination_list'),
    path('vaccinations/add/',views.EmployeeVaccinationCreateView.as_view(),name='employee_vaccination_add'),
    path('vaccinations/<int:pk>/',views.EmployeeVaccinationDetailView.as_view(),name='employee_vaccination_detail'),
    path('vaccinations/<int:pk>/edit/',views.EmployeeVaccinationUpdateView.as_view(),name='employee_vaccination_edit'),
    # Vaccinations Dashboard
    path('vaccinations/dashboard/',views.EmployeeVaccinationDashboardView.as_view(),name='employee_vaccination_dashboard'),

    # Occupational Diseases
    path('occupational-diseases/',views.EmployeeOccupationalDiseaseListView.as_view(),name='employee_occupational_disease_list'),
    path('occupational-diseases/add/',views.EmployeeOccupationalDiseaseCreateView.as_view(),name='employee_occupational_disease_add'),
    path('occupational-diseases/<int:pk>/',views.EmployeeOccupationalDiseaseDetailView.as_view(),name='employee_occupational_disease_detail'),
    path('occupational-diseases/<int:pk>/edit/',views.EmployeeOccupationalDiseaseUpdateView.as_view(),name='employee_occupational_disease_edit'),
    # Occupational Diseases Dashboard
    path('occupational-diseases/dashboard/',views.EmployeeOccupationalDiseaseDashboardView.as_view(),name='employee_occupational_disease_dashboard'),

    # Health Incidents
    path('health-incidents/',views.HealthIncidentListView.as_view(),name='health_incident_list'),
    path('health-incidents/add/',views.HealthIncidentCreateView.as_view(),name='health_incident_add'),
    path('health-incidents/<int:pk>/',views.HealthIncidentDetailView.as_view(),name='health_incident_detail'),
    path('health-incidents/<int:pk>/edit/',views.HealthIncidentUpdateView.as_view(),name='health_incident_edit'),
    # Health Incidents Dashboards
    path('health-incidents/dashboard/',views.HealthIncidentDashboardView.as_view(),name='health_incident_dashboard'),

    # Return To Work
    path('return-to-work/',views.ReturnToWorkListView.as_view(),name='return_to_work_list'),
    path('return-to-work/add/',views.ReturnToWorkCreateView.as_view(),name='return_to_work_add'),
    path('return-to-work/<int:pk>/',views.ReturnToWorkDetailView.as_view(),name='return_to_work_detail'),
    path('return-to-work/<int:pk>/edit/',views.ReturnToWorkUpdateView.as_view(),name='return_to_work_edit'),
    # Return To Work Dashboard
    path('return-to-work/dashboard/',views.ReturnToWorkDashboardView.as_view(),name='return_to_work_dashboard'),

    # Medical Records
    path('medical-records/',views.MedicalRecordListView.as_view(),name='medical_record_list'),
    path('medical-records/add/',views.MedicalRecordCreateView.as_view(),name='medical_record_add'),
    path('medical-records/<int:pk>/',views.MedicalRecordDetailView.as_view(),name='medical_record_detail'),
    path('medical-records/<int:pk>/edit/',views.MedicalRecordUpdateView.as_view(),name='medical_record_edit'),
    # Medical Records Dashboards
    path('medical-records/dashboard/',views.MedicalRecordDashboardView.as_view(),name='medical_record_dashboard'),


    # Health Camp
    path('health-camps/',views.HealthCampListView.as_view(),name='health_camp_list'),
    path('health-camps/add/',views.HealthCampCreateView.as_view(),name='health_camp_add'),
    path('health-camps/<int:pk>/edit/',views.HealthCampUpdateView.as_view(),name='health_camp_edit'),
    path('health-camps/<int:pk>/',views.HealthCampDetailView.as_view(),name='health_camp_detail'),

    # Health Camp Participation
    path('health-camp-participation/',views.HealthCampParticipationListView.as_view(),name='health_camp_participation_list'),
    path('health-camp-participation/add/',views.HealthCampParticipationCreateView.as_view(),name='health_camp_participation_add'),
    path('health-camp-participation/<int:pk>/edit/',views.HealthCampParticipationUpdateView.as_view(),name='health_camp_participation_edit'),
    path('health-camp-participation/<int:pk>/',views.HealthCampParticipationDetailView.as_view(),name='health_camp_participation_detail'),

    # Common Dashboard for Health Camp and Participation
    path('health-camps/dashboard/',views.HealthCampDashboardView.as_view(),name='health_camp_dashboard'),


    # Occupational Health Analytics Dashboard
    path('analytics/',views.OccupationalHealthAnalyticsDashboardView.as_view(),name='occupational_health_analytics_dashboard'),

]