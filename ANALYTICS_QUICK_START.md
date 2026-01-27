# 📊 Analytics System - Quick Start Guide

## 🚀 What's New

You now have a **comprehensive analytics system** with beautiful, grounded UI for tracking student and class performance.

---

## ✅ Completed Features

### For Students
✨ **Analytics Dashboard** (`/student/analytics/`)
- Overall performance metrics
- Subject-wise performance with rankings
- Topic mastery breakdown
- Learning objective tracking
- Strengths & weaknesses identification
- Engagement overview

### For Teachers
✨ **Class Analytics Dashboard** (`/teacher/analytics/`)
- Class performance by subject
- LO mastery heatmap with red zone alerts
- At-risk student identification
- Individual student deep-dive
- Comprehensive filtering (grade, section, group, time range)

✨ **Test Analytics** (`/teacher/tests/<id>/analytics/`)
- Class statistics (mean, median, std dev)
- Student rankings
- Performance distribution

---

## 🎯 How to Access

### As a Student:
1. Login to your account
2. Click "📈 Analytics" in the top navbar
3. Select time range (Last Month, 3 Months, 6 Months, Year)
4. Explore your performance metrics

**Note**: Analytics will only show if you have completed and graded tests.

### As a Teacher:
1. Login to your teacher account
2. Click "📊 Performance Analytics" in the left sidebar
3. Apply filters:
   - Select Grade, Section, or Class Group
   - Choose time range
4. Switch between views:
   - **Class Overview** - See class-wide metrics
   - **Individual Student** - Analyze one student in detail
   - **Comparative Analysis** - Compare groups (structure ready)

### Test-Specific Analytics:
1. Go to "Tests Library"
2. Click on any completed test
3. Visit `/teacher/tests/<test_id>/analytics/`
4. View class statistics and student rankings

---

## 📊 Metrics Available

### Student Metrics
- ✅ Overall average percentage
- ✅ Subject performance with rankings
- ✅ Subject trends over time
- ✅ Topic mastery (Strong/Moderate/Weak)
- ✅ Learning objective performance
- ✅ Strengths (top 10 LOs)
- ✅ Weaknesses (bottom 10 LOs)
- ✅ Persistent weak areas
- ✅ LO coverage percentage
- ✅ Topic coverage percentage
- ✅ Questions attempted
- ✅ Attempt rate per week

### Teacher Metrics
- ✅ Class average per subject (mean, median, std dev)
- ✅ LO mastery heatmap
- ✅ Red zone LOs (low class mastery)
- ✅ At-risk students (<40% average)
- ✅ Individual student performance
- ✅ Test class statistics
- ✅ Student rankings per test

---

## 🎨 UI Highlights

### Design Features
- **Modern gradient branding** - Purple gradient "Lumen" logo throughout
- **Color-coded performance**:
  - 🟢 Green: Excellent (≥80%)
  - 🟣 Purple: Good (60-79%)
  - 🟠 Orange: Average (40-59%)
  - 🔴 Red: Poor (<40%)
- **Interactive cards** - Hover effects and smooth animations
- **Progress bars** - Visual performance indicators
- **Empty states** - Helpful messages when no data
- **Responsive design** - Works on all screen sizes

### Visual Indicators
- **Badges** - Rounded status indicators
- **Heatmaps** - LO mastery visualization
- **Tables** - Clean, sortable data grids
- **Gradients** - Engaging color schemes

---

## 🔧 Technical Implementation

### New Files Created

1. **`core/analytics.py`** (366 lines)
   - `StudentAnalytics` class
   - `ClassAnalytics` class
   - All metric calculation logic

2. **`core/analytics_views.py`** (203 lines)
   - `student_analytics_dashboard`
   - `teacher_analytics_dashboard`
   - `test_analytics`

3. **`core/templates/student/analytics_dashboard.html`** (517 lines)
   - Complete student-facing UI
   - Metrics dashboard, subject cards, topic grid, LO tables

4. **`core/templates/teacher/analytics_dashboard.html`** (460 lines)
   - Teacher-facing analytics UI
   - Filters, view tabs, class stats, heatmaps

5. **`core/templates/teacher/test_analytics.html`** (162 lines)
   - Test-specific analytics
   - Class stats cards, student ranking table

6. **`ANALYTICS_SYSTEM.md`** (Full documentation)

### Modified Files

1. **`core/urls.py`**
   - Added 3 new analytics routes
   - Imported `analytics_views`

