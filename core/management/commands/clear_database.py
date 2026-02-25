"""
Management command to clear all users and questions from the database
Usage: python manage.py clear_database
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import (
    Question, Test, TestQuestion, StudentAnswer, Student,
    UserProfile, ClassGroup, PDFImportSession, ProcessedPDF
)


class Command(BaseCommand):
    help = 'Clear all users and questions from the database (keeps schools, subjects, grades, topics, LOs, combinations)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without prompting',
        )
        parser.add_argument(
            '--users-only',
            action='store_true',
            help='Delete only users, keep questions',
        )
        parser.add_argument(
            '--questions-only',
            action='store_true',
            help='Delete only questions, keep users',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING('='*60))
            self.stdout.write(self.style.WARNING('⚠️  WARNING: This will delete data!'))
            self.stdout.write(self.style.WARNING('='*60))

            if not options['users_only'] and not options['questions_only']:
                self.stdout.write('This will delete:')
                self.stdout.write('  - All users (except superusers)')
                self.stdout.write('  - All students')
                self.stdout.write('  - All questions')
                self.stdout.write('  - All tests')
                self.stdout.write('  - All student answers')
                self.stdout.write('  - All class groups')
                self.stdout.write('  - All PDF import sessions')
            elif options['users_only']:
                self.stdout.write('This will delete:')
                self.stdout.write('  - All users (except superusers)')
                self.stdout.write('  - All students')
                self.stdout.write('  - All class groups')
            elif options['questions_only']:
                self.stdout.write('This will delete:')
                self.stdout.write('  - All questions')
                self.stdout.write('  - All tests')
                self.stdout.write('  - All student answers')
                self.stdout.write('  - All PDF import sessions')

            self.stdout.write('')
            self.stdout.write(self.style.WARNING('This will KEEP:'))
            self.stdout.write('  - Schools')
            self.stdout.write('  - Subjects')
            self.stdout.write('  - Grades')
            self.stdout.write('  - Topics')
            self.stdout.write('  - Learning Objectives')
            self.stdout.write('  - Subject-Grade Combinations')
            self.stdout.write('  - Question Banks (DLCs)')
            self.stdout.write('  - Superuser accounts')
            self.stdout.write('')

            confirm = input('Type "DELETE" to confirm: ')
            if confirm != 'DELETE':
                self.stdout.write(self.style.ERROR('Cancelled.'))
                return

        # Count before deletion
        self.stdout.write('')
        self.stdout.write('Counting records...')

        users_count = User.objects.filter(is_superuser=False).count()
        students_count = Student.objects.count()
        questions_count = Question.objects.count()
        tests_count = Test.objects.count()
        answers_count = StudentAnswer.objects.count()
        groups_count = ClassGroup.objects.count()
        sessions_count = PDFImportSession.objects.count()

        self.stdout.write(f'Users: {users_count}')
        self.stdout.write(f'Students: {students_count}')
        self.stdout.write(f'Questions: {questions_count}')
        self.stdout.write(f'Tests: {tests_count}')
        self.stdout.write(f'Student Answers: {answers_count}')
        self.stdout.write(f'Class Groups: {groups_count}')
        self.stdout.write(f'PDF Sessions: {sessions_count}')

        # Delete data
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Deleting...'))

        deleted_counts = {}

        if not options['questions_only']:
            # Delete users and related data
            self.stdout.write('Deleting student answers...')
            deleted_counts['StudentAnswer'] = StudentAnswer.objects.all().delete()[0]

            self.stdout.write('Deleting class groups...')
            deleted_counts['ClassGroup'] = ClassGroup.objects.all().delete()[0]

            self.stdout.write('Deleting students...')
            deleted_counts['Student'] = Student.objects.all().delete()[0]

            self.stdout.write('Deleting user profiles...')
            deleted_counts['UserProfile'] = UserProfile.objects.all().delete()[0]

            self.stdout.write('Deleting users (except superusers)...')
            deleted_counts['User'] = User.objects.filter(is_superuser=False).delete()[0]

        if not options['users_only']:
            # Delete questions and related data
            if not options['questions_only']:
                # Already deleted answers above
                pass
            else:
                self.stdout.write('Deleting student answers...')
                deleted_counts['StudentAnswer'] = StudentAnswer.objects.all().delete()[0]

            self.stdout.write('Deleting test questions...')
            deleted_counts['TestQuestion'] = TestQuestion.objects.all().delete()[0]

            self.stdout.write('Deleting tests...')
            deleted_counts['Test'] = Test.objects.all().delete()[0]

            self.stdout.write('Deleting PDF sessions...')
            deleted_counts['PDFImportSession'] = PDFImportSession.objects.all().delete()[0]

            self.stdout.write('Deleting processed PDFs...')
            deleted_counts['ProcessedPDF'] = ProcessedPDF.objects.all().delete()[0]

            self.stdout.write('Deleting questions...')
            deleted_counts['Question'] = Question.objects.all().delete()[0]

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('✅ Deletion Complete!'))
        self.stdout.write(self.style.SUCCESS('='*60))

        for model, count in deleted_counts.items():
            self.stdout.write(self.style.SUCCESS(f'{model}: {count} deleted'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Database cleaned successfully!'))
        self.stdout.write('')
        self.stdout.write('Remaining data:')

        from core.models import School, Subject, Grade, Topic, LearningObjective, SubjectGradeCombination, QuestionBank
        self.stdout.write(f'  - Schools: {School.objects.count()}')
        self.stdout.write(f'  - Subjects: {Subject.objects.count()}')
        self.stdout.write(f'  - Grades: {Grade.objects.count()}')
        self.stdout.write(f'  - Topics: {Topic.objects.count()}')
        self.stdout.write(f'  - Learning Objectives: {LearningObjective.objects.count()}')
        self.stdout.write(f'  - Subject-Grade Combinations: {SubjectGradeCombination.objects.count()}')
        self.stdout.write(f'  - Question Banks: {QuestionBank.objects.count()}')
        self.stdout.write(f'  - Superusers: {User.objects.filter(is_superuser=True).count()}')
