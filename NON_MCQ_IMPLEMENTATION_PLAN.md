# Non-MCQ Paper System - Implementation Plan

## Executive Summary

This document outlines the implementation plan for a comprehensive non-MCQ assessment system that supports:
- Multi-page question handling
- Multiple answer space types (text lines, calculation spaces, tables, drawing canvas)
- Student interactive answering with rich text editor and drawing tools
- Automatic answer rasterization and overlay onto question images
- OCR-based grading assistance

---

## Requirements Analysis

### 1. Answer Space Types

#### Type 1: Text Lines (1-2 lines)
- **Purpose**: Definitions, short answers, explanations
- **Width**: Full available width to right margin
- **Student Interface**: Rich text editor with all formatting tools
- **Example**: "Define photosynthesis" → 2-line text input

#### Type 2: Calculation Space
- **Purpose**: Working space for calculations, step-by-step solutions
- **Layout**: Large empty area + half-line answer box on right
- **Student Interface**: Drawing canvas (for handwritten work) + text box for final answer
- **Unit Support**: Teacher can specify unit (e.g., "m/s", "kg") pre-filled
- **Example**: "Calculate velocity" → Canvas for work + "_____ m/s" for answer

#### Type 3: Table Cells
- **Purpose**: Fill in missing data in tables
- **Layout**: Table with some pre-filled cells, some empty
- **Student Interface**: Text inputs in empty cells only
- **Example**: Periodic table with atomic numbers → Fill missing elements

#### Type 4: Drawing Canvas
- **Purpose**: Graphs, diagrams, shapes, freehand drawing
- **Tools**: Lines, shapes, freeform drawing, eraser
- **Student Interface**: Full drawing canvas with toolbar
- **Example**: "Draw velocity-time graph" → Canvas with grid

### 2. Multi-Page Question Handling

**Key Innovation**: Questions can span multiple pages

**Page Markers:**
- **Green Line** (top): Marks start of new question
- **Red Line** (bottom): Marks end of question
- **Blue Rectangle**: Defines horizontal boundaries (width) for all pages

**Logic:**
```
IF page has green line at top:
    → Start of new question
IF page has red line at bottom:
    → End of current question
IF no green line at top AND no red line at bottom:
    → Continuation of previous question (middle page)

Question Image = Stitch all pages from green line to red line vertically
Width = Blue rectangle width (consistent across all pages)
```

**Examples:**

**Single-page question:**
```
Page 1:
  [Green line] ←─ Question starts
  Question text
  [Red line]   ←─ Question ends
```

**Multi-page question (3 pages):**
```
Page 1:
  [Green line] ←─ Question starts
  Question text...
  (no red line) ←─ Continues to next page

Page 2:
  (no green line) ←─ Continuation
  ...more question text...
  (no red line) ←─ Continues to next page

Page 3:
  (no green line) ←─ Continuation
  ...end of question
  [Red line]   ←─ Question ends
```

### 3. Workflow Overview

```
Teacher:
1. Upload PDF (Question Paper)
2. Mark pages with green/red lines + blue rectangle
3. System stitches multi-page questions into single tall images
4. Teacher places answer spaces on question image
5. Specify type, size, position for each space
6. Publish test

Student:
1. View question with answer spaces
2. Type in text boxes / Draw on canvas
3. Submit answers
4. System rasterizes all inputs → Creates answer overlay
5. Composite: Question image + Answer overlay = Final answer image

Grading:
1. Teacher views final answer images
2. OCR extracts text from rasterized answers
3. AI assists with grading
4. Teacher reviews and adjusts grades
```

---

## Database Schema Design

### New Models

#### 1. AnswerSpace
```python
class AnswerSpace(models.Model):
    """Defines an answer space on a question"""
    SPACE_TYPES = [
        ('text_line', 'Text Line (1-2 lines)'),
        ('calc_space', 'Calculation Space'),
        ('table_cell', 'Table Cell'),
        ('canvas', 'Drawing Canvas'),
    ]

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answer_spaces')
    space_type = models.CharField(max_length=20, choices=SPACE_TYPES)

    # Position on question image (pixels)
    x = models.IntegerField()  # Left position
    y = models.IntegerField()  # Top position
    width = models.IntegerField()
    height = models.IntegerField()

    # Configuration (JSON for flexibility)
    config = models.JSONField(default=dict)
    # Examples:
    # text_line: {"lines": 2, "max_chars": 200}
    # calc_space: {"unit": "m/s", "answer_width": 100}
    # table_cell: {"row": 2, "col": 3, "table_id": "table1"}
    # canvas: {"grid": true, "grid_size": 10, "tools": ["pen", "line", "shape"]}

    # Ordering
    order = models.IntegerField(default=0)

    # Marks allocation
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ['question', 'order']
```

