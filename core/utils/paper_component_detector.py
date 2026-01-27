"""
Paper Component Detection for IGCSE Papers
Automatically detects paper type from paper code
"""

# Subject code mapping
SUBJECT_CODES = {
    '0625': 'Physics',
    '0620': 'Chemistry',
    '0610': 'Biology',
}

# Paper component mapping
PAPER_COMPONENTS = {
    'MCQ': ['11', '12', '13', '21', '22', '23'],
    'Theory': ['31', '32', '33', '41', '42', '43'],
    'Practical': ['51', '52', '53'],
    'Alternative to Practical': ['61', '62', '63'],
}

def detect_subject(paper_code):
    """
    Detect subject from paper code

    Args:
        paper_code (str): Paper code like "0625_s23_qp_11"

    Returns:
        str: Subject name or None
    """
    if not paper_code:
        return None

    # Extract subject code (first 4 digits)
    subject_code = paper_code[:4]
    return SUBJECT_CODES.get(subject_code)


def detect_component(paper_code):
    """
    Detect paper component from paper code

    Args:
        paper_code (str): Paper code like "0625_s23_qp_11"

    Returns:
        str: Component name or None

    Examples:
        "0625_s23_qp_11" -> "MCQ"
        "0625_s23_qp_31" -> "Theory"
        "0625_s23_qp_51" -> "Practical"
        "0625_s23_qp_61" -> "Alternative to Practical"
    """
    if not paper_code:
        return None

    # Extract paper component (last 2 digits before extension)
    parts = paper_code.replace('.pdf', '').split('_')

    # Find the part that looks like paper number (2 digits)
    paper_number = None
    for part in reversed(parts):
        if len(part) == 2 and part.isdigit():
            paper_number = part
            break

    if not paper_number:
        return None

    # Check which component it belongs to
    for component, codes in PAPER_COMPONENTS.items():
        if paper_number in codes:
            return component

    return None


def detect_year(paper_code):
    """
    Detect year from paper code

    Args:
        paper_code (str): Paper code like "0625_s23_qp_11"

    Returns:
        int: Year (e.g., 2023) or None

    Examples:
        "0625_s23_qp_11" -> 2023
        "0625_w22_qp_31" -> 2022
    """
    if not paper_code:
        return None

    parts = paper_code.split('_')

    for part in parts:
        # Look for pattern like "s23", "w22" (season + 2-digit year)
        if len(part) == 3 and part[0] in ['s', 'w', 'm'] and part[1:].isdigit():
            year_2digit = int(part[1:])
            # Convert to 4-digit year (assume 2000s)
            return 2000 + year_2digit

    return None


def parse_paper_code(paper_code):
    """
    Parse complete paper information from code

    Args:
        paper_code (str): Paper code like "0625_s23_qp_11"

    Returns:
        dict: {
            'subject': str,
            'component': str,
            'year': int,
            'paper_code': str
        }
    """
    return {
        'subject': detect_subject(paper_code),
        'component': detect_component(paper_code),
        'year': detect_year(paper_code),
        'paper_code': paper_code
    }


def is_mcq_paper(paper_code):
    """Check if paper is MCQ type"""
    component = detect_component(paper_code)
    return component == 'MCQ'


def is_theory_paper(paper_code):
    """Check if paper is Theory type"""
    component = detect_component(paper_code)
    return component in ['Theory', 'Practical', 'Alternative to Practical']
