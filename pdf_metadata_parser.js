// PDF Filename Metadata Parser
// This function extracts grade, subject, year, and question type from Cambridge IGCSE/A-Level PDF filenames

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
  // m = May/June, s = October/November, w = February/March
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

// Function to auto-fill form fields based on parsed metadata
function autoFillFormFields(metadata, grades, subjects) {
  // Auto-select grade
  if (metadata.grade) {
    const gradeSelect = document.getElementById('gradeSelect');
    for (let option of gradeSelect.options) {
      if (option.text === metadata.grade) {
        gradeSelect.value = option.value;
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
        break;
      }
    }
  }

  // Auto-fill year
  if (metadata.year) {
    const yearInput = document.getElementById('yearInput');
    yearInput.value = metadata.year;
  }
}

// Example usage:
// const metadata = parseFileMetadata('9702_s23_qp_41.pdf');
// console.log(metadata);
// Output: {
//   subjectCode: '9702',
//   subject: 'Physics',
//   gradeLevel: 'A-Level',
//   grade: 'A-Level Physics',
//   year: 2023,
//   paperCode: '41',
//   questionType: 'A Level Structured Questions'
// }
