"""
PDF to JSON Slicer - Uses colored line detection and OCR to extract structured questions
"""
import json
import base64
import io
import re
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .models import Grade, Subject, Topic


# Configure pytesseract path if needed (Windows)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def detect_colored_lines(page, color_tolerance=30):
    """
    Detect horizontal colored lines (red, green, purple) in a PDF page.
    Returns list of (y_position, color_type, line_height) tuples.
    """
    lines = []

    # Get page as image for pixel analysis
    mat = fitz.Matrix(2, 2)  # 2x zoom for better detection
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    width, height = img.size
    pixels = img.load()

    # Scan for colored horizontal lines
    y = 0
    while y < height:
        # Sample pixels across the width
        red_count = 0
        green_count = 0
        purple_count = 0
        total_samples = 0

        for x in range(0, width, 10):  # Sample every 10 pixels
            r, g, b = pixels[x, y]
            total_samples += 1

            # Red detection (high R, low G, low B)
            if r > 180 and g < 100 and b < 100:
                red_count += 1
            # Green detection (low R, high G, low B)
            elif g > 150 and r < 100 and b < 100:
                green_count += 1
            # Purple detection (high R, low G, high B)
            elif r > 150 and b > 150 and g < 100:
                purple_count += 1

        # If significant portion is colored, it's a line
        threshold = total_samples * 0.3  # 30% of width

        if red_count > threshold:
            lines.append((y / 2, 'red', 2))  # Divide by 2 due to zoom
        elif green_count > threshold:
            lines.append((y / 2, 'green', 2))
        elif purple_count > threshold:
            lines.append((y / 2, 'purple', 2))

        y += 2  # Skip pixels for speed

    # Merge nearby lines of same color
    merged = []
    for line in lines:
        if not merged or abs(line[0] - merged[-1][0]) > 10 or line[1] != merged[-1][1]:
            merged.append(line)

    return merged


def extract_region_as_image(page, y_start, y_end, zoom=2):
    """
    Extract a region of a PDF page as a base64 encoded image.
    """
    rect = fitz.Rect(0, y_start, page.rect.width, y_end)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=rect)

    img_data = pix.tobytes("png")
    return base64.b64encode(img_data).decode('utf-8')


def ocr_region(page, y_start, y_end, zoom=2):
    """
    Extract text from a region using OCR.
    """
    rect = fitz.Rect(0, y_start, page.rect.width, y_end)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=rect)

    # Convert to PIL Image
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Run OCR
    try:
        text = pytesseract.image_to_string(img, config='--psm 6')
        return text.strip()
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""


def parse_question_number(text):
    """
    Try to extract question number and part letter from OCR text.
    Returns (number, letter) tuple.
    """
    # Pattern: "1", "1.", "1 (a)", "(a)", "a)", etc.

    # Try main question number
    main_match = re.match(r'^(\d+)[\.\s\)]', text)
    if main_match:
        num = int(main_match.group(1))
        # Check for part letter after
        part_match = re.search(r'\(([a-z])\)', text)
        if part_match:
            return (num, part_match.group(1))
        return (num, None)

    # Try just part letter
    part_match = re.match(r'^\(?([a-z])\)?[\.\s\)]', text)
    if part_match:
        return (None, part_match.group(1))

    return (None, None)


