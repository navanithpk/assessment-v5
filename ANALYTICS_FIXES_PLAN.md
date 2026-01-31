# Analytics Dashboard Fixes - Implementation Plan

## Summary of Issues & Proposed Fixes

### ✅ What's Already REAL:
- **Mean Mastery** (class average)
- **Cohort Performance Curve** (Gaussian distribution)
- **Top Misconceptions** (distractor analysis from questions)
- **Examiner's Narrative** (generated from actual data)

### ❌ What's FAKE (Needs Fixing):

---

## Fix 1: Cognitive Rigor Radar (Bloom's Taxonomy)

### Current Problem:
```javascript
// Hardcoded fake data
data: [85, 70, 45, 30, 15, 5]
```

### Proposed Solution:
Since questions don't have Bloom's taxonomy tags yet, we have three options:

**Option A: Use Question Type as Proxy**
- MCQ → Lower cognitive (Remember/Understand)
- Theory → Mid cognitive (Apply/Analyze)
- Structured → Higher cognitive (Analyze/Evaluate)
- Practical → Highest cognitive (Evaluate/Create)

**Option B: Infer from Marks**
- Low marks (1-2) → Remember/Understand
- Mid marks (3-5) → Apply/Analyze
- High marks (6+) → Evaluate/Create

**Option C: Add Bloom's Field to Model** (Best, but requires migration)
```python
# Add to Question model
bloom_level = models.CharField(
    max_length=20,
    choices=[
        ('remember', 'Remember'),
        ('understand', 'Understand'),
        ('apply', 'Apply'),
        ('analyze', 'Analyze'),
        ('evaluate', 'Evaluate'),
        ('create', 'Create'),
    ],
    null=True, blank=True
)
```

**Recommendation**: Start with **Option A** (quick fix), add **Option C** later for accuracy.

### Backend Changes:
```python
# In views.py - test_analytics_view
bloom_distribution = defaultdict(lambda: {"correct": 0, "total": 0})

for q in questions:
    # Map question_type to bloom level (Option A)
    if q.question_type == 'mcq':
        level = 'remember' if q.marks <= 2 else 'understand'
    elif q.question_type == 'theory':
        level = 'apply'
    elif q.question_type == 'structured':
        level = 'analyze'
    else:  # practical
        level = 'evaluate'

    # Calculate success rate for this level
    q_answers = answers.filter(question=q)
    correct = q_answers.filter(marks_awarded__gte=float(q.marks) * 0.7).count()

    bloom_distribution[level]["correct"] += correct
    bloom_distribution[level]["total"] += q_answers.count()

# Calculate percentages
bloom_data = []
for level in ['remember', 'understand', 'apply', 'analyze', 'evaluate', 'create']:
    if bloom_distribution[level]["total"] > 0:
        percentage = (bloom_distribution[level]["correct"] / bloom_distribution[level]["total"]) * 100
    else:
        percentage = 0
    bloom_data.append(round(percentage, 1))

context["analytics"]["bloom_taxonomy"] = bloom_data
```

### Frontend Changes:
```javascript
// Replace hardcoded data with:
data: {{ analytics.bloom_taxonomy|safe }}
```

---

## Fix 2: LO Competency Matrix

### Current Problem:
```django
{# Uses total student score for ALL LOs #}
{% if s.score >= 80 %}m-mastery{% elif s.score >= 50 %}m-developing{% else %}m-critical{% endif %}
```

### Proposed Solution:
Calculate per-student, per-LO performance matrix.

### Backend Changes:
```python
# In views.py - test_analytics_view

# Build LO performance matrix
lo_matrix = {}  # {student_id: {lo_id: {earned, max}}}

for a in answers:
    sid = a.student_id

    # Get all LOs for this question
    for lo in a.question.learning_objectives.all():
        if sid not in lo_matrix:
            lo_matrix[sid] = {}
        if lo.id not in lo_matrix[sid]:
            lo_matrix[sid][lo.id] = {"earned": 0.0, "max": 0.0}

        # Distribute marks proportionally if question has multiple LOs
        lo_count = a.question.learning_objectives.count()
        proportion = 1 / lo_count if lo_count > 0 else 1

        lo_matrix[sid][lo.id]["earned"] += float(a.marks_awarded) * proportion
        lo_matrix[sid][lo.id]["max"] += float(a.question.marks) * proportion

# Convert to template-friendly format
for s in students:
    s["lo_performance"] = {}
    for lo in learning_objectives:
        if s["id"] in lo_matrix and lo["id"] in lo_matrix[s["id"]]:
            data = lo_matrix[s["id"]][lo["id"]]
            percentage = (data["earned"] / data["max"]) * 100 if data["max"] > 0 else 0
            s["lo_performance"][lo["id"]] = round(percentage, 1)
        else:
            s["lo_performance"][lo["id"]] = None  # No questions for this LO
```

### Frontend Changes:
```django
{% for lo in analytics.learning_objectives %}
    {% with perf=s.lo_performance|get_item:lo.id %}
        {% if perf == None %}
            <td style="background: #e0e0e0;" title="No data"></td>
        {% elif perf >= 80 %}
            <td class="m-mastery" title="{{ perf }}%"></td>
        {% elif perf >= 50 %}
            <td class="m-developing" title="{{ perf }}%"></td>
        {% else %}
            <td class="m-critical" title="{{ perf }}%"></td>
        {% endif %}
    {% endwith %}
{% endfor %}
```

**Note**: Requires template filter for dict access. Add to templatetags:
```python
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
```

---

## Fix 3: Differentiated Groups

