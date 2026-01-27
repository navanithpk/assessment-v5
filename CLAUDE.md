# CLAUDE.MD - Assessment Platform v3

## Project Overview

This is an **Educational Assessment Platform** built with Django that enables schools to create and administer tests to students, manage user accounts, and track student performance. The system implements multi-tenant architecture where each school has isolated data.

**Current Status**: Active development with recent improvements to test creation and user management features.

---

## Technology Stack

- **Framework**: Django 4.2
- **Language**: Python 3.x
- **Database**: SQLite3 (development)
- **Additional Libraries**: pandas, PyMuPDF

---

## Project Structure

```
assessment-v3/
├── assessment_v3/          # Django project settings
│   ├── settings.py         # Main configuration
│   ├── urls.py             # Root URL routing
│   ├── wsgi.py & asgi.py   # Server interfaces
├── core/                   # Main application
│   ├── models.py           # 14 database models
│   ├── views.py            # 30+ view functions
│   ├── pdf_tasks_views.py  # PDF task management (7 views)
│   ├── analytics_views.py  # Analytics dashboards (3 views)
│   ├── urls.py             # App routing
│   ├── admin.py            # Admin configuration
│   ├── management/         # Custom commands
│   │   ├── create_school_admin.py
│   │   └── import_los.py   # Learning objectives importer
│   ├── migrations/         # Database migrations
│   ├── templates/          # HTML templates
│   │   ├── registration/   # Login
│   │   ├── teacher/        # Teacher UI
│   │   ├── admin_panel/    # Admin dashboard
│   │   └── student/        # Student UI
│   └── tests.py
├── static/                 # Static assets
├── db.sqlite3              # SQLite database
└── manage.py
```

---

## Database Models

### Academic Hierarchy
- **School** - Organization unit (name, code, address, phone, email)
- **Grade** - Academic levels (e.g., 9, 10, 11, 12)
- **Subject** - Subject domains (Biology, Chemistry, Physics, etc.)
- **Topic** - Specific topics within subject/grade
- **LearningObjective** - Granular learning outcomes with codes

### User Management
- **User** - Django's built-in auth (extended)
- **UserProfile** - Role-based extension (student/teacher/school_admin)
- **Student** - Student records with academic details (roll_number, admission_id)
- **ClassGroup** - Student groupings for bulk operations

### Assessment System
- **Question** - Question bank with 4 types:
  - MCQ
  - Theory
  - Structured
  - Practical
- **Test** - Assessment instances with 2 types:
  - Standard (question-bank based)
  - Descriptive (hierarchical JSON structure)
- **TestQuestion** - Join model with ordering
- **StudentAnswer** - Answer submissions with grading
- **PDFImportSession** - Tracks PDF import tasks with session persistence
- **ProcessedPDF** - Tracks processed PDFs with SHA-256 hash for duplicate detection

---

## Key Features

### 1. User Management
- Three user roles: Student, Teacher, School Admin
- Role-based dashboard routing
- School-based multi-tenancy
- Custom login with role detection

### 2. Test Management
- Create/edit/delete tests
- Two test types: Standard and Descriptive
- Question ordering and reuse from question bank
- Test publishing/unpublishing
- Test duplication
- Auto-save functionality
- Student assignment (individual or group-based)

### 3. Question Bank
- Full CRUD operations
- 4 question types supported
- Filtering by grade, subject, topic, marks, year
- Learning objective tagging
- Inline question creation during test building

### 4. Student Assessment
- View assigned tests
- Take tests with auto-save
- Submit answers
- View results and reviews

### 5. Real-Time Test Monitoring
- Live dashboard showing student progress during tests
- Real-time status updates (Not Started, In Progress, Submitted)
- Auto-refresh functionality (configurable interval)
- Progress bars and completion statistics
- Last activity timestamps for each student

### 6. Answer Grading & Evaluation
- Comprehensive grading interface
- Side-by-side view of model answers and student responses
- AI-assisted grading suggestions (placeholder for AI integration)
- Manual grade override capability
- Question-by-question evaluation
- Progress tracking (graded vs. pending)
- Results publishing system

### 7. Performance Analytics
- Class performance tracking
- Student performance views
- Individual student score summaries

### 8. PDF Task Management (NEW)
- Track PDF import sessions across login-logout sessions
- Resume interrupted imports from where you left off
- Duplicate PDF detection using SHA-256 hashing
- Progress tracking with visual progress bars
- Task status management (pending/in_progress/paused/completed)
- Session persistence with JSON metadata storage

### 9. Startup Automation (NEW)
- One-click startup script for all services
- Automated launch sequence: LM Studio → ngrok → Django
- Proper timing delays between service starts
- Error handling and user feedback

### 10. Data Import
- Excel import for Learning Objectives
- Management command: `python manage.py import_los <file.xlsx>`
- PDF import with question slicing
- Year field persistence in imported questions

---

## Important URL Patterns

