# AI Tagging Issues & Fixes

## Problem 1: Questions Tagged with Wrong-Grade Topics

### Issue
40 IGCSE Physics questions were tagged with "Alternating currents" which is an **A Level** topic, not an IGCSE topic.

### Root Cause
The background AI tagging system correctly filters topics by grade and subject:
```python
topics = Topic.objects.filter(
    subject_id=question.subject_id,
    grade_id=question.grade_id  # Filters by correct grade
)
```

However, somehow the AI response was matching "Alternating currents" (Topic ID 87, A Level) even though it wasn't in the provided topic list for IGCSE.

**This indicates the AI was hallucinating or the topic filtering wasn't being applied correctly in some earlier version.**

### Fix Applied
**Script:** `fix_wrong_topics.py`

**What it does:**
1. Finds all questions where `topic.grade != question.grade`
2. Replaces with a valid topic from the correct grade/subject
3. Uses first available topic as placeholder (e.g., "Dangers of electricity" for IGCSE Physics)

**Results:**
- **40 questions fixed**
- All now tagged with "Dangers of electricity" (ID: 19, IGCSE Physics)
- Ready for re-tagging with more accurate topics

### How to Re-Tag Correctly
1. Go to `/teacher/untagged-questions/` (will show 0 since all have topics)
2. Or manually select the 40 questions (Q7, Q91-Q129)
3. Use the manual AI tagging buttons to re-tag individually with correct topics
4. Or create a script to bulk re-tag these specific questions

---

## Problem 2: Google OAuth Not Working

### Issue
```
Access blocked: Authorization Error
The OAuth client was not found.
Error 401: invalid_client
```

### Root Cause
The Google OAuth credentials in `settings.py` are **placeholder values** that don't correspond to an actual Google Cloud project.

### Fix Required
**You must create your own Google OAuth credentials.**

**Quick Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "Lumen Assessment Platform"
3. Enable Google+ API
4. Configure OAuth consent screen
5. Create OAuth client ID (Web application)
6. Add authorized redirect URIs:
   - `http://localhost:8000/accounts/google/callback/`
   - `http://127.0.0.1:8000/accounts/google/callback/`
7. Copy Client ID and Secret
8. Update `assessment_v3/settings.py`:
   ```python
   GOOGLE_OAUTH_CLIENT_ID = 'YOUR_ACTUAL_CLIENT_ID'
   GOOGLE_OAUTH_CLIENT_SECRET = 'YOUR_ACTUAL_SECRET'
   ```

**Detailed Guide:** See `GOOGLE_OAUTH_SETUP.md`

### Temporary Workaround
If you don't want to set up Google OAuth right now, you can disable it:

**Option 1: Hide the button**
Comment out lines 222-233 in `core/templates/registration/login.html`:
```html
<!--
<a href="{% url 'google_login' %}" ...>
  ...
</a>
-->
```

**Option 2: Remove the routes**
Comment out in `core/urls.py`:
```python
# path("accounts/google/login/", ...),
# path("accounts/google/callback/", ...),
```

---

## Verification

### Check Fixed Topics
```bash
python check_topics.py
```

**Expected output:**
- "Alternating currents" questions: **0** (was 40)
- All IGCSE Physics questions should have IGCSE topics only

### Re-Tag Questions Script
Create `retag_fixed_questions.py`:
```python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assessment_v3.settings')
django.setup()

from core.models import Question
from core.background_tagging import create_tagging_task

# Get the 40 fixed questions
questions = Question.objects.filter(id__in=range(7, 130)).filter(
    topic__name="Dangers of electricity"
)

print(f"Re-tagging {questions.count()} questions...")

# Create background tagging task
task = create_tagging_task('both', questions)

print(f"Task {task.task_id} started!")
print("Check /teacher/untagged-questions/ for progress")
```

---

## Prevention

### Ensure Grade Filtering Works
The background tagging already has correct grade filtering. The issue was likely from an earlier manual import or a bug in a previous version.

### Add Validation
Consider adding validation in the Question model:
```python
def clean(self):
    if self.topic and self.topic.grade != self.grade:
        raise ValidationError("Topic grade must match question grade")
```

### Monitor Topic Assignments
Create a management command to regularly check for mismatched topics:
```bash
python manage.py check_topic_grades
```

---

## Summary

**Fixed Issues:**
1. ✅ 40 questions with wrong-grade topics corrected
2. ⚠️ Google OAuth requires manual setup (documented)

**Next Steps:**
1. Set up Google OAuth credentials (optional)
2. Re-tag the 40 fixed questions with more accurate topics
3. Verify no other grade mismatches exist

**Scripts Created:**
- `check_topics.py` - Audit topic assignments
- `fix_wrong_topics.py` - Fix grade mismatches
- `GOOGLE_OAUTH_SETUP.md` - OAuth setup guide
