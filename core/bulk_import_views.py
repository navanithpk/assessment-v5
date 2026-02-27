"""
Bulk Import Views - For importing users from XLSX / XLS / CSV files
"""
import re
import csv
import datetime

try:
    import pandas as pd
    _PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    _PANDAS_AVAILABLE = False

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse

from .models import UserProfile, Student, School, Grade, Subject


# ── helpers ──────────────────────────────────────────────────────────────────

def _safe_str(val):
    """Convert any cell value to a clean string (handles NaN, floats, ints)."""
    if val is None:
        return ''
    import math
    if isinstance(val, float) and math.isnan(val):
        return ''
    try:
        val = val.item()   # numpy scalar → python scalar
    except AttributeError:
        pass
    return str(val).strip()


def _next_roll(school, grade_obj, section):
    """Return the next sequential roll number string for a given class."""
    existing = Student.objects.filter(
        school=school, grade=grade_obj, section=section
    ).values_list('roll_number', flat=True)
    max_num = 0
    for roll in existing:
        if roll:
            m = re.search(r'(\d+)$', roll)
            if m:
                max_num = max(max_num, int(m.group(1)))
    return str(max_num + 1)


def _next_admission_id(school):
    """Return the next sequential ADM{year}### string for the school."""
    year = datetime.datetime.now().year
    prefix = f"ADM{year}"
    existing = Student.objects.filter(school=school).values_list('admission_id', flat=True)
    max_num = 0
    for adm in existing:
        if adm:
            if adm.startswith(prefix):
                try:
                    max_num = max(max_num, int(adm[len(prefix):]))
                except ValueError:
                    pass
            else:
                m = re.search(r'(\d+)$', adm)
                if m:
                    max_num = max(max_num, int(m.group(1)))
    return f"{prefix}{str(max_num + 1).zfill(3)}"


def _read_file(file_obj):
    """Read an uploaded file (xlsx/xls/csv) into a DataFrame.

    Always reads the FIRST sheet of Excel files.
    Columns are normalised: stripped, lowercased, spaces→underscores.
    """
    name = getattr(file_obj, 'name', '').lower()
    if name.endswith('.csv'):
        df = pd.read_csv(file_obj, dtype=str)
    else:
        # sheet_name=0 → always read first sheet (prevents two-sheet confusion)
        df = pd.read_excel(file_obj, dtype=str, sheet_name=0)
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    return df


# ── views ─────────────────────────────────────────────────────────────────────

