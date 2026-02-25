"""
Analytics Views for Student and Teacher Performance Dashboards
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import Student, ClassGroup, Grade, Subject
# Note: analytics.py file is shadowed by analytics/ package
# Commenting out for now - will create simplified version
#from .analytics import StudentAnalytics, ClassAnalytics
from .views import get_user_school, staff_member_required


@login_required
def student_analytics_dashboard(request):
    """
    Comprehensive yet concise analytics dashboard for students.
    Shows: key metrics, competence level, subject performance,
    top strengths/weaknesses, and recent test timeline.
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found")
        return redirect("student_dashboard")

    # Time range
    time_range = request.GET.get('range', '6m')
    range_map = {'1m': 30, '3m': 90, '6m': 180, '1y': 365}
    start_date = timezone.now() - timedelta(days=range_map.get(time_range, 180))
    end_date = timezone.now()

    from .models import StudentAnswer, Test, Topic
    import math
    from collections import defaultdict

    # Only include graded answers (marks_awarded is not null)
    # This prevents unattended/ungraded tests from appearing as 0%
    answers = StudentAnswer.objects.filter(
        student=student,
        test__created_at__gte=start_date,
        test__created_at__lte=end_date,
        marks_awarded__isnull=False,
    ).select_related('test', 'test__subject', 'question', 'question__topic')

    # ── Basic metrics ──
    test_ids = answers.values_list('test_id', flat=True).distinct()
    total_tests = len(set(test_ids))
    total_questions = answers.count()

    total_marks = sum(float(a.question.marks or 0) for a in answers)
    earned_marks = sum(float(a.marks_awarded or 0) for a in answers)
    average_score = (earned_marks / total_marks * 100) if total_marks > 0 else 0

    # ── Per-test results (for timeline) ──
    test_data = defaultdict(lambda: {'total': 0, 'earned': 0, 'subject': '', 'date': None, 'title': ''})
    for a in answers:
        tid = a.test_id
        test_data[tid]['total'] += float(a.question.marks or 0)
        test_data[tid]['earned'] += float(a.marks_awarded or 0)
        test_data[tid]['subject'] = a.test.subject.name if a.test.subject else 'General'
        test_data[tid]['date'] = a.test.created_at
        test_data[tid]['title'] = a.test.title

    recent_tests = []
    for tid, d in test_data.items():
        pct = (d['earned'] / d['total'] * 100) if d['total'] > 0 else 0
        recent_tests.append({
            'title': d['title'],
            'subject': d['subject'],
            'percentage': round(pct, 1),
            'date': d['date'].strftime('%d-%m-%Y') if d['date'] else '',
            'earned': round(d['earned'], 1),
            'total': round(d['total'], 1),
        })
    recent_tests.sort(key=lambda x: x['date'], reverse=True)

    # ── Subject performance ──
    subject_performance = []
    subject_map = defaultdict(lambda: {'total': 0, 'earned': 0, 'tests': set()})
    for a in answers:
        sid = a.test.subject_id if a.test.subject else None
        if not sid:
            continue
        subject_map[sid]['total'] += float(a.question.marks or 0)
        subject_map[sid]['earned'] += float(a.marks_awarded or 0)
        subject_map[sid]['tests'].add(a.test_id)

    for sid, d in subject_map.items():
        subj = Subject.objects.get(id=sid)
        pct = (d['earned'] / d['total'] * 100) if d['total'] > 0 else 0
        subject_performance.append({
            'name': subj.name,
            'score': round(pct, 1),
            'tests': len(d['tests']),
        })
    subject_performance.sort(key=lambda x: x['score'], reverse=True)

    # ── Topic mastery ──
    topic_map = defaultdict(lambda: {'total': 0, 'earned': 0, 'count': 0})
    for a in answers:
        t = a.question.topic
        if not t:
            continue
        topic_map[t.id]['total'] += float(a.question.marks or 0)
        topic_map[t.id]['earned'] += float(a.marks_awarded or 0)
        topic_map[t.id]['count'] += 1
        topic_map[t.id]['name'] = t.name
        topic_map[t.id]['subject'] = a.test.subject.name if a.test.subject else ''

    topic_mastery = []
    for tid, d in topic_map.items():
        pct = (d['earned'] / d['total'] * 100) if d['total'] > 0 else 0
        if pct >= 80:
            band = 'Mastered'
        elif pct >= 60:
            band = 'Good'
        elif pct >= 40:
            band = 'Developing'
        else:
            band = 'Weak'
        topic_mastery.append({
            'name': d['name'],
            'subject': d['subject'],
            'score': round(pct, 1),
            'band': band,
            'questions': d['count'],
        })
    topic_mastery.sort(key=lambda x: x['score'])

    # Strengths = top 3 mastered, Weaknesses = bottom 3
    strengths = [t for t in reversed(topic_mastery) if t['band'] in ('Mastered', 'Good')][:3]
    weaknesses = [t for t in topic_mastery if t['band'] in ('Weak', 'Developing')][:3]

    # ── Competence assessment ──
    competence = {'level': 'Not Assessed', 'score': 0}
    if recent_tests:
        avg_score = min(average_score / 100, 1.0)

        # Consistency
        percentages = [t['percentage'] for t in recent_tests]
        if len(percentages) > 1:
            mean_p = sum(percentages) / len(percentages)
            variance = sum((p - mean_p) ** 2 for p in percentages) / len(percentages)
            std_dev = math.sqrt(variance)
            consistency_score = max(0, 1.0 - (std_dev / 30.0))
        else:
            consistency_score = 0.5

        # Trend
        sorted_by_date = sorted(recent_tests, key=lambda t: t['date'])
        if len(sorted_by_date) >= 2:
            recent_half = sorted_by_date[len(sorted_by_date)//2:]
            older_half = sorted_by_date[:len(sorted_by_date)//2]
            recent_avg = sum(t['percentage'] for t in recent_half) / len(recent_half)
            older_avg = sum(t['percentage'] for t in older_half) / len(older_half)
            trend_diff = recent_avg - older_avg
            trend_score = max(0, min(1.0, 0.5 + (trend_diff / 20.0)))
        else:
            trend_score = 0.5
            trend_diff = 0

        # Mastery breadth
        if topic_mastery:
            mastered_ratio = len([t for t in topic_mastery if t['band'] in ('Mastered', 'Good')]) / len(topic_mastery)
        else:
            mastered_ratio = 0

        composite = (avg_score * 0.40 + consistency_score * 0.15 + trend_score * 0.20 + mastered_ratio * 0.25)
        composite_pct = round(composite * 100, 1)

        if composite_pct >= 80:
            level = 'Excellent'
        elif composite_pct >= 65:
            level = 'Good'
        elif composite_pct >= 50:
            level = 'Moderate'
        elif composite_pct >= 35:
            level = 'Needs Improvement'
        else:
            level = 'At Risk'

        trend_dir = 'Improving' if trend_diff > 2 else 'Declining' if trend_diff < -2 else 'Stable'
        competence = {
            'level': level,
            'score': composite_pct,
            'trend': trend_dir,
            'trend_diff': round(trend_diff, 1),
        }

    # ── Score timeline for chart (chronological) ──
    timeline = sorted(recent_tests, key=lambda t: t['date'])

    context = {
        'student': student,
        'time_range': time_range,
        'total_tests': total_tests,
        'total_questions': total_questions,
        'average_score': round(average_score, 1),
        'subject_performance': subject_performance,
        'recent_tests': recent_tests[:10],
        'strengths': strengths,
        'weaknesses': weaknesses,
        'competence': competence,
        'timeline': timeline,
        'topic_mastery': topic_mastery,
    }

    return render(request, 'student/analytics_dashboard_simple.html', context)


@login_required
@staff_member_required
def teacher_analytics_dashboard(request):
    """
    Comprehensive analytics dashboard for teachers
    """
    school = get_user_school(request.user)

    # Get filters from request
    grade_id = request.GET.get('grade')
    section = request.GET.get('section')
    group_id = request.GET.get('group')
    time_range = request.GET.get('range', '6m')

    # Time range
    if time_range == '1m':
        start_date = timezone.now() - timedelta(days=30)
    elif time_range == '3m':
        start_date = timezone.now() - timedelta(days=90)
    elif time_range == '6m':
        start_date = timezone.now() - timedelta(days=180)
    elif time_range == '1y':
        start_date = timezone.now() - timedelta(days=365)
    else:
        start_date = timezone.now() - timedelta(days=180)

    end_date = timezone.now()

    # Get filter objects
    grade = Grade.objects.get(id=grade_id) if grade_id else None
    class_group = ClassGroup.objects.get(id=group_id) if group_id else None

    # Initialize class analytics
    #class_analytics = ClassAnalytics( school=school, section=section, class_group=class_group, start_date=start_date,, end_date=end_date)

    # Get student list for individual analysis
    students = class_analytics._get_students()

    # Get view type
    view_type = request.GET.get('view', 'overview')  # overview, student, comparative

    context = {
        'school': school,
        'time_range': time_range,
        'start_date': start_date,
        'end_date': end_date,
        'view_type': view_type,

        # Filters
        'grades': Grade.objects.all(),
        'selected_grade': grade,
        'selected_section': section,
        'class_groups': ClassGroup.objects.filter(school=school),
        'selected_group': class_group,

        # Class-level metrics
        'class_average_per_subject': class_analytics.class_average_per_subject(),
        'lo_mastery_heatmap': class_analytics.lo_mastery_heatmap(),
        'at_risk_students': class_analytics.at_risk_students(),

        # Student list for dropdown
        'students': students,
    }

    # If viewing individual student
    if view_type == 'student':
        student_id = request.GET.get('student_id')
        if student_id:
            try:
                student = Student.objects.get(id=student_id, school=school)
                student_analytics = StudentAnalytics(student, start_date, end_date)

                context['selected_student'] = student
                context['student_subject_performance'] = student_analytics.subject_performance_summary()
                context['student_topic_performance'] = student_analytics.topic_performance()
                context['student_strengths_weaknesses'] = student_analytics.strengths_and_weaknesses()
                context['student_engagement'] = student_analytics.engagement_metrics()
            except Student.DoesNotExist:
                messages.error(request, "Student not found")

    return render(request, 'teacher/analytics_dashboard.html', context)


@login_required
@staff_member_required
def test_analytics(request, test_id):
    """
    Detailed analytics for a specific test
    """
    from .models import Test, StudentAnswer

    school = get_user_school(request.user)

    try:
        test = Test.objects.get(id=test_id)
    except Test.DoesNotExist:
        messages.error(request, "Test not found")
        return redirect("tests_list")

    # Get all students who took the test
    student_answers = StudentAnswer.objects.filter(
        test=test,
        marks_awarded__isnull=False
    ).select_related('student', 'question')

    # Calculate class statistics
    student_totals = {}
    for ans in student_answers:
        if ans.student.id not in student_totals:
            student_totals[ans.student.id] = {
                'student': ans.student,
                'total_marks': 0,
                'earned_marks': 0
            }

        student_totals[ans.student.id]['total_marks'] += float(ans.question.marks)
        student_totals[ans.student.id]['earned_marks'] += float(ans.marks_awarded)

    # Calculate percentages
    student_results = []
    for student_id, data in student_totals.items():
        percentage = (data['earned_marks'] / data['total_marks'] * 100) if data['total_marks'] > 0 else 0
        student_results.append({
            'student_id': data['student'].id,
            'student_name': data['student'].full_name,
            'total_marks': data['total_marks'],
            'earned_marks': data['earned_marks'],
            'percentage': round(percentage, 2)
        })


    student_results.sort(key=lambda x: x['percentage'], reverse=True)

    # Class statistics
    percentages = [r['percentage'] for r in student_results]

    import statistics
    class_stats = {
        'mean': round(statistics.mean(percentages), 2) if percentages else 0,
        'median': round(statistics.median(percentages), 2) if percentages else 0,
        'std_dev': round(statistics.stdev(percentages), 2) if len(percentages) > 1 else 0,
        'max': round(max(percentages), 2) if percentages else 0,
        'min': round(min(percentages), 2) if percentages else 0,
        'count': len(percentages)
    }

    context = {
        'test': test,
        'student_results': student_results,
        'class_stats': class_stats,
    }

    return render(request, 'teacher/analytics_dashboard.html', context)

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from core.models import Test
from core.analytics.mcq_signals import compute_mcq_signals
from core.analytics.examiner_schema import build_examiner_schema
from core.analytics.examiner_ai import generate_examiner_report


@login_required
@staff_member_required
def mcq_examiner_report(request, test_id):
    """
    JSON API: MCQ Examiner-style report for a test
    """

    test = get_object_or_404(Test, id=test_id)

    # No responses → graceful exit
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
