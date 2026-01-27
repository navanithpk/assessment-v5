"""
Image Processing Utilities for Structured Question Papers
Handles multi-page question stitching and answer space rasterization
"""

import base64
import io
from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Optional


def stitch_question_pages(pages_data: List[dict]) -> str:
    """
    Stitch multiple pages into a single tall question image.

    This is the core algorithm for handling multi-page questions.
    It combines pages marked with green/red lines into one vertical image.

    Args:
        pages_data: List of dicts with structure:
            {
                'page_number': int,
                'page_image': str (base64),
                'has_green_line': bool,
                'has_red_line': bool,
                'blue_rect_x': int,
                'blue_rect_y': int,
                'blue_rect_width': int,
                'blue_rect_height': int
            }

    Returns:
        Base64 encoded PNG of stitched image

    Algorithm:
        1. Find question boundaries (green → red)
        2. Crop each page to blue rectangle bounds
        3. Stack vertically
        4. Return as single image
    """

    if not pages_data:
        raise ValueError("No pages provided for stitching")

    # Decode all page images
    page_images = []
    target_width = None

    for page in pages_data:
        # Decode base64 image
        if page['page_image'].startswith('data:image'):
            # Remove data URL prefix
            img_data = page['page_image'].split(',')[1]
        else:
            img_data = page['page_image']

        img_bytes = base64.b64decode(img_data)
        img = Image.open(io.BytesIO(img_bytes))

        # Crop to blue rectangle bounds if specified
        if all([
            page.get('blue_rect_x') is not None,
            page.get('blue_rect_y') is not None,
            page.get('blue_rect_width') is not None,
            page.get('blue_rect_height') is not None
        ]):
            x = page['blue_rect_x']
            y = page['blue_rect_y']
            w = page['blue_rect_width']
            h = page['blue_rect_height']

            # Crop to rectangle
            img = img.crop((x, y, x + w, y + h))

            # Set target width (should be consistent across pages)
            if target_width is None:
                target_width = w

        page_images.append(img)

    # Calculate total height
    total_height = sum(img.height for img in page_images)

    # Use the width from first image if not set
    if target_width is None:
        target_width = page_images[0].width

    # Create combined image
    stitched = Image.new('RGB', (target_width, total_height), 'white')

    # Paste pages vertically
    current_y = 0
    for img in page_images:
        stitched.paste(img, (0, current_y))
        current_y += img.height

    # Convert to base64
    buffer = io.BytesIO()
    stitched.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/png;base64,{img_str}"


