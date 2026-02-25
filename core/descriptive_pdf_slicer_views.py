"""
Descriptive PDF Slicer Views
Handles multi-page structured questions with green/red line detection
Auto-parses Cambridge mark scheme table format
"""

import json
import base64
import hashlib
import re
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


def detect_colored_lines(page, zoom=2):
    """
    Detect horizontal colored lines (red, green, purple) in a PDF page.
    Returns dict with line positions and colors.
    """
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    width = pix.width
    height = pix.height
    samples = pix.samples

    lines = {
        'red': [],
        'green': [],
        'purple': []
    }

    # Scan each row
    y = 0
    while y < height:
        red_count = 0
        green_count = 0
        purple_count = 0
        total = 0

        for x in range(0, width, 5):  # Sample every 5 pixels
            idx = (y * width + x) * 3
            if idx + 2 >= len(samples):
                break

            r = samples[idx]
            g = samples[idx + 1]
            b = samples[idx + 2]
            total += 1

            # Red: high R, low G, low B
            if r > 200 and g < 80 and b < 80:
                red_count += 1
            # Green: low R, high G, low B
            elif g > 150 and r < 100 and b < 100:
                green_count += 1
            # Purple: high R, low G, high B
            elif r > 150 and b > 150 and g < 100:
                purple_count += 1

        threshold = total * 0.15  # 15% of width

        if red_count > threshold:
            lines['red'].append(y / zoom)
        elif green_count > threshold:
            lines['green'].append(y / zoom)
        elif purple_count > threshold:
            lines['purple'].append(y / zoom)

        y += 2

    # Merge nearby lines
    for color in lines:
        merged = []
        for pos in lines[color]:
            if not merged or pos - merged[-1] > 10:
                merged.append(pos)
        lines[color] = merged

    return lines


def extract_page_as_image(page, zoom=2):
    """Extract a page as base64 PNG image."""
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    return f"data:image/png;base64,{base64.b64encode(img_data).decode('utf-8')}"


def extract_region_as_image(page, y_start, y_end, zoom=2):
    """Extract a region of a page as base64 PNG image."""
    rect = fitz.Rect(0, max(0, y_start), page.rect.width, min(page.rect.height, y_end))
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=rect)
    img_data = pix.tobytes("png")
    return f"data:image/png;base64,{base64.b64encode(img_data).decode('utf-8')}"


