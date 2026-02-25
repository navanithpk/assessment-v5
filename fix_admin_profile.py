#!/usr/bin/env python
"""Fix admin user profile"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assessment_v3.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile, School

# Get or create school
school, created = School.objects.get_or_create(
    code='DEFAULT',
    defaults={
        'name': 'My School',
        'address': '',
        'phone': '',
        'email': ''
    }
)

if created:
    print(f'Created school: {school.name}')
else:
    print(f'Using existing school: {school.name}')

# Fix sis_admin user
try:
    user = User.objects.get(username='sis_admin')

    # Check if profile exists
    try:
        profile = user.profile
        print(f'Profile already exists for {user.username}')
        print(f'  Role: {profile.role}')
        print(f'  School: {profile.school}')
    except UserProfile.DoesNotExist:
        # Create profile
        profile = UserProfile.objects.create(
            user=user,
            role='school_admin',
            school=school
        )
        user.is_staff = True
        user.save()
        print(f'Created profile for {user.username}')
        print(f'  Role: {profile.role}')
        print(f'  School: {profile.school}')

except User.DoesNotExist:
    print('User sis_admin does not exist')
