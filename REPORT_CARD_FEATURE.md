# 📋 Report Card Mode - Feature Documentation

## Overview

Comprehensive report card generation system with advanced search, filtering, pagination, and professional PDF export using jsPDF. Allows teachers to search for students across cohorts and generate detailed academic performance reports.

---

## Features

### 1. **Smart Search & Filtering**

Search and filter students across multiple dimensions:

| Filter | Type | Purpose |
|--------|------|---------|
| **Search** | Text input | Name, Roll Number, Admission ID |
| **Grade** | Dropdown | Filter by academic grade (9, 10, 11, 12, etc.) |
| **Cohort** | Dropdown | Filter by class group/cohort |
| **Subject** | Dropdown | Show only tests from specific subject |
| **Date From** | Date picker | Start date for test inclusion |
| **Date To** | Date picker | End date for test inclusion |

**Example Queries:**
- "Show all Grade 11 students who took Biology tests in December 2025"
- "Find student with roll number 'A-45'"
- "Show Morning Batch students' performance in Chemistry"

---

### 2. **Pagination**

- **10 students per page** for optimal loading
- Navigation: First, Previous, Next, Last buttons
- Page counter: "Page X of Y"
- Total count display: "Showing 10 of 125 students"

---

### 3. **Student Dashboard Table**

Each row shows:
- **Student Name** + Roll Number + Admission ID
- **Grade & Section** (e.g., "11-A")
- **Tests Taken** (count within filter criteria)
- **Average Score** (percentage across all filtered tests)
- **Status Badge**:
  - 🟢 **Excellent** (≥80%)
  - 🟡 **Good** (60-79%)
  - 🔴 **Needs Improvement** (<60%)
- **Actions**: PDF export button

---

### 4. **Professional PDF Report Cards**

Click the PDF icon to generate a comprehensive report card.

#### PDF Structure:

**Page 1 - Header & Summary:**
```
┌─────────────────────────────────────────┐
│ School Name                              │
│ School Address                           │
│                                          │
│      ACADEMIC REPORT CARD                │
│                                          │
│ ┌─────────────────────────────────────┐ │
│ │ Name: John Doe                      │ │
│ │ Grade: 11  |  Section: A            │ │
│ │ Roll Number: A-23                   │ │
│ │ Admission ID: 2024-001              │ │
│ └─────────────────────────────────────┘ │
│                                          │
│ Period: 2025-09-01 to 2026-01-31        │
│                                          │
│ Overall Performance                      │
│ ┌──────────────────┬─────────────────┐ │
│ │ Metric           │ Value           │ │
│ ├──────────────────┼─────────────────┤ │
│ │ Total Tests      │ 12              │ │
│ │ Average Score    │ 78.5%           │ │
│ │ Grade            │ B+              │ │
│ └──────────────────┴─────────────────┘ │
│                                          │
│ Subject-wise Performance                 │
│ ┌────────┬───────┬─────────┬────────┐ │
│ │Subject │ Tests │ Average │ Grade  │ │
│ ├────────┼───────┼─────────┼────────┤ │
│ │Biology │ 4     │ 82.3%   │ A      │ │
│ │Chemistry│ 5     │ 75.8%   │ B+     │ │
│ │Physics │ 3     │ 76.1%   │ B+     │ │
│ └────────┴───────┴─────────┴────────┘ │
└─────────────────────────────────────────┘
```

**Page 2+ - Detailed Test Results:**
```
┌──────────────────────────────────────────────┐
│ Individual Test Performance                  │
│ ┌────────────┬────────┬──────┬───────┬───┐ │
│ │Test        │Subject │Date  │Marks  │Grd│ │
│ ├────────────┼────────┼──────┼───────┼───┤ │
│ │Genetics Q1 │Biology │Jan 15│18/20  │A  │ │
│ │Cell Bio    │Biology │Jan 10│15/20  │B+ │ │
│ │...         │...     │...   │...    │...│ │
│ └────────────┴────────┴──────┴───────┴───┘ │
│                                              │
│ Page 2 of 3        Generated by Lumen        │
└──────────────────────────────────────────────┘
```

