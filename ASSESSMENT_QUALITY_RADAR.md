# 📊 Assessment Quality Radar - Feature Documentation

## Overview

Replaced the **Cognitive Rigor Radar** (Bloom's Taxonomy) with a more meaningful **Assessment Quality Radar** that measures six key dimensions of test effectiveness.

---

## Why the Change?

### Problems with Bloom's Taxonomy Radar:
- ❌ Question model doesn't have a `bloom_level` field
- ❌ Used proxy mapping (question_type → Bloom's level) which is inaccurate
- ❌ Bloom's classification requires pedagogical judgment, not algorithmic mapping
- ❌ Not immediately actionable for teachers
- ❌ Doesn't measure test quality, just cognitive distribution

### Benefits of Assessment Quality Radar:
- ✅ All metrics calculated from real test data
- ✅ Directly measures test construction quality
- ✅ Actionable insights for improving assessments
- ✅ Industry-standard psychometric indicators
- ✅ No assumptions about question cognitive levels

---

## The Six Metrics

### 1. **Question Variety** (0-100%)
**What it measures**: Distribution of question types across the test

**Calculation**:
```python
question_types = {MCQ, Theory, Structured, Practical}
variety_score = (number_of_types_used / 4) * 100
```

**Interpretation**:
- **100%**: All 4 question types used (excellent variety)
- **75%**: 3 question types used (good variety)
- **50%**: 2 question types used (moderate)
- **25%**: Only 1 question type (poor variety)

**Why it matters**:
- Diverse question types assess different skills
- Reduces test bias towards specific learning styles
- Provides richer performance data

---

### 2. **Difficulty Balance** (0-100%)
**What it measures**: How well the test balances easy, medium, and hard questions

**Calculation**:
```python
# Ideal distribution: 20% easy, 60% medium, 20% hard
actual_distribution = {easy: X%, medium: Y%, hard: Z%}
balance_score = 100 - sum(|actual - ideal|) * 100
```

**Interpretation**:
- **90-100%**: Near-ideal balance
- **70-89%**: Good balance with minor skew
- **50-69%**: Moderate imbalance
- **<50%**: Poorly balanced (too easy or too hard)

**Why it matters**:
- Discriminates across full ability range
- Prevents floor/ceiling effects
- Maintains student motivation

---

### 3. **Discrimination Power** (0-100%)
**What it measures**: How well the test separates high performers from low performers

**Calculation**:
```python
top_27_percent = top performing students
bottom_27_percent = bottom performing students
discrimination_score = mean(top) - mean(bottom)
```

**Interpretation**:
- **70-100%**: Excellent discrimination
- **50-69%**: Good discrimination
- **30-49%**: Moderate discrimination
- **<30%**: Poor discrimination (test may be too easy/hard)

**Why it matters**:
- Validates test reliability
- Identifies students who truly understand vs. guessing
- Industry standard: 27% is statistically optimal (Johnson, 1951)

---

### 4. **Topic Coverage** (0-100%)
**What it measures**: Breadth of topics assessed in the test

**Calculation**:
```python
unique_topics = count of distinct topics in test
coverage_score = min(100, (unique_topics / 5) * 100)
```

**Interpretation**:
- **100%**: 5+ unique topics (comprehensive)
- **80%**: 4 unique topics (good coverage)
- **60%**: 3 unique topics (moderate)
- **<60%**: Narrow topic focus

**Why it matters**:
- Ensures curriculum alignment
- Prevents over-testing one area
- Provides balanced learning objective assessment

---

### 5. **Reliability Indicator** (0-100%)
**What it measures**: Consistency of test results (inverse of score variance)

**Calculation**:
```python
# Ideal std deviation: 15-20 for well-constructed tests
reliability_score = 100 - |std_dev - 17.5| * 3
```

**Interpretation**:
- **High score**: Scores cluster near ideal spread
- **Low score**: Too much or too little variance

**Why it matters**:
- **Low variance** (std < 10): Test may be too easy/hard for all
- **High variance** (std > 25): Test may have quality issues
- **Ideal variance** (std ≈ 15-20): Good differentiation without noise

**Technical note**: This is a proxy for Cronbach's alpha, which requires item-level variance calculation

---

### 6. **Performance Level** (0-100%)
**What it measures**: Overall cohort achievement

**Calculation**:
```python
performance_score = mean_score_of_all_students
```

**Interpretation**:
- **80-100%**: Excellent cohort performance
- **70-79%**: Good performance
- **60-69%**: Satisfactory performance
- **50-59%**: Below expectations
- **<50%**: Significant concerns

**Why it matters**:
- Validates instructional effectiveness
- Identifies need for remediation
- Benchmarks against expected outcomes

---

## Visual Design

### Radar Chart
- **Shape**: Hexagon (6 metrics)
- **Scale**: 0-100% for all axes
- **Color**: Blue (#1a73e8) with 20% fill opacity
- **Points**: Visible (3px) for precise reading

### Tooltips
Hover over any metric to see:
- **Full name**: E.g., "Question Type Variety"
- **Score**: Percentage value

### Labels
Abbreviated for readability:
- Variety
- Balance
- Discrimination
- Coverage
- Reliability
- Performance

---

## Interpreting the Radar

### Ideal Shape
A well-constructed test should show:
- **Balanced hexagon** (all metrics 70-100%)
- **No extreme spikes** (one metric 100%, others <50%)
- **No extreme dips** (one metric <30%)

### Common Patterns

#### Pattern: "Performance Spike"
```
Variety: 50%
Balance: 60%
Discrimination: 40%
Coverage: 70%
Reliability: 65%
Performance: 95% ← SPIKE
```
**Diagnosis**: Test is too easy
**Action**: Add harder questions, increase rigor

---

#### Pattern: "Variety Dip"
```
Variety: 25% ← DIP
Balance: 80%
Discrimination: 75%
Coverage: 85%
Reliability: 70%
Performance: 72%
```
**Diagnosis**: Only using 1 question type (probably all MCQ)
**Action**: Add Theory/Structured/Practical questions

---

#### Pattern: "Discrimination Dip"
```
Variety: 75%
Balance: 80%
Discrimination: 20% ← DIP
Coverage: 90%
Reliability: 40%
Performance: 50%
```
**Diagnosis**: Test doesn't separate high/low performers (too easy or too hard for everyone)
**Action**: Review question difficulty distribution

---

## Implementation Details

### Backend (`core/views.py`)

**Lines 3820-3878**: Assessment Quality Radar calculation
```python
# 1. Question Variety
question_types = count by type
variety_score = (types_used / 4) * 100

# 2. Difficulty Balance
difficulty_dist = {easy, medium, hard}
ideal = {0.2, 0.6, 0.2}
balance_score = 100 - deviation_from_ideal

# 3. Discrimination Power
top_27 = sorted_students[:n]
bottom_27 = sorted_students[-n:]
discrimination_score = avg_top - avg_bottom

# 4. Topic Coverage
unique_topics = count distinct topics
coverage_score = (unique_topics / 5) * 100

# 5. Reliability Indicator
reliability_score = 100 - |std - 17.5| * 3

# 6. Performance Level
performance_score = mean_score

assessment_quality_radar = [
    variety, balance, discrimination,
    coverage, reliability, performance
]
```

---

### Frontend (`analytics_dashboard.html`)

**Lines 165-167**: Card HTML
```html
<div class="card span-4">
    <h3>Assessment Quality Radar</h3>
    <p style="font-size: 11px; color: #5f6368;">
        Six key metrics for test effectiveness
    </p>
    <div style="flex: 1; min-height: 180px;">
        <canvas id="qualityRadar"></canvas>
    </div>
</div>
```

**Lines 274-311**: Chart.js configuration
```javascript
new Chart(document.getElementById('qualityRadar'), {
    type: 'radar',
    data: {
        labels: ['Variety', 'Balance', 'Discrimination',
                 'Coverage', 'Reliability', 'Performance'],
        datasets: [{
            label: 'Quality Score',
            data: {{ analytics.assessment_quality_radar|safe }},
            backgroundColor: 'rgba(26, 115, 232, 0.2)',
            borderColor: '#1a73e8',
            pointRadius: 3,
            pointBackgroundColor: '#1a73e8',
            borderWidth: 2
        }]
    },
    options: {
        plugins: {
            tooltip: {
                callbacks: {
                    title: function(context) {
                        const labels = {
                            'Variety': 'Question Type Variety',
                            'Balance': 'Difficulty Balance',
                            'Discrimination': 'Discrimination Power',
                            'Coverage': 'Topic Coverage',
                            'Reliability': 'Consistency Indicator',
                            'Performance': 'Overall Performance'
                        };
                        return labels[context[0].label];
                    },
                    label: function(context) {
                        return context.parsed.r.toFixed(1) + '%';
                    }
                }
            }
        },
        scales: { r: { min: 0, max: 100 } }
    }
});
```

---

## Data Accuracy

✅ **100% Real Data** - All six metrics calculated from:
- Actual question types in test
- Actual student performance data
- Actual topic distribution
- Actual score statistics

❌ **No Fake Data** - Unlike the old Bloom's taxonomy which used proxy mappings

---

## Testing Checklist

To verify this feature:

- [ ] Navigate to `/teacher/tests/<test_id>/analytics/`
- [ ] Locate "Assessment Quality Radar" card (top right)
- [ ] Verify you see 6 axes: Variety, Balance, Discrimination, Coverage, Reliability, Performance
- [ ] Hover over each point to see tooltip with full metric name and percentage
- [ ] Check that values change when you:
  - [ ] Add questions of different types
  - [ ] Modify question difficulty
  - [ ] Change student performance data

---

## Comparison with Old System

| Aspect | Bloom's Taxonomy (OLD) | Assessment Quality (NEW) |
|--------|----------------------|-------------------------|
| **Data Source** | Proxy mapping (question_type → level) | Real test statistics |
| **Accuracy** | ❌ Inaccurate without bloom_level field | ✅ Calculated from actual data |
| **Actionability** | Low - requires pedagogical interpretation | High - direct quality metrics |
| **Industry Standard** | No - Bloom's is for curriculum design | Yes - discrimination, reliability, etc. |
| **Teacher Value** | Limited - doesn't help improve tests | High - clear improvement targets |

---

## Future Enhancements

### Phase 2 (Optional):
1. **Add benchmark comparison**: Compare to school/district averages
2. **Historical trending**: Track quality metrics over time
3. **Auto-recommendations**: Suggest specific questions to add/remove
4. **Item Response Theory (IRT)**: Advanced psychometric modeling
5. **Cronbach's Alpha**: Replace reliability proxy with actual calculation

---

## References

- **Discrimination Index**: Johnson, A. P. (1951). "Notes on a suggested index of item validity"
- **Difficulty Distribution**: Ebel, R. L. (1979). "Essentials of Educational Measurement"
- **Test Reliability**: Cronbach, L. J. (1951). "Coefficient alpha and the internal structure of tests"

---

## Result

The Assessment Quality Radar provides **actionable, data-driven insights** into test construction quality, replacing the theoretical Bloom's taxonomy with practical metrics teachers can use to improve their assessments.

---

**Last Updated**: 2026-01-31
**Feature**: Assessment Quality Radar (replaces Cognitive Rigor Radar)
