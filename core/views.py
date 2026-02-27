from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.template.loader import render_to_string
from django.db import models
from django.db.models import Q
from django.urls import reverse
import json
from core.ai.topic_tagger import suggest_topic_for_question
from core.ai.lo_tagger import suggest_los_for_question
from django.db.models import Count

from .models import (
    Grade,
    Subject,
    Topic,
    LearningObjective,
    Question,
    Test,
    TestQuestion,
    Student,
    ClassGroup,
    StudentAnswer,
    School,
    UserProfile,
    AnswerSpace,
    StudentAnswerSpace,
    QuestionPage,
)

# Import logs views
from .logs_views import ai_tagging_logs, view_log_file

# Import improved bulk tagging
from .bulk_tagging_view import bulk_ai_tag_questions_improved
import re
from bs4 import BeautifulSoup


# ===================== HELPER FUNCTIONS FOR STRUCTURED QUESTIONS =====================

def build_answer_parts_from_config(parts_config):
    """
    Build answer parts list from question's parts_config JSON.
    Expected format:
    {
        "parts": [
            {"id": "a", "label": "(a)", "marks": 2, "level": 0},
            {"id": "a_i", "label": "(a)(i)", "marks": 1, "level": 1},
            ...
        ]
    }
    """
    if not parts_config:
        return []

    parts = parts_config.get('parts', [])
    answer_parts = []

    for part in parts:
        answer_parts.append({
            'partId': part.get('id', f'part_{len(answer_parts)}'),
            'label': part.get('label', f'Part {len(answer_parts) + 1}'),
            'marks': part.get('marks', 0),
            'level': part.get('level', 0),
            'hint': part.get('hint', '')
        })

    return answer_parts


def parse_answer_parts_from_markscheme(answer_text, total_marks=0):
    """
    Parse mark scheme HTML to extract answer parts.
    Looks for patterns like (a), (b), (i), (ii) etc.
    Returns a list of answer parts with labels and marks.
    """
    if not answer_text:
        return []

    answer_parts = []

    try:
        # Try to parse as HTML
        soup = BeautifulSoup(answer_text, 'html.parser')
        text = soup.get_text()
    except:
        text = answer_text

    # Pattern to match question parts like (a), (b), (a)(i), 1(a), etc.
    # Also match standalone letters like "a)", "b)", and roman numerals
    part_patterns = [
        r'\(([a-z])\)\s*\(([ivx]+)\)',  # (a)(i) format
        r'\(([a-z])\)',                   # (a) format
        r'\(([ivx]+)\)',                  # (i) format
        r'^([a-z])\)',                    # a) format at line start
        r'^([ivx]+)\)',                   # i) format at line start
    ]

    found_parts = set()

    for pattern in part_patterns:
        matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            groups = match.groups()
            if len(groups) == 2:
                # Combined format like (a)(i)
                part_id = f"{groups[0].lower()}_{groups[1].lower()}"
                label = f"({groups[0].lower()})({groups[1].lower()})"
                level = 1
            else:
                # Single format like (a) or (i)
                part_val = groups[0].lower()
                if part_val in ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']:
                    # Roman numeral - likely sub-part
                    part_id = f"roman_{part_val}"
                    label = f"({part_val})"
                    level = 1
                else:
                    # Letter - main part
                    part_id = part_val
                    label = f"({part_val})"
                    level = 0

            if part_id not in found_parts:
                found_parts.add(part_id)
                answer_parts.append({
                    'partId': part_id,
                    'label': label,
                    'marks': 0,  # Will try to extract from context
                    'level': level,
                    'hint': ''
                })

    # Sort parts: letters first, then roman numerals
    def sort_key(part):
        label = part['label'].lower()
        # Extract the main identifier
        if '(' in label:
            inner = label.replace('(', '').replace(')', '')
            if '_' in part['partId']:
                # Combined like a_i
                main, sub = part['partId'].split('_')
                return (ord(main) - ord('a'), 1, sub)
            elif 'roman_' in part['partId']:
                roman_order = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5,
                               'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10}
                return (100, 1, roman_order.get(inner, 99))
            else:
                return (ord(inner) - ord('a'), 0, '')
        return (999, 0, '')

    answer_parts.sort(key=sort_key)

    # If no parts found but there's mark scheme content, create a single part
    if not answer_parts and answer_text.strip():
        answer_parts.append({
            'partId': 'main',
            'label': 'Answer',
            'marks': total_marks,
            'level': 0,
            'hint': ''
        })

    # Try to extract marks from the HTML table if present
    try:
        soup = BeautifulSoup(answer_text, 'html.parser')
        table = soup.find('table', class_='ms-table')
        if table:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header row
                cells = row.find_all('td')
                if len(cells) >= 3:
                    part_label = cells[0].get_text().strip()
                    marks_text = cells[2].get_text().strip()
                    try:
                        marks = int(marks_text)
                        # Find matching part
                        for part in answer_parts:
                            if part_label in part['label']:
                                part['marks'] = marks
                                break
                    except:
                        pass
    except:
        pass

    return answer_parts


def build_question_data_recursive(question, number_prefix, level=0):
    """
    Build question data recursively including all sub-questions.
    Returns a nested structure with parent question and all children.
    """
    from .models import AnswerSpace

    # Check for answer spaces
    answer_spaces = AnswerSpace.objects.filter(question=question).order_by('order')

    question_data = {
        'id': question.id,
        'number': number_prefix,
        'questionNumber': question.question_number or '',
        'content': question.question_text,
        'marks': question.marks,
        'totalMarks': question.get_total_marks(),
        'questionType': question.question_type,
        'answerId': f'q{question.id}',
        'level': level
    }

    # Check if this is a structured question with parts_config
    is_structured = question.question_type == 'structured' or question.parts_config

    if is_structured and question.parts_config:
        question_data['isStructured'] = True
        question_data['answerParts'] = build_answer_parts_from_config(question.parts_config)
    elif is_structured and question.answer_text:
        question_data['isStructured'] = True
        question_data['answerParts'] = parse_answer_parts_from_markscheme(question.answer_text, question.marks)
    else:
        question_data['isStructured'] = False

    # Add legacy answer spaces if exists
    if answer_spaces.exists():
        question_data['hasAnswerSpaces'] = True
        question_data['answerSpaces'] = [{
            'id': space.id,
            'type': space.space_type,
            'x': space.x,
            'y': space.y,
            'width': space.width,
            'height': space.height,
            'order': space.order,
            'marks': float(space.marks),
            'config': space.config
        } for space in answer_spaces]
    else:
        question_data['hasAnswerSpaces'] = False

    # Recursively build sub-questions
    sub_questions = question.sub_questions.all().order_by('order')
    if sub_questions.exists():
        question_data['subQuestions'] = []
        for idx, sub_q in enumerate(sub_questions):
            sub_number = sub_q.question_number or chr(ord('a') + idx)
            sub_prefix = f"{number_prefix}({sub_number})"
            sub_data = build_question_data_recursive(sub_q, sub_prefix, level + 1)
            question_data['subQuestions'].append(sub_data)

    return question_data


# ===================== QP SLICER WORKSTATION =====================

@login_required
@staff_member_required
def qp_slicer_workstation(request):
    """
    Interactive QP Slicer Workstation - Draw lines on PDF to slice questions.
    Z = Green (Question Start), X = Red (Question End), W = Purple (Stitch/Continue)
    A = White mask (to cover question numbers)
    """
    grades = Grade.objects.all().order_by('name')
    subjects = Subject.objects.all().order_by('name')

    return render(request, 'teacher/qp_slicer_workstation.html', {
        'grades': grades,
        'subjects': subjects,
    })


# ===================== AUTHENTICATION & REDIRECTS =====================

def root_redirect(request):
    if request.user.is_authenticated:
        role = get_user_role(request.user)
        if role in ['teacher', 'school_admin']:
            return redirect("teacher_dashboard")
        return redirect("student_dashboard")
    return redirect("login")


def redirect_after_login(user):
    """Redirect user to appropriate dashboard based on their role"""
    role = get_user_role(user)
    if role in ['teacher', 'school_admin', 'superuser']:
        return redirect("teacher_dashboard")
    elif role == 'student':
        return redirect("student_dashboard")
    else:
        return redirect("teacher_dashboard")


def custom_login(request):
    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        role_clicked = request.POST.get("role")  # Get which button was clicked

        user = authenticate(request, username=username, password=password)

        if user is None:
            error = "Invalid username or password"
        else:
            login(request, user)

            # Always redirect based on actual profile role, not which button was clicked
            return redirect_after_login(user)

    return render(request, "registration/login.html", {"error": error})


# ===================== DASHBOARDS =====================

@login_required
def teacher_dashboard(request):
    school = get_user_school(request.user)
    role = get_user_role(request.user)

    # Get pending tasks for admin to-do list
    pending_tasks = []

    # ── 1. Tests with ungraded student answers (one entry per test) ──
    grading_qs = Test.objects.filter(
        student_answers__marks_awarded__isnull=True
    ).distinct()
    if not request.user.is_superuser:
        grading_qs = grading_qs.filter(created_by=request.user)
    for test in grading_qs[:10]:
        waiting = Student.objects.filter(
            answers__test=test,
            answers__marks_awarded__isnull=True
        ).distinct().count()
        pending_tasks.append({
            'type': 'grade_test',
            'url': reverse('grade_test_answers', args=[test.id]),
            'title': f'Grade: {test.title}',
            'description': f'{waiting} student{"s" if waiting != 1 else ""} awaiting grading',
            'icon': '✏️',
        })

    # ── 2. Questions without topics ──
    questions_without_topic = Question.objects.filter(topic__isnull=True)[:10]
    for q in questions_without_topic:
        pending_tasks.append({
            'type': 'tag_topic',
            'url': reverse('edit_question', args=[q.id]),
            'title': 'Tag topic for question',
            'description': f'Question #{q.id} needs a topic tag',
            'icon': '🏷️',
        })

    # ── 3. Questions without answer keys ──
    questions_without_answer = Question.objects.filter(
        Q(answer_text__isnull=True) | Q(answer_text='')
    )[:10]
    for q in questions_without_answer:
        pending_tasks.append({
            'type': 'tag_answer',
            'url': reverse('edit_question', args=[q.id]),
            'title': 'Tag answer key for question',
            'description': f'Question #{q.id} needs an answer key',
            'icon': '✅',
        })

    # ── 4. Questions without learning objectives ──
    all_questions = Question.objects.all()[:50]
    for q in all_questions:
        if q.learning_objectives.count() == 0:
            pending_tasks.append({
                'type': 'tag_lo',
                'url': reverse('edit_question', args=[q.id]),
                'title': 'Tag learning objective for question',
                'description': f'Question #{q.id} needs a learning objective',
                'icon': '🎯',
            })
            if len([t for t in pending_tasks if t['type'] == 'tag_lo']) >= 10:
                break

    # Count all untagged questions (without topic or LOs)
    untagged_count = Question.objects.filter(
        Q(topic__isnull=True) | Q(learning_objectives__isnull=True)
    ).distinct().count()

    context = {
        'school': school,
        'role': role,
        'is_school_admin': role == 'school_admin',
        'pending_tasks': pending_tasks[:15],  # Limit to 15 most urgent tasks
        'untagged_questions_count': untagged_count,
    }

    return render(request, "teacher/teacher_dashboard.html", context)


