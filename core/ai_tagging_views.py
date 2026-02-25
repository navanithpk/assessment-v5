"""
AI Tagging Export/Import Views
- Export: Generates a document with question images, IDs, topic list, and LO list
  for input to ChatGPT/AI to get topic and LO code assignments.
- Import: Accepts CSV/TXT file with question_id -> topic/LO mappings
  and bulk-updates the questions.
"""
import csv
import io
import json
import re

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from .models import (
    Question, Topic, LearningObjective, Grade, Subject
)


@login_required
def ai_tagging_export(request):
    """
    Renders an export page with all questions for a given grade/subject,
    along with the complete topic and LO reference lists.
    Designed to be copy-pasted or printed for ChatGPT input.
    """
    grade_id = request.GET.get('grade', '')
    subject_id = request.GET.get('subject', '')
    include_tagged = request.GET.get('include_tagged', '') == '1'

    grades = Grade.objects.all().order_by('name')
    subjects = Subject.objects.all().order_by('name')

    questions = []
    topics = []
    los = []
    selected_grade = None
    selected_subject = None

    if grade_id and subject_id:
        selected_grade = Grade.objects.filter(id=grade_id).first()
        selected_subject = Subject.objects.filter(id=subject_id).first()

        if selected_grade and selected_subject:
            # Get questions
            q_filter = Q(grade=selected_grade, subject=selected_subject, parent__isnull=True)
            qs = Question.objects.filter(q_filter).select_related(
                'topic', 'grade', 'subject'
            ).prefetch_related('learning_objectives').order_by('id')

            for q in qs:
                current_topic = q.topic.name if q.topic else ''
                current_los = [lo.code for lo in q.learning_objectives.all()]

                # Skip already-tagged questions if not requested
                if not include_tagged and current_topic and current_los:
                    continue

                questions.append({
                    'id': q.id,
                    'question_text': q.question_text,
                    'question_type': q.question_type,
                    'marks': q.marks,
                    'year': q.year,
                    'current_topic': current_topic,
                    'current_los': ', '.join(current_los),
                    'has_image': 'data:image' in q.question_text,
                })

            # Get available topics for this grade/subject
            topics = list(
                Topic.objects.filter(grade=selected_grade, subject=selected_subject)
                .order_by('name')
                .values('id', 'name')
            )

            # Get available LOs for this grade/subject
            los = list(
                LearningObjective.objects.filter(grade=selected_grade, subject=selected_subject)
                .select_related('topic')
                .order_by('topic__name', 'code')
                .values('id', 'code', 'description', 'topic__name')
            )

    # Paginate: 40 questions per page
    total_questions = len(questions)
    paginator = Paginator(questions, 40)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'grades': grades,
        'subjects': subjects,
        'questions': page_obj,
        'all_question_count': total_questions,
        'topics': topics,
        'los': los,
        'selected_grade': selected_grade,
        'selected_subject': selected_subject,
        'filters': {
            'grade': grade_id,
            'subject': subject_id,
            'include_tagged': include_tagged,
        },
        'question_count': total_questions,
        'topic_count': len(topics),
        'lo_count': len(los),
        'page_obj': page_obj,
    }

    return render(request, 'teacher/ai_tagging_export.html', context)


