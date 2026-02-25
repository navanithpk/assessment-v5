"""
Resource Views — Google Classroom-style file sharing.
Teachers and students can upload notes, homework, worksheets, files and links.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Resource, Grade, Subject, School, UserProfile
from .views import get_user_school


@login_required
def resource_list(request):
    """
    List resources visible to the current user.
    Supports filtering by subject and resource_type.
    Both students and teachers see resources from their school.
    """
    school = get_user_school(request.user)
    qs = Resource.objects.filter(school=school).order_by('-created_at')

    # Filters
    subject_id = request.GET.get('subject')
    rtype = request.GET.get('type')

    if subject_id:
        qs = qs.filter(subject_id=subject_id)
    if rtype:
        qs = qs.filter(resource_type=rtype)

    subjects = Subject.objects.all().order_by('name')

    # Check role
    try:
        profile = request.user.profile
        is_teacher = profile.role in ('teacher', 'school_admin')
    except UserProfile.DoesNotExist:
        is_teacher = request.user.is_staff

    context = {
        'resources': qs[:50],
        'subjects': subjects,
        'selected_subject': subject_id,
        'selected_type': rtype,
        'is_teacher': is_teacher,
        'resource_types': Resource.RESOURCE_TYPES,
    }

    # Use different base templates for teacher vs student
    if is_teacher:
        return render(request, 'teacher/resources.html', context)
    else:
        return render(request, 'student/resources.html', context)


@login_required
def resource_upload(request):
    """Upload a new resource (POST only)."""
    if request.method != 'POST':
        return redirect('resource_list')

    school = get_user_school(request.user)
    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    resource_type = request.POST.get('resource_type', 'file')
    subject_id = request.POST.get('subject') or None
    grade_id = request.POST.get('grade') or None
    link_url = request.POST.get('link_url', '').strip()
    uploaded_file = request.FILES.get('file')

    if not title:
        messages.error(request, 'Title is required.')
        return redirect('resource_list')

    if resource_type == 'link' and not link_url:
        messages.error(request, 'URL is required for link resources.')
        return redirect('resource_list')

    if resource_type != 'link' and not uploaded_file:
        messages.error(request, 'File is required.')
        return redirect('resource_list')

    resource = Resource.objects.create(
        title=title,
        description=description,
        resource_type=resource_type,
        file=uploaded_file if resource_type != 'link' else None,
        link_url=link_url if resource_type == 'link' else '',
        school=school,
        grade_id=grade_id if grade_id else None,
        subject_id=subject_id if subject_id else None,
        uploaded_by=request.user,
    )

    messages.success(request, f'"{title}" uploaded successfully.')
    return redirect('resource_list')


@login_required
def resource_delete(request, resource_id):
    """Delete a resource (owner or teacher only)."""
    resource = get_object_or_404(Resource, id=resource_id)
    school = get_user_school(request.user)

    # Permission check
    if resource.school != school:
        messages.error(request, 'Access denied.')
        return redirect('resource_list')

    try:
        profile = request.user.profile
        is_teacher = profile.role in ('teacher', 'school_admin')
    except UserProfile.DoesNotExist:
        is_teacher = request.user.is_staff

    if resource.uploaded_by != request.user and not is_teacher:
        messages.error(request, 'Only the uploader or a teacher can delete resources.')
        return redirect('resource_list')

    resource.file.delete(save=False)  # delete file from disk
    resource.delete()
    messages.success(request, 'Resource deleted.')
    return redirect('resource_list')
