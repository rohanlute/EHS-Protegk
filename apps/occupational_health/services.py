from django.utils import timezone
from .models import MedicalFollowUp

def create_medical_examination_follow_up(examination,created_by=None):
    if not examination.follow_up_required or not examination.follow_up_date:
        return None
    employee_health_profile=examination.employee_health_profile
    existing_follow_up=MedicalFollowUp.objects.filter(
        employee_health_profile=employee_health_profile,
        medical_examination=examination,
        follow_up_type='EXAMINATION',
        is_active=True
    ).exclude(status='CANCELLED').first()
    if existing_follow_up:
        return existing_follow_up
    employee_name=(
        employee_health_profile.employee.get_full_name()
        or employee_health_profile.employee.username
    )
    follow_up=MedicalFollowUp(
        employee_health_profile=employee_health_profile,
        medical_examination=examination,
        follow_up_type='EXAMINATION',
        title=f'Medical Examination Follow-up - {employee_name}',
        description=(
            f'Follow-up required for {examination.examination_type.name} '
            f'conducted on {examination.examination_date.strftime("%d %b %Y")}.'
        ),
        scheduled_date=examination.follow_up_date,
        priority='MEDIUM',
        assigned_medical_professional=examination.medical_professional,
        medical_facility=examination.medical_facility,
        status='PENDING',
        is_active=True,
        created_by=created_by or examination.created_by
    )
    follow_up.full_clean()
    follow_up.save()
    return follow_up




def create_medical_test_follow_up(test_result,created_by=None):
    if not test_result.follow_up_required or not test_result.follow_up_date:
        return None
    examination=test_result.medical_examination
    employee_health_profile=examination.employee_health_profile
    existing_follow_up=MedicalFollowUp.objects.filter(
        employee_health_profile=employee_health_profile,
        medical_test_result=test_result,
        follow_up_type='TEST',
        is_active=True
    ).exclude(status='CANCELLED').first()
    if existing_follow_up:
        return existing_follow_up
    employee_name=(
        employee_health_profile.employee.get_full_name()
        or employee_health_profile.employee.username
    )
    priority='MEDIUM'
    if test_result.result_status in ['ABNORMAL','BORDERLINE']:
        priority='HIGH'
    follow_up=MedicalFollowUp(
        employee_health_profile=employee_health_profile,
        medical_examination=examination,
        medical_test_result=test_result,
        follow_up_type='TEST',
        title=f'Medical Test Follow-up - {employee_name}',
        description=(
            f'Follow-up required for {test_result.medical_test.name} '
            f'conducted on {test_result.test_date.strftime("%d %b %Y")}. '
            f'Result Status: {test_result.get_result_status_display()}.'
        ),
        scheduled_date=test_result.follow_up_date,
        priority=priority,
        assigned_medical_professional=examination.medical_professional,
        medical_facility=examination.medical_facility,
        outcome='',
        recommendations=test_result.recommendations,
        remarks=test_result.doctor_comments,
        status='PENDING',
        is_active=True,
        created_by=created_by or test_result.created_by
    )
    follow_up.full_clean()
    follow_up.save()
    return follow_up




def create_fitness_follow_up(fitness_assessment,created_by=None):
    if not fitness_assessment.follow_up_required or not fitness_assessment.follow_up_date:
        return None
    employee_health_profile=fitness_assessment.employee_health_profile
    existing_follow_up=MedicalFollowUp.objects.filter(
        employee_health_profile=employee_health_profile,
        fitness_assessment=fitness_assessment,
        follow_up_type='FITNESS',
        is_active=True
    ).exclude(status='CANCELLED').first()
    if existing_follow_up:
        return existing_follow_up
    employee_name=(
        employee_health_profile.employee.get_full_name()
        or employee_health_profile.employee.username
    )
    priority='MEDIUM'
    if fitness_assessment.fitness_status in ['TEMPORARILY_UNFIT','UNFIT']:
        priority='HIGH'
    elif fitness_assessment.fitness_status=='FIT_WITH_RESTRICTIONS':
        priority='MEDIUM'
    medical_professional=None
    medical_facility=None
    if fitness_assessment.medical_examination_id:
        medical_professional=fitness_assessment.medical_examination.medical_professional
        medical_facility=fitness_assessment.medical_examination.medical_facility
    follow_up=MedicalFollowUp(
        employee_health_profile=employee_health_profile,
        medical_examination=fitness_assessment.medical_examination,
        fitness_assessment=fitness_assessment,
        follow_up_type='FITNESS',
        title=f'Fitness Assessment Follow-up - {employee_name}',
        description=(
            f'Follow-up required for Fitness Assessment conducted on '
            f'{fitness_assessment.assessment_date.strftime("%d %b %Y")}. '
            f'Fitness Status: {fitness_assessment.get_fitness_status_display()}.'
        ),
        scheduled_date=fitness_assessment.follow_up_date,
        priority=priority,
        assigned_medical_professional=medical_professional,
        medical_facility=medical_facility,
        outcome='',
        recommendations=fitness_assessment.work_recommendations,
        remarks=fitness_assessment.doctor_comments,
        status='PENDING',
        is_active=True,
        created_by=created_by or fitness_assessment.created_by
    )
    follow_up.full_clean()
    follow_up.save()
    return follow_up