| Endpoint | Purpose |
|----------|---------|
| `/` | Root redirect (role-based) |
| `/accounts/login/` | Login page |
| `/teacher/` | Teacher dashboard |
| `/student/dashboard/` | Student dashboard |
| `/teacher/tests/` | Test list |
| `/teacher/tests/create/` | Create test |
| `/teacher/tests/<id>/edit/` | Edit test |
| `/teacher/tests/<id>/monitor/` | **NEW** Real-time test monitoring |
| `/teacher/tests/<id>/grade/` | **NEW** Grade student answers |
| `/teacher/pdf-tasks/` | **NEW** PDF task management dashboard |
| `/teacher/analytics/` | **NEW** Teacher analytics dashboard |
| `/student/analytics/` | **NEW** Student analytics dashboard |
| `/teacher/users/add/` | Add user account |
| `/teacher/users/manage/` | Manage users |
| `/student/tests/<id>/take/` | Take test |
| `/questions/` | Question library |
| `/teacher/groups/` | Manage class groups |

---

## Recent Git History

- **49c3e36**: "Massive improvement - Tests"
- **0d5fa99**: "Some new changes - added facility for nested(descriptive) tests"
- **5570257**: "Things work fine, except for the create-test"
- **13dc824**: "The student and Teacher account adding view works now!"
- **8b7dee3**: "broken view-users and view-student logic"

---

## Common Development Tasks

### Running the Server
```bash
python manage.py runserver
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Creating a School Admin
```bash
python manage.py create_school_admin
```

### Importing Learning Objectives
```bash
python manage.py import_los <excel_file_path>
```

### Access Django Admin
Navigate to `/admin/` and login with superuser credentials

---

## User Workflows

### Teacher Workflow
1. Login → Teacher dashboard
2. Create questions in question bank
3. Create test (standard or descriptive)
4. Assign test to students/groups
5. Publish test
6. **Monitor test in real-time** (new feature)
   - View live student progress
   - Track completion status
   - Monitor last activity
7. **Grade student answers** (new feature)
   - Review all submissions
   - Use AI-assisted grading
   - Manually adjust marks
   - Add feedback
8. Publish results to students
9. View performance analytics

### Student Workflow
1. Login → Student dashboard
2. View assigned tests
3. Take test (with auto-save)
4. Submit test
5. View results and reviews

### School Admin Workflow
1. Login → Admin dashboard
2. Manage teachers and students
3. Manage class groups
4. View school-wide analytics

---

## Data Relationships

```
School
  ├── Users (via UserProfile)
  │     ├── Teachers
  │     ├── Students (with Student model)
  │     └── School Admins
  │
  ├── ClassGroups → Students
  │
  ├── Tests
  │     ├── TestQuestions → Questions
  │     └── StudentAnswers
  │
  └── Questions
        ├── Grade, Subject, Topic
        └── LearningObjectives
```

---

## Development Notes

### Current Status
- **Environment**: Development (DEBUG=True)
- **Database**: SQLite3 (single file)
- **Modified Files**: db.sqlite3 (uncommitted changes)
- **Untracked Files**:
  - lolist_IGBio.xlsx
  - lolist_IGChem.xlsx
  - venv/ directories

### Security Considerations
- Default SECRET_KEY in use (needs environment variable in production)
- No ALLOWED_HOSTS configured (localhost only)
- SQLite suitable for development/small deployments only

### Multi-Tenancy
- School-based data isolation via ForeignKey filters
- Users scoped to their school context
- Staff flag automatically managed based on user role

---

## File Locations

### Templates by Role
- `core/templates/teacher/` - Teacher-specific pages (10+)
- `core/templates/student/` - Student pages (9 files)
- `core/templates/registration/` - Login page
- `core/templates/admin_panel/` - Admin dashboard

### Key Template Files
- `create_test.html` - Standard test builder
- `create_descriptive_test.html` - Hierarchical test builder
- `student_take_test.html` - Test-taking interface
- `manage_class_groups.html` - Group management
- `manage_teacher_student.html` - User management

---

## Testing

Tests are located in `core/tests.py`. Run with:
```bash
python manage.py test
```

---

## Known Issues & TODOs

Based on recent commits:
- ✅ Student/teacher account creation - Fixed
- ✅ Descriptive test support - Added
- 🔧 View-users and view-student logic - Under refinement
- 🔧 School-based filtering - Being improved

---

## Quick Reference

### Models Count
- 13 core models
- 10 database migrations

### Views Count
- 30+ view functions across teacher/student/admin roles

### Question Types
1. MCQ
2. Theory
3. Structured
4. Practical

### Test Types
1. Standard (question-bank based)
2. Descriptive (hierarchical structure)

### User Roles
1. Student
2. Teacher
3. School Admin

---

## Production Readiness Checklist

Before deploying to production:
- [ ] Set SECRET_KEY via environment variable
- [ ] Configure ALLOWED_HOSTS
- [ ] Switch to production database (PostgreSQL/MySQL)
- [ ] Set DEBUG=False
- [ ] Configure static file serving
- [ ] Set up proper logging
- [ ] Configure email backend
- [ ] Implement backup strategy
- [ ] Set up monitoring
- [ ] Review security settings

---

## Contact & Support

For questions about this codebase, refer to:
- Git history for recent changes
- Django admin at `/admin/`
- Template files for UI implementation details
- Models in `core/models.py` for data structure

---

**Last Updated**: 2026-01-24
**Project Branch**: main
