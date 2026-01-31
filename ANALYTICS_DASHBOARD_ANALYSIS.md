# Analytics Dashboard Analysis - Issues & Fixes

## Current Issues

### 1. **Cognitive Rigor Radar (Bloom's Taxonomy)** ❌ FAKE DATA
**Location**: Line 246-262 in template
**Problem**: Hardcoded values `[85, 70, 45, 30, 15, 5]`
**Reality**: Not calculating actual Bloom's levels from questions

**What it should show**:
- Questions tagged with Bloom's taxonomy levels (Remember, Understand, Apply, Analyze, Evaluate, Create)
- Distribution of questions across these cognitive levels
- Student performance per cognitive level

**Current**: Shows fake static data regardless of actual test content

---

### 2. **LO Competency Matrix** ⚠️ PARTIALLY FAKE
**Location**: Line 168-199 in template
**Problem**: Line 192 uses `s.score >= 80` - checking TOTAL score, not per-LO performance

**What it should show**:
- Each cell = student's mastery of that specific Learning Objective
- Color based on student's performance on questions tagged with that LO
- Requires question-level LO tagging

**Current**: Colors all LOs the same for each student based on their total score only

---

### 3. **Cohort Performance Curve** ✅ REAL DATA (but could be better)
**Location**: Line 265-283 in template
**Backend**: Lines 3745-3758 in views.py

**Status**: CORRECT - Uses gaussian curve with actual mean and std dev
**Calculation**:
```python
pdf = (1 / (sigma * sqrt(2π))) * exp(-0.5 * ((x - mu) / sigma)²)
```

**Note**: The curve is drawn correctly over student score distribution

---

### 4. **Differentiated Groups** ❌ FAKE DATA
**Location**: Line 232-237 in template
**Problem**: Hardcoded text: "5 Candidates ready for Level 4 tasks" and "8 Candidates require re-teaching"

**What it should show**:
- Extension Group: Students scoring >80% (or top quartile)
- Intervention Group: Students scoring <50% (or bottom quartile)
- Actual student names and count from real data

**Current**: Shows made-up numbers regardless of actual results

---

### 5. **Reliability (α), Discrimination Index, Velocity** ❌ FAKE DATA
**Location**: Line 149-159 in template
**Problem**: Hardcoded values `0.82`, `0.41`, `+5.4%`

**What they should be**:
- **Reliability (Cronbach's α)**: Internal consistency measure (complex calculation)
- **Discrimination Index**: How well questions differentiate between high/low performers
- **Velocity**: Growth rate compared to previous test

**Current**: Shows static fake numbers

---

## Real Data vs. Fake Data Summary

| Component | Status | Data Source |
|-----------|--------|-------------|
| Mean Mastery | ✅ REAL | `analytics.distribution.mean` |
| Reliability (α) | ❌ FAKE | Hardcoded `0.82` |
| Discrimination Index | ❌ FAKE | Hardcoded `0.41` |
| Velocity | ❌ FAKE | Hardcoded `+5.4%` |
| **Cognitive Rigor Radar** | ❌ **FAKE** | **Hardcoded `[85, 70, 45, 30, 15, 5]`** |
| **LO Competency Matrix** | ⚠️ **PARTIAL** | **Uses total score, not per-LO** |
| Cohort Performance Curve | ✅ REAL | Gaussian curve from actual scores |
| Top Misconceptions | ✅ REAL | From `analytics.questions` |
| **Differentiated Groups** | ❌ **FAKE** | **Hardcoded "5 Candidates" / "8 Candidates"** |
| Examiner Report | ✅ REAL | Generated from actual data |

---

## Fixes Required

### Priority 1: Critical Fixes
1. ❌ **Cognitive Rigor Radar** - Calculate from question taxonomy tags
2. ❌ **LO Competency Matrix** - Per-student, per-LO performance
3. ❌ **Differentiated Groups** - Calculate from actual scores

### Priority 2: Nice-to-Have
4. ❌ **Reliability (α)** - Implement Cronbach's alpha
5. ❌ **Discrimination Index** - Calculate from high/low performer comparison
6. ❌ **Velocity** - Compare with previous test (requires historical data)

---

## Implementation Notes

### Cognitive Rigor Radar Fix
**Requires**: Questions must have Bloom's taxonomy tags
**Backend**: Aggregate questions by bloom_level, calculate student success per level
**Frontend**: Pass real data instead of `[85, 70, 45, 30, 15, 5]`

### LO Competency Matrix Fix
**Requires**: Questions must be tagged with Learning Objectives
**Backend**: For each (student, LO) pair, calculate % of marks earned
**Frontend**: Pass matrix data structure instead of using `s.score`

### Differentiated Groups Fix
**Backend**:
```python
extension_group = [s for s in students if s["score"] >= 80]
intervention_group = [s for s in students if s["score"] < 50]
```
**Frontend**: Use actual counts and names

---

## Next Steps

1. **Add Bloom's taxonomy field to Question model** (if not exists)
2. **Fix backend view** to calculate real data for all fake components
3. **Update template** to use real data from context
4. **Create 404 page** with consistent design language
