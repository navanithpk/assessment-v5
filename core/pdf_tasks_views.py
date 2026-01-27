"""
PDF Processing Task Management Views
Handles task list, duplicate detection, and session management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from .models import PDFImportSession, ProcessedPDF, Grade, Subject
from .views import staff_member_required
import hashlib


@login_required
@staff_member_required
def pdf_tasks_list(request):
    """
    Display all PDF processing tasks (sessions) for the current user
    Shows pending, in-progress, paused, and completed sessions
    """
    # Get all sessions for current user
    sessions = PDFImportSession.objects.filter(created_by=request.user)

    # Separate by status
    pending_sessions = sessions.filter(status='pending')
    in_progress_sessions = sessions.filter(status='in_progress')
    paused_sessions = sessions.filter(status='paused')
    completed_sessions = sessions.filter(status='completed')[:10]  # Last 10 completed

    context = {
        'pending_sessions': pending_sessions,
        'in_progress_sessions': in_progress_sessions,
        'paused_sessions': paused_sessions,
        'completed_sessions': completed_sessions,
        'total_pending': pending_sessions.count() + in_progress_sessions.count() + paused_sessions.count(),
    }

    return render(request, 'teacher/pdf_tasks_list.html', context)


@login_required
@staff_member_required
def check_duplicate_pdf(request):
    """
    Check if a PDF file has already been processed
    Uses file hash for duplicate detection
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        import json
        data = json.loads(request.body)
        file_name = data.get('file_name')
        file_content_base64 = data.get('file_content')  # Base64 encoded file content

        if not file_name or not file_content_base64:
            return JsonResponse({'error': 'Missing file_name or file_content'}, status=400)

        # Calculate hash of file content
        import base64
        file_bytes = base64.b64decode(file_content_base64)
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Check if this hash exists
        existing_pdf = ProcessedPDF.objects.filter(file_hash=file_hash).first()

        if existing_pdf:
            return JsonResponse({
                'is_duplicate': True,
                'processed_date': existing_pdf.processed_at.strftime('%Y-%m-%d %H:%M'),
                'processed_by': existing_pdf.processed_by.username,
                'questions_created': existing_pdf.questions_created,
                'grade': existing_pdf.grade.name,
                'subject': existing_pdf.subject.name,
                'year': existing_pdf.year
            })
        else:
            return JsonResponse({
                'is_duplicate': False,
                'file_hash': file_hash  # Return hash for later use
            })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@staff_member_required
def mark_pdf_processed(request):
    """
    Mark a PDF as processed after successful import
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        import json
        data = json.loads(request.body)

        file_name = data.get('file_name')
        file_hash = data.get('file_hash')
        grade_id = data.get('grade_id')
        subject_id = data.get('subject_id')
        year = data.get('year')
        questions_created = data.get('questions_created', 0)

        if not all([file_name, file_hash, grade_id, subject_id]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        # Create ProcessedPDF record
        processed_pdf, created = ProcessedPDF.objects.get_or_create(
            file_hash=file_hash,
            defaults={
                'file_name': file_name,
                'processed_by': request.user,
                'grade_id': grade_id,
                'subject_id': subject_id,
                'year': year,
                'questions_created': questions_created
            }
        )

        return JsonResponse({
            'success': True,
            'created': created,
            'message': 'PDF marked as processed'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@staff_member_required
def delete_task(request, session_id):
    """
    Delete a PDF import task/session
    """
    session = get_object_or_404(PDFImportSession, id=session_id, created_by=request.user)
    session.delete()
    messages.success(request, f'Task "{session.session_name}" deleted successfully')
    return redirect('pdf_tasks_list')


@login_required
@staff_member_required
def mark_task_complete(request, session_id):
    """
    Mark a task as completed
    """
    session = get_object_or_404(PDFImportSession, id=session_id, created_by=request.user)
    session.status = 'completed'
    session.completed_at = timezone.now()
    session.save()
    messages.success(request, f'Task "{session.session_name}" marked as complete')
    return redirect('pdf_tasks_list')


@login_required
@staff_member_required
def pause_task(request, session_id):
    """
    Pause an in-progress task
    """
    session = get_object_or_404(PDFImportSession, id=session_id, created_by=request.user)
    session.status = 'paused'
    session.save()
    messages.success(request, f'Task "{session.session_name}" paused')
    return redirect('pdf_tasks_list')


@login_required
@staff_member_required
def resume_task(request, session_id):
    """
    Resume a paused task
    """
    session = get_object_or_404(PDFImportSession, id=session_id, created_by=request.user)
    session.status = 'in_progress'
    session.save()
    messages.success(request, f'Task "{session.session_name}" resumed')
    # Redirect to PDF import page with session data
    return redirect('pending_import_sessions')  # Or redirect to import page with session loaded
