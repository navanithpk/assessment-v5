# Non-MCQ Question Import - Two-Step Design

## Overview

A comprehensive two-step process for importing structured/theory questions with proper answer space definition and grading support.

---

## Step 1: Question Slicing (EXISTING)

**Tool**: Current Descriptive PDF Slicer

**Process**:
1. Upload QP PDF
2. Mark questions with green (Z) and red (X) lines
3. Mark answer spaces to omit with purple (W) lines
4. Slice & Review
5. Enter **marks only** (no markscheme yet)
6. Import questions to database

**Output**: Question images stored without answer spaces

---

## Step 2: Answer Space & Markscheme Definition (NEW)

### Teacher Interface

After Step 1 import, teacher accesses "Define Answer Spaces" page for each question.

#### Left Panel: Question Image
- Display stitched question image (without answer spaces)
- Read-only, for reference

#### Right Panel: Answer Space Configuration

For each question, teacher defines:

**Question Parts** (dynamic list):
```
Part (a):
  ├── Answer Type: [Text | Canvas | Both]
  ├── Marks: [3]
  ├── Text Answer:
  │   ├── Input Type: [Short Text | Long Text | Number]
  │   ├── Expected Answer: "gravitational force..."
  │   ├── AI Grading: [✓ Enable]
  ├── Canvas Answer:
  │   ├── Width: [400px]
  │   ├── Height: [300px]
  │   ├── Instructions: "Draw a free body diagram"
  │   ├── AI Grading: [✗ Manual only]
  └── Markscheme: [Textarea with full criteria]

Part (b):
  └── [Similar structure]

[+ Add Part]
```

#### Visual Answer Space Designer