@login_required
def ai_tagging_export_text(request):
    """
    Generates a plain-text export file optimized for ChatGPT input.
    Contains: question IDs with text snippets, topic reference, LO reference.
    """
    grade_id = request.GET.get('grade', '')
    subject_id = request.GET.get('subject', '')

    if not grade_id or not subject_id:
        return HttpResponse("Missing grade or subject parameter.", status=400)

    grade = Grade.objects.filter(id=grade_id).first()
    subject = Subject.objects.filter(id=subject_id).first()

    if not grade or not subject:
        return HttpResponse("Invalid grade or subject.", status=404)

    questions = Question.objects.filter(
        grade=grade, subject=subject, parent__isnull=True
    ).select_related('topic').prefetch_related('learning_objectives').order_by('id')

    topics = Topic.objects.filter(
        grade=grade, subject=subject
    ).order_by('name')

    los = LearningObjective.objects.filter(
        grade=grade, subject=subject
    ).select_related('topic').order_by('topic__name', 'code')

    # Build the text output
    lines = []
    lines.append("=" * 70)
    lines.append(f"AI TAGGING EXPORT - {grade.name} {subject.name}")
    lines.append("=" * 70)
    lines.append("")
    lines.append("INSTRUCTIONS FOR AI:")
    lines.append("For each question below, assign the most appropriate TOPIC and")
    lines.append("LEARNING OBJECTIVE codes from the reference lists. Return your")
    lines.append("answer as CSV with columns: question_id,topic_name,lo_codes")
    lines.append("(lo_codes can be multiple, separated by semicolons)")
    lines.append("")
    lines.append("Example output row: 142,Kinematics,1.1.1;1.1.2")
    lines.append("")

    # Topic reference
    lines.append("-" * 70)
    lines.append("AVAILABLE TOPICS:")
    lines.append("-" * 70)
    for t in topics:
        lines.append(f"  - {t.name}")
    lines.append("")

    # LO reference
    lines.append("-" * 70)
    lines.append("AVAILABLE LEARNING OBJECTIVES:")
    lines.append("-" * 70)
    for lo in los:
        topic_name = lo.topic.name if lo.topic else "N/A"
        lines.append(f"  [{lo.code}] {lo.description}  (Topic: {topic_name})")
    lines.append("")

    # Questions
    lines.append("-" * 70)
    lines.append(f"QUESTIONS TO TAG ({questions.count()} total):")
    lines.append("-" * 70)

    for q in questions:
        lines.append("")
        lines.append(f"--- Question ID: {q.id} | Type: {q.question_type} | Marks: {q.marks} ---")

        # Extract full plain text from HTML (strip all tags, keep text)
        text_content = q.question_text or ''
        # Replace <br>, <p>, </p>, </div> with newlines for readability
        text_content = re.sub(r'<br\s*/?>', '\n', text_content)
        text_content = re.sub(r'</(?:p|div|li|tr|h\d)>', '\n', text_content)
        # Mark images
        has_image = bool(re.search(r'<img[^>]*>', text_content))
        text_content = re.sub(r'<img[^>]*>', '[IMAGE]', text_content)
        # Strip remaining HTML tags
        text_content = re.sub(r'<[^>]+>', '', text_content)
        # Collapse whitespace but preserve newlines
        text_content = re.sub(r'[ \t]+', ' ', text_content)
        text_content = re.sub(r'\n\s*\n', '\n', text_content).strip()

        if has_image and (not text_content or text_content == '[IMAGE]'):
            lines.append("[IMAGE-ONLY QUESTION - no extractable text; view in browser export]")
        elif has_image:
            lines.append(f"[CONTAINS IMAGE(S)]")
            lines.append(f"Text: {text_content}")
        else:
            lines.append(f"Text: {text_content}")

        # Include sub-questions / parts if any
        sub_qs = Question.objects.filter(parent=q).order_by('id')
        if sub_qs.exists():
            for i, sq in enumerate(sub_qs, 1):
                sub_text = sq.question_text or ''
                sub_has_img = bool(re.search(r'<img[^>]*>', sub_text))
                sub_text = re.sub(r'<br\s*/?>', '\n', sub_text)
                sub_text = re.sub(r'</(?:p|div|li|tr|h\d)>', '\n', sub_text)
                sub_text = re.sub(r'<img[^>]*>', '[IMAGE]', sub_text)
                sub_text = re.sub(r'<[^>]+>', '', sub_text)
                sub_text = re.sub(r'[ \t]+', ' ', sub_text)
                sub_text = re.sub(r'\n\s*\n', '\n', sub_text).strip()
                part_label = f"  Part {i} (ID: {sq.id}, {sq.marks} marks)"
                if sub_has_img and (not sub_text or sub_text == '[IMAGE]'):
                    lines.append(f"{part_label}: [IMAGE-ONLY]")
                else:
                    lines.append(f"{part_label}: {sub_text}")

        current_topic = q.topic.name if q.topic else "UNTAGGED"
        current_los = ', '.join([lo.code for lo in q.learning_objectives.all()])
        lines.append(f"Current: Topic={current_topic}, LOs={current_los or 'NONE'}")

    lines.append("")
    lines.append("=" * 70)
    lines.append("END OF EXPORT")
    lines.append("=" * 70)

    content = "\n".join(lines)

    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="ai_tagging_export_{grade.name}_{subject.name}.txt"'
    )
    return response


