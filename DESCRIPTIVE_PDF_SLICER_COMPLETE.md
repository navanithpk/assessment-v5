# Descriptive PDF Slicer - Implementation Complete

## Overview

The Descriptive PDF Slicer is now fully implemented and ready to use. It provides an **EXACT replica** of the MCQ PDF slicer UI with backend modifications to handle structured/theory questions that span multiple pages.

---

## Access

**URL**: `http://localhost:8000/questions/import-descriptive-pdf/`

---

## Key Features

### 1. Identical UI to MCQ Slicer
- ✅ Sidebar with page navigation
- ✅ Blue rectangle for content cropping
- ✅ Fabric.js canvas for interactive line drawing
- ✅ All keyboard shortcuts working
- ✅ Multi-file auto-pairing
- ✅ Same toolbar and buttons
- ✅ Same workflow and interactions

### 2. Keyboard Shortcuts (Exact Same as MCQ)
| Shortcut | Function |
|----------|----------|
| `Z` | Add green line (question start) at mouse position |
| `X` | Add red line (question end) at mouse position |
| `C` | Add QP-MS pair line at mouse position |
| `←` | Previous page |
| `→` | Next page |
| `Shift + ←` | Previous PDF pair |
| `Shift + →` | Next PDF pair |
| `↑` | Move selected line up |
| `↓` | Move selected line down |
| `Delete` | Remove selected line |

### 3. Multi-Page Question Support
- Green line = Question START marker (top of page)
- Red line = Question END marker (bottom of page)
- Pages without markers = Middle pages of multi-page questions
- Algorithm automatically stitches Green→(Blue pages)→Red into single question

### 4. Descriptive Question Data
Instead of A/B/C/D answers, each question now has:
- **Marks field**: Numeric input (default: 5)
- **Markscheme field**: Textarea for full marking criteria text

---

## How to Use

### Step 1: Upload PDFs
1. Click "Choose Files" and select both:
   - Question Paper PDF (e.g., `0625_s23_qp_31.pdf`)
   - Mark Scheme PDF (e.g., `0625_s23_ms_31.pdf`)
2. System auto-detects and pairs files by matching filenames
3. Auto-extracts metadata (grade, subject, year) from filename

### Step 2: Mark Question Boundaries
1. Navigate through pages using arrow keys or page selector
2. Press `Z` to add green line at question START
3. Press `X` to add red line at question END
4. For multi-page questions:
   - Add green line on first page (top)
   - Leave middle pages unmarked
   - Add red line on last page (bottom)

**Example Multi-Page Question**:
```
Page 5: [Green line at top]────────────  ← Question 3 starts
Page 6: [No markers]───────────────────  ← Continues on next page
Page 7: [No markers]───────────────────  ← Still continues
Page 8: [Red line at bottom]───────────  ← Question 3 ends
```
Result: Question 3 spans 4 pages and will be stitched vertically

### Step 3: Adjust Blue Rectangle (Optional)
- Click and drag the blue rectangle corners to define content area
- This crops out margins and non-question content
- All questions will be cropped to this rectangle

### Step 4: Slice & Review
1. Click "📐 Slice & Review" button
2. System processes all pages:
   - Groups pages by green/red markers
   - Crops to blue rectangle
   - Stitches multi-page questions vertically
3. Review modal appears showing all detected questions

### Step 5: Enter Question Data
For each question in the modal:
1. **Marks**: Enter total marks (e.g., 5, 10, 15)
2. **Markscheme**: Enter the marking criteria
   - If MS PDF was uploaded, text may be auto-extracted
   - Edit or enter manually as needed

### Step 6: Import Questions
1. Click "Import Questions" button
2. Questions are saved to database as type `structured`
3. Each question stores:
   - Stitched image (vertical combination of all pages)
   - Individual page images (in `QuestionPage` model)
   - Marks and markscheme text
   - Metadata (grade, subject, year)

---

## File Structure

### Templates
- **Location**: `core/templates/teacher/import_descriptive_pdf.html`
- **Size**: 1,468 lines (exact copy of MCQ template with modifications)
- **Changes from MCQ**:
  - Lines 1203-1216: Answer dropdown replaced with marks input + markscheme textarea
  - Lines 1221-1240: Markscheme extraction (full text instead of A/B/C/D pattern)
  - Lines 1323-1349: Data submission format (JSON with pages array)
  - Line 1348: Endpoint changed to `/questions/import-descriptive-pdf/`

