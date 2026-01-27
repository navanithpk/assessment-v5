#!/usr/bin/env python
"""Fix questions tagged with wrong-grade topics"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assessment_v3.settings')
django.setup()

from core.models import Question, Topic, Grade, Subject

# Find questions where topic.grade != question.grade
mismatched = Question.objects.exclude(topic__isnull=True).select_related('grade', 'subject', 'topic').exclude(
    topic__grade=django.db.models.F('grade')
)

print(f"Questions with mismatched topic grades: {mismatched.count()}")

for q in mismatched[:10]:
    print(f"\nQ{q.id}:")
    print(f"  Question Grade: {q.grade.name}")
    print(f"  Topic: {q.topic.name}")
    print(f"  Topic Grade: {q.topic.grade.name}")

# Ask if we should fix them
if mismatched.count() > 0:
    response = input(f"\nFix all {mismatched.count()} questions? (yes/no): ")
    if response.lower() == 'yes':
        fixed = 0
        for q in mismatched:
            # Find a valid topic for this question's grade and subject
            valid_topic = Topic.objects.filter(
                grade=q.grade,
                subject=q.subject
            ).first()

            if valid_topic:
                q.topic = valid_topic
                q.save()
                fixed += 1
                print(f"  Fixed Q{q.id}: {valid_topic.name}")
            else:
                print(f"  ⚠️ No valid topic found for Q{q.id} ({q.grade.name} - {q.subject.name})")

        print(f"\n✓ Fixed {fixed} questions")
        print("These questions now have placeholder topics from the correct grade.")
        print("Re-run AI tagging to assign more accurate topics.")
