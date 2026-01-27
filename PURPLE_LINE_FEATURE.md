# Purple Line Feature - Answer Space Omission

## Overview

The **Purple Line (W key)** feature allows you to mark sections of questions that should be **omitted** from the final stitched image. This is particularly useful for:
- Answer spaces/boxes where students write their answers
- Blank regions that don't need to be shown in the question bank
- Sections that should be excluded from the question preview

---

## How It Works

### Basic Usage

**Press `W`** to add a purple line at the cursor position.

### Purple Line Pairing

Purple lines work in **pairs**:
- **First purple line**: Start of omitted section
- **Second purple line**: End of omitted section
- The region **between** the two purple lines is **excluded** from the stitched image

### Visual Example

```
Page 3:
┌────────────────────────────┐
│ [GREEN] Question Start     │ ← Z key
│                            │
│ (a) Calculate the force... │  } Included
│                            │  } in final
│ [PURPLE] Answer Space Start│ ← W key (1st)
│                            │
│ [Large blank box]          │  } OMITTED
│ [Students write here]      │  } (not in
│                            │  } stitched
│ [PURPLE] Answer Space End  │ ← W key (2nd)
│                            │
│ (b) Explain why...         │  } Included
│                            │  } in final
│ [RED] Question End         │ ← X key
└────────────────────────────┘

Result: Question stitched WITHOUT the answer space
```

---

## Multi-Page Purple Regions

### Cross-Page Omission

If a purple region spans multiple pages:

1. **Last line on page**: Purple line at bottom
2. **First line on next page**: Must be purple (matching pair)
3. The **entire region** across both pages is omitted

### Example

```
Page 5:
┌────────────────────────────┐
│ [GREEN] Question Start     │
│ (a) Describe the process...│  } Included
│ [PURPLE] Answer box starts │ ← W key
│                            │
│ [Large answer space]       │  } OMITTED
│ [Continues to next page]   │  } (page break)
│ [PURPLE] (at page bottom)  │ ← Continues
└────────────────────────────┘

Page 6:
┌────────────────────────────┐
│ [PURPLE] (at page top)     │ ← Matching pair
│ [Answer space continues]   │  } OMITTED
│                            │  } (continued)
│ [PURPLE] Answer box ends   │ ← W key (end)
│                            │
│ (b) Calculate the value... │  } Included
│ [RED] Question End         │
└────────────────────────────┘

Result: Question stitched from pages 5-6 WITHOUT the cross-page answer space
```

---

## Multiple Purple Pairs

You can have **multiple omitted sections** in a single question:

```
┌────────────────────────────┐
│ [GREEN] Question Start     │
│ Part (a): Calculate...     │  } Included
│ [PURPLE]                   │
│ [Answer space 1]           │  } OMITTED
│ [PURPLE]                   │
│ Part (b): Explain...       │  } Included
│ [PURPLE]                   │
│ [Answer space 2]           │  } OMITTED
│ [PURPLE]                   │
│ Part (c): Draw a diagram...│  } Included
│ [RED] Question End         │
└────────────────────────────┘

Result: Question with parts (a), (b), (c) visible, but answer spaces omitted
```

---

## Keyboard Shortcuts Reference

| Key | Color | Purpose |
|-----|-------|---------|
| **Z** | Green | Question **START** marker |
| **X** | Red | Question **END** marker |
| **W** | Purple | **OMIT** region marker (use in pairs) |
| **C** | Red+Green | QP-MS **PAIR** marker |
| **↑↓** | - | Move selected line |
| **Delete** | - | Remove selected line |

---

## Workflow

### Step 1: Mark Question Boundaries
1. Press **Z** at question start (green line)
2. Press **X** at question end (red line)

### Step 2: Mark Answer Spaces
1. Press **W** at start of answer space (first purple)
2. Press **W** at end of answer space (second purple)
3. Repeat for each answer space in the question

### Step 3: Slice & Review
1. Click "📐 Slice & Review"
2. System will:
   - Stitch visible parts
   - **Exclude** purple regions
   - Show preview without answer spaces

### Step 4: Verify & Import
1. Review stitched images
2. Confirm answer spaces are omitted
3. Enter marks and markscheme
4. Import questions

---

## Algorithm Details

### Purple Line State Machine

```
State: NOT_IN_OMIT
  → Encounter Purple Line #1
  → State: IN_OMIT (start omitting)
  → Stitch content up to this point
  → Skip content until next purple

State: IN_OMIT
  → Encounter Purple Line #2
  → State: NOT_IN_OMIT (stop omitting)
  → Resume stitching from this point

State: IN_OMIT (at page boundary)
  → Page ends
  → Set flag: lastPurpleOnPage = true
  → DON'T stitch content (we're in omit region)
  → Continue to next page

Next Page (with lastPurpleOnPage = true)
  → Expect purple line at start
  → Remove matching purple line
  → State: NOT_IN_OMIT
  → Resume stitching from purple line position
```

### Edge Cases Handled

1. **Odd number of purple lines**: Warning logged, last purple ignored
2. **Purple before green**: Ignored (no question context)
3. **Purple after red**: Ignored (question already ended)
4. **Page break in purple region**: Automatically handles continuation
5. **Multiple purple pairs**: Each pair processed independently

---

## Markscheme Auto-Extraction

### For Structured Questions (Non-MCQ)

The system extracts markschemes from MS PDFs with table structure:

