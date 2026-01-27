"""
Answer Space Designer Views (Step 2 of Two-Step Non-MCQ Import)

After importing questions with marks only (Step 1), teachers use this interface
to define:
- Question parts (a, b, c...)
- Answer types (text/canvas/both) per part
- Markschemes per part
- Model answers for AI grading
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json

from .models import Question, Topic


@login_required
def list_unconfigured_questions(request):
    """
    List all structured questions that don't have parts_config yet
    """
    if not request.user.is_staff:
        return redirect('login')

    # Get all structured/theory questions without parts_config
    questions = Question.objects.filter(
        question_type__in=['structured', 'theory'],
        created_by=request.user
    ).filter(parts_config__isnull=True).order_by('-created_at')

    context = {
        'questions': questions,
        'total_count': questions.count()
    }

    return render(request, 'teacher/unconfigured_questions_list.html', context)


@login_required
def answer_space_designer(request, question_id):
    """
    Main interface for configuring answer spaces for a question
    """
    if not request.user.is_staff:
        return redirect('login')

    question = get_object_or_404(Question, id=question_id, created_by=request.user)

    # Get existing config or create default
    parts_config = question.parts_config if question.parts_config else {
        "parts": [
            {
                "part_id": "1",
                "part_label": "",
                "marks": question.marks,
                "answer_type": "text",
                "text_config": {
                    "input_type": "long_text",
                    "max_length": 1000,
                    "model_answer": "",
                    "ai_grading_enabled": True
                },
                "canvas_config": None,
                "markscheme": question.answer_text or ""
            }
        ]
    }

    context = {
        'question': question,
        'parts_config': json.dumps(parts_config),  # JSON string for JavaScript
        'parts_config_obj': parts_config,  # Python object for template
    }

    return render(request, 'teacher/answer_space_designer.html', context)


@login_required
@require_http_methods(["POST"])
def save_answer_spaces(request, question_id):
    """
    Save the parts configuration for a question
    """
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    question = get_object_or_404(Question, id=question_id, created_by=request.user)

    try:
        # Parse the JSON configuration from request
        parts_config = json.loads(request.POST.get('parts_config', '{}'))

        # Validate structure
        if 'parts' not in parts_config or not isinstance(parts_config['parts'], list):
            return JsonResponse({'success': False, 'error': 'Invalid configuration structure'})

        if len(parts_config['parts']) == 0:
            return JsonResponse({'success': False, 'error': 'At least one part is required'})

        # Validate each part
        for part in parts_config['parts']:
            if 'part_id' not in part or 'marks' not in part or 'answer_type' not in part:
                return JsonResponse({'success': False, 'error': 'Missing required fields in part configuration'})

            # Ensure marks is a number
            try:
                part['marks'] = int(part['marks'])
            except (ValueError, TypeError):
                return JsonResponse({'success': False, 'error': f'Invalid marks value for part {part["part_id"]}'})

        # Calculate total marks
        total_marks = sum(part['marks'] for part in parts_config['parts'])

        # Save configuration
        question.parts_config = parts_config
        question.marks = total_marks  # Update total marks
        question.save()

        return JsonResponse({
            'success': True,
            'message': f'Configuration saved for {len(parts_config["parts"])} part(s)',
            'total_marks': total_marks
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON format'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def duplicate_part_config(request, question_id):
    """
    Duplicate the parts configuration from another question
    """
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    question = get_object_or_404(Question, id=question_id, created_by=request.user)
    source_question_id = request.POST.get('source_question_id')

    if not source_question_id:
        return JsonResponse({'success': False, 'error': 'Source question ID is required'})

    try:
        source_question = Question.objects.get(id=source_question_id, created_by=request.user)

        if not source_question.parts_config:
            return JsonResponse({'success': False, 'error': 'Source question has no configuration'})

        # Copy configuration (deep copy)
        question.parts_config = json.loads(json.dumps(source_question.parts_config))
        question.save()

        return JsonResponse({
            'success': True,
            'message': f'Configuration copied from Question {source_question_id}',
            'parts_config': question.parts_config
        })

    except Question.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Source question not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
