# New Features Guide - Assessment Platform v3

## Overview

This guide covers the new features added to the Assessment Platform:

1. **Subject-Grade Combinations** - Pre-configured curriculum codes (IGCSE, AS/A Level, JEE, SAT, CUET)
2. **Bulk User Import** - Import students and teachers from Excel files
3. **Question Bank DLCs** - Modular question databases for different subjects/exams

---

## 1. Subject-Grade Combinations

### What is it?

A system to manage standardized subject-grade combinations like:
- **0610** - IGCSE Biology
- **0620** - IGCSE Chemistry
- **0625** - IGCSE Physics
- **9700** - AS & A Level Biology
- **9701** - AS & A Level Chemistry
- **9702** - AS & A Level Physics

### How to Access

Navigate to: **Teacher Dashboard → Question Bank DLCs → Manage Combinations**

Or directly: `http://localhost:8000/teacher/subject-grade-combinations/`

### Pre-loaded Combinations

The system comes with 12 pre-configured combinations:

| Code | Name | Level |
|------|------|-------|
| 0610 | IGCSE Biology | IGCSE |
| 0620 | IGCSE Chemistry | IGCSE |
| 0625 | IGCSE Physics | IGCSE |
| 9700 | AS & A Level Biology | AS & A Level |
| 9701 | AS & A Level Chemistry | AS & A Level |
| 9702 | AS & A Level Physics | AS & A Level |
| 9700-AS | AS Level Biology | AS Level |
| 9701-AS | AS Level Chemistry | AS Level |
| 9702-AS | AS Level Physics | AS Level |
| 9700-A | A Level Biology | A Level |
| 9701-A | A Level Chemistry | A Level |
| 9702-A | A Level Physics | A Level |

### Adding New Combinations

1. Go to Subject-Grade Combinations page
2. Click "➕ Add New Combination"
3. Fill in the form:
   - **Code**: Unique identifier (e.g., "JEE-PHYS", "SAT-MATH")
   - **Name**: Descriptive name (e.g., "JEE Physics")
   - **Subject**: Select from existing subjects
   - **Grade**: Select from existing grades
   - **Level**: Choose curriculum level (IGCSE, AS/A Level, JEE, SAT, CUET)
   - **Description**: Optional notes
4. Click "✅ Create Combination"

### Use Cases

- **Standardized syllabus codes**: Easy identification of Cambridge IGCSE/AS/A Level subjects
- **Exam preparation modules**: Separate question banks for JEE, SAT, CUET
- **Multi-curriculum schools**: Manage different exam boards simultaneously

---

## 2. Bulk User Import

### What is it?

Import multiple students or teachers at once from an Excel file instead of creating them one by one.

### How to Access

Navigate to: **Teacher Dashboard → User Management → 📥 Bulk Import Users**

Or directly: `http://localhost:8000/teacher/users/bulk-import/`

### Step-by-Step Guide

#### Step 1: Download Template

1. Go to Bulk Import Users page
2. Click "📥 Download Template"
3. Excel file will download with two sheets:
   - **Students** sheet
   - **Teachers** sheet

#### Step 2: Fill Template

**For Students:**

| Column | Required | Example | Notes |
|--------|----------|---------|-------|
| username | ✅ | alice.johnson | Must be unique |
| email | ✅ | alice@school.com | Must be unique |
| password | ✅ | Pass@1234 | Initial password |
| first_name | ✅ | Alice | First name |
| last_name | ✅ | Johnson | Last name |
| role | ✅ | student | Must be "student" |
| full_name | ❌ | Alice Johnson | Display name |
| roll_number | ❌ | 2024001 | Roll number |
| admission_id | ❌ | ADM001 | Admission ID |
| grade | ❌ | AS Level | Grade/class |
| division | ❌ | A | Section |

**For Teachers:**

| Column | Required | Example | Notes |
|--------|----------|---------|-------|
| username | ✅ | john.physics | Must be unique |
| email | ✅ | john.p@school.com | Must be unique |
| password | ✅ | Teach@123 | Initial password |
| first_name | ✅ | John | First name |
| last_name | ✅ | Peterson | Last name |
| role | ✅ | teacher | Must be "teacher" |
| subject | ❌ | Physics | Subject taught |

#### Step 3: Upload File

1. Click "📤 Upload Excel File"
2. Select your filled template
3. Click "👁️ Preview Data"

#### Step 4: Review Preview

- System shows first 50 rows for verification
- Check for any errors in data
- Verify usernames and emails are correct

#### Step 5: Confirm Import

1. Click "✅ Confirm & Import X Users"
2. Wait for processing
3. View results:
   - Success count
   - Error count (with details)

### Important Notes

- **Passwords are hashed** before storing (secure)
- **Duplicate usernames/emails** will be skipped with error message
- **Grades are auto-created** if they don't exist
- **Empty optional fields** are allowed
- **Maximum file size**: 10MB

### Error Handling

Common errors:
- **"Missing required fields"**: Fill all required columns
- **"Username already exists"**: Use unique usernames
- **"Email already exists"**: Use unique emails
- **"Invalid role"**: Must be exactly "student" or "teacher" (lowercase)

### Best Practices