### Current Problem:
```django
<p><strong>Extension Group:</strong> 5 Candidates ready for Level 4 tasks.</p>
<p><strong>Intervention Group:</strong> 8 Candidates require re-teaching...</p>
```

### Proposed Solution:
Calculate from actual student scores.

### Backend Changes:
```python
# In views.py - test_analytics_view

# Calculate differentiated groups
extension_threshold = 80  # Top performers
intervention_threshold = 50  # Needs support

extension_group = [s for s in students if s["score"] >= extension_threshold]
intervention_group = [s for s in students if s["score"] < intervention_threshold]

# Identify common weak LO for intervention group
if intervention_group:
    weak_los = []
    for lo in learning_objectives:
        if lo["band"] == "weak":
            weak_los.append(lo["name"])
    primary_weak_lo = weak_los[0] if weak_los else "fundamental concepts"
else:
    primary_weak_lo = ""

context["analytics"]["differentiated_groups"] = {
    "extension": {
        "count": len(extension_group),
        "students": [s["name"] for s in extension_group[:5]],  # First 5 names
    },
    "intervention": {
        "count": len(intervention_group),
        "students": [s["name"] for s in intervention_group[:5]],
        "focus_area": primary_weak_lo
    }
}
```

### Frontend Changes:
```django
<div style="font-size: 13px;">
    {% if analytics.differentiated_groups.extension.count > 0 %}
    <p>
        <strong>Extension Group:</strong>
        {{ analytics.differentiated_groups.extension.count }} Candidate{{ analytics.differentiated_groups.extension.count|pluralize }} ready for enrichment.
        <br><small style="color: #666;">{{ analytics.differentiated_groups.extension.students|join:", " }}</small>
    </p>
    {% endif %}

    {% if analytics.differentiated_groups.intervention.count > 0 %}
    <p>
        <strong>Intervention Group:</strong>
        {{ analytics.differentiated_groups.intervention.count }} Candidate{{ analytics.differentiated_groups.intervention.count|pluralize }} require re-teaching on
        <strong>{{ analytics.differentiated_groups.intervention.focus_area }}</strong>.
        <br><small style="color: #666;">{{ analytics.differentiated_groups.intervention.students|join:", " }}</small>
    </p>
    {% endif %}
</div>
```

---

## Fix 4: Advanced Metrics (Optional - Complex)

### Reliability (Cronbach's α)
**Complexity**: High
**Formula**: α = (k/(k-1)) × (1 - Σσᵢ²/σₜ²)
**Requires**: Item-level variance calculations
**Recommendation**: Implement later if needed

### Discrimination Index
**Complexity**: Medium
**Formula**: DI = (% High Group Correct) - (% Low Group Correct)
**Implementation**:
```python
# Split into high/low groups (top 27% vs bottom 27%)
sorted_students = sorted(students, key=lambda x: x["score"])
n = len(sorted_students)
high_group = sorted_students[int(n * 0.73):]
low_group = sorted_students[:int(n * 0.27)]

# For each question, calculate DI
# Average across all questions for overall index
```

### Velocity (Growth Rate)
**Complexity**: Medium
**Requires**: Historical test data
**Recommendation**: Implement when comparing multiple tests

---

## Fix 5: Custom 404 Page

### Create: `templates/404.html`
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - Page Not Found | Lumen</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
        }
        .container {
            text-align: center;
            max-width: 600px;
            padding: 40px;
        }
        .error-code {
            font-size: 120px;
            font-weight: 700;
            line-height: 1;
            margin-bottom: 20px;
            text-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        h1 {
            font-size: 32px;
            margin-bottom: 16px;
        }
        p {
            font-size: 18px;
            opacity: 0.9;
            margin-bottom: 32px;
            line-height: 1.6;
        }
        .btn {
            display: inline-block;
            padding: 14px 32px;
            background: white;
            color: #667eea;
            text-decoration: none;
            border-radius: 30px;
            font-weight: 600;
            transition: transform 0.2s;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-code">404</div>
        <h1>Oops! Page Not Found</h1>
        <p>The page you're looking for seems to have wandered off. It might have been moved, deleted, or perhaps it never existed.</p>
        <a href="/" class="btn">← Back to Home</a>
    </div>
</body>
</html>
```

### Update: `settings.py`
```python
# Add to settings.py
DEBUG = False  # For 404 page to work
ALLOWED_HOSTS = ['*']  # Or specific domains

# Handler404
handler404 = 'core.views.custom_404'
```

### Create: Handler in `views.py`
```python
def custom_404(request, exception=None):
    return render(request, '404.html', status=404)
```

---

## Implementation Priority

### Phase 1 (Quick Wins - 30 mins):
1. ✅ Fix Differentiated Groups
2. ✅ Create 404 page

### Phase 2 (Medium - 1 hour):
3. ✅ Fix Cognitive Rigor Radar (Option A)
4. ✅ Fix LO Competency Matrix

### Phase 3 (Advanced - Later):
5. ⏳ Add Bloom's taxonomy field to model
6. ⏳ Implement Discrimination Index
7. ⏳ Implement Velocity tracking

---

## Testing Checklist

After implementation:
- [ ] Cognitive Rigor Radar shows different values for different tests
- [ ] LO Matrix cells vary by student and LO
- [ ] Differentiated Groups show actual student names
- [ ] Differentiated Groups count matches filtered students
- [ ] 404 page displays when accessing invalid URL
- [ ] Normal curve remains accurate

---

**Ready to implement?** Should I proceed with Phase 1 & 2 fixes?
