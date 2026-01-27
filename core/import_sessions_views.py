"""
PDF Import Session Management Views
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils import timezone
from .models import PDFImportSession, Grade, Subject


@login_required
@staff_member_required
def save_import_session(request):
    """Save current import session progress"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)

        session_name = data.get('session_name')
        grade_id = data.get('grade_id')
        subject_id = data.get('subject_id')
        year = data.get('year')
        files_data = data.get('files_data', [])
        slicing_data = data.get('slicing_data', {})
        current_index = data.get('current_index', 0)

        if not all([session_name, grade_id, subject_id, year]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        # Create or update session
        session = PDFImportSession.objects.create(
            created_by=request.user,
            grade_id=grade_id,
            subject_id=subject_id,
            year=year,
            session_name=session_name,
            total_files=len(files_data),
            processed_files=current_index,
            status='paused',
            files_data=files_data,
            slicing_data=slicing_data
        )

        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'message': f'Session "{session_name}" saved successfully!'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@staff_member_required
def pending_import_sessions(request):
    """View all pending/paused import sessions"""
    sessions = PDFImportSession.objects.filter(
        created_by=request.user,
        status__in=['pending', 'paused', 'in_progress']
    ).select_related('grade', 'subject')

    context = {
        'sessions': sessions,
    }

    return render(request, 'teacher/pending_imports.html', context)


@login_required
@staff_member_required
def resume_import_session(request, session_id):
    """Resume a saved import session - redirects to PDF import page"""
    session = get_object_or_404(
        PDFImportSession,
        id=session_id,
        created_by=request.user
    )

    # Update status
    session.status = 'in_progress'
    session.save()

    # For now, redirect to PDF import page
    # TODO: Implement session data restoration in PDF import interface
    return redirect('import_mcq_pdf')


@login_required
@staff_member_required
def delete_import_session(request, session_id):
    """Delete an import session"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    session = get_object_or_404(
        PDFImportSession,
        id=session_id,
        created_by=request.user
    )

    session.delete()

    return JsonResponse({'success': True, 'message': 'Session deleted'})


@login_required
@staff_member_required
def mark_session_complete(request, session_id):
    """Mark an import session as completed"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    session = get_object_or_404(
        PDFImportSession,
        id=session_id,
        created_by=request.user
    )

    session.status = 'completed'
    session.completed_at = timezone.now()
    session.processed_files = session.total_files
    session.save()

    return JsonResponse({'success': True, 'message': 'Session marked as complete'})
