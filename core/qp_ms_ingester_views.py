"""
QP-MS Ingester Views
Unified tool for importing Cambridge question papers + mark schemes
as hierarchical Question objects with proper parent-child relationships.

Uses PDF.js + Fabric.js on the frontend for manual line drawing and slicing
(the proven approach from the QP Slicer Workstation). The backend only handles:
  1. Rendering the page (GET)
  2. Saving hierarchical questions with answer spaces (POST)
"""

import json
import re
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import (
    Question, Grade, Subject, Topic,
    QuestionPage, AnswerSpace,
)


# ─── Utilities ───────────────────────────────────────────────────────

def format_ms_entries_html(entries):
    """Format mark scheme entries as simple HTML."""
    if not entries:
        return ''
    lines = []
    for e in entries:
        if isinstance(e, str):
            lines.append(e)
        elif isinstance(e, dict):
            answer = e.get('answer', '')
            marks = e.get('marks', '')
            if answer or marks:
                lines.append(f'{answer} [{marks}]' if marks else answer)
    return '<br>'.join(lines)


# ─── Main Page View ──────────────────────────────────────────────────

@login_required
@staff_member_required
def qp_ms_ingester(request):
    """
    GET: Render the ingester page with PDF.js + Fabric.js interface.
    All processing happens client-side.
    """
    grades = Grade.objects.all().order_by('name')
    subjects = Subject.objects.all().order_by('name')
    topics = Topic.objects.all().order_by('name')

    return render(request, 'teacher/qp_ms_ingester.html', {
        'grades': grades,
        'subjects': subjects,
        'topics': topics,
    })


# ─── Save Hierarchical Questions ─────────────────────────────────────

@login_required
@staff_member_required
@require_http_methods(["POST"])
def qp_ms_ingester_save(request):
    """
    Save sliced questions as hierarchical Question records.

    Expects JSON body:
    {
        "grade_id": 1,
        "subject_id": 2,
        "topic_id": 3,        // optional
        "year": 2023,          // optional
        "questions": [
            {
                "question_number": "1",
                "image": "data:image/png;base64,...",
                "marks": 15,
                "answer_text": "",
                "order": 0,
                "children": [
                    {
                        "question_number": "a",
                        "marks": 3,
                        "answer_text": "markscheme text...",
                        "order": 0,
                        "answer_spaces": [
                            {"type": "text_line", "x": 50, "y": 200, "width": 500, "height": 80, "marks": 3}
                        ],
                        "children": []
                    },
                    ...
                ]
            }
        ]
    }
    """
    try:
        data = json.loads(request.body)

        grade_id = data.get('grade_id')
        subject_id = data.get('subject_id')
        topic_id = data.get('topic_id')
        year = data.get('year')
        questions = data.get('questions', [])

        if not all([grade_id, subject_id, questions]):
            return JsonResponse({'error': 'Missing required fields (grade, subject, questions)'}, status=400)

        # Default topic if not specified
        if not topic_id:
            topic = Topic.objects.filter(subject_id=subject_id).first()
            topic_id = topic.id if topic else None

        if not topic_id:
            return JsonResponse({'error': 'No topic available for this subject'}, status=400)

        saved_roots = []

        for q_data in questions:
            root = _save_question_recursive(
                node=q_data,
                parent=None,
                grade_id=grade_id,
                subject_id=subject_id,
                topic_id=topic_id,
                year=int(year) if year else None,
                user=request.user,
            )
            saved_roots.append(root.id)

        return JsonResponse({
            'success': True,
            'question_ids': saved_roots,
            'count': len(saved_roots),
        })

    except Exception as e:
        import traceback
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


