from django.core.management.base import BaseCommand
from apps.contractor.models import DocumentType, PreQualificationQuestion


class Command(BaseCommand):
    help = 'Update onboarding data - remove mandatory flag from all items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--status',
            type=str,
            choices=['remove', 'add'],
            default='remove',
            help='Remove or add mandatory flag (default: remove)'
        )

    def handle(self, *args, **options):
        status = options['status']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        if status == 'remove':
            self.stdout.write(self.style.SUCCESS('REMOVING MANDATORY FLAG FROM ALL ITEMS'))
        else:
            self.stdout.write(self.style.SUCCESS('ADDING MANDATORY FLAG TO ALL ITEMS'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # Update Document Types
        self.stdout.write('\n📄 Updating Document Types...')
        self.stdout.write('-' * 40)
        
        doc_count_before = DocumentType.objects.count()
        mandatory_docs_before = DocumentType.objects.filter(is_mandatory=True).count()
        
        if status == 'remove':
            doc_count = DocumentType.objects.all().update(is_mandatory=False)
        else:
            doc_count = DocumentType.objects.all().update(is_mandatory=True)
        
        mandatory_docs_after = DocumentType.objects.filter(is_mandatory=True).count()
        
        self.stdout.write(f'  Total Document Types: {doc_count_before}')
        self.stdout.write(f'  Mandatory before: {mandatory_docs_before}')
        self.stdout.write(self.style.SUCCESS(f'  ✅ Updated {doc_count} document types'))
        self.stdout.write(f'  Mandatory after: {mandatory_docs_after}')

        # Update Pre-Qualification Questions
        self.stdout.write('\n📋 Updating Pre-Qualification Questions...')
        self.stdout.write('-' * 40)
        
        q_count_before = PreQualificationQuestion.objects.count()
        mandatory_qs_before = PreQualificationQuestion.objects.filter(is_mandatory=True).count()
        
        if status == 'remove':
            q_count = PreQualificationQuestion.objects.all().update(is_mandatory=False)
        else:
            q_count = PreQualificationQuestion.objects.all().update(is_mandatory=True)
        
        mandatory_qs_after = PreQualificationQuestion.objects.filter(is_mandatory=True).count()
        
        self.stdout.write(f'  Total Questions: {q_count_before}')
        self.stdout.write(f'  Mandatory before: {mandatory_qs_before}')
        self.stdout.write(self.style.SUCCESS(f'  ✅ Updated {q_count} pre-qualification questions'))
        self.stdout.write(f'  Mandatory after: {mandatory_qs_after}')

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📊 SUMMARY'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'  Document Types: {DocumentType.objects.count()}')
        self.stdout.write(f'  Mandatory Documents: {mandatory_docs_after}')
        self.stdout.write(f'  Pre-Qualification Questions: {PreQualificationQuestion.objects.count()}')
        self.stdout.write(f'  Mandatory Questions: {mandatory_qs_after}')
        
        if status == 'remove':
            self.stdout.write(self.style.SUCCESS('\n✅ All mandatory flags removed successfully!'))
            self.stdout.write(self.style.WARNING('\n⚠️  Note: Now no items are mandatory. Users can select any items they want to send.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ All mandatory flags added successfully!'))
            self.stdout.write(self.style.WARNING('\n⚠️  Note: All items are now mandatory. Users cannot unselect them.'))