1. **Test with small batch first** (5-10 users)
2. **Keep backup** of your Excel file
3. **Use consistent naming** (e.g., firstname.lastname)
4. **Strong passwords** recommended (min 8 chars, mix of upper/lower/numbers)
5. **Inform users** of their credentials separately

---

## 3. Question Bank DLCs

### What is it?

**DLC (Downloadable Content)** - Modular question databases for different subjects and exam boards. Each subject-grade combination can have its own isolated question bank.

### Benefits

- **Modular**: Activate only the subjects you need
- **Organized**: Questions grouped by curriculum (IGCSE, AS/A Level, JEE, etc.)
- **Scalable**: Add new modules as you expand
- **Flexible**: Future support for separate database files per module

### How to Access

Navigate to: **Teacher Dashboard → 📦 Question Bank DLCs**

Or directly: `http://localhost:8000/teacher/dlc/`

### DLC Dashboard

Shows three sections:
1. **✅ Active Question Banks** - Currently enabled modules
2. **⏳ Pending Activation** - Created but not activated
3. **⏸️ Inactive Question Banks** - Previously activated but now disabled

### Creating a Question Bank

1. Go to DLC Dashboard
2. Scroll to "➕ Create New Question Bank"
3. Select a Subject-Grade Combination from dropdown
4. Click "➕ Create Question Bank"
5. New bank appears in "Pending Activation" section

### Activating a DLC

1. Find the question bank in "Pending" or "Inactive" section
2. Click "✅ Activate" button
3. Bank moves to "Active" section
4. Questions from this bank become available

### Deactivating a DLC

1. Find the question bank in "Active" section
2. Click "⏸️ Deactivate" button (only for non-core modules)
3. Bank moves to "Inactive" section
4. Questions are hidden but not deleted

### Core vs Regular Modules

- **Core modules**: Cannot be deactivated (essential subjects)
- **Regular modules**: Can be activated/deactivated as needed

### Future Enhancements

The DLC system is designed to support:
- **Separate database files** per subject (e.g., `9702_physics.db`)
- **Import/Export** of question banks
- **Sharing** question banks between schools
- **Version control** for question updates
- **Download statistics** and usage tracking

---

## Database Schema Changes

### New Models

1. **SubjectGradeCombination**
   - Stores curriculum codes (9702, 0625, etc.)
   - Links subjects to grades with levels
   - Supports IGCSE, AS/A Level, JEE, SAT, CUET

2. **QuestionBank**
   - Manages modular question databases
   - Tracks activation status
   - Stores metadata (question count, size, version)
   - Links to school for multi-tenancy

### Modified Models

1. **Subject**
   - Added `code` field (e.g., "9702")
   - Added `description` field

---

## Management Commands

### populate_combinations

Populates the database with default subject-grade combinations.

```bash
python manage.py populate_combinations
```

**Output:**
- Creates 12 default combinations (IGCSE and AS/A Level sciences)
- Updates existing combinations if names/descriptions changed
- Skips duplicates

**When to use:**
- After initial setup
- After database reset
- To restore default combinations

---

## URL Reference

| URL | Purpose |
|-----|---------|
| `/teacher/subject-grade-combinations/` | View all combinations |
| `/teacher/subject-grade-combinations/add/` | Add new combination |
| `/teacher/users/bulk-import/` | Bulk user import |
| `/teacher/users/download-template/` | Download Excel template |
| `/teacher/dlc/` | DLC dashboard |
| `/teacher/dlc/<id>/activate/` | Activate question bank |
| `/teacher/dlc/<id>/deactivate/` | Deactivate question bank |
| `/teacher/dlc/create/` | Create question bank |

---

## Permissions

All features require:
- **Teacher** or **School Admin** role
- Active account in a school

Students cannot access these features.

---

## Troubleshooting

### Bulk Import Issues

**Problem**: "Missing required columns"
- **Solution**: Ensure Excel file has exact column names (case-sensitive)

**Problem**: Upload fails silently
- **Solution**: Check file size (max 10MB), ensure .xlsx format

**Problem**: Some users imported, some failed
- **Solution**: Review error messages for specific rows, fix and re-upload failed ones

### DLC Issues

**Problem**: Can't create question bank for a combination
- **Solution**: Check if combination already has a question bank for your school

**Problem**: Can't deactivate a module
- **Solution**: Core modules cannot be deactivated (by design)

**Problem**: No combinations showing in dropdown
- **Solution**: Run `python manage.py populate_combinations`

---

## Future Roadmap

### Planned Features

1. **Enhanced Question Bank Filtering**
   - Filter by DLC/module
   - Search within specific question banks
   - Cross-module question search

2. **DLC Import/Export**
   - Export question banks to file
   - Import question banks from other schools
   - Share question banks

3. **Bulk Question Import**
   - Import questions from Excel
   - Map to subject-grade combinations
   - Auto-assign to appropriate DLC

4. **Analytics per DLC**
   - Usage statistics
   - Popular question banks
   - Student performance by module

5. **JEE/SAT/CUET Modules**
   - Pre-configured question banks
   - Exam-specific question types
   - Practice test templates

---

## Support

For issues or questions:
1. Check this guide first
2. Review error messages carefully
3. Test with small datasets
4. Contact system administrator

---

**Last Updated**: 2026-02-01
**Version**: 3.0 with DLC Support
