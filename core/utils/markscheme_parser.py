"""
Cambridge Mark Scheme Table Parser
Extracts question answers from the standard Cambridge MS table format:
| Question | Answer | Marks |
"""

import re
import fitz  # PyMuPDF


def extract_ms_table_from_pdf(pdf_file, start_page=4):
    """
    Extract mark scheme data from Cambridge-format PDF.
    The table typically starts at page 5 (index 4).

    Returns dict: {
        '1(a)': [{'answer': '78 N', 'marks': 'A3'}, ...],
        '1(b)': [...],
        ...
    }
    """
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")

    markscheme_data = {}
    current_question = None

    for page_num in range(start_page, len(doc)):
        page = doc[page_num]

        # Extract text with layout preservation
        text = page.get_text("text")
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip header rows
            if 'Question' in line and 'Answer' in line and 'Marks' in line:
                continue
            if 'Cambridge IGCSE' in line or 'Mark Scheme' in line or 'PUBLISHED' in line:
                continue

            # Try to parse as question row
            # Pattern: "1(a)" or "2(b)(i)" at start
            q_match = re.match(r'^(\d+)(\([a-z]\))?(\([ivx]+\))?', line)

            if q_match:
                # New question/part detected
                q_num = q_match.group(1)
                q_part = q_match.group(2) or ''
                q_subpart = q_match.group(3) or ''
                current_question = f"{q_num}{q_part}{q_subpart}".strip()

                if current_question not in markscheme_data:
                    markscheme_data[current_question] = []

                # Extract answer and marks from rest of line
                rest = line[q_match.end():].strip()

                # Try to extract marks (usually at the end: A1, B2, C1, M1, etc.)
                marks_match = re.search(r'\b([ABCM]\d+)\s*$', rest)
                if marks_match:
                    marks = marks_match.group(1)
                    answer = rest[:marks_match.start()].strip()
                else:
                    marks = ''
                    answer = rest

                if answer or marks:
                    markscheme_data[current_question].append({
                        'answer': answer,
                        'marks': marks
                    })

            elif current_question:
                # Continuation of previous question's answer
                # Check for marks pattern at end
                marks_match = re.search(r'\b([ABCM]\d+)\s*$', line)
                if marks_match:
                    marks = marks_match.group(1)
                    answer = line[:marks_match.start()].strip()
                else:
                    marks = ''
                    answer = line

                if answer or marks:
                    markscheme_data[current_question].append({
                        'answer': answer,
                        'marks': marks
                    })

    doc.close()
    return markscheme_data


def extract_ms_table_with_tables(pdf_file, start_page=4):
    """
    Alternative extraction using PyMuPDF's table detection.
    More reliable for structured tables.
    """
    pdf_file.seek(0)
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")

    markscheme_data = {}

    for page_num in range(start_page, len(doc)):
        page = doc[page_num]

        # Try to find tables
        tables = page.find_tables()

        for table in tables:
            # Extract table data
            data = table.extract()

            current_question = None

            for row in data:
                if not row or len(row) < 2:
                    continue

                # Skip header row
                if row[0] and 'Question' in str(row[0]):
                    continue

                cell0 = str(row[0]).strip() if row[0] else ''
                cell1 = str(row[1]).strip() if len(row) > 1 and row[1] else ''
                cell2 = str(row[2]).strip() if len(row) > 2 and row[2] else ''

                # Check if first cell has question number
                q_match = re.match(r'^(\d+)(\([a-z]\))?(\([ivx]+\))?', cell0)

                if q_match:
                    current_question = cell0.strip()
                    if current_question not in markscheme_data:
                        markscheme_data[current_question] = []

                # Add answer data
                if current_question and (cell1 or cell2):
                    markscheme_data[current_question].append({
                        'answer': cell1,
                        'marks': cell2
                    })

    doc.close()
    return markscheme_data


def get_markscheme_for_question(ms_data, question_number):
    """
    Get all mark scheme entries for a given question number.

    Args:
        ms_data: Dict from extract_ms_table_from_pdf
        question_number: int or str like 1, "1", etc.

    Returns:
        Dict with all parts and their answers
    """
    q_num = str(question_number)
    result = {}

    for key, answers in ms_data.items():
        # Check if this key starts with the question number
        if key.startswith(q_num) and (len(key) == len(q_num) or key[len(q_num)] == '('):
            result[key] = answers

    return result


def format_markscheme_html(ms_entries):
    """
    Format mark scheme entries as HTML for display.

    Args:
        ms_entries: Dict from get_markscheme_for_question

    Returns:
        HTML string
    """
    if not ms_entries:
        return '<em>No mark scheme found</em>'

    html = '<div class="ms-table">'

    for q_key in sorted(ms_entries.keys()):
        answers = ms_entries[q_key]
        html += f'<div class="ms-question"><strong>{q_key}</strong></div>'

        for ans in answers:
            marks_badge = f'<span class="ms-marks">{ans["marks"]}</span>' if ans['marks'] else ''
            html += f'<div class="ms-answer">{ans["answer"]} {marks_badge}</div>'

    html += '</div>'
    return html


def calculate_total_marks(ms_entries):
    """
    Calculate total marks from mark scheme entries.
    Parses marks like A3, B1, C1, M2 and sums the numbers.
    """
    total = 0

    for q_key, answers in ms_entries.items():
        for ans in answers:
            marks_str = ans.get('marks', '')
            # Extract number from marks like "A3", "B1", "C1"
            num_match = re.search(r'(\d+)', marks_str)
            if num_match:
                total += int(num_match.group(1))

    return total
