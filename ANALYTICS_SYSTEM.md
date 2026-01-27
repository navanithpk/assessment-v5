# 📊 Lumen Analytics System

## Overview

The Lumen Analytics System provides comprehensive performance tracking and insights for both students and teachers. The system implements 21 distinct metric categories covering individual performance, class-level analysis, and diagnostic insights.

---

## Architecture

### Core Components

1. **`core/analytics.py`** - Analytics computation engine
   - `StudentAnalytics` class - Individual student metrics
   - `ClassAnalytics` class - Group/class/cohort metrics

2. **`core/analytics_views.py`** - View controllers
   - `student_analytics_dashboard` - Student-facing analytics
   - `teacher_analytics_dashboard` - Teacher-facing analytics
   - `test_analytics` - Individual test performance

3. **Templates**
   - `student/analytics_dashboard.html` - Student UI
   - `teacher/analytics_dashboard.html` - Teacher UI
   - `teacher/test_analytics.html` - Test-specific analytics

---

## Student Analytics

### Access
- URL: `/student/analytics/`
- Navigation: Student navbar → "📈 Analytics"
- Requires: Graded test submissions

### Features Implemented

#### 🎯 Key Metrics Dashboard
- **Overall Average** - Aggregate performance across all subjects
- **LO Coverage** - Percentage of learning objectives attempted
- **Topic Coverage** - Percentage of curriculum topics covered
- **Questions Attempted** - Total engagement metric

#### 📊 Subject-Level Performance
**Metric**: Performance across different subjects
- Average percentage per subject
- Rank among student's own subjects
- Consistency score (standard deviation)
- Total questions per subject
- Visual progress bars with color coding:
  - Excellent: ≥80% (green gradient)
  - Good: 60-79% (purple gradient)
  - Average: 40-59% (pink gradient)
  - Poor: <40% (orange gradient)

**Metric**: Subject performance trend (on click)
- Time-series data
- Rolling average (3-test window)
- Trend classification (improving/stable/declining)
- Best and worst scores
- Stability index (variance)

#### 🎯 Topic & LO Performance
**Metric**: Performance across specific topics
- Mastery percentage (60% threshold)
- Average score
- Questions attempted
- Classification: Strong (≥80%), Moderate (50-79%), Weak (<50%)
- Color-coded cards with visual indicators

**Metric**: Learning Objective performance
- Mastery percentage
- Attempt frequency
- Improvement rate (first half vs second half comparison)
- Volatility (standard deviation of scores)

#### 💪 Strengths & Weaknesses
**Metric**: Strong LOs
- Top 10 LOs with ≥80% mastery
- Displayed with green success indicators

**Metric**: Weak LOs
- Bottom 10 LOs with <50% mastery
- Persistent weak LOs (≥3 attempts, still weak)
- Red alert indicators

#### 🔥 Engagement Overview
- Total questions attempted
- Questions per week (attempt rate)
- LO coverage percentage
- Topic coverage percentage
- Date range display

### Time Range Filters
- Last Month (1m)
- Last 3 Months (3m)
- Last 6 Months (6m)
- Last Year (1y)

---

## Teacher Analytics

### Access
- URL: `/teacher/analytics/`
- Navigation: Teacher sidebar → "📊 Performance Analytics"
- Requires: Staff permissions

### Features Implemented

#### 📊 Class Overview View

**Metric**: Class average per subject
- Mean score per subject
- Median score per subject
- Standard deviation (consistency measure)
- Question count
- Tabular display with sortable columns

**Metric**: LO Mastery Heatmap
- Percentage of class mastering each LO
- Students mastered vs total students
- Visual progress bars
- Color coding: Green (≥70%), Yellow (40-69%), Red (<40%)
- **Red Zone** badges for LOs with <50% class mastery
- Identifies curriculum gaps

**Metric**: At-Risk Students
- Students with <40% average (configurable threshold)
- Visual cards with student info
- Average percentage display
- Grade and section information
- Empty state shows success message if none at risk

#### 👨‍🎓 Individual Student View

**Filters**:
- Select any student in school/grade/section/group
- View all metrics for that student
- Same metrics as student self-view
- Subject performance cards
- Topic performance breakdown
- Strengths and weaknesses
- Engagement metrics

#### 🔍 Comparative Analysis View
(Template structure ready, full implementation pending)
- Compare multiple students
- Compare class groups
- Compare sections
- Performance distribution charts

### Filters Available

1. **Grade** - Filter by academic grade
2. **Section** - Filter by section (A, B, C, etc.)
3. **Class Group** - Filter by custom student groups
4. **Time Range** - 1m, 3m, 6m, 1y

