# apps/five_s/tasks.py
from celery import shared_task
from django.core.management import call_command

@shared_task
def auto_generate_5s_audits():
    """
    Celery task that runs daily to generate 5S audits
    based on active schedules.
    """
    try:
        call_command('generate_5s_audits')
    except Exception as e:
        print(f"Error generating 5S audits: {e}")