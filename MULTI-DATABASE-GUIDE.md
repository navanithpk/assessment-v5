# Multi-Database Architecture Guide

## Overview

This system supports **separate database files for each subject-grade combination**. This means:
- **9702 (AS & A Level Physics)** questions → `9702.db`
- **0625 (IGCSE Physics)** questions → `0625.db`
- **JEE Physics** questions → `jee-phys.db`

This architecture provides:
✅ **Modularity** - Each subject is completely isolated
✅ **Portability** - Share question banks as single files
✅ **Performance** - Smaller, faster databases
✅ **Scalability** - Add subjects without affecting existing ones

---

## Quick Start

### Step 1: Clear Existing Data

```bash
# Clear all users and questions (keeps structure)
python manage.py clear_database

# Or clear only users
python manage.py clear_database --users-only

# Or clear only questions
python manage.py clear_database --questions-only
```

**What this does:**
- ✅ Deletes all users (except superusers)
- ✅ Deletes all students
- ✅ Deletes all questions
- ✅ Deletes all tests
- ✅ Deletes all answers
- ❌ KEEPS: Schools, Subjects, Grades, Topics, LOs, Combinations, Question Banks

### Step 2: Set Up Question Databases

```bash
# Create database files for all active combinations
python manage.py setup_question_databases --create-all
```

**What this creates:**
```
question_databases/
├── 0610.db          # IGCSE Biology
├── 0620.db          # IGCSE Chemistry
├── 0625.db          # IGCSE Physics
├── 9700.db          # AS & A Level Biology
├── 9701.db          # AS & A Level Chemistry
├── 9702.db          # AS & A Level Physics
├── 9700-as.db       # AS Level Biology
├── 9701-as.db       # AS Level Chemistry
├── 9702-as.db       # AS Level Physics
├── 9700-a.db        # A Level Biology
├── 9701-a.db        # A Level Chemistry
└── 9702-a.db        # A Level Physics
```

### Step 3: Start Adding Questions

Questions will now be automatically stored in their respective database files based on subject-grade combination.

---

## Management Commands

### clear_database

**Purpose:** Clean the database of user and question data

**Usage:**
```bash
# Interactive mode (prompts for confirmation)
python manage.py clear_database

# Skip confirmation
python manage.py clear_database --confirm

# Delete only users
python manage.py clear_database --users-only --confirm

# Delete only questions
python manage.py clear_database --questions-only --confirm
```

**What gets deleted:**
- Users (except superusers)
- Students
- UserProfiles
- Questions
- Tests
- TestQuestions
- StudentAnswers
- ClassGroups
- PDFImportSessions
- ProcessedPDFs

**What is preserved:**
- Schools
- Subjects
- Grades
- Topics
- LearningObjectives
- SubjectGradeCombinations
- QuestionBanks
- Superuser accounts

---

### setup_question_databases

**Purpose:** Create separate database files for question banks

**Usage:**
```bash
# Show current status
python manage.py setup_question_databases

# Create all databases
python manage.py setup_question_databases --create-all

# Create specific database
python manage.py setup_question_databases --combination 9702
```

**What it does:**
1. Creates `question_databases/` directory
2. Creates SQLite file for each combination
3. Updates QuestionBank records with database file paths
4. Shows status of all combinations

**Output example:**
```
📦 Question Bank Database Setup
============================================================

✅ Created directory: question_databases/

📦 9702 - AS & A Level Physics
   ✅ Created: 9702.db
   ✅ Updated 1 QuestionBank record(s)

📦 0625 - IGCSE Physics
   ✅ Created: 0625.db
   ℹ️  No QuestionBank created yet for this combination

============================================================
✅ Setup Complete!
============================================================
```

---

## Database Architecture

### Main Database (`db.sqlite3`)

Stores:
- Schools
- Users, UserProfiles, Students
- Subjects, Grades, Topics, LearningObjectives
- SubjectGradeCombinations
- QuestionBanks (metadata only)
- Tests, ClassGroups

### Question Databases (`question_databases/*.db`)

Each file stores:
- Questions for that specific subject-grade
- TestQuestions linking to those questions
- StudentAnswers for those questions

**Example:**
```
9702.db contains:
- Question: "Explain Newton's First Law..." (9702 Physics)
- Question: "Calculate the momentum of..." (9702 Physics)
- StudentAnswer: John's answer to physics question
```

---

## Directory Structure

```
assessment-v3/
├── db.sqlite3                    # Main database
├── question_databases/           # Question bank databases
│   ├── 0610.db                  # IGCSE Biology
│   ├── 0620.db                  # IGCSE Chemistry
│   ├── 0625.db                  # IGCSE Physics
│   ├── 9700.db                  # AS & A Level Biology
│   ├── 9701.db                  # AS & A Level Chemistry
│   ├── 9702.db                  # AS & A Level Physics
│   └── jee-phys.db              # JEE Physics (if added)
├── core/
│   ├── db_router.py             # Database routing logic
│   └── management/commands/
│       ├── clear_database.py
│       └── setup_question_databases.py
└── ...
```

---

## How It Works

### 1. Database Router

The `QuestionBankRouter` (in `core/db_router.py`) automatically routes:
- **Question reads** → Correct question database
- **Question writes** → Correct question database
- **All other operations** → Main database

### 2. QuestionBank Model

Each `QuestionBank` has a `database_file` field:
```python
database_file = "question_databases/9702.db"
```

When you create/read questions through a QuestionBank, the router uses this path.

### 3. Automatic Routing

```python
# This question goes to 9702.db
physics_bank = QuestionBank.objects.get(subject__code='9702')
question = Question.objects.create(
    subject=physics_bank.subject,
    grade=physics_bank.grade,
    question_text="...",
    question_type="mcq"
)
```

