# Background AI Tagging System - User Guide

## Overview

The new background AI tagging system allows you to manage and tag untagged questions with **individual control** over topics and learning objectives. The tagging process **runs in the background** and continues even if you navigate away from the page.

---

## Features

### ✅ What's New

1. **Dedicated Untagged Questions View**
   - See all questions missing topics or LOs
   - Filter by: All, No Topic, No LOs
   - View question details before tagging

2. **Three Tagging Modes**
   - **Tag Topics Only** - Only assign topics
   - **Tag LOs Only** - Only assign learning objectives (requires topics)
   - **Tag Both Sequentially** - First topics, then LOs for all questions

3. **Background Processing**
   - Runs in a separate thread
   - Continues even if you close the page
   - Navigate freely while tagging happens

4. **Real-Time Progress**
   - Live progress bar
   - Questions processed count
   - Success/error statistics
   - Current question being processed

5. **Live Logging**
   - See what's happening in real-time
   - Toggle logs on/off
   - Color-coded messages (info, success, error)

---

## How to Access

### From Teacher Dashboard

1. Look for the **"Untagged Questions"** card
2. Shows count of untagged questions
3. Click **"🤖 Manage & Tag Questions"**

### Direct URL

Navigate to: `/teacher/untagged-questions/`

---

## The Untagged Questions Page

### Statistics Cards

At the top, you'll see 4 cards:

1. **Total Untagged** - Questions missing either topic or LOs
2. **Missing Topics** - Questions without a topic assigned
3. **Missing LOs** - Questions without learning objectives
4. **Ready to Tag** - Questions that can be tagged (have subject/grade)

### Action Buttons

Three main action buttons:

#### 1. 🏷️ Tag Topics Only

**Use When:**
- You only want to assign topics
- Questions already have LOs
- You want to review LOs manually later

**What It Does:**
- Analyzes each question
- Suggests and assigns topics
- Skips LO assignment

#### 2. 📚 Tag Learning Objectives Only

**Use When:**
- Questions already have topics
- You only need to add LOs
- Topics were manually assigned

**What It Does:**
- Uses existing topic to find relevant LOs
- Suggests and assigns LOs
- Skips questions without topics

#### 3. 🚀 Tag Topics + LOs (Sequential)

**Use When:**
- Questions need both topics and LOs
- You want complete tagging
- Starting from scratch

**What It Does:**
1. First pass: Tags all topics
2. Second pass: Tags LOs using the newly assigned topics
3. Complete tagging in one operation

**This is the RECOMMENDED option for fully untagged questions!**

---

## How Tagging Works

### Step 1: Click an Action Button

Choose one of the three tagging modes based on your needs.

### Step 2: Background Task Starts

- Task ID is generated
- Progress section appears
- Tagging begins immediately

### Step 3: Monitor Progress

Watch the real-time updates:

```
Processing...  15 / 85
───────────────────────────────────────
17% [████████░░░░░░░░░░░░░░░░░░░░░░░░]
───────────────────────────────────────
12 topics tagged • 8 LOs tagged • 0 errors
```

### Step 4: Live Logs (Optional)

Click **"Show Logs"** to see detailed processing:

```
[14:30:22] Processing question 15: What is photosynthesis?...
[14:30:24] ✓ Question 15 tagged with Topic: Photosynthesis
[14:30:26] ✓ Question 15 tagged with LOs: B.2.1, B.2.2
```

### Step 5: Navigate Away (Optional)

**You can:**
- Close the tab
- Navigate to other pages
- Work on other tasks

**The tagging continues in the background!**

### Step 6: Check Back Later

Return to the page to see:
- Final statistics
- Completion message
- Any errors encountered

Or check `/teacher/ai-logs/` for full details.

---

## Questions Table

### View All Untagged Questions

The bottom section shows all untagged questions in a table:

| Column | Description |
|--------|-------------|
| **Question** | Preview of question text |
| **Grade** | Grade level |
| **Subject** | Subject area |
| **Topic** | Current topic (or "Missing") |
| **Learning Objectives** | Count of LOs (or "Missing") |
| **Actions** | Edit link (opens in new tab) |

### Filter Options

Three filter buttons above the table:

- **All** - Show all untagged questions
- **No Topic** - Only questions missing topics
- **No LOs** - Only questions missing learning objectives

