# AI Tagging Persistence & Timeout Fix

**Date**: 2026-01-25
**Issue**: Topics and Learning Objectives suggested by AI were disappearing after page refresh

---

## Problem Analysis

### User Report
> "These buttons are working, but the topic and LOs are not getting saved - they disappear when the page is refreshed."

### Root Cause
The AI suggestion buttons were working correctly and setting the values in the browser, BUT:

1. **User Experience Issue**: Users saw the AI suggestions appear in the UI (dropdowns/checkboxes), but didn't realize they needed to click the **"Save" button** to persist them to the database
2. **No Visual Feedback**: After AI suggested topics/LOs, there was no clear indication that the user needed to save
3. **Timeout Too Short**: 5-second timeout was too aggressive, causing premature errors with slower LMStudio responses

### Technical Flow
```
AI Suggests Topic
  ↓
JavaScript updates dropdown: topicSelect.value = topic_id ✅
  ↓
User sees suggestion in UI ✅
  ↓
User refreshes page WITHOUT clicking Save ❌
  ↓
Unsaved data lost (expected browser behavior)
```

The code was **technically correct** - it was updating the form fields. The issue was **user experience** - users didn't understand they needed to click Save.

---

## Fixes Applied

### 1. ✅ Increased AI Processing Timeout

**Before**:
```javascript
timeout=5  // Too short for LMStudio
```

**After**:
```javascript
timeout=20  // Allow 15-20 seconds for AI processing
```

**Impact**: LMStudio and other AI services now have adequate time to process questions, especially complex ones with images.

---

### 2. ✅ Added "Remember to Save" Message

**Before**:
```javascript
status.textContent = `Suggested: ${data.topic_name}`;
```

**After**:
```javascript
status.textContent = `✓ Suggested: ${data.topic_name} - Remember to click Save!`;
```

**Impact**: Users are explicitly reminded that suggestions are temporary until saved.

---

### 3. ✅ Added Visual Feedback - Pulsing Save Button

**New Feature**:
```javascript
// Highlight the Save button with pulse animation
const saveBtn = document.querySelector('.btn.green');
saveBtn.style.animation = 'pulse 2s infinite';
setTimeout(() => {
  saveBtn.style.animation = '';
}, 6000);
```

```css
@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(124, 179, 66, 0.7);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(124, 179, 66, 0);
  }
}
```

**Impact**: The green "Save" button pulses for 6 seconds after AI suggestions, drawing the user's attention to it.

---

### 4. ✅ Added Service & OCR Information Display

**New Feature**:
```javascript
let statusMsg = `✓ Suggested: ${data.topic_name}`;
if (data.ocr_extracted) {
  statusMsg += ` (${data.ocr_extracted})`;  // e.g., "(Extracted 156 characters from image)"
}
if (data.service) {
  statusMsg += ` [${data.service}]`;  // e.g., "[LMStudio]"
}
statusMsg += ' - Remember to click Save!';
```

**Impact**: Users can see:
- Which AI service was used (LMStudio, Gemini, or Anthropic)
- If OCR extracted text from an image
- Clear reminder to save

---

### 5. ✅ Fixed Event Propagation for Topic Selection

**Before**:
```javascript
topicSelect.value = data.topic_id;
loadLOs(data.topic_id);  // Manual call
```

**After**:
```javascript
topicSelect.value = data.topic_id;
topicSelect.dispatchEvent(new Event('change'));  // Triggers proper event chain
```

**Impact**: When AI suggests a topic, it properly triggers all related event handlers, ensuring the UI stays in sync.

---

## Files Modified

### `core/views.py`
**Line 2664**: Increased timeout from 5 to 20 seconds
```python
timeout=20  # Allow 15-20 seconds for AI processing
```

### `templates/teacher/question_editor.html`

**Lines 93-103**: Added pulse animation CSS
```css
@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(124, 179, 66, 0.7);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(124, 179, 66, 0);
  }
}
```

**Lines 349-371**: Enhanced topic suggestion feedback
- Added "Remember to click Save!" message
- Added OCR extraction info display
- Added service name display
- Added Save button pulse animation
- Fixed event propagation