#### 2. StudentAnswerSpace
```python
class StudentAnswerSpace(models.Model):
    """Student's response to an answer space"""
    student_answer = models.ForeignKey(StudentAnswer, on_delete=models.CASCADE, related_name='space_responses')
    answer_space = models.ForeignKey(AnswerSpace, on_delete=models.CASCADE)

    # Text response (for text_line, calc_space final answer)
    text_response = models.TextField(blank=True)

    # Canvas data (for calc_space work, canvas)
    # Stored as base64 PNG or SVG paths
    canvas_data = models.TextField(blank=True)

    # Rasterized overlay image (PNG base64)
    rasterized_image = models.TextField(blank=True)

    # OCR extracted text (for grading assistance)
    ocr_text = models.TextField(blank=True)

    # Grading
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### 3. QuestionPage
```python
class QuestionPage(models.Model):
    """Tracks multi-page questions during import"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='pages')
    page_number = models.IntegerField()  # Sequential order
    page_image = models.TextField()  # Base64 image data

    # Markers
    has_green_line = models.BooleanField(default=False)  # Start marker
    has_red_line = models.BooleanField(default=False)    # End marker

    # Bounds
    blue_rect_x = models.IntegerField(null=True)
    blue_rect_y = models.IntegerField(null=True)
    blue_rect_width = models.IntegerField(null=True)
    blue_rect_height = models.IntegerField(null=True)

    class Meta:
        ordering = ['question', 'page_number']
```

---

## UI/UX Design

### A. Teacher - PDF Import & Question Creation

#### Enhanced PDF Slicer Interface

**New Features:**
1. **Multi-page question detection**
   - Visual indicator showing which pages belong to same question
   - Preview of stitched question image

2. **Answer space placement tool**
   - Click to add answer space
   - Drag to resize
   - Context menu to configure type
   - Visual overlay showing all spaces

**Workflow:**
```
1. Upload PDF
2. Mark pages:
   - Green line = Question start
   - Red line = Question end
   - Blue rectangle = Width bounds

3. System auto-detects:
   - Page 1: Green + Red → Single question
   - Page 1: Green, no Red → Multi-page start
   - Page 2: No Green, no Red → Continuation
   - Page 3: No Green + Red → End

4. Preview stitched questions
5. Place answer spaces:
   - Click "Add Text Line" → Click position → Drag size
   - Click "Add Calc Space" → Click position → Configure unit
   - Click "Add Table" → Click cells → Mark editable
   - Click "Add Canvas" → Click position → Drag size

6. Save question with spaces
```

#### Answer Space Configuration Panel

**Text Line:**
```
┌─────────────────────────────┐
│ Text Line Configuration     │
├─────────────────────────────┤
│ Number of lines: [2] ▼      │
│ Max characters: [200]        │
│ Marks: [2]                   │
└─────────────────────────────┘
```

**Calculation Space:**
```
┌─────────────────────────────┐
│ Calculation Space Config    │
├─────────────────────────────┤
│ Canvas height: [300px]      │
│ Answer box width: [150px]   │
│ Unit: [m/s        ]          │
│ Show grid: ☑                 │
│ Marks: [5]                   │
└─────────────────────────────┘
```

**Table Cell:**
```
┌─────────────────────────────┐
│ Table Cell Configuration    │
├─────────────────────────────┤
│ Table ID: [table1]          │
│ Row: [2]                     │
│ Column: [3]                  │
│ Width: [100px]              │
│ Marks: [1]                   │
└─────────────────────────────┘
```

**Drawing Canvas:**
```
┌─────────────────────────────┐
│ Canvas Configuration        │
├─────────────────────────────┤
│ Canvas size:                │
│   Width: [600px]            │
│   Height: [400px]           │
│ Show grid: ☑                │
│ Grid size: [10px]           │
│ Tools:                      │
│   ☑ Pen                     │
│   ☑ Line                    │
│   ☑ Rectangle               │
│   ☑ Circle                  │
│   ☑ Eraser                  │
│ Marks: [10]                 │
└─────────────────────────────┘
```

### B. Student - Test Taking Interface

#### Question Display with Answer Spaces

**Layout:**
```
┌────────────────────────────────────────────────┐
│  Question 1                         [3/10 marks]│
├────────────────────────────────────────────────┤
│                                                │
│  [Question Image - may be very tall]           │
│                                                │
│  With overlaid interactive answer spaces:      │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │ Type your answer here...                 │ │ ← Text Line
│  └──────────────────────────────────────────┘ │
│                                                │
│  ┌──────────────────┐  ________ m/s           │ ← Calc Space
│  │                  │                         │
│  │  [Canvas for     │                         │
│  │   working]       │                         │
│  │                  │                         │
│  └──────────────────┘                         │
│                                                │
│  Table: [some cells filled, others editable]  │ ← Table
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │                                          │ │
│  │  [Drawing Canvas with toolbar]           │ │ ← Canvas
│  │  🖊️ ━ □ ○ 🗑️                              │ │
│  │                                          │ │
│  └──────────────────────────────────────────┘ │
│                                                │
├────────────────────────────────────────────────┤
│  [Previous] [Auto-Save: 2 mins ago] [Next]    │
└────────────────────────────────────────────────┘
```

#### Rich Text Editor (for text lines)

Use the custom editor already in the system with all tools:
- Bold, Italic, Underline
- Superscript, Subscript (for math)
- Equations (inline LaTeX or MathML)
- Lists, indentation
- Special characters

#### Drawing Canvas Tools

**Toolbar:**
```
🖊️ Pen (freehand)
━  Line
□  Rectangle
○  Circle/Ellipse
⌗  Grid toggle
🗑️ Eraser
↶  Undo
↷  Redo
🎨 Color picker
📏 Line width
```

**Features:**
- Touch/mouse support
- Smooth drawing with canvas API
- Export to PNG for rasterization
- Real-time preview

### C. Grading Interface

#### Answer Review Screen

**Layout:**
```
┌────────────────────────────────────────────────┐
│  Student: John Doe              Question 1/10  │
├────────────────────────────────────────────────┤
│                                                │
│  ┌─────────────────┐  ┌─────────────────┐    │
│  │ Question Image  │  │ Answer Image    │    │
│  │                 │  │ (with overlays) │    │
│  │                 │  │                 │    │
│  │                 │  │ [Student's      │    │
│  │                 │  │  responses      │    │
│  │                 │  │  composited]    │    │
│  └─────────────────┘  └─────────────────┘    │
│                                                │
├────────────────────────────────────────────────┤
│  OCR Extracted Text:                           │
│  ┌──────────────────────────────────────────┐ │
│  │ "Photosynthesis is the process by which │ │
│  │  plants convert light energy..."         │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  AI Grading Suggestion: 7/10 marks             │
│  Reasoning: Answer covers key points...        │
│                                                │
│  Manual Grade: [7] / 10                        │
│  Feedback: ┌────────────────────────────────┐ │
│           │ Good understanding. Include    │ │
│           │ chlorophyll role for full marks│ │
│           └────────────────────────────────┘ │
│                                                │
│  [Previous Student] [Save Grade] [Next Student]│
└────────────────────────────────────────────────┘
```

---

## Technical Implementation

### Phase 1: Database & Models (Week 1)

**Tasks:**
1. Create migration for `AnswerSpace` model
2. Create migration for `StudentAnswerSpace` model
3. Create migration for `QuestionPage` model
4. Update `Question` model to support multi-page flag
5. Add indexes for performance

### Phase 2: PDF Slicer Enhancement (Week 2)

**Tasks:**
1. Update PDF slicer to detect green/red lines
2. Implement multi-page question grouping logic
3. Create page stitching algorithm:
   ```python
   def stitch_pages(pages):
       # Find all pages between green and red
       # Crop each to blue rectangle width
       # Concatenate vertically
       # Return single tall image
   ```
4. Add visual indicators for question boundaries
5. Implement answer space placement UI:
   - Drag-and-drop answer space creation
   - Resize handles
   - Configuration modals

### Phase 3: Student Answer Interface (Week 3)

**Tasks:**
1. Create answer space renderer component
2. Implement rich text editor integration
3. Build drawing canvas component:
   ```javascript
   class DrawingCanvas {
       constructor(width, height, tools) {
           this.canvas = document.createElement('canvas');
           this.ctx = this.canvas.getContext('2d');
           this.initTools(tools);
       }

       drawLine(x1, y1, x2, y2) { /*...*/ }
       drawRect(x, y, w, h) { /*...*/ }
       exportPNG() { return this.canvas.toDataURL(); }
   }
   ```
4. Implement table cell editor
5. Add auto-save for all answer types
6. Create answer submission handler

### Phase 4: Rasterization System (Week 4)

**Tasks:**
1. Build HTML-to-Canvas converter for text responses:
   ```python
   # Using html2canvas.js or similar
   # Convert rich text HTML to PNG
   ```
2. Composite answer overlays onto question image:
   ```python
   from PIL import Image, ImageDraw

   def create_answer_image(question_img, answers):
       base = Image.open(question_img)

       for answer_space in answers:
           overlay = Image.open(answer_space.rasterized_image)
           base.paste(overlay, (answer_space.x, answer_space.y))

       return base
   ```
3. Implement OCR with Tesseract:
   ```python
   import pytesseract

   def extract_text(image):
       return pytesseract.image_to_string(image)
   ```
4. Create answer image storage system

### Phase 5: Grading Interface (Week 5)

**Tasks:**
1. Build grading dashboard
2. Display question + answer side-by-side
3. Show OCR extracted text
4. Integrate AI grading suggestions
5. Manual grade input and feedback
6. Bulk grading features

---

## API Endpoints

### Question Creation
```
POST /questions/import-structured/
- Upload PDF
- Mark pages with green/red/blue
- Returns question ID

POST /questions/{id}/add-answer-space/
- type: text_line|calc_space|table_cell|canvas
- position: {x, y, width, height}
- config: {...}
- Returns answer space ID
```

### Student Answering
```
GET /student/tests/{test_id}/take/
- Returns question with answer spaces

POST /student/tests/{test_id}/save-answer/
- question_id
- answer_space_id
- response_data: {text, canvas, ...}
- Auto-save every 30 seconds

POST /student/tests/{test_id}/submit/
- Triggers rasterization
- Creates composite answer images
```

### Grading
```
GET /teacher/tests/{test_id}/grade/
- Returns all student submissions

GET /teacher/answer-image/{student_id}/{question_id}/
- Returns composite answer image

POST /teacher/grade-answer/
- student_answer_id
- marks
- feedback
```

---

## Libraries & Dependencies

### Frontend
- **html2canvas** - Convert rich text to PNG
- **Fabric.js** or **Konva.js** - Canvas drawing library
- **MathJax** or **KaTeX** - Math equation rendering
- **Quill.js** (already in use) - Rich text editor

### Backend
- **Pillow (PIL)** - Image manipulation
- **pytesseract** - OCR
- **pdf2image** - PDF processing (already in use)
- **numpy** - Image array operations

---

## User Experience Considerations

### 1. Responsive Design
- Mobile-friendly canvas (touch support)
- Responsive answer spaces
- Scrollable long questions

### 2. Accessibility
- Keyboard navigation
- Screen reader support for answer spaces
- High contrast mode

### 3. Performance
- Lazy load question images
- Compress rasterized answers
- Background OCR processing
- Pagination for grading

### 4. Error Handling
- Save drafts automatically
- Recover from crashes
- Validate answer completeness
- Show submission progress

---

## Migration Strategy

### For Existing MCQ System
1. Keep MCQ workflow as-is
2. Add "Question Type" field:
   - MCQ (existing)
   - Structured (new - with answer spaces)
3. Both types coexist in question library
4. Test can mix both types

### Backward Compatibility
- Existing tests continue to work
- No changes to MCQ grading
- New features opt-in

---

## Testing Plan

### Unit Tests
- Page stitching algorithm
- Answer space placement validation
- Rasterization accuracy
- OCR text extraction

### Integration Tests
- Full workflow: Import → Answer → Grade
- Multi-page question handling
- Auto-save functionality
- Concurrent student access

### User Acceptance Testing
- Teacher creates structured question paper
- Students take test with all answer types
- Teacher grades with OCR assistance
- Performance under load (100 students)

---

## Timeline

| Phase | Tasks | Duration | Status |
|-------|-------|----------|--------|
| 1 | Database & Models | 1 week | Not Started |
| 2 | PDF Slicer Enhancement | 2 weeks | Not Started |
| 3 | Student Interface | 2 weeks | Not Started |
| 4 | Rasterization System | 1 week | Not Started |
| 5 | Grading Interface | 1 week | Not Started |
| 6 | Testing & Refinement | 1 week | Not Started |

**Total Estimated Time: 8 weeks**

---

## Next Steps

### Immediate Actions Required

1. **Approve Design** ✋ (User decision needed)
   - Review this plan
   - Confirm requirements
   - Approve UI/UX mockups

2. **Start Phase 1** (If approved)
   - Create database migrations
   - Set up models
   - Write initial tests

3. **Prototype** (Quick validation)
   - Build simple proof-of-concept
   - Single text line answer space
   - Test rasterization

Would you like me to:
- **Option A**: Start implementing Phase 1 (Database & Models)
- **Option B**: Create a working prototype first
- **Option C**: Revise the plan based on your feedback
- **Option D**: Focus on specific features first

---

**Document Version**: 1.0
**Date**: January 26, 2026
**Author**: Claude (Lumen Development Team)
**Status**: Awaiting Approval