---

## Sequential Processing (Tag Both)

When you choose **"Tag Topics + LOs (Sequential)"**, here's what happens:

### Phase 1: Topic Tagging

```
Processing: Topics
───────────────────
Question 1: What is photosynthesis?
├─ Extract OCR from image (if present)
├─ Build context: Biology, Grade 10
├─ Available topics: 1. Cell Structure, 2. Photosynthesis...
├─ AI suggests: Topic #2 (Photosynthesis)
└─ ✓ Topic saved

Question 2: Explain cellular respiration...
├─ Extract OCR from image (if present)
├─ Build context: Biology, Grade 10
├─ AI suggests: Topic #2 (Photosynthesis and Respiration)
└─ ✓ Topic saved
```

### Phase 2: LO Tagging

```
Processing: Learning Objectives
───────────────────────────────
Question 1 (Topic: Photosynthesis)
├─ Available LOs: B.2.1, B.2.2, B.2.3...
├─ AI suggests: B.2.1, B.2.2
└─ ✓ LOs saved

Question 2 (Topic: Photosynthesis)
├─ Available LOs: B.2.1, B.2.2, B.2.3...
├─ AI suggests: B.2.2, B.2.3
└─ ✓ LOs saved
```

---

## Background Task Details

### How It Works

1. **Task Creation**
   - Unique task ID generated
   - Thread spawned for processing
   - Stored in memory

2. **Processing Loop**
   - Each question processed sequentially
   - AI services tried in order: LMStudio → Gemini → Anthropic
   - Results saved to database immediately

3. **Progress Tracking**
   - JavaScript polls every 2 seconds
   - Updates progress bar and statistics
   - Shows current question

4. **Task Completion**
   - Status changes to "completed" or "failed"
   - Polling stops
   - Page can refresh to show updated data

### Task Persistence

**Important Notes:**
- Tasks run in Python threads (in-memory)
- If Django server restarts, tasks are lost
- Completed data is safe (saved to database)
- For production, use Celery or similar for true background tasks

### Timeout & Retry

- Each AI service has 20-second timeout
- If one service fails, tries next service
- If all services fail, question is skipped
- Error is logged for review

---

## Error Handling

### Common Errors

#### "No models loaded"
**Cause**: LMStudio has no model loaded
**Solution**:
1. Open LMStudio
2. Load a model (Llama 3.1 8B recommended)
3. Try tagging again

#### "API key expired"
**Cause**: Google Gemini API key expired
**Solution**:
1. Get new key from https://aistudio.google.com/app/apikey
2. Set: `set GOOGLE_API_KEY=your-new-key`
3. Restart Django server

#### "No topics found for subject/grade"
**Cause**: Question has subject/grade, but no topics exist in database
**Solution**:
1. Create topics for that subject/grade combination
2. Or manually assign subject/grade to existing topics

#### "Missing subject or grade"
**Cause**: Question doesn't have subject or grade assigned
**Solution**:
1. Edit the question
2. Assign subject and grade
3. Run tagging again

### Viewing Detailed Errors

1. Click **"Show Logs"** on the tagging page
2. Look for red error messages
3. Or visit `/teacher/ai-logs/` for full log files

---

## Best Practices

### Before Tagging

1. **Load LMStudio Model**
   - Ensure LMStudio is running with a model loaded
   - Test with one question first

2. **Check Question Data**
   - Questions need subject and grade
   - Topics must exist for subject/grade combinations
   - LOs must exist for topics

3. **Review Statistics**
   - Check how many questions need tagging
   - Estimate time: ~6 seconds per question with LMStudio

### During Tagging

1. **Monitor Progress**
   - Watch for errors in real-time
   - Check if tagging is progressing

2. **Navigate Freely**
   - Feel free to work on other tasks
   - Check back periodically

3. **Don't Restart Server**
   - Background tasks are in-memory
   - Server restart will lose progress

### After Tagging

1. **Review Results**
   - Check `/teacher/ai-logs/` for full details
   - Spot-check some tagged questions

2. **Fix Errors**
   - Manually fix any questions that failed
   - Rerun tagging for failed questions

3. **Verify Accuracy**
   - AI suggestions may not be perfect
   - Manual review recommended for critical questions

---

## Performance

### Expected Timing

