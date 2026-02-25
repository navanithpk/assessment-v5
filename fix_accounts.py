#!/usr/bin/env python
"""Fix admin permissions and student account"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assessment_v3.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile, School, Student

# Get the school
school = School.objects.first()
print(f'Using school: {school.name}\n')

# Fix sis_admin - ensure they have proper admin permissions
print('=== Fixing sis_admin account ===')
try:
    admin_user = User.objects.get(username='sis_admin')
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.save()

    # Update profile
    profile = admin_user.profile
    profile.role = 'school_admin'
    profile.school = school
    profile.save()

    print(f'[OK] Fixed sis_admin')
    print(f'  - is_superuser: {admin_user.is_superuser}')
    print(f'  - is_staff: {admin_user.is_staff}')
    print(f'  - Profile role: {profile.role}')
    print(f'  - School: {profile.school}')
except User.DoesNotExist:
    print('[ERROR] sis_admin not found')

print()

# Fix student account new10@gmail.com
print('=== Fixing new10@gmail.com student account ===')
try:
    student_user = User.objects.get(email='new10@gmail.com')

    # Reset password
    student_user.set_password('TestMaker')
    student_user.is_active = True
    student_user.save()

    print(f'[OK] Fixed student account: {student_user.username}')
    print(f'  - Email: {student_user.email}')
    print(f'  - Password: TestMaker (reset)')
    print(f'  - is_active: {student_user.is_active}')

    # Check/create profile
    try:
        profile = student_user.profile
        print(f'  - Profile role: {profile.role}')
        print(f'  - School: {profile.school}')
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(
            user=student_user,
            role='student',
            school=school
        )
        print(f'  - Created profile with role: {profile.role}')

    # Check Student record
    try:
        student_record = Student.objects.get(user=student_user)
        print(f'  - Student record exists')
        print(f'  - Full name: {student_record.full_name}')
    except Student.DoesNotExist:
        print(f'  - No Student record (optional)')

except User.DoesNotExist:
    print('[ERROR] Student with email new10@gmail.com not found')
    print('\nSearching for similar accounts...')
    students = User.objects.filter(email__icontains='new10')
    if students.exists():
        for s in students:
            print(f'  Found: {s.username} ({s.email})')
    else:
        print('  No similar accounts found')

print('\n=== All Users in System ===')
for user in User.objects.all():
    try:
        role = user.profile.role
    except:
        role = 'NO PROFILE'
    print(f'{user.username:20} | {user.email:30} | {role:15} | Active: {user.is_active}')
