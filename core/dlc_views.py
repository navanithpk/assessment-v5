"""
DLC (Downloadable Content) Views - Modular Question Bank Management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, F
from django.db import models
from .models import QuestionBank, SubjectGradeCombination, Question, Subject, Grade
from django.http import JsonResponse


@login_required
def dlc_dashboard(request):
    """
    DLC Management Dashboard - View and manage question bank modules
    """
    if request.user.profile.role not in ['teacher', 'school_admin']:
        messages.error(request, "You don't have permission to access DLC management.")
        return redirect('teacher_dashboard')

    school = request.user.profile.school

    # Get all question banks for this school
    active_banks = QuestionBank.objects.filter(
        school=school,
        status='active'
    ).select_related('subject', 'grade')

    inactive_banks = QuestionBank.objects.filter(
        school=school,
        status='inactive'
    ).select_related('subject', 'grade')

    pending_banks = QuestionBank.objects.filter(
        school=school,
        status='pending'
    ).select_related('subject', 'grade')

    # Get available subject-grade combinations
    available_combinations = SubjectGradeCombination.objects.filter(
        is_active=True
    ).select_related('subject', 'grade')

    # Calculate total statistics
    total_active = active_banks.count()
    total_questions = sum(bank.question_count for bank in active_banks)
    total_size = sum(bank.total_size_mb for bank in active_banks)

    context = {
        'active_banks': active_banks,
        'inactive_banks': inactive_banks,
        'pending_banks': pending_banks,
        'available_combinations': available_combinations,
        'total_active': total_active,
        'total_questions': total_questions,
        'total_size': total_size,
    }

    return render(request, 'teacher/dlc_dashboard.html', context)


@login_required
def activate_dlc(request, bank_id):
    """
    Activate a question bank DLC
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    school = request.user.profile.school
    bank = get_object_or_404(QuestionBank, id=bank_id, school=school)

    bank.activate()

    messages.success(request, f"Activated: {bank.name}")
    return redirect('dlc_dashboard')


@login_required
def deactivate_dlc(request, bank_id):
    """
    Deactivate a question bank DLC
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    school = request.user.profile.school
    bank = get_object_or_404(QuestionBank, id=bank_id, school=school)

    if bank.is_core:
        messages.error(request, "Cannot deactivate core modules.")
        return redirect('dlc_dashboard')

    bank.deactivate()

    messages.success(request, f"Deactivated: {bank.name}")
    return redirect('dlc_dashboard')


@login_required
def create_dlc(request):
    """
    Create a new question bank DLC from subject-grade combination
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    school = request.user.profile.school
    combination_id = request.POST.get('combination_id')

    if not combination_id:
        messages.error(request, "Please select a subject-grade combination.")
        return redirect('dlc_dashboard')

    combination = get_object_or_404(SubjectGradeCombination, id=combination_id)

    # Check if bank already exists
    existing = QuestionBank.objects.filter(
        school=school,
        subject=combination.subject,
        grade=combination.grade
    ).first()

    if existing:
        messages.warning(request, f"Question bank for {combination.name} already exists.")
        return redirect('dlc_dashboard')

    # Create new question bank
    bank = QuestionBank.objects.create(
        subject=combination.subject,
        grade=combination.grade,
        name=combination.name,
        description=combination.description,
        school=school,
        created_by=request.user,
        status='pending',
        version="1.0"
    )

    messages.success(request, f"Created question bank: {bank.name}. Activate it to start using.")
    return redirect('dlc_dashboard')


@login_required
def subject_grade_combinations(request):
    """
    Manage subject-grade combinations (IGCSE, AS/A Level, JEE, SAT, CUET)
    """
    if request.user.profile.role not in ['teacher', 'school_admin']:
        messages.error(request, "You don't have permission to manage combinations.")
        return redirect('teacher_dashboard')

    combinations = SubjectGradeCombination.objects.all().select_related('subject', 'grade')

    # Group by level
    grouped = {}
    for combo in combinations:
        level = combo.get_level_display()
        if level not in grouped:
            grouped[level] = []
        grouped[level].append(combo)

    context = {
        'grouped_combinations': grouped,
    }

    return render(request, 'teacher/subject_grade_combinations.html', context)


@login_required
def add_combination(request):
    """
    Add a new subject-grade combination
    """
    if request.method != 'POST':
        # Show form
        subjects = Subject.objects.all()
        grades = Grade.objects.all()
        return render(request, 'teacher/add_combination.html', {
            'subjects': subjects,
            'grades': grades,
            'levels': SubjectGradeCombination.LEVEL_CHOICES,
        })

    # Process form
    code = request.POST.get('code')
    name = request.POST.get('name')
    subject_id = request.POST.get('subject')
    grade_id = request.POST.get('grade')
    level = request.POST.get('level')
    description = request.POST.get('description', '')

    if not all([code, name, subject_id, grade_id, level]):
        messages.error(request, "All fields are required.")
        return redirect('add_combination')

    # Check if code already exists
    if SubjectGradeCombination.objects.filter(code=code).exists():
        messages.error(request, f"Combination with code {code} already exists.")
        return redirect('add_combination')

    subject = get_object_or_404(Subject, id=subject_id)
    grade = get_object_or_404(Grade, id=grade_id)

    SubjectGradeCombination.objects.create(
        code=code,
        name=name,
        subject=subject,
        grade=grade,
        level=level,
        description=description,
        is_active=True
    )

    messages.success(request, f"Added combination: {code} - {name}")
    return redirect('subject_grade_combinations')
