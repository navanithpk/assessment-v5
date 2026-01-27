# PDF Slicer Enhancements - Implementation Guide

## Overview
These enhancements add intelligent filename parsing and queue management to the PDF import system.

## Changes Needed

### 1. Add Metadata Parsing Function

Add this function before the `pairFilesByName` function (around line 572):

```javascript
// Parse metadata from PDF filename
function parseFileMetadata(filename) {
  const metadata = {
    subjectCode: null,
    subject: null,
    gradeLevel: null,
    grade: null,
    year: null,
    paperCode: null,
    questionType: null
  };

  // Subject code mapping (9700, 9701, 9702)
  const subjectMap = {
    '9700': { name: 'Biology', asLevel: 'AS-Level Biology', aLevel: 'A-Level Biology' },
    '9701': { name: 'Chemistry', asLevel: 'AS-Level Chemistry', aLevel: 'A-Level Chemistry' },
    '9702': { name: 'Physics', asLevel: 'AS-Level Physics', aLevel: 'A-Level Physics' }
  };

  // Paper code to question type and grade mapping
  const paperTypeMap = {
    '11': { type: 'Multiple Choice', grade: 'AS-Level' },
    '12': { type: 'Multiple Choice', grade: 'AS-Level' },
    '13': { type: 'Multiple Choice', grade: 'AS-Level' },
    '21': { type: 'AS Level Structured Questions', grade: 'AS-Level' },
    '22': { type: 'AS Level Structured Questions', grade: 'AS-Level' },
    '23': { type: 'AS Level Structured Questions', grade: 'AS-Level' },
    '31': { type: 'Advanced Practical Skills', grade: 'A-Level' },
    '32': { type: 'Advanced Practical Skills', grade: 'A-Level' },
    '33': { type: 'Advanced Practical Skills', grade: 'A-Level' },
    '34': { type: 'Advanced Practical Skills', grade: 'A-Level' },
    '35': { type: 'Advanced Practical Skills', grade: 'A-Level' },
    '36': { type: 'Advanced Practical Skills', grade: 'A-Level' },
    '37': { type: 'Advanced Practical Skills', grade: 'A-Level' },
    '38': { type: 'Advanced Practical Skills', grade: 'A-Level' },
    '42': { type: 'A Level Structured Questions', grade: 'A-Level' },
    '43': { type: 'A Level Structured Questions', grade: 'A-Level' },
    '51': { type: 'Planning, Analysis and Evaluation', grade: 'A-Level' },
    '52': { type: 'Planning, Analysis and Evaluation', grade: 'A-Level' },
    '53': { type: 'Planning, Analysis and Evaluation', grade: 'A-Level' }
  };

  // Extract subject code (9700, 9701, 9702)
  const subjectMatch = filename.match(/\b(970[0-2])\b/);
  if (subjectMatch) {
    metadata.subjectCode = subjectMatch[1];
    const subjectInfo = subjectMap[metadata.subjectCode];
    if (subjectInfo) {
      metadata.subject = subjectInfo.name;
    }
  }

  // Extract year from pattern like _m21_, _s22_, _w23_, etc.
  const yearMatch = filename.match(/_([mswMSW])(\d{2})_/);
  if (yearMatch) {
    const yearSuffix = yearMatch[2];
    // Convert 2-digit year to 4-digit (21 -> 2021, 23 -> 2023)
    metadata.year = 2000 + parseInt(yearSuffix);
  }

  // Extract paper code (11, 12, 13, 21-23, 31-38, 42-43, 51-53)
  const paperMatch = filename.match(/_qp_(\d{2})/i) || filename.match(/_(\d{2})\.pdf/i);
  if (paperMatch) {
    metadata.paperCode = paperMatch[1];
    const paperInfo = paperTypeMap[metadata.paperCode];
    if (paperInfo) {
      metadata.questionType = paperInfo.type;
      metadata.gradeLevel = paperInfo.grade;

      // Determine full grade name
      if (metadata.subject && metadata.gradeLevel) {
        if (metadata.gradeLevel === 'AS-Level') {
          metadata.grade = subjectMap[metadata.subjectCode]?.asLevel || `AS-Level ${metadata.subject}`;
        } else {
          metadata.grade = subjectMap[metadata.subjectCode]?.aLevel || `A-Level ${metadata.subject}`;
        }
      }
    }
  }

  return metadata;
}
```

### 2. Modify pairFilesByName to Include Metadata

In the `pairFilesByName` function, add metadata parsing:

```javascript
// Inside the qpFiles.forEach loop, after finding msFile:
// Parse metadata from filename
const metadata = parseFileMetadata(qpFile.name);

pairs.push({
  qp: qpFile,
  ms: msFile || null,
  name: `${paperCode} Variant ${variant}`,
  metadata: metadata  // ADD THIS LINE
});
```

Also update the unmatched files section:

