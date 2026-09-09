# apps/contractor/management/commands/calculate_contractor_performance.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.contractor.services.performance_service import BulkPerformanceCalculator


class Command(BaseCommand):
    help = 'Calculate contractor performance metrics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=int,
            help='Month to calculate (1-12). Default: current month',
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Year to calculate. Default: current year',
        )
        parser.add_argument(
            '--period',
            type=str,
            choices=['MONTHLY', 'QUARTERLY', 'YEARLY'],
            default='MONTHLY',
            help='Period type for calculation',
        )
        parser.add_argument(
            '--contractor',
            type=int,
            help='Calculate for specific contractor ID',
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        month = options.get('month') or today.month
        year = options.get('year') or today.year
        period = options.get('period')
        contractor_id = options.get('contractor')

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(' Contractor Performance Calculation '))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f"Period: {period} {month}/{year}")
        self.stdout.write('')

        if contractor_id:
            # Calculate for specific contractor
            from apps.contractor.models import Contractor
            from apps.contractor.services.performance_service import ContractorPerformanceService
            
            contractor = Contractor.objects.get(id=contractor_id)
            metric = ContractorPerformanceService.calculate_contractor_performance(
                contractor, month, year, period
            )
            self.stdout.write(self.style.SUCCESS(
                f"✅ {contractor.contractor_name}: {metric.overall_performance_score}% ({metric.rating})"
            ))
        else:
            # Calculate for all contractors
            results = BulkPerformanceCalculator.calculate_all_contractors(month, year, period)
            
            self.stdout.write(self.style.WARNING('📊 Results:'))
            for result in sorted(results, key=lambda x: x['score'], reverse=True):
                rating_color = self.style.SUCCESS if result['rating'] in ['Excellent', 'Good'] else self.style.WARNING
                self.stdout.write(
                    f"  {result['contractor']}: {result['score']}% "
                    f"({rating_color(result['rating'])}) - Risk: {result['risk_level']}"
                )
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f"✅ Calculated for {len(results)} contractors"))

        self.stdout.write(self.style.SUCCESS('=' * 60))