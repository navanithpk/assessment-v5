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
    Simplified analytics dashboard for students
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found")
        return redirect("student_dashboard")

    # Get time range from request (default: last 6 months)
    time_range = request.GET.get('range', '6m')

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

    # Get student's test data
    from .models import StudentAnswer, Test

    answers = StudentAnswer.objects.filter(
        student=student,
        test__created_at__gte=start_date,
        test__created_at__lte=end_date
    ).select_related('test', 'test__subject', 'question')

    # Calculate basic metrics
    total_tests = answers.values('test').distinct().count()
    total_questions = answers.count()

    # Calculate average score
    total_marks = sum(float(a.question.marks or 0) for a in answers)
    earned_marks = sum(float(a.marks_awarded or 0) for a in answers)
    average_score = (earned_marks / total_marks * 100) if total_marks > 0 else 0

    # Subject performance
    subject_performance = []
    subjects = answers.values_list('test__subject', flat=True).distinct()
    for subject_id in subjects:
        if not subject_id:
            continue
        subject_answers = answers.filter(test__subject_id=subject_id)
        subject = Subject.objects.get(id=subject_id)

        subj_total = sum(float(a.question.marks or 0) for a in subject_answers)
        subj_earned = sum(float(a.marks_awarded or 0) for a in subject_answers)
        subj_score = (subj_earned / subj_total * 100) if subj_total > 0 else 0

        subject_performance.append({
            'name': subject.name,
            'score': round(subj_score, 1),
            'tests': subject_answers.values('test').distinct().count()
        })

    context = {
        'student': student,
        'time_range': time_range,
        'start_date': start_date,
        'end_date': end_date,
        'total_tests': total_tests,
        'total_questions': total_questions,
        'average_score': round(average_score, 1),
        'subject_performance': subject_performance,
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
