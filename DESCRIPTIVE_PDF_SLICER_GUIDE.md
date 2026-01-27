# Descriptive PDF Slicer - Complete Guide

## ✅ What's Built

### Features Implemented
1. **Paper Component Auto-Detection** - Automatically identifies Physics/Chemistry/Biology and MCQ/Theory/Practical from paper codes
2. **Multi-Page Question Detection** - Handles questions spanning multiple pages using green/red line markers
3. **Green/Red/Blue Line Detection** - Image processing to identify question boundaries
4. **Page Stitching** - Combines multi-page questions into single vertical images
5. **Full Markscheme Extraction** - Extracts complete text (not just A/B/C/D) for theory questions
6. **Visual UI** - Beautiful interface with real-time preview and status tracking

---

## 🚀 Quick Start

### Access URL
```
http://localhost:8000/questions/import-descriptive-pdf/
```

### Required Files
- Question Paper PDF (with green/red lines marked)
- Mark Scheme PDF (optional but recommended)

---

## 📝 How to Use

### Step 1: Enter Paper Information

**Paper Code Format**: `SSSS_XYY_qp_NN`
- `SSSS` = Subject code (0625=Physics, 0620=Chemistry, 0610=Biology)
- `X` = Season (s=Summer, w=Winter, m=March)
- `YY` = Year (23=2023, 22=2022)
- `NN` = Paper number

**Examples**:
```
0625_s23_qp_31  → Physics, Theory, 2023
0620_w22_qp_51  → Chemistry, Practical, 2022
0610_s23_qp_61  → Biology, Alternative to Practical, 2023
```

The system will auto-detect:
- ✅ Subject
- ✅ Component (MCQ/Theory/Practical/Alt to Practical)
- ✅ Year

### Step 2: Select Metadata
- **Grade**: Select from dropdown
- **Subject**: Select Physics/Chemistry/Biology
- **Topic**: Select relevant topic

### Step 3: Upload Files
- **Question Paper (PDF)**: Required
- **Mark Scheme (PDF)**: Optional

Click **🚀 Process PDF**

### Step 4: Review Questions

The system will show:
- Question cards with stitched previews
- Green/Red/Blue marker indicators
- Full markscheme text
- Page ranges (e.g., "Pages 2-5 (4 pages)")

### Step 5: Save Questions

For each question:
1. Review the stitched image
2. Check the markscheme
3. Adjust marks if needed
4. Click **💾 Save Question X**

---

## 🎨 Understanding the Markers

### Green Line (Question Start)
- Appears at **top** of page
- Marks the **beginning** of a new question
- All questions must start with a green line

### Red Line (Question End)
- Appears at **bottom** of page
- Marks the **end** of a question
- All questions must end with a red line

### Blue Line (Continuation)
- Pages with **neither** green nor red
- Indicates **middle pages** of multi-page questions
- Automatically detected

### Example Page Sequence
```
Page 1: [Green]─────────[Red]         → Question 1 (single page)
Page 2: [Green]─────────[Blue]        → Question 2 starts
Page 3: [Blue]──────────[Blue]        → Question 2 continues
Page 4: [Blue]──────────[Red]         → Question 2 ends (3 pages total)
Page 5: [Green]─────────[Red]         → Question 3 (single page)
```

Result:
- **Q1**: 1 page
- **Q2**: 3 pages (stitched vertically)
- **Q3**: 1 page

---

## 🔍 Paper Component Detection

### Subject Codes
```
0625 = Physics
0620 = Chemistry
0610 = Biology
```

### Paper Numbers
```
MCQ Papers:              11, 12, 13, 21, 22, 23
Theory Papers:           31, 32, 33, 41, 42, 43
Practical Papers:        51, 52, 53
Alt. to Practical:       61, 62, 63
```

### Auto-Detection Logic
When you enter `0625_s23_qp_31`:
- Subject: **0625** → Physics
- Year: **s23** → 2023
- Component: **31** → Theory

Display: "✓ Detected: Physics - Theory"

---

## 📋 Markscheme Extraction

### For MCQ Papers (11-23)
- Extracts single letter answers (A, B, C, D)
- One answer per question

### For Theory Papers (31-63)
- Extracts **full text content**
- Includes all marking criteria
- Preserves formatting and notes
- Maps to question page ranges