```
┌──────────┬────────────────────────────────────┬───────┐
│ Question │ Answer                             │ Marks │
├──────────┼────────────────────────────────────┼───────┤
│ 1(a)     │ (gravitational) force is (directly)│  B1   │
│          │ proportional to product of masses  │       │
├──────────┼────────────────────────────────────┼───────┤
│ 1(b)     │ correct read offs from graph with  │  C1   │
│          │ correct power of ten for R²        │       │
│          │ M = (calculation shown)            │  C1   │
│          │ = 3.0 × 10³⁰ kg                   │  A1   │
└──────────┴────────────────────────────────────┴───────┘
```

### Extraction Logic

1. **Parse PDF Table**: Extract text with positioning
2. **Identify Columns**: Question | Answer | Marks
3. **Match Pattern**: Recognize `1(a)`, `1(b)`, `2(c)(i)`, etc.
4. **Extract Marks**: Parse `B1`, `C1`, `A1`, `M1` notation
5. **Calculate Total**: Sum marks for each question part
6. **Auto-fill**: Pre-populate markscheme textarea

### Mark Types

- **B1**: Basic mark (1 point)
- **C1**: Calculation mark (1 point)
- **A1**: Answer mark (1 point)
- **M1**: Method mark (1 point)

Total marks = Sum of all mark values

---

## Practical Examples

### Example 1: Single Answer Space

```
Mark the question:
1. Z at "Question 2(a)" line
2. W at start of answer box
3. W at end of answer box
4. X at "Question 2(b)" line

Result: Question 2(a) text + Question 2(b) text (answer box omitted)
```

### Example 2: Multi-Part Question with Multiple Spaces

```
Mark the question:
1. Z at "Question 3" line
2. For part (a):
   - W at answer space start
   - W at answer space end
3. For part (b):
   - W at answer space start
   - W at answer space end
4. For part (c):
   - W at answer space start
   - W at answer space end
5. X at "Question 4" line

Result: Question 3 with parts (a)(b)(c) visible, all answer spaces omitted
```

### Example 3: Cross-Page Answer Space

```
Page 8:
1. Z at "Question 5(a)" line
2. W at answer box start
3. (answer space continues to next page)
4. W at bottom of page (page break)

Page 9:
5. W at top of page (continuation)
6. (answer space continues)
7. W at answer box end
8. X at "Question 5(b)" line

Result: Question 5(a) and 5(b) visible, large cross-page answer space omitted
```

---

## Troubleshooting

### Issue: Purple region not omitted
**Cause**: Unpaired purple lines (odd number)
**Solution**: Ensure purple lines come in pairs (start/end)

### Issue: Too much content omitted
**Cause**: Purple lines too far apart
**Solution**: Adjust purple line positions, ensure they bracket only answer space

### Issue: Content missing at page boundary
**Cause**: Missing purple line at page start/end
**Solution**: If page ends with purple, next page must start with purple

### Issue: Markscheme not extracted
**Cause**: MS PDF table format not recognized
**Solution**: Manually enter markscheme in textarea

### Issue: Footer and header stitched together (FIXED)
**Cause**: Previous version incorrectly stitched content when page ended in purple region
**Solution**: Algorithm now correctly skips content in omit regions across page boundaries
- When page ends with purple (in omit region), content is NOT stitched
- Next page starts with purple, omit region ends, stitching resumes from that point
- No content between the two purple lines (across pages) is included

---

## Best Practices

1. **Always use pairs**: Each purple start needs a purple end
2. **Mark carefully**: Purple lines should bracket ONLY answer spaces
3. **Check page boundaries**: Ensure purple continuation across pages
4. **Verify preview**: Always review stitched image before importing
5. **Manual fallback**: If auto-extraction fails, enter markscheme manually

---

## Technical Implementation

### Data Structure

```javascript
{
  pages: [
    {
      page_number: 1,
      page_image: "base64...",
      has_green_line: true,
      has_red_line: false,
      purple_regions: [
        { start: 250, end: 450 },  // Y coordinates
        { start: 600, end: 750 }
      ]
    }
  ],
  marks: 10,
  markscheme: "Extracted or manual text"
}
```

### Canvas Cropping

```javascript
// For each page segment:
if (inPurpleRegion) {
  // Skip this segment
  continue;
} else {
  // Crop and stitch
  let part = crop(canvas, left, startY, width, endY - startY);
  stitchedCanvas = stitch(stitchedCanvas, part);
}
```

---

## Question Identifiers

Each sliced question is assigned a unique identifier in the format:

```
<filename>.pdf - Q<number>
```

**Example**:
```
9702_s23_qp_42.pdf - Q1
9702_s23_qp_42.pdf - Q2
9702_s23_qp_42.pdf - Q3
```

This identifier is displayed below the "Question X" heading in the Slice & Review modal. It helps you:
- Track which PDF each question came from
- Match questions to the correct markscheme even later
- Identify questions when working with multiple PDFs
- Maintain traceability in the question bank

The identifier is visible in the preview modal but is not stored in the database - it's for reference during the import process.

---

## Summary

The Purple Line feature (W key) provides precise control over which parts of questions are included in the final stitched image. By marking answer spaces with purple line pairs, you can create clean question previews that show only the question text, omitting blank answer regions.

**Key Points**:
- Purple lines work in **pairs** (start/end)
- Regions **between** purple lines are **omitted**
- Supports **cross-page** omission with proper handling
- **Multiple pairs** allowed per question
- Markschemes **auto-extracted** from table-format MS PDFs
- **Manual fallback** always available
- **Unique identifiers** (filename + Q number) for each question