---

## Benefits

### 1. Modularity
- Each subject is completely isolated
- No cross-contamination between subjects
- Easy to backup individual subjects

### 2. Portability
- Share `9702.db` with another school
- Import question banks as single files
- Distribute DLCs as database files

### 3. Performance
- Smaller databases = faster queries
- No need to filter by subject every time
- Reduced index sizes

### 4. Scalability
- Add unlimited subjects without slowdown
- Each database stays manageable size
- No single database bottleneck

### 5. Organization
- Clear separation by curriculum
- Easy to see what's installed
- Simple to manage storage

---

## Use Cases

### Use Case 1: Starting Fresh

```bash
# 1. Clear everything
python manage.py clear_database --confirm

# 2. Set up databases
python manage.py setup_question_databases --create-all

# 3. Bulk import users
# Go to: http://localhost:8000/teacher/users/bulk-import/

# 4. Create question banks and activate them
# Go to: http://localhost:8000/teacher/dlc/

# 5. Start adding questions!
```

### Use Case 2: Add New Subject (JEE Physics)

```bash
# 1. Add combination
# Go to: http://localhost:8000/teacher/subject-grade-combinations/add/
# Code: JEE-PHYS, Name: JEE Physics, Level: JEE

# 2. Create database
python manage.py setup_question_databases --combination JEE-PHYS

# 3. Create and activate question bank
# Go to: http://localhost:8000/teacher/dlc/

# 4. Add questions (they go to jee-phys.db automatically)
```

### Use Case 3: Share Question Bank

```bash
# On School A:
# 1. Copy 9702.db to USB drive
# 2. Share with School B

# On School B:
# 1. Copy 9702.db to question_databases/
# 2. Create QuestionBank record pointing to this file
# 3. Activate the question bank
# 4. All 9702 questions are now available!
```

### Use Case 4: Backup Specific Subject

```bash
# Backup only Physics questions
cp question_databases/9702.db backups/9702_backup_2026-02-01.db

# Restore if needed
cp backups/9702_backup_2026-02-01.db question_databases/9702.db
```

---

## Future Enhancements

The system is designed to support:

### 1. Import/Export DLCs
```bash
python manage.py export_dlc --combination 9702 --output 9702_export.zip
python manage.py import_dlc --file 9702_export.zip
```

### 2. DLC Marketplace
- Download pre-made question banks
- Share with other schools
- Version control for question banks

### 3. Cloud Sync
- Sync specific databases to cloud
- Collaborative question editing
- Backup to Google Drive/Dropbox

### 4. Migration Tools
```bash
# Migrate questions from main DB to separate DBs
python manage.py migrate_questions_to_dlc --combination 9702

# Merge two databases
python manage.py merge_dlcs --from 9702-as.db --to 9702.db
```

---

## Troubleshooting

### Problem: "Database file not found"
**Solution:**
```bash
python manage.py setup_question_databases --create-all
```

### Problem: "Questions not showing up"
**Solution:**
1. Check if QuestionBank is activated
2. Verify database_file path in QuestionBank
3. Ensure database file exists in question_databases/

### Problem: "Permission denied on database file"
**Solution:**
```bash
# Windows
icacls question_databases\*.db /grant Users:F

# Linux/Mac
chmod 644 question_databases/*.db
```

### Problem: "Want to move existing questions to new structure"
**Solution:**
Coming soon - migration tool will handle this automatically

---

## Best Practices

### 1. Backup Strategy
- **Daily**: Backup main database (db.sqlite3)
- **Weekly**: Backup all question databases
- **Before import**: Backup specific subject database

### 2. Naming Conventions
- Use official codes: `9702.db`, `0625.db`
- Lowercase filenames: `jee-phys.db`, not `JEE-PHYS.db`
- Consistent format: `code.db`

### 3. Testing
- Test on a single subject first
- Verify questions appear correctly
- Test student access
- Check grading functionality

### 4. Organization
- Create question banks for all subjects upfront
- Activate only what you need
- Deactivate unused subjects

---

## Technical Details

### Database Routing Logic

```python
# When creating a question:
QuestionBankRouter checks:
1. Is this a Question model?
2. Is there a question_bank hint?
3. Does the bank have a database_file?
4. Route to that database
5. Otherwise, use main database
```

### Model Relationships

```
Main Database:
- School → Users
- Subject → QuestionBank (metadata)
- QuestionBank.database_file = "question_databases/9702.db"

9702.db:
- Questions (subject=9702 Physics)
- TestQuestions
- StudentAnswers
```

### File Permissions

Database files should be:
- **Readable**: By web server user
- **Writable**: By web server user
- **Not executable**: Security best practice

```bash
# Set correct permissions (Linux/Mac)
chmod 644 question_databases/*.db
chown www-data:www-data question_databases/*.db
```

---

## Migration from Single Database

If you have existing questions in the main database:

```bash
# Step 1: Backup everything
cp db.sqlite3 db.sqlite3.backup

# Step 2: Set up new structure
python manage.py setup_question_databases --create-all

# Step 3: Migration tool (coming soon)
python manage.py migrate_questions_to_dlc --all

# Step 4: Verify migration
python manage.py verify_question_migration

# Step 5: Clean old questions (optional)
python manage.py clear_database --questions-only --confirm
```

---

## Summary

✅ **Separate database per subject** - Clean isolation
✅ **Easy management** - Simple commands
✅ **Portable** - Share as files
✅ **Scalable** - Add unlimited subjects
✅ **Performant** - Smaller, faster databases

**Ready to use!** Start by clearing your database and setting up the new structure.

---

**Last Updated**: 2026-02-01
**Version**: 3.0 Multi-Database Architecture