def detect_page_markers(image_data: str, line_color_threshold: int = 10) -> dict:
    """
    Detect green and red lines in a page image.

    This helps identify question boundaries automatically.

    Args:
        image_data: Base64 encoded image
        line_color_threshold: Tolerance for color detection

    Returns:
        {
            'has_green_line_top': bool,
            'has_red_line_bottom': bool,
            'green_line_y': int or None,
            'red_line_y': int or None
        }
    """

    # Decode image
    if image_data.startswith('data:image'):
        img_data = image_data.split(',')[1]
    else:
        img_data = image_data

    img_bytes = base64.b64decode(img_data)
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')

    width, height = img.size

    # Check top 50 pixels for green line
    has_green_top = False
    green_y = None

    for y in range(min(50, height)):
        # Sample pixels across the width
        green_count = 0
        for x in range(0, width, 10):  # Sample every 10 pixels
            r, g, b = img.getpixel((x, y))
            # Green is high G, low R and B
            if g > 200 and r < 100 and b < 100:
                green_count += 1

        # If most samples are green, it's a green line
        if green_count > (width // 10) * 0.7:  # 70% threshold
            has_green_top = True
            green_y = y
            break

    # Check bottom 50 pixels for red line
    has_red_bottom = False
    red_y = None

    for y in range(max(0, height - 50), height):
        red_count = 0
        for x in range(0, width, 10):
            r, g, b = img.getpixel((x, y))
            # Red is high R, low G and B
            if r > 200 and g < 100 and b < 100:
                red_count += 1

        if red_count > (width // 10) * 0.7:
            has_red_bottom = True
            red_y = y
            break

    return {
        'has_green_line_top': has_green_top,
        'has_red_line_bottom': has_red_bottom,
        'green_line_y': green_y,
        'red_line_y': red_y
    }


def detect_blue_rectangle(image_data: str) -> Optional[Tuple[int, int, int, int]]:
    """
    Detect blue rectangle bounds in an image.

    The blue rectangle defines the question area width.

    Args:
        image_data: Base64 encoded image

    Returns:
        (x, y, width, height) or None if not found
    """

    # Decode image
    if image_data.startswith('data:image'):
        img_data = image_data.split(',')[1]
    else:
        img_data = image_data

    img_bytes = base64.b64decode(img_data)
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')

    width, height = img.size

    # Find blue pixels (high B, low R and G)
    blue_pixels = []

    for y in range(0, height, 5):  # Sample every 5 pixels
        for x in range(0, width, 5):
            r, g, b = img.getpixel((x, y))
            if b > 200 and r < 100 and g < 100:
                blue_pixels.append((x, y))

    if not blue_pixels:
        return None

    # Find bounding box of blue pixels
    min_x = min(p[0] for p in blue_pixels)
    max_x = max(p[0] for p in blue_pixels)
    min_y = min(p[1] for p in blue_pixels)
    max_y = max(p[1] for p in blue_pixels)

    return (min_x, min_y, max_x - min_x, max_y - min_y)


def create_answer_overlay(
    answer_spaces: List[dict],
    question_width: int,
    question_height: int
) -> str:
    """
    Create a transparent overlay with answer space placeholders.

    This shows where students will type their answers.

    Args:
        answer_spaces: List of dicts with {x, y, width, height, order, type}
        question_width: Width of question image
        question_height: Height of question image

    Returns:
        Base64 encoded PNG with transparency
    """

    # Create transparent image
    overlay = Image.new('RGBA', (question_width, question_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for space in answer_spaces:
        x = space['x']
        y = space['y']
        w = space['width']
        h = space['height']

        # Draw semi-transparent box
        draw.rectangle(
            [(x, y), (x + w, y + h)],
            fill=(173, 216, 230, 100),  # Light blue, 40% opacity
            outline=(70, 130, 180, 200),  # Steel blue, 80% opacity
            width=2
        )

        # Draw order number
        draw.text(
            (x + 5, y + 5),
            f"#{space['order']}",
            fill=(0, 0, 0, 255)
        )

    # Convert to base64
    buffer = io.BytesIO()
    overlay.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/png;base64,{img_str}"


def rasterize_html_answer(html_content: str, width: int, height: int) -> str:
    """
    Convert HTML answer to rasterized PNG.

    This will be done client-side with html2canvas.js in the actual implementation.
    This function is a placeholder for the backend equivalent if needed.

    Args:
        html_content: HTML from rich text editor
        width: Target width in pixels
        height: Target height in pixels

    Returns:
        Base64 encoded PNG

    Note:
        For the prototype, this will be handled by frontend JavaScript.
        This backend function is for potential server-side rendering if needed.
    """

    # For now, create a placeholder image
    # Real implementation will use html2canvas.js on frontend

    img = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Add placeholder text
    draw.text(
        (10, 10),
        "Student's answer will be rendered here",
        fill=(0, 0, 0, 255)
    )

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/png;base64,{img_str}"


def composite_answer_image(
    question_image: str,
    answer_overlays: List[dict]
) -> str:
    """
    Composite question image with student answer overlays.

    This creates the final grading view image.

    Args:
        question_image: Base64 encoded question image
        answer_overlays: List of dicts with {x, y, rasterized_image}

    Returns:
        Base64 encoded composite PNG
    """

    # Decode question image
    if question_image.startswith('data:image'):
        img_data = question_image.split(',')[1]
    else:
        img_data = question_image

    img_bytes = base64.b64decode(img_data)
    base_img = Image.open(io.BytesIO(img_bytes)).convert('RGBA')

    # Overlay each answer
    for overlay_data in answer_overlays:
        x = overlay_data['x']
        y = overlay_data['y']

        # Decode overlay image
        if overlay_data['rasterized_image'].startswith('data:image'):
            overlay_img_data = overlay_data['rasterized_image'].split(',')[1]
        else:
            overlay_img_data = overlay_data['rasterized_image']

        overlay_bytes = base64.b64decode(overlay_img_data)
        overlay_img = Image.open(io.BytesIO(overlay_bytes)).convert('RGBA')

        # Paste overlay at position
        base_img.paste(overlay_img, (x, y), overlay_img)

    # Convert to RGB for final output
    final_img = Image.new('RGB', base_img.size, (255, 255, 255))
    final_img.paste(base_img, (0, 0), base_img)

    # Convert to base64
    buffer = io.BytesIO()
    final_img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/png;base64,{img_str}"