@login_required
def ai_tagging_import(request):
    """
    Import page - accepts CSV/TXT file with question_id, topic_name, lo_codes
    and updates questions accordingly.
    GET: shows upload form
    POST: processes the uploaded file
    """
    if request.method == 'GET':
        grades = Grade.objects.all().order_by('name')
        subjects = Subject.objects.all().order_by('name')
        return render(request, 'teacher/ai_tagging_import.html', {
            'grades': grades,
            'subjects': subjects,
        })

    # POST - process uploaded file
    uploaded_file = request.FILES.get('tagging_file')
    grade_id = request.POST.get('grade', '')
    subject_id = request.POST.get('subject', '')

    if not uploaded_file:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    if not grade_id or not subject_id:
        return JsonResponse({'error': 'Grade and subject are required'}, status=400)

    grade = Grade.objects.filter(id=grade_id).first()
    subject = Subject.objects.filter(id=subject_id).first()

    if not grade or not subject:
        return JsonResponse({'error': 'Invalid grade or subject'}, status=404)

    # Read and parse the file
    try:
        content = uploaded_file.read().decode('utf-8')
    except UnicodeDecodeError:
        content = uploaded_file.read().decode('latin-1')

    # Parse CSV/TXT content
    results = []
    errors = []
    updated = 0
    skipped = 0

    # Try to parse as CSV
    reader = csv.reader(io.StringIO(content))

    for row_num, row in enumerate(reader, 1):
        # Skip empty rows and header rows
        if not row or len(row) < 2:
            continue

        # Skip header row
        first_cell = row[0].strip().lower()
        if first_cell in ('question_id', 'id', '#', 'qid', 'question id'):
            continue

        try:
            question_id = int(row[0].strip())
        except (ValueError, IndexError):
            errors.append(f"Row {row_num}: Invalid question ID '{row[0]}'")
            continue

        topic_name = row[1].strip() if len(row) > 1 else ''
        lo_codes_str = row[2].strip() if len(row) > 2 else ''

        # Parse LO codes (semicolon or comma separated)
        lo_codes = []
        if lo_codes_str:
            for code in lo_codes_str.replace(';', ',').split(','):
                code = code.strip()
                if code:
                    lo_codes.append(code)

        # Find the question
        question = Question.objects.filter(id=question_id, grade=grade, subject=subject).first()
        if not question:
            errors.append(f"Row {row_num}: Question ID {question_id} not found for {grade.name}/{subject.name}")
            skipped += 1
            continue

        # Find the topic
        topic = None
        if topic_name:
            topic = Topic.objects.filter(
                name__iexact=topic_name, grade=grade, subject=subject
            ).first()

            if not topic:
                # Try partial match
                topic = Topic.objects.filter(
                    name__icontains=topic_name, grade=grade, subject=subject
                ).first()

            if not topic:
                errors.append(f"Row {row_num}: Topic '{topic_name}' not found for Q{question_id}")

        # Find LOs
        found_los = []
        for code in lo_codes:
            lo = LearningObjective.objects.filter(
                code__iexact=code, grade=grade, subject=subject
            ).first()
            if lo:
                found_los.append(lo)
            else:
                errors.append(f"Row {row_num}: LO code '{code}' not found for Q{question_id}")

        # Apply updates
        changes = []
        if topic:
            old_topic = question.topic.name if question.topic else 'None'
            question.topic = topic
            question.save(update_fields=['topic'])
            changes.append(f"Topic: {old_topic} -> {topic.name}")

        if found_los:
            old_los = ', '.join([lo.code for lo in question.learning_objectives.all()])
            question.learning_objectives.set(found_los)
            new_los = ', '.join([lo.code for lo in found_los])
            changes.append(f"LOs: [{old_los or 'none'}] -> [{new_los}]")

        if changes:
            updated += 1
            results.append({
                'question_id': question_id,
                'changes': changes,
                'status': 'updated',
            })
        else:
            skipped += 1
            results.append({
                'question_id': question_id,
                'changes': ['No valid changes to apply'],
                'status': 'skipped',
            })

    return JsonResponse({
        'success': True,
        'summary': {
            'total_rows': row_num if 'row_num' in dir() else 0,
            'updated': updated,
            'skipped': skipped,
            'errors': len(errors),
        },
        'results': results[:50],  # Limit to first 50 for display
        'errors': errors[:30],    # Limit errors for display
    })
