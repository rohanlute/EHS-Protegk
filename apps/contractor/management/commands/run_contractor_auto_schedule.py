# apps/contractor/management/commands/run_contractor_auto_schedule.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from apps.contractor.models import ContractorInspection
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run auto-schedule for contractor inspections'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually saving',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(' Contractor Inspection Auto-Schedule '))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY RUN MODE - No changes will be saved'))
            self.stdout.write('')
        
        parent_inspections = ContractorInspection.objects.filter(
            enable_auto_schedule=True,
            status__in=['SCHEDULED', 'IN_PROGRESS', 'OVERDUE'],
            is_recurring_copy=False
        ).distinct()
        
        total_created = 0
        total_skipped = 0
        
        for parent in parent_inspections:
            today = timezone.now().date()
            
            # Calculate next month's start date
            if today.month == 12:
                next_month_start = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month_start = today.replace(month=today.month + 1, day=1)
            
            # Check if copy already exists
            existing_copy = ContractorInspection.objects.filter(
                parent_inspection=parent,
                inspection_start_date=next_month_start,
                is_recurring_copy=True
            ).first()
            
            if existing_copy:
                self.stdout.write(
                    self.style.WARNING(f'  ⏭️  Skipping {parent.inspection_code} - Copy exists for {next_month_start}')
                )
                total_skipped += 1
                continue
            
            if parent.status == 'CLOSED':
                self.stdout.write(
                    self.style.WARNING(f'  ⏭️  Skipping {parent.inspection_code} - Parent is closed')
                )
                total_skipped += 1
                continue
            
            if dry_run:
                offset = parent.due_date_offset_days
                next_month_end = next_month_start + timedelta(days=offset - 1)
                self.stdout.write(
                    self.style.WARNING(
                        f'  [DRY RUN] Would create copy of {parent.inspection_code} '
                        f'for {next_month_start} to {next_month_end} (Offset: {offset} days)'
                    )
                )
                total_created += 1
                continue
            
            try:
                with transaction.atomic():
                    new_inspection = parent.create_recurring_copy()
                    if new_inspection:
                        total_created += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✅ Created {new_inspection.inspection_code} from {parent.inspection_code} '
                                f'for {new_inspection.inspection_start_date} to {new_inspection.inspection_end_date} '
                                f'(Offset: {parent.due_date_offset_days} days)'
                            )
                        )
                        try:
                            from apps.notifications.services import NotificationService
                            NotificationService.notify(
                                content_object=new_inspection,
                                notification_type='INSPECTION_SCHEDULE',
                                module='CONTRACTOR_INSPECTION'
                            )
                        except Exception as e:
                            logger.error(f"Notification error: {e}")
                    else:
                        total_skipped += 1
                        self.stdout.write(self.style.ERROR(f'  ❌ Failed to create copy for {parent.inspection_code}'))
            except Exception as e:
                total_skipped += 1
                self.stdout.write(self.style.ERROR(f'  ❌ Error: {str(e)}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(' 📊 SUMMARY '))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'⚠️  DRY RUN - Would create {total_created} inspections'))
        else:
            self.stdout.write(f'✅ Total created: {total_created}')
            self.stdout.write(f'⏭️  Total skipped: {total_skipped}')
        
        self.stdout.write(self.style.SUCCESS('=' * 60))