### Backend View
- **Location**: `core/descriptive_pdf_slicer_views.py`
- **Function**: `descriptive_pdf_slicer(request)`
- **Process**:
  1. GET request: Renders template with grade/subject dropdowns
  2. POST request: Receives question data as JSON
  3. Creates `Question` objects with type='structured'
  4. Saves individual pages to `QuestionPage` model
  5. Stitches pages and saves combined image

### Utilities
- **Location**: `core/utils/paper_component_detector.py`
- **Functions**:
  - `detect_subject(code)` - Maps 0625→Physics, 0620→Chemistry, 0610→Biology
  - `detect_component(code)` - Maps paper numbers to MCQ/Theory/Practical
  - `parse_paper_code(code)` - Full parsing with year extraction

- **Location**: `core/utils/image_processing.py` (existing)
- **Functions**:
  - `stitch_question_pages(pages_data)` - Vertical page stitching
  - `detect_page_markers(image)` - Green/red line detection
  - `detect_blue_rectangle(canvas)` - Crop boundary detection

### URL Routing
- **Location**: `core/urls.py` (line 53)
```python
path("questions/import-descriptive-pdf/",
     descriptive_pdf_slicer_views.descriptive_pdf_slicer,
     name="descriptive_pdf_slicer"),
```

---

## Database Models

### Question Model (Enhanced)
```python
Question:
    question_text       # Base64 stitched image
    answer_text         # Full markscheme text
    marks               # Total marks
    question_type       # 'structured'
    year                # Exam year
    grade               # ForeignKey to Grade
    subject             # ForeignKey to Subject
    topic               # ForeignKey to Topic
    created_by          # User who imported
```

### QuestionPage Model (New)
```python
QuestionPage:
    question            # ForeignKey to Question
    page_number         # Sequential page number
    page_image          # Base64 PNG of individual page
    has_green_line      # Boolean
    has_red_line        # Boolean
    blue_rect_x         # Crop boundary X
    blue_rect_y         # Crop boundary Y
    blue_rect_width     # Crop boundary width
    blue_rect_height    # Crop boundary height
```

---

## Technical Implementation

### Frontend Data Flow
1. **File Upload** → PDF.js renders pages to canvas
2. **User Marks Lines** → Fabric.js stores line positions
3. **Slice Button** → Algorithm groups pages by markers
4. **Crop & Stitch** → Blue rectangle crops, vertical stitching
5. **Review Modal** → Display stitched questions with input fields
6. **Submit** → JSON POST to backend

### Backend Data Flow
1. **Receive POST** → Parse form data (grade, subject, year, questions array)
2. **Loop Questions** → For each question JSON:
   - Extract pages, marks, markscheme
   - Create Question object
   - Save QuestionPage objects for each page
   - Call stitching utility
   - Save stitched image to question_text
3. **Return Response** → Success count or error message

### Multi-Page Detection Algorithm
```javascript
State machine:
- IDLE → (green line) → COLLECTING
- COLLECTING → (no markers) → COLLECTING (accumulate page)
- COLLECTING → (red line) → COMPLETE (stitch & save)
- Any state → (green line) → NEW QUESTION
```

### Stitching Algorithm
```python
def stitch_question_pages(pages_data):
    canvases = []
    max_width = 0

    for page in pages_data:
        img = decode_base64_image(page['page_image'])
        canvases.append(img)
        max_width = max(max_width, img.width)

    total_height = sum(c.height for c in canvases)

    stitched = Image.new('RGB', (max_width, total_height), 'white')
    y_offset = 0

    for canvas in canvases:
        stitched.paste(canvas, (0, y_offset))
        y_offset += canvas.height

    return encode_to_base64(stitched)
```

---

## Paper Code Auto-Detection

### Filename Pattern
```
<subject_code>_<session><year>_<type>_<paper>.pdf

Examples:
0625_s23_qp_31.pdf → Physics, Summer 2023, Question Paper, Paper 31
0620_w22_ms_51.pdf → Chemistry, Winter 2022, Mark Scheme, Paper 51
0610_m21_qp_61.pdf → Biology, March 2021, Question Paper, Paper 61
```

### Subject Mapping
| Code | Subject |
|------|---------|
| 0625 | Physics |
| 0620 | Chemistry |
| 0610 | Biology |

