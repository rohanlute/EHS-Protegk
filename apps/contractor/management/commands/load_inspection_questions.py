# apps/contractor/management/commands/load_inspection_questions.py

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
from apps.contractor.models import ContractorInspectionQuestion


class Command(BaseCommand):
    help = 'Load pre-defined contractor inspection questions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing questions before loading new ones',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be loaded without actually saving',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        clear = options.get('clear', False)

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(' Contractor Inspection Questions Loader '))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY RUN MODE - No changes will be saved'))
            self.stdout.write('')

        if clear and not dry_run:
            with transaction.atomic():
                count = ContractorInspectionQuestion.objects.count()
                ContractorInspectionQuestion.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'🗑️  Cleared {count} existing questions'))

        # ==========================================================
        # 1. PPE Questions
        # ==========================================================
        ppe_questions = [
            'Are all workers wearing appropriate safety helmets?',
            'Are workers wearing proper safety shoes with steel toe protection?',
            'Are workers wearing required hand gloves for their specific task?',
            'Is eye protection (safety glasses/goggles) being used where required?',
            'Is hearing protection being used in high-noise areas?',
            'Are workers wearing high-visibility vests where required?',
            'Is full body harness being used for work at height?',
            'Are workers wearing appropriate respiratory protection in dusty/hazardous areas?',
            'Is all PPE in good condition (no damage, wear, or tears)?',
            'Are workers trained on proper use and maintenance of their PPE?'
        ]

        # ==========================================================
        # 2. Safety Questions
        # ==========================================================
        safety_questions = [
            'Are all electrical tools and equipment properly grounded and in good condition?',
            'Is there proper guarding on all moving machinery parts?',
            'Are fire extinguishers accessible, properly charged, and inspected?',
            'Are emergency exits clearly marked and unobstructed?',
            'Is proper lockout/tagout being followed for equipment maintenance?',
            'Are all work areas properly barricaded and marked?',
            'Are warning signs and caution tapes properly displayed?',
            'Is there proper ventilation in confined spaces or enclosed areas?',
            'Are all chemical containers properly labeled with MSDS available?',
            'Is safe work permit system being followed for high-risk activities?',
            'Are all workers following safe work practices and procedures?',
            'Is there proper fall protection for work at height (above 1.8 meters)?',
            'Are all lifting equipment and slings inspected and in good condition?',
            'Is safe storage maintained for flammable and hazardous materials?',
            'Are all safety interlocks and emergency stop buttons functional?'
        ]

        # ==========================================================
        # 3. Housekeeping Questions
        # ==========================================================
        housekeeping_questions = [
            'Is the work area clean and free from debris and waste materials?',
            'Are all walkways and passageways clear and unobstructed?',
            'Is proper waste segregation (hazardous, non-hazardous, recyclable) being followed?',
            'Are storage areas organized and materials properly stacked?',
            'Are spill kits readily available and properly maintained?',
            'Is proper lighting maintained in all work areas?',
            'Are emergency exits and fire escape routes clear and accessible?',
            'Is waste disposed of properly and in a timely manner?',
            'Are all tools and equipment stored properly after use?',
            'Is the area free from slip, trip, and fall hazards?',
            'Are first aid boxes available and fully stocked?',
            'Is proper signage displayed for restricted areas and hazards?'
        ]

        # ==========================================================
        # 4. Contractor Management Questions
        # ==========================================================
        contractor_management_questions = [
            'Is the contractor\'s supervisor present at the work site?',
            'Are all contractor workers authorized and registered for this site?',
            'Is the contractor\'s training compliance record up to date?',
            'Are all required work permits available and valid?',
            'Is the contractor\'s insurance coverage valid and adequate?',
            'Does the contractor have valid registration and licensing documents?',
            'Are the required job safety analysis (JSA) documents available?',
            'Is the contractor\'s accident/incident reporting system in place?',
            'Are contractor workers medically fit for their assigned tasks?',
            'Has the contractor completed the mandatory site safety induction?',
            'Are the contractor\'s tools and equipment regularly maintained and inspected?',
            'Does the contractor have an emergency response plan in place?',
            'Is the contractor maintaining proper attendance and man-hours records?',
            'Are all contractor vehicles and equipment properly maintained and safe?',
            'Does the contractor have a valid environmental clearance if required?'
        ]

        # ==========================================================
        # Create questions in order
        # ==========================================================
        order = 1
        total_created = 0
        total_skipped = 0
        total_questions = (
            len(ppe_questions) + 
            len(safety_questions) + 
            len(housekeeping_questions) + 
            len(contractor_management_questions)
        )

        self.stdout.write(f'📝 Total questions to load: {total_questions}')
        self.stdout.write('')

        def create_questions(questions_list, category, start_order):
            nonlocal order, total_created, total_skipped
            count = 0
            
            for question_text in questions_list:
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] Would create: {category} - {question_text[:50]}...')
                    count += 1
                    order += 1
                    continue

                try:
                    # Check if question already exists with same category and text
                    existing = ContractorInspectionQuestion.objects.filter(
                        category=category,
                        question_text=question_text
                    ).first()

                    if existing:
                        self.stdout.write(self.style.WARNING(f'  ⚠️  Skipping duplicate: {category} - {question_text[:50]}...'))
                        total_skipped += 1
                    else:
                        question = ContractorInspectionQuestion.objects.create(
                            category=category,
                            question_text=question_text,
                            display_order=order,
                            is_active=True
                        )
                        total_created += 1
                        count += 1
                        self.stdout.write(self.style.SUCCESS(f'  ✅ Created: {category} - {question_text[:50]}... (Order: {order})'))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ❌ Error creating question: {str(e)}'))
                
                order += 1
            
            return count

        if not dry_run:
            with transaction.atomic():
                # Create PPE Questions
                self.stdout.write(self.style.WARNING('📋 Creating PPE Questions...'))
                create_questions(ppe_questions, 'PPE', order)

                # Create Safety Questions
                self.stdout.write(self.style.WARNING('📋 Creating Safety Questions...'))
                create_questions(safety_questions, 'SAFETY', order)

                # Create Housekeeping Questions
                self.stdout.write(self.style.WARNING('📋 Creating Housekeeping Questions...'))
                create_questions(housekeeping_questions, 'HOUSEKEEPING', order)

                # Create Contractor Management Questions
                self.stdout.write(self.style.WARNING('📋 Creating Contractor Management Questions...'))
                create_questions(contractor_management_questions, 'CONTRACTOR_MANAGEMENT', order)

        else:
            # Dry run - just count
            ppe_count = len(ppe_questions)
            safety_count = len(safety_questions)
            housekeeping_count = len(housekeeping_questions)
            contractor_count = len(contractor_management_questions)
            
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('📊 DRY RUN SUMMARY:'))
            self.stdout.write(f'  PPE: {ppe_count} questions')
            self.stdout.write(f'  Safety: {safety_count} questions')
            self.stdout.write(f'  Housekeeping: {housekeeping_count} questions')
            self.stdout.write(f'  Contractor Management: {contractor_count} questions')
            self.stdout.write(f'  TOTAL: {total_questions} questions')

        # ==========================================================
        # Summary
        # ==========================================================
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(' 📊 SUMMARY '))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY RUN - No changes were saved'))
        else:
            self.stdout.write(f'✅ Total created: {total_created}')
            self.stdout.write(f'⏭️  Total skipped (duplicates): {total_skipped}')
            self.stdout.write(f'📝 Total questions in database: {ContractorInspectionQuestion.objects.count()}')

            if total_created > 0:
                self.stdout.write(self.style.SUCCESS('\n🎉 Questions loaded successfully!'))
            elif total_skipped > 0 and total_created == 0:
                self.stdout.write(self.style.WARNING('\n⚠️  All questions already exist. No new questions were created.'))

        self.stdout.write(self.style.SUCCESS('=' * 60))


# ==========================================================
# ALTERNATIVE: Delete and Load All Questions
# ==========================================================

class CommandDeleteAndLoad(BaseCommand):
    """
    Alternative command to delete all questions and load fresh.
    Usage: python manage.py load_inspection_questions --clear
    """
    help = 'Delete all existing questions and load fresh'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('⚠️  This will delete ALL existing questions!'))
        confirm = input('Are you sure? Type "yes" to continue: ')

        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('❌ Aborted.'))
            return

        call_command('load_inspection_questions', clear=True)