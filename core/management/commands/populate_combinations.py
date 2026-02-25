"""
Management command to populate default subject-grade combinations
Usage: python manage.py populate_combinations
"""
from django.core.management.base import BaseCommand
from core.models import Subject, Grade, SubjectGradeCombination


class Command(BaseCommand):
    help = 'Populate default subject-grade combinations for IGCSE and AS/A Levels'

    def handle(self, *args, **options):
        # Define default combinations
        combinations = [
            # IGCSE Science
            {
                'code': '0610',
                'name': 'IGCSE Biology',
                'subject_name': 'Biology',
                'subject_code': '0610',
                'grade_name': 'IGCSE',
                'level': 'igcse',
                'description': 'Cambridge IGCSE Biology'
            },
            {
                'code': '0620',
                'name': 'IGCSE Chemistry',
                'subject_name': 'Chemistry',
                'subject_code': '0620',
                'grade_name': 'IGCSE',
                'level': 'igcse',
                'description': 'Cambridge IGCSE Chemistry'
            },
            {
                'code': '0625',
                'name': 'IGCSE Physics',
                'subject_name': 'Physics',
                'subject_code': '0625',
                'grade_name': 'IGCSE',
                'level': 'igcse',
                'description': 'Cambridge IGCSE Physics'
            },

            # AS & A Level Science
            {
                'code': '9700',
                'name': 'AS & A Level Biology',
                'subject_name': 'Biology',
                'subject_code': '9700',
                'grade_name': 'AS & A Level',
                'level': 'as_a_level',
                'description': 'Cambridge International AS & A Level Biology'
            },
            {
                'code': '9701',
                'name': 'AS & A Level Chemistry',
                'subject_name': 'Chemistry',
                'subject_code': '9701',
                'grade_name': 'AS & A Level',
                'level': 'as_a_level',
                'description': 'Cambridge International AS & A Level Chemistry'
            },
            {
                'code': '9702',
                'name': 'AS & A Level Physics',
                'subject_name': 'Physics',
                'subject_code': '9702',
                'grade_name': 'AS & A Level',
                'level': 'as_a_level',
                'description': 'Cambridge International AS & A Level Physics'
            },

            # AS Level only
            {
                'code': '9700-AS',
                'name': 'AS Level Biology',
                'subject_name': 'Biology',
                'subject_code': '9700',
                'grade_name': 'AS Level',
                'level': 'as_level',
                'description': 'Cambridge International AS Level Biology'
            },
            {
                'code': '9701-AS',
                'name': 'AS Level Chemistry',
                'subject_name': 'Chemistry',
                'subject_code': '9701',
                'grade_name': 'AS Level',
                'level': 'as_level',
                'description': 'Cambridge International AS Level Chemistry'
            },
            {
                'code': '9702-AS',
                'name': 'AS Level Physics',
                'subject_name': 'Physics',
                'subject_code': '9702',
                'grade_name': 'AS Level',
                'level': 'as_level',
                'description': 'Cambridge International AS Level Physics'
            },

            # A Level only
            {
                'code': '9700-A',
                'name': 'A Level Biology',
                'subject_name': 'Biology',
                'subject_code': '9700',
                'grade_name': 'A Level',
                'level': 'a_level',
                'description': 'Cambridge International A Level Biology'
            },
            {
                'code': '9701-A',
                'name': 'A Level Chemistry',
                'subject_name': 'Chemistry',
                'subject_code': '9701',
                'grade_name': 'A Level',
                'level': 'a_level',
                'description': 'Cambridge International A Level Chemistry'
            },
            {
                'code': '9702-A',
                'name': 'A Level Physics',
                'subject_name': 'Physics',
                'subject_code': '9702',
                'grade_name': 'A Level',
                'level': 'a_level',
                'description': 'Cambridge International A Level Physics'
            },
        ]

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for combo_data in combinations:
            # Get or create subject
            subject, subject_created = Subject.objects.get_or_create(
                name=combo_data['subject_name'],
                defaults={'code': combo_data['subject_code'], 'description': ''}
            )

            # Update code if subject exists but doesn't have code
            if not subject.code:
                subject.code = combo_data['subject_code']
                subject.save()

            # Get or create grade
            grade, grade_created = Grade.objects.get_or_create(
                name=combo_data['grade_name']
            )

            # Get or create combination
            combination, combo_created = SubjectGradeCombination.objects.get_or_create(
                code=combo_data['code'],
                defaults={
                    'name': combo_data['name'],
                    'subject': subject,
                    'grade': grade,
                    'level': combo_data['level'],
                    'description': combo_data['description'],
                    'is_active': True
                }
            )

            if combo_created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created: {combo_data['code']} - {combo_data['name']}")
                )
            else:
                # Update existing
                updated = False
                if combination.name != combo_data['name']:
                    combination.name = combo_data['name']
                    updated = True
                if combination.description != combo_data['description']:
                    combination.description = combo_data['description']
                    updated = True

                if updated:
                    combination.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f"Updated: {combo_data['code']} - {combo_data['name']}")
                    )
                else:
                    skipped_count += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS(f"Summary:"))
        self.stdout.write(self.style.SUCCESS(f"  - Created: {created_count}"))
        self.stdout.write(self.style.SUCCESS(f"  - Updated: {updated_count}"))
        self.stdout.write(self.style.SUCCESS(f"  - Skipped (already exists): {skipped_count}"))
        self.stdout.write(self.style.SUCCESS(f"  - Total: {len(combinations)}"))
        self.stdout.write(self.style.SUCCESS('='*60))
