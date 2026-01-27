#!/usr/bin/env python
"""
One-time script to create superuser on Railway
Run this after deployment: railway run python create_admin.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assessment_v3.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = 'admin'
email = 'admin@example.com'
password = 'admin123'  # Change this!

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'✅ Superuser created: {username} / {password}')
    print('⚠️ Please change the password after first login!')
else:
    print(f'❌ User {username} already exists')