@login_required
def bulk_import_users(request):
    """Bulk import students OR teachers from a CSV / XLSX file.

    Fields are 100% aligned with the individual add_user form:
      Common   : full_name, email (used as username), password
      Students : grade (req), division (req), roll_number (opt), admission_id (opt)
      Teachers : subject (opt)
    """
    if not _PANDAS_AVAILABLE:
        messages.error(
            request,
            'Bulk import requires pandas. '
            'Ask your administrator to run: pip install pandas openpyxl'
        )
        return redirect('teacher_dashboard')

    profile = request.user.profile
    if profile.role not in ['teacher', 'school_admin']:
        messages.error(request, "You don't have permission to import users.")
        return redirect('teacher_dashboard')

    school = profile.school
    is_school_admin = (
        profile.role in ['school_admin', 'superuser'] or request.user.is_superuser
    )

    if request.method == 'POST':
        import_type = request.POST.get('import_type', 'student')  # 'student' | 'teacher'

        # ── STEP 1: PREVIEW ────────────────────────────────────────────────
        if 'preview' in request.POST:
            if import_type == 'teacher' and not is_school_admin:
                messages.error(request, "Only school administrators can import teacher accounts.")
                return redirect('bulk_import_users')

            excel_file = request.FILES.get('excel_file')
            if not excel_file:
                messages.error(request, "Please upload a file.")
                return redirect('bulk_import_users')

            try:
                df = _read_file(excel_file)
            except Exception as e:
                messages.error(request, f"Could not read file: {e}")
                return redirect('bulk_import_users')

            # Required columns — mirrors the individual creation form exactly
            if import_type == 'student':
                required_cols = ['full_name', 'email', 'password', 'grade', 'division']
            else:
                required_cols = ['full_name', 'email', 'password']

            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                messages.error(
                    request,
                    f"Missing required columns: {', '.join(missing)}. "
                    f"Columns found: {', '.join(df.columns.tolist())}"
                )
                return redirect('bulk_import_users')

            preview_data = df.fillna('').astype(str).to_dict('records')
            request.session['import_data'] = preview_data
            request.session['import_type'] = import_type

            return render(request, 'teacher/bulk_import_preview.html', {
                'preview_data': preview_data[:50],
                'total_rows': len(preview_data),
                'import_type': import_type,
            })

        # ── STEP 2: CONFIRM IMPORT ─────────────────────────────────────────
        elif 'confirm_import' in request.POST:
            import_data = request.session.get('import_data', [])
            import_type = request.session.get('import_type', 'student')

            if not import_data:
                messages.error(request, "No data to import. Please upload the file again.")
                return redirect('bulk_import_users')

            success_count = 0
            error_count = 0
            errors = []

            with transaction.atomic():
                for idx, row in enumerate(import_data, start=2):
                    try:
                        full_name = _safe_str(row.get('full_name', ''))
                        email     = _safe_str(row.get('email', '')).lower()
                        password  = _safe_str(row.get('password', ''))

                        # ── Validate common required fields ───────────────
                        if not full_name or not email or not password:
                            errors.append(
                                f"Row {idx}: Missing required field(s) — "
                                f"full_name, email and password are all required"
                            )
                            error_count += 1
                            continue

                        if len(password) < 8:
                            errors.append(
                                f"Row {idx}: Password too short (minimum 8 characters)"
                            )
                            error_count += 1
                            continue

                        # Email is used as the username (matches individual form)
                        username = email

                        if User.objects.filter(username=username).exists():
                            errors.append(f"Row {idx}: '{email}' already has an account")
                            error_count += 1
                            continue

                        if User.objects.filter(email=email).exists():
                            errors.append(f"Row {idx}: Email '{email}' already in use")
                            error_count += 1
                            continue

                        # Split full_name → first_name / last_name (mirrors add_user)
                        name_parts = full_name.split()
                        first_name = name_parts[0] if name_parts else ''
                        last_name  = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

                        # ── Create Django User ────────────────────────────
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            password=password,
                            first_name=first_name,
                            last_name=last_name,
                            is_staff=(import_type == 'teacher'),
                        )

                        # ── Student path ──────────────────────────────────
                        if import_type == 'student':
                            grade_name = _safe_str(row.get('grade', ''))
                            division   = _safe_str(row.get('division', ''))

                            if not grade_name or not division:
                                raise ValueError(
                                    "Grade and Division are required for students"
                                )

                            grade_num = None
                            try:
                                grade_num = int(grade_name)
                            except (ValueError, TypeError):
                                pass

                            UserProfile.objects.create(
                                user=user,
                                role='student',
                                school=school,
                                grade=grade_num,
                                division=division,
                            )

                            roll_number  = _safe_str(row.get('roll_number', ''))
                            admission_id = _safe_str(row.get('admission_id', ''))

                            grade_obj, _ = Grade.objects.get_or_create(name=grade_name)

                            if not roll_number:
                                roll_number = _next_roll(school, grade_obj, division)
                            if not admission_id:
                                admission_id = _next_admission_id(school)

                            Student.objects.create(
                                user=user,
                                school=school,
                                full_name=full_name,
                                roll_number=roll_number,
                                admission_id=admission_id,
                                grade=grade_obj,
                                section=division,
                                created_by=request.user,
                            )

                        # ── Teacher path ──────────────────────────────────
                        else:
                            profile_obj = UserProfile.objects.create(
                                user=user,
                                role='teacher',
                                school=school,
                            )
                            subject = _safe_str(row.get('subject', ''))
                            if subject:
                                profile_obj.subject = subject
                                profile_obj.save()

                        success_count += 1

                    except Exception as e:
                        errors.append(f"Row {idx}: {e}")
                        error_count += 1

            # Clear session data
            request.session.pop('import_data', None)
            request.session.pop('import_type', None)

            role_label = 'student' if import_type == 'student' else 'teacher'
            if success_count:
                messages.success(
                    request,
                    f"Successfully imported {success_count} {role_label}(s)."
                )
            if error_count:
                messages.warning(request, f"{error_count} row(s) had errors (see below).")
                for err in errors[:10]:
                    messages.error(request, err)

            return redirect('manage_users')

    return render(request, 'teacher/bulk_import_users.html', {
        'is_school_admin': is_school_admin,
    })


# ── Template downloads ────────────────────────────────────────────────────────

@login_required
def download_student_template(request):
    """Download CSV template for student bulk import.

    Columns match the individual Add User form (student) exactly:
      full_name, email, password, grade, division, roll_number, admission_id
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=student_import_template.csv'

    writer = csv.writer(response)
    writer.writerow(['full_name', 'email', 'password', 'grade', 'division', 'roll_number', 'admission_id'])
    writer.writerow(['Alice Johnson',  'alice.johnson@school.com',  'Pass@1234', 'AS Level', 'A', '', ''])
    writer.writerow(['Bob Williams',   'bob.williams@school.com',   'Pass@1234', 'AS Level', 'A', '', ''])
    writer.writerow(['Charlie Brown',  'charlie.brown@school.com',  'Pass@1234', 'A Level',  'B', '3', 'ADM2024003'])

    return response


@login_required
def download_teacher_template(request):
    """Download CSV template for teacher bulk import.

    Columns match the individual Add User form (teacher) exactly:
      full_name, email, password, subject
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=teacher_import_template.csv'

    writer = csv.writer(response)
    writer.writerow(['full_name', 'email', 'password', 'subject'])
    writer.writerow(['John Peterson', 'john.peterson@school.com', 'Teach@123', 'Physics'])
    writer.writerow(['Mary Chen',     'mary.chen@school.com',     'Teach@123', 'Chemistry'])
    writer.writerow(['Sarah Davis',   'sarah.davis@school.com',   'Teach@123', ''])

    return response


@login_required
def download_user_template(request):
    """Legacy endpoint — redirects to the student template."""
    return download_student_template(request)
