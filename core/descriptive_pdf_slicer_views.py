"""
Descriptive PDF Slicer Views
Handles multi-page structured questions with green/red line detection
Matches MCQ slicer UI and auto-detection pattern
"""

import json
import base64
import hashlib
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.contrib import messages
import fitz  # PyMuPDF

from .models import (
    Question, Grade, Subject, Topic, LearningObjective,
    QuestionPage, AnswerSpace, ProcessedPDF
)
from .utils.paper_component_detector import parse_paper_code, is_theory_paper
from .utils.image_processing import detect_page_markers, detect_blue_rectangle


@login_required
@staff_member_required
def descriptive_pdf_slicer(request):
    """
    Main view for descriptive PDF slicer
    Matches MCQ slicer UI and workflow
    """
    grades = Grade.objects.all()
    subjects = Subject.objects.all()

    if request.method == 'POST':
        try:
            grade_id = request.POST.get('grade_id')
            subject_id = request.POST.get('subject_id')
            year = request.POST.get('year')
            total_questions = int(request.POST.get('total_questions', 0))

            if not all([grade_id, subject_id]):
                return JsonResponse({'error': 'Missing grade or subject'}, status=400)

            # Get first topic for this subject
            topic = Topic.objects.filter(subject_id=subject_id).first()
            if not topic:
                return JsonResponse({'error': 'No topics found for this subject'}, status=400)

            imported_count = 0

            for i in range(total_questions):
                question_data_json = request.POST.get(f'question_{i}')
                if not question_data_json:
                    continue

                question_data = json.loads(question_data_json)
                pages_data = question_data.get('pages', [])
                markscheme = question_data.get('markscheme', '')
                marks = question_data.get('marks', 5)

                if not pages_data:
                    continue

                # Create Question
                question = Question.objects.create(
                    question_text='',  # Will be set to stitched image
                    answer_text=markscheme,
                    marks=marks,
                    question_type='structured',
                    year=int(year) if year else None,
                    grade_id=grade_id,
                    subject_id=subject_id,
                    topic_id=topic.id,
                    created_by=request.user
                )

                # Save individual pages
                for page in pages_data:
                    QuestionPage.objects.create(
                        question=question,
                        page_number=page['page_number'],
                        page_image=page['page_image'],
                        has_green_line=page.get('has_green_line', False),
                        has_red_line=page.get('has_red_line', False),
                        blue_rect_x=page.get('blue_rect_x'),
                        blue_rect_y=page.get('blue_rect_y'),
                        blue_rect_width=page.get('blue_rect_width'),
                        blue_rect_height=page.get('blue_rect_height'),
                    )

                # Stitch pages for preview
                try:
                    from .utils.image_processing import stitch_question_pages
                    stitched_image = stitch_question_pages(pages_data)
                    question.question_text = stitched_image
                    question.save()
                except Exception as e:
                    print(f"Error stitching pages: {e}")

                imported_count += 1

            messages.success(request, f'Successfully imported {imported_count} structured questions!')
            return JsonResponse({'success': True, 'count': imported_count})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    context = {
        'grades': grades,
        'subjects': subjects,
    }

    return render(request, 'teacher/import_descriptive_pdf.html', context)
