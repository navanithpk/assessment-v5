"""
Management command to set up separate database files for each QuestionBank
Usage: python manage.py setup_question_databases
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import QuestionBank, SubjectGradeCombination
import os


class Command(BaseCommand):
    help = 'Set up separate database files for each QuestionBank DLC'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-all',
            action='store_true',
            help='Create databases for all active QuestionBanks',
        )
        parser.add_argument(
            '--combination',
            type=str,
            help='Create database for specific combination code (e.g., 9702)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('📦 Question Bank Database Setup'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write('')

        # Create databases directory
        db_dir = os.path.join(settings.BASE_DIR, 'question_databases')
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            self.stdout.write(self.style.SUCCESS(f'✅ Created directory: {db_dir}'))

        if options['combination']:
            # Create database for specific combination
            code = options['combination']
            combination = SubjectGradeCombination.objects.filter(code=code).first()

            if not combination:
                self.stdout.write(self.style.ERROR(f'❌ Combination {code} not found'))
                return

            self._create_database_for_combination(combination, db_dir)

        elif options['create_all']:
            # Create databases for all combinations
            combinations = SubjectGradeCombination.objects.filter(is_active=True)

            self.stdout.write(f'Found {combinations.count()} active combinations')
            self.stdout.write('')

            for combination in combinations:
                self._create_database_for_combination(combination, db_dir)

        else:
            # Show current status
            self._show_status(db_dir)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('✅ Setup Complete!'))
        self.stdout.write(self.style.SUCCESS('='*60))

    def _create_database_for_combination(self, combination, db_dir):
        """Create database file for a specific combination"""
        code = combination.code
        name = combination.name

        # Generate database filename
        db_filename = f"{code.lower()}.db"
        db_path = os.path.join(db_dir, db_filename)

        self.stdout.write(f'📦 {code} - {name}')

        # Check if database file already exists
        if os.path.exists(db_path):
            self.stdout.write(f'   ⚠️  Database file already exists: {db_filename}')
        else:
            # Create empty database file
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.close()
            self.stdout.write(f'   ✅ Created: {db_filename}')

        # Update QuestionBank records for all schools
        banks = QuestionBank.objects.filter(
            subject=combination.subject,
            grade=combination.grade
        )

        for bank in banks:
            bank.database_file = db_path
            bank.save()

        if banks.exists():
            self.stdout.write(f'   ✅ Updated {banks.count()} QuestionBank record(s)')
        else:
            self.stdout.write(f'   ℹ️  No QuestionBank created yet for this combination')

        self.stdout.write('')

    def _show_status(self, db_dir):
        """Show current database status"""
        self.stdout.write('Current Status:')
        self.stdout.write('')

        combinations = SubjectGradeCombination.objects.filter(is_active=True).order_by('code')

        for combination in combinations:
            code = combination.code
            name = combination.name
            db_filename = f"{code.lower()}.db"
            db_path = os.path.join(db_dir, db_filename)

            exists = '✅' if os.path.exists(db_path) else '❌'
            banks_count = QuestionBank.objects.filter(
                subject=combination.subject,
                grade=combination.grade
            ).count()

            self.stdout.write(f'{exists} {code:10} {name:40} (Banks: {banks_count})')

        self.stdout.write('')
        self.stdout.write('Commands:')
        self.stdout.write('  --create-all              Create databases for all combinations')
        self.stdout.write('  --combination 9702        Create database for specific combination')
