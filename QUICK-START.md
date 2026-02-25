# Quick Start - New Features

## 🚀 Getting Started

All new features are ready to use! Here's a quick guide to get you started.

---

## 1️⃣ Bulk Import Users (Fastest Way to Add Students/Teachers)

### Step 1: Access the Feature
```
http://localhost:8000/teacher/users/bulk-import/
```
Or navigate: **Teacher Dashboard → User Management → 📥 Bulk Import Users**

### Step 2: Download Template
Click **"📥 Download Template"** - You'll get an Excel file with:
- **Students** sheet (sample data included)
- **Teachers** sheet (sample data included)

### Step 3: Fill Template
Edit the Excel file:
- **Delete sample rows**
- **Add your real data** (one user per row)
- **Required columns**: username, email, password, first_name, last_name, role

**Example Student Row:**
```
username: john.doe
email: john@school.com
password: Student@123
first_name: John
last_name: Doe
role: student
full_name: John Doe
roll_number: 2024001
grade: AS Level
division: A
```

### Step 4: Upload & Import
1. Upload your Excel file
2. Click **"👁️ Preview Data"**
3. Verify the preview
4. Click **"✅ Confirm & Import"**
5. Done! Users are created instantly

**⚡ Pro Tip:** Test with 2-3 users first, then do bulk import.

---

## 2️⃣ Subject-Grade Combinations (Pre-configured Curriculum Codes)

### Already Set Up! ✅
The system comes with **12 pre-loaded combinations**:

**IGCSE:**
- 0610 - IGCSE Biology
- 0620 - IGCSE Chemistry
- 0625 - IGCSE Physics

**AS & A Level:**
- 9700 - AS & A Level Biology
- 9701 - AS & A Level Chemistry
- 9702 - AS & A Level Physics

**Plus separate AS Level and A Level variants**

### View All Combinations
```
http://localhost:8000/teacher/subject-grade-combinations/
```

### Add Custom Combination (JEE, SAT, CUET)
1. Go to Subject-Grade Combinations page
2. Click **"➕ Add New Combination"**
3. Fill form:
   - Code: `JEE-PHYS`
   - Name: `JEE Physics`
   - Subject: Physics
   - Grade: JEE
   - Level: JEE
4. Click **"✅ Create Combination"**

---

## 3️⃣ Question Bank DLCs (Modular Question Databases)

### Access DLC Dashboard
```
http://localhost:8000/teacher/dlc/
```
Or navigate: **Teacher Dashboard → 📦 Question Bank DLCs**

### Create Your First Question Bank
1. Go to DLC Dashboard
2. Scroll to **"➕ Create New Question Bank"**
3. Select a combination from dropdown (e.g., "9702 - AS & A Level Physics")
4. Click **"➕ Create Question Bank"**
5. Bank appears in **"Pending Activation"** section

### Activate Question Bank
1. Find your bank in **"Pending"** section
2. Click **"✅ Activate"**
3. Bank moves to **"Active"** section
4. Questions from this bank are now available!

### Why Use DLCs?
- **Organize questions** by curriculum (IGCSE, AS/A Level, JEE, etc.)
- **Activate only what you need** - Keep your question bank clean
- **Future-ready** for separate database files per subject
- **Easy expansion** - Add JEE, SAT, CUET modules later

---

## 📊 Feature Comparison

| Task | Old Way | New Way | Time Saved |
|------|---------|---------|------------|
| Add 50 students | 50 × manual forms | 1 Excel upload | ~2 hours |
| Organize subjects | Manual tagging | Pre-configured codes | Instant |
| Manage question banks | Single database | Modular DLCs | Better organization |

---

## 🎯 Common Workflows

### Workflow 1: New School Setup
1. **Populate combinations**: Already done! ✅
2. **Bulk import teachers**: Use Excel template
3. **Bulk import students**: Use Excel template
4. **Create question banks**: One per subject-grade
5. **Activate banks**: Start with core subjects