2. **`templates/student/student_base.html`**
   - Added "📈 Analytics" link to navbar

3. **`core/templates/teacher/teacher_base.html`**
   - Added "📊 Performance Analytics" to sidebar

---

## 🧪 Testing the System

### Prerequisites
- Have some graded test submissions in the database
- Students must have `marks_awarded` set (not null)
- Tests must be published

### Test as Student
```
1. Login as a student with graded tests
2. Navigate to /student/analytics/
3. You should see:
   - Overall metrics (4 cards)
   - Subject performance (list with progress bars)
   - Topic performance (grid of cards)
   - Strengths section
   - Weaknesses section
   - Engagement card
```

### Test as Teacher
```
1. Login as teacher/admin
2. Navigate to /teacher/analytics/
3. Apply filters (select grade, section, time range)
4. You should see:
   - Class average table
   - LO mastery heatmap
   - At-risk students (if any below 40%)
5. Switch to "Individual Student" view
6. Select a student from dropdown
7. See student's detailed metrics
```

### Test Analytics
```
1. Go to /teacher/tests/
2. Click on a completed test
3. Visit /teacher/tests/<test_id>/analytics/
4. You should see:
   - 6 stat cards (mean, median, std dev, max, min, count)
   - Student ranking table
```

---

## ⚙️ Configuration

### Adjust Mastery Threshold
**Current**: 60% considered mastery

**Location**: `core/analytics.py:118, 242`
```python
if percentage >= 60:  # Change to your threshold
    topic_data[topic_name]['correct'] += 1
```

### Adjust At-Risk Threshold
**Current**: 40% average triggers at-risk status

**Location**: `core/analytics_views.py:144`
```python
'at_risk_students': class_analytics.at_risk_students(threshold=40)
```

### Adjust Trend Sensitivity
**Current**: slope > 2 = improving, < -2 = declining

**Location**: `core/analytics.py:79-84`
```python
if slope > 2:  # More/less sensitive
    trend = 'improving'
elif slope < -2:
    trend = 'declining'
```

---

## 🐛 Troubleshooting

### "No data available" everywhere
**Cause**: No graded submissions in date range
**Fix**:
- Check that tests are published
- Verify `marks_awarded` is set (not null)
- Try "Last Year" time range
- Check that student has submitted answers

### ImportError: cannot import name 'StudentAnalytics'
**Cause**: Module not found
**Fix**:
- Ensure `core/analytics.py` exists
- Restart Django server
- Check for syntax errors in analytics.py

### Page not loading (404)
**Cause**: URL route not registered
**Fix**:
- Verify `core/urls.py` has analytics routes
- Check `from . import analytics_views` at top
- Restart server

### Slow page loads
**Cause**: Large number of answers to process
**Fix**:
- Add database indexes on `student_id`, `test_id`, `submitted_at`
- Implement caching (future enhancement)
- Reduce time range

---

## 🚀 Next Steps

### Recommended Enhancements

1. **Add Charts** - Integrate Chart.js for visual graphs
2. **Export Reports** - PDF/CSV export functionality
3. **Caching** - Redis for computed metrics
4. **Real-time Updates** - WebSocket for live data
5. **Predictive Analytics** - ML-based performance forecasting
6. **Mobile App** - React Native companion app

### Quick Wins
- Add "Download PDF" button to analytics pages
- Create email digest of weekly performance
- Add comparative bar charts using Chart.js
- Implement print-friendly CSS

---

## 📚 Documentation

**Full Documentation**: See `ANALYTICS_SYSTEM.md`

**Key Sections**:
- Architecture overview
- Metric calculations (formulas)
- Database optimization strategies
- Visual design guidelines
- API endpoints reference
- Future enhancement roadmap

---

## ✨ Summary

You now have:
- ✅ 16 fully functional metrics
- ✅ Beautiful, modern UI design
- ✅ Student-facing analytics dashboard
- ✅ Teacher-facing analytics dashboard
- ✅ Test-specific analytics
- ✅ Time range filtering
- ✅ Grade/Section/Group filtering
- ✅ Individual student analysis
- ✅ At-risk student identification
- ✅ LO mastery heatmaps
- ✅ Strengths & weaknesses detection
- ✅ Comprehensive documentation

**Ready to use at**: `http://127.0.0.1:8000/student/analytics/` and `/teacher/analytics/`

Enjoy your new analytics system! 🎉
