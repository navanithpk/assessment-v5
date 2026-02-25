"""
Management command to migrate questions from main database to dedicated question databases.
Usage:
    python manage.py migrate_questions_to_dlc --all
    python manage.py migrate_questions_to_dlc --combination 9702
    python manage.py migrate_questions_to_dlc --dry-run
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from core.models import (
    Question, TestQuestion, StudentAnswer,
    QuestionBank, SubjectGradeCombination,
    Subject, Grade
)
import sqlite3
import os
import json


class Command(BaseCommand):
    help = 'Migrate questions from main database to dedicated question bank databases'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Migrate questions for all active combinations',
        )
        parser.add_argument(
            '--combination',
            type=str,
            help='Migrate questions for specific combination code (e.g., 9702)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes',
        )
        parser.add_argument(
            '--delete-after',
            action='store_true',
            help='Delete questions from main DB after successful migration',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('📦 Question Migration Tool'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write('')

        self.dry_run = options['dry_run']
        self.delete_after = options['delete_after']

        if self.dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
            self.stdout.write('')

        # Ensure question_databases directory exists
        db_dir = os.path.join(settings.BASE_DIR, 'question_databases')
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        if options['combination']:
            # Migrate specific combination
            code = options['combination']
            self._migrate_combination(code, db_dir)
        elif options['all']:
            # Migrate all active combinations
            combinations = SubjectGradeCombination.objects.filter(is_active=True)
            self.stdout.write(f'Found {combinations.count()} active combinations')
            self.stdout.write('')

            for combo in combinations:
                self._migrate_combination(combo.code, db_dir)
        else:
            # Show status and help
            self._show_status(db_dir)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('✅ Migration Complete!'))
        self.stdout.write(self.style.SUCCESS('='*60))

    def _migrate_combination(self, code, db_dir):
        """Migrate questions for a specific combination code"""
        self.stdout.write(f'\n📦 Processing: {code}')
        self.stdout.write('-' * 40)

        # Find the combination
        try:
            combo = SubjectGradeCombination.objects.get(code=code)
        except SubjectGradeCombination.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'   ❌ Combination {code} not found'))
            return

        subject = combo.subject
        grade = combo.grade

        # Find questions to migrate
        questions = Question.objects.filter(subject=subject, grade=grade)
        question_count = questions.count()

        if question_count == 0:
            self.stdout.write(f'   ℹ️  No questions found for {code}')
            return

        self.stdout.write(f'   📊 Found {question_count} questions to migrate')

        # Prepare target database
        db_filename = f"{code.lower()}.db"
        db_path = os.path.join(db_dir, db_filename)

        if not os.path.exists(db_path):
            self.stdout.write(f'   ⚠️  Database file not found: {db_filename}')
            self.stdout.write(f'   💡 Run: python manage.py setup_question_databases --combination {code}')
            return

        if self.dry_run:
            self.stdout.write(f'   🔍 Would migrate {question_count} questions to {db_filename}')
            self._show_sample_questions(questions[:5])
            return

        # Perform migration
        try:
            migrated_count = self._copy_questions_to_db(questions, db_path, subject, grade)
            self.stdout.write(self.style.SUCCESS(f'   ✅ Migrated {migrated_count} questions to {db_filename}'))

            # Optionally delete from main DB
            if self.delete_after and migrated_count > 0:
                self._delete_migrated_questions(questions)
                self.stdout.write(self.style.WARNING(f'   🗑️  Deleted {migrated_count} questions from main DB'))

            # Update QuestionBank records
            self._update_question_banks(subject, grade, db_path, migrated_count)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Migration failed: {str(e)}'))
            import traceback
            traceback.print_exc()

    def _copy_questions_to_db(self, questions, db_path, subject, grade):
        """Copy questions to the target SQLite database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create the questions table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS core_question (
                id INTEGER PRIMARY KEY,
                grade_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                year INTEGER,
                question_text TEXT NOT NULL,
                answer_text TEXT,
                marks INTEGER DEFAULT 1,
                question_type VARCHAR(20) NOT NULL,
                parts_config TEXT,
                created_by_id INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
        ''')

        # Create learning objectives junction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS core_question_learning_objectives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                learningobjective_id INTEGER NOT NULL,
                UNIQUE(question_id, learningobjective_id)
            )
        ''')

        # Create TestQuestion table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS core_testquestion (
                id INTEGER PRIMARY KEY,
                test_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                "order" INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL
            )
        ''')

        # Create StudentAnswer table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS core_studentanswer (
                id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL,
                test_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                answer_text TEXT,
                answer_parts TEXT,
                marks_awarded DECIMAL(5,2),
                submitted_at TIMESTAMP NOT NULL,
                evaluated_at TIMESTAMP,
                evaluated_by_id INTEGER
            )
        ''')

        migrated = 0
        for q in questions:
            try:
                # Convert parts_config to JSON string
                parts_config_str = json.dumps(q.parts_config) if q.parts_config else None

                cursor.execute('''
                    INSERT OR REPLACE INTO core_question
                    (id, grade_id, subject_id, topic_id, year, question_text, answer_text,
                     marks, question_type, parts_config, created_by_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    q.id,
                    q.grade_id,
                    q.subject_id,
                    q.topic_id,
                    q.year,
                    q.question_text,
                    q.answer_text,
                    q.marks,
                    q.question_type,
                    parts_config_str,
                    q.created_by_id,
                    q.created_at.isoformat()
                ))

                # Copy learning objectives
                for lo in q.learning_objectives.all():
                    cursor.execute('''
                        INSERT OR IGNORE INTO core_question_learning_objectives
                        (question_id, learningobjective_id)
                        VALUES (?, ?)
                    ''', (q.id, lo.id))

                # Copy related TestQuestions
                for tq in TestQuestion.objects.filter(question=q):
                    cursor.execute('''
                        INSERT OR REPLACE INTO core_testquestion
                        (id, test_id, question_id, "order", created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        tq.id,
                        tq.test_id,
                        tq.question_id,
                        tq.order,
                        tq.created_at.isoformat()
                    ))

                # Copy related StudentAnswers
                for sa in StudentAnswer.objects.filter(question=q):
                    answer_parts_str = json.dumps(sa.answer_parts) if sa.answer_parts else None
                    cursor.execute('''
                        INSERT OR REPLACE INTO core_studentanswer
                        (id, student_id, test_id, question_id, answer_text, answer_parts,
                         marks_awarded, submitted_at, evaluated_at, evaluated_by_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        sa.id,
                        sa.student_id,
                        sa.test_id,
                        sa.question_id,
                        sa.answer_text,
                        answer_parts_str,
                        float(sa.marks_awarded) if sa.marks_awarded else None,
                        sa.submitted_at.isoformat(),
                        sa.evaluated_at.isoformat() if sa.evaluated_at else None,
                        sa.evaluated_by_id
                    ))

                migrated += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'   ⚠️  Failed to migrate Q{q.id}: {str(e)}'))

        conn.commit()
        conn.close()
        return migrated

    def _delete_migrated_questions(self, questions):
        """Delete migrated questions from main database"""
        # Delete in order to respect FK constraints
        question_ids = list(questions.values_list('id', flat=True))

        # Delete StudentAnswers first
        StudentAnswer.objects.filter(question_id__in=question_ids).delete()

        # Delete TestQuestions
        TestQuestion.objects.filter(question_id__in=question_ids).delete()

        # Delete Questions
        questions.delete()

    def _update_question_banks(self, subject, grade, db_path, question_count):
        """Update QuestionBank records with new database path and count"""
        banks = QuestionBank.objects.filter(subject=subject, grade=grade)

        for bank in banks:
            bank.database_file = db_path
            bank.question_count = question_count
            bank.save()
            self.stdout.write(f'   📝 Updated QuestionBank: {bank.name}')

    def _show_sample_questions(self, questions):
        """Show sample questions that would be migrated"""
        self.stdout.write('   Sample questions:')
        for q in questions:
            text_preview = q.question_text[:50] + '...' if len(q.question_text) > 50 else q.question_text
            text_preview = text_preview.replace('\n', ' ')
            self.stdout.write(f'     - Q{q.id}: {text_preview}')

    def _show_status(self, db_dir):
        """Show current migration status"""
        self.stdout.write('Current Status:')
        self.stdout.write('')
        self.stdout.write(f'{"Code":<10} {"Name":<35} {"Questions":<12} {"DB Exists":<10}')
        self.stdout.write('-' * 70)

        combinations = SubjectGradeCombination.objects.filter(is_active=True).order_by('code')

        for combo in combinations:
            db_filename = f"{combo.code.lower()}.db"
            db_path = os.path.join(db_dir, db_filename)
            db_exists = '✅' if os.path.exists(db_path) else '❌'

            question_count = Question.objects.filter(
                subject=combo.subject,
                grade=combo.grade
            ).count()

            self.stdout.write(f'{combo.code:<10} {combo.name[:35]:<35} {question_count:<12} {db_exists:<10}')

        self.stdout.write('')
        self.stdout.write('Commands:')
        self.stdout.write('  --all                  Migrate all combinations')
        self.stdout.write('  --combination 9702     Migrate specific combination')
        self.stdout.write('  --dry-run              Preview without changes')
        self.stdout.write('  --delete-after         Delete from main DB after migration')
        self.stdout.write('')
        self.stdout.write('Example:')
        self.stdout.write('  python manage.py migrate_questions_to_dlc --combination 9702 --dry-run')
        self.stdout.write('  python manage.py migrate_questions_to_dlc --all --delete-after')