# ══════════════════════════════════════════════════════════════════
#  ACADEMIC OVERVIEW DASHBOARD
# ══════════════════════════════════════════════════════════════════
@login_required
@staff_member_required
def academic_overview_dashboard(request):
    """School-wide academic analytics dashboard with rich interactive charts."""
    from django.db.models import Sum, Count, FloatField
    from django.db.models.functions import Cast, TruncMonth, TruncDay
    from django.utils import timezone
    from datetime import timedelta
    import json as _json

    school = get_user_school(request.user)
    now = timezone.now()

    # ── KPI METRICS ──────────────────────────────────────────────
    all_students_qs  = Student.objects.filter(school=school)
    total_students   = all_students_qs.count()
    active_students  = all_students_qs.filter(user__is_active=True).count()
    inactive_students = total_students - active_students

    online_students = all_students_qs.filter(
        user__last_login__gte=now - timedelta(minutes=15)
    ).count()

    writing_now = StudentAnswer.objects.filter(
        student__school=school,
        submitted_at__gte=now - timedelta(minutes=10)
    ).values('student').distinct().count()

    total_questions = Question.objects.filter(created_by__profile__school=school).count()
    total_tests     = Test.objects.filter(created_by__profile__school=school).count()
    pending_grading = Test.objects.filter(
        created_by__profile__school=school,
        student_answers__marks_awarded__isnull=True
    ).distinct().count()

    # ── SUBJECT PERFORMANCE (horizontal bar) ─────────────────────
    subj_buckets = {}
    for ans in StudentAnswer.objects.filter(
        student__school=school,
        marks_awarded__isnull=False,
        test__subject__isnull=False,
    ).select_related('test__subject', 'question'):
        s = ans.test.subject.name
        subj_buckets.setdefault(s, [0.0, 0.0])
        subj_buckets[s][0] += float(ans.marks_awarded)
        subj_buckets[s][1] += float(ans.question.marks)

    subject_labels, subject_scores = [], []
    for s, (earned, total) in sorted(subj_buckets.items()):
        if total > 0:
            subject_labels.append(s)
            subject_scores.append(round(earned / total * 100, 1))

    # ── PERFORMANCE TREND (monthly area, last 12 months) ─────────
    monthly_raw = (
        StudentAnswer.objects
        .filter(
            student__school=school,
            marks_awarded__isnull=False,
            submitted_at__gte=now - timedelta(days=365),
        )
        .annotate(month=TruncMonth('submitted_at'))
        .values('month')
        .annotate(
            t=Sum(Cast('question__marks', FloatField())),
            e=Sum(Cast('marks_awarded', FloatField())),
        )
        .order_by('month')
    )
    trend_labels, trend_scores = [], []
    for r in monthly_raw:
        if r['t'] and r['t'] > 0:
            trend_labels.append(r['month'].strftime('%b %Y'))
            trend_scores.append(round(r['e'] / r['t'] * 100, 1))

    # ── SUBJECT TREND LINES (per-subject monthly, last 6 months) ──
    six_months_ago = now - timedelta(days=183)
    subj_trend_raw = (
        StudentAnswer.objects
        .filter(
            student__school=school,
            marks_awarded__isnull=False,
            test__subject__isnull=False,
            submitted_at__gte=six_months_ago,
        )
        .annotate(month=TruncMonth('submitted_at'))
        .values('month', 'test__subject__name')
        .annotate(
            t=Sum(Cast('question__marks', FloatField())),
            e=Sum(Cast('marks_awarded', FloatField())),
        )
        .order_by('month', 'test__subject__name')
    )
    # Build per-subject series
    subj_trend_months = sorted(set(r['month'].strftime('%b %Y') for r in subj_trend_raw))
    subj_trend_subjects = sorted(set(r['test__subject__name'] for r in subj_trend_raw))
    subj_trend_series = []
    for subj in subj_trend_subjects:
        data = []
        for m_str in subj_trend_months:
            match = next(
                (r for r in subj_trend_raw
                 if r['test__subject__name'] == subj
                 and r['month'].strftime('%b %Y') == m_str),
                None
            )
            if match and match['t'] and match['t'] > 0:
                data.append(round(match['e'] / match['t'] * 100, 1))
            else:
                data.append(None)
        subj_trend_series.append({'name': subj, 'data': data})

    # ── GRADE DISTRIBUTION (donut) ────────────────────────────────
    gd_raw = (
        all_students_qs
        .values('grade__name', 'grade__grade_level')
        .annotate(count=Count('id'))
        .order_by('grade__grade_level')
    )
    grade_labels = [r['grade__name'] or 'N/A' for r in gd_raw]
    grade_counts  = [r['count'] for r in gd_raw]

    # ── QUESTION TYPES (pie) ──────────────────────────────────────
    _qt_map = {'mcq': 'MCQ', 'theory': 'Theory', 'structured': 'Structured', 'practical': 'Practical'}
    qt_raw = (
        Question.objects
        .filter(created_by__profile__school=school)
        .values('question_type')
        .annotate(count=Count('id'))
    )
    qt_labels = [_qt_map.get(r['question_type'], r['question_type'].title()) for r in qt_raw]
    qt_counts  = [r['count'] for r in qt_raw]

    # ── TEST STATUS (donut) ───────────────────────────────────────
    all_tests_qs = Test.objects.filter(created_by__profile__school=school)
    test_draft   = all_tests_qs.filter(is_published=False).count()
    test_live    = all_tests_qs.filter(is_published=True, results_published=False).count()
    test_done    = all_tests_qs.filter(results_published=True).count()

    # ── SCORE DISTRIBUTION (10 bands histogram) ───────────────────
    score_bands = [0] * 10
    ts_qs = (
        StudentAnswer.objects
        .filter(student__school=school, marks_awarded__isnull=False)
        .values('student_id', 'test_id')
        .annotate(
            t=Sum(Cast('question__marks', FloatField())),
            e=Sum(Cast('marks_awarded', FloatField())),
        )
    )
    for row in ts_qs:
        if row['t'] and row['t'] > 0:
            score_bands[min(int((row['e'] / row['t'] * 100) // 10), 9)] += 1

    # ── TEACHER METRICS (grouped bar) ────────────────────────────
    teacher_names, teacher_tests_ct, teacher_students_ct, teacher_avg_scores = [], [], [], []
    for tp in UserProfile.objects.filter(
        school=school, role__in=['teacher', 'school_admin']
    ).select_related('user')[:12]:
        u = tp.user
        t_tests = Test.objects.filter(created_by=u).count()
        t_studs = Student.objects.filter(
            answers__test__created_by=u, school=school
        ).distinct().count()
        buckets = {}
        for row in StudentAnswer.objects.filter(
            test__created_by=u,
            student__school=school,
            marks_awarded__isnull=False,
        ).values('student_id', 'test_id').annotate(
            t=Sum(Cast('question__marks', FloatField())),
            e=Sum(Cast('marks_awarded', FloatField())),
        ):
            if row['t'] and row['t'] > 0:
                buckets[(row['student_id'], row['test_id'])] = row['e'] / row['t'] * 100
        avg = round(sum(buckets.values()) / len(buckets), 1) if buckets else 0.0
        teacher_names.append(u.get_full_name() or u.username)
        teacher_tests_ct.append(t_tests)
        teacher_students_ct.append(t_studs)
        teacher_avg_scores.append(avg)

    # ── DAILY ACTIVITY (area line, last 30 days) ──────────────────
    da_raw = (
        StudentAnswer.objects
        .filter(
            student__school=school,
            submitted_at__gte=now - timedelta(days=30),
        )
        .annotate(day=TruncDay('submitted_at'))
        .values('day')
        .annotate(active=Count('student', distinct=True))
        .order_by('day')
    )
    activity_labels = [r['day'].strftime('%d %b') for r in da_raw]
    activity_counts  = [r['active'] for r in da_raw]

    # ── TOP & BOTTOM PERFORMERS ───────────────────────────────────
    perf_map = {}
    for ans in StudentAnswer.objects.filter(
        student__school=school,
        marks_awarded__isnull=False,
    ).select_related('student', 'question'):
        k = ans.student_id
        perf_map.setdefault(k, {'name': ans.student.full_name, 'e': 0.0, 't': 0.0})
        perf_map[k]['e'] += float(ans.marks_awarded)
        perf_map[k]['t'] += float(ans.question.marks)

    perf_list = [
        {'name': v['name'], 'score': round(v['e'] / v['t'] * 100, 1)}
        for v in perf_map.values() if v['t'] > 0
    ]
    perf_list.sort(key=lambda x: -x['score'])
    top_names  = [p['name'] for p in perf_list[:8]]
    top_scores = [p['score'] for p in perf_list[:8]]
    bot_names  = [p['name'] for p in reversed(perf_list[-8:])] if len(perf_list) >= 8 else [p['name'] for p in reversed(perf_list)]
    bot_scores = [p['score'] for p in reversed(perf_list[-8:])] if len(perf_list) >= 8 else [p['score'] for p in reversed(perf_list)]

    # ── SUBJECT × GRADE HEATMAP ───────────────────────────────────
    sg_raw = list(
        StudentAnswer.objects
        .filter(
            student__school=school,
            marks_awarded__isnull=False,
            test__subject__isnull=False,
        )
        .values('test__subject__name', 'student__grade__name', 'student__grade__grade_level')
        .annotate(
            t=Sum(Cast('question__marks', FloatField())),
            e=Sum(Cast('marks_awarded', FloatField())),
        )
        .order_by('student__grade__grade_level', 'test__subject__name')
    )
    hm_grades   = list(dict.fromkeys(r['student__grade__name'] for r in sg_raw))
    hm_subjects = sorted(set(r['test__subject__name'] for r in sg_raw))
    heatmap_series = []
    for subj in hm_subjects:
        data = []
        for grade in hm_grades:
            match = next(
                (r for r in sg_raw
                 if r['test__subject__name'] == subj and r['student__grade__name'] == grade),
                None
            )
            y = round(match['e'] / match['t'] * 100, 1) if (match and match['t'] and match['t'] > 0) else 0
            data.append({'x': grade or 'N/A', 'y': y})
        heatmap_series.append({'name': subj, 'data': data})

    # ── AVERAGE LOGIN FREQUENCY (radar per grade) ─────────────────
    # Using last_login within last 7 / 14 / 30 days as tier buckets
    login_7d  = all_students_qs.filter(user__last_login__gte=now - timedelta(days=7)).count()
    login_14d = all_students_qs.filter(
        user__last_login__gte=now - timedelta(days=14),
        user__last_login__lt=now - timedelta(days=7),
    ).count()
    login_30d = all_students_qs.filter(
        user__last_login__gte=now - timedelta(days=30),
        user__last_login__lt=now - timedelta(days=14),
    ).count()
    login_old = all_students_qs.filter(
        user__last_login__lt=now - timedelta(days=30)
    ).count()
    login_never = all_students_qs.filter(user__last_login__isnull=True).count()

    context = {
        # KPIs
        'total_students':   total_students,
        'active_students':  active_students,
        'inactive_students': inactive_students,
        'online_students':  online_students,
        'writing_now':      writing_now,
        'total_questions':  total_questions,
        'total_tests':      total_tests,
        'pending_grading':  pending_grading,
        'school':           school,
        # Test status raw
        'test_draft': test_draft,
        'test_live':  test_live,
        'test_done':  test_done,
        # Login tiers
        'login_7d':   login_7d,
        'login_14d':  login_14d,
        'login_30d':  login_30d,
        'login_old':  login_old,
        'login_never': login_never,
        # JSON for ApexCharts
        'subject_labels':       _json.dumps(subject_labels),
        'subject_scores':       _json.dumps(subject_scores),
        'trend_labels':         _json.dumps(trend_labels),
        'trend_scores':         _json.dumps(trend_scores),
        'subj_trend_months':    _json.dumps(subj_trend_months),
        'subj_trend_series':    _json.dumps(subj_trend_series),
        'grade_labels':         _json.dumps(grade_labels),
        'grade_counts':         _json.dumps(grade_counts),
        'qt_labels':            _json.dumps(qt_labels),
        'qt_counts':            _json.dumps(qt_counts),
        'score_bands':          _json.dumps(score_bands),
        'teacher_names':        _json.dumps(teacher_names),
        'teacher_tests_ct':     _json.dumps(teacher_tests_ct),
        'teacher_students_ct':  _json.dumps(teacher_students_ct),
        'teacher_avg_scores':   _json.dumps(teacher_avg_scores),
        'activity_labels':      _json.dumps(activity_labels),
        'activity_counts':      _json.dumps(activity_counts),
        'top_names':            _json.dumps(top_names),
        'top_scores':           _json.dumps(top_scores),
        'bot_names':            _json.dumps(bot_names),
        'bot_scores':           _json.dumps(bot_scores),
        'heatmap_series':       _json.dumps(heatmap_series),
        'login_freq_data':      _json.dumps([login_7d, login_14d, login_30d, login_old, login_never]),
    }
    return render(request, 'teacher/academic_overview_dashboard.html', context)


@login_required
def student_dashboard(request):
    school = get_user_school(request.user)

    # Calculate real stats for the dashboard
    pending_tests = 0
    completed_tests = 0
    average_score = 0
    total_points = 0
    has_graded_results = False

    try:
        student = Student.objects.get(user=request.user)

        from django.db.models import Q
        assigned_tests = Test.objects.filter(
            Q(assigned_students=student) | Q(assigned_groups__students=request.user),
            is_published=True
        ).distinct()

        submitted_test_ids = set(
            StudentAnswer.objects.filter(student=student)
            .values_list('test_id', flat=True).distinct()
        )

        pending_tests = assigned_tests.exclude(id__in=submitted_test_ids).count()
        completed_tests = len(submitted_test_ids)

        graded = StudentAnswer.objects.filter(
            student=student, marks_awarded__isnull=False
        ).select_related('question')
        total_m = sum(float(a.question.marks or 0) for a in graded)
        earned_m = sum(float(a.marks_awarded or 0) for a in graded)
        average_score = round((earned_m / total_m * 100), 1) if total_m > 0 else 0
        total_points = round(earned_m, 1)
        has_graded_results = graded.exists()
    except Student.DoesNotExist:
        pass

    context = {
        'school': school,
        'pending_tests': pending_tests,
        'completed_tests': completed_tests,
        'average_score': average_score,
        'total_points': total_points,
        'has_graded_results': has_graded_results,
    }

    return render(request, "student/student_dashboard.html", context)


@login_required
def student_change_password(request):
    """Allow a student to change their own password."""
    if request.method == 'POST':
        current_password  = request.POST.get('current_password', '').strip()
        new_password      = request.POST.get('new_password', '').strip()
        confirm_password  = request.POST.get('confirm_password', '').strip()

        if not current_password or not new_password or not confirm_password:
            messages.error(request, 'All fields are required.')
        elif not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
        elif len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)  # keep session alive
            messages.success(request, '✓ Password changed successfully.')
            return redirect('student_dashboard')

    return render(request, 'student/student_change_password.html')


# ===================== USER MANAGEMENT =====================
# Replace your create_user_account view with this fixed version
from django.db import transaction

def enforce_staff_flag(user):
    if hasattr(user, "profile"):
        user.is_staff = user.profile.role in ("teacher", "school_admin")
        user.save(update_fields=["is_staff"])

@transaction.atomic
def create_user_with_role(
    *,
    email,
    password,
    full_name,
    role,
    school,
    created_by,
    grade=None,
    division=None,
    subject=None,
):
    email = email.lower().strip()

    # Create auth user
    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=full_name.split()[0],
        last_name=" ".join(full_name.split()[1:]),
    )

    # 🔒 STAFF RULE (HARD)
    user.is_staff = role in ("teacher", "school_admin")
    user.save()

    # Create profile (ALWAYS)
    profile = UserProfile.objects.create(
        user=user,
        role=role,
        school=school,
        grade=int(grade) if role == "student" and grade else None,
        division=division if role == "student" else None,
        subject=subject if role == "teacher" else None,
    )

    # Create Student record ONLY for students
    if role == "student":
        grade_obj = Grade.objects.get(name=str(grade))
        Student.objects.create(
            user=user,
            full_name=full_name,
            grade=grade_obj,
            section=division,
            school=school,
            created_by=created_by,
        )

    return user

@login_required
def create_user_account(request):
    school = get_user_school(request.user)

    # 🔁 Pull confirmation from session (if any)
    created_user = request.session.pop("created_user", None)
    created_password = request.session.pop("created_password", None)

    if request.method == 'POST':
        role = request.POST.get('role', 'student')

        email = request.POST.get('username', '').strip().lower()
        password = request.POST.get('password', '').strip()
        full_name = request.POST.get('name', '').strip()

        if not email or not password or not full_name:
            messages.error(request, 'All fields are required')
            return redirect('create_user_account')

        if User.objects.filter(username=email).exists():
            messages.error(request, f'Account with {email} already exists')
            return redirect('create_user_account')

        if role == 'teacher' and request.user.profile.role != 'school_admin':
            messages.error(request, 'Only school admins can create teacher accounts')
            return redirect('create_user_account')

        try:
            create_user_with_role(
                email=email,
                password=password,
                full_name=full_name,
                role=role,
                school=school,
                created_by=request.user,
                grade=request.POST.get('grade'),
                division=request.POST.get('division'),
                subject=request.POST.get('subject'),
            )

            # ✅ STORE confirmation in session
            request.session["created_user"] = email
            request.session["created_password"] = password

            return redirect('create_user_account')

        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return redirect('create_user_account')

    return render(request, 'teacher/create_user_account.html', {
        'school': school,
        'is_school_admin': request.user.profile.role == 'school_admin',
        'created_user': created_user,
        'created_password': created_password,
    })


# Add these views to your views.py

from django.db import transaction
from django.contrib.auth.models import User
from core.models import UserProfile, Student, Grade, Subject, School

def get_user_school(user):
    """Helper function to get user's school"""
    try:
        return user.profile.school
    except:
        return None

def get_user_role(user):
    """Helper function to get user's role"""
    if user.is_superuser:
        return 'superuser'
    try:
        return user.profile.role
    except:
        return 'student' if not user.is_staff else 'teacher'


@login_required
def add_user(request):
    """
    Add new teacher or student account
    - School admins can create teachers and students
    - Teachers can only create students
    """
    school = get_user_school(request.user)
    role = get_user_role(request.user)
    is_school_admin = (role == 'school_admin' or role == 'superuser' or request.user.is_superuser)
    
    if not school:
        messages.error(request, "You are not assigned to a school.")
        return redirect("teacher_dashboard")
    
    if request.method == "POST":
        new_user_role = request.POST.get("role", "student")
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()
        
        # Validation
        if not full_name or not email or not password:
            messages.error(request, "All required fields must be filled.")
            return redirect("add_user")
        
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect("add_user")
        
        # Permission check: Only school admin can create teachers
        if new_user_role == 'teacher' and not is_school_admin:
            messages.error(request, "Only school administrators can create teacher accounts.")
            return redirect("add_user")
        
        # Check if user already exists
        if User.objects.filter(username=email).exists():
            messages.error(request, f"An account with email {email} already exists.")
            return redirect("add_user")
        
        try:
            with transaction.atomic():
                # Split name
                name_parts = full_name.split()
                first_name = name_parts[0] if name_parts else ""
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                
                # Create User
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=(new_user_role in ['teacher', 'school_admin'])
                )
                
                # Create UserProfile
                profile = UserProfile.objects.create(
                    user=user,
                    role=new_user_role,
                    school=school
                )
                
                # Handle role-specific data
                if new_user_role == 'teacher':
                    # Teacher-specific
                    subject = request.POST.get("subject", "")
                    if subject:
                        profile.subject = subject
                        profile.save()
                    
                    messages.success(
                        request,
                        f'✓ Teacher account created successfully!\n'
                        f'Username: {email}\n'
                        f'Password: {password}'
                    )
                
                elif new_user_role == 'student':
                    # Student-specific
                    grade_name = request.POST.get("grade", "")
                    division = request.POST.get("division", "").strip()
                    roll_number = request.POST.get("roll_number", "").strip()
                    admission_id = request.POST.get("admission_id", "").strip()
                    
                    if not grade_name or not division:
                        raise ValueError("Grade and section are required for students")
                    
                    # Update profile
                    profile.grade = int(grade_name) if grade_name.isdigit() else None
                    profile.division = division
                    profile.save()
                    
                    # Create Student record
                    grade_obj = Grade.objects.get(name=grade_name)
                    Student.objects.create(
                        user=user,
                        full_name=full_name,
                        roll_number=roll_number,
                        admission_id=admission_id,
                        grade=grade_obj,
                        section=division,
                        school=school,
                        created_by=request.user
                    )
                    
                    messages.success(
                        request,
                        f'✓ Student account created successfully!\n'
                        f'Username: {email}\n'
                        f'Password: {password}'
                    )
                
                return redirect("manage_users")
        
        except Grade.DoesNotExist:
            messages.error(request, "Selected grade does not exist.")
        except Exception as e:
            messages.error(request, f"Error creating account: {str(e)}")
        
        return redirect("add_user")
    
    # GET request
    context = {
        'school': school,
        'is_school_admin': is_school_admin,
        'grades': Grade.objects.all(),
        'subjects': Subject.objects.all()
    }
    
    return render(request, "teacher/add_new_teacher_student.html", context)


@login_required
def manage_users(request):
    """
    View and manage all teachers and students
    - Show all users from the same school
    - Allow password changes based on permissions
    """
    school = get_user_school(request.user)
    role = get_user_role(request.user)
    is_school_admin = (role == 'school_admin' or role == 'superuser' or request.user.is_superuser)
    
    if not school:
        messages.error(request, "You are not assigned to a school.")
        return redirect("teacher_dashboard")
    
    # Get all user profiles from same school
    teachers = UserProfile.objects.filter(
        school=school,
        role__in=['teacher', 'school_admin']
    ).select_related('user').order_by('user__first_name', 'user__last_name')
    
    # Get student records
    students = Student.objects.filter(
        school=school
    ).select_related('grade', 'user').order_by('grade__name', 'section', 'roll_number')
    
    # Combine into unified list
    all_users = []
    
    for teacher in teachers:
        all_users.append({
            'user_id': teacher.user.id,
            'name': f"{teacher.user.first_name} {teacher.user.last_name}".strip() or teacher.user.username,
            'username': teacher.user.username,
            'email': teacher.user.email,
            'role': teacher.role,
            'role_display': teacher.get_role_display(),
            'joined': teacher.created_at,
            'additional_info': None,
            'student_id': None
        })
    
    for student in students:
        all_users.append({
            'user_id': student.user.id if student.user else None,
            'name': student.full_name,
            'username': student.user.username if student.user else 'No account',
            'email': student.user.email if student.user else '',
            'role': 'student',
            'role_display': 'Student',
            'joined': student.created_at,
            'additional_info': {
                'grade': student.grade.name,
                'section': student.section,
                'roll_number': student.roll_number,
                'admission_id': student.admission_id
            },
            'student_id': student.id
        })
    
    # Sort by name
    all_users.sort(key=lambda x: x['name'].lower())
    
    context = {
        'school': school,
        'all_users': all_users,
        'is_school_admin': is_school_admin,
        'role': role,
        'total_users': len(all_users),
        'total_teachers': teachers.count(),
        'total_students': students.count()
    }
    
    return render(request, "teacher/manage_teacher_student.html", context)


@login_required
def change_password(request):
    """
    Change password for users
    - School admin can change teacher and student passwords
    - Teacher can only change student passwords
    """
    if request.method != "POST":
        return redirect("manage_users")
    
    school = get_user_school(request.user)
    role = get_user_role(request.user)
    is_school_admin = (role == 'school_admin' or role == 'superuser' or request.user.is_superuser)
    
    user_id = request.POST.get("user_id")
    new_password = request.POST.get("new_password", "").strip()
    
    if not user_id or not new_password:
        messages.error(request, "User ID and password are required.")
        return redirect("manage_users")
    
    if len(new_password) < 8:
        messages.error(request, "Password must be at least 8 characters long.")
        return redirect("manage_users")
    
    try:
        user = User.objects.get(id=user_id)
        
        # Get the target user's role
        try:
            target_role = user.profile.role
        except:
            # Check if it's a student
            try:
                student = user.student_profile
                target_role = 'student'
            except:
                messages.error(request, "User profile not found.")
                return redirect("manage_users")
        
        # Permission check
        if target_role in ['teacher', 'school_admin'] and not is_school_admin:
            messages.error(request, "Only school administrators can change teacher passwords.")
            return redirect("manage_users")
        
        # Verify user belongs to same school
        try:
            user_profile = user.profile
            if user_profile.school != school:
                messages.error(request, "You can only change passwords for users in your school.")
                return redirect("manage_users")
        except:
            # Check student
            try:
                student = user.student_profile
                if student.school != school:
                    messages.error(request, "You can only change passwords for users in your school.")
                    return redirect("manage_users")
            except:
                messages.error(request, "User not found in your school.")
                return redirect("manage_users")
        
        # Change password
        user.set_password(new_password)
        user.save()
        
        messages.success(request, f"✓ Password changed successfully for {user.username}")
    
    except User.DoesNotExist:
        messages.error(request, "User not found.")
    except Exception as e:
        messages.error(request, f"Error changing password: {str(e)}")
    
    return redirect("manage_users")

# ===================== SCHOOL USERS LIST =====================
# Add this to your views.py
@login_required
def manage_students(request):
    """
    View and manage all students in the school
    """
    school = get_user_school(request.user)
    
    if not school:
        messages.error(request, "You are not assigned to a school.")
        return redirect("teacher_dashboard")
    
    # Get all students from the same school
    students = Student.objects.filter(
        school=school
    ).select_related('grade', 'school', 'created_by', 'user').order_by('grade', 'section', 'roll_number')
    
    # Get all grades for the edit modal dropdown
    grades = Grade.objects.all()
    
    context = {
        'students': students,
        'grades': grades,
        'school': school,
        'role': get_user_role(request.user)
    }
    
    return render(request, 'teacher/manage_students.html', context)



# You'll also need to add this URL pattern to urls.py:
# path("teacher/students/manage/", views.manage_students, name="manage_students"),


@login_required
def school_users_list(request):
    """
    View all teachers and students in the same school
    """
    school = get_user_school(request.user)
    role = get_user_role(request.user)
    
    if not school:
        messages.error(request, "You are not assigned to a school.")
        return redirect("teacher_dashboard")
    
    # Get all users from same school
    teachers = UserProfile.objects.filter(
        school=school,
        role__in=['teacher', 'school_admin']
    ).select_related('user')
    
    students_profiles = UserProfile.objects.filter(
        school=school,
        role='student'
    ).select_related('user')
    print(">>> SCHOOL USERS LIST VIEW HIT <<<")
    # Get student details
    students = Student.objects.filter(school=school).select_related('grade')
    
    context = {
        'school': school,
        'teachers': teachers,
        'students': students,
        'role': role
    }
    
    return render(request, "teacher/school/users_list.html", context)


# ===================== TESTS =====================

@login_required
def tests_list(request):
    school = get_user_school(request.user)
    if request.user.username == "sis_admin":
        tests = Test.objects.all()
    else:
        # Show tests created by the user OR shared with them
        from django.db.models import Q
        tests = Test.objects.filter(
            Q(created_by=request.user) | Q(assigned_teachers=request.user)
        ).distinct().select_related('created_by').order_by("-id")

    # Get teachers from same school for the assign-teacher modal
    teachers = UserProfile.objects.filter(
        school=school,
        role__in=['teacher', 'school_admin']
    ).exclude(user=request.user).select_related('user')

    return render(
        request,
        "teacher/tests_list.html",
        {"tests": tests, "school": school, "teachers": teachers}
    )


@login_required
def create_test(request):
    test = Test.objects.create(
        title="Untitled Test",
        created_by=request.user,
        is_published=False,
    )
    return redirect("edit_test", test_id=test.id)