def create_health_surveillance_follow_up(surveillance,created_by=None):
    if not surveillance.is_active:
        return None
    if surveillance.status not in ['ACTIVE']:
        return None
    if not surveillance.next_due_date:
        return None
    employee_health_profile=surveillance.employee_health_profile
    existing_follow_up=MedicalFollowUp.objects.filter(
        employee_health_profile=employee_health_profile,
        health_surveillance=surveillance,
        follow_up_type='SURVEILLANCE',
        is_active=True
    ).exclude(status='CANCELLED').first()
    if existing_follow_up:
        return existing_follow_up
    employee_name=(
        employee_health_profile.employee.get_full_name()
        or employee_health_profile.employee.username
    )
    follow_up=MedicalFollowUp(
        employee_health_profile=employee_health_profile,
        health_surveillance=surveillance,
        follow_up_type='SURVEILLANCE',
        title=f'Health Surveillance Follow-up - {employee_name}',
        description=(
            f'Health surveillance follow-up for {surveillance.surveillance_name}. '
            f'Exposure Type: {surveillance.exposure_type.name}. '
            f'Next Due Date: {surveillance.next_due_date.strftime("%d %b %Y")}.'
        ),
        scheduled_date=surveillance.next_due_date,
        priority='MEDIUM',
        assigned_medical_professional=surveillance.responsible_medical_professional,
        medical_facility=surveillance.medical_facility,
        outcome='',
        recommendations='',
        remarks=surveillance.remarks,
        status='PENDING',
        is_active=True,
        created_by=created_by or surveillance.created_by
    )
    follow_up.full_clean()
    follow_up.save()
    return follow_up



def create_exposure_follow_up(exposure,created_by=None):
    if not exposure.is_active:
        return None
    if exposure.status not in ['ACTIVE']:
        return None
    if not exposure.health_surveillance_required:
        return None
    existing_follow_up=MedicalFollowUp.objects.filter(
        employee_health_profile=exposure.employee_health_profile,
        exposure=exposure,
        follow_up_type='EXPOSURE',
        is_active=True
    ).exclude(status='CANCELLED').first()
    if existing_follow_up:
        return existing_follow_up
    employee_health_profile=exposure.employee_health_profile
    employee_name=(
        employee_health_profile.employee.get_full_name()
        or employee_health_profile.employee.username
    )
    assigned_medical_professional=None
    medical_facility=None
    if exposure.health_surveillance_id:
        surveillance=exposure.health_surveillance
        assigned_medical_professional=surveillance.responsible_medical_professional
        medical_facility=surveillance.medical_facility
    follow_up_date=None
    if exposure.health_surveillance_id and exposure.health_surveillance.next_due_date:
        follow_up_date=exposure.health_surveillance.next_due_date
    if not follow_up_date:
        return None
    priority='MEDIUM'
    if exposure.exposure_level:
        exposure_level=exposure.exposure_level.upper()
        if any(level in exposure_level for level in ['HIGH','SEVERE','CRITICAL']):
            priority='HIGH'
    follow_up=MedicalFollowUp(
        employee_health_profile=employee_health_profile,
        health_surveillance=exposure.health_surveillance,
        exposure=exposure,
        follow_up_type='EXPOSURE',
        title=f'Exposure Review Follow-up - {employee_name}',
        description=(
            f'Exposure review required for {exposure.exposure_name}. '
            f'Exposure Type: {exposure.exposure_type.name}. '
            f'Work Area: {exposure.work_area or "Not specified"}.'
        ),
        scheduled_date=follow_up_date,
        priority=priority,
        assigned_medical_professional=assigned_medical_professional,
        medical_facility=medical_facility,
        outcome='',
        recommendations='',
        remarks=exposure.remarks,
        status='PENDING',
        is_active=True,
        created_by=created_by or exposure.created_by
    )
    follow_up.full_clean()
    follow_up.save()
    return follow_up