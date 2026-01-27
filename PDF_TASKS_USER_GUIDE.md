# PDF Tasks - Quick User Guide

## How to Access

1. Login to Lumen as a teacher
2. Look at the sidebar on the left
3. Under "Assessments" section, click **📋 PDF Import Tasks**

## What You'll See

### Dashboard Sections

The PDF Tasks page is divided into four main sections:

#### 1. **⏳ Pending** (Yellow badges)
Tasks that are waiting to be started or resumed.

**What you'll see**:
- Task name (e.g., "Biology A-Level 2024 Papers")
- Grade • Subject • Year
- Progress: "X/Y files processed" with progress bar
- "Created X time ago"

**Available actions**:
- ▶️ **Resume** - Continue working on this task
- ✅ **Mark Complete** - Mark as finished without processing all files
- 🗑️ **Delete** - Remove this task permanently

#### 2. **🔄 In Progress** (Blue badges)
Tasks you're currently working on.

**What you'll see**:
- Same info as Pending
- "Last updated X time ago" instead of creation time

**Available actions**:
- ▶️ **Continue** - Keep working
- ⏸️ **Pause** - Temporarily stop (move to Paused section)
- ✅ **Complete** - Mark as finished

#### 3. **⏸️ Paused** (Red badges)
Tasks that were temporarily stopped.

**What you'll see**:
- Same basic info
- "Paused X time ago"

**Available actions**:
- ▶️ **Resume** - Pick up where you left off
- 🗑️ **Delete** - Remove permanently

#### 4. **✅ Recently Completed** (Green badges)
Last 10 tasks you finished (shown with slight transparency).

**What you'll see**:
- Task name and metadata
- "Completed X time ago • Y files processed"

**Available actions**:
- 🗑️ **Remove** - Delete from completed list

## Common Workflows

### Starting a New PDF Import

1. Click "➕ New Import" button (top right of PDF Tasks page)
   - Or go to **Question Library → Import from PDF**

2. Upload your PDFs

3. A new task is automatically created and appears in **Pending** section

4. Start processing the PDFs

### Resuming an Interrupted Session

**Scenario**: You started importing PDFs yesterday but didn't finish.

**Steps**:
1. Go to **PDF Import Tasks** from sidebar
2. Find your task in **Pending** or **Paused** section
3. Click **▶️ Resume**
4. You'll be taken back to the PDF slicer with all your previous work saved
5. Continue from where you left off

### Taking a Break During Long Imports

**Scenario**: You're processing 20 PDFs and need to take a lunch break.

**Steps**:
1. While in the PDF import interface, just close the browser or logout
2. The task automatically saves your progress
3. When you return:
   - Go to **PDF Import Tasks**
   - Your task will be in **In Progress** or **Paused**
   - Click **▶️ Continue** or **▶️ Resume**

### Cleaning Up Finished Work

**Scenario**: You have many completed tasks cluttering the list.

**Steps**:
1. Scroll to **Recently Completed** section
2. Click **🗑️ Remove** on tasks you no longer need
3. Completed tasks are deleted permanently (questions remain safe)

## Understanding Progress Bars

Each task shows a progress indicator:

```
📊 Progress: 15/20 files processed [■■■■■■■□□□] 75%
```

- **15/20** = 15 files done, 20 total
- **Progress bar** = Visual representation
- **75%** = Percentage complete

## Task Information Display

Each task card shows:

```
┌─────────────────────────────────────────┐
│ Biology A-Level 2024 Papers     [PENDING]│
│ A-Level • Biology • Year 2024           │
│                                         │
│ Progress: 15/20 files processed  75%    │
│ [■■■■■■■□□□]                           │
│                                         │
│ Created 2 hours ago                     │
│                                         │
│ [▶️ Resume] [✅ Complete] [🗑️ Delete]  │
└─────────────────────────────────────────┘
```

## Tips & Best Practices

### 1. Use Descriptive Names
When creating import sessions, use clear names:
- ✅ Good: "Biology A-Level 2024 Papers 1-5"
- ✅ Good: "Chemistry AS-Level 2023 All Variants"
- ❌ Bad: "Import 1"
- ❌ Bad: "PDFs"

### 2. Don't Delete Active Work
- Only delete tasks you're sure you don't need
- Deletion is permanent (but created questions remain safe)
- Use **Pause** instead of **Delete** if you might come back