def process_pdf_for_json(qp_file, ms_file=None):
    """
    Process question paper (and optional mark scheme) PDF to extract
    structured questions with OCR.

    Returns list of question dictionaries in the JSON format.
    """
    questions = []

    # Open question paper
    qp_doc = fitz.open(stream=qp_file.read(), filetype="pdf")

    ms_doc = None
    if ms_file:
        ms_doc = fitz.open(stream=ms_file.read(), filetype="pdf")

    current_question = None
    question_number = 0

    for page_num in range(len(qp_doc)):
        page = qp_doc[page_num]
        page_height = page.rect.height

        # Detect colored lines
        lines = detect_colored_lines(page)

        if not lines:
            # No lines detected, try to OCR the whole page
            # and detect question patterns
            full_text = ocr_region(page, 0, page_height)
            # Could implement text-based question detection here
            continue

        # Process regions between lines
        prev_y = 0
        prev_color = None

        for y_pos, color, _ in lines:
            if prev_color:
                # Extract region between previous line and this one
                region_img = extract_region_as_image(page, prev_y, y_pos)
                region_text = ocr_region(page, prev_y, y_pos)

                # Parse based on previous line color
                if prev_color == 'red':
                    # Red = new main question
                    if current_question:
                        questions.append(current_question)

                    question_number += 1
                    num, part = parse_question_number(region_text)

                    current_question = {
                        'number': num or question_number,
                        'type': 'parent',
                        'stem': f'<img src="data:image/png;base64,{region_img}" />',
                        'stem_text': region_text,
                        'marks': 0,
                        'parts': []
                    }

                elif prev_color == 'green':
                    # Green = sub-part
                    if current_question:
                        num, part = parse_question_number(region_text)
                        letter = part or chr(97 + len(current_question['parts']))

                        # Try to extract marks from text (e.g., "[3]" or "(3 marks)")
                        marks_match = re.search(r'\[(\d+)\]|\((\d+)\s*marks?\)', region_text, re.IGNORECASE)
                        marks = int(marks_match.group(1) or marks_match.group(2)) if marks_match else 1

                        current_question['parts'].append({
                            'letter': letter,
                            'content': f'<img src="data:image/png;base64,{region_img}" />',
                            'content_text': region_text,
                            'answer': '',
                            'marks': marks
                        })

                elif prev_color == 'purple':
                    # Purple = answer/mark scheme region
                    if current_question and current_question['parts']:
                        # Append to last part's answer
                        last_part = current_question['parts'][-1]
                        last_part['answer'] = f'<img src="data:image/png;base64,{region_img}" />'
                        last_part['answer_text'] = region_text

            prev_y = y_pos
            prev_color = color

        # Handle last region on page
        if prev_color and prev_y < page_height - 50:
            region_img = extract_region_as_image(page, prev_y, page_height)
            region_text = ocr_region(page, prev_y, page_height)

            if prev_color == 'green' and current_question:
                num, part = parse_question_number(region_text)
                letter = part or chr(97 + len(current_question['parts']))

                marks_match = re.search(r'\[(\d+)\]|\((\d+)\s*marks?\)', region_text, re.IGNORECASE)
                marks = int(marks_match.group(1) or marks_match.group(2)) if marks_match else 1

                current_question['parts'].append({
                    'letter': letter,
                    'content': f'<img src="data:image/png;base64,{region_img}" />',
                    'content_text': region_text,
                    'answer': '',
                    'marks': marks
                })

    # Don't forget the last question
    if current_question:
        questions.append(current_question)

    # Calculate total marks for each question
    for q in questions:
        if q['type'] == 'parent' and q['parts']:
            q['marks'] = sum(p.get('marks', 0) for p in q['parts'])
        # Convert parent to standalone if no parts
        if q['type'] == 'parent' and not q['parts']:
            q['type'] = 'standalone'

    qp_doc.close()
    if ms_doc:
        ms_doc.close()

    return questions


@login_required
def pdf_to_json_slicer(request):
    """
    PDF to JSON Slicer page - upload PDFs, detect colored lines,
    OCR content, and generate structured JSON for the question editor.
    """
    grades = Grade.objects.all().order_by('name')
    subjects = Subject.objects.all().order_by('name')
    topics = Topic.objects.all().order_by('name')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'process_pdf':
            qp_file = request.FILES.get('qp_file')
            ms_file = request.FILES.get('ms_file')

            if not qp_file:
                return JsonResponse({'success': False, 'error': 'Question paper PDF is required'})

            try:
                questions = process_pdf_for_json(qp_file, ms_file)

                return JsonResponse({
                    'success': True,
                    'questions': questions,
                    'count': len(questions)
                })

            except Exception as e:
                import traceback
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })

    return render(request, 'teacher/pdf_to_json_slicer.html', {
        'grades': grades,
        'subjects': subjects,
        'topics': topics,
    })


@login_required
@require_http_methods(["POST"])
def ocr_image_region(request):
    """
    API endpoint to OCR a specific image region.
    Accepts base64 image data and returns extracted text.
    """
    try:
        data = json.loads(request.body)
        image_data = data.get('image')

        if not image_data:
            return JsonResponse({'success': False, 'error': 'No image data provided'})

        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        # Decode base64
        img_bytes = base64.b64decode(image_data)
        img = Image.open(io.BytesIO(img_bytes))

        # Run OCR
        text = pytesseract.image_to_string(img, config='--psm 6')

        return JsonResponse({
            'success': True,
            'text': text.strip()
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