**Example Theory Markscheme**:
```
Question 3 (Pages 5-7):

Step 1: Calculate gravitational potential energy
        E = mgh
        = 2.0 × 10 × 5.0
        = 100 J                                    [2]

Step 2: Find kinetic energy at bottom
        KE = PE (conservation of energy)
        KE = 100 J                                 [1]

[Accept alternative valid methods]
[Total: 3 marks]
```

---

## 🧪 Testing Checklist

### ✅ Basic Upload
- [ ] Can access `/questions/import-descriptive-pdf/`
- [ ] Paper code auto-detection works
- [ ] Can upload QP file
- [ ] Can upload MS file (optional)
- [ ] Form validates required fields

### ✅ Processing
- [ ] System detects green/red lines
- [ ] Pages grouped into questions correctly
- [ ] Multi-page questions identified
- [ ] Single-page questions handled
- [ ] Markscheme extracted

### ✅ Preview & Review
- [ ] Question cards display
- [ ] Stitched images shown
- [ ] Marker indicators visible (🟢🔵🔴)
- [ ] Page ranges correct
- [ ] Markscheme text displayed

### ✅ Saving
- [ ] Can save individual questions
- [ ] Status changes to "✓ Saved"
- [ ] Questions appear in question library
- [ ] Metadata (grade, subject, topic) saved
- [ ] Year and component stored

---

## 🐛 Troubleshooting

### Issue: "No questions detected"
**Cause**: PDF doesn't have green/red lines
**Solution**: Ensure PDFs have proper marker lines at top/bottom of pages

### Issue: "Questions split incorrectly"
**Cause**: Marker lines not detected properly
**Solution**:
- Verify green line is at TOP of start page
- Verify red line is at BOTTOM of end page
- Middle pages should have NO green/red lines

### Issue: "Paper info not auto-detected"
**Cause**: Paper code format incorrect
**Solution**: Use exact format: `SSSS_XYY_qp_NN`
- Example: `0625_s23_qp_31` ✅
- Wrong: `0625-s23-qp-31` ❌

### Issue: "Markscheme empty"
**Cause**: MS file not uploaded or page mismatch
**Solution**:
- Upload MS file
- Ensure MS page numbers align with QP

### Issue: "User profile error"
**Cause**: User doesn't have profile
**Solution**: System automatically creates one (fixed)

---

## 📊 Database Storage

### Question Table
- `question_text`: Stitched image (base64)
- `answer_text`: Full markscheme text
- `question_type`: 'structured'
- `marks`: Total marks
- `year`: Extracted from paper code
- `grade`, `subject`, `topic`: Metadata

### QuestionPage Table
Each page stored separately:
- `page_number`: Sequential number
- `page_image`: Base64 PNG
- `has_green_line`: Boolean
- `has_red_line`: Boolean
- `blue_rect_x/y/width/height`: Crop boundaries

---

## 🎯 Example Workflow

### Scenario: Import Physics Theory Paper

**Files**:
- `0625_s23_qp_31.pdf` (Question Paper)
- `0625_s23_ms_31.pdf` (Mark Scheme)

**Paper Structure**:
```
Page 1: Cover page
Page 2: Q1 [Green]────[Red]           (1 page)
Page 3: Q2 [Green]────[Blue]          (starts)
Page 4:    [Blue]─────[Blue]          (continues)
Page 5:    [Blue]─────[Red]           (ends - 3 pages total)
Page 6: Q3 [Green]────[Red]           (1 page)
```

**Processing**:
1. Enter paper code: `0625_s23_qp_31`
2. Auto-detects: Physics, Theory, 2023
3. Select Grade 10, Subject Physics, Topic Mechanics
4. Upload both PDFs
5. Click Process

**Result**:
- 3 question cards displayed
- Q1: 1 page
- Q2: 3 pages (stitched)
- Q3: 1 page
- Each with full markscheme text

**Save**:
- Save each question individually
- All stored in question library
- Ready for test creation

---

## 🔗 Integration

### With Question Library
Saved questions appear in: `/questions/`
- Filter by subject, grade, topic
- Edit answer spaces: `/questions/<id>/edit-spaces/`
- Add to tests

### With Test Creation
Use saved questions in:
- Standard tests
- Descriptive tests
- Mixed question tests

### With Grading System
Questions with answer spaces:
- Student interface with positioned editors
- Rasterization on submission
- Grading view with composite images

---

## 📞 Support

If you encounter issues:
1. Check browser console for errors
2. Verify PDF format and markers
3. Check Django logs
4. Review paper code format

---

**Ready to test!** 🎉

Access: `http://localhost:8000/questions/import-descriptive-pdf/`