### Component Mapping
| Paper Range | Component |
|-------------|-----------|
| 11-23 | MCQ |
| 31-43 | Theory |
| 51-53 | Practical |
| 61-63 | Alternative to Practical |

### Year Extraction
| Pattern | Year |
|---------|------|
| s23 | 2023 (Summer) |
| w22 | 2022 (Winter) |
| m21 | 2021 (March) |

---

## Comparison: MCQ vs Descriptive Slicer

| Feature | MCQ Slicer | Descriptive Slicer |
|---------|-----------|-------------------|
| UI Layout | Sidebar + Canvas + Toolbar | **IDENTICAL** |
| Keyboard Shortcuts | Z/X/C/Arrows/Delete | **IDENTICAL** |
| Blue Rectangle | Yes | **IDENTICAL** |
| Multi-file Pairing | Yes | **IDENTICAL** |
| Question Detection | Green/Red lines | **IDENTICAL** |
| Multi-page Support | No | **YES** (new) |
| Answer Format | A/B/C/D dropdown | Marks + Markscheme textarea |
| Question Type | 'mcq' | 'structured' |
| Markscheme | Single letter | Full text |
| Database Model | Question only | Question + QuestionPage |

---

## Testing Checklist

### ✅ UI Elements
- [x] Sidebar displays and updates
- [x] Blue rectangle appears and is draggable
- [x] Canvas renders PDF pages
- [x] Toolbar buttons visible and functional
- [x] Page navigation works

### ✅ Keyboard Shortcuts
- [x] Z adds green line
- [x] X adds red line
- [x] C adds pair line
- [x] Arrow keys navigate pages
- [x] Shift+arrows switch files
- [x] Delete removes lines
- [x] Up/down arrows move lines

### ✅ Processing
- [x] Slice & Review detects questions
- [x] Multi-page questions stitched correctly
- [x] Single-page questions handled
- [x] Blue rectangle cropping works
- [x] Modal displays stitched images

### ✅ Data Entry
- [x] Marks input accepts numbers
- [x] Markscheme textarea accepts text
- [x] Validation prevents empty marks
- [x] Pre-filled data from MS extraction (if available)

### ✅ Backend
- [x] POST endpoint receives data
- [x] Questions saved to database
- [x] QuestionPage records created
- [x] Stitched images saved
- [x] Success response returned

---

## Troubleshooting

### Issue: "No questions detected"
**Cause**: No green/red lines marked
**Solution**: Press Z to add green lines at question starts, X for red lines at question ends

### Issue: Questions split incorrectly
**Cause**: Incorrect marker placement
**Solution**:
- Green lines should be at TOP of first page
- Red lines should be at BOTTOM of last page
- Middle pages should have NO markers

### Issue: Keyboard shortcuts not working
**Cause**: Focus on input field or modal open
**Solution**: Click on canvas area first, close any open modals

### Issue: Blue rectangle not visible
**Cause**: Canvas not rendered yet
**Solution**: Wait for PDF to load completely, try clicking on canvas

### Issue: "Missing grade or subject" error
**Cause**: Metadata not auto-detected from filename
**Solution**: Manually select grade and subject from dropdowns before slicing

### Issue: Markscheme empty
**Cause**: MS PDF not uploaded or text extraction failed
**Solution**: Manually enter markscheme in textarea fields

---

## Future Enhancements (Optional)

1. **Smart Markscheme Matching**: Better algorithm to match MS pages with questions
2. **Mark Detection**: Auto-extract marks from MS (e.g., "[3]", "[5]")
3. **Sub-question Detection**: Split questions with parts (a), (b), (c)
4. **PDF Annotations**: Direct PDF annotation instead of line drawing
5. **Batch Import**: Process multiple papers in one session
6. **Export Options**: Export questions to different formats

---

## Summary

The Descriptive PDF Slicer is a complete, production-ready feature that:
- Provides an **IDENTICAL UI** to the MCQ slicer (as requested)
- Supports **multi-page questions** through green/red/blue line detection
- Handles **full markscheme text** instead of single letters
- Maintains **all keyboard shortcuts and interactions**
- Integrates seamlessly with existing question library
- Stores both stitched images and individual pages for flexibility

**Status**: ✅ **COMPLETE AND READY TO USE**

Access at: `http://localhost:8000/questions/import-descriptive-pdf/`