### Workflow 2: Add IGCSE Students
1. Download template
2. Fill students with grade = "IGCSE"
3. Upload and import
4. Create/activate IGCSE question banks (0610, 0620, 0625)

### Workflow 3: Expand to JEE/SAT
1. Add JEE/SAT combinations
2. Create corresponding question banks
3. Import JEE/SAT questions
4. Activate when ready

---

## 🔧 Troubleshooting

### "Missing required columns" Error
- **Fix**: Check Excel column names match exactly (case-sensitive)
- **Required**: username, email, password, first_name, last_name, role

### "Username already exists" Error
- **Fix**: Use unique usernames for each user
- **Tip**: Format like `firstname.lastname` or `firstname.lastname.grade`

### Can't See Combinations Dropdown
- **Fix**: Run `python manage.py populate_combinations`
- This populates the 12 default combinations

### DLC Page Shows Empty
- **Normal**: You need to create question banks first
- **Action**: Click "➕ Create New Question Bank" and select a combination

---

## 📚 Navigation Quick Reference

| Feature | URL | Shortcut |
|---------|-----|----------|
| Bulk Import | `/teacher/users/bulk-import/` | Teacher → User Management → Bulk Import |
| Download Template | `/teacher/users/download-template/` | Click button on bulk import page |
| DLC Dashboard | `/teacher/dlc/` | Teacher → Question Bank DLCs |
| Combinations | `/teacher/subject-grade-combinations/` | DLC page → Manage Combinations link |
| Add Combination | `/teacher/subject-grade-combinations/add/` | Combinations page → Add New |

---

## 🎓 Best Practices

### For Bulk Import
1. ✅ **Test small first** (2-3 users)
2. ✅ **Keep backup** of Excel file
3. ✅ **Use strong passwords** (min 8 chars)
4. ✅ **Consistent naming** (firstname.lastname)
5. ✅ **Inform users** of credentials via email/letter

### For Question Banks
1. ✅ **Start with core subjects** (Biology, Chemistry, Physics)
2. ✅ **One bank per curriculum** (separate IGCSE and AS/A Level)
3. ✅ **Activate only what's needed** (reduce clutter)
4. ✅ **Use standard codes** (9702, 0625, etc.)

### For Combinations
1. ✅ **Use official syllabus codes** (Cambridge, etc.)
2. ✅ **Descriptive names** (AS & A Level Physics, not just Physics)
3. ✅ **Consistent format** (9702-AS, 9702-A for variants)

---

## 🚦 Status Indicators

### DLC Status Badges
- **✅ Active** - Question bank is enabled and in use
- **⏳ Pending** - Created but not activated yet
- **⏸️ Inactive** - Previously active but now disabled
- **Core** - Cannot be deactivated (essential subjects)

### Import Status
- **Success** - Green message with count
- **Partial** - Yellow warning with error details
- **Failed** - Red error with specific issues

---

## 💡 Pro Tips

1. **Excel Tips:**
   - Use formulas to generate usernames: `=LOWER(A2&"."&B2)` for firstname.lastname
   - Fill passwords with a formula for consistency
   - Use Excel's data validation for role column (student/teacher dropdown)

2. **Combination Codes:**
   - Stick to official codes for Cambridge (9702, 0625, etc.)
   - Use prefixes for other boards (JEE-PHYS, SAT-MATH)
   - Keep codes short (max 10 characters)

3. **Question Bank Strategy:**
   - Create all banks at once, activate gradually
   - Deactivate unused banks to reduce clutter
   - Use consistent naming across your school

---

## 📖 Need More Help?

- **Full Guide**: Read `FEATURES-GUIDE.md` for detailed documentation
- **Django Admin**: Access `/admin/` for direct database management
- **Project Docs**: Check `CLAUDE.md` for overall project structure

---

**Ready to use!** Start with bulk importing a few test users, then explore the other features.

**Last Updated**: 2026-02-01