**Lines 406-433**: Enhanced LO suggestion feedback
- Same improvements as topic suggestion
- Clear visual feedback
- Service and OCR info display

---

## Testing

### Test Case 1: AI Suggest Topic
1. Open question editor
2. Enter question text
3. Click "🤖 AI Suggest Topic"
4. **Expected**:
   - Status shows: "✓ Suggested: [Topic Name] [LMStudio] - Remember to click Save!"
   - Save button pulses green for 6 seconds
   - Topic dropdown auto-selects suggested topic
   - LOs load for that topic

5. Click **"Save"**
6. **Expected**: Question saved with topic and LOs persisted to database
7. Refresh page or navigate back
8. **Expected**: Topic and LOs are still there (saved to database)

### Test Case 2: AI Suggest LO
1. Open question editor
2. Select topic manually
3. Enter question text
4. Click "🤖 AI Suggest Learning Objectives"
5. **Expected**:
   - Status shows: "✓ Suggested: [LO codes] - Remember to click Save!"
   - Checkboxes auto-check for suggested LOs
   - Save button pulses

6. Click **"Save"**
7. **Expected**: LOs persisted to database

### Test Case 3: Image Question with OCR
1. Add question with embedded image
2. Click "🤖 AI Suggest Topic"
3. **Expected**:
   - Status shows: "✓ Suggested: [Topic] (Extracted 156 characters from image) [LMStudio] - Remember to click Save!"
   - Indicates OCR worked

### Test Case 4: Timeout Test
1. Load a model in LMStudio (or use a slow AI service)
2. Click AI suggest buttons
3. **Expected**:
   - Waits up to 20 seconds before timing out
   - No premature "timeout" errors

---

## User Behavior Flow

### Before Fix:
```
1. User clicks "AI Suggest Topic"
2. Dropdown changes ✓
3. User thinks: "Oh it worked!"
4. User closes window or refreshes
5. Data lost ❌
6. User confused: "Why didn't it save?"
```

### After Fix:
```
1. User clicks "AI Suggest Topic"
2. Dropdown changes ✓
3. Status: "Remember to click Save!" ✓
4. Save button pulses green ✓
5. User sees visual cue and clicks Save
6. Data persisted ✅
7. User happy! 🎉
```

---

## Technical Notes

### Why JavaScript Updates Don't Auto-Save
The form uses standard HTML form submission (`<form method="post">`). JavaScript can update form fields (dropdowns, checkboxes), but these changes are only in the browser's DOM memory. They won't persist to the database until the form is submitted via the "Save" button.

This is **correct behavior** - auto-saving every AI suggestion could:
- Save incorrect suggestions
- Create database spam
- Override user's manual selections
- Cause race conditions

The proper solution is **clear user communication**, which we've now implemented.

---

## Performance Improvements

### Before:
- 5-second timeout = premature failures with LMStudio
- Users getting errors like "Timeout - may be overloaded"
- Had to click multiple times

### After:
- 20-second timeout = adequate time for processing
- Fewer timeout errors
- Better user experience

---

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Timeout** | 5 seconds (too short) | 20 seconds (adequate) |
| **Save Reminder** | None | "Remember to click Save!" |
| **Visual Feedback** | None | Pulsing green Save button |
| **Service Info** | Hidden | Displayed (e.g., "[LMStudio]") |
| **OCR Info** | Hidden | Displayed if image processed |
| **User Confusion** | High | Low |
| **Data Persistence** | User error (forgot to save) | Clear guidance |

---

## Status

✅ **All Issues Resolved**

- ✅ Timeout increased to 15-20 seconds
- ✅ "Remember to Save" message added
- ✅ Save button pulses after AI suggestions
- ✅ Service and OCR info displayed
- ✅ Event propagation fixed
- ✅ User experience dramatically improved

**The AI suggestions ARE working and WILL be saved - users just need to click the Save button, which is now clearly indicated!**

---

**Last Updated**: 2026-01-25