def parse_cambridge_markscheme(pdf_bytes, start_page=4):
    """
    Parse Cambridge mark scheme table format.
    Table structure: Question | Answer | Marks

    Returns dict: {
        '1': {'parts': {'a': [...], 'b': [...], ...}, 'total_marks': X},
        '2': {...},
        ...
    }
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    markscheme = {}
    current_main_q = None
    current_part = None

    for page_num in range(start_page, len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip headers
            if any(skip in line for skip in ['Question', 'Answer', 'Marks', 'Cambridge', 'IGCSE', 'PUBLISHED', 'Mark Scheme']):
                if 'Question' in line and 'Answer' in line:
                    continue
                if 'Cambridge' in line or 'IGCSE' in line:
                    continue

            # Try to match question patterns
            # Pattern: "1(a)" or "1(a)(i)" or just "1"
            q_match = re.match(r'^(\d+)(?:\(([a-z])\))?(?:\(([ivx]+)\))?', line)

            if q_match:
                main_q = q_match.group(1)
                part = q_match.group(2)  # a, b, c, etc.
                subpart = q_match.group(3)  # i, ii, iii, etc.

                # Initialize question structure
                if main_q not in markscheme:
                    markscheme[main_q] = {
                        'parts': {},
                        'stem_answers': [],
                        'total_marks': 0
                    }

                current_main_q = main_q

                # Determine the part key
                if part:
                    part_key = part
                    if subpart:
                        part_key = f"{part}({subpart})"

                    if part_key not in markscheme[main_q]['parts']:
                        markscheme[main_q]['parts'][part_key] = []

                    current_part = part_key
                else:
                    current_part = None

                # Extract answer and marks from rest of line
                rest = line[q_match.end():].strip()
                marks_match = re.search(r'\b([ABCM]\d+)\s*$', rest)

                if marks_match:
                    marks = marks_match.group(1)
                    answer = rest[:marks_match.start()].strip()
                    marks_value = int(re.search(r'\d+', marks).group())
                    markscheme[main_q]['total_marks'] += marks_value
                else:
                    marks = ''
                    answer = rest

                entry = {'answer': answer, 'marks': marks}

                if current_part:
                    markscheme[main_q]['parts'][current_part].append(entry)
                else:
                    markscheme[main_q]['stem_answers'].append(entry)

            elif current_main_q:
                # Continuation line - add to current question/part
                marks_match = re.search(r'\b([ABCM]\d+)\s*$', line)

                if marks_match:
                    marks = marks_match.group(1)
                    answer = line[:marks_match.start()].strip()
                    marks_value = int(re.search(r'\d+', marks).group())
                    markscheme[current_main_q]['total_marks'] += marks_value
                else:
                    marks = ''
                    answer = line

                entry = {'answer': answer, 'marks': marks}

                if current_part and current_part in markscheme[current_main_q]['parts']:
                    markscheme[current_main_q]['parts'][current_part].append(entry)
                else:
                    markscheme[current_main_q]['stem_answers'].append(entry)

    doc.close()
    return markscheme


def format_markscheme_html(ms_data):
    """Format mark scheme data as HTML."""
    if not ms_data:
        return ''

    html = '<table class="ms-table"><thead><tr><th>Part</th><th>Answer</th><th>Marks</th></tr></thead><tbody>'

    # Add stem answers first
    for entry in ms_data.get('stem_answers', []):
        if entry['answer']:
            html += f'<tr><td>-</td><td>{entry["answer"]}</td><td>{entry["marks"]}</td></tr>'

    # Add part answers
    for part, entries in sorted(ms_data.get('parts', {}).items()):
        for i, entry in enumerate(entries):
            part_label = f'({part})' if i == 0 else ''
            html += f'<tr><td>{part_label}</td><td>{entry["answer"]}</td><td>{entry["marks"]}</td></tr>'

    html += '</tbody></table>'
    html += f'<div class="ms-total">Total: {ms_data.get("total_marks", 0)} marks</div>'

    return html


@login_required
@staff_member_required
def descriptive_pdf_slicer(request):
    """
    Main view for descriptive PDF slicer.
    Handles question paper slicing with colored lines and
    auto-parses Cambridge mark scheme table format.
    """
    grades = Grade.objects.all().order_by('name')
    subjects = Subject.objects.all().order_by('name')
    topics = Topic.objects.all().order_by('name')

    if request.method == 'POST':
        # Check action from form data first, then from JSON body
        action = request.POST.get('action')

        # For JSON requests, action is in the body
        if not action and request.content_type == 'application/json':
            try:
                body_data = json.loads(request.body)
                action = body_data.get('action')
            except:
                pass

        if action == 'upload_pdf':
            # Process uploaded PDFs
            qp_file = request.FILES.get('qp_file')
            ms_file = request.FILES.get('ms_file')

            if not qp_file:
                return JsonResponse({'error': 'Question paper PDF is required'}, status=400)

            try:
                # Read question paper
                qp_bytes = qp_file.read()
                qp_doc = fitz.open(stream=qp_bytes, filetype="pdf")

                # Parse mark scheme if provided
                markscheme_data = {}
                if ms_file:
                    ms_bytes = ms_file.read()
                    markscheme_data = parse_cambridge_markscheme(ms_bytes, start_page=4)

                # Process each page for colored lines
                pages_data = []
                questions_grouped = []
                current_question = None
                question_number = 0

                for page_num in range(len(qp_doc)):
                    page = qp_doc[page_num]
                    lines = detect_colored_lines(page)

                    page_image = extract_page_as_image(page)

                    page_info = {
                        'page_number': page_num + 1,
                        'page_image': page_image,
                        'has_red_line': len(lines['red']) > 0,
                        'has_green_line': len(lines['green']) > 0,
                        'has_purple_line': len(lines['purple']) > 0,
                        'red_positions': lines['red'],
                        'green_positions': lines['green'],
                        'purple_positions': lines['purple'],
                    }

                    pages_data.append(page_info)

                    # Group into questions based on red lines
                    if lines['red']:
                        # New question starts
                        if current_question:
                            questions_grouped.append(current_question)

                        question_number += 1
                        current_question = {
                            'question_number': question_number,
                            'start_page': page_num + 1,
                            'end_page': page_num + 1,
                            'pages': [page_info],
                            'has_subparts': len(lines['green']) > 0,
                            'markscheme': markscheme_data.get(str(question_number), {}),
                        }
                    elif current_question:
                        # Continuation of current question
                        current_question['end_page'] = page_num + 1
                        current_question['pages'].append(page_info)
                        if lines['green']:
                            current_question['has_subparts'] = True

                # Don't forget the last question
                if current_question:
                    questions_grouped.append(current_question)

                qp_doc.close()

                return JsonResponse({
                    'success': True,
                    'pages': pages_data,
                    'questions_grouped': questions_grouped,
                    'markscheme_data': markscheme_data,
                    'total_pages': len(pages_data),
                    'total_questions': len(questions_grouped),
                })

            except Exception as e:
                import traceback
                return JsonResponse({
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }, status=500)

        elif action == 'save_question':
            # Save individual question
            try:
                data = json.loads(request.body)

                grade_id = data.get('grade_id')
                subject_id = data.get('subject_id')
                topic_id = data.get('topic_id')
                year = data.get('year')
                marks = data.get('marks', 5)
                pages_data = data.get('pages', [])
                markscheme = data.get('markscheme', {})

                if not all([grade_id, subject_id, pages_data]):
                    return JsonResponse({'error': 'Missing required fields'}, status=400)

                # Get default topic if not specified
                if not topic_id:
                    topic = Topic.objects.filter(subject_id=subject_id).first()
                    topic_id = topic.id if topic else None

                # Format markscheme as HTML
                ms_html = format_markscheme_html(markscheme)

                # Create question
                question = Question.objects.create(
                    question_text='',
                    answer_text=ms_html,
                    marks=marks,
                    question_type='structured',
                    year=int(year) if year else None,
                    grade_id=grade_id,
                    subject_id=subject_id,
                    topic_id=topic_id,
                    created_by=request.user
                )

                # Save pages
                for page in pages_data:
                    QuestionPage.objects.create(
                        question=question,
                        page_number=page.get('page_number', 0),
                        page_image=page.get('page_image', ''),
                        has_green_line=page.get('has_green_line', False),
                        has_red_line=page.get('has_red_line', False),
                    )

                # Stitch pages for preview
                if pages_data:
                    question.question_text = pages_data[0]['page_image']
                    question.save()

                return JsonResponse({
                    'success': True,
                    'question_id': question.id
                })

            except Exception as e:
                import traceback
                return JsonResponse({
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }, status=500)

        elif action == 'save_all':
            # Batch save all questions
            try:
                data = json.loads(request.body)

                grade_id = data.get('grade_id')
                subject_id = data.get('subject_id')
                topic_id = data.get('topic_id')
                year = data.get('year')
                questions = data.get('questions', [])

                if not all([grade_id, subject_id, questions]):
                    return JsonResponse({'error': 'Missing required fields'}, status=400)

                if not topic_id:
                    topic = Topic.objects.filter(subject_id=subject_id).first()
                    topic_id = topic.id if topic else None

                saved_count = 0
                saved_question_ids = []

                for q_data in questions:
                    pages_data = q_data.get('pages', [])
                    markscheme = q_data.get('markscheme', {})
                    marks = markscheme.get('total_marks', 5) if markscheme else 5

                    ms_html = format_markscheme_html(markscheme)

                    question = Question.objects.create(
                        question_text='',
                        answer_text=ms_html,
                        marks=marks,
                        question_type='structured',
                        year=int(year) if year else None,
                        grade_id=grade_id,
                        subject_id=subject_id,
                        topic_id=topic_id,
                        created_by=request.user
                    )

                    for page in pages_data:
                        QuestionPage.objects.create(
                            question=question,
                            page_number=page.get('page_number', 0),
                            page_image=page.get('page_image', ''),
                            has_green_line=page.get('has_green_line', False),
                            has_red_line=page.get('has_red_line', False),
                        )

                    if pages_data:
                        question.question_text = pages_data[0]['page_image']
                        question.save()

                    saved_count += 1
                    saved_question_ids.append(question.id)

                # Auto-register this PDF as processed if file_hash provided
                file_hash = data.get('file_hash')
                file_name = data.get('file_name', '')
                if file_hash:
                    ProcessedPDF.objects.update_or_create(
                        file_hash=file_hash,
                        defaults={
                            'file_name': file_name,
                            'processed_by': request.user,
                            'grade_id': grade_id,
                            'subject_id': subject_id,
                            'year': int(year) if year else None,
                            'questions_created': saved_count,
                            'question_ids': saved_question_ids,
                        }
                    )

                return JsonResponse({
                    'success': True,
                    'count': saved_count,
                    'question_ids': saved_question_ids,
                })

            except Exception as e:
                import traceback
                return JsonResponse({
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }, status=500)

    context = {
        'grades': grades,
        'subjects': subjects,
        'topics': topics,
    }

    return render(request, 'teacher/descriptive_pdf_slicer.html', context)
