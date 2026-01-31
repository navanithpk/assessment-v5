from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.template.loader import render_to_string
from django.db import models
from django.db.models import Q
import json

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
    if role in ['teacher', 'school_admin']:
        return redirect("teacher_dashboard")
    elif role == 'student':
        return redirect("student_dashboard")
    else:
        return redirect("/admin/")


def custom_login(request):
    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            error = "Invalid username or password"
        else:
            login(request, user)
            return redirect_after_login(user)

    return render(request, "registration/login.html", {"error": error})


# ===================== DASHBOARDS =====================

@login_required
def teacher_dashboard(request):
    school = get_user_school(request.user)
    role = get_user_role(request.user)

    # Get pending tasks for admin to-do list
    pending_tasks = []

    # Find questions without topics
    questions_without_topic = Question.objects.filter(topic__isnull=True)[:10]
    for q in questions_without_topic:
        pending_tasks.append({
            'type': 'tag_topic',
            'question_id': q.id,
            'title': 'Tag topic for question',
            'description': f'Question #{q.id} needs a topic tag',
            'icon': '🏷️'
        })

    # Find questions without answer keys (empty answer_text)
    questions_without_answer = Question.objects.filter(
        Q(answer_text__isnull=True) | Q(answer_text='')
    )[:10]
    for q in questions_without_answer:
        pending_tasks.append({
            'type': 'tag_answer',
            'question_id': q.id,
            'title': 'Tag answer key for question',
            'description': f'Question #{q.id} needs an answer key',
            'icon': '✅'
        })

    # Find questions without learning objectives (ManyToMany field)
    all_questions = Question.objects.all()[:50]  # Check first 50 questions
    for q in all_questions:
        if q.learning_objectives.count() == 0:
            pending_tasks.append({
                'type': 'tag_lo',
                'question_id': q.id,
                'title': 'Tag learning objective for question',
                'description': f'Question #{q.id} needs a learning objective',
                'icon': '🎯'
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


@login_required
def student_dashboard(request):
    school = get_user_school(request.user)
    
    context = {
        'school': school,
    }
    
    return render(request, "student/student_dashboard.html", context)


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
    is_school_admin = (role == 'school_admin')
    
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
    is_school_admin = (role == 'school_admin')
    
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
    is_school_admin = (role == 'school_admin')
    
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
    tests = Test.objects.filter(created_by=request.user).order_by("-id")

    return render(
        request,
        "teacher/tests_list.html",
        {"tests": tests, "school": school}
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
def toggle_publish(request, test_id):
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    test.is_published = not test.is_published
    test.save()
    return redirect("tests_list")


@login_required
def delete_test(request, test_id):
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    test.delete()
    return redirect("tests_list")


@login_required
def duplicate_test(request, test_id):
    test = get_object_or_404(Test, id=test_id, created_by=request.user)

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
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
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

    school = get_user_school(request.user)
    qs = Question.objects.filter(
        created_by=request.user
    ).select_related("grade", "subject", "topic").prefetch_related("learning_objectives")

    # Filters
    grade = request.GET.get("grade")
    subject = request.GET.get("subject")
    qtype = request.GET.get("question_type")
    marks = request.GET.get("marks")
    year = request.GET.get("year")

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

    topics = request.GET.getlist("topics[]")
    if topics:
        qs = qs.filter(topic_id__in=topics)

    los = request.GET.getlist("los[]")
    if los:
        qs = qs.filter(learning_objectives__id__in=los).distinct()

    # Sorting
    sort_by = request.GET.get("sort", "id")
    order = request.GET.get("order", "desc")

    # Valid sort fields
    valid_sorts = ["id", "grade__name", "subject__name", "topic__name", "question_type", "marks", "year"]
    if sort_by not in valid_sorts:
        sort_by = "id"

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
def inline_add_question(request, test_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    test = get_object_or_404(Test, id=test_id, created_by=request.user)

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
    
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
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
    
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
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

# ===================== DESCRIPTIVE TESTS (TEACHER) =====================

@login_required
def create_descriptive_test(request):
    """
    Create a new descriptive test with hierarchical questions
    """
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
            
            # Create the test
            test = Test.objects.create(
                title=title,
                created_by=request.user,
                is_published=False
            )
            
            # Store the hierarchical structure as JSON in a TextField
            # You'll need to add this field to your Test model
            test.descriptive_structure = json.dumps(questions_data)
            test.save()
            
            return JsonResponse({
                'success': True,
                'test_id': test.id,
                'message': 'Test created successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    # GET request - show the editor
    return render(request, 'teacher/create_descriptive_test.html', {
        'school': school
    })


@login_required
def edit_descriptive_test(request, test_id):
    """
    Edit an existing descriptive test
    """
    school = get_user_school(request.user)
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            test.title = data.get('title', test.title)
            test.descriptive_structure = json.dumps(data.get('questions', []))
            test.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Test updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    # GET request - show editor with existing data
    questions_data = []
    if hasattr(test, 'descriptive_structure') and test.descriptive_structure:
        try:
            questions_data = json.loads(test.descriptive_structure)
        except:
            questions_data = []
    
    return render(request, 'teacher/create_descriptive_test.html', {
        'school': school,
        'test': test,
        'questions_data': json.dumps(questions_data)
    })


# ===================== STUDENT TEST TAKING =====================


# CRITICAL FIX: Update these specific views in your views.py file

@login_required
def test_editor(request, test_id):
    """
    Test editor with proper student assignment handling
    """
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
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
            "grades": Grade.objects.all(),
            "subjects": subjects,
            "school": school,
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
        # Check if question has answer spaces (structured question)
        answer_spaces = AnswerSpace.objects.filter(question=tq.question).order_by('order')

        question_data = {
            'id': tq.question.id,
            'number': f'Q{idx}',
            'content': tq.question.question_text,
            'marks': tq.question.marks,
            'type': tq.question.question_type,
            'answerId': f'q{tq.question.id}'
        }

        # Add answer spaces if this is a structured question
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

        # Each question is a separate page
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

            # Extract question ID from format "q123" -> 123 (regular questions)
            elif answer_key.startswith('q'):
                try:
                    question_id = int(answer_key[1:])
                    question = Question.objects.get(id=question_id)

                    # Create or update StudentAnswer
                    StudentAnswer.objects.update_or_create(
                        student=student,
                        test=test,
                        question=question,
                        defaults={
                            'answer_text': answer_text
                        }
                    )
                except (ValueError, Question.DoesNotExist):
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
    Submit completed test
    """
    try:
        student = Student.objects.get(user=request.user)
        test = get_object_or_404(Test, id=test_id)

        data = json.loads(request.body)
        answers = data.get('answers', {})

        # Save all answers to StudentAnswer model
        # You'll need to modify this based on your question structure

        for question_id, answer_text in answers.items():
            # Extract actual question ID from answerId format (e.g., "q1a" -> "1a")
            # This depends on your question identification scheme

            # For now, store as JSON in a submission tracking model
            pass

        # Clear session answers
        if f'test_{test_id}_answers' in request.session:
            del request.session[f'test_{test_id}_answers']

        return JsonResponse({
            'success': True,
            'message': 'Test submitted successfully'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
    test = get_object_or_404(Test, id=test_id, created_by=request.user)

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
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
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
    test = get_object_or_404(Test, id=test_id, created_by=request.user)

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
    test = get_object_or_404(Test, id=test_id, created_by=request.user)

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
    Publish test results to students
    """
    try:
        test = get_object_or_404(Test, id=test_id, created_by=request.user)

        # Check if all answers are graded
        total_answers = StudentAnswer.objects.filter(test=test).count()
        graded_answers = StudentAnswer.objects.filter(
            test=test,
            marks_awarded__isnull=False
        ).count()

        if total_answers > graded_answers:
            return JsonResponse({
                'error': f'Only {graded_answers} out of {total_answers} answers are graded',
                'success': False
            }, status=400)

        # Mark test as results published (you may need to add this field to Test model)
        # test.results_published = True
        # test.save()

        return JsonResponse({
            'success': True,
            'message': 'Results published successfully',
            'graded_answers': graded_answers
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

        # Check if all answers are graded
        graded_count = student_answers.filter(marks_awarded__isnull=False).count()
        total_count = student_answers.count()
        is_graded = graded_count == total_count and total_count > 0

        if is_graded and total_marks > 0:
            percentage = (scored_marks / total_marks) * 100

            results.append({
                'test': test,
                'scored_marks': scored_marks,
                'total_marks': total_marks,
                'percentage': round(percentage, 1),
                'is_graded': True,
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
        test_questions = test.test_questions.all().order_by('order')

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

    context = {
        'test': test,
        'student': student,
        'review_data': review_data,
        'total_marks': total_marks,
        'scored_marks': scored_marks,
        'percentage': round(percentage, 1),
        'is_fully_graded': is_fully_graded
    }

    return render(request, 'student/test_review.html', context)


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
def ai_suggest_topic(request):
    """AI-powered topic suggestion for questions with context-aware prompting and OCR"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        question_text = data.get('question_text', '')
        subject_id = data.get('subject_id')
        grade_id = data.get('grade_id')

        if not question_text or not subject_id or not grade_id:
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        # Get subject and grade names for context-aware prompting
        from .models import Subject, Grade
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

        # Use AI to suggest topic
        import anthropic
        import os
        import re
        import requests
        from .ai_tagging_improved import ImageTextExtractor, ContextAwarePromptBuilder

        api_key = os.environ.get('ANTHROPIC_API_KEY')
        google_api_key = os.environ.get('GOOGLE_API_KEY', 'AIzaSyCzbW72vCJ3YfxBEkQNb8HZkBTXD3iL6QE')
        lmstudio_url = os.environ.get('LMSTUDIO_URL', 'http://localhost:1234/v1/chat/completions')

        # Check if question contains image
        has_image = '<img' in question_text and 'base64' in question_text

        # Extract text from images using OCR
        image_text = ImageTextExtractor.extract_from_html(question_text)

        # Build context-aware prompt
        prompt_text, clean_text = ContextAwarePromptBuilder.build_topic_prompt(
            question_text, image_text, subject_name, grade_name, topic_list
        )

        # Priority 1: Try LMStudio FIRST (works with OCR-extracted text)
        suggested_topic_id = None
        used_service = None
        error_details = {}

        try:
            response = requests.post(
                lmstudio_url,
                json={
                    "model": "local-model",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert educational content analyzer. Always respond with just the topic number."
                        },
                        {
                            "role": "user",
                            "content": prompt_text
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 50
                },
                timeout=45  # Allow 30-50 seconds for AI processing
            )

            if response.status_code == 200:
                response_data = response.json()
                response_text = response_data['choices'][0]['message']['content'].strip()
                topic_number = int(re.search(r'\d+', response_text).group())

                if 0 < topic_number <= len(topic_list):
                    suggested_topic_id = topic_list[topic_number - 1]['id']
                    suggested_topic_name = topic_list[topic_number - 1]['name']
                    used_service = 'LMStudio'
            else:
                error_details['lmstudio'] = f"HTTP {response.status_code}"

        except requests.exceptions.ConnectionError:
            error_details['lmstudio'] = 'Connection refused - not running'
        except requests.exceptions.Timeout:
            error_details['lmstudio'] = 'Timeout - may be overloaded'
        except Exception as e:
            error_details['lmstudio'] = str(e)
            print(f"LMStudio failed: {str(e)}")

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
        question_text = data.get('question_text', '')
        topic_id = data.get('topic_id')

        if not question_text or not topic_id:
            return JsonResponse({'error': 'Missing required fields'}, status=400)

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

        # Use AI to suggest LOs
        import anthropic
        import os
        import re
        import requests
        from .ai_tagging_improved import ImageTextExtractor, ContextAwarePromptBuilder

        api_key = os.environ.get('ANTHROPIC_API_KEY')
        google_api_key = os.environ.get('GOOGLE_API_KEY', 'AIzaSyCzbW72vCJ3YfxBEkQNb8HZkBTXD3iL6QE')
        lmstudio_url = os.environ.get('LMSTUDIO_URL', 'http://localhost:1234/v1/chat/completions')

        # Extract text from images using OCR
        image_text = ImageTextExtractor.extract_from_html(question_text)

        # Build context-aware prompt for LO selection
        prompt_text, clean_text = ContextAwarePromptBuilder.build_lo_prompt(
            question_text, image_text, subject_name, grade_name, topic_name, lo_list
        )

        # Priority 1: Try LMStudio FIRST (works with OCR-extracted text)
        suggested_los = []
        used_service = None

        try:
            response = requests.post(
                lmstudio_url,
                json={
                    "model": "local-model",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert educational content analyzer. Always respond with just the numbers separated by commas."
                        },
                        {
                            "role": "user",
                            "content": prompt_text
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 100
                },
                timeout=30
            )

            if response.status_code == 200:
                response_data = response.json()
                response_text = response_data['choices'][0]['message']['content'].strip()
                lo_numbers = [int(n.strip()) for n in re.findall(r'\d+', response_text)]
                suggested_los = [lo_list[n - 1] for n in lo_numbers if 0 < n <= len(lo_list)]
                if suggested_los:
                    used_service = 'LMStudio'

        except Exception as e:
            print(f"LMStudio failed: {str(e)}")

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
            return JsonResponse({'error': 'All AI services failed. Please check your API keys and LMStudio connection.'}, status=500)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@staff_member_required
def bulk_ai_tag_questions(request):
    """
    Bulk AI tagging with OCR, context-aware prompting, and comprehensive logging
    """
    from django.http import StreamingHttpResponse
    import time
    from .ai_tagging_improved import (
        AITaggingLogger, ImageTextExtractor, ContextAwarePromptBuilder,
        call_lmstudio, call_google_gemini, call_anthropic
    )

    # Initialize logger
    tag_logger = AITaggingLogger()

    def event_stream():
        try:
            # Get all untagged questions (without topic or LOs)
            untagged_questions = Question.objects.filter(
                Q(topic__isnull=True) | Q(learning_objectives__isnull=True)
            ).distinct()

            total = untagged_questions.count()
            processed = 0

            for question in untagged_questions:
                try:
                    # Skip if both topic and LOs are already set
                    has_topic = question.topic is not None
                    has_los = question.learning_objectives.count() > 0

                    if has_topic and has_los:
                        processed += 1
                        yield f'data: {json.dumps({"progress": processed, "total": total})}\n\n'
                        continue

                    # Tag topic if missing
                    if not has_topic and question.subject and question.grade:
                        # Call AI topic suggestion
                        try:
                            topic_data = {
                                'question_text': question.question_text,
                                'subject_id': question.subject.id,
                                'grade_id': question.grade.id
                            }

                            # Use the existing ai_suggest_topic logic inline
                            import anthropic
                            import os
                            import re
                            import requests

                            api_key = os.environ.get('ANTHROPIC_API_KEY')
                            google_api_key = os.environ.get('GOOGLE_API_KEY', 'AIzaSyCzbW72vCJ3YfxBEkQNb8HZkBTXD3iL6QE')
                            lmstudio_url = os.environ.get('LMSTUDIO_URL', 'http://localhost:1234/v1/chat/completions')

                            topics = Topic.objects.filter(
                                subject_id=question.subject.id,
                                grade_id=question.grade.id
                            ).values('id', 'name')
                            topic_list = [{'id': t['id'], 'name': t['name']} for t in topics]

                            if topic_list:
                                topic_names = '\n'.join([f"{i+1}. {t['name']}" for i, t in enumerate(topic_list)])
                                clean_text = re.sub(r'<[^>]+>', '', question.question_text)

                                suggested_topic_id = None

                                # Try Anthropic first
                                if api_key:
                                    try:
                                        client = anthropic.Anthropic(api_key=api_key)
                                        message = client.messages.create(
                                            model="claude-3-5-sonnet-20241022",
                                            max_tokens=200,
                                            messages=[{
                                                "role": "user",
                                                "content": f"""Analyze this question and select the most appropriate topic from the list below.

Question:
{clean_text}

Available topics:
{topic_names}

Respond with ONLY the topic number (e.g., "3" for the third topic). Do not include any explanation or additional text."""
                                            }]
                                        )
                                        response_text = message.content[0].text.strip()
                                        topic_number = int(re.search(r'\d+', response_text).group())
                                        suggested_topic_id = topic_list[topic_number - 1]['id']
                                    except:
                                        pass

                                # Try Google Gemini if Anthropic failed
                                if not suggested_topic_id and google_api_key:
                                    try:
                                        google_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={google_api_key}"
                                        response = requests.post(
                                            google_url,
                                            json={
                                                "contents": [{
                                                    "parts": [{
                                                        "text": f"""Analyze this question and select the most appropriate topic from the list below.

Question:
{clean_text}

Available topics:
{topic_names}

Respond with ONLY the topic number (e.g., "3" for the third topic). Do not include any explanation or additional text."""
                                                    }]
                                                }]
                                            },
                                            timeout=30
                                        )
                                        if response.status_code == 200:
                                            response_data = response.json()
                                            response_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
                                            topic_number = int(re.search(r'\d+', response_text).group())
                                            suggested_topic_id = topic_list[topic_number - 1]['id']
                                    except:
                                        pass

                                if suggested_topic_id:
                                    question.topic_id = suggested_topic_id
                                    question.save()

                        except Exception as e:
                            print(f"Error tagging topic for question {question.id}: {str(e)}")

                    # Tag LOs if missing and topic is now set
                    if question.topic and question.learning_objectives.count() == 0:
                        try:
                            # Use the existing ai_suggest_los logic inline
                            import anthropic
                            import os
                            import re
                            import requests

                            api_key = os.environ.get('ANTHROPIC_API_KEY')
                            google_api_key = os.environ.get('GOOGLE_API_KEY', 'AIzaSyCzbW72vCJ3YfxBEkQNb8HZkBTXD3iL6QE')

                            los = LearningObjective.objects.filter(topic_id=question.topic.id).values('id', 'code', 'description')
                            lo_list = [{'id': lo['id'], 'code': lo['code'], 'description': lo['description']} for lo in los]

                            if lo_list:
                                lo_descriptions = '\n'.join([f"{i+1}. [{lo['code']}] {lo['description']}" for i, lo in enumerate(lo_list)])
                                clean_text = re.sub(r'<[^>]+>', '', question.question_text)

                                suggested_los = []

                                # Try Anthropic first
                                if api_key:
                                    try:
                                        client = anthropic.Anthropic(api_key=api_key)
                                        message = client.messages.create(
                                            model="claude-3-5-sonnet-20241022",
                                            max_tokens=300,
                                            messages=[{
                                                "role": "user",
                                                "content": f"""Analyze this question and select the most relevant learning objective(s) from the list below.

Topic: {question.topic.name}

Question:
{clean_text}

Available learning objectives:
{lo_descriptions}

You may select multiple learning objectives if relevant. Respond with ONLY the numbers separated by commas (e.g., "1,3,5"). Do not include any explanation or additional text."""
                                            }]
                                        )
                                        response_text = message.content[0].text.strip()
                                        lo_numbers = [int(n.strip()) for n in re.findall(r'\d+', response_text)]
                                        suggested_los = [lo_list[n - 1] for n in lo_numbers if 0 < n <= len(lo_list)]
                                    except:
                                        pass

                                # Try Google Gemini if Anthropic failed
                                if not suggested_los and google_api_key:
                                    try:
                                        google_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={google_api_key}"
                                        response = requests.post(
                                            google_url,
                                            json={
                                                "contents": [{
                                                    "parts": [{
                                                        "text": f"""Analyze this question and select the most relevant learning objective(s) from the list below.

Topic: {question.topic.name}

Question:
{clean_text}

Available learning objectives:
{lo_descriptions}

You may select multiple learning objectives if relevant. Respond with ONLY the numbers separated by commas (e.g., "1,3,5"). Do not include any explanation or additional text."""
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
                                    except:
                                        pass

                                if suggested_los:
                                    for lo in suggested_los:
                                        question.learning_objectives.add(lo['id'])

                        except Exception as e:
                            print(f"Error tagging LOs for question {question.id}: {str(e)}")

                    processed += 1
                    yield f'data: {json.dumps({"progress": processed, "total": total})}\n\n'

                    # Small delay to avoid rate limiting
                    time.sleep(0.5)

                except Exception as e:
                    print(f"Error processing question {question.id}: {str(e)}")
                    processed += 1
                    yield f'data: {json.dumps({"progress": processed, "total": total, "error": str(e)})}\n\n'

            yield f'data: {json.dumps({"complete": True, "total": total})}\n\n'

        except Exception as e:
            yield f'data: {json.dumps({"error": str(e)})}\n\n'

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')

# ===================== UNTAGGED QUESTIONS & BACKGROUND TAGGING =====================

@login_required
@staff_member_required
def untagged_questions_view(request):
    """View to display and manage untagged questions"""
    from django.db.models import Count

    # Get all questions that are missing topic OR learning objectives
    untagged_questions = Question.objects.filter(
        Q(topic__isnull=True) | Q(learning_objectives__isnull=True)
    ).select_related('grade', 'subject', 'topic').prefetch_related('learning_objectives').distinct()

    # Filter by school if user is not superuser
    if not request.user.is_superuser:
        try:
            user_school = request.user.userprofile.school
            untagged_questions = untagged_questions.filter(
                created_by__userprofile__school=user_school
            )
        except (AttributeError, UserProfile.DoesNotExist):
            # User doesn't have a profile or school, show only their own questions
            untagged_questions = untagged_questions.filter(created_by=request.user)

    # Statistics
    total_untagged = untagged_questions.count()
    missing_topics = untagged_questions.filter(topic__isnull=True).count()
    missing_los = untagged_questions.filter(learning_objectives__isnull=True).count()

    context = {
        'questions': untagged_questions,
        'total_untagged': total_untagged,
        'missing_topics': missing_topics,
        'missing_los': missing_los,
    }

    return render(request, 'teacher/untagged_questions.html', context)


@login_required
@staff_member_required
def start_background_tagging(request):
    """Start a background tagging task"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        from .background_tagging import create_tagging_task

        data = json.loads(request.body)
        mode = data.get('mode', 'both')  # 'topics', 'los', or 'both'

        # Validate mode
        if mode not in ['topics', 'los', 'both']:
            return JsonResponse({'error': 'Invalid mode'}, status=400)

        # Get untagged questions
        questions = Question.objects.filter(
            Q(topic__isnull=True) | Q(learning_objectives__isnull=True)
        ).select_related('grade', 'subject', 'topic').distinct()

        # Filter by school
        if not request.user.is_superuser:
            try:
                user_school = request.user.userprofile.school
                questions = questions.filter(
                    created_by__userprofile__school=user_school
                )
            except (AttributeError, UserProfile.DoesNotExist):
                # User doesn't have a profile or school, show only their own questions
                questions = questions.filter(created_by=request.user)

        if not questions.exists():
            return JsonResponse({'error': 'No untagged questions found'}, status=400)

        # Create and start the background task
        task = create_tagging_task(mode, questions)

        return JsonResponse({
            'success': True,
            'task_id': task.task_id,
            'total_questions': task.total,
            'mode': mode
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@staff_member_required
def get_tagging_progress(request, task_id):
    """Get the progress of a background tagging task"""
    from .background_tagging import get_task_status

    task_status = get_task_status(task_id)

    if not task_status:
        return JsonResponse({'error': 'Task not found'}, status=404)

    return JsonResponse(task_status)