**Interface**:
```
┌─────────────────────────────────────────────┐
│  Question 1(a): Calculate the force...      │
│                                             │
│  Answer Type: ● Text  ○ Canvas  ○ Both     │
│                                             │
│  ┌─── Text Answer ────────────────────┐    │
│  │ Input Type: [Long Text ▼]          │    │
│  │ Max Length: [500 characters]       │    │
│  │                                     │    │
│  │ Model Answer:                      │    │
│  │ ┌─────────────────────────────┐   │    │
│  │ │ F = GMm/r²                  │   │    │
│  │ │ where G = gravitational...  │   │    │
│  │ └─────────────────────────────┘   │    │
│  │                                     │    │
│  │ ☑ Enable AI-assisted grading      │    │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─── Canvas Answer ───────────────────┐   │
│  │ Dimensions: 600 x 400 px            │   │
│  │ Tool Palette: Pen, Line, Circle... │   │
│  │ Instructions: "Draw free body..."   │   │
│  │ ☐ Enable AI image analysis         │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  Marks: [3]                                 │
│                                             │
│  Markscheme:                                │
│  ┌─────────────────────────────────────┐   │
│  │ B1: Correct formula stated          │   │
│  │ C1: Substitution with correct values│   │
│  │ A1: Final answer 6.67 × 10⁻¹¹ N    │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## Student Interface

### Taking Test - Question Display

```
┌───────────────────────────────────────────────────┐
│  Question 1                              Marks: 8 │
│  ┌─────────────────────────────────────────────┐ │
│  │  [Question Image - rendered]                │ │
│  │  Calculate the gravitational force...       │ │
│  │  (a) State the formula... [3 marks]         │ │
│  │  (b) Calculate the value... [3 marks]       │ │
│  │  (c) Draw a diagram... [2 marks]            │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  ─────────────────────────────────────────────── │
│                                                   │
│  Your Answer:                                     │
│                                                   │
│  Part (a):                              [3 marks] │
│  ┌─────────────────────────────────────────────┐ │
│  │ F = GMm/r²                                  │ │
│  │                                             │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  Part (b):                              [3 marks] │
│  ┌─────────────────────────────────────────────┐ │
│  │ F = (6.67×10⁻¹¹)(5.97×10²⁴)(1000)/(6.37... │ │
│  │                                             │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  Part (c): Draw a free body diagram   [2 marks]  │
│  ┌─────────────────────────────────────────────┐ │
│  │                                             │ │
│  │      [Canvas Drawing Area]                  │ │
│  │      Tools: ✏️ Pen | ⬜ Shapes | 🔄 Undo    │ │
│  │                                             │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  [💾 Save Draft]          [✅ Submit Answer]     │
└───────────────────────────────────────────────────┘
```

---

## Database Schema Changes

### Enhanced Question Model

```python
Question:
    question_text        # Stitched image (existing)
    answer_text          # Deprecated for structured questions
    marks                # Total marks (sum of all parts)
    question_type        # 'structured'
    parts_config         # JSON: Answer space configuration
    # ... existing fields
```

### Parts Configuration JSON Structure

```json
{
  "parts": [
    {
      "part_id": "1a",
      "part_label": "(a)",
      "marks": 3,
      "answer_type": "text",
      "text_config": {
        "input_type": "long_text",
        "max_length": 500,
        "model_answer": "F = GMm/r² where...",
        "ai_grading_enabled": true
      },
      "canvas_config": null,
      "markscheme": "B1: Formula\nC1: Substitution\nA1: Answer"
    },
    {
      "part_id": "1b",
      "part_label": "(b)",
      "marks": 3,
      "answer_type": "both",
      "text_config": {
        "input_type": "short_text",
        "max_length": 100,
        "model_answer": "6.67 × 10⁻¹¹ N",
        "ai_grading_enabled": true
      },
      "canvas_config": {
        "width": 400,
        "height": 300,
        "instructions": "Show your working",
        "ai_grading_enabled": false
      },
      "markscheme": "C1: Correct calculation\nA1: Final answer"
    },
    {
      "part_id": "1c",
      "part_label": "(c)",
      "marks": 2,
      "answer_type": "canvas",
      "text_config": null,
      "canvas_config": {
        "width": 600,
        "height": 400,
        "instructions": "Draw free body diagram",
        "ai_grading_enabled": false
      },
      "markscheme": "B1: Correct arrows\nB1: Correct labels"
    }
  ]
}
```

### Enhanced StudentAnswer Model

```python
StudentAnswer:
    test_question        # ForeignKey (existing)
    student              # ForeignKey (existing)
    answer_parts         # JSON: Answers for each part
    marks_obtained       # Total marks (existing)
    graded_by            # ForeignKey to User (existing)
    # ... existing fields
```

### Answer Parts JSON Structure

```json
{
  "parts": [
    {
      "part_id": "1a",
      "text_answer": "F = GMm/r² where G is gravitational constant...",
      "canvas_answer": null,
      "marks_obtained": 3,
      "marks_allocated": 3,
      "grading_method": "ai",
      "ai_feedback": "Correct formula and explanation",
      "teacher_feedback": null,
      "graded_at": "2026-01-26T10:30:00Z"
    },
    {
      "part_id": "1b",
      "text_answer": "6.67 × 10⁻¹¹ N",
      "canvas_answer": "data:image/png;base64,iVBORw0KG...",
      "marks_obtained": 2.5,
      "marks_allocated": 3,
      "grading_method": "manual",
      "ai_feedback": null,
      "teacher_feedback": "Calculation correct but units missing (-0.5)",
      "graded_at": "2026-01-26T11:00:00Z"
    }
  ]
}
```

---

## Grading Interface

### Teacher Grading Dashboard

```
┌─────────────────────────────────────────────────────────┐
│  Grading: Test 1 - Physics Paper 42                    │
│  Student: John Smith                                    │
│  Question 1 (8 marks)                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─── Question ───────────┐  ┌─── Student Answer ───┐ │
│  │                         │  │                       │ │
│  │  [Question Image]       │  │  Part (a): [3 marks] │ │
│  │                         │  │  ┌──────────────────┐│ │
│  │  (a) State formula...   │  │  │ F = GMm/r²       ││ │
│  │  (b) Calculate...       │  │  │ G = 6.67×10⁻¹¹  ││ │
│  │  (c) Draw diagram...    │  │  └──────────────────┘│ │
│  │                         │  │                       │ │
│  └─────────────────────────┘  │  🤖 AI: 3/3 ✅       │ │
│                                │  [Override: ___]     │ │
│                                │                       │ │
│                                │  Part (b): [3 marks] │ │
│                                │  Text: 6.67×10⁻¹¹ N  │ │
│                                │  Canvas:             │ │
│                                │  ┌──────────────────┐│ │
│                                │  │ [Drawing shows   ││ │
│                                │  │  calculation]    ││ │
│                                │  └──────────────────┘│ │
│                                │  🤖 AI: 2.5/3        │ │
│                                │  Manual: [2.5_____]  │ │
│                                │  Feedback:           │ │
│                                │  ┌──────────────────┐│ │
│                                │  │ Missing units    ││ │
│                                │  └──────────────────┘│ │
│                                │                       │ │
│                                │  Part (c): [2 marks] │ │
│                                │  ┌──────────────────┐│ │
│                                │  │ [Free body       ││ │
│                                │  │  diagram drawn]  ││ │
│                                │  └──────────────────┘│ │
│                                │  Manual: [2_______]  │ │
│                                │  Feedback:           │ │
│                                │  ┌──────────────────┐│ │
│                                │  │ Perfect!         ││ │
│                                │  └──────────────────┘│ │
│  ─────────────────────────────────────────────────────│ │
│  Total: 7.5 / 8                                        │ │
│                                                         │
│  [⬅️ Previous Student]  [Save & Next ➡️]              │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Database & Models (Week 1)

1. **Migration**: Add `parts_config` JSON field to Question model
2. **Migration**: Add `answer_parts` JSON field to StudentAnswer model
3. **Create Views**:
   - `define_answer_spaces(question_id)` - Teacher config interface
   - `save_answer_spaces(question_id)` - Save configuration
4. **Update Views**:
   - `import_descriptive_pdf()` - Remove markscheme requirement, only marks

### Phase 2: Teacher Answer Space Designer (Week 2)

**New Template**: `core/templates/teacher/define_answer_spaces.html`

**Features**:
- Question image display
- Dynamic part addition/removal
- Answer type selection (text/canvas/both)
- Text input configuration (short/long/number)
- Canvas configuration (dimensions, tools)
- Markscheme entry per part
- Model answer entry
- AI grading toggle

**JavaScript Components**:
- Part manager (add/remove/reorder)
- Canvas preview
- Form validation
- Auto-save

### Phase 3: Student Test-Taking Interface (Week 3)

**Update Template**: `core/templates/student/student_take_test.html`

**Features**:
- Render question parts from `parts_config`
- Dynamic input fields based on answer type
- Canvas drawing widget (Fabric.js)
- Auto-save answers to `answer_parts` JSON
- Part-by-part validation
- Progress tracking per part

**JavaScript Components**:
- Canvas drawing tools
- Answer serialization
- Draft saving (localStorage + server)

### Phase 4: AI Grading Integration (Week 4)

**New Module**: `core/ai_grading.py`

**Functions**:
```python
def grade_text_answer(student_answer, model_answer, markscheme):
    """
    Use LLM to grade text answers
    Returns: {
        'marks': 2.5,
        'feedback': 'Correct approach but...',
        'confidence': 0.85
    }
    """

def grade_canvas_answer(canvas_image, markscheme):
    """
    Use vision model for basic image analysis
    Returns: {
        'has_diagram': True,
        'suggested_marks': 1.5,
        'feedback': 'Contains diagram, manual review needed',
        'confidence': 0.4
    }
    """
```

**Integration Points**:
- Auto-grade text answers on submission
- Flag canvas answers for manual review
- Store AI suggestions for teacher override

### Phase 5: Enhanced Grading Interface (Week 5)

**Update Template**: `core/templates/teacher/grade_answers.html`

**Features**:
- Side-by-side question and answer display
- Per-part grading
- AI suggestion display
- Override capability
- Feedback textarea per part
- Bulk grading (accept all AI suggestions)
- Progress tracker (parts graded vs pending)

### Phase 6: Analytics & Reporting (Week 6)

**Enhancements**:
- Part-level performance analytics
- AI grading accuracy tracking
- Common mistake identification
- Time-per-part analytics

---

## UI/UX Improvements

### For Teachers:

1. **Batch Answer Space Definition**
   - Define template for question type (e.g., "Physics calculation")
   - Apply to multiple similar questions

2. **Quick Actions**
   - Duplicate part configuration
   - Copy from previous question
   - Import markscheme from clipboard

3. **Preview Mode**
   - See question as student will see it
   - Test canvas drawing tools
   - Verify text input constraints

4. **Grading Efficiency**
   - Keyboard shortcuts (Tab to next part, Enter to save)
   - Common feedback snippets
   - Bulk operations (accept all AI grades)

### For Students:

1. **Clear Visual Hierarchy**
   - Question image at top
   - Parts clearly separated
   - Marks visible per part

2. **Drawing Tools**
   - Pen, line, circle, rectangle
   - Undo/redo
   - Clear canvas
   - Color picker
   - Eraser

3. **Auto-Save & Sync**
   - Save every 30 seconds
   - Visual indicator (🟢 Saved, 🟡 Saving, 🔴 Error)
   - Resume from last save

4. **Input Validation**
   - Character count for text
   - Required field indicators
   - Submit disabled until all parts answered

---

## Practical Benefits

### Flexibility:
- Text answers → Fast AI grading
- Canvas answers → Manual teacher review
- Both → Best of both worlds

### Traceability:
- Each part tracked separately
- AI vs manual grading logged
- Audit trail for marks

### Scalability:
- AI handles bulk text grading
- Teachers focus on diagrams/calculations
- Faster turnaround for students

### Accuracy:
- AI provides consistent text grading
- Teachers verify edge cases
- Model answers guide students

---

## Migration Strategy

### For Existing Questions:

**Option 1**: Bulk convert with default config
```python
# Set all existing structured questions to single text part
parts_config = {
    "parts": [{
        "part_id": "1",
        "part_label": "",
        "marks": question.marks,
        "answer_type": "text",
        "text_config": {
            "input_type": "long_text",
            "max_length": 1000,
            "model_answer": question.answer_text or "",
            "ai_grading_enabled": True
        },
        "canvas_config": null,
        "markscheme": question.answer_text or ""
    }]
}
```

**Option 2**: Manual migration UI
- List all questions without `parts_config`
- Teacher clicks "Configure" to define parts
- Gradual migration as needed

---

## Testing Plan

### Unit Tests:
- JSON schema validation
- Part configuration saving/loading
- Answer serialization

### Integration Tests:
- Full workflow (import → configure → take test → grade)
- AI grading accuracy
- Multi-part questions

### User Testing:
- Teacher: Answer space definition flow
- Student: Test-taking experience
- Teacher: Grading interface

---

## Success Metrics

1. **Import Efficiency**: Time to import 40 questions < 15 minutes
2. **Configuration Accuracy**: < 5% error rate in answer space definition
3. **Student Experience**: > 90% satisfaction with input methods
4. **Grading Speed**: 50% faster with AI assistance
5. **AI Accuracy**: > 85% agreement with teacher grading for text answers

---

## Next Steps

1. ✅ Review and approve design
2. 🔧 Create database migrations
3. 🎨 Build answer space designer UI
4. 🧪 Implement AI grading module
5. 📊 Test with real exam questions
6. 🚀 Deploy to production

---

**Status**: Design Complete - Awaiting Approval
**Date**: 2026-01-26
