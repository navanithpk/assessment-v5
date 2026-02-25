# Database Cleanup & Multi-Database Setup

## 🗑️ Quick Cleanup Commands

### Clear Everything (Users + Questions)
```bash
python manage.py clear_database --confirm
```

### Clear Only Users
```bash
python manage.py clear_database --users-only --confirm
```

### Clear Only Questions
```bash
python manage.py clear_database --questions-only --confirm
```

---

## 📦 Set Up Separate Question Databases

### Create All Databases
```bash
python manage.py setup_question_databases --create-all
```

This creates:
```
question_databases/
├── 0610.db    # IGCSE Biology
├── 0620.db    # IGCSE Chemistry
├── 0625.db    # IGCSE Physics
├── 9700.db    # AS & A Level Biology
├── 9701.db    # AS & A Level Chemistry
├── 9702.db    # AS & A Level Physics
└── ... (6 more files)
```

### Create Specific Database
```bash
python manage.py setup_question_databases --combination 9702
```

### Check Status
```bash
python manage.py setup_question_databases
```

---

## ✅ Complete Workflow (Start Fresh)

```bash
# Step 1: Clear all data
python manage.py clear_database --confirm

# Step 2: Set up question databases
python manage.py setup_question_databases --create-all

# Step 3: Done! Now you can:
# - Bulk import users from Excel
# - Create question banks via web interface
# - Add questions (they go to separate DBs automatically)
```

---

## 📊 What Gets Deleted?

### ✅ Deleted:
- All users (except superusers)
- All students
- All questions
- All tests
- All answers
- All class groups
- All PDF import sessions

### ❌ Preserved:
- Schools
- Subjects
- Grades
- Topics
- Learning Objectives
- Subject-Grade Combinations (12 pre-loaded)
- Question Banks (metadata)
- Superuser accounts

---

## 🎯 Common Scenarios

### Scenario 1: "I want a clean start"
```bash
python manage.py clear_database --confirm
python manage.py setup_question_databases --create-all
```

### Scenario 2: "Keep questions, reset users"
```bash
python manage.py clear_database --users-only --confirm
```

### Scenario 3: "Keep users, reset questions"
```bash
python manage.py clear_database --questions-only --confirm
python manage.py setup_question_databases --create-all
```

### Scenario 4: "Add new subject (JEE)"
```bash
# 1. Add combination via web: /teacher/subject-grade-combinations/add/
# 2. Create database:
python manage.py setup_question_databases --combination JEE-PHYS
```

---

## 🔍 Verification

### Check What Remains
```bash
python manage.py clear_database --confirm
# Shows counts at the end:
# - Schools: X
# - Subjects: X
# - Grades: X
# - Combinations: 12
# - Superusers: X
```

### Check Database Status
```bash
python manage.py setup_question_databases
# Shows:
# ✅ 9702    AS & A Level Physics    (Banks: 1)
# ❌ 0625    IGCSE Physics           (Banks: 0)
```

---

## ⚠️ Safety Notes

1. **Interactive Mode**: By default, `clear_database` asks for confirmation
2. **Type "DELETE"**: Must type exactly "DELETE" (uppercase) to confirm
3. **Skip Confirmation**: Use `--confirm` flag to skip prompt
4. **Backup First**: Always backup `db.sqlite3` before clearing

### Backup Command
```bash
# Windows
copy db.sqlite3 db.sqlite3.backup

# Linux/Mac
cp db.sqlite3 db.sqlite3.backup
```

---

## 📚 Full Documentation

For detailed information, see:
- **MULTI-DATABASE-GUIDE.md** - Complete architecture guide
- **FEATURES-GUIDE.md** - New features documentation
- **QUICK-START.md** - Getting started guide

---

## 🚀 Next Steps After Cleanup

1. **Import Users**
   - Go to: http://localhost:8000/teacher/users/bulk-import/
   - Download template
   - Fill and upload

2. **Create Question Banks**
   - Go to: http://localhost:8000/teacher/dlc/
   - Create banks for each subject
   - Activate them

3. **Add Questions**
   - Questions automatically go to correct database
   - Each subject isolated in its own .db file

---

**Quick Reference Card - Keep This Handy!**

| Command | Purpose |
|---------|---------|
| `clear_database` | Delete users/questions |
| `clear_database --users-only` | Delete only users |
| `clear_database --questions-only` | Delete only questions |
| `setup_question_databases --create-all` | Create all databases |
| `setup_question_databases --combination CODE` | Create one database |
| `setup_question_databases` | Show status |

**Last Updated**: 2026-02-01