@login_required
def create_descriptive_test(request):
    school = get_user_school(request.user)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            title = data.get('title', '').strip()
            questions_data = data.get('questions', [])

            if not title:
                return JsonResponse({'error': 'Title is required'}, status=400)
            if not questions_data:
                return JsonResponse({'error': 'At least one question is required'}, status=400)

            test = Test.objects.create(
                title=title,
                created_by=request.user,
                is_published=False,
            )
            test.descriptive_structure = json.dumps(questions_data)
            test.save()

            return JsonResponse({'success': True, 'test_id': test.id, 'message': 'Test created successfully'})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return render(request, 'teacher/create_descriptive_test.html', {'school': school})


@login_required
def edit_descriptive_test(request, test_id):
    school = get_user_school(request.user)
    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        return redirect("tests_list")

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            test.title = data.get('title', test.title)
            test.descriptive_structure = json.dumps(data.get('questions', []))
            test.save()
            return JsonResponse({'success': True, 'message': 'Test updated successfully'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    questions_data = []
    if test.descriptive_structure:
        try:
            questions_data = json.loads(test.descriptive_structure)
        except Exception:
            questions_data = []

    return render(request, 'teacher/create_descriptive_test.html', {
        'school': school,
        'test': test,
        'questions_data': json.dumps(questions_data),
    })



@login_required
def toggle_publish(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        return redirect("tests_list")
    test.is_published = not test.is_published
    test.save()
    return redirect("tests_list")


@login_required
def delete_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        return redirect("tests_list")
    test.delete()
    return redirect("tests_list")


@login_required
def duplicate_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        return redirect("tests_list")

    new_test = Test.objects.create(
        title=f"{test.title} (Copy)",
        created_by=request.user,
        duration_minutes=test.duration_minutes,
        start_time=test.start_time,
        subject=test.subject,
    )

    # Copy test questions
    test_questions = TestQuestion.objects.filter(test=test).order_by('order')
    for tq in test_questions:
        TestQuestion.objects.create(
            test=new_test,
            question=tq.question,
            order=tq.order,
        )

    return redirect("tests_list")


@login_required
def autosave_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        return JsonResponse({"error": "Access denied"}, status=403)
    data = json.loads(request.body)

    test.title = data.get("title", test.title)
    test.is_published = data.get("published", test.is_published)
    test.save()

    return JsonResponse({"status": "ok"})


# ===================== STUDENT TEST LIST WITH SORTING =====================




# ===================== QUESTIONS =====================

@login_required
def question_library(request):
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.db.models import Count

    school = get_user_school(request.user)
    qs = Question.objects.filter(
        created_by=request.user
    ).select_related("grade", "subject", "topic").prefetch_related("learning_objectives")

    # Annotate with usage count (how many tests use this question)
    qs = qs.annotate(usage_count=Count('testquestion', distinct=True))

    # Filters
    grade = request.GET.get("grade")
    subject = request.GET.get("subject")
    qtype = request.GET.get("question_type")
    marks = request.GET.get("marks")
    year = request.GET.get("year")
    usage_filter = request.GET.get("usage")  # 'most', 'least', 'unused'

    if grade:
        qs = qs.filter(grade_id=grade)
    if subject:
        qs = qs.filter(subject_id=subject)
    if qtype:
        qs = qs.filter(question_type=qtype)
    if marks:
        qs = qs.filter(marks=marks)
    if year:
        qs = qs.filter(year=year)
    if usage_filter == 'unused':
        qs = qs.filter(usage_count=0)
    elif usage_filter == 'least':
        qs = qs.filter(usage_count__gt=0)

    topics = request.GET.getlist("topics[]")
    if topics:
        qs = qs.filter(topic_id__in=topics)

    los = request.GET.getlist("los[]")
    if los:
        qs = qs.filter(learning_objectives__id__in=los).distinct()

    # Sorting
    sort_by = request.GET.get("sort", "id")
    order = request.GET.get("order", "desc")

    # Valid sort fields — now includes usage_count
    valid_sorts = ["id", "grade__name", "subject__name", "topic__name", "question_type", "marks", "year", "usage_count"]
    if sort_by not in valid_sorts:
        sort_by = "id"

    # Auto-sort for usage filters
    if usage_filter == 'most' and sort_by == 'id':
        sort_by = 'usage_count'
        order = 'desc'
    elif usage_filter == 'least' and sort_by == 'id':
        sort_by = 'usage_count'
        order = 'asc'

    # Apply sort with order
    if order == "asc":
        qs = qs.order_by(sort_by)
    else:
        qs = qs.order_by(f"-{sort_by}")

    # Pagination - 20 questions per page
    paginator = Paginator(qs, 20)
    page = request.GET.get("page", 1)

    try:
        questions = paginator.page(page)
    except PageNotAnInteger:
        questions = paginator.page(1)
    except EmptyPage:
        questions = paginator.page(paginator.num_pages)

    return render(
        request,
        "teacher/question_library.html",
        {
            "questions": questions,
            "grades": Grade.objects.all(),
            "subjects": Subject.objects.all(),
            "topics": Topic.objects.all(),
            "school": school,
            "current_sort": sort_by,
            "current_order": order,
            "current_usage": usage_filter or '',
        }
    )

# views.py
from django.http import JsonResponse
from .models import Question

def question_exists(request, pk):
    return JsonResponse({"exists": Question.objects.filter(pk=pk).exists()})


@login_required
def add_edit_question(request, question_id=None):
    question = None
    selected_lo_ids = []

    if question_id:
        question = get_object_or_404(
            Question,
            id=question_id,
            created_by=request.user
        )
        selected_lo_ids = list(
            question.learning_objectives.values_list("id", flat=True)
        )

    grades = Grade.objects.all()
    subjects = Subject.objects.all()
    topics = Topic.objects.all()

    if request.method == "POST":
        data = request.POST

        question_text = data.get("question_text", "").strip()
        answer_text = data.get("answer_text", "").strip()

        if not question_text:
            raise ValueError("Question text is empty")

        if not question:
            question = Question.objects.create(
                grade_id=data["grade"],
                subject_id=data["subject"],
                topic_id=data["topic"],
                year=data.get("year") or None,
                question_text=question_text,
                answer_text=answer_text,
                marks=data["marks"],
                question_type=data["question_type"],
                created_by=request.user,
            )
        else:
            question.grade_id = data["grade"]
            question.subject_id = data["subject"]
            question.topic_id = data["topic"]
            question.year = data.get("year") or None
            question.question_text = question_text
            question.answer_text = answer_text
            question.marks = data["marks"]
            question.question_type = data["question_type"]
            question.save()

        los_raw = data.get("los_selected", "")
        lo_ids = [int(x) for x in los_raw.split(",") if x]
        question.learning_objectives.set(lo_ids)

        return render(request, "teacher/close_window.html")

    years = list(range(2026, 1999, -1))

    return render(
        request,
        "teacher/question_editor.html",
        {
            "question": question,
            "grades": grades,
            "subjects": subjects,
            "topics": topics,
            "selected_lo_ids": selected_lo_ids,
            "years": years,
        }
    )


@login_required
def structured_question_editor(request):
    """
    New structured question editor - allows creating questions with sub-parts,
    per-question topic and LO tagging, and batch saving to library.
    """
    grades = Grade.objects.all().order_by('name')
    subjects = Subject.objects.all().order_by('name')

    return render(request, 'teacher/structured_question_editor.html', {
        'grades': grades,
        'subjects': subjects,
    })


@login_required
@staff_member_required
def delete_question(request, question_id):
    """Delete a question from the library"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    question = get_object_or_404(
        Question,
        id=question_id,
        created_by=request.user
    )

    # Check if question is used in any tests
    test_count = TestQuestion.objects.filter(question=question).count()
    if test_count > 0:
        return JsonResponse({
            'error': f'Cannot delete. This question is used in {test_count} test(s).'
        }, status=400)

    question.delete()
    return JsonResponse({'success': True, 'message': 'Question deleted successfully'})


@login_required
@staff_member_required
def edit_structured_question(request, question_id):
    """Edit structured question with answer space placement"""
    from .models import AnswerSpace, QuestionPage
    from .utils.image_processing import stitch_question_pages

    question = get_object_or_404(Question, id=question_id, created_by=request.user)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')

            if action == 'save_answer_spaces':
                # Delete existing answer spaces
                AnswerSpace.objects.filter(question=question).delete()

                # Create new answer spaces
                spaces_data = data.get('answer_spaces', [])
                for space_data in spaces_data:
                    AnswerSpace.objects.create(
                        question=question,
                        space_type=space_data.get('type', 'text_line'),
                        x=space_data['x'],
                        y=space_data['y'],
                        width=space_data['width'],
                        height=space_data['height'],
                        order=space_data.get('order', 0),
                        marks=space_data.get('marks', 1),
                        config=space_data.get('config', {})
                    )

                return JsonResponse({
                    'success': True,
                    'message': f'Saved {len(spaces_data)} answer space(s)'
                })

            return JsonResponse({'error': 'Invalid action'}, status=400)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # GET request - display editor
    # Check if question has multiple pages
    pages = QuestionPage.objects.filter(question=question).order_by('page_number')

    if pages.exists():
        # Stitch pages together
        pages_data = []
        for page in pages:
            pages_data.append({
                'page_number': page.page_number,
                'page_image': page.page_image,
                'has_green_line': page.has_green_line,
                'has_red_line': page.has_red_line,
                'blue_rect_x': page.blue_rect_x,
                'blue_rect_y': page.blue_rect_y,
                'blue_rect_width': page.blue_rect_width,
                'blue_rect_height': page.blue_rect_height
            })

        try:
            stitched_image = stitch_question_pages(pages_data)
        except Exception as e:
            messages.error(request, f'Error stitching pages: {str(e)}')
            stitched_image = pages_data[0]['page_image'] if pages_data else None
    else:
        # Single page question - use question_text as image if it's base64
        stitched_image = question.question_text if question.question_text.startswith('data:image') else None

    # Get existing answer spaces
    answer_spaces = AnswerSpace.objects.filter(question=question).order_by('order')
    answer_spaces_json = json.dumps([{
        'id': space.id,
        'type': space.space_type,
        'x': space.x,
        'y': space.y,
        'width': space.width,
        'height': space.height,
        'order': space.order,
        'marks': float(space.marks),
        'config': space.config
    } for space in answer_spaces])

    school = request.user.userprofile.school

    return render(request, 'teacher/edit_structured_question.html', {
        'question': question,
        'stitched_image': stitched_image,
        'answer_spaces_json': answer_spaces_json,
        'school': school,
        'page_count': pages.count()
    })


@login_required
def edit_question_v2(request, question_id):
    """
    Revamped unified question editor.
    - Shows question image with interactive answer-space overlays (QP-MS ingested questions).
    - Editable metadata: grade, subject, topic, year, marks, type, LOs.
    - Editable mark scheme (answer_text).
    - Add / move / resize / delete answer spaces inline.
    - Full save via a single POST endpoint.
    """
    from .models import AnswerSpace, QuestionPage
    from .utils.image_processing import stitch_question_pages

    # Allow editing questions from same school (not just own questions)
    question = get_object_or_404(Question, id=question_id)

    # ── POST: save all changes ───────────────────────────────────────
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # 1. Metadata
            question.grade_id    = data.get('grade_id',    question.grade_id)
            question.subject_id  = data.get('subject_id',  question.subject_id)
            question.topic_id    = data.get('topic_id',    question.topic_id)
            question.year        = data.get('year') or None
            question.marks       = data.get('marks',       question.marks)
            question.question_type = data.get('question_type', question.question_type)
            question.answer_text = data.get('answer_text', question.answer_text)

            # 2. question_text: only update when the client sends it
            #    (text-mode editors send HTML; image-mode questions keep existing img tag)
            if 'question_text' in data and data['question_text']:
                question.question_text = data['question_text']

            question.save()

            # 3. Learning objectives
            if 'lo_ids' in data:
                question.learning_objectives.set(data['lo_ids'])

            # 4. Answer spaces (full replace)
            if 'answer_spaces' in data:
                AnswerSpace.objects.filter(question=question).delete()
                for idx, sp in enumerate(data['answer_spaces']):
                    AnswerSpace.objects.create(
                        question=question,
                        space_type=sp.get('type', 'text_line'),
                        x=int(sp.get('x', 0)),
                        y=int(sp.get('y', 0)),
                        width=int(sp.get('width', 600)),
                        height=int(sp.get('height', 80)),
                        order=sp.get('order', idx),
                        marks=sp.get('marks', 1),
                        config=sp.get('config', {}),
                    )

            return JsonResponse({'success': True, 'message': 'Saved successfully'})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    # ── GET: build editor context ────────────────────────────────────

    # Determine if there is a displayable image
    pages = QuestionPage.objects.filter(question=question).order_by('page_number')
    question_image = None

    if pages.exists():
        pages_data = [
            {
                'page_number': p.page_number,
                'page_image':  p.page_image,
                'has_green_line': p.has_green_line,
                'has_red_line':   p.has_red_line,
                'blue_rect_x':    p.blue_rect_x,
                'blue_rect_y':    p.blue_rect_y,
                'blue_rect_width':  p.blue_rect_width,
                'blue_rect_height': p.blue_rect_height,
            }
            for p in pages
        ]
        try:
            question_image = stitch_question_pages(pages_data)
        except Exception:
            question_image = pages_data[0]['page_image']
    elif question.question_text.strip().startswith('<img') or \
         question.question_text.strip().startswith('data:image'):
        question_image = question.question_text.strip()
        # If it's a raw base64 string (no <img> tag), keep as-is for the <img src="">
        # If it's an <img> tag, extract the src
        import re
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', question_image)
        if m:
            question_image = m.group(1)

    # Answer spaces JSON
    answer_spaces = AnswerSpace.objects.filter(question=question).order_by('order')
    answer_spaces_json = json.dumps([
        {
            'id':     sp.id,
            'type':   sp.space_type,
            'x':      sp.x,
            'y':      sp.y,
            'width':  sp.width,
            'height': sp.height,
            'order':  sp.order,
            'marks':  float(sp.marks),
            'config': sp.config,
        }
        for sp in answer_spaces
    ])

    # LOs for the current topic
    selected_lo_ids = list(question.learning_objectives.values_list('id', flat=True))

    grades   = Grade.objects.all()
    subjects = Subject.objects.all()
    topics   = Topic.objects.all()
    years    = list(range(2026, 1999, -1))

    return render(request, 'teacher/edit_question_v2.html', {
        'question':          question,
        'question_image':    question_image,
        'answer_spaces_json': answer_spaces_json,
        'selected_lo_ids':   selected_lo_ids,
        'grades':            grades,
        'subjects':          subjects,
        'topics':            topics,
        'years':             years,
        'page_count':        pages.count(),
    })


@login_required
def inline_add_question(request, test_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        data = json.loads(request.body)

        if not data.get("question_text"):
            return JsonResponse({"error": "Question text is required"}, status=400)
        
        if not data.get("grade") or not data.get("subject") or not data.get("topic"):
            return JsonResponse({"error": "Grade, subject, and topic are required"}, status=400)

        question = Question.objects.create(
            question_text=data["question_text"],
            answer_text=data.get("answer_text", ""),
            marks=data.get("marks", 1),
            question_type=data.get("question_type", "theory"),
            year=data.get("year") or None,
            grade_id=data["grade"],
            subject_id=data["subject"],
            topic_id=data["topic"],
            created_by=request.user,
        )
        
        lo_ids = data.get("learning_objectives", [])
        if lo_ids:
            question.learning_objectives.set(lo_ids)

        last_order = (
            TestQuestion.objects
            .filter(test=test)
            .aggregate(max_order=models.Max("order"))
            ["max_order"] or 0
        )

        tq = TestQuestion.objects.create(
            test=test,
            question=question,
            order=last_order + 1
        )

        return JsonResponse({
            "status": "ok",
            "question_id": question.id,
            "order": tq.order,
            "message": "Question added successfully"
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def remove_question_from_test(request, test_id, test_question_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        return JsonResponse({"error": "Access denied"}, status=403)
    test_question = get_object_or_404(TestQuestion, id=test_question_id, test=test)
    
    test_question.delete()
    
    # Reorder
    remaining_questions = TestQuestion.objects.filter(test=test).order_by('order')
    for idx, tq in enumerate(remaining_questions, start=1):
        if tq.order != idx:
            tq.order = idx
            tq.save()
    
    return JsonResponse({"status": "ok", "message": "Question removed"})


@login_required
def add_questions_to_test(request, test_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        return JsonResponse({"error": "Access denied"}, status=403)
    
    try:
        data = json.loads(request.body)
        question_ids = data.get("question_ids", [])
        
        if not question_ids:
            return JsonResponse({"error": "No questions selected"}, status=400)
        
        max_order = TestQuestion.objects.filter(test=test).aggregate(
            models.Max('order')
        )['order__max'] or 0
        
        for idx, question_id in enumerate(question_ids):
            question = get_object_or_404(Question, id=question_id)
            
            if not TestQuestion.objects.filter(test=test, question=question).exists():
                TestQuestion.objects.create(
                    test=test,
                    question=question,
                    order=max_order + idx + 1
                )
        
        return JsonResponse({"status": "ok", "message": "Questions added successfully"})
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ===================== STUDENTS =====================

# Replace your add_student view in views.py with this

@login_required
def add_student(request):
    school = get_user_school(request.user)
    
    if request.method == "POST":
        from django.db import transaction
        
        try:
            with transaction.atomic():
                full_name = request.POST["full_name"]
                roll_number = request.POST.get("roll_number", "")
                admission_id = request.POST.get("admission_id", "")
                grade_id = request.POST["grade"]
                section = request.POST["section"]
                
                # Get the Grade object
                grade = Grade.objects.get(id=grade_id)
                
                # Create student record
                student = Student.objects.create(
                    full_name=full_name,
                    roll_number=roll_number,
                    admission_id=admission_id,
                    grade=grade,
                    section=section,
                    school=school,
                    created_by=request.user
                )
                
                # Generate username
                base_username = admission_id if admission_id else \
                               full_name.lower().replace(' ', '_')
                username = base_username
                counter = 1
                
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                # Create user account
                user = User.objects.create_user(
                    username=username,
                    first_name=full_name.split()[0] if full_name else '',
                    last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
                    password='student123'  # Default password
                )
                
                # Create UserProfile with student role
                profile, created = UserProfile.objects.get_or_create(user=user)
                profile.role = 'student'
                profile.school = school
                profile.grade = int(grade.name) if grade.name.isdigit() else None
                profile.division = section
                profile.save()
                
                # Link user to student
                student.user = user
                student.save()
                
                messages.success(
                    request, 
                    f'Student "{full_name}" added successfully! Username: {username}, Password: student123'
                )
                
        except Exception as e:
            messages.error(request, f'Error creating student: {str(e)}')
            
        return redirect("students_list")

    return render(request, "teacher/students/add_student.html", {
        "grades": Grade.objects.all(),
        "school": school
    })
@login_required
def students_list(request):
    school = get_user_school(request.user)
    students = Student.objects.filter(school=school)

    return render(request, "teacher/students/students_list.html", {
        "students": students,
        "school": school
    })


@login_required
def edit_student(request, student_id):
    school = get_user_school(request.user)
    student = get_object_or_404(Student, id=student_id, school=school)

    if request.method == "POST":
        student.full_name = request.POST.get("full_name")
        student.roll_number = request.POST.get("roll_number", "")
        student.admission_id = request.POST.get("admission_id", "")
        student.grade_id = request.POST.get("grade")
        student.section = request.POST.get("section")
        student.save()
        return redirect("students_list")

    return render(
        request,
        "teacher/students/edit_student.html",
        {
            "student": student,
            "grades": Grade.objects.all(),
            "school": school,
        }
    )


# ===================== GROUPS =====================

@login_required
def add_group(request):
    school = get_user_school(request.user)
    
    if request.method == "POST":
        group = ClassGroup.objects.create(
            name=request.POST["name"],
            grade_id=request.POST["grade"],
            section=request.POST["section"],
            subject_id=request.POST["subject"],
            school=school,
            created_by=request.user
        )

        student_ids = request.POST.getlist("students")
        group.students.set(student_ids)

        return redirect("groups_list")

    return render(request, "teacher/groups/add_group.html", {
        "grades": Grade.objects.all(),
        "subjects": Subject.objects.all(),
        "students": Student.objects.filter(school=school),
        "school": school,
    })


@login_required
def groups_list(request):
    school = get_user_school(request.user)
    groups = ClassGroup.objects.filter(school=school, created_by=request.user)
    return render(
        request,
        "teacher/groups/groups_list.html",
        {"groups": groups, "school": school}
    )


# ===================== AJAX =====================

@login_required
def ajax_topics(request):
    grade_id = request.GET.get("grade_id")
    subject_id = request.GET.get("subject_id")

    qs = Topic.objects.all()

    if grade_id:
        qs = qs.filter(grade_id=grade_id)
    if subject_id:
        qs = qs.filter(subject_id=subject_id)

    topics = [
        {"id": t.id, "name": t.name}
        for t in qs.order_by("name")
    ]

    return JsonResponse({"topics": topics})


@login_required
@require_GET
def ajax_learning_objectives(request):
    topic_id = request.GET.get("topic_id")

    if not topic_id:
        return JsonResponse({"los": []})

    los = LearningObjective.objects.filter(
        topic_id=topic_id
    ).order_by("code")

    return JsonResponse({
        "los": [
            {
                "id": lo.id,
                "code": lo.code,
                "description": lo.description,
            }
            for lo in los
        ]
    })


@staff_member_required
def admin_dashboard(request):
    return render(request, "admin_panel/admin_dashboard.html")
    
@login_required
def class_performance(request):
    school = get_user_school(request.user)
    return render(request, "teacher/performance/class_performance.html", {
        "school": school
    })


@login_required
def student_performance(request, student_id):
    school = get_user_school(request.user)
    student = get_object_or_404(Student, id=student_id, school=school)
    return render(request, "teacher/performance/student_performance.html", {
        "school": school,
        "student": student
    })

# Add these views to your views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q

@login_required
def manage_class_groups(request):
    """
    Main page for managing class groups (all teachers can access)
    """
    school = get_user_school(request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if action == 'create':
            # Create new group
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            color = request.POST.get('color', '#3b82f6')
            grade_id = request.POST.get('grade')
            student_ids = request.POST.getlist('students')
            
            if not name:
                if is_ajax:
                    return JsonResponse({'error': 'Group name is required'}, status=400)
                messages.error(request, 'Group name is required')
                return redirect('manage_class_groups')
            
            try:
                group = ClassGroup.objects.create(
                    name=name,
                    school=school,
                    created_by=request.user,
                    grade_id=grade_id if grade_id else None,
                )
                
                # Add color if the field exists
                if hasattr(group, 'color'):
                    group.color = color
                    group.save()
                
                # Add description if the field exists
                if hasattr(group, 'description'):
                    group.description = description
                    group.save()
                
                # Add students
                if student_ids:
                    students = User.objects.filter(
                        id__in=student_ids,
                        profile__school=school,
                        profile__role='student'
                    )
                    group.students.set(students)
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Group "{name}" created successfully',
                        'group_id': group.id
                    })
                
                messages.success(request, f'Group "{name}" created successfully with {len(student_ids)} students')
                return redirect('manage_class_groups')
                
            except Exception as e:
                if is_ajax:
                    return JsonResponse({'error': str(e)}, status=500)
                messages.error(request, f'Error creating group: {str(e)}')
                return redirect('manage_class_groups')
        
        elif action == 'edit':
            # Edit existing group
            group_id = request.POST.get('group_id')
            
            if not group_id:
                if is_ajax:
                    return JsonResponse({'error': 'Group ID is required'}, status=400)
                messages.error(request, 'Group ID is required')
                return redirect('manage_class_groups')
            
            try:
                group = get_object_or_404(ClassGroup, id=group_id, school=school)
                
                group.name = request.POST.get('name', group.name)
                grade_id = request.POST.get('grade')
                group.grade_id = grade_id if grade_id else None
                
                # Update optional fields if they exist
                if hasattr(group, 'description'):
                    group.description = request.POST.get('description', '')
                
                if hasattr(group, 'color'):
                    group.color = request.POST.get('color', group.color if hasattr(group, 'color') else '#3b82f6')
                
                group.save()
                
                # Update students
                student_ids = request.POST.getlist('students')
                if student_ids:
                    students = User.objects.filter(
                        id__in=student_ids,
                        profile__school=school,
                        profile__role='student'
                    )
                    group.students.set(students)
                else:
                    group.students.clear()
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Group "{group.name}" updated successfully'
                    })
                
                messages.success(request, f'Group "{group.name}" updated successfully')
                return redirect('manage_class_groups')
                
            except Exception as e:
                if is_ajax:
                    return JsonResponse({'error': str(e)}, status=500)
                messages.error(request, f'Error updating group: {str(e)}')
                return redirect('manage_class_groups')
        
        elif action == 'delete':
            # Delete group
            group_id = request.POST.get('group_id')
            
            try:
                group = get_object_or_404(ClassGroup, id=group_id, school=school)
                group_name = group.name
                group.delete()
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Group "{group_name}" deleted successfully'
                    })
                
                messages.success(request, f'Group "{group_name}" deleted successfully')
                return redirect('manage_class_groups')
                
            except Exception as e:
                if is_ajax:
                    return JsonResponse({'error': str(e)}, status=500)
                messages.error(request, f'Error deleting group: {str(e)}')
                return redirect('manage_class_groups')
    
    # GET request - display groups
    groups = ClassGroup.objects.filter(
        school=school
    ).prefetch_related('students').order_by('name')
    
    # Get all students in the school
    students = User.objects.filter(
        profile__school=school,
        profile__role='student'
    ).select_related('profile').order_by('profile__grade', 'profile__division', 'first_name')
    
    grades = Grade.objects.all()
    
    return render(request, 'teacher/manage_class_groups.html', {
        'groups': groups,
        'students': students,
        'grades': grades,
        'school': school
    })

@login_required
def get_group_students(request, group_id):
    """
    API endpoint to get students in a specific group
    """
    school = get_user_school(request.user)
    group = get_object_or_404(ClassGroup, id=group_id, school=school)
    
    student_ids = list(group.students.values_list('id', flat=True))
    
    return JsonResponse({
        'student_ids': student_ids,
        'count': len(student_ids)
    })

# Add these new views to your views.py

import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST

# ===================== STUDENT TEST TAKING =====================


# CRITICAL FIX: Update these specific views in your views.py file

@login_required
def test_editor(request, test_id):
    """
    Test editor with proper student assignment handling.
    Allows access for test creator and assigned teachers.
    """
    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        messages.error(request, "You don't have access to this test.")
        return redirect("tests_list")
    school = get_user_school(request.user)

    if request.method == "POST":
        # Save test details
        test.title = request.POST.get("title", test.title)
        test.is_published = bool(request.POST.get("is_published"))
        
        # Handle datetime
        start_time = request.POST.get("start_time")
        if start_time:
            test.start_time = start_time
        else:
            test.start_time = None
            
        duration = request.POST.get("duration_minutes")
        if duration:
            test.duration_minutes = int(duration)
        else:
            test.duration_minutes = None
        
        # Handle subject
        subject_id = request.POST.get("subject")
        if subject_id:
            test.subject_id = subject_id
        else:
            test.subject = None
            
        test.save()

        # Handle student assignments - CRITICAL FIX
        # Get individual student IDs from the hidden inputs
        assigned_student_ids = request.POST.getlist("assigned_students")
        
        # Clear existing assignments and set new ones
        test.assigned_students.clear()
        test.assigned_groups.clear()
        
        if assigned_student_ids:
            # Validate that these students belong to the teacher's school
            valid_students = Student.objects.filter(
                id__in=assigned_student_ids,
                school=school
            )
            test.assigned_students.set(valid_students)

        # Handle teacher assignments (only the creator can manage teacher assignments)
        if test.created_by == request.user or request.user.username == 'sis_admin':
            assigned_teacher_ids = request.POST.getlist("assigned_teachers")
            if assigned_teacher_ids:
                valid_teachers = User.objects.filter(
                    id__in=assigned_teacher_ids,
                    profile__school=school,
                    profile__role__in=['teacher', 'school_admin']
                )
                test.assigned_teachers.set(valid_teachers)
            else:
                test.assigned_teachers.clear()

        messages.success(request, "Test saved successfully!")
        return redirect("edit_test", test_id=test.id)

    # GET request - load test data
    test_questions = TestQuestion.objects.filter(
        test=test
    ).select_related('question', 'question__topic', 'question__grade', 'question__subject').order_by('order')
    
    # Get students and groups from same school
    students = Student.objects.filter(school=school).select_related('grade', 'user').order_by('grade__name', 'section', 'roll_number')
    groups = ClassGroup.objects.filter(school=school, created_by=request.user).prefetch_related('students')
    
    # Get currently assigned students
    assigned_students = test.assigned_students.all()

    # Get currently assigned teachers
    assigned_teacher_ids = list(test.assigned_teachers.values_list('id', flat=True))

    # Get all teachers from same school (for teacher assignment dropdown)
    school_teachers = UserProfile.objects.filter(
        school=school,
        role__in=['teacher', 'school_admin']
    ).exclude(user=request.user).exclude(user=test.created_by).select_related('user')

    subjects = Subject.objects.all()

    return render(
        request,
        "teacher/create_test.html",
        {
            "test": test,
            "test_questions": test_questions,
            "groups": groups,
            "students": students,
            "assigned_students": assigned_students,
            "assigned_teacher_ids": assigned_teacher_ids,
            "school_teachers": school_teachers,
            "grades": Grade.objects.all(),
            "subjects": subjects,
            "school": school,
            "is_owner": test.created_by == request.user or request.user.username == 'sis_admin',
        }
    )


@login_required
def student_tests_list(request):
    """
    Show all published tests assigned to the logged-in student
    CRITICAL FIX: Changed from created_by to user lookup
    """
    # Get student profile - FIXED
    try:
        student = Student.objects.get(user=request.user)  # ✅ FIXED: was created_by=request.user
    except Student.DoesNotExist:
        return render(request, "student/student_tests_list.html", {
            "tests_with_status": [],
            "error": "Student profile not found. Please contact your teacher.",
            "student": None,
        })
    
    # Get sorting parameters
    sort_by = request.GET.get('sort', 'date')
    order = request.GET.get('order', 'desc')
    subject_filter = request.GET.get('subject', '')
    
    # Get tests assigned directly to this student
    directly_assigned = Test.objects.filter(
        assigned_students=student,
        is_published=True
    )
    
    # Get tests assigned through groups (if using group-based assignment)
    # Note: Since we're now using individual student assignment, this may not be needed
    # but keeping it for backward compatibility
    student_groups = ClassGroup.objects.filter(students__student_profile=student)
    group_assigned = Test.objects.filter(
        assigned_groups__in=student_groups,
        is_published=True
    )
    
    # Combine and remove duplicates
    all_tests = (directly_assigned | group_assigned).distinct()
    
    # Apply subject filter
    if subject_filter:
        all_tests = all_tests.filter(subject_id=subject_filter)
    
    # Apply sorting
    if sort_by == 'subject':
        all_tests = all_tests.order_by('subject__name' if order == 'asc' else '-subject__name')
    else:  # date
        all_tests = all_tests.order_by('created_at' if order == 'asc' else '-created_at')
    
    # Add attempt status
    tests_with_status = []
    for test in all_tests:
        attempts = StudentAnswer.objects.filter(
            student=student,
            test=test
        ).count()
        
        tests_with_status.append({
            'test': test,
            'attempted': attempts > 0,
            'attempt_count': attempts
        })
    
    # Get available subjects for filter dropdown
    subjects = Subject.objects.filter(
        test__in=all_tests
    ).distinct()
    
    return render(request, "student/student_tests_list.html", {
        "tests_with_status": tests_with_status,
        "student": student,
        "sort_by": sort_by,
        "order": order,
        "subject_filter": subject_filter,
        "subjects": subjects,
    })


@login_required
def take_test(request, test_id):
    """
    Student interface for taking a test
    CRITICAL FIX: Changed from created_by to user lookup
    """
    # Get student profile - FIXED
    try:
        student = Student.objects.get(user=request.user)  # ✅ FIXED: was created_by=request.user
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found")
        return redirect("student_dashboard")
    
    test = get_object_or_404(Test, id=test_id, is_published=True)
    
    # Check if student is assigned to this test
    is_directly_assigned = test.assigned_students.filter(id=student.id).exists()
    
    # Check group assignment
    student_groups = ClassGroup.objects.filter(students__student_profile=student)
    is_group_assigned = test.assigned_groups.filter(id__in=student_groups).exists()
    
    if not (is_directly_assigned or is_group_assigned):
        messages.error(request, "You are not assigned to this test")
        return redirect("student_tests_list")
    
    # Get test questions
    test_questions = TestQuestion.objects.filter(
        test=test
    ).select_related('question').order_by('order')

    # Prepare test data with pages structure (one question per page)
    test_data = {
        'test_id': test.id,
        'title': test.title,
        'duration': test.duration_minutes,
        'pages': []
    }

    for idx, tq in enumerate(test_questions, 1):
        question = tq.question

        # Build question data with hierarchical sub-questions
        question_data = build_question_data_recursive(question, f'Q{idx}')

        # Each question (with all its sub-questions) is a separate page
        test_data['pages'].append({
            'pageNumber': idx,
            'questions': [question_data]
        })

    return render(request, 'student/student_take_test.html', {
        'test': test,
        'test_data': json.dumps(test_data),  # Convert to JSON string
        'student': student,
        'question_count': test_questions.count()
    })


# Additional helper function for debugging
@login_required
def debug_student_assignments(request, test_id):
    """
    DEBUG VIEW - Remove in production
    Shows assignment details for troubleshooting
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    test = get_object_or_404(Test, id=test_id)
    
    assigned_students = test.assigned_students.all().values('id', 'full_name', 'user__username')
    assigned_groups = test.assigned_groups.all().values('id', 'name')
    
    return JsonResponse({
        'test': {
            'id': test.id,
            'title': test.title,
            'is_published': test.is_published,
        },
        'assigned_students': list(assigned_students),
        'assigned_groups': list(assigned_groups),
        'total_assigned': test.assigned_students.count(),
    })

def convert_to_pages(questions_structure):
    """
    Convert hierarchical question structure to paginated format for student view
    Each main question becomes a page
    """
    pages = []
    
    for idx, main_question in enumerate(questions_structure, 1):
        page = {
            'pageNumber': idx,
            'questions': [convert_question_to_display_format(main_question)]
        }
        pages.append(page)
    
    return {'pages': pages}


def convert_question_to_display_format(question, parent_number=''):
    """
    Recursively convert question structure to display format
    """
    result = {
        'number': question.get('number', ''),
        'content': question.get('content', ''),
        'marks': question.get('marks', 1),
        'subQuestions': []
    }
    
    # Add answer field if this is a leaf question (no children)
    if not question.get('children') or len(question.get('children', [])) == 0:
        result['answerId'] = f"q{question.get('id', '')}"
    
    # Process children
    if question.get('children'):
        for child in question['children']:
            sub_q = convert_question_to_display_format(child, result['number'])
            result['subQuestions'].append(sub_q)
    
    return result


def convert_regular_test_to_pages(test):
    """
    Convert regular question-bank test to paginated format
    """
    pages = []
    test_questions = TestQuestion.objects.filter(test=test).select_related('question').order_by('order')
    
    for idx, tq in enumerate(test_questions, 1):
        page = {
            'pageNumber': idx,
            'questions': [{
                'number': str(idx),
                'content': tq.question.question_text,
                'marks': tq.question.marks,
                'answerId': f'q{tq.question.id}',
                'subQuestions': []
            }]
        }
        pages.append(page)
    
    return {'pages': pages}


@login_required
@require_POST
def autosave_test_answers(request, test_id):
    """
    Auto-save student answers and track current question
    """
    try:
        student = Student.objects.get(user=request.user)
        test = get_object_or_404(Test, id=test_id)

        data = json.loads(request.body)
        answers = data.get('answers', {})
        current_page = data.get('currentPage', 0)
        question_timers = data.get('questionTimers', {})

        # Save answers to database
        for answer_key, answer_text in answers.items():
            # Handle structured question answer spaces: "space-<question_id>-<space_id>"
            if answer_key.startswith('space-'):
                try:
                    parts = answer_key.split('-')
                    if len(parts) >= 3:
                        question_id = int(parts[1])
                        space_id = int(parts[2])

                        question = Question.objects.get(id=question_id)
                        answer_space = AnswerSpace.objects.get(id=space_id, question=question)

                        # Get or create StudentAnswer for the question
                        student_answer, _ = StudentAnswer.objects.get_or_create(
                            student=student,
                            test=test,
                            question=question
                        )

                        # Create or update StudentAnswerSpace
                        StudentAnswerSpace.objects.update_or_create(
                            student_answer=student_answer,
                            answer_space=answer_space,
                            defaults={
                                'text_response': answer_text
                            }
                        )
                except (ValueError, Question.DoesNotExist, AnswerSpace.DoesNotExist):
                    continue

            # Handle rasterized images: "space-<question_id>-<space_id>-raster"
            elif answer_key.startswith('space-') and answer_key.endswith('-raster'):
                try:
                    parts = answer_key.replace('-raster', '').split('-')
                    if len(parts) >= 3:
                        question_id = int(parts[1])
                        space_id = int(parts[2])

                        question = Question.objects.get(id=question_id)
                        answer_space = AnswerSpace.objects.get(id=space_id, question=question)

                        # Get or create StudentAnswer for the question
                        student_answer, _ = StudentAnswer.objects.get_or_create(
                            student=student,
                            test=test,
                            question=question
                        )

                        # Update rasterized image
                        StudentAnswerSpace.objects.update_or_create(
                            student_answer=student_answer,
                            answer_space=answer_space,
                            defaults={
                                'rasterized_image': answer_text  # Base64 image data
                            }
                        )
                except (ValueError, Question.DoesNotExist, AnswerSpace.DoesNotExist):
                    continue

            # Handle structured answer form parts: "structured-<question_id>-<part_id>"
            elif answer_key.startswith('structured-'):
                try:
                    parts = answer_key.split('-')
                    if len(parts) >= 3:
                        question_id = int(parts[1])
                        part_id = '-'.join(parts[2:])  # Part ID might contain hyphens

                        question = Question.objects.get(id=question_id)

                        # Get or create StudentAnswer for the question
                        student_answer, created = StudentAnswer.objects.get_or_create(
                            student=student,
                            test=test,
                            question=question
                        )

                        # Store structured answers in JSON format
                        # Retrieve existing structured_answers or initialize
                        existing_answers = {}
                        if student_answer.answer_text:
                            try:
                                # Check if it's JSON structured answers
                                if student_answer.answer_text.startswith('{'):
                                    existing_answers = json.loads(student_answer.answer_text)
                            except json.JSONDecodeError:
                                # Existing text is not JSON, preserve it
                                existing_answers = {'_legacy': student_answer.answer_text}

                        # Update the specific part
                        existing_answers[part_id] = answer_text

                        # Save as JSON
                        student_answer.answer_text = json.dumps(existing_answers)
                        student_answer.save()

                except (ValueError, Question.DoesNotExist):
                    continue

            # Extract question ID from format "q123" -> 123 (regular questions)
            elif answer_key.startswith('q'):
                try:
                    question_id = int(answer_key[1:])
                    question = Question.objects.get(id=question_id)

                    defaults = {'answer_text': answer_text}
                    timer_val = question_timers.get(str(question_id))
                    if timer_val is not None:
                        defaults['time_spent_seconds'] = int(timer_val)

                    # Create or update StudentAnswer
                    StudentAnswer.objects.update_or_create(
                        student=student,
                        test=test,
                        question=question,
                        defaults=defaults
                    )
                except (ValueError, Question.DoesNotExist):
                    continue

        # Update time for any questions tracked but not yet answered
        for q_id_str, seconds in question_timers.items():
            try:
                q_id = int(q_id_str)
                StudentAnswer.objects.filter(
                    student=student, test=test, question_id=q_id
                ).update(time_spent_seconds=int(seconds))
            except (ValueError, Exception):
                continue

        # Store current page in session for monitoring
        request.session[f'test_{test_id}_current_page'] = current_page
        request.session[f'test_{test_id}_answers'] = answers

        return JsonResponse({'success': True, 'message': 'Answers saved'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_saved_answers(request, test_id):
    """
    Retrieve saved answers for a test
    """
    try:
        answers = request.session.get(f'test_{test_id}_answers', {})
        return JsonResponse({'answers': answers})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def submit_test(request, test_id):
    """
    Submit completed test - saves all answers and marks test as submitted
    """
    try:
        student = Student.objects.get(user=request.user)
        test = get_object_or_404(Test, id=test_id)

        data = json.loads(request.body)
        answers = data.get('answers', {})
        question_timers = data.get('questionTimers', {})

        # Group answers by question
        question_answers = {}  # question_id -> {part_id: answer_text}

        for answer_key, answer_text in answers.items():
            if answer_key.startswith('structured-'):
                # Structured answer: "structured-<question_id>-<part_id>"
                parts = answer_key.split('-')
                if len(parts) >= 3:
                    question_id = int(parts[1])
                    part_id = '-'.join(parts[2:])

                    if question_id not in question_answers:
                        question_answers[question_id] = {}
                    question_answers[question_id][part_id] = answer_text

            elif answer_key.startswith('space-'):
                # Legacy overlay answer: "space-<question_id>-<space_id>"
                parts = answer_key.split('-')
                if len(parts) >= 3:
                    question_id = int(parts[1])
                    space_id = parts[2]

                    if question_id not in question_answers:
                        question_answers[question_id] = {}
                    question_answers[question_id][f'space_{space_id}'] = answer_text

            elif answer_key.startswith('q'):
                # Regular answer: "q<question_id>"
                try:
                    question_id = int(answer_key[1:])
                    if question_id not in question_answers:
                        question_answers[question_id] = {}
                    question_answers[question_id]['main'] = answer_text
                except ValueError:
                    continue

        # Save answers to database
        for question_id, parts_answers in question_answers.items():
            try:
                question = Question.objects.get(id=question_id)

                # For structured questions, store as JSON
                if len(parts_answers) > 1 or 'main' not in parts_answers:
                    answer_text = json.dumps(parts_answers)
                else:
                    answer_text = parts_answers.get('main', '')

                time_spent = question_timers.get(str(question_id))

                # For structured questions with parts, also save to answer_parts
                if len(parts_answers) > 1 or 'main' not in parts_answers:
                    defaults = {
                        'answer_text': answer_text,
                        'answer_parts': parts_answers
                    }
                else:
                    defaults = {'answer_text': answer_text}

                if time_spent is not None:
                    defaults['time_spent_seconds'] = int(time_spent)

                StudentAnswer.objects.update_or_create(
                    student=student,
                    test=test,
                    question=question,
                    defaults=defaults
                )
            except Question.DoesNotExist:
                continue

        # Clear session answers
        if f'test_{test_id}_answers' in request.session:
            del request.session[f'test_{test_id}_answers']
        if f'test_{test_id}_current_page' in request.session:
            del request.session[f'test_{test_id}_current_page']

        return JsonResponse({
            'success': True,
            'message': 'Test submitted successfully'
        })

    except Exception as e:
        import traceback
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


# ===================== TEST MONITORING & GRADING =====================

from django.utils import timezone
from django.views.decorators.http import require_POST

@login_required
@staff_member_required
def monitor_test(request, test_id):
    """
    Real-time test monitoring page for teachers
    Shows students taking the test, their progress, and status
    """
    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        return redirect("tests_list")

    # Get all students assigned to this test
    assigned_students = test.get_all_assigned_students()

    # Get student answers and calculate progress
    student_progress = []
    for student in assigned_students:
        # Get all questions for this test
        if test.test_type == 'standard':
            total_questions = test.test_questions.count()
        else:
            # For descriptive tests, count questions in JSON structure
            if test.descriptive_structure:
                try:
                    structure = json.loads(test.descriptive_structure)
                    total_questions = sum(len(section.get('questions', [])) for section in structure.get('sections', []))
                except:
                    total_questions = 0
            else:
                total_questions = 0

        # Get answered questions
        answered_questions = StudentAnswer.objects.filter(
            student=student,
            test=test
        ).count()

        # Get latest answer time
        latest_answer = StudentAnswer.objects.filter(
            student=student,
            test=test
        ).order_by('-submitted_at').first()

        # Calculate progress percentage
        progress_percentage = (answered_questions / total_questions * 100) if total_questions > 0 else 0

        # Determine status
        has_submitted = StudentAnswer.objects.filter(
            student=student,
            test=test,
            submitted_at__isnull=False
        ).exists()

        if has_submitted:
            status = 'Submitted'
        elif answered_questions > 0:
            status = 'Started'
        else:
            status = 'Not Started'

        # Get current question from session (if student is actively taking test)
        from django.contrib.sessions.models import Session
        current_question = None
        if student.user:
            # Try to find active session and current page
            sessions = Session.objects.filter(expire_date__gte=timezone.now())
            for session in sessions:
                session_data = session.get_decoded()
                if session_data.get(f'test_{test_id}_current_page') is not None:
                    # Check if this session belongs to this student
                    user_id = session_data.get('_auth_user_id')
                    if user_id and int(user_id) == student.user.id:
                        current_question = session_data.get(f'test_{test_id}_current_page', 0) + 1
                        break

        student_progress.append({
            'student': student,
            'progress': int(progress_percentage),
            'answered': answered_questions,
            'total': total_questions,
            'status': status,
            'last_activity': latest_answer.submitted_at if latest_answer else None,
            'current_question': current_question
        })

    context = {
        'test': test,
        'student_progress': student_progress,
        'total_students': len(student_progress),
        'started_count': sum(1 for sp in student_progress if sp['status'] in ['Started', 'Submitted']),
        'submitted_count': sum(1 for sp in student_progress if sp['status'] == 'Submitted'),
    }

    return render(request, 'teacher/monitor_test.html', context)


@login_required
@staff_member_required
def monitor_test_api(request, test_id):
    """
    API endpoint for real-time monitoring data
    Returns JSON with current test status
    """
    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        return JsonResponse({"error": "Access denied"}, status=403)
    assigned_students = test.get_all_assigned_students()

    # Get student progress data
    students_data = []
    for student in assigned_students:
        if test.test_type == 'standard':
            total_questions = test.test_questions.count()
        else:
            if test.descriptive_structure:
                try:
                    structure = json.loads(test.descriptive_structure)
                    total_questions = sum(len(section.get('questions', [])) for section in structure.get('sections', []))
                except:
                    total_questions = 0
            else:
                total_questions = 0

        answered_questions = StudentAnswer.objects.filter(
            student=student,
            test=test
        ).count()

        latest_answer = StudentAnswer.objects.filter(
            student=student,
            test=test
        ).order_by('-submitted_at').first()

        progress_percentage = (answered_questions / total_questions * 100) if total_questions > 0 else 0

        # Get current question from session
        from django.contrib.sessions.models import Session
        current_question = None
        if student.user:
            sessions = Session.objects.filter(expire_date__gte=timezone.now())
            for session in sessions:
                session_data = session.get_decoded()
                user_id = session_data.get('_auth_user_id')
                if user_id and int(user_id) == student.user.id:
                    current_question = session_data.get(f'test_{test_id}_current_page', 0) + 1
                    break

        students_data.append({
            'id': student.id,
            'name': student.full_name,
            'roll_number': student.roll_number,
            'progress': int(progress_percentage),
            'answered': answered_questions,
            'total': total_questions,
            'last_activity': latest_answer.submitted_at.isoformat() if latest_answer else None,
            'current_question': current_question
        })

    return JsonResponse({
        'students': students_data,
        'timestamp': timezone.now().isoformat()
    })


@login_required
@staff_member_required
def grade_test_answers(request, test_id):
    """
    Teacher page for grading student answers
    Shows all student submissions with AI-assisted grading
    """
    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        return redirect("tests_list")

    # Get all students who submitted answers
    students_with_answers = Student.objects.filter(
        answers__test=test
    ).distinct()

    # Filter by student if specified
    selected_student_id = request.GET.get('student')
    if selected_student_id:
        selected_student = get_object_or_404(Student, id=selected_student_id)
    else:
        selected_student = students_with_answers.first()

    # Get questions and answers for selected student
    grading_data = []
    if selected_student:
        if test.test_type == 'standard':
            # Standard test with question bank
            test_questions = test.test_questions.all().order_by('order')

            for tq in test_questions:
                question = tq.question
                student_answer = StudentAnswer.objects.filter(
                    student=selected_student,
                    test=test,
                    question=question
                ).first()

                grading_data.append({
                    'question': question,
                    'test_question': tq,
                    'student_answer': student_answer,
                    'max_marks': question.marks,
                    'awarded_marks': student_answer.marks_awarded if student_answer else None,
                })
        else:
            # Descriptive test
            if test.descriptive_structure:
                try:
                    structure = json.loads(test.descriptive_structure)
                    # Handle descriptive structure
                    # This would need custom handling based on your structure
                except:
                    pass

    # Calculate statistics
    total_marks = sum(gd['max_marks'] for gd in grading_data)
    awarded_marks = sum(gd['awarded_marks'] or 0 for gd in grading_data if gd['awarded_marks'] is not None)
    graded_count = sum(1 for gd in grading_data if gd['awarded_marks'] is not None)
    pending_count = len(grading_data) - graded_count

    context = {
        'test': test,
        'students_with_answers': students_with_answers,
        'selected_student': selected_student,
        'grading_data': grading_data,
        'total_marks': total_marks,
        'awarded_marks': awarded_marks,
        'graded_count': graded_count,
        'pending_count': pending_count,
        'percentage': (awarded_marks / total_marks * 100) if total_marks > 0 else 0,
    }

    return render(request, 'teacher/grade_test_answers.html', context)


@login_required
@staff_member_required
def grade_test_spreadsheet(request, test_id):
    """
    Spreadsheet-style grading view with all students and questions
    """
    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        return redirect("tests_list")


    # Get all students who submitted answers
    students_with_answers = Student.objects.filter(
        answers__test=test
    ).distinct().order_by('full_name')

    # Get questions
    questions = []
    if test.test_type == 'standard':
        test_questions = test.test_questions.all().order_by('order')
        questions = [tq.question for tq in test_questions]

    # Build spreadsheet data
    grading_spreadsheet = []
    for student in students_with_answers:
        student_row = {
            'student': {
                'id': student.id,
                'full_name': student.full_name,
                'grade': student.grade.name if student.grade else '',
                'section': student.section or '',
            },
            'answers': [],
            'total_marks': 0,
            'max_total': 0,
        }

        for question in questions:
            student_answer = StudentAnswer.objects.filter(
                student=student,
                test=test,
                question=question
            ).first()

            if student_answer:
                # Check if question has answer spaces (structured question)
                answer_spaces = AnswerSpace.objects.filter(question=question).order_by('order')
                has_spaces = answer_spaces.exists()

                answer_data = {
                    'id': student_answer.id,
                    'answer_text': student_answer.answer_text,
                    'marks_awarded': float(student_answer.marks_awarded) if student_answer.marks_awarded is not None else None,
                    'max_marks': float(question.marks),
                    'has_answer_spaces': has_spaces,
                }

                # Add answer space responses if structured question
                if has_spaces:
                    space_responses = []
                    for space in answer_spaces:
                        space_response = StudentAnswerSpace.objects.filter(
                            student_answer=student_answer,
                            answer_space=space
                        ).first()

                        space_responses.append({
                            'space_id': space.id,
                            'space_type': space.space_type,
                            'space_order': space.order,
                            'space_marks': float(space.marks),
                            'text_response': space_response.text_response if space_response else '',
                            'rasterized_image': space_response.rasterized_image if space_response else '',
                            'marks_awarded': float(space_response.marks_awarded) if space_response and space_response.marks_awarded is not None else None,
                        })

                    answer_data['answer_spaces'] = space_responses

                if student_answer.marks_awarded is not None:
                    student_row['total_marks'] += float(student_answer.marks_awarded)
            else:
                # Create empty answer placeholder
                answer_data = {
                    'id': None,
                    'answer_text': '',
                    'marks_awarded': None,
                    'max_marks': float(question.marks),
                    'has_answer_spaces': False,
                }

            student_row['answers'].append(answer_data)
            student_row['max_total'] += float(question.marks)

        grading_spreadsheet.append(student_row)

    # Prepare JSON data for JavaScript
    import json
    grading_spreadsheet_json = json.dumps(grading_spreadsheet)

    context = {
        'test': test,
        'students_with_answers': students_with_answers,
        'questions': questions,
        'grading_spreadsheet': grading_spreadsheet,
        'grading_spreadsheet_json': grading_spreadsheet_json,
    }

    return render(request, 'teacher/grade_test_spreadsheet.html', context)


@login_required
@staff_member_required
@require_POST
def save_grade(request, test_id=None):
    """
    Save individual question grade
    """
    try:
        data = json.loads(request.body)
        answer_id = data.get('answer_id')
        marks = data.get('marks')

        student_answer = get_object_or_404(StudentAnswer, id=answer_id)

        # Verify the teacher owns this test
        if student_answer.test.created_by != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        # Validate marks
        max_marks = student_answer.question.marks
        if marks is not None and (marks < 0 or marks > max_marks):
            return JsonResponse({'error': f'Marks must be between 0 and {max_marks}'}, status=400)

        # Save marks
        student_answer.marks_awarded = marks
        student_answer.evaluated_at = timezone.now()
        student_answer.evaluated_by = request.user
        student_answer.save()

        return JsonResponse({
            'success': True,
            'marks_awarded': marks,
            'evaluated_at': student_answer.evaluated_at.isoformat()
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@staff_member_required
@require_POST
def save_answer_space_grade(request):
    """
    Save grade for individual answer space in structured question
    """
    try:
        data = json.loads(request.body)
        student_answer_id = data.get('student_answer_id')
        space_id = data.get('space_id')
        marks = data.get('marks')
        feedback = data.get('feedback', '')

        student_answer = get_object_or_404(StudentAnswer, id=student_answer_id)
        answer_space = get_object_or_404(AnswerSpace, id=space_id)

        # Verify the teacher owns this test
        if student_answer.test.created_by != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        # Validate marks
        max_marks = answer_space.marks
        if marks is not None and (marks < 0 or marks > max_marks):
            return JsonResponse({'error': f'Marks must be between 0 and {max_marks}'}, status=400)

        # Get or create StudentAnswerSpace
        space_response, created = StudentAnswerSpace.objects.get_or_create(
            student_answer=student_answer,
            answer_space=answer_space
        )

        # Save marks and feedback
        space_response.marks_awarded = marks
        space_response.feedback = feedback
        space_response.save()

        # Recalculate total marks for StudentAnswer
        total_marks = StudentAnswerSpace.objects.filter(
            student_answer=student_answer
        ).aggregate(
            total=models.Sum('marks_awarded')
        )['total'] or 0

        student_answer.marks_awarded = total_marks
        student_answer.evaluated_at = timezone.now()
        student_answer.evaluated_by = request.user
        student_answer.save()

        return JsonResponse({
            'success': True,
            'marks_awarded': marks,
            'total_marks': float(total_marks)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@staff_member_required
@require_POST
def ai_grade_answer(request):
    """
    Use AI to suggest a grade for an answer
    This is a placeholder - you'll need to integrate with an AI service
    """
    try:
        data = json.loads(request.body)
        answer_id = data.get('answer_id')

        student_answer = get_object_or_404(StudentAnswer, id=answer_id)

        # Verify the teacher owns this test
        if student_answer.test.created_by != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        question = student_answer.question
        student_response = student_answer.answer_text
        model_answer = question.answer_text
        max_marks = question.marks

        # AI Grading Logic (Placeholder)
        # In production, you would call an AI service like OpenAI, Claude, etc.
        # For now, we'll return a simple heuristic

        # Simple similarity check (you should replace this with actual AI)
        if not student_response or not student_response.strip():
            suggested_marks = 0
            feedback = "No answer provided"
        elif not model_answer or not model_answer.strip():
            suggested_marks = max_marks  # Give benefit of doubt if no model answer
            feedback = "No model answer available for comparison"
        else:
            # Very basic similarity (replace with AI)
            response_words = set(student_response.lower().split())
            answer_words = set(model_answer.lower().split())

            if len(answer_words) > 0:
                similarity = len(response_words & answer_words) / len(answer_words)
                suggested_marks = round(similarity * max_marks, 2)

                if similarity > 0.8:
                    feedback = "Excellent answer covering most key points"
                elif similarity > 0.6:
                    feedback = "Good answer with room for improvement"
                elif similarity > 0.4:
                    feedback = "Partial answer, missing some key concepts"
                else:
                    feedback = "Answer lacks many expected concepts"
            else:
                suggested_marks = max_marks / 2
                feedback = "Unable to compare with model answer"

        return JsonResponse({
            'success': True,
            'suggested_marks': suggested_marks,
            'max_marks': max_marks,
            'feedback': feedback,
            'ai_used': False,  # Set to True when using actual AI
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@staff_member_required
@require_POST
def publish_results(request, test_id):
    """
    Publish test results to students.
    Only publishes results for students whose answers are ALL graded.
    Does NOT block if some students still have ungraded answers.
    """
    try:
        test = get_object_or_404(Test, id=test_id)
        if not test.user_has_access(request.user):
            return JsonResponse({'error': 'Access denied'}, status=403)

        # Count students who have submitted answers
        submitted_students = Student.objects.filter(
            answers__test=test
        ).distinct()
        total_submitted = submitted_students.count()

        # Count students who are fully graded (all their answers have marks)
        fully_graded_count = 0
        pending_count = 0
        for student in submitted_students:
            student_answers = StudentAnswer.objects.filter(student=student, test=test)
            if student_answers.exists() and not student_answers.filter(marks_awarded__isnull=True).exists():
                fully_graded_count += 1
            else:
                pending_count += 1

        if fully_graded_count == 0:
            return JsonResponse({
                'success': False,
                'error': 'No students have fully graded answers yet. Grade at least one student before publishing.',
            }, status=400)

        # Set the flag — students with graded answers can now see results
        test.results_published = True
        test.save(update_fields=['results_published'])

        return JsonResponse({
            'success': True,
            'message': f'Results published for {fully_graded_count} student(s).',
            'fully_graded': fully_graded_count,
            'pending': pending_count,
            'total_submitted': total_submitted,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ===================== STUDENT RESULTS =====================

@login_required
def student_results(request):
    """
    Show all test results for the logged-in student
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found")
        return redirect("student_dashboard")

    # Get all tests where student has submitted answers
    submitted_tests = Test.objects.filter(
        student_answers__student=student
    ).distinct()

    results = []
    for test in submitted_tests:
        # Get all student answers for this test
        student_answers = StudentAnswer.objects.filter(
            student=student,
            test=test
        )

        # Calculate total marks
        total_marks = sum(sa.question.marks for sa in student_answers)
        scored_marks = sum(sa.marks_awarded or 0 for sa in student_answers)

        # Check if this student's answers are all graded
        graded_count = student_answers.filter(marks_awarded__isnull=False).count()
        total_count = student_answers.count()
        is_graded = graded_count == total_count and total_count > 0

        # Only show result if teacher has published results AND this student is fully graded
        if test.results_published and is_graded and total_marks > 0:
            percentage = (scored_marks / total_marks) * 100
            results.append({
                'test': test,
                'scored_marks': scored_marks,
                'total_marks': total_marks,
                'percentage': round(percentage, 1),
                'is_graded': True,
                'submitted_at': student_answers.first().submitted_at if student_answers.exists() else None
            })
        elif not test.results_published and is_graded:
            # Submitted and graded but not yet published — show as "pending release"
            results.append({
                'test': test,
                'scored_marks': None,
                'total_marks': total_marks,
                'percentage': None,
                'is_graded': False,
                'pending_release': True,
                'submitted_at': student_answers.first().submitted_at if student_answers.exists() else None
            })

    context = {
        'results': results,
        'student': student
    }

    return render(request, 'student/results.html', context)


@login_required
def student_test_review(request, test_id):
    """
    Show detailed test review with questions, answers, and marks
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found")
        return redirect("student_dashboard")

    test = get_object_or_404(Test, id=test_id)

    # Get student answers for this test
    student_answers = StudentAnswer.objects.filter(
        student=student,
        test=test
    ).select_related('question')

    # Check if all answers are graded
    graded_count = student_answers.filter(marks_awarded__isnull=False).count()
    total_count = student_answers.count()
    is_fully_graded = graded_count == total_count and total_count > 0

    if not is_fully_graded:
        messages.warning(request, "This test has not been fully graded yet")

    # Prepare question-answer pairs
    review_data = []
    if test.test_type == 'standard':
        test_questions = test.test_questions.all().order_by('order').select_related('question__topic')

        for tq in test_questions:
            question = tq.question
            student_answer = student_answers.filter(question=question).first()

            review_data.append({
                'question': question,
                'test_question': tq,
                'student_answer': student_answer,
                'max_marks': question.marks,
                'awarded_marks': student_answer.marks_awarded if student_answer else None,
            })

    # Calculate totals
    total_marks = sum(rd['max_marks'] for rd in review_data)
    scored_marks = sum(rd['awarded_marks'] or 0 for rd in review_data if rd['awarded_marks'] is not None)
    percentage = (scored_marks / total_marks * 100) if total_marks > 0 else 0

    # ── Topic-wise performance stats ──────────────────────────────
    topic_map = {}
    for rd in review_data:
        topic_obj = rd['question'].topic
        topic_name = topic_obj.name if topic_obj else 'General'
        topic_id = topic_obj.id if topic_obj else None
        if topic_name not in topic_map:
            topic_map[topic_name] = {
                'name': topic_name,
                'topic_id': topic_id,
                'total_marks': 0,
                'awarded_marks': 0.0,
                'question_count': 0,
                'graded_count': 0,
                'percentage': None,
                'mastery': 'Pending Evaluation',
            }
        s = topic_map[topic_name]
        s['total_marks']    += rd['max_marks']
        s['question_count'] += 1
        if rd['awarded_marks'] is not None:
            s['awarded_marks'] += float(rd['awarded_marks'])
            s['graded_count']  += 1

    for s in topic_map.values():
        if s['graded_count'] > 0 and s['total_marks'] > 0:
            pct = (s['awarded_marks'] / s['total_marks']) * 100
            s['percentage'] = round(pct, 1)
            if pct >= 80:
                s['mastery'] = 'Mastered'
            elif pct >= 60:
                s['mastery'] = 'Good'
            elif pct >= 40:
                s['mastery'] = 'Needs Improvement'
            else:
                s['mastery'] = 'Weak'

    # Sort: weakest first (best practice recommendation order), ungraded at end
    topic_stats = sorted(
        topic_map.values(),
        key=lambda x: (x['percentage'] is None, x['percentage'] if x['percentage'] is not None else 0)
    )
    weak_topics = [t for t in topic_stats if t['percentage'] is not None and t['percentage'] < 60]

    context = {
        'test': test,
        'student': student,
        'review_data': review_data,
        'total_marks': total_marks,
        'scored_marks': scored_marks,
        'percentage': round(percentage, 1),
        'is_fully_graded': is_fully_graded,
        'topic_stats': topic_stats,
        'weak_topics': weak_topics,
    }

    return render(request, 'student/test_review.html', context)


@login_required
def student_practice(request, topic_id):
    """
    Show 5 practice questions from a weak topic for the student.
    The student can view them and print as a PDF using jsPDF.
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found")
        return redirect("student_dashboard")

    topic = get_object_or_404(Topic, id=topic_id)

    # Get questions from this topic that the student has NOT answered correctly
    # First, get question IDs the student already answered well (>= 70%)
    well_answered_ids = list(
        StudentAnswer.objects.filter(
            student=student,
            question__topic=topic,
            marks_awarded__isnull=False,
        ).values_list('question_id', 'marks_awarded', 'question__marks')
    )

    skip_ids = set()
    for qid, awarded, qmax in well_answered_ids:
        if qmax and qmax > 0 and float(awarded) / float(qmax) >= 0.7:
            skip_ids.add(qid)

    # Fetch questions from this topic, excluding well-answered ones, parent-level only
    practice_qs = (
        Question.objects.filter(topic=topic, parent__isnull=True)
        .exclude(id__in=skip_ids)
        .order_by('?')[:5]
    )

    # If not enough, fill with any questions from this topic
    if practice_qs.count() < 5:
        remaining = 5 - practice_qs.count()
        extra_ids = set(practice_qs.values_list('id', flat=True))
        extra_qs = (
            Question.objects.filter(topic=topic, parent__isnull=True)
            .exclude(id__in=extra_ids)
            .order_by('?')[:remaining]
        )
        practice_qs = list(practice_qs) + list(extra_qs)
    else:
        practice_qs = list(practice_qs)

    # Also try nearby LOs if not enough questions
    if len(practice_qs) < 5:
        remaining = 5 - len(practice_qs)
        existing_ids = set(q.id for q in practice_qs)
        # Get questions from same subject/grade, nearby topics
        nearby_qs = (
            Question.objects.filter(
                grade=topic.grade,
                subject=topic.subject,
                parent__isnull=True,
            )
            .exclude(id__in=existing_ids)
            .order_by('?')[:remaining]
        )
        practice_qs = practice_qs + list(nearby_qs)

    context = {
        'student': student,
        'topic': topic,
        'practice_questions': practice_qs,
        'question_count': len(practice_qs),
    }

    return render(request, 'student/practice.html', context)


@login_required
@staff_member_required
def edit_school_settings(request):
    """
    Allow school admin / teacher to view and edit school details.
    """
    school = get_user_school(request.user)
    if not school:
        messages.error(request, "No school associated with your account.")
        return redirect("teacher_dashboard")

    if request.method == 'POST':
        school.name = request.POST.get('name', school.name).strip()
        school.address = request.POST.get('address', school.address).strip()
        school.phone = request.POST.get('phone', school.phone).strip()
        school.email = request.POST.get('email', school.email).strip()
        school.code = request.POST.get('code', school.code).strip()
        school.save()
        messages.success(request, "School details updated successfully.")
        return redirect("edit_school_settings")

    context = {
        'school': school,
    }
    return render(request, 'teacher/school_settings.html', context)


@login_required
@staff_member_required
def assign_teachers_to_test(request):
    """
    API endpoint to assign/update teachers for a test.
    POST { test_id: int, teacher_ids: [int,...] }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
        test_id = data.get('test_id')
        teacher_ids = data.get('teacher_ids', [])

        test = get_object_or_404(Test, id=test_id)
        # Only the test creator (or sis_admin) can assign teachers
        if test.created_by != request.user and request.user.username != 'sis_admin':
            return JsonResponse({'error': 'Only the test creator can assign teachers.'}, status=403)

        school = get_user_school(request.user)
        valid_teachers = User.objects.filter(
            id__in=teacher_ids,
            profile__school=school,
            profile__role__in=['teacher', 'school_admin']
        ).exclude(id=test.created_by.id)

        test.assigned_teachers.set(valid_teachers)

        return JsonResponse({
            'success': True,
            'assigned_count': valid_teachers.count(),
            'teacher_names': list(valid_teachers.values_list('first_name', flat=True)),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@staff_member_required
def get_test_teachers(request, test_id):
    """API endpoint to get currently assigned teachers for a test."""
    test = get_object_or_404(Test, id=test_id)
    if not test.user_has_access(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)

    assigned = list(test.assigned_teachers.values('id', 'first_name', 'last_name', 'username'))
    return JsonResponse({'teachers': assigned})


@login_required
@staff_member_required
def import_mcq_images(request):
    """Import MCQ questions from PNG images"""
    import base64

    grades = Grade.objects.all()
    subjects = Subject.objects.all()

    if request.method == 'POST':
        try:
            grade_id = request.POST.get('grade')
            subject_id = request.POST.get('subject')
            topic_id = request.POST.get('topic')
            year = request.POST.get('year') or None
            marks = int(request.POST.get('marks', 1))
            total_images = int(request.POST.get('total_images', 0))

            if not all([grade_id, subject_id, topic_id]):
                return JsonResponse({'error': 'Missing required fields'}, status=400)

            imported_count = 0

            for i in range(total_images):
                image_file = request.FILES.get(f'image_{i}')
                correct_answer = request.POST.get(f'correct_{i}')

                if not image_file or not correct_answer:
                    continue

                # Read image and convert to base64
                image_data = image_file.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')

                # Create HTML img tag with base64 data
                question_html = f'<img src="data:image/png;base64,{base64_image}" alt="MCQ Question" style="max-width: 100%; height: auto;" />'

                # Create question
                Question.objects.create(
                    grade_id=grade_id,
                    subject_id=subject_id,
                    topic_id=topic_id,
                    year=year,
                    question_text=question_html,
                    answer_text=correct_answer,  # Store correct answer (A, B, C, or D)
                    marks=marks,
                    question_type='mcq',
                    created_by=request.user
                )

                imported_count += 1

            messages.success(request, f'Successfully imported {imported_count} MCQ questions!')
            return JsonResponse({'success': True, 'count': imported_count})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    context = {
        'grades': grades,
        'subjects': subjects,
    }

    return render(request, 'teacher/import_mcq_images.html', context)


@login_required
@staff_member_required
def import_mcq_pdf(request):
    """Import MCQ questions from multiple PDFs with automatic QP-MS pairing"""
    import base64
    import re
    from pathlib import Path

    grades = Grade.objects.all()
    subjects = Subject.objects.all()

    if request.method == 'POST':
        try:
            grade_id = request.POST.get('grade_id')
            subject_id = request.POST.get('subject_id')
            year = request.POST.get('year')  # Get year from form
            total_images = int(request.POST.get('total_images', 0))

            if not all([grade_id, subject_id]):
                return JsonResponse({'error': 'Missing grade or subject'}, status=400)

            # Get the first topic for this subject (since we're not asking for topic)
            # User can change it later if needed via the to-do list and AI tagging
            topic = Topic.objects.filter(subject_id=subject_id).first()
            if not topic:
                return JsonResponse({'error': 'No topics found for this subject'}, status=400)

            imported_count = 0

            for i in range(total_images):
                image_data = request.POST.get(f'image_{i}')
                correct_answer = request.POST.get(f'answer_{i}')

                if not image_data or not correct_answer:
                    continue

                # Extract base64 from data URL
                base64_str = image_data.split(',')[1]

                # Create HTML img tag
                question_html = f'<img src="data:image/png;base64,{base64_str}" alt="MCQ Question" style="max-width: 100%; height: auto;" />'

                # Create question with year if provided
                question_data = {
                    'grade_id': grade_id,
                    'subject_id': subject_id,
                    'topic_id': topic.id,
                    'question_text': question_html,
                    'answer_text': correct_answer,
                    'marks': 1,
                    'question_type': 'mcq',
                    'created_by': request.user
                }

                if year:  # Add year only if provided
                    question_data['year'] = int(year)

                Question.objects.create(**question_data)

                imported_count += 1

            messages.success(request, f'Successfully imported {imported_count} MCQ questions!')
            return JsonResponse({'success': True, 'count': imported_count})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    context = {
        'grades': grades,
        'subjects': subjects,
    }

    return render(request, 'teacher/import_mcq_pdf.html', context)


@login_required
@staff_member_required
def import_qp_slices(request):
    """Import structured/theory questions from QP Slicer Workstation"""
    import base64

    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        grade_id = request.POST.get('grade_id')
        subject_id = request.POST.get('subject_id')
        year = request.POST.get('year')
        question_type = request.POST.get('question_type', 'structured')
        total_images = int(request.POST.get('total_images', 0))

        if not all([grade_id, subject_id]):
            return JsonResponse({'error': 'Missing grade or subject'}, status=400)

        # Get the first topic for this subject
        topic = Topic.objects.filter(subject_id=subject_id).first()
        if not topic:
            return JsonResponse({'error': 'No topics found for this subject'}, status=400)

        imported_count = 0

        for i in range(total_images):
            image_data = request.POST.get(f'image_{i}')
            marks = request.POST.get(f'marks_{i}', 5)

            if not image_data:
                continue

            # Extract base64 from data URL
            if ',' in image_data:
                base64_str = image_data.split(',')[1]
            else:
                base64_str = image_data

            # Create HTML img tag
            question_html = f'<img src="data:image/png;base64,{base64_str}" alt="Question {i+1}" style="max-width: 100%; height: auto;" />'

            # Create question
            question_data = {
                'grade_id': grade_id,
                'subject_id': subject_id,
                'topic_id': topic.id,
                'question_text': question_html,
                'answer_text': '',  # Can be filled in later via AI or manual entry
                'marks': int(marks) if marks else 5,
                'question_type': question_type,
                'created_by': request.user
            }

            if year:
                question_data['year'] = int(year)

            Question.objects.create(**question_data)
            imported_count += 1

        return JsonResponse({'success': True, 'count': imported_count})

    except Exception as e:
        import traceback
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


def _get_lmstudio_model(lmstudio_url):
    """Return the LMStudio model ID to use.
    Priority: Django settings → /api/v1/models (0.4.x) → /v1/models (0.3.x) → fallback."""
    import requests as _req
    from django.conf import settings as _s
    # 1. Django settings (set via LMSTUDIO_MODEL env var or settings.py)
    configured = getattr(_s, 'LMSTUDIO_MODEL', None)
    if configured:
        return configured
    # 2. Dynamically query the running server — try both API paths
    base = lmstudio_url.split('/v1/')[0]  # e.g. http://127.0.0.1:1234
    for path in ('/api/v1/models', '/v1/models'):
        try:
            r = _req.get(f"{base}{path}", timeout=5)
            if r.status_code == 200:
                models = r.json().get('data', [])
                if models:
                    print(f"[LMStudio] model discovered via {path}: {models[0]['id']}")
                    return models[0]['id']
        except Exception:
            pass
    # 3. Fallback
    return 'openai/gpt-oss-20b'


@login_required
@staff_member_required
def ai_suggest_topic(request):
    """AI-powered topic suggestion for questions with context-aware prompting and OCR"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        question_text = data.get('question_text', '')   # mark scheme / answer text
        question_id = data.get('question_id')           # DB question id
        subject_id = data.get('subject_id')
        grade_id = data.get('grade_id')

        if not subject_id or not grade_id:
            return JsonResponse({'error': 'Missing required fields (subject, grade)'}, status=400)

        # Get subject and grade names for context-aware prompting
        from .models import Subject, Grade, QuestionPage
        try:
            subject = Subject.objects.get(id=subject_id)
            grade = Grade.objects.get(id=grade_id)
            subject_name = subject.name
            grade_name = grade.name
        except (Subject.DoesNotExist, Grade.DoesNotExist):
            return JsonResponse({'error': 'Invalid subject or grade'}, status=400)

        # Get all topics for the given subject AND grade combination
        topics = Topic.objects.filter(subject_id=subject_id, grade_id=grade_id).values('id', 'name')
        topic_list = [{'id': t['id'], 'name': t['name']} for t in topics]

        if not topic_list:
            return JsonResponse({'error': 'No topics found for this subject and grade combination'}, status=400)

        import os
        import re
        import requests
        from .ai_tagging_improved import ImageTextExtractor, ContextAwarePromptBuilder
        from django.conf import settings as _dj_settings
        lmstudio_url = getattr(_dj_settings, 'LMSTUDIO_URL', 'http://127.0.0.1:1234/v1/chat/completions')

        # ── Build question context from the DB image (not the mark scheme) ──
        image_text = ''
        question_content = question_text  # fallback to whatever the frontend sent

        if question_id:
            try:
                q = Question.objects.get(id=question_id)

                # 1) Try QuestionPage images (QP-MS ingested questions)
                pages = QuestionPage.objects.filter(question=q).order_by('page_number')
                if pages.exists():
                    for p in pages:
                        if p.page_image:
                            extracted = ImageTextExtractor.extract_from_base64(p.page_image)
                            if extracted:
                                image_text += ' ' + extracted
                    print(f"[AI] OCR from {pages.count()} page(s): {len(image_text)} chars")

                # 2) Try base64 image in question_text field
                elif q.question_text and ('base64' in q.question_text):
                    image_text = ImageTextExtractor.extract_from_html(q.question_text)
                    print(f"[AI] OCR from question_text image: {len(image_text)} chars")

                # 3) Use plain question_text if it's not just an image tag
                elif q.question_text and not q.question_text.strip().startswith('<img'):
                    question_content = q.question_text
                    print(f"[AI] Using plain question_text: {len(question_content)} chars")

                # Also include mark scheme as supplementary context
                if q.answer_text:
                    question_content = f"Mark scheme: {q.answer_text}\n{question_content}"

            except Question.DoesNotExist:
                pass

        if not question_content.strip() and not image_text:
            return JsonResponse({'error': 'No question content or image found to analyze'}, status=400)

        # Build context-aware prompt
        prompt_text, clean_text = ContextAwarePromptBuilder.build_topic_prompt(
            question_content, image_text, subject_name, grade_name, topic_list
        )
        print(f"[AI] Prompt length: {len(prompt_text)} chars, OCR text: {len(image_text)} chars")

        # Priority 1: LMStudio (primary service)
        suggested_topic_id = None
        used_service = None
        error_details = {}
        lmstudio_reachable = False  # True once we get any HTTP response back

        try:
            lmstudio_model = _get_lmstudio_model(lmstudio_url)
            print(f"[LMStudio] using model: {lmstudio_model}")
            response = requests.post(
                lmstudio_url,
                json={
                    "model": lmstudio_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an educational content classifier. "
                                f"The user will show you a question and a numbered list of {len(topic_list)} topics. "
                                "Reply with ONLY the single integer that matches best. No words, no explanation."
                            )
                        },
                        {
                            "role": "user",
                            "content": prompt_text
                        }
                    ],
                    "temperature": 0.0,
                    "max_tokens": 256
                },
                timeout=60
            )

            print(f"[LMStudio] HTTP {response.status_code}")

            if response.status_code == 200:
                response_data = response.json()
                msg = response_data['choices'][0]['message']
                # Reasoning models put output in 'reasoning' first, then 'content'
                response_text = (msg.get('content') or '').strip()
                reasoning_text = (msg.get('reasoning') or '').strip()
                print(f"[LMStudio] content: {repr(response_text)}")
                print(f"[LMStudio] reasoning: {repr(reasoning_text[:200])}")
                # Try content first, fall back to reasoning field
                parse_text = response_text or reasoning_text
                match = re.search(r'\d+', parse_text)
                if match:
                    topic_number = int(match.group())
                    print(f"[LMStudio] parsed topic number: {topic_number} (list has {len(topic_list)} topics)")
                    if 0 < topic_number <= len(topic_list):
                        suggested_topic_id = topic_list[topic_number - 1]['id']
                        suggested_topic_name = topic_list[topic_number - 1]['name']
                        used_service = f'LMStudio ({lmstudio_model})'
                    else:
                        error_details['lmstudio'] = f'Number {topic_number} out of range (1–{len(topic_list)})'
                else:
                    error_details['lmstudio'] = f'No digit in content or reasoning: {repr(parse_text[:120])}'
            else:
                error_details['lmstudio'] = f"HTTP {response.status_code}: {response.text[:120]}"

        except requests.exceptions.ConnectionError as e:
            error_details['lmstudio'] = 'Connection refused - LMStudio not running'
            print(f"[LMStudio] ConnectionError: {e}")
        except requests.exceptions.Timeout:
            error_details['lmstudio'] = 'Timeout after 45s'
            print(f"[LMStudio] Timeout")
        except Exception as e:
            error_details['lmstudio'] = str(e)
            print(f"[LMStudio] exception: {e}")

        # Always stop after LMStudio — never fall through to external paid APIs.
        if not suggested_topic_id:
            return JsonResponse({
                'error': f"LMStudio: {error_details.get('lmstudio', 'unknown error')}",
                'details': error_details
            }, status=500)

        # (Gemini / Anthropic fallbacks disabled — LMStudio is the sole service)
        # Priority 2: Fallback to Google Gemini (works with OCR-extracted text)
        if not suggested_topic_id and google_api_key:
            try:
                google_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={google_api_key}"

                response = requests.post(
                    google_url,
                    json={
                        "contents": [{
                            "parts": [{
                                "text": prompt_text
                            }]
                        }]
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    response_data = response.json()
                    response_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
                    topic_number = int(re.search(r'\d+', response_text).group())

                    if 0 < topic_number <= len(topic_list):
                        suggested_topic_id = topic_list[topic_number - 1]['id']
                        suggested_topic_name = topic_list[topic_number - 1]['name']
                        used_service = 'Google Gemini'
                else:
                    error_details['gemini'] = f"HTTP {response.status_code}"
                    if response.status_code == 429:
                        error_details['gemini'] = 'Rate limited - too many requests'
                    elif response.status_code == 400:
                        try:
                            error_msg = response.json().get('error', {}).get('message', '')
                            error_details['gemini'] = f"Bad request: {error_msg[:100]}"
                        except:
                            error_details['gemini'] = 'Bad request'

            except Exception as e:
                error_details['gemini'] = str(e)
                print(f"Google Gemini failed: {str(e)}")

        # Priority 3: Fallback to Anthropic with native image support
        if not suggested_topic_id and api_key and has_image:
            try:
                client = anthropic.Anthropic(api_key=api_key)

                # Extract base64 image
                img_match = re.search(r'data:image/(png|jpeg|jpg);base64,([^"]+)', question_text)
                if img_match:
                    image_type = img_match.group(1)
                    base64_data = img_match.group(2)

                    message = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=200,
                        messages=[{
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": f"image/{image_type}",
                                        "data": base64_data,
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt_text
                                }
                            ]
                        }]
                    )

                    response_text = message.content[0].text.strip()
                    topic_number = int(re.search(r'\d+', response_text).group())

                    if 0 < topic_number <= len(topic_list):
                        suggested_topic_id = topic_list[topic_number - 1]['id']
                        suggested_topic_name = topic_list[topic_number - 1]['name']
                        used_service = 'Anthropic (with image)'

            except Exception as e:
                print(f"Anthropic API failed: {str(e)}")

        # Priority 4: Fallback to Anthropic for text-only
        if not suggested_topic_id and api_key:
            try:
                client = anthropic.Anthropic(api_key=api_key)

                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=200,
                    messages=[{
                        "role": "user",
                        "content": prompt_text
                    }]
                )

                response_text = message.content[0].text.strip()
                topic_number = int(re.search(r'\d+', response_text).group())

                if 0 < topic_number <= len(topic_list):
                    suggested_topic_id = topic_list[topic_number - 1]['id']
                    suggested_topic_name = topic_list[topic_number - 1]['name']
                    used_service = 'Anthropic'

            except Exception as e:
                print(f"Anthropic API failed: {str(e)}")

        # Return result or error
        if suggested_topic_id:
            response_data = {
                'success': True,
                'topic_id': suggested_topic_id,
                'topic_name': suggested_topic_name
            }
            if image_text:
                response_data['ocr_extracted'] = f"Extracted {len(image_text)} characters from image"
            elif has_image:
                response_data['ocr_note'] = 'OCR not available - install pytesseract for image text extraction'
            if used_service:
                response_data['service'] = used_service
            return JsonResponse(response_data)
        else:
            # Build detailed error message with specific failure reasons
            error_parts = ['All AI services failed.']

            if has_image and not image_text:
                error_parts.append('⚠️ OCR unavailable (install: pip install pytesseract) - image text not extracted.')

            # Show specific service errors
            if error_details:
                service_errors = []
                if 'lmstudio' in error_details:
                    service_errors.append(f"LMStudio: {error_details['lmstudio']}")
                if 'gemini' in error_details:
                    service_errors.append(f"Gemini: {error_details['gemini']}")
                if 'anthropic' in error_details:
                    service_errors.append(f"Anthropic: {error_details['anthropic']}")

                if service_errors:
                    error_parts.append('Errors: ' + '; '.join(service_errors))

            # Provide actionable solutions
            solutions = []
            if 'lmstudio' in error_details and 'Connection refused' in error_details['lmstudio']:
                solutions.append('Start LMStudio at http://localhost:1234')
            if 'gemini' in error_details and ('Rate limited' in error_details.get('gemini', '') or 'Bad request' in error_details.get('gemini', '')):
                solutions.append('Check Google API key or wait for rate limit reset')
            if not api_key:
                solutions.append('Set ANTHROPIC_API_KEY for fallback')

            if solutions:
                error_parts.append('Solutions: ' + '; '.join(solutions))

            return JsonResponse({
                'error': ' '.join(error_parts),
                'details': error_details
            }, status=500)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@staff_member_required
def ai_suggest_learning_objectives(request):
    """AI-powered learning objective suggestion with context-aware prompting and OCR"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        question_text = data.get('question_text', '')   # mark scheme / answer text
        question_id = data.get('question_id')           # DB question id
        topic_id = data.get('topic_id')

        if not topic_id:
            return JsonResponse({'error': 'Missing required fields (topic)'}, status=400)

        # Get topic details with subject and grade for context
        topic = get_object_or_404(Topic, id=topic_id)
        subject_name = topic.subject.name
        grade_name = topic.grade.name
        topic_name = topic.name

        # Get all learning objectives for this topic
        los = LearningObjective.objects.filter(topic_id=topic_id).values('id', 'code', 'description')
        lo_list = [{'id': lo['id'], 'code': lo['code'], 'description': lo['description']} for lo in los]

        if not lo_list:
            return JsonResponse({'error': 'No learning objectives found for this topic'}, status=400)

        import os
        import re
        import requests
        from .models import QuestionPage
        from .ai_tagging_improved import ImageTextExtractor, ContextAwarePromptBuilder
        from django.conf import settings as _dj_settings
        lmstudio_url = getattr(_dj_settings, 'LMSTUDIO_URL', 'http://127.0.0.1:1234/v1/chat/completions')

        # ── Build question context from the DB image ────────────────────
        image_text = ''
        question_content = question_text  # fallback

        if question_id:
            try:
                q = Question.objects.get(id=question_id)

                # 1) Try QuestionPage images
                pages = QuestionPage.objects.filter(question=q).order_by('page_number')
                if pages.exists():
                    for p in pages:
                        if p.page_image:
                            extracted = ImageTextExtractor.extract_from_base64(p.page_image)
                            if extracted:
                                image_text += ' ' + extracted
                    print(f"[AI-LO] OCR from {pages.count()} page(s): {len(image_text)} chars")

                # 2) Try base64 image in question_text
                elif q.question_text and ('base64' in q.question_text):
                    image_text = ImageTextExtractor.extract_from_html(q.question_text)
                    print(f"[AI-LO] OCR from question_text image: {len(image_text)} chars")

                # 3) Plain text question
                elif q.question_text and not q.question_text.strip().startswith('<img'):
                    question_content = q.question_text
                    print(f"[AI-LO] Using plain question_text: {len(question_content)} chars")

                if q.answer_text:
                    question_content = f"Mark scheme: {q.answer_text}\n{question_content}"

            except Question.DoesNotExist:
                pass

        if not question_content.strip() and not image_text:
            return JsonResponse({'error': 'No question content or image found to analyze'}, status=400)

        # Build context-aware prompt for LO selection
        prompt_text, clean_text = ContextAwarePromptBuilder.build_lo_prompt(
            question_content, image_text, subject_name, grade_name, topic_name, lo_list
        )
        print(f"[AI-LO] Prompt length: {len(prompt_text)} chars, OCR text: {len(image_text)} chars")

        # Primary service: LMStudio
        suggested_los = []
        used_service = None
        lmstudio_error = None

        try:
            lmstudio_model = _get_lmstudio_model(lmstudio_url)
            print(f"[LMStudio] using model: {lmstudio_model}")
            response = requests.post(
                lmstudio_url,
                json={
                    "model": lmstudio_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an educational content classifier. "
                                f"The user will show you a question and a numbered list of {len(lo_list)} learning objectives. "
                                "Reply with ONLY the comma-separated integers that match best. No words, no explanation."
                            )
                        },
                        {
                            "role": "user",
                            "content": prompt_text
                        }
                    ],
                    "temperature": 0.0,
                    "max_tokens": 256
                },
                timeout=60
            )

            print(f"[LMStudio] HTTP {response.status_code}")

            if response.status_code == 200:
                response_data = response.json()
                msg = response_data['choices'][0]['message']
                response_text = (msg.get('content') or '').strip()
                reasoning_text = (msg.get('reasoning') or '').strip()
                print(f"[LMStudio] content: {repr(response_text)}")
                print(f"[LMStudio] reasoning: {repr(reasoning_text[:200])}")
                parse_text = response_text or reasoning_text
                lo_numbers = [int(n) for n in re.findall(r'\d+', parse_text)]
                print(f"[LMStudio] parsed LO numbers: {lo_numbers} (list has {len(lo_list)} items)")
                suggested_los = [lo_list[n - 1] for n in lo_numbers if 0 < n <= len(lo_list)]
                if suggested_los:
                    used_service = f'LMStudio ({lmstudio_model})'
                else:
                    lmstudio_error = f'No valid LO numbers in content or reasoning: {repr(parse_text[:120])}'
            else:
                lmstudio_error = f"HTTP {response.status_code}: {response.text[:120]}"

        except requests.exceptions.ConnectionError as e:
            lmstudio_error = 'Connection refused - LMStudio not running'
            print(f"[LMStudio] ConnectionError: {e}")
        except requests.exceptions.Timeout:
            lmstudio_error = 'Timeout after 30s'
            print(f"[LMStudio] Timeout")
        except Exception as e:
            lmstudio_error = str(e)
            print(f"[LMStudio] exception: {e}")

        # Always stop after LMStudio — never fall through to external paid APIs.
        if not suggested_los:
            return JsonResponse({
                'error': f"LMStudio: {lmstudio_error or 'unknown error'}",
                'details': {'lmstudio': lmstudio_error}
            }, status=500)

        # (Gemini / Anthropic fallbacks disabled — LMStudio is the sole service)
        # Priority 2: Fallback to Google Gemini (works with OCR-extracted text)
        if not suggested_los and google_api_key:
            try:
                google_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={google_api_key}"

                response = requests.post(
                    google_url,
                    json={
                        "contents": [{
                            "parts": [{
                                "text": prompt_text
                            }]
                        }]
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    response_data = response.json()
                    response_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
                    lo_numbers = [int(n.strip()) for n in re.findall(r'\d+', response_text)]
                    suggested_los = [lo_list[n - 1] for n in lo_numbers if 0 < n <= len(lo_list)]
                    if suggested_los:
                        used_service = 'Google Gemini'

            except Exception as e:
                print(f"Google Gemini failed: {str(e)}")

        # Priority 3: Fallback to Anthropic
        if not suggested_los and api_key:
            try:
                client = anthropic.Anthropic(api_key=api_key)

                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=300,
                    messages=[{
                        "role": "user",
                        "content": prompt_text
                    }]
                )

                response_text = message.content[0].text.strip()
                lo_numbers = [int(n.strip()) for n in re.findall(r'\d+', response_text)]
                suggested_los = [lo_list[n - 1] for n in lo_numbers if 0 < n <= len(lo_list)]
                if suggested_los:
                    used_service = 'Anthropic'

            except Exception as e:
                print(f"Anthropic API failed: {str(e)}")

        # Return result or error
        if suggested_los:
            response_data = {
                'success': True,
                'learning_objectives': suggested_los
            }
            if image_text:
                response_data['ocr_extracted'] = f"Extracted {len(image_text)} characters from image"
            if used_service:
                response_data['service'] = used_service
            return JsonResponse(response_data)
        else:
            detail = lmstudio_error or 'No response from any service'
            return JsonResponse({
                'error': f'All AI services failed. LMStudio: {detail}',
                'details': {'lmstudio': lmstudio_error}
            }, status=500)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@staff_member_required
def bulk_ai_tag_questions(request):
    """
    Bulk AI tagging that EXACTLY emulates pressing the AI buttons
    in the Edit Question page.
    """

    from django.http import StreamingHttpResponse
    from django.db.models import Count
    from django.test import RequestFactory
    import json
    import time

    factory = RequestFactory()

    def event_stream():
        try:
            qs = (
                Question.objects
                .annotate(lo_count=Count("learning_objectives"))
                .filter(
                    Q(topic__isnull=True) | Q(lo_count=0)
                )
                .select_related("grade", "subject", "topic")
                .distinct()
            )

            total = qs.count()
            processed = 0

            yield f"data: {json.dumps({'status': 'started', 'total': total})}\n\n"

            for question in qs:
                log = {
                    "question_id": question.id,
                    "topic": None,
                    "learning_objectives": []
                }

                try:
                    # ---------------- TOPIC ----------------
                    question.refresh_from_db(fields=["topic"])

                    if question.topic_id is None:
                        payload = {
                            "question_text": question.question_text,
                            "subject_id": question.subject_id,
                            "grade_id": question.grade_id,
                        }

                        fake_request = factory.post(
                            "/ai/suggest-topic/",
                            data=json.dumps(payload),
                            content_type="application/json",
                        )
                        fake_request.user = request.user

                        response = ai_suggest_topic(fake_request)
                        data = json.loads(response.content)

                        if data.get("success"):
                            question.topic_id = data["topic_id"]
                            question.save(update_fields=["topic"])
                            log["topic"] = data["topic_name"]

                    # ---------------- LOS ----------------
                    question.refresh_from_db(fields=["topic"])

                    if question.topic_id and question.learning_objectives.count() == 0:
                        payload = {
                            "question_text": question.question_text,
                            "topic_id": question.topic_id,
                        }

                        fake_request = factory.post(
                            "/ai/suggest-los/",
                            data=json.dumps(payload),
                            content_type="application/json",
                        )
                        fake_request.user = request.user

                        response = ai_suggest_learning_objectives(fake_request)
                        data = json.loads(response.content)

                        if data.get("success"):
                            lo_ids = [lo["id"] for lo in data["learning_objectives"]]
                            question.learning_objectives.set(lo_ids)
                            log["learning_objectives"] = [
                                lo["code"] for lo in data["learning_objectives"]
                            ]

                    processed += 1

                    payload = {
                        "progress": processed,
                        "total": total,
                        "log": log,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                    time.sleep(0.2)

                except Exception as e:
                    processed += 1

                    payload = {
                        "progress": processed,
                        "total": total,
                        "error": f"Q{question.id}: {str(e)}"
                    }

                    yield f"data: {json.dumps(payload)}\n\n"


            yield f"data: {json.dumps({'complete': True, 'total': total})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'fatal_error': str(e)})}\n\n"

    return StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream"
    )



# ===================== UNTAGGED QUESTIONS & BACKGROUND TAGGING =====================

@login_required
@staff_member_required
def untagged_questions_view(request):
    """
    Display questions missing topic and/or learning objectives
    (ORM-safe, no ghost data)
    """
    from django.db.models import Count

    # Base queryset with safe annotation
    qs = (
        Question.objects
        .annotate(lo_count=Count("learning_objectives"))
        .filter(
            Q(topic__isnull=True) | Q(lo_count=0)
        )
        .select_related("grade", "subject", "topic")
        .prefetch_related("learning_objectives")
        .distinct()
    )

    # School filtering
    if not request.user.is_superuser:
        try:
            user_school = request.user.userprofile.school
            qs = qs.filter(created_by__userprofile__school=user_school)
        except (AttributeError, UserProfile.DoesNotExist):
            qs = qs.filter(created_by=request.user)

    # Statistics (ALL derived from the SAME annotated queryset)
    total_untagged = qs.count()
    missing_topics = qs.filter(topic__isnull=True).count()
    missing_los = qs.filter(lo_count=0).count()

    context = {
        "questions": qs,
        "total_untagged": total_untagged,
        "missing_topics": missing_topics,
        "missing_los": missing_los,
    }

    return render(request, "teacher/untagged_questions.html", context)



@login_required
@staff_member_required
def start_background_tagging(request):
    """
    Start a background AI tagging task with a clean, correct queryset
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        from django.db.models import Count
        from .background_tagging import create_tagging_task

        data = json.loads(request.body)
        mode = data.get("mode", "both")  # 'topics', 'los', 'both'

        if mode not in ["topics", "los", "both"]:
            return JsonResponse({"error": "Invalid mode"}, status=400)

        # ORM-safe untagged queryset
        qs = (
            Question.objects
            .annotate(lo_count=Count("learning_objectives"))
            .filter(
                Q(topic__isnull=True) | Q(lo_count=0)
            )
            .select_related("grade", "subject", "topic")
            .distinct()
        )

        # School filtering
        if not request.user.is_superuser:
            try:
                user_school = request.user.userprofile.school
                qs = qs.filter(created_by__userprofile__school=user_school)
            except (AttributeError, UserProfile.DoesNotExist):
                qs = qs.filter(created_by=request.user)

        if not qs.exists():
            return JsonResponse(
                {"error": "No untagged questions found"},
                status=400
            )

        # Start background task
        task = create_tagging_task(mode, qs)

        return JsonResponse({
            "success": True,
            "task_id": task.task_id,
            "total_questions": task.total,
            "mode": mode,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
@staff_member_required
def get_tagging_progress(request, task_id):
    """
    Get progress for a background tagging task
    """
    from .background_tagging import get_task_status

    task_status = get_task_status(task_id)

    if task_status is None:
        return JsonResponse(
            {"error": "Task not found"},
            status=404
        )

    return JsonResponse(task_status)

@login_required
@staff_member_required
def mcq_examiner_report(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    from core.analytics.mcq_signals import compute_mcq_signals
    from core.analytics.examiner_schema import build_examiner_schema
    from core.analytics.examiner_ai import generate_examiner_report

    if not test.student_answers.exists():
        return JsonResponse({
            "examiner_report": "No candidate response data is available for this test.",
            "structured_data": {
                "question_analysis": [],
                "learning_objective_analysis": []
            }
        })

    signals = compute_mcq_signals(test)
    schema = build_examiner_schema(test, signals)
    narrative = generate_examiner_report(schema)

    return JsonResponse({
        "examiner_report": narrative,
        "structured_data": schema
    })

from django.shortcuts import render, get_object_or_404
from collections import defaultdict
from decimal import Decimal
import statistics
import math

from core.models import Test, StudentAnswer
from django.db.models import Avg, Count, Sum


def test_analytics_view(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    # ─────────────────────────────────────────────
    # 1. Pull all evaluated answers safely
    # ─────────────────────────────────────────────
    answers = (
        StudentAnswer.objects
        .select_related("student", "question", "question__topic")
        .filter(test=test, marks_awarded__isnull=False)
    )
    
    

    if not answers.exists():
        return render(request, "analytics_dashboard.html", {
            "test": test,
            "error": "No evaluated student responses available for this test."
        })

    # ─────────────────────────────────────────────
    # 2. Student-level aggregation
    # ─────────────────────────────────────────────
    student_map = {}
    total_test_marks = float(
        test.questions.aggregate(total=Sum("marks"))["total"] or 0
    )

    for a in answers:
        sid = a.student_id
        student_map.setdefault(sid, {
            "id": sid,
            "name": a.student.full_name,
            "grade": a.student.grade.name if a.student.grade else "",
            "section": a.student.section or "",
            "earned": 0.0,
            "max": 0.0,
            "answered": 0,
        })

        student_map[sid]["earned"] += float(a.marks_awarded)
        student_map[sid]["max"] += float(a.question.marks)
        student_map[sid]["answered"] += 1

    students = []
    scores = []

    for s in student_map.values():
        percent = round((s["earned"] / total_test_marks) * 100, 2) if total_test_marks else 0.0
        scores.append(percent)

        # rule-based risk
        if percent < 40:
            risk = "high"
        elif percent < 60:
            risk = "medium"
        else:
            risk = "low"

        students.append({
            "id": s["id"],
            "name": s["name"],
            "grade": s["grade"],
            "section": s["section"],
            "score": percent,
            "risk": risk,
            "completion": {
                "answered": s["answered"],
                "total": test.questions.count(),
                "complete": s["answered"] == test.questions.count(),
            }
        })

    students.sort(key=lambda x: x["score"], reverse=True)

    # ─────────────────────────────────────────────
    # 3. Cohort distribution & statistics
    # ─────────────────────────────────────────────
    mean = statistics.mean(scores)
    std = statistics.stdev(scores) if len(scores) > 1 else 0.0

    def histogram(values):
        bins = [0] * 10
        for v in values:
            idx = min(9, int(v // 10))
            bins[idx] += 1
        return bins

    def gaussian_curve(mu, sigma, n):
        curve_x = list(range(0, 101, 2))
        curve_y = []
        if sigma == 0:
            curve_y = [0 for _ in curve_x]
        else:
            for x in curve_x:
                pdf = (1 / (sigma * math.sqrt(2 * math.pi))) * math.exp(
                    -0.5 * ((x - mu) / sigma) ** 2
                )
                curve_y.append(pdf * n * 10)
        return curve_x, curve_y

    curve_x, curve_y = gaussian_curve(mean, std, len(scores))

    # ─────────────────────────────────────────────
    # 4. Question-level analytics
    # ─────────────────────────────────────────────
    question_stats = []
    questions = test.questions.all().select_related("topic")

    for idx, q in enumerate(questions, 1):
        q_answers = answers.filter(question=q)
        attempts = q_answers.count()

        if attempts == 0:
            continue

        correct = q_answers.filter(
            marks_awarded__gte=float(q.marks) * 0.5
        ).count()

        success_rate = round((correct / attempts) * 100, 1)

        # Time analytics per question
        q_times = [a.time_spent_seconds for a in q_answers if a.time_spent_seconds is not None]
        avg_time = round(sum(q_times) / len(q_times), 1) if q_times else None
        min_time = min(q_times) if q_times else None
        max_time = max(q_times) if q_times else None

        question_stats.append({
            "id": q.id,
            "number": idx,
            "topic": q.topic.name if q.topic else "",
            "marks": float(q.marks),
            "attempts": attempts,
            "success_rate": success_rate,
            "type": q.question_type,
            "difficulty": (
                "easy" if success_rate >= 75 else
                "medium" if success_rate >= 50 else
                "hard"
            ),
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
        })

    # ─────────────────────────────────────────────
    # 4b. Time Analytics
    # ─────────────────────────────────────────────
    all_timed_answers = [
        (a.time_spent_seconds, float(a.marks_awarded), float(a.question.marks))
        for a in answers if a.time_spent_seconds is not None
    ]

    if all_timed_answers:
        all_times_raw = [t[0] for t in all_timed_answers]
        avg_time_overall = round(sum(all_times_raw) / len(all_times_raw), 1)
        sorted_times = sorted(all_times_raw)
        median_time = sorted_times[len(sorted_times) // 2]

        # Per-student total time
        student_times = {}
        for a in answers:
            if a.time_spent_seconds is not None:
                sid = a.student_id
                student_times.setdefault(sid, 0)
                student_times[sid] += a.time_spent_seconds

        avg_total_time = round(sum(student_times.values()) / len(student_times), 1) if student_times else 0

        # Time vs accuracy correlation (Pearson) across all timed answers
        times_list = [t[0] for t in all_timed_answers]
        accuracy_list = [round((t[1] / t[2]) * 100, 1) if t[2] > 0 else 0 for t in all_timed_answers]

        correlation = 0
        if len(times_list) > 2:
            n = len(times_list)
            mean_t = sum(times_list) / n
            mean_a = sum(accuracy_list) / n
            numerator = sum((t - mean_t) * (a - mean_a) for t, a in zip(times_list, accuracy_list))
            denom_t = (sum((t - mean_t) ** 2 for t in times_list)) ** 0.5
            denom_a = (sum((a - mean_a) ** 2 for a in accuracy_list)) ** 0.5
            correlation = round(numerator / (denom_t * denom_a), 3) if (denom_t * denom_a) > 0 else 0

        # Compute overall expected time per mark for flagging
        total_marks_timed = sum(t[2] for t in all_timed_answers)
        total_time_timed = sum(t[0] for t in all_timed_answers)
        time_per_mark = total_time_timed / total_marks_timed if total_marks_timed > 0 else 0

        for qs in question_stats:
            if qs["avg_time"] is not None:
                expected_time = time_per_mark * qs["marks"]
                time_ratio = qs["avg_time"] / expected_time if expected_time > 0 else 1

                if time_ratio < 0.6 and qs["success_rate"] < 50:
                    qs["time_flag"] = "rushed"
                elif time_ratio > 1.5 and qs["success_rate"] < 50:
                    qs["time_flag"] = "overthought"
                elif time_ratio > 1.5 and qs["success_rate"] >= 50:
                    qs["time_flag"] = "challenging"
                else:
                    qs["time_flag"] = "normal"
            else:
                qs["time_flag"] = "no_data"

        # Per-student time vs score for scatter chart
        student_time_score = []
        for sid, total_t in student_times.items():
            for s in students:
                if s["id"] == sid:
                    student_time_score.append({
                        "name": s["name"],
                        "time": round(total_t / 60, 1),  # minutes
                        "score": s["score"],
                    })
                    break

        time_analytics = {
            "has_data": True,
            "avg_time_per_question": avg_time_overall,
            "median_time_per_question": median_time,
            "avg_total_time_per_student": avg_total_time,
            "avg_total_time_minutes": round(avg_total_time / 60, 1),
            "time_accuracy_correlation": correlation,
            "time_per_mark": round(time_per_mark, 1),
            "student_time_score": student_time_score,
            "total_timed_answers": len(all_timed_answers),
        }
    else:
        time_analytics = {"has_data": False}
        for qs in question_stats:
            qs["time_flag"] = "no_data"

    # ─────────────────────────────────────────────
    # 5. Topic / LO mastery
    # ─────────────────────────────────────────────
    topic_map = defaultdict(lambda: {"earned": 0.0, "max": 0.0})

    for a in answers:
        topic = a.question.topic
        topic_map[topic]["earned"] += float(a.marks_awarded)
        topic_map[topic]["max"] += float(a.question.marks)

    learning_objectives = []
    for topic, d in topic_map.items():
        mastery = round((d["earned"] / d["max"]) * 100, 1) if d["max"] else 0.0

        band = (
            "mastered" if mastery >= 80 else
            "developing" if mastery >= 65 else
            "weak"
        )

        learning_objectives.append({
            "name": topic.name,
            "avg_mastery": mastery,
            "band": band,
            "question_count": test.questions.filter(topic=topic).count()
        })

    # ─────────────────────────────────────────────
    # 6. Assessment Quality Radar - REAL DATA
    # ─────────────────────────────────────────────
    # Six meaningful metrics for assessment quality

    # 1. Question Variety (0-100): Based on question type distribution
    question_types = {'mcq': 0, 'theory': 0, 'structured': 0, 'practical': 0}
    for q in question_stats:
        qtype = q.get('type', 'mcq')
        if qtype in question_types:
            question_types[qtype] += 1

    # Calculate variety score (more uniform = better)
    total_q = sum(question_types.values()) or 1
    type_percentages = [v/total_q for v in question_types.values() if v > 0]
    variety_score = (len(type_percentages) / 4.0) * 100  # Max 100% if all 4 types used

    # 2. Difficulty Balance (0-100): How balanced easy/medium/hard questions are
    difficulty_dist = {'easy': 0, 'medium': 0, 'hard': 0}
    for q in question_stats:
        difficulty_dist[q['difficulty']] += 1

    # Ideal is 20% easy, 60% medium, 20% hard
    ideal = {'easy': 0.2, 'medium': 0.6, 'hard': 0.2}
    total_q = sum(difficulty_dist.values()) or 1
    balance_score = 100 - sum([abs((difficulty_dist[k]/total_q) - ideal[k]) for k in ideal]) * 100
    balance_score = max(0, balance_score)

    # 3. Discrimination Power (0-100): How well test separates high/low performers
    # Top 27% vs Bottom 27% - classic item discrimination
    sorted_students = sorted(students, key=lambda x: x['score'], reverse=True)
    n_group = max(1, int(len(sorted_students) * 0.27))
    top_group = sorted_students[:n_group]
    bottom_group = sorted_students[-n_group:]

    if top_group and bottom_group:
        avg_top = sum(s['score'] for s in top_group) / len(top_group)
        avg_bottom = sum(s['score'] for s in bottom_group) / len(bottom_group)
        discrimination_score = min(100, (avg_top - avg_bottom))  # Difference as percentage
    else:
        discrimination_score = 0

    # 4. Coverage Breadth (0-100): Topic coverage across test
    unique_topics = set()
    for q in questions:
        if q.topic:
            unique_topics.add(q.topic.name)

    # Assume 5+ unique topics is excellent coverage
    coverage_score = min(100, (len(unique_topics) / 5.0) * 100)

    # 5. Reliability Indicator (0-100): Based on std dev (lower std = more reliable)
    # Ideal std is around 15-20 for a well-constructed test
    if std > 0:
        reliability_score = max(0, 100 - abs(std - 17.5) * 3)  # Penalize deviation from ideal
    else:
        reliability_score = 0

    # 6. Performance Level (0-100): Overall cohort performance
    performance_score = mean  # Already a percentage

    # Compile radar data
    assessment_quality_radar = [
        round(variety_score, 1),
        round(balance_score, 1),
        round(discrimination_score, 1),
        round(coverage_score, 1),
        round(reliability_score, 1),
        round(performance_score, 1)
    ]

    # ─────────────────────────────────────────────
    # 7. LO Competency Matrix - REAL DATA
    # ─────────────────────────────────────────────
    # Build per-student, per-LO performance matrix
    lo_matrix = {}  # {student_id: {lo_name: {earned, max}}}

    for a in answers:
        sid = a.student_id

        # Get all LOs for this question (using topic as proxy for now)
        # In future, use a.question.learning_objectives.all() if properly tagged
        lo_name = a.question.topic.name if a.question.topic else "Uncategorized"

        if sid not in lo_matrix:
            lo_matrix[sid] = {}
        if lo_name not in lo_matrix[sid]:
            lo_matrix[sid][lo_name] = {"earned": 0.0, "max": 0.0}

        lo_matrix[sid][lo_name]["earned"] += float(a.marks_awarded)
        lo_matrix[sid][lo_name]["max"] += float(a.question.marks)

    # Add LO performance to each student
    for s in students:
        s["lo_performance"] = {}
        for lo in learning_objectives:
            lo_name = lo["name"]
            if s["id"] in lo_matrix and lo_name in lo_matrix[s["id"]]:
                data = lo_matrix[s["id"]][lo_name]
                percentage = (data["earned"] / data["max"]) * 100 if data["max"] > 0 else 0
                s["lo_performance"][lo_name] = round(percentage, 1)
            else:
                s["lo_performance"][lo_name] = None  # No questions for this LO

    # ─────────────────────────────────────────────
    # 8. Differentiated Groups - REAL DATA
    # ─────────────────────────────────────────────
    extension_threshold = 80  # Top performers
    intervention_threshold = 50  # Needs support

    extension_group = [s for s in students if s["score"] >= extension_threshold]
    intervention_group = [s for s in students if s["score"] < intervention_threshold]

    # Identify common weak LO for intervention group
    weak_los = [lo["name"] for lo in learning_objectives if lo["band"] == "weak"]
    primary_weak_lo = weak_los[0] if weak_los else "fundamental concepts"

    differentiated_groups = {
        "extension": {
            "count": len(extension_group),
            "students": [s["name"] for s in extension_group[:5]],  # First 5 names
        },
        "intervention": {
            "count": len(intervention_group),
            "students": [s["name"] for s in intervention_group[:5]],
            "focus_area": primary_weak_lo
        }
    }

    # ─────────────────────────────────────────────
    # 9. Examiner-style narrative (rule-based)
    # ─────────────────────────────────────────────
    overview = (
        "Overall performance was strong."
        if mean >= 70 else
        "Overall performance was moderate."
        if mean >= 50 else
        "Overall performance was below expectations."
    )

    examiner_report = {
        "overview": overview,
        "strengths": [
            lo["name"] for lo in learning_objectives if lo["band"] == "mastered"
        ],
        "weaknesses": [
            lo["name"] for lo in learning_objectives if lo["band"] == "weak"
        ],
        "recommendations": [
            "Reinforce weak learning objectives.",
            "Provide targeted practice for at-risk students.",
        ]
    }

    # ─────────────────────────────────────────────
    # FINAL CONTEXT
    # ─────────────────────────────────────────────
    # Completion rate
    total_students = len(students)
    completed_students = sum(1 for s in students if s["completion"]["complete"])
    completion_rate = round((completed_students / total_students) * 100, 1) if total_students else 0

    context = {
        "test": test,
        "analytics": {
            "students": students,
            "distribution": {
                "scores": scores,
                "histogram": histogram(scores),
                "mean": round(mean, 2),
                "median": round(statistics.median(scores), 2),
                "std_dev": round(std, 2),
                "curve": {"x": curve_x, "y": curve_y},
            },
            "questions": question_stats,
            "learning_objectives": learning_objectives,
            "assessment_quality_radar": assessment_quality_radar,
            "differentiated_groups": differentiated_groups,
            "examiner_report": examiner_report,
            "time_analytics": time_analytics,
            "summary": {
                "discrimination_index": round(discrimination_score / 100, 2),
                "completion_rate": completion_rate,
                "total_students": total_students,
                "completed_students": completed_students,
            },
        }
    }

    return render(request, "teacher/analytics_dashboard.html", context)


# ===================== QUESTION LIBRARY API =====================

@login_required
def question_library_api_search(request):
    """
    API endpoint to search questions in the library
    GET /questions/api/search/?subject_id=&grade_id=&topic_id=&q=
    """
    try:
        # Support both naming conventions: subject_id or subject, grade_id or grade
        subject_id = request.GET.get('subject_id') or request.GET.get('subject')
        grade_id = request.GET.get('grade_id') or request.GET.get('grade')
        topic_id = request.GET.get('topic_id') or request.GET.get('topic')
        search_query = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', 50))

        questions = Question.objects.all().order_by('-created_at')

        if subject_id:
            questions = questions.filter(subject_id=subject_id)
        if grade_id:
            questions = questions.filter(grade_id=grade_id)
        if topic_id:
            questions = questions.filter(topic_id=topic_id)
        if search_query:
            questions = questions.filter(question_text__icontains=search_query)

        questions = questions[:limit]

        results = []
        for q in questions:
            # Get topic name
            topic_name = q.topic.name if q.topic else 'No Topic'

            # Truncate question text for preview
            preview_text = q.question_text[:150] + '...' if len(q.question_text) > 150 else q.question_text

            results.append({
                'id': q.id,
                'question_text': q.question_text,
                'preview_text': preview_text,
                'answer_text': q.answer_text or '',
                'marks': q.marks,
                'question_type': q.question_type,
                'topic_name': topic_name,
                'topic_id': q.topic_id,
                'subject_id': q.subject_id,
                'grade_id': q.grade_id,
                'year': q.year,
                'parts_config': q.parts_config,
            })

        return JsonResponse({
            'success': True,
            'questions': results,
            'total': len(results)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def question_library_api_get(request, question_id):
    """
    API endpoint to get a single question by ID
    GET /questions/api/<id>/
    """
    try:
        question = get_object_or_404(Question, id=question_id)

        return JsonResponse({
            'success': True,
            'question': {
                'id': question.id,
                'question_text': question.question_text,
                'answer_text': question.answer_text or '',
                'marks': question.marks,
                'question_type': question.question_type,
                'topic_name': question.topic.name if question.topic else 'No Topic',
                'topic_id': question.topic_id,
                'subject_id': question.subject_id,
                'grade_id': question.grade_id,
                'year': question.year,
                'parts_config': question.parts_config,
            }
        })

    except Question.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Question not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def question_library_api_create(request):
    """
    API endpoint to create a new question in the library
    POST /questions/api/create/
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)

        # Required fields
        question_text = data.get('question_text', '').strip()
        if not question_text:
            return JsonResponse({'error': 'Question text is required'}, status=400)

        # Get subject and grade
        subject_id = data.get('subject_id')
        grade_id = data.get('grade_id')
        topic_id = data.get('topic_id')

        if not subject_id or not grade_id:
            return JsonResponse({'error': 'Subject and Grade are required'}, status=400)

        # Create the question
        question = Question.objects.create(
            question_text=question_text,
            answer_text=data.get('answer_text', ''),
            marks=int(data.get('marks', 1)),
            question_type=data.get('question_type', 'theory'),
            subject_id=subject_id,
            grade_id=grade_id,
            topic_id=topic_id if topic_id else None,
            year=data.get('year'),
            parts_config=data.get('parts_config'),
            created_by=request.user,
        )

        # Set learning objectives if provided
        los = data.get('los', [])
        if los:
            question.learning_objectives.set(los)

        return JsonResponse({
            'success': True,
            'question_id': question.id,
            'message': 'Question created successfully'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

