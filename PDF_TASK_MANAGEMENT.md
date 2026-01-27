# PDF Task Management System

## Overview

The PDF Task Management system allows teachers to track their PDF import sessions across multiple login-logout sessions. Tasks are persisted in the database and can be resumed, paused, completed, or deleted.

## Features

### 1. Task Persistence
- All PDF import sessions are saved to the database
- Information persists across login-logout sessions
- Tasks can be resumed from where you left off

### 2. Duplicate Detection
- SHA-256 hash-based duplicate detection
- Prevents accidentally processing the same PDF twice
- Shows when/who processed a duplicate file

### 3. Status Management

Tasks can be in one of four states:

- **Pending**: Created but not yet started
- **In Progress**: Currently being worked on
- **Paused**: Temporarily stopped, can be resumed
- **Completed**: Finished processing

### 4. Progress Tracking

Each task shows:
- Number of files processed vs. total files
- Progress percentage with visual progress bar
- Creation/update timestamps
- Grade, subject, and year metadata

## User Interface

### Accessing the Task List

Navigate to: **Teacher Dashboard → PDF Import Tasks** (in sidebar)

Or directly: `/teacher/pdf-tasks/`

### Task Dashboard Layout

The dashboard is organized into sections:

1. **Pending Tasks** - Tasks waiting to be started
2. **In Progress** - Currently active tasks
3. **Paused Tasks** - Tasks temporarily halted
4. **Recently Completed** - Last 10 completed tasks

### Available Actions

**For Pending Tasks:**
- ▶️ Resume - Continue working on the task
- ✅ Mark Complete - Mark as finished
- 🗑️ Delete - Remove the task

**For In Progress Tasks:**
- ▶️ Continue - Keep working
- ⏸️ Pause - Temporarily stop
- ✅ Complete - Mark as finished

**For Paused Tasks:**
- ▶️ Resume - Continue from where you left off
- 🗑️ Delete - Remove the task

**For Completed Tasks:**
- 🗑️ Remove - Delete from the list

## How It Works

### When Creating a New PDF Import Session

1. Upload PDFs in the import interface
2. A new `PDFImportSession` is automatically created
3. Session stores:
   - Grade, subject, year
   - List of uploaded files
   - Processing status for each file
   - Slicing configuration data

### Task State Transitions

```
pending → in_progress → completed
    ↓           ↓
    ↓        paused
    ↓           ↓
    └─────→ deleted
```

### Duplicate Detection Process

When a PDF is uploaded:

1. System calculates SHA-256 hash of file content
2. Checks `ProcessedPDF` table for matching hash
3. If duplicate found:
   - Shows when it was processed
   - Shows who processed it
   - Shows how many questions were created
   - Asks for confirmation to process again

4. If not duplicate:
   - Proceeds with normal processing
   - Marks as processed after completion

## Database Models

### PDFImportSession

Tracks the overall import session:

```python
- created_by (User)
- grade (ForeignKey)
- subject (ForeignKey)
- year (Integer)
- session_name (String)
- total_files (Integer)
- processed_files (Integer)
- status (Choice: pending/in_progress/paused/completed)
- files_data (JSON)
- slicing_data (JSON)
- created_at (DateTime)
- updated_at (DateTime)
- completed_at (DateTime)
```

### ProcessedPDF

Tracks individual processed PDFs:

```python
- file_name (String)
- file_hash (String, unique) - SHA-256
- processed_by (User)
- grade (ForeignKey)
- subject (ForeignKey)
- year (Integer)
- questions_created (Integer)
- processed_at (DateTime)
```

## API Endpoints

### Task Management

- `GET /teacher/pdf-tasks/` - Task list dashboard
- `POST /teacher/pdf-tasks/check-duplicate/` - Check if PDF is duplicate
- `POST /teacher/pdf-tasks/mark-processed/` - Mark PDF as processed
- `POST /teacher/pdf-tasks/<id>/delete/` - Delete task
- `POST /teacher/pdf-tasks/<id>/complete/` - Mark task complete
- `POST /teacher/pdf-tasks/<id>/pause/` - Pause task
- `POST /teacher/pdf-tasks/<id>/resume/` - Resume task

## Usage Examples

### Resuming an Interrupted Session

1. Go to **PDF Import Tasks** in sidebar
2. Find your paused/pending task
3. Click **▶️ Resume**
4. Continue from where you left off

### Checking for Duplicates

The system automatically checks for duplicates when you upload PDFs. If a duplicate is detected, you'll see:

```
⚠️ This PDF has already been processed

Processed on: 2026-01-25 14:30
Processed by: teacher@example.com
Questions created: 25
Grade: A-Level
Subject: Biology
Year: 2024

Do you want to process it again?
```

### Cleaning Up Completed Tasks

1. Go to **PDF Import Tasks**
2. Scroll to **Recently Completed** section
3. Click **🗑️ Remove** on tasks you want to delete

## Best Practices

1. **Session Names**: Use descriptive names like "Biology A-Level 2024 Papers 1-5"
2. **Regular Cleanup**: Delete completed tasks periodically to keep the list manageable
3. **Pause Long Sessions**: If processing many PDFs, use Pause to take breaks
4. **Check Progress**: Monitor the progress bars to see how much is left
5. **Avoid Duplicates**: The system will warn you, but check file names before uploading

## Technical Notes

### Session Data Storage

Tasks use JSONField to store flexible metadata:

**files_data** stores array of file objects:
```json
[
  {
    "qp_name": "Biology_2024_P1_QP.pdf",
    "ms_name": "Biology_2024_P1_MS.pdf",
    "processed": false,
    "question_ids": []
  }
]
```

**slicing_data** stores slicing configuration:
```json
{
  "0": {
    "linesByPage": {...},
    "settings": {...}
  }
}
```

### SHA-256 Hashing

File hashes are calculated on the binary content of PDFs:

```python
import hashlib
file_hash = hashlib.sha256(file_bytes).hexdigest()
```

This ensures:
- Identical files have the same hash
- Different files have different hashes (with very high probability)
- Fast duplicate detection via database index

## Troubleshooting

### Task Not Showing Up

- Check you're logged in as the user who created the task
- Verify the task wasn't deleted
- Check the correct status section (Pending/In Progress/Paused/Completed)

### Can't Resume Task

- Ensure the task status is 'pending' or 'paused'
- Check that you have permission to access the task
- Verify the session data is valid

### Duplicate Detection Not Working

- Ensure the file content is exactly the same (not just the name)
- Check that ProcessedPDF records exist in the database
- Verify the hash is being calculated correctly

## Future Enhancements

Planned improvements:

1. **Batch Operations**: Select multiple tasks for bulk actions
2. **Search/Filter**: Find tasks by grade, subject, date range
3. **Export Reports**: Download task completion reports
4. **Notifications**: Email alerts when long tasks complete
5. **Archive**: Archive old tasks instead of deleting
6. **Collaboration**: Share tasks with other teachers
7. **Auto-Resume**: Option to auto-resume interrupted tasks on login

---

**Last Updated**: January 25, 2026
**Version**: Lumen v3.1
