#!/usr/bin/env python
"""Check IGCSE Physics topics in database"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assessment_v3.settings')
django.setup()

from core.models import Topic, Subject, Grade, Question

# Find IGCSE grade
igcse_grades = Grade.objects.filter(name__icontains='IGCSE')
print(f"IGCSE Grades found: {igcse_grades.count()}")
for g in igcse_grades:
    print(f"  - {g.name} (ID: {g.id})")

# Find Physics subject
physics_subjects = Subject.objects.filter(name__icontains='Physics')
print(f"\nPhysics Subjects found: {physics_subjects.count()}")
for s in physics_subjects:
    print(f"  - {s.name} (ID: {s.id})")

# Get topics for each combination
for grade in igcse_grades:
    for subject in physics_subjects:
        topics = Topic.objects.filter(grade=grade, subject=subject)
        print(f"\n{grade.name} - {subject.name} Topics ({topics.count()}):")
        for t in topics[:30]:
            print(f"  - {t.name} (ID: {t.id})")

# Check for "Alternating Currents" topic
alt_current = Topic.objects.filter(name__icontains='Alternating')
print(f"\n'Alternating' topics found: {alt_current.count()}")
for t in alt_current:
    print(f"  - {t.name} (Grade: {t.grade.name}, Subject: {t.subject.name}, ID: {t.id})")

# Check questions tagged with wrong topic
wrong_topic_questions = Question.objects.filter(topic__name__icontains='Alternating')
print(f"\nQuestions tagged with 'Alternating' topic: {wrong_topic_questions.count()}")
for q in wrong_topic_questions[:5]:
    print(f"  Q{q.id}: Grade={q.grade.name}, Subject={q.subject.name}, Topic={q.topic.name}")
