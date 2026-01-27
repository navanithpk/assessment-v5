# Non-MCQ Prototype - Development Progress

## Goal
Build a working proof-of-concept for structured question papers with multi-page support and answer spaces.

## Prototype Scope (Week 1)

### Features to Implement
1. ✅ **Database Models** - Core schema for answer spaces
2. 🔄 **Multi-page PDF Stitching** - Combine pages into single question images
3. ⏳ **Answer Space Placement** - Teacher UI to place text boxes on questions
4. ⏳ **Student Text Interface** - Rich text editor for answers
5. ⏳ **Answer Rasterization** - Convert HTML to PNG and overlay
6. ⏳ **Basic Grading View** - Display composite answer images

### What's NOT in Prototype
- ❌ Calculation spaces (canvas + answer box)
- ❌ Table cell editing
- ❌ Drawing canvas
- ❌ OCR text extraction
- ❌ AI grading suggestions
- ❌ Advanced UI polish

---

## Progress Log

### Day 1 - January 26, 2026

#### ✅ Completed: Database Models

**Created 3 new models:**

1. **AnswerSpace**
   - Defines answer regions on questions
   - Fields: position (x, y, width, height), type, config (JSON), marks
   - Supports 4 types (text_line, calc_space, table_cell, canvas)
   - Prototype focuses on `text_line` type

2. **StudentAnswerSpace**
   - Stores student responses to answer spaces
   - Fields: text_response, canvas_data, rasterized_image
   - Links to StudentAnswer and AnswerSpace
   - Includes grading fields (marks_awarded, feedback)

3. **QuestionPage**
   - Tracks multi-page questions
   - Fields: page_number, page_image, markers (green/red lines), bounds (blue rectangle)
   - Enables page stitching algorithm

**Migration:**
- Created: `core/migrations/0013_answerspace_studentanswerspace_questionpage.py`
- Applied successfully to database
- All models registered

**Files Modified:**
- `core/models.py` (added ~130 lines)

---

## Next Steps

### Immediate (Today)

#### Step 2: Multi-page PDF Stitching Algorithm

**What to Build:**
```python
def stitch_question_pages(pages):
    """
    Combine multiple pages into single tall question image

    Args:
        pages: QuerySet of QuestionPage ordered by page_number

    Returns:
        base64 encoded PNG of stitched image

    Logic:
        1. Find first page with green_line
        2. Collect all pages until red_line found
        3. For each page, crop to blue_rect bounds
        4. Stack vertically into single image
        5. Return as base64 PNG
    """
```

**Files to Create/Modify:**
- `core/utils/image_processing.py` - New utility module
- `core/views.py` - Add stitching to import flow

**Testing:**
- Single page (green + red on same page)
- Two pages (green on page 1, red on page 2)
- Three pages (green on 1, continuation on 2, red on 3)

---

### Tomorrow

#### Step 3: Answer Space Placement UI

**What to Build:**
- Question editor page showing stitched question image
- Click-to-place answer space tool
- Drag handles to resize
- Save positions to database

**UI Mockup:**
```
┌────────────────────────────────────────┐
│  Question Editor                       │
├────────────────────────────────────────┤
│  [Add Text Line] [Save Spaces]         │
├────────────────────────────────────────┤
│                                        │
│  ┌──────────────────────────────────┐ │
│  │                                  │ │
│  │  [Question Image]                │ │
│  │                                  │ │
│  │  ┌────────answer space──────┐   │ │
│  │  │ Editable text area        │   │ │
│  │  │ (drag to resize)          │   │ │
│  │  └───────────────────────────┘   │ │
│  │                                  │ │
│  └──────────────────────────────────┘ │
│                                        │
└────────────────────────────────────────┘
```

---

### Day After Tomorrow

#### Steps 4-6: Student Interface + Rasterization + Grading

Quick implementations to complete the full workflow.

---

## Technical Architecture

### Data Flow

```
Teacher Workflow:
1. Upload PDF → Pages stored in QuestionPage
2. System detects green/red lines
3. Stitch pages → Create single question image
4. Place answer spaces → Save to AnswerSpace
5. Publish test

Student Workflow:
1. View test → Load question with answer spaces
2. Type in rich text editor → Auto-save to StudentAnswerSpace
3. Submit → Trigger rasterization

Rasterization:
1. Get HTML from rich text editor
2. Render HTML to canvas (html2canvas.js)
3. Export as PNG
4. Save as base64 in rasterized_image field

Grading:
1. Load question image
2. Load rasterized answer overlays
3. Composite images (question + answers)
4. Display to teacher
5. Manual grading
```

### Libraries Needed

**Frontend:**
- `html2canvas.js` - Convert HTML to PNG
- Quill.js (already in system) - Rich text editor

**Backend:**
- Pillow (already installed) - Image processing
- Base64 encoding - Built-in Python

---

## Testing Strategy

### Unit Tests
- [ ] Page stitching with 1, 2, 3 pages
- [ ] Answer space CRUD operations
- [ ] Rasterization accuracy

### Integration Tests
- [ ] Full flow: Import → Place → Answer → Grade
- [ ] Multi-page question handling
- [ ] Answer persistence

### Manual Testing
- [ ] Create test with 2-page question
- [ ] Student answers with rich text
- [ ] Verify overlay positioning
- [ ] Check grading view

---

## Known Limitations (Prototype)

1. **Text-only answer spaces** - No canvas/drawing yet
2. **Manual page marking** - Teacher marks green/red lines manually
3. **Basic rasterization** - Simple HTML to PNG
4. **No OCR** - Manual grading only
5. **Single question type** - Only structured questions

---

## Success Criteria

The prototype is successful if:
- ✅ Can import multi-page PDF
- ✅ Pages stitch correctly into single image
- ✅ Teacher can place answer spaces
- ✅ Student can type rich text answers
- ✅ Answers rasterize and overlay correctly
- ✅ Teacher sees composite answer images

If all criteria met → Proceed with full implementation
If issues found → Revise approach

---

## Timeline

| Day | Task | Status |
|-----|------|--------|
| Mon Jan 26 | Database models | ✅ Done |
| Tue Jan 27 | PDF stitching algorithm | 🔄 In Progress |
| Wed Jan 28 | Answer space placement UI | ⏳ Pending |
| Thu Jan 29 | Student interface + Rasterization | ⏳ Pending |
| Fri Jan 30 | Grading view + Testing | ⏳ Pending |

**Target Completion:** Friday, January 30, 2026

---

## Current Status

**Overall Progress:** 15% (1/6 tasks complete)

**What's Working:**
- ✅ Database schema created and migrated
- ✅ Models registered in Django admin
- ✅ Foundation ready for implementation

**What's Next:**
- 🔄 Building page stitching algorithm
- ⏰ ETA: 4-6 hours

---

**Last Updated:** January 26, 2026, 1:00 AM
**Developer:** Claude (Lumen Team)
**Status:** Active Development
