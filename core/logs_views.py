"""
Views for AI Tagging Logs
"""
import os
import re
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required


@login_required
@staff_member_required
def ai_tagging_logs(request):
    """Display list of AI tagging log files"""

    logs_dir = 'logs'
    log_files = []

    if os.path.exists(logs_dir):
        for filename in os.listdir(logs_dir):
            if filename.startswith('ai_tagging_') and filename.endswith('.log'):
                filepath = os.path.join(logs_dir, filename)
                # Extract date from filename: ai_tagging_20260125_143022.log
                date_match = re.search(r'(\d{8})_(\d{6})', filename)
                if date_match:
                    date_str = date_match.group(1)
                    time_str = date_match.group(2)
                    dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
                    display_date = dt.strftime("%d-%m-%Y %H:%M:%S")
                else:
                    display_date = "Unknown date"

                log_files.append({
                    'name': filename,
                    'display_name': filename,
                    'date': display_date,
                    'path': filepath
                })

    # Sort by date, newest first
    log_files.sort(key=lambda x: x['date'], reverse=True)

    context = {
        'log_files': log_files
    }

    return render(request, 'teacher/ai_tagging_logs.html', context)


@login_required
@staff_member_required
def view_log_file(request, filename):
    """Return log file contents as JSON"""

    # Security: only allow log files from logs directory
    if not filename.startswith('ai_tagging_') or not filename.endswith('.log'):
        return JsonResponse({'error': 'Invalid log file'}, status=400)

    filepath = os.path.join('logs', filename)

    if not os.path.exists(filepath):
        return JsonResponse({'error': 'Log file not found'}, status=404)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        parsed_lines = []
        for line in lines:
            parsed = parse_log_line(line)
            parsed_lines.append(parsed)

        return JsonResponse({
            'success': True,
            'filename': filename,
            'lines': parsed_lines,
            'total_lines': len(parsed_lines)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def parse_log_line(line):
    """Parse a log line into components"""

    # Example format: 2026-01-25 14:30:22,123 - INFO - Processing Question 42
    pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}),\d+ - (\w+) - (.+)'
    match = re.match(pattern, line)

    if match:
        return {
            'timestamp': match.group(1),
            'level': match.group(2),
            'message': match.group(3),
            'raw': line.strip()
        }
    else:
        return {
            'timestamp': '',
            'level': '',
            'message': line.strip(),
            'raw': line.strip()
        }