### View Types
- **Overview** - Class-level aggregates
- **Student** - Individual student deep-dive
- **Comparative** - Multi-entity comparison

---

## Test Analytics

### Access
- URL: `/teacher/tests/<test_id>/analytics/`
- Available from: Tests list or individual test pages

### Metrics

**Class Statistics**:
- Mean score
- Median score
- Standard deviation
- Highest score
- Lowest score
- Total students

**Student Performance Table**:
- Rank (sorted by percentage descending)
- Student name
- Grade-Section
- Marks (earned/total)
- Percentage with color-coded badges

**Actions**:
- Link to grade test answers
- Back to tests list

---

## Metric Calculations

### Subject Performance
```python
avg_percentage = sum(question_percentages) / count
consistency = standard_deviation(question_percentages)
overall_percentage = (total_earned / total_marks) * 100
```

### Topic Mastery
```python
mastery_percentage = (questions_above_60_percent / total_questions) * 100
classification = {
    'strong': mastery >= 80%,
    'moderate': 50% <= mastery < 80%,
    'weak': mastery < 50%
}
```

### LO Performance
```python
mastery_percentage = (questions_above_60_percent / total_attempts) * 100
improvement_rate = avg(second_half_scores) - avg(first_half_scores)
volatility = standard_deviation(all_scores)
```

### Trend Analysis (Linear Regression)
```python
slope = Σ((x - x̄)(y - ȳ)) / Σ((x - x̄)²)
trend = {
    'improving': slope > 2,
    'stable': -2 ≤ slope ≤ 2,
    'declining': slope < -2
}
```

### Class Percentile
```python
student_rank = count(students_with_score <= student_score)
percentile = (student_rank / total_students) * 100
```

---

## Visual Design

### Color Palette
- **Primary Gradient**: #667eea → #764ba2 (Purple)
- **Success**: #11998e → #38ef7d (Green)
- **Warning**: #f093fb → #f5576c (Pink)
- **Danger**: #fa709a → #fee140 (Orange/Red)

### UI Components
- **Metric Cards** - Hover effects, shadow elevation
- **Progress Bars** - Smooth animations, gradient fills
- **Badges** - Rounded, color-coded status indicators
- **Tables** - Zebra striping, hover highlights
- **Empty States** - Large icons with helpful messages

### Responsive Design
- Grid layouts with `auto-fit` and `minmax()`
- Mobile-friendly breakpoints
- Touch-friendly click targets
- Readable typography at all sizes

---

## Database Queries

### Optimization Strategies
1. **select_related()** for foreign keys (question, topic, subject, test)
2. **prefetch_related()** for M2M (learning_objectives)
3. **Filter early** - Date range and student filters before aggregation
4. **Aggregate in Python** - Calculations done post-query for flexibility

### Query Patterns
```python
# Efficient answer retrieval
answers = StudentAnswer.objects.filter(
    student=student,
    marks_awarded__isnull=False,
    test__published=True,
    submitted_at__gte=start_date,
    submitted_at__lte=end_date
).select_related('question', 'test', 'question__topic', 'question__subject')
```

---

## Future Enhancements

### Planned Features (Not Yet Implemented)

1. **Question-Level Analysis**
   - Error type classification (conceptual, careless, procedural)
   - Average time per question
   - Question difficulty vs performance correlation

2. **Performance Distribution Charts**
   - Histograms
   - Box plots
   - Quartile/decile analysis

3. **Learning Gap Analysis**
   - Gap widening/narrowing trends
   - Pre/post intervention comparison
   - Effect size calculations

4. **Curriculum Coverage Reports**
   - LO representation fairness
   - Assessment balance
   - Untested areas

5. **Assessment Quality Metrics**
   - Discrimination index
   - Reliability coefficients
   - Item analysis

6. **Export Functionality**
   - PDF reports
   - CSV data export
   - Print-friendly views

7. **Interactive Charts**
   - Chart.js integration
   - Time-series graphs
   - Comparative bar charts

8. **Predictive Analytics**
   - Forgetting curve modeling
   - Performance forecasting
   - Risk prediction algorithms

---

## Usage Examples

### Student Workflow
1. Navigate to "📈 Analytics"
2. View overall dashboard with key metrics
3. Select time range (e.g., "Last 3 Months")
4. Review subject performance
5. Click subject to see trend
6. Scroll to topics and LOs
7. Identify strengths and weaknesses
8. Review engagement metrics