With LMStudio (local, 8B model):
- Topic tagging: ~3-5 seconds per question
- LO tagging: ~3-5 seconds per question
- Total (both): ~6-10 seconds per question

### Examples

| Questions | Topics Only | LOs Only | Both Sequential |
|-----------|-------------|----------|-----------------|
| 10 | ~40 seconds | ~40 seconds | ~1.5 minutes |
| 50 | ~3 minutes | ~3 minutes | ~6 minutes |
| 100 | ~6 minutes | ~6 minutes | ~12 minutes |
| 500 | ~30 minutes | ~30 minutes | ~60 minutes |

*Add 0.3s per question for rate limiting*

### Optimization Tips

1. **Use LMStudio**
   - Faster than cloud APIs
   - No rate limits
   - Free

2. **Smaller Models**
   - 3B models are faster
   - 7B-8B models are good balance
   - 70B+ models may be slow

3. **Batch Processing**
   - For 1000+ questions, tag in batches
   - Tag by subject/grade combinations
   - Easier to review and fix errors

---

## Troubleshooting

### Page Shows "No untagged questions"

**Possible Causes:**
1. All questions are tagged ✅
2. Questions belong to different school
3. User doesn't have permission

**Solutions:**
- Check question library
- Verify school filtering
- Try as admin/superuser

### Progress Bar Stuck

**Possible Causes:**
1. All AI services failing
2. LMStudio frozen
3. Network issues

**Solutions:**
- Check LMStudio is responding
- Refresh page and try again
- Check logs for specific errors

### "Task not found" Error

**Possible Causes:**
1. Server was restarted
2. Task ID is old
3. Task was cleaned up

**Solutions:**
- Start a new tagging task
- Background tasks don't survive restarts

---

## Comparison: Old vs New System

| Feature | Old System | New System |
|---------|------------|------------|
| **Interface** | Dashboard button | Dedicated page |
| **Visibility** | Hidden process | Full transparency |
| **Control** | All or nothing | Topics, LOs, or both |
| **Progress** | Basic bar | Detailed stats + logs |
| **Background** | Blocks page | True background |
| **Monitoring** | Limited | Real-time logs |
| **Filtering** | None | Filter by missing data |
| **Review** | After only | Before and during |

---

## FAQ

### Can I close the browser while tagging?
**No** - Background tasks run in Django process, not browser. You can navigate to other pages, but keep browser open.

### Will tagging continue if I log out?
**No** - Tasks are tied to Django process. Keep logged in and server running.

### Can I run multiple tagging tasks?
**Yes** - Each task gets unique ID. You can start multiple tasks for different modes.

### What if my computer goes to sleep?
**Task will pause** - When computer wakes, Django might have stopped the task. Check progress and restart if needed.

### How do I stop a running task?
**Currently not implemented** - Let it complete or restart Django server to force stop.

### Can I delete the logs?
**Yes** - Delete files from `logs/` folder. Or clear via `/teacher/ai-logs/` interface (if delete function added).

---

## Future Enhancements

Planned improvements:

1. **Persistent Background Tasks** - Use Celery for true background processing
2. **Task Cancellation** - Stop running tasks
3. **Email Notifications** - Get notified when large batches complete
4. **Batch Scheduling** - Schedule tagging for off-peak hours
5. **Selective Tagging** - Choose specific questions to tag
6. **Confidence Scores** - AI reports confidence in suggestions
7. **Manual Review Mode** - Approve AI suggestions before saving

---

## Technical Details

### Architecture

```
User clicks button
    ↓
Django view creates BackgroundTaggingTask
    ↓
Task spawns Python thread (daemon=True)
    ↓
Thread loops through questions:
    - Extract OCR
    - Build context-aware prompt
    - Try LMStudio → Gemini → Anthropic
    - Save to database
    ↓
JavaScript polls every 2 seconds for progress
    ↓
Updates UI with real-time status
    ↓
Task completes → Page can refresh
```

### Files Involved

- `core/templates/teacher/untagged_questions.html` - UI
- `core/background_tagging.py` - Background task logic
- `core/views.py` - View handlers
- `core/urls.py` - URL routing
- `core/ai_tagging_improved.py` - AI infrastructure

---

**Last Updated**: 2026-01-25
**Version**: 3.0 (Background Tagging System)