def _save_question_recursive(node, parent, grade_id, subject_id, topic_id, year, user):
    """Recursively create Question objects with parent FK chain."""

    children = node.get('children', [])
    has_children = len(children) > 0

    # Build question_text from image data (only for root questions)
    question_text = ''
    if parent is None:
        image_data = node.get('image', '')
        if image_data:
            question_text = (
                f'<img src="{image_data}" '
                f'alt="Question {node.get("question_number", "")}" '
                f'style="max-width:100%;height:auto;display:block;" />'
            )

    # Build answer_text from markscheme
    answer_text = node.get('answer_text', '')

    # Marks: leaf nodes get their own marks, parents get 0
    marks = node.get('marks', 0) if not has_children else 0

    question = Question.objects.create(
        question_text=question_text,
        answer_text=answer_text,
        marks=marks,
        question_type='structured',
        year=year,
        grade_id=grade_id,
        subject_id=subject_id,
        topic_id=topic_id,
        created_by=user,
        parent=parent,
        question_number=node.get('question_number', ''),
        order=node.get('order', 0),
    )

    # Save AnswerSpace records
    for idx, space in enumerate(node.get('answer_spaces', [])):
        AnswerSpace.objects.create(
            question=question,
            space_type=space.get('type', 'text_line'),
            x=int(space.get('x', 0)),
            y=int(space.get('y', 0)),
            width=int(space.get('width', 600)),
            height=int(space.get('height', 80)),
            config=space.get('config', {}),
            order=idx,
            marks=space.get('marks', 1),
        )

    # Recursively create children
    for child_data in children:
        _save_question_recursive(
            node=child_data,
            parent=question,
            grade_id=grade_id,
            subject_id=subject_id,
            topic_id=topic_id,
            year=year,
            user=user,
        )

    return question


# ─── Tree Update (AJAX) ──────────────────────────────────────────────

@login_required
@staff_member_required
@require_http_methods(["POST"])
def qp_ms_ingester_update_tree(request):
    """
    Handle tree editing operations from the frontend.
    Operations: add_child, remove_node, update_marks, update_label
    All operations work on the in-memory tree (not DB) and return updated tree.
    """
    try:
        data = json.loads(request.body)
        operation = data.get('operation')
        tree = data.get('tree', [])

        if operation == 'add_child':
            parent_path = data.get('parent_path')
            node = _find_node_by_path(tree, parent_path)
            if node is not None:
                new_child = {
                    'question_number': '',
                    'label': '(new)',
                    'marks': 1,
                    'answer_text': '',
                    'order': len(node.get('children', [])),
                    'children': [],
                    'answer_spaces': [],
                }
                if 'children' not in node:
                    node['children'] = []
                node['children'].append(new_child)

        elif operation == 'remove_node':
            parent_path = data.get('parent_path')
            child_index = data.get('child_index')
            node = _find_node_by_path(tree, parent_path)
            if node and 'children' in node and 0 <= child_index < len(node['children']):
                node['children'].pop(child_index)
                for i, child in enumerate(node['children']):
                    child['order'] = i

        elif operation == 'update_marks':
            node_path = data.get('node_path')
            new_marks = data.get('marks', 0)
            node = _find_node_by_path(tree, node_path)
            if node is not None:
                node['marks'] = int(new_marks)

        elif operation == 'update_label':
            node_path = data.get('node_path')
            new_label = data.get('question_number', '')
            node = _find_node_by_path(tree, node_path)
            if node is not None:
                node['question_number'] = new_label
                node['label'] = f'({new_label})' if new_label else '(new)'

        return JsonResponse({'success': True, 'tree': tree})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def _find_node_by_path(tree, path):
    """
    Navigate a tree by dot-separated path.
    e.g. "0" -> tree[0], "0.children.1" -> tree[0]['children'][1]
    """
    if not path and path != 0:
        return None

    parts = str(path).split('.')
    current = tree

    for part in parts:
        if part == 'children':
            if isinstance(current, dict):
                current = current.get('children', [])
            else:
                return None
        else:
            try:
                idx = int(part)
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            except (ValueError, IndexError):
                return None

    return current