### Teacher Workflow - Class Analysis
1. Navigate to "📊 Performance Analytics"
2. Select filters (Grade 10, Section A, Last 6 Months)
3. Click "Apply Filters"
4. Review class average per subject
5. Examine LO mastery heatmap
6. Identify red zones (problem LOs)
7. Check at-risk students list
8. Plan interventions

### Teacher Workflow - Individual Student
1. Navigate to "📊 Performance Analytics"
2. Click "Individual Student" tab
3. Select student from dropdown
4. Review student's subject performance
5. Examine topic mastery
6. Identify strengths and weaknesses
7. Share insights with student/parents

### Teacher Workflow - Test Analysis
1. Navigate to "Tests Library"
2. Click on a completed test
3. Click "Analytics" button (or visit `/teacher/tests/<id>/analytics/`)
4. Review class statistics
5. Examine student rankings
6. Identify top performers and struggling students
7. Use insights for grade discussion

---

## Configuration

### Mastery Threshold
Currently hardcoded at **60%**. To change:
```python
# In core/analytics.py
if percentage >= 60:  # Change this value
    topic_data[topic_name]['correct'] += 1
```

### At-Risk Threshold
Currently **40%**. To change:
```python
# In core/analytics_views.py
at_risk = class_analytics.at_risk_students(threshold=40)  # Adjust threshold
```

### Trend Sensitivity
Currently slope > 2 = improving, < -2 = declining:
```python
# In core/analytics.py StudentAnalytics.subject_performance_trend()
if slope > 2:  # Adjust sensitivity
    trend = 'improving'
elif slope < -2:  # Adjust sensitivity
    trend = 'declining'
```

---

## Technical Notes

### Performance Considerations
- **Time Complexity**: Most operations are O(n) where n = number of answers
- **Space Complexity**: Metrics computed on-demand, not cached
- **Database Load**: One primary query per metric, with eager loading

### Future Optimization Opportunities
1. **Caching** - Redis/Memcached for computed metrics
2. **Materialized Views** - Pre-aggregate common queries
3. **Background Jobs** - Celery tasks for heavy computations
4. **Pagination** - For large student lists

### Security
- All views require `@login_required`
- Teacher views require `@staff_member_required`
- School-based filtering ensures data isolation
- No direct student ID exposure in student views

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/student/analytics/` | GET | Student analytics dashboard |
| `/teacher/analytics/` | GET | Teacher analytics dashboard |
| `/teacher/tests/<id>/analytics/` | GET | Individual test analytics |

### Query Parameters

**Student Analytics**:
- `range` - Time range (1m, 3m, 6m, 1y)
- `subject` - Filter to specific subject (optional)

**Teacher Analytics**:
- `range` - Time range (1m, 3m, 6m, 1y)
- `grade` - Grade ID filter
- `section` - Section name filter
- `group` - ClassGroup ID filter
- `view` - View type (overview, student, comparative)
- `student_id` - Student ID for individual view

---

## Troubleshooting

### No Data Showing
**Issue**: Empty states on all metrics
**Solution**:
- Ensure tests are published
- Ensure answers are graded (marks_awarded not null)
- Check date range includes graded submissions

### Incorrect Percentages
**Issue**: Percentages don't match expected values
**Solution**:
- Verify question marks are set correctly
- Check that marks_awarded ≤ question.marks
- Ensure division by zero protection

### Performance Issues
**Issue**: Slow page loads
**Solution**:
- Check number of answers in date range
- Consider adding database indexes
- Implement caching for repeat views

---

## Credits

**Designed for**: Lumen Assessment Platform v3
**Created**: January 2026
**Framework**: Django 4.2, Python 3.x
**UI Inspiration**: Modern educational dashboards, data visualization best practices

---

## Summary of Implemented Metrics

✅ **Implemented (Student View)**:
1. Performance across subjects
2. Subject performance trends
3. Performance across topics
4. LO performance
5. Strengths identification
6. Weaknesses identification
7. Persistent weak LOs
8. LO coverage
9. Topic coverage
10. Engagement metrics

✅ **Implemented (Teacher View)**:
11. Class average per subject
12. LO mastery heatmap
13. At-risk student identification
14. Individual student analysis
15. Test-level class statistics
16. Student rankings per test

⏳ **Partially Implemented**:
17. Comparative group analysis (structure ready)
18. Performance distribution (awaiting chart integration)

❌ **Not Yet Implemented**:
19. Question-level analysis
20. Assessment quality metrics
21. Predictive analytics

**Coverage**: 16/21 metrics fully functional, 2/21 partially ready
