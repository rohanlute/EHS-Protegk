from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.five_s.models import FiveSSchedule, FiveSAudit
from dateutil.relativedelta import relativedelta
import datetime

class Command(BaseCommand):
    help = 'Generate 5S audits based on active schedules'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        
        # 1. Only fetch ACTIVE schedules
        schedules = FiveSSchedule.objects.filter(status='ACTIVE')

        generated_count = 0

        for schedule in schedules:
            # 2. Auto-end schedules if the end date has passed
            if schedule.end_date and schedule.end_date < today:
                schedule.status = 'ENDED'
                schedule.save()
                continue

            # 3. CRITICAL FIX: Check if the schedule is actually due today!
            if schedule.start_date > today:
                continue # Skip if the next due date is in the future

            # 4. Create ONE Audit per assignee
            for user in schedule.assignee.all():
                # We use the scheduled_date in the cycle_key to prevent duplicate audits
                cycle_key = f"schedule_{schedule.id}_user_{user.id}-{today.strftime('%Y%m%d')}"

                if FiveSAudit.objects.filter(cycle_key=cycle_key).exists():
                    continue

                due_date = today + datetime.timedelta(days=7)
                
                FiveSAudit.objects.create(
                    schedule=schedule,
                    user=user, 
                    template_version=schedule.template.version,
                    cycle_key=cycle_key,
                    scheduled_date=today,
                    due_date=due_date,
                    status='SCHEDULED'
                )
                generated_count += 1

            # 5. Calculate the Next Date and save it
            if schedule.frequency == 'DAILY':
                schedule.start_date = schedule.start_date + relativedelta(days=1)
            elif schedule.frequency == 'WEEKLY':
                schedule.start_date = schedule.start_date + relativedelta(weeks=1)
            elif schedule.frequency == 'MONTHLY':
                schedule.start_date = schedule.start_date + relativedelta(months=1)
            elif schedule.frequency == 'QUARTERLY':
                schedule.start_date = schedule.start_date + relativedelta(months=3)
            elif schedule.frequency == 'YEARLY':
                schedule.start_date = schedule.start_date + relativedelta(years=1)

            schedule.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully generated {generated_count} audits.'))