#### PDF Features:
- ✅ **Professional Layout**: Rounded boxes, color headers, grid tables
- ✅ **Multi-page**: Automatic page breaks for large datasets
- ✅ **Page Numbers**: "Page X of Y" on every page
- ✅ **Branding**: "Generated by Lumen Analytics" footer
- ✅ **Timestamps**: Generation date on every page
- ✅ **Color Coding**: Blue headers (#1a73e8 - primary color)
- ✅ **Dynamic Filename**: `ReportCard_StudentName_2026-01-31.pdf`

---

## User Workflows

### Workflow 1: Generate Individual Report Card
1. Navigate to `/teacher/report-cards/`
2. (Optional) Apply filters (subject, date range)
3. Search for student by name or roll number
4. Click PDF icon next to student
5. Wait for PDF generation (loading overlay shown)
6. PDF automatically downloads

### Workflow 2: Bulk Subject-Specific Reports
1. Navigate to `/teacher/report-cards/`
2. Select **Subject**: "Biology"
3. Set **Date From**: "2025-09-01"
4. Set **Date To**: "2026-01-31"
5. Click "Apply Filters"
6. Generate PDFs for each student (shows only Biology test performance)

### Workflow 3: Cohort Performance Review
1. Navigate to `/teacher/report-cards/`
2. Select **Cohort**: "Morning Batch"
3. Click "Apply Filters"
4. Review average scores in table
5. Identify students needing intervention (<60%)
6. Generate report cards for those students

---

## Technical Architecture

### Backend (`core/report_card_views.py`)

#### 1. `report_card_dashboard(request)`
**Purpose**: Main dashboard view with search, filter, pagination

**Query Logic**:
```python
# Base: All students in teacher's school
students = Student.objects.filter(school=school)

# Apply search (name, roll_number, admission_id)
if search_query:
    students = students.filter(
        Q(full_name__icontains=search_query) |
        Q(roll_number__icontains=search_query) |
        Q(admission_id__icontains=search_query)
    )

# Apply grade filter
if grade_filter:
    students = students.filter(grade__id=grade_filter)

# Apply cohort filter (via ClassGroup -> User -> Student)
if cohort_filter:
    cohort_user_ids = cohort.students.values_list('id', flat=True)
    students = students.filter(user__id__in=cohort_user_ids)

# Paginate (10 per page)
paginator = Paginator(students, 10)
```

**Performance Calculation**:
```python
for student in page_obj:
    # Get all StudentAnswer records for this student
    answers = StudentAnswer.objects.filter(student=student)

    # Apply subject filter
    if subject_filter:
        answers = answers.filter(test__subject__id=subject_filter)

    # Apply date range
    if date_from:
        answers = answers.filter(test__created_at__gte=date_from)
    if date_to:
        answers = answers.filter(test__created_at__lte=date_to)

    # Calculate per-test percentages
    for test_id in answers.values_list('test__id', distinct=True):
        test_answers = answers.filter(test=test)
        total_marks = sum(a.question.marks for a in test_answers)
        earned_marks = sum(a.marks_awarded for a in test_answers)
        percentage = (earned_marks / total_marks) * 100
        test_scores.append(percentage)

    # Average across tests
    avg_score = sum(test_scores) / len(test_scores)
```

---

#### 2. `report_card_detail(request, student_id)`
**Purpose**: JSON API endpoint for PDF generation

**Response Format**:
```json
{
  "student": {
    "name": "John Doe",
    "roll_number": "A-23",
    "admission_id": "2024-001",
    "grade": "11",
    "section": "A"
  },
  "school": {
    "name": "Springfield High School",
    "code": "SCH001",
    "address": "123 Main St, Springfield"
  },
  "period": {
    "from": "2025-09-01",
    "to": "2026-01-31"
  },
  "tests": [
    {
      "id": 45,
      "subject": "Biology",
      "title": "Genetics Quiz 1",
      "date": "2026-01-15",
      "total_marks": 20.0,
      "earned_marks": 18.0,
      "percentage": 90.0,
      "grade": "A+"
    }
  ],
  "subjects": [
    {
      "name": "Biology",
      "test_count": 4,
      "average": 82.3,
      "grade": "A"
    }
  ],
  "overall": {
    "total_tests": 12,
    "average_percentage": 78.5,
    "grade": "B+"
  }
}
```

**Benefits**:
- ✅ Clean separation: data (backend) vs presentation (frontend PDF)
- ✅ Reusable: Same API can power mobile apps, exports, etc.
- ✅ Fast: JSON is lightweight compared to server-side PDF generation

---

#### 3. `get_letter_grade(percentage)`
**Purpose**: Convert percentage to letter grade

**Grading Scale**:
```python
90-100%  → A+
80-89%   → A
70-79%   → B+
60-69%   → B
50-59%   → C+
40-49%   → C
33-39%   → D
0-32%    → F
```

---

### Frontend (`report_card_dashboard.html`)

#### Search & Filter UI
- **Material Design** components
- **Live filtering** via form submission
- **Clear All** button to reset filters
- **Responsive grid** (6 columns on desktop, stacks on mobile)

#### jsPDF Implementation

**Libraries Used**:
```html
<!-- Core jsPDF library -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>

<!-- AutoTable plugin for professional tables -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.31/jspdf.plugin.autotable.min.js"></script>
```

**PDF Generation Flow**:
```javascript
async function generateReportCard(studentId, studentName) {
    // 1. Show loading overlay
    document.getElementById('loadingOverlay').classList.add('active');

    // 2. Fetch data from JSON API
    const url = `/teacher/report-cards/${studentId}/data/?subject=${subject}&date_from=${dateFrom}&date_to=${dateTo}`;
    const response = await fetch(url);
    const data = await response.json();

    // 3. Initialize jsPDF
    const doc = new jsPDF();

    // 4. Add header (school info, title)
    doc.setFontSize(10);
    doc.text(data.school.name, margin, yPos);
    doc.setFontSize(22);
    doc.text('ACADEMIC REPORT CARD', pageWidth / 2, yPos, { align: 'center' });

    // 5. Add student info box (rounded rectangle)
    doc.setFillColor(248, 249, 250);
    doc.roundedRect(margin, yPos, width, height, 3, 3, 'FD');
    doc.text(`Name: ${data.student.name}`, margin + 5, yPos);

    // 6. Add overall performance table
    doc.autoTable({
        startY: yPos,
        head: [['Metric', 'Value']],
        body: [
            ['Total Tests', data.overall.total_tests],
            ['Average Score', `${data.overall.average_percentage}%`],
            ['Grade', data.overall.grade]
        ],
        theme: 'grid',
        headStyles: { fillColor: [26, 115, 232] }  // Primary blue
    });

    // 7. Add subject-wise table
    doc.autoTable({
        head: [['Subject', 'Tests', 'Average', 'Grade']],
        body: data.subjects.map(s => [s.name, s.test_count, `${s.average}%`, s.grade]),
        theme: 'grid'
    });

    // 8. Add individual test table (new page)
    doc.addPage();
    doc.autoTable({
        head: [['Test', 'Subject', 'Date', 'Marks', 'Score', 'Grade']],
        body: data.tests.map(t => [t.title, t.subject, t.date, `${t.earned_marks}/${t.total_marks}`, `${t.percentage}%`, t.grade]),
        bodyStyles: { fontSize: 8 },
        columnStyles: {
            0: { cellWidth: 'auto' },
            1: { cellWidth: 30 },
            2: { cellWidth: 25 }
        }
    });

    // 9. Add footers to all pages
    for (let i = 1; i <= totalPages; i++) {
        doc.setPage(i);
        doc.text(`Page ${i} of ${totalPages}`, pageWidth - margin, pageHeight - 10);
        doc.text('Generated by Lumen Analytics', margin, pageHeight - 10);
    }

    // 10. Save PDF
    doc.save(`ReportCard_${studentName}_${new Date().toISOString().split('T')[0]}.pdf`);

    // 11. Hide loading overlay
    document.getElementById('loadingOverlay').classList.remove('active');
}
```

---

## URL Routing

| URL | View | Purpose |
|-----|------|---------|
| `/teacher/report-cards/` | `report_card_dashboard` | Main dashboard (HTML) |
| `/teacher/report-cards/<student_id>/data/` | `report_card_detail` | JSON API for PDF |

**Query Parameters** (both URLs):
- `?search=john` - Search query
- `?grade=5` - Grade ID filter
- `?cohort=12` - ClassGroup ID filter
- `?subject=3` - Subject ID filter
- `?date_from=2025-09-01` - Start date
- `?date_to=2026-01-31` - End date
- `?page=2` - Pagination (dashboard only)

---

## Database Queries

### Key Models Involved:
1. **Student** - Student records (name, roll, admission ID)
2. **ClassGroup** - Cohorts/batches (M2M with User)
3. **Test** - Test metadata (subject, date, school)
4. **StudentAnswer** - Answer records with marks
5. **Grade** - Academic grades
6. **Subject** - Subject domains

### Query Optimization:
```python
# Efficient querying with select_related and prefetch_related
students = Student.objects.filter(school=school).select_related('grade')
answers = StudentAnswer.objects.filter(student=student).select_related(
    'test', 'test__subject', 'question', 'question__topic'
)
```

---

## Performance Considerations

### Client-Side PDF Generation
**Why?**
- ✅ No server CPU load
- ✅ Instant generation (no upload/download delays)
- ✅ Scales infinitely (runs on user's device)
- ✅ Works offline (once data is fetched)

**Trade-offs**:
- ❌ Requires modern browser with JavaScript
- ❌ Limited to jsPDF capabilities (vs server-side libraries like WeasyPrint)

### Pagination Benefits
- Loads only 10 students at a time
- Fast page load even with 1000+ students
- Prevents browser memory issues

### Filter Performance
- Django ORM uses indexed fields (grade FK, school FK)
- `Q` objects for OR queries (name OR roll OR admission)
- Date filters on `created_at` (indexed by default)

---

## Security

### Multi-Tenancy
```python
# ALWAYS filter by school to prevent cross-school data leaks
school = request.user.profile.school
student = get_object_or_404(Student, id=student_id, school=school)
```

### Authorization
```python
# @login_required decorator ensures only authenticated users
@login_required
def report_card_dashboard(request):
    # Only teachers/admins can access (check role if needed)
    if request.user.profile.role not in ['teacher', 'school_admin']:
        return HttpResponseForbidden()
```

### Input Validation
- Date parsing with `try/except` blocks
- Integer IDs validated by Django ORM
- Search queries sanitized via `icontains` (prevents SQL injection)

---

## Testing Checklist

- [ ] **Search Functionality**
  - [ ] Search by student name (full/partial match)
  - [ ] Search by roll number
  - [ ] Search by admission ID
  - [ ] Case-insensitive search works

- [ ] **Filters**
  - [ ] Grade filter shows only students in that grade
  - [ ] Cohort filter shows only students in that group
  - [ ] Subject filter affects test count and average
  - [ ] Date range filters exclude tests outside range
  - [ ] Multiple filters work together (AND logic)

- [ ] **Pagination**
  - [ ] 10 students per page
  - [ ] Next/Previous buttons work
  - [ ] First/Last buttons work
  - [ ] Page counter accurate
  - [ ] Filters persist across pages

- [ ] **PDF Generation**
  - [ ] School info appears at top
  - [ ] Student info box formatted correctly
  - [ ] Overall performance table has correct data
  - [ ] Subject-wise table shows all subjects
  - [ ] Individual test table shows all tests
  - [ ] Multi-page PDFs work (for students with many tests)
  - [ ] Page numbers correct on all pages
  - [ ] Footer appears on all pages
  - [ ] Filename includes student name and date
  - [ ] Loading overlay shows/hides correctly

- [ ] **Edge Cases**
  - [ ] Student with 0 tests (shows "No tests" or 0%)
  - [ ] Student with 1 test (no division errors)
  - [ ] Very long student names (PDF layout doesn't break)
  - [ ] 100+ tests (PDF pagination works)
  - [ ] Empty search results (shows empty state)

---

## Future Enhancements

### Phase 2 (Optional):
1. **Batch PDF Export**: Select multiple students, download as ZIP
2. **Email Reports**: Send PDF directly to parents via email
3. **Custom Templates**: School-specific report card designs
4. **Attendance Integration**: Include attendance % in report
5. **Remarks Section**: Teacher comments/recommendations
6. **Comparison Charts**: Student vs class average graphs
7. **Progress Tracking**: Show trend over multiple terms
8. **Digital Signatures**: Principal/Teacher signature images
9. **QR Code**: Verification QR code for authenticity
10. **Excel Export**: Alternative to PDF for data analysis

---

## Files Modified

### Backend
1. **core/report_card_views.py** (NEW)
   - `report_card_dashboard` view
   - `report_card_detail` JSON API
   - `get_letter_grade` helper

2. **core/urls.py**
   - Added import for `report_card_views`
   - Added 2 URL patterns

### Frontend
3. **core/templates/teacher/report_card_dashboard.html** (NEW)
   - 700+ lines of HTML/CSS/JavaScript
   - Filter panel with 6 inputs
   - Students table with pagination
   - jsPDF generation function

---

## Result

Teachers can now:
- ✅ Quickly search for any student across the school
- ✅ Filter performance data by subject, date range, cohort
- ✅ View summary statistics before generating reports
- ✅ Generate professional, multi-page PDF report cards
- ✅ Export reports with school branding and proper formatting
- ✅ Share printable reports with parents and administrators

**All with zero server-side PDF generation overhead!**

---

**Last Updated**: 2026-01-31
**Feature**: Report Card Mode with jsPDF Export
