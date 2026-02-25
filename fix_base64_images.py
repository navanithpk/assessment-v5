"""
Fix existing questions that have raw base64 data URLs instead of proper <img> tags
"""

import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assessment_v3.settings')
django.setup()

from core.models import Question

# Pattern to match base64 data URLs that are NOT already in <img> tags
# Matches: data:image/png;base64,iVBORw... but NOT <img src="data:image/png;base64,iVBORw...">
BASE64_PATTERN = r'(?<!src=")(?<!src=\')data:image/[^;]+;base64,[A-Za-z0-9+/=]+'

def fix_questions():
    """
    Find all questions with raw base64 strings and wrap them in <img> tags
    """
    questions = Question.objects.all()
    fixed_count = 0

    for question in questions:
        # Check question_text
        if question.question_text and re.search(BASE64_PATTERN, question.question_text):
            print(f"\nFixing Question ID {question.id}...")
            print(f"  Original length: {len(question.question_text)}")

            # Replace raw base64 with <img> tag
            def replace_base64(match):
                data_url = match.group(0)
                return f'<img src="{data_url}" style="max-width: 100%; height: auto;" />'

            question.question_text = re.sub(BASE64_PATTERN, replace_base64, question.question_text)
            print(f"  New length: {len(question.question_text)}")

            question.save()
            fixed_count += 1

        # Check answer_text
        if question.answer_text and re.search(BASE64_PATTERN, question.answer_text):
            print(f"\nFixing Answer for Question ID {question.id}...")

            def replace_base64(match):
                data_url = match.group(0)
                return f'<img src="{data_url}" style="max-width: 100%; height: auto;" />'

            question.answer_text = re.sub(BASE64_PATTERN, replace_base64, question.answer_text)
            question.save()
            fixed_count += 1

    print(f"\n{'='*60}")
    print(f"[OK] Fixed {fixed_count} questions/answers with raw base64 data")
    print(f"{'='*60}")

if __name__ == '__main__':
    print("[INFO] Scanning for questions with raw base64 image data...")
    print("="*60)
    fix_questions()