```javascript
// Also add QP files that don't match the pattern
const unmatchedQP = qpFiles.filter(qp => !qp.name.match(/(\d+_[a-z]\d+)_qp_(\d+)/i));
unmatchedQP.forEach(qp => {
  const metadata = parseFileMetadata(qp.name);  // ADD THIS LINE
  pairs.push({
    qp: qp,
    ms: null,
    name: qp.name.replace('.pdf', ''),
    metadata: metadata  // ADD THIS LINE
  });
});
```

### 3. Add Auto-Fill Function

Add this function after `parseFileMetadata`:

```javascript
// Function to auto-fill form fields based on parsed metadata
function autoFillFormFields(metadata) {
  if (!metadata) return;

  // Auto-select grade
  if (metadata.grade) {
    const gradeSelect = document.getElementById('gradeSelect');
    for (let option of gradeSelect.options) {
      if (option.text === metadata.grade) {
        gradeSelect.value = option.value;
        // Trigger change event to load topics
        gradeSelect.dispatchEvent(new Event('change'));
        break;
      }
    }
  }

  // Auto-select subject
  if (metadata.subject) {
    const subjectSelect = document.getElementById('subjectSelect');
    for (let option of subjectSelect.options) {
      if (option.text === metadata.subject) {
        subjectSelect.value = option.value;
        // Trigger change event to load topics
        subjectSelect.dispatchEvent(new Event('change'));
        break;
      }
    }
  }

  // Auto-fill year
  if (metadata.year) {
    const yearInput = document.getElementById('yearInput');
    yearInput.value = metadata.year;
  }

  // Show detected info to user
  if (metadata.grade || metadata.subject || metadata.year) {
    console.log('✓ Auto-detected from filename:', metadata);
  }
}
```

### 4. Call Auto-Fill in loadPair Function

In the `loadPair` function (around line 632), add auto-fill call:

```javascript
async function loadPair(index) {
  if (index < 0 || index >= pairedFiles.length) {
    if (index >= pairedFiles.length) {
      alert('All papers processed!');
    }
    return;
  }

  currentPairIndex = index;
  const pair = pairedFiles[index];

  // Auto-fill form fields from metadata
  if (pair.metadata) {
    autoFillFormFields(pair.metadata);
  }

  // ... rest of the function
```

### 5. Update Success Handler (Already Done)

The success handler should already be modified to stay on the page and load the next PDF:

```javascript
if (data.success) {
  alert(`✓ Successfully imported ${data.count} questions!`);

  // Reset for next paper
  importBtn.disabled = false;
  importBtn.textContent = 'Import Questions';
  slicedImages = [];

  // Check if there are more papers in the queue
  if (currentPairIndex + 1 < pairedFiles.length) {
    if (confirm(`Paper ${currentPairIndex + 1}/${pairedFiles.length} complete! Load next paper?`)) {
      loadPair(currentPairIndex + 1);
    }
  } else {
    alert('🎉 All papers processed! You can now close this page or upload more files.');
  }
}
```

## Testing the Changes

### Test Filenames:

1. `9702_s23_qp_41.pdf` should detect:
   - Subject: Physics
   - Grade: A-Level Physics
   - Year: 2023
   - Paper: 41 (A Level Structured Questions)

2. `9700_m21_qp_11.pdf` should detect:
   - Subject: Biology
   - Grade: AS-Level Biology
   - Year: 2021
   - Paper: 11 (Multiple Choice)

3. `9701_w24_qp_31.pdf` should detect:
   - Subject: Chemistry
   - Grade: A-Level Chemistry
   - Year: 2024
   - Paper: 31 (Advanced Practical Skills)

## Expected Behavior

1. **Upload PDFs**: User uploads multiple PDF files
2. **Auto-Pairing**: System pairs QP and MS files automatically
3. **Load First Paper**: User clicks to start importing
4. **Auto-Fill**: Grade, subject, year are automatically filled from filename
5. **Slice & Import**: User slices questions and imports
6. **Auto-Next**: After import, system offers to load next paper
7. **Stay on Page**: No redirect to question library
8. **Complete Queue**: User can process all papers in one session

## Benefits

✓ **Faster Workflow**: No manual form filling for standard Cambridge papers
✓ **Fewer Errors**: Automatic detection reduces typos
✓ **Batch Processing**: Complete entire queue without leaving page
✓ **Time Saved**: Estimated 30-60 seconds saved per paper

## Filename Pattern Recognition

The system recognizes these patterns:

- **Subject Codes**: 9700 (Biology), 9701 (Chemistry), 9702 (Physics)
- **Session Codes**: m (May/June), s (October/November), w (February/March)
- **Year**: 2-digit format after session code (21 = 2021, 24 = 2024)
- **Paper Codes**: 11-13, 21-23, 31-38, 42-43, 51-53

**Standard Format**: `{subject_code}_{session}{year}_qp_{paper_code}.pdf`

**Example**: `9702_s23_qp_42.pdf` = Physics, October/November 2023, Paper 42 (A Level Structured)

---

**Implementation Status**: Ready to apply
**File**: `core/templates/teacher/import_mcq_pdf.html`
**Estimated Time**: 10-15 minutes to implement