### 3. Monitor Your Progress
- Check the progress bars to see how much is left
- Tasks with low progress might be good candidates to resume first

### 4. Clean Up Regularly
- Delete completed tasks you no longer need
- Keeps the list manageable
- Improves page load time

### 5. One Task at a Time
- Focus on completing one task before starting another
- Use the Pause feature to manage multiple tasks

## Duplicate Detection

### What Happens

When you upload a PDF that has already been processed:

```
⚠️ DUPLICATE PDF DETECTED

File: Biology_2024_P1.pdf
Already processed on: January 24, 2026 at 3:45 PM
Processed by: teacher@example.com
Questions created: 25
Grade: A-Level
Subject: Biology
Year: 2024

Do you want to process this PDF again?
[Yes, Process Again]  [No, Skip This File]
```

### What to Do

**If you click "Yes, Process Again"**:
- The PDF will be processed again
- New questions will be created (duplicates of existing ones)
- Previous questions remain unchanged

**If you click "No, Skip This File"**:
- The PDF is skipped
- Other PDFs in the queue continue processing
- No new questions from this file

### Why This Helps

- **Prevents Accidents**: Won't accidentally create duplicate questions
- **Saves Time**: Know which files you've already done
- **Transparency**: See when and who processed each file

## Troubleshooting

### Task Not Showing Up

**Problem**: I created a task but don't see it.

**Solutions**:
1. Make sure you're logged in as the same user who created it
2. Check all sections (Pending, In Progress, Paused, Completed)
3. Refresh the page (F5)
4. Check if it was accidentally deleted

### Can't Resume Task

**Problem**: Resume button doesn't work.

**Solutions**:
1. Check your internet connection
2. Make sure the task is in Pending or Paused status
3. Try logging out and back in
4. Contact support if issue persists

### Progress Not Updating

**Problem**: Progress bar stuck at old percentage.

**Solutions**:
1. Refresh the page to see latest progress
2. Check if the task is actually paused
3. Verify you're processing files from this task

### Lost My Work

**Problem**: I was importing PDFs and my browser crashed.

**Good News**: Your work is saved!

**Steps**:
1. Restart browser and login
2. Go to PDF Import Tasks
3. Find your task (probably in "In Progress")
4. Click Resume
5. Continue from last saved point

## Keyboard Shortcuts (Planned)

Future versions will support:
- `Shift + Left Arrow` - Previous file in queue
- `Shift + Right Arrow` - Next file in queue
- `Ctrl + S` - Save current progress
- `Ctrl + P` - Pause current task

## Status Badge Colors

- 🟡 **Yellow (Pending)** - Not started yet
- 🔵 **Blue (In Progress)** - Currently working
- 🔴 **Red (Paused)** - Temporarily stopped
- 🟢 **Green (Completed)** - All done

## Empty State

If you see this:

```
📋
No PDF processing tasks yet
Start importing questions from PDFs to see tasks here

[➕ Start New Import]
```

It means:
- You haven't created any PDF import tasks yet
- Click the button to start your first import

## API Integration (For Developers)

The PDF Tasks system provides JSON endpoints for building custom interfaces:

- Check duplicate: `POST /teacher/pdf-tasks/check-duplicate/`
- Mark processed: `POST /teacher/pdf-tasks/mark-processed/`

See `PDF_TASK_MANAGEMENT.md` for full API documentation.

---

## Quick Reference Card

### Task States
| State | Icon | Color | Meaning |
|-------|------|-------|---------|
| Pending | ⏳ | Yellow | Waiting to start |
| In Progress | 🔄 | Blue | Currently working |
| Paused | ⏸️ | Red | Temporarily stopped |
| Completed | ✅ | Green | Finished |

### Available Actions by State

| State | Resume | Pause | Complete | Delete |
|-------|--------|-------|----------|--------|
| Pending | ✅ | ❌ | ✅ | ✅ |
| In Progress | ✅ | ✅ | ✅ | ❌ |
| Paused | ✅ | ❌ | ❌ | ✅ |
| Completed | ❌ | ❌ | ❌ | ✅ |

---

**Need More Help?**
- See `PDF_TASK_MANAGEMENT.md` for technical details
- See `COMPLETED_FEATURES_SUMMARY.md` for implementation details
- Contact your system administrator

---

**Last Updated**: January 25, 2026
**Version**: Lumen v3.1
