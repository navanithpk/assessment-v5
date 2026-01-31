"""
Report Card Views - Generate comprehensive student report cards
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Avg, Sum, Count
from django.core.paginator import Paginator
from datetime import datetime

from .models import (
    Student, Test, StudentAnswer, Subject, Grade,
    ClassGroup, School
)


@login_required
def report_card_dashboard(request):
    """
    Main report card dashboard with search, filter, and pagination
    """
    # Get user's school
    school = request.user.profile.school

    # Initialize filters
    search_query = request.GET.get('search', '').strip()
    subject_filter = request.GET.get('subject', '')
    grade_filter = request.GET.get('grade', '')
    cohort_filter = request.GET.get('cohort', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    page_number = request.GET.get('page', 1)

    # Base queryset - students in this school
    students = Student.objects.filter(school=school).select_related('grade')

    # Apply search filter (name, roll number, admission ID)
    if search_query:
        students = students.filter(
            Q(full_name__icontains=search_query) |
            Q(roll_number__icontains=search_query) |
            Q(admission_id__icontains=search_query)
        )

    # Apply grade filter
    if grade_filter:
        students = students.filter(grade__id=grade_filter)

    # Apply cohort filter
    if cohort_filter:
        cohort = ClassGroup.objects.filter(id=cohort_filter, school=school).first()
        if cohort:
            # Get users in this cohort
            cohort_user_ids = cohort.students.values_list('id', flat=True)
            # Filter students whose user is in this cohort
            students = students.filter(user__id__in=cohort_user_ids)

    # Get filter options for dropdowns
    subjects = Subject.objects.all().order_by('name')
    grades = Grade.objects.all().order_by('name')
    cohorts = ClassGroup.objects.filter(school=school).order_by('name')

    # Pagination (10 students per page)
    paginator = Paginator(students.order_by('grade', 'section', 'roll_number'), 10)
    page_obj = paginator.get_page(page_number)

    # For each student on current page, get summary data
    students_data = []
    for student in page_obj:
        # Get all tests this student has taken
        test_filters = Q(student=student)

        # Apply date range filter if specified
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                test_filters &= Q(test__created_at__gte=date_from_obj)
            except ValueError:
                pass

        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                test_filters &= Q(test__created_at__lte=date_to_obj)
            except ValueError:
                pass

        answers = StudentAnswer.objects.filter(test_filters).select_related('test', 'test__subject')

        # Apply subject filter
        if subject_filter:
            answers = answers.filter(test__subject__id=subject_filter)

        # Get unique tests
        tests = answers.values('test__id').distinct()
        test_count = tests.count()

        # Calculate average performance
        if test_count > 0:
            # Group by test, calculate percentage for each
            test_scores = []
            for test_id in answers.values_list('test__id').distinct():
                test = Test.objects.get(id=test_id[0])
                test_answers = answers.filter(test=test)

                total_marks = sum(float(a.question.marks or 0) for a in test_answers)
                earned_marks = sum(float(a.marks_awarded or 0) for a in test_answers)

                if total_marks > 0:
                    percentage = (earned_marks / total_marks) * 100
                    test_scores.append(percentage)

            avg_score = sum(test_scores) / len(test_scores) if test_scores else 0
        else:
            avg_score = 0

        students_data.append({
            'student': student,
            'test_count': test_count,
            'avg_score': round(avg_score, 1),
            'status': 'Excellent' if avg_score >= 80 else 'Good' if avg_score >= 60 else 'Needs Improvement'
        })

    context = {
        'page_obj': page_obj,
        'students_data': students_data,
        'subjects': subjects,
        'grades': grades,
        'cohorts': cohorts,
        'filters': {
            'search': search_query,
            'subject': subject_filter,
            'grade': grade_filter,
            'cohort': cohort_filter,
            'date_from': date_from,
            'date_to': date_to,
        },
        'total_count': paginator.count,
    }

    return render(request, 'teacher/report_card_dashboard.html', context)


@login_required
def report_card_detail(request, student_id):
    """
    Get detailed report card data for a specific student (JSON for jsPDF)
    """
    school = request.user.profile.school
    student = get_object_or_404(Student, id=student_id, school=school)

    # Get filters from request
    subject_filter = request.GET.get('subject', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Build query filters
    test_filters = Q(student=student)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            test_filters &= Q(test__created_at__gte=date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            test_filters &= Q(test__created_at__lte=date_to_obj)
        except ValueError:
            pass

    answers = StudentAnswer.objects.filter(test_filters).select_related(
        'test', 'test__subject', 'question', 'question__topic'
    )

    if subject_filter:
        answers = answers.filter(test__subject__id=subject_filter)

    # Group by test
    tests_data = {}
    for answer in answers:
        test_id = answer.test.id
        if test_id not in tests_data:
            tests_data[test_id] = {
                'test': answer.test,
                'subject': answer.test.subject.name if answer.test.subject else 'General',
                'title': answer.test.title,
                'date': answer.test.created_at.strftime('%Y-%m-%d'),
                'answers': [],
                'total_marks': 0,
                'earned_marks': 0,
            }

        tests_data[test_id]['answers'].append(answer)
        tests_data[test_id]['total_marks'] += float(answer.question.marks or 0)
        tests_data[test_id]['earned_marks'] += float(answer.marks_awarded or 0)

    # Calculate percentages and build response
    tests_list = []
    subject_summary = {}

    for test_id, data in tests_data.items():
        percentage = (data['earned_marks'] / data['total_marks']) * 100 if data['total_marks'] > 0 else 0

        test_info = {
            'id': test_id,
            'subject': data['subject'],
            'title': data['title'],
            'date': data['date'],
            'total_marks': round(data['total_marks'], 1),
            'earned_marks': round(data['earned_marks'], 1),
            'percentage': round(percentage, 1),
            'grade': get_letter_grade(percentage),
        }
        tests_list.append(test_info)

        # Update subject summary
        if data['subject'] not in subject_summary:
            subject_summary[data['subject']] = {
                'test_count': 0,
                'total_percentage': 0,
            }
        subject_summary[data['subject']]['test_count'] += 1
        subject_summary[data['subject']]['total_percentage'] += percentage

    # Calculate subject averages
    subjects_list = []
    overall_average = 0
    for subject, summary in subject_summary.items():
        avg = summary['total_percentage'] / summary['test_count']
        subjects_list.append({
            'name': subject,
            'test_count': summary['test_count'],
            'average': round(avg, 1),
            'grade': get_letter_grade(avg),
        })
        overall_average += avg

    if subjects_list:
        overall_average = overall_average / len(subjects_list)

    response_data = {
        'student': {
            'name': student.full_name,
            'roll_number': student.roll_number,
            'admission_id': student.admission_id,
            'grade': student.grade.name,
            'section': student.section,
        },
        'school': {
            'name': school.name,
            'code': school.code,
            'address': school.address,
        },
        'period': {
            'from': date_from or 'All time',
            'to': date_to or 'Present',
        },
        'tests': sorted(tests_list, key=lambda x: x['date']),
        'subjects': sorted(subjects_list, key=lambda x: x['name']),
        'overall': {
            'total_tests': len(tests_list),
            'average_percentage': round(overall_average, 1),
            'grade': get_letter_grade(overall_average),
        }
    }

    return JsonResponse(response_data)


def get_letter_grade(percentage):
    """Convert percentage to letter grade"""
    if percentage >= 90:
        return 'A+'
    elif percentage >= 80:
        return 'A'
    elif percentage >= 70:
        return 'B+'
    elif percentage >= 60:
        return 'B'
    elif percentage >= 50:
        return 'C+'
    elif percentage >= 40:
        return 'C'
    elif percentage >= 33:
        return 'D'
    else:
        return 'F'
