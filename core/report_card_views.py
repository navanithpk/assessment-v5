"""
Report Card Views - Generate comprehensive student report cards
with topic mastery, LO mastery, subject trends, and strengths/weaknesses
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Avg, Sum, Count
from django.core.paginator import Paginator
from datetime import datetime
from collections import defaultdict

from .models import (
    Student, Test, TestQuestion, StudentAnswer, Subject, Grade,
    ClassGroup, School, LearningObjective, Topic, Question
)


@login_required
def report_card_dashboard(request):
    """
    Main report card dashboard with search, filter, test selection, and pagination
    """
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

    # Apply search filter
    if search_query:
        students = students.filter(
            Q(full_name__icontains=search_query) |
            Q(roll_number__icontains=search_query) |
            Q(admission_id__icontains=search_query)
        )

    if grade_filter:
        students = students.filter(grade__id=grade_filter)

    if cohort_filter:
        cohort = ClassGroup.objects.filter(id=cohort_filter, school=school).first()
        if cohort:
            cohort_user_ids = cohort.students.values_list('id', flat=True)
            students = students.filter(user__id__in=cohort_user_ids)

    # Get filter options for dropdowns
    subjects = Subject.objects.all().order_by('name')
    grades = Grade.objects.all().order_by('name')
    cohorts = ClassGroup.objects.filter(school=school).order_by('name')

    # Get available tests for the test selector
    available_tests = Test.objects.filter(
        created_by__profile__school=school,
        is_published=True
    ).select_related('subject').order_by('-created_at')

    # Apply date filters to available tests
    if date_from:
        try:
            available_tests = available_tests.filter(
                created_at__gte=datetime.strptime(date_from, '%Y-%m-%d')
            )
        except ValueError:
            pass
    if date_to:
        try:
            available_tests = available_tests.filter(
                created_at__lte=datetime.strptime(date_to, '%Y-%m-%d')
            )
        except ValueError:
            pass

    if subject_filter:
        available_tests = available_tests.filter(subject__id=subject_filter)

    # Pagination
    paginator = Paginator(students.order_by('grade', 'section', 'roll_number'), 10)
    page_obj = paginator.get_page(page_number)

    # Summary data per student on current page
    students_data = []
    for student in page_obj:
        test_filters = Q(student=student, marks_awarded__isnull=False)

        if date_from:
            try:
                test_filters &= Q(test__created_at__gte=datetime.strptime(date_from, '%Y-%m-%d'))
            except ValueError:
                pass
        if date_to:
            try:
                test_filters &= Q(test__created_at__lte=datetime.strptime(date_to, '%Y-%m-%d'))
            except ValueError:
                pass

        answers = StudentAnswer.objects.filter(test_filters).select_related('test', 'test__subject')

        if subject_filter:
            answers = answers.filter(test__subject__id=subject_filter)

        test_ids = answers.values_list('test__id', flat=True).distinct()
        test_count = test_ids.count()

        if test_count > 0:
            test_scores = []
            for tid in test_ids:
                test_answers = answers.filter(test_id=tid)
                total_marks = sum(float(a.question.marks or 0) for a in test_answers)
                earned_marks = sum(float(a.marks_awarded or 0) for a in test_answers)
                if total_marks > 0:
                    test_scores.append((earned_marks / total_marks) * 100)
            avg_score = sum(test_scores) / len(test_scores) if test_scores else 0
        else:
            avg_score = 0

        if avg_score >= 80:
            status = 'Excellent'
        elif avg_score >= 65:
            status = 'Good'
        elif avg_score >= 50:
            status = 'Moderate'
        elif avg_score >= 35:
            status = 'Needs Improvement'
        elif test_count > 0:
            status = 'At Risk'
        else:
            status = 'No Data'

        students_data.append({
            'student': student,
            'test_count': test_count,
            'avg_score': round(avg_score, 1),
            'status': status,
        })

    # Build test list for JSON (for the test selector in the template)
    tests_for_selector = []
    for t in available_tests[:100]:  # limit to 100 recent tests
        tests_for_selector.append({
            'id': t.id,
            'title': t.title,
            'subject': t.subject.name if t.subject else 'General',
            'date': t.created_at.strftime('%d/%m/%Y'),
        })

    context = {
        'page_obj': page_obj,
        'students_data': students_data,
        'subjects': subjects,
        'grades': grades,
        'cohorts': cohorts,
        'available_tests': tests_for_selector,
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
    Comprehensive report card data for a specific student (JSON for jsPDF).
    Now includes: topic mastery, LO mastery, subject-vs-subject,
    per-subject trends over time, and strengths/weaknesses analysis.
    """
    school = request.user.profile.school
    student = get_object_or_404(Student, id=student_id, school=school)

    # Get filters
    subject_filter = request.GET.get('subject', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    selected_tests = request.GET.get('tests', '')  # comma-separated test IDs

    # Build query filters
    test_filters = Q(student=student, marks_awarded__isnull=False)

    if date_from:
        try:
            test_filters &= Q(test__created_at__gte=datetime.strptime(date_from, '%Y-%m-%d'))
        except ValueError:
            pass

    if date_to:
        try:
            test_filters &= Q(test__created_at__lte=datetime.strptime(date_to, '%Y-%m-%d'))
        except ValueError:
            pass

    answers = StudentAnswer.objects.filter(test_filters).select_related(
        'test', 'test__subject', 'question', 'question__topic',
        'question__topic__grade', 'question__topic__subject'
    ).prefetch_related('question__learning_objectives')

    if subject_filter:
        answers = answers.filter(test__subject__id=subject_filter)

    # Filter by selected tests if provided
    if selected_tests:
        test_id_list = [int(x) for x in selected_tests.split(',') if x.strip().isdigit()]
        if test_id_list:
            answers = answers.filter(test__id__in=test_id_list)

    # ─────────────────────────────────────────────
    # 1. Group by test - basic test performance
    # ─────────────────────────────────────────────
    tests_data = {}
    for answer in answers:
        test_id = answer.test.id
        if test_id not in tests_data:
            tests_data[test_id] = {
                'test': answer.test,
                'subject': answer.test.subject.name if answer.test.subject else 'General',
                'title': answer.test.title,
                'date': answer.test.created_at.strftime('%d/%m/%Y'),
                'answers': [],
                'total_marks': 0,
                'earned_marks': 0,
            }

        tests_data[test_id]['answers'].append(answer)
        tests_data[test_id]['total_marks'] += float(answer.question.marks or 0)
        tests_data[test_id]['earned_marks'] += float(answer.marks_awarded or 0)

    tests_list = []
    subject_summary = {}
    subject_trend = defaultdict(list)  # subject -> [{date, percentage}, ...]

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

        # Subject summary
        if data['subject'] not in subject_summary:
            subject_summary[data['subject']] = {
                'test_count': 0,
                'total_percentage': 0,
            }
        subject_summary[data['subject']]['test_count'] += 1
        subject_summary[data['subject']]['total_percentage'] += percentage

        # Subject trend (per-subject over time)
        subject_trend[data['subject']].append({
            'date': data['date'],
            'percentage': round(percentage, 1),
            'title': data['title'],
        })

    # Sort trends by date
    for subj in subject_trend:
        subject_trend[subj].sort(key=lambda x: x['date'])

    # ─────────────────────────────────────────────
    # 2. Subject averages
    # ─────────────────────────────────────────────
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

    # ─────────────────────────────────────────────
    # 3. Topic mastery analysis (with LO coverage)
    # ─────────────────────────────────────────────
    topic_map = defaultdict(lambda: {
        'earned': 0.0, 'max': 0.0, 'count': 0, 'subject': '',
        'topic_id': None, 'grade_id': None, 'subject_id': None,
        'tested_lo_codes': set(),
    })

    for answer in answers:
        topic = answer.question.topic
        if topic:
            key = topic.name
            topic_map[key]['earned'] += float(answer.marks_awarded or 0)
            topic_map[key]['max'] += float(answer.question.marks or 0)
            topic_map[key]['count'] += 1
            topic_map[key]['subject'] = answer.test.subject.name if answer.test.subject else 'General'
            topic_map[key]['topic_id'] = topic.id
            topic_map[key]['grade_id'] = topic.grade_id
            topic_map[key]['subject_id'] = topic.subject_id
            # Track which LOs have been tested
            for lo in answer.question.learning_objectives.all():
                topic_map[key]['tested_lo_codes'].add(lo.code)

    # Get total LO counts per topic for coverage calculation
    topic_ids = [d['topic_id'] for d in topic_map.values() if d['topic_id']]
    all_topic_los = defaultdict(list)
    if topic_ids:
        for lo in LearningObjective.objects.filter(topic_id__in=topic_ids).values('topic_id', 'code', 'description'):
            all_topic_los[lo['topic_id']].append({'code': lo['code'], 'description': lo['description']})

    topic_mastery = []
    for topic_name, data in topic_map.items():
        mastery = round((data['earned'] / data['max']) * 100, 1) if data['max'] > 0 else 0
        band = (
            'Mastered' if mastery >= 80 else
            'Good' if mastery >= 60 else
            'Developing' if mastery >= 40 else
            'Weak'
        )
        # Calculate LO coverage
        total_los = all_topic_los.get(data['topic_id'], [])
        tested_codes = data['tested_lo_codes']
        untested_los = [lo for lo in total_los if lo['code'] not in tested_codes]

        topic_mastery.append({
            'name': topic_name,
            'subject': data['subject'],
            'mastery': mastery,
            'band': band,
            'questions': data['count'],
            'earned': round(data['earned'], 1),
            'max': round(data['max'], 1),
            'total_los': len(total_los),
            'tested_los': len(tested_codes),
            'untested_los': [{'code': lo['code'], 'description': lo['description']} for lo in untested_los],
            'lo_coverage': round((len(tested_codes) / len(total_los)) * 100, 0) if total_los else 100,
        })

    topic_mastery.sort(key=lambda x: x['mastery'], reverse=True)

    # ─────────────────────────────────────────────
    # 4. LO mastery analysis (ONLY tested LOs)
    # ─────────────────────────────────────────────
    lo_map = defaultdict(lambda: {'earned': 0.0, 'max': 0.0, 'count': 0, 'description': '', 'topic': ''})

    for answer in answers:
        los = answer.question.learning_objectives.all()
        for lo in los:
            key = lo.code
            # Distribute marks equally across LOs
            lo_share = 1.0 / len(los) if len(los) > 0 else 1.0
            lo_map[key]['earned'] += float(answer.marks_awarded or 0) * lo_share
            lo_map[key]['max'] += float(answer.question.marks or 0) * lo_share
            lo_map[key]['count'] += 1
            lo_map[key]['description'] = lo.description
            lo_map[key]['topic'] = lo.topic.name if lo.topic else ''

    lo_mastery = []
    for lo_code, data in lo_map.items():
        mastery = round((data['earned'] / data['max']) * 100, 1) if data['max'] > 0 else 0
        band = (
            'Mastered' if mastery >= 80 else
            'Good' if mastery >= 60 else
            'Developing' if mastery >= 40 else
            'Weak'
        )
        lo_mastery.append({
            'code': lo_code,
            'description': data['description'],
            'topic': data['topic'],
            'mastery': mastery,
            'band': band,
            'questions': data['count'],
            'tested': True,  # Explicitly flag as tested
        })

    lo_mastery.sort(key=lambda x: x['mastery'], reverse=True)

    # ─────────────────────────────────────────────
    # 5. Strengths & Weaknesses
    # ─────────────────────────────────────────────
    strengths = [t for t in topic_mastery if t['mastery'] >= 75][:5]
    weaknesses = [t for t in reversed(topic_mastery) if t['mastery'] < 50][:5]

    lo_strengths = [lo for lo in lo_mastery if lo['mastery'] >= 75][:5]
    lo_weaknesses = [lo for lo in reversed(lo_mastery) if lo['mastery'] < 50][:5]

    # ─────────────────────────────────────────────
    # 6. Teacher recommendations (re-issue suggestions)
    # ─────────────────────────────────────────────
    recommendations = []
    for t in topic_mastery:
        if t['band'] in ('Weak', 'Developing'):
            rec = {
                'topic': t['name'],
                'subject': t['subject'],
                'current_mastery': t['mastery'],
                'band': t['band'],
                'tested_los': t['tested_los'],
                'total_los': t['total_los'],
                'untested_los': t['untested_los'],
            }
            if t['untested_los']:
                rec['action'] = 'Re-issue topic with untested LOs'
                rec['message'] = (
                    f"Only {t['tested_los']}/{t['total_los']} LOs tested. "
                    f"Consider re-issuing questions covering the remaining "
                    f"{len(t['untested_los'])} untested LO(s) before concluding "
                    f"this topic is weak."
                )
            else:
                rec['action'] = 'Assign targeted practice'
                rec['message'] = (
                    f"All {t['total_los']} LOs have been tested. "
                    f"Student needs more practice in this topic."
                )
            recommendations.append(rec)

    # ─────────────────────────────────────────────
    # 7. Student Competence Assessment
    # ─────────────────────────────────────────────
    # Competence is a holistic measure derived from multiple signals:
    #   - Overall average score
    #   - Score consistency (std dev)
    #   - Trend direction (improving vs declining)
    #   - Topic breadth (mastered topics ratio)
    #   - LO coverage
    #
    # Levels: Excellent / Good / Moderate / Needs Improvement / At Risk

    competence = {
        'level': 'Not Assessed',
        'score': 0,
        'signals': {},
    }

    if tests_list:
        import math

        # Signal 1: Overall average (0-100)
        avg = overall_average
        avg_score = min(avg / 100, 1.0)  # normalised 0-1

        # Signal 2: Consistency (low std dev = more consistent = better)
        percentages = [t['percentage'] for t in tests_list]
        if len(percentages) > 1:
            mean_p = sum(percentages) / len(percentages)
            variance = sum((p - mean_p) ** 2 for p in percentages) / len(percentages)
            std_dev = math.sqrt(variance)
            # Consistency score: std_dev of 0 => 1.0, std_dev >= 30 => 0.0
            consistency_score = max(0, 1.0 - (std_dev / 30.0))
        else:
            std_dev = 0
            consistency_score = 0.5  # neutral with single test

        # Signal 3: Trend (improvement over recent tests)
        sorted_tests = sorted(tests_list, key=lambda t: t['date'])
        if len(sorted_tests) >= 3:
            recent_half = sorted_tests[len(sorted_tests)//2:]
            older_half = sorted_tests[:len(sorted_tests)//2]
            recent_avg = sum(t['percentage'] for t in recent_half) / len(recent_half)
            older_avg = sum(t['percentage'] for t in older_half) / len(older_half)
            trend_diff = recent_avg - older_avg
            # Trend score: +10 or more => 1.0, -10 or less => 0.0, 0 => 0.5
            trend_score = max(0, min(1.0, 0.5 + (trend_diff / 20.0)))
            trend_direction = 'Improving' if trend_diff > 2 else 'Declining' if trend_diff < -2 else 'Stable'
        elif len(sorted_tests) == 2:
            trend_diff = sorted_tests[1]['percentage'] - sorted_tests[0]['percentage']
            trend_score = max(0, min(1.0, 0.5 + (trend_diff / 20.0)))
            trend_direction = 'Improving' if trend_diff > 2 else 'Declining' if trend_diff < -2 else 'Stable'
        else:
            trend_diff = 0
            trend_score = 0.5
            trend_direction = 'Insufficient data'

        # Signal 4: Topic mastery breadth
        if topic_mastery:
            mastered_ratio = len([t for t in topic_mastery if t['band'] in ('Mastered', 'Good')]) / len(topic_mastery)
        else:
            mastered_ratio = 0
        mastery_breadth_score = mastered_ratio

        # Weighted composite (avg=40%, consistency=15%, trend=20%, breadth=25%)
        composite = (
            avg_score * 0.40 +
            consistency_score * 0.15 +
            trend_score * 0.20 +
            mastery_breadth_score * 0.25
        )
        composite_pct = round(composite * 100, 1)

        # Map to competence level
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

        competence = {
            'level': level,
            'score': composite_pct,
            'signals': {
                'average': round(avg, 1),
                'average_weight': 40,
                'consistency': round((1 - std_dev / 30.0) * 100, 1) if std_dev < 30 else 0,
                'consistency_weight': 15,
                'std_dev': round(std_dev, 1),
                'trend': trend_direction,
                'trend_diff': round(trend_diff, 1),
                'trend_weight': 20,
                'mastery_breadth': round(mastered_ratio * 100, 1),
                'mastery_breadth_weight': 25,
            }
        }

    # ─────────────────────────────────────────────
    # 8. Competence over time (for graph)
    # ─────────────────────────────────────────────
    # Build a rolling competence score per test chronologically.
    # For each test point, compute cumulative stats up to that test.
    competence_timeline = []
    sorted_all_tests = sorted(tests_list, key=lambda t: t['date'])

    # Also build per-subject timelines
    subject_competence_timeline = defaultdict(list)

    if sorted_all_tests:
        # Overall timeline
        running_scores = []
        for t in sorted_all_tests:
            running_scores.append(t['percentage'])
            running_avg = sum(running_scores) / len(running_scores)

            # Simple competence at this point = running average
            if running_avg >= 80:
                pt_level = 'Excellent'
            elif running_avg >= 65:
                pt_level = 'Good'
            elif running_avg >= 50:
                pt_level = 'Moderate'
            elif running_avg >= 35:
                pt_level = 'Needs Improvement'
            else:
                pt_level = 'At Risk'

            competence_timeline.append({
                'date': t['date'],
                'test_title': t['title'],
                'score': round(running_avg, 1),
                'test_score': t['percentage'],
                'level': pt_level,
            })

        # Per-subject timeline
        subject_running = defaultdict(list)
        for t in sorted_all_tests:
            subj_name = t['subject']
            subject_running[subj_name].append(t['percentage'])
            subj_avg = sum(subject_running[subj_name]) / len(subject_running[subj_name])

            if subj_avg >= 80:
                s_level = 'Excellent'
            elif subj_avg >= 65:
                s_level = 'Good'
            elif subj_avg >= 50:
                s_level = 'Moderate'
            elif subj_avg >= 35:
                s_level = 'Needs Improvement'
            else:
                s_level = 'At Risk'

            subject_competence_timeline[subj_name].append({
                'date': t['date'],
                'test_title': t['title'],
                'score': round(subj_avg, 1),
                'test_score': t['percentage'],
                'level': s_level,
            })

    # ─────────────────────────────────────────────
    # 9. Build response
    # ─────────────────────────────────────────────
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
        'subject_trends': dict(subject_trend),
        'topic_mastery': topic_mastery,
        'lo_mastery': lo_mastery,
        'strengths': {
            'topics': strengths,
            'learning_objectives': lo_strengths,
        },
        'weaknesses': {
            'topics': weaknesses,
            'learning_objectives': lo_weaknesses,
        },
        'recommendations': recommendations,
        'overall': {
            'total_tests': len(tests_list),
            'average_percentage': round(overall_average, 1),
            'grade': get_letter_grade(overall_average),
            'total_topics': len(topic_mastery),
            'mastered_topics': len([t for t in topic_mastery if t['band'] == 'Mastered']),
            'weak_topics': len([t for t in topic_mastery if t['band'] == 'Weak']),
        },
        'competence': competence,
        'competence_timeline': competence_timeline,
        'subject_competence_timeline': dict(subject_competence_timeline),
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


@login_required
def topic_reissue_suggestions(request):
    """
    Returns JSON with per-topic list of students who are weak and should be
    re-issued practice. Useful for teachers to create targeted assignments.

    Query params:
        grade: grade ID
        subject: subject ID
        test: optional test ID to scope to a specific test
    """
    school = request.user.profile.school
    grade_id = request.GET.get('grade', '')
    subject_id = request.GET.get('subject', '')
    test_id = request.GET.get('test', '')

    if not grade_id or not subject_id:
        return JsonResponse({'error': 'Grade and subject are required'}, status=400)

    grade = Grade.objects.filter(id=grade_id).first()
    subject = Subject.objects.filter(id=subject_id).first()
    if not grade or not subject:
        return JsonResponse({'error': 'Invalid grade or subject'}, status=404)

    # Get all students in this school/grade
    students = Student.objects.filter(school=school, grade=grade)

    # Get all answers for these students in this subject
    answer_filter = Q(
        student__in=students,
        test__subject=subject,
        marks_awarded__isnull=False,
    )
    if test_id:
        answer_filter &= Q(test_id=test_id)

    answers = StudentAnswer.objects.filter(answer_filter).select_related(
        'student', 'question', 'question__topic'
    ).prefetch_related('question__learning_objectives')

    # Build per-student, per-topic mastery
    # Structure: {topic_name: {student_id: {earned, max, tested_los}}}
    topic_student_map = defaultdict(lambda: defaultdict(lambda: {
        'earned': 0.0, 'max': 0.0, 'tested_lo_codes': set(),
        'student_name': '', 'roll_number': '', 'student_id': None,
    }))

    for answer in answers:
        topic = answer.question.topic
        if not topic:
            continue

        sid = answer.student.id
        entry = topic_student_map[topic.name][sid]
        entry['earned'] += float(answer.marks_awarded or 0)
        entry['max'] += float(answer.question.marks or 0)
        entry['student_name'] = answer.student.full_name
        entry['roll_number'] = answer.student.roll_number or ''
        entry['student_id'] = sid

        for lo in answer.question.learning_objectives.all():
            entry['tested_lo_codes'].add(lo.code)

    # Get total LOs per topic
    topics = Topic.objects.filter(grade=grade, subject=subject)
    topic_total_los = {}
    for topic in topics:
        lo_count = LearningObjective.objects.filter(topic=topic).count()
        topic_total_los[topic.name] = lo_count

    # Build suggestions per topic
    suggestions = []
    for topic_name, student_data in topic_student_map.items():
        total_los = topic_total_los.get(topic_name, 0)
        weak_students = []

        for sid, data in student_data.items():
            if data['max'] <= 0:
                continue
            mastery = round((data['earned'] / data['max']) * 100, 1)
            if mastery < 60:  # Weak or Developing
                weak_students.append({
                    'id': data['student_id'],
                    'name': data['student_name'],
                    'roll_number': data['roll_number'],
                    'mastery': mastery,
                    'tested_los': len(data['tested_lo_codes']),
                    'total_los': total_los,
                    'lo_coverage': round((len(data['tested_lo_codes']) / total_los) * 100, 0) if total_los > 0 else 100,
                })

        if weak_students:
            weak_students.sort(key=lambda x: x['mastery'])
            suggestions.append({
                'topic': topic_name,
                'total_los': total_los,
                'weak_student_count': len(weak_students),
                'students': weak_students,
            })

    suggestions.sort(key=lambda x: x['weak_student_count'], reverse=True)

    return JsonResponse({
        'grade': grade.name,
        'subject': subject.name,
        'suggestions': suggestions,
        'total_topics_with_issues': len(suggestions),
    })


@login_required
def reissue_dashboard(request):
    """Teacher dashboard for re-issuing topics to weak students."""
    school = request.user.profile.school
    grades = Grade.objects.all().order_by('name')
    subjects = Subject.objects.all().order_by('name')
    tests = Test.objects.filter(
        created_by__profile__school=school,
        is_published=True
    ).select_related('subject').order_by('-created_at')[:100]

    return render(request, 'teacher/reissue_dashboard.html', {
        'grades': grades,
        'subjects': subjects,
        'tests': tests,
    })


@login_required
def assign_practice(request):
    """
    Assign a published test to specific students.
    POST JSON: { test_id: int, student_ids: [int, ...] }
    """
    import json
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    test_id = data.get('test_id')
    student_ids = data.get('student_ids', [])

    if not test_id or not student_ids:
        return JsonResponse({'error': 'test_id and student_ids are required'}, status=400)

    school = request.user.profile.school
    test = Test.objects.filter(id=test_id, created_by__profile__school=school).first()
    if not test:
        return JsonResponse({'error': 'Test not found'}, status=404)

    students = Student.objects.filter(id__in=student_ids, school=school)
    # Add students to the test's assigned_students (don't replace existing)
    for student in students:
        test.assigned_students.add(student)

    return JsonResponse({
        'success': True,
        'message': f'Assigned {students.count()} student(s) to "{test.title}"',
        'assigned_count': students.count(),
    })


@login_required
def smart_test_generator(request):
    """
    Dashboard for semi-automatically creating individualised tests/worksheets
    based on weak topics/LOs per student or cohort.
    """
    school = request.user.profile.school
    grades = Grade.objects.all().order_by('name')
    subjects = Subject.objects.all().order_by('name')
    cohorts = ClassGroup.objects.filter(school=school).order_by('name')

    return render(request, 'teacher/smart_test_generator.html', {
        'grades': grades,
        'subjects': subjects,
        'cohorts': cohorts,
    })


@login_required
def smart_test_analyse(request):
    """
    API: Analyse student/cohort performance and return weak areas with available questions.
    GET params: grade, subject, student_id (optional), cohort_id (optional)
    """
    import json
    school = request.user.profile.school
    grade_id = request.GET.get('grade', '')
    subject_id = request.GET.get('subject', '')
    student_id = request.GET.get('student_id', '')
    cohort_id = request.GET.get('cohort_id', '')

    if not grade_id or not subject_id:
        return JsonResponse({'error': 'Grade and subject are required'}, status=400)

    grade = Grade.objects.filter(id=grade_id).first()
    subject = Subject.objects.filter(id=subject_id).first()
    if not grade or not subject:
        return JsonResponse({'error': 'Invalid grade or subject'}, status=404)

    # Grade-level: all grades in the same curriculum level (IGCSE-1/2/IGCSE share questions)
    same_level_grades = grade.get_same_level_grades()

    # Determine target students
    if student_id:
        students = Student.objects.filter(id=student_id, school=school)
    elif cohort_id:
        cohort = ClassGroup.objects.filter(id=cohort_id, school=school).first()
        if cohort:
            cohort_user_ids = cohort.students.values_list('id', flat=True)
            students = Student.objects.filter(user__id__in=cohort_user_ids, school=school)
        else:
            students = Student.objects.filter(school=school, grade=grade)
    else:
        students = Student.objects.filter(school=school, grade=grade)

    # Get all answers for these students in this subject
    answers = StudentAnswer.objects.filter(
        student__in=students,
        test__subject=subject,
        marks_awarded__isnull=False,
    ).select_related('student', 'question', 'question__topic').prefetch_related(
        'question__learning_objectives'
    )

    # Build topic mastery map
    topic_performance = defaultdict(lambda: {'earned': 0.0, 'max': 0.0, 'count': 0})
    lo_performance = defaultdict(lambda: {'earned': 0.0, 'max': 0.0, 'count': 0})

    for a in answers:
        t = a.question.topic
        if t:
            topic_performance[t.id]['earned'] += float(a.marks_awarded or 0)
            topic_performance[t.id]['max'] += float(a.question.marks or 0)
            topic_performance[t.id]['count'] += 1
        for lo in a.question.learning_objectives.all():
            lo_share = 1.0 / len(a.question.learning_objectives.all()) if a.question.learning_objectives.count() > 0 else 1.0
            lo_performance[lo.id]['earned'] += float(a.marks_awarded or 0) * lo_share
            lo_performance[lo.id]['max'] += float(a.question.marks or 0) * lo_share
            lo_performance[lo.id]['count'] += 1

    # Get all topics across same-level grades (e.g. IGCSE-1 sees topics from IGCSE, IGCSE-2 too)
    topics = Topic.objects.filter(
        grade__in=same_level_grades, subject=subject
    ).order_by('name').distinct()

    weak_topics = []
    for topic in topics:
        perf = topic_performance.get(topic.id)
        if perf and perf['max'] > 0:
            mastery = round((perf['earned'] / perf['max']) * 100, 1)
        else:
            mastery = None  # Not tested

        # Count available questions across ALL same-level grades for this topic
        q_count = Question.objects.filter(
            topic=topic, grade__in=same_level_grades, subject=subject, parent__isnull=True
        ).count()

        band = (
            'Mastered' if mastery is not None and mastery >= 80 else
            'Good' if mastery is not None and mastery >= 60 else
            'Developing' if mastery is not None and mastery >= 40 else
            'Weak' if mastery is not None else
            'Untested'
        )

        # Get LOs for this topic
        topic_los = LearningObjective.objects.filter(topic=topic)
        lo_details = []
        for lo in topic_los:
            lp = lo_performance.get(lo.id)
            if lp and lp['max'] > 0:
                lo_mastery = round((lp['earned'] / lp['max']) * 100, 1)
            else:
                lo_mastery = None
            lo_details.append({
                'id': lo.id,
                'code': lo.code,
                'description': lo.description[:80],
                'mastery': lo_mastery,
                'band': (
                    'Mastered' if lo_mastery is not None and lo_mastery >= 80 else
                    'Good' if lo_mastery is not None and lo_mastery >= 60 else
                    'Developing' if lo_mastery is not None and lo_mastery >= 40 else
                    'Weak' if lo_mastery is not None else
                    'Untested'
                ),
            })

        weak_topics.append({
            'id': topic.id,
            'name': topic.name,
            'mastery': mastery,
            'band': band,
            'question_count': q_count,
            'questions_tested': perf['count'] if perf else 0,
            'los': lo_details,
        })

    # Sort: weak first, then developing, then untested, then good, then mastered
    band_order = {'Weak': 0, 'Developing': 1, 'Untested': 2, 'Good': 3, 'Mastered': 4}
    weak_topics.sort(key=lambda x: (band_order.get(x['band'], 5), x.get('mastery') or 0))

    # Student list for individual selection
    student_list = [
        {'id': s.id, 'name': s.full_name, 'roll': s.roll_number or ''}
        for s in students.order_by('full_name')
    ]

    return JsonResponse({
        'grade': grade.name,
        'grade_level': grade.grade_level or grade.name,
        'same_level_grades': [g.name for g in same_level_grades],
        'subject': subject.name,
        'student_count': students.count(),
        'students': student_list[:100],
        'topics': weak_topics,
    })


@login_required
def smart_test_create(request):
    """
    API: Create a test from selected topics/questions and assign to students.
    POST JSON: {
        title: str,
        grade_id: int,
        subject_id: int,
        topic_ids: [int,...],          # topics to pull questions from
        questions_per_topic: int,      # how many per topic
        student_ids: [int,...],        # students to assign
        include_untested_los: bool,    # prefer questions covering untested LOs
    }
    """
    import json
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    school = request.user.profile.school
    title = data.get('title', 'Smart Worksheet')
    grade_id = data.get('grade_id')
    subject_id = data.get('subject_id')
    topic_ids = data.get('topic_ids', [])
    questions_per_topic = int(data.get('questions_per_topic', 5))
    student_ids = data.get('student_ids', [])
    include_untested = data.get('include_untested_los', False)

    if not grade_id or not subject_id or not topic_ids:
        return JsonResponse({'error': 'grade_id, subject_id, and topic_ids are required'}, status=400)

    grade = Grade.objects.filter(id=grade_id).first()
    subject = Subject.objects.filter(id=subject_id).first()
    if not grade or not subject:
        return JsonResponse({'error': 'Invalid grade or subject'}, status=404)

    # Create the test
    test = Test.objects.create(
        title=title,
        created_by=request.user,
        subject=subject,
        test_type='standard',
        is_published=False,
    )

    # Pull questions from selected topics
    order = 0
    total_added = 0

    for topic_id in topic_ids:
        topic = Topic.objects.filter(id=topic_id).first()
        if not topic:
            continue

        # Get available questions across all same-level grades for this topic
        same_level_grades = grade.get_same_level_grades()
        qs = Question.objects.filter(
            topic=topic, grade__in=same_level_grades, subject=subject, parent__isnull=True
        )

        if include_untested:
            # If student_ids provided, prefer questions with untested LOs for those students
            if student_ids:
                students = Student.objects.filter(id__in=student_ids, school=school)
                # Find LOs already tested by these students
                tested_lo_ids = set(
                    StudentAnswer.objects.filter(
                        student__in=students,
                        test__subject=subject,
                        marks_awarded__isnull=False,
                    ).values_list('question__learning_objectives__id', flat=True)
                )
                # Prefer questions with untested LOs
                untested_qs = qs.exclude(learning_objectives__id__in=tested_lo_ids)
                if untested_qs.exists():
                    selected = list(untested_qs.order_by('?')[:questions_per_topic])
                else:
                    selected = list(qs.order_by('?')[:questions_per_topic])
            else:
                selected = list(qs.order_by('?')[:questions_per_topic])
        else:
            selected = list(qs.order_by('?')[:questions_per_topic])

        for q in selected:
            order += 1
            TestQuestion.objects.create(test=test, question=q, order=order)
            total_added += 1

    # Assign to students
    if student_ids:
        valid_students = Student.objects.filter(id__in=student_ids, school=school)
        test.assigned_students.set(valid_students)

    return JsonResponse({
        'success': True,
        'test_id': test.id,
        'title': test.title,
        'questions_added': total_added,
        'students_assigned': len(student_ids),
        'edit_url': f'/teacher/tests/{test.id}/edit/',
    })
