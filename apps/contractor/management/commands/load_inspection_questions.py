from django.core.management.base import BaseCommand
from apps.contractor.models import DocumentType, PreQualificationQuestion


class Command(BaseCommand):
    help = 'Initialize pre-qualification questions and document types for onboarding'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('CREATING ONBOARDING DATA'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # Create Document Types
        document_types = [
            {'name': 'Company Registration Certificate', 'code': 'COMPANY_REGISTRATION', 'is_mandatory': True},
            {'name': 'PAN Card Copy', 'code': 'PAN', 'is_mandatory': True},
            {'name': 'GST Registration Certificate', 'code': 'GST', 'is_mandatory': True},
            {'name': 'Contractor License / Registration', 'code': 'CONTRACTOR_LICENSE', 'is_mandatory': True},
            {'name': 'PF Registration', 'code': 'PF', 'is_mandatory': False},
            {'name': 'ESIC Registration', 'code': 'ESIC', 'is_mandatory': False},
            {'name': 'Insurance Policy - General', 'code': 'INSURANCE', 'is_mandatory': True},
            {'name': 'Workmen Compensation Insurance', 'code': 'WORKMEN_COMPENSATION', 'is_mandatory': True},
            {'name': 'Public Liability Insurance', 'code': 'PUBLIC_LIABILITY', 'is_mandatory': True},
            {'name': 'Safety Policy Document', 'code': 'SAFETY_POLICY', 'is_mandatory': True},
            {'name': 'EHS Certification', 'code': 'EHS_CERTIFICATION', 'is_mandatory': False},
        ]

        self.stdout.write('\n📄 Creating Document Types...')
        self.stdout.write('-' * 40)
        for data in document_types:
            obj, created = DocumentType.objects.get_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'is_mandatory': data['is_mandatory'],
                    'description': f"{data['name']} document for contractor verification",
                    'is_active': True
                }
            )
            status = '✅ Created' if created else '⏩ Already exists'
            mandatory = '🔴 Mandatory' if data['is_mandatory'] else '⚪ Optional'
            self.stdout.write(f'  {status}: {obj.name} ({mandatory})')

        # Create Pre-Qualification Questions
        questions = [
            # Experience
            {'question': 'Does the contractor have at least 5 years of experience in similar work?', 'question_type': 'EXPERIENCE', 'is_mandatory': True, 'sequence': 1},
            {'question': 'Has the contractor completed at least 3 similar projects in the last 3 years?', 'question_type': 'EXPERIENCE', 'is_mandatory': True, 'sequence': 2},
            {'question': 'Does the contractor have a proven track record with major clients?', 'question_type': 'EXPERIENCE', 'is_mandatory': False, 'sequence': 3},
            # EHS Performance
            {'question': 'Has the contractor had any major accidents in the last 3 years?', 'question_type': 'EHS_PERFORMANCE', 'is_mandatory': True, 'sequence': 4},
            {'question': 'Has the contractor had any fatalities at their work sites?', 'question_type': 'EHS_PERFORMANCE', 'is_mandatory': True, 'sequence': 5},
            {'question': 'Has the contractor faced any regulatory violations or penalties?', 'question_type': 'EHS_PERFORMANCE', 'is_mandatory': True, 'sequence': 6},
            {'question': 'Does the contractor maintain a positive EHS performance record?', 'question_type': 'EHS_PERFORMANCE', 'is_mandatory': False, 'sequence': 7},
            # Safety Capability
            {'question': 'Does the contractor have a dedicated safety team/manager?', 'question_type': 'SAFETY_CAPABILITY', 'is_mandatory': True, 'sequence': 8},
            {'question': 'Does the contractor have a documented Safety Policy?', 'question_type': 'SAFETY_CAPABILITY', 'is_mandatory': True, 'sequence': 9},
            {'question': 'Does the contractor have a formal training system in place?', 'question_type': 'SAFETY_CAPABILITY', 'is_mandatory': True, 'sequence': 10},
            {'question': 'Does the contractor have emergency preparedness and response plans?', 'question_type': 'SAFETY_CAPABILITY', 'is_mandatory': True, 'sequence': 11},
            {'question': 'Has the contractor provided safety training to all employees?', 'question_type': 'SAFETY_CAPABILITY', 'is_mandatory': False, 'sequence': 12},
            # Technical Capability
            {'question': 'Does the contractor have adequate equipment and resources for the work?', 'question_type': 'TECHNICAL_CAPABILITY', 'is_mandatory': True, 'sequence': 13},
            {'question': 'Does the contractor have qualified and skilled workforce?', 'question_type': 'TECHNICAL_CAPABILITY', 'is_mandatory': True, 'sequence': 14},
            {'question': 'Does the contractor have relevant certifications/qualifications?', 'question_type': 'TECHNICAL_CAPABILITY', 'is_mandatory': False, 'sequence': 15},
            # Insurance
            {'question': 'Does the contractor have valid insurance coverage?', 'question_type': 'INSURANCE', 'is_mandatory': True, 'sequence': 16},
            {'question': 'Does the contractor have Workmen Compensation Insurance?', 'question_type': 'INSURANCE', 'is_mandatory': True, 'sequence': 17},
            {'question': 'Does the contractor have Public Liability Insurance?', 'question_type': 'INSURANCE', 'is_mandatory': True, 'sequence': 18},
            # Financial
            {'question': 'Does the contractor have a stable financial standing?', 'question_type': 'FINANCIAL', 'is_mandatory': True, 'sequence': 19},
            {'question': 'Does the contractor have audited financial statements for the last 2 years?', 'question_type': 'FINANCIAL', 'is_mandatory': False, 'sequence': 20},
        ]

        self.stdout.write('\n📋 Creating Pre-Qualification Questions...')
        self.stdout.write('-' * 40)
        for data in questions:
            obj, created = PreQualificationQuestion.objects.get_or_create(
                question=data['question'],
                defaults={
                    'question_type': data['question_type'],
                    'is_mandatory': data['is_mandatory'],
                    'sequence': data['sequence']
                }
            )
            status = '✅ Created' if created else '⏩ Already exists'
            mandatory = '🔴 Mandatory' if data['is_mandatory'] else '⚪ Optional'
            self.stdout.write(f'  {status}: {obj.question[:50]}... ({mandatory})')

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📊 SUMMARY'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'  Document Types: {DocumentType.objects.count()}')
        self.stdout.write(f'  Pre-Qualification Questions: {PreQualificationQuestion.objects.count()}')
        self.stdout.write('\n' + self.style.SUCCESS('✅ All data created successfully!'))