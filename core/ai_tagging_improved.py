"""
Improved AI Tagging System with OCR, Context-Aware Prompting, and Comprehensive Logging
"""
import os
import re
import json
import time
import logging
import base64
from datetime import datetime
from io import BytesIO
from PIL import Image
import requests
from django.http import StreamingHttpResponse
from django.db.models import Q

try:
    import pytesseract
    # Configure Tesseract path for Windows if not in PATH
    if os.name == 'nt':  # Windows
        tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Warning: pytesseract not available. Install with: pip install pytesseract")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AITaggingLogger:
    """Comprehensive logging for AI tagging operations"""

    def __init__(self):
        self.log_file = f'ai_tagging_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        self.log_path = os.path.join('logs', self.log_file)
        os.makedirs('logs', exist_ok=True)

        # Setup logger
        self.logger = logging.getLogger('ai_tagging')
        self.logger.setLevel(logging.DEBUG)

        # File handler
        file_handler = logging.FileHandler(self.log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Statistics
        self.stats = {
            'total_questions': 0,
            'processed': 0,
            'topics_tagged': 0,
            'los_tagged': 0,
            'skipped': 0,
            'errors': 0,
            'anthropic_calls': 0,
            'gemini_calls': 0,
            'lmstudio_calls': 0,
            'ocr_extractions': 0
        }

    def log_start(self, total):
        self.stats['total_questions'] = total
        self.logger.info("="*80)
        self.logger.info(f"BULK AI TAGGING STARTED - Total Questions: {total}")
        self.logger.info("="*80)

    def log_question_start(self, question_id, question_text_preview):
        self.logger.info(f"\n--- Processing Question {question_id} ---")
        self.logger.debug(f"Question Preview: {question_text_preview[:200]}")

    def log_ocr_extraction(self, question_id, extracted_text):
        self.stats['ocr_extractions'] += 1
        self.logger.info(f"OCR Extracted from Question {question_id}: {len(extracted_text)} chars")
        self.logger.debug(f"OCR Text: {extracted_text[:500]}")

    def log_prompt(self, service, prompt):
        self.logger.debug(f"\n[{service}] PROMPT:")
        self.logger.debug("-"*60)
        self.logger.debug(prompt)
        self.logger.debug("-"*60)

    def log_response(self, service, response):
        self.logger.debug(f"\n[{service}] RESPONSE:")
        self.logger.debug("-"*60)
        self.logger.debug(response)
        self.logger.debug("-"*60)

    def log_topic_tagged(self, question_id, topic_name, service):
        self.stats['topics_tagged'] += 1
        self.logger.info(f"✓ Question {question_id} tagged with Topic: {topic_name} (via {service})")

    def log_lo_tagged(self, question_id, lo_codes, service):
        self.stats['los_tagged'] += len(lo_codes)
        self.logger.info(f"✓ Question {question_id} tagged with LOs: {', '.join(lo_codes)} (via {service})")

    def log_error(self, question_id, error_msg):
        self.stats['errors'] += 1
        self.logger.error(f"✗ Error on Question {question_id}: {error_msg}")

    def log_skip(self, question_id, reason):
        self.stats['skipped'] += 1
        self.logger.info(f"⊘ Skipped Question {question_id}: {reason}")

    def log_info(self, message):
        """General info logging"""
        self.logger.info(message)

    def log_warning(self, question_id, message):
        """Warning logging"""
        self.logger.warning(f"⚠ Question {question_id}: {message}")

    def log_summary(self):
        """Alias for log_complete"""
        self.log_complete()

    def log_api_call(self, service):
        if service == 'anthropic':
            self.stats['anthropic_calls'] += 1
        elif service == 'gemini':
            self.stats['gemini_calls'] += 1
        elif service == 'lmstudio':
            self.stats['lmstudio_calls'] += 1

    def log_complete(self):
        self.logger.info("\n" + "="*80)
        self.logger.info("BULK AI TAGGING COMPLETED")
        self.logger.info("="*80)
        self.logger.info(f"Total Questions: {self.stats['total_questions']}")
        self.logger.info(f"Processed: {self.stats['processed']}")
        self.logger.info(f"Topics Tagged: {self.stats['topics_tagged']}")
        self.logger.info(f"LOs Tagged: {self.stats['los_tagged']}")
        self.logger.info(f"Skipped: {self.stats['skipped']}")
        self.logger.info(f"Errors: {self.stats['errors']}")
        self.logger.info(f"\nAPI Calls:")
        self.logger.info(f"  Anthropic: {self.stats['anthropic_calls']}")
        self.logger.info(f"  Google Gemini: {self.stats['gemini_calls']}")
        self.logger.info(f"  LMStudio: {self.stats['lmstudio_calls']}")
        self.logger.info(f"  OCR Extractions: {self.stats['ocr_extractions']}")
        self.logger.info("="*80)

    def get_log_path(self):
        return self.log_path


class ImageTextExtractor:
    """Extract text from images using OCR"""

    @staticmethod
    def extract_from_base64(base64_string):
        """Extract text from base64 image using Tesseract OCR"""
        if not TESSERACT_AVAILABLE:
            return ""

        try:
            # Remove data URI prefix if present
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]

            # Decode base64 to image
            image_data = base64.b64decode(base64_string)
            image = Image.open(BytesIO(image_data))

            # Extract text using OCR
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            print(f"OCR extraction error: {str(e)}")
            return ""

    @staticmethod
    def extract_from_html(html_content):
        """Extract text from all images in HTML content"""
        if not html_content:
            return ""

        # Find all base64 images
        img_pattern = r'data:image/[^;]+;base64,([^"]+)'
        matches = re.findall(img_pattern, html_content)

        extracted_texts = []
        for base64_data in matches:
            text = ImageTextExtractor.extract_from_base64(base64_data)
            if text:
                extracted_texts.append(text)

        return " ".join(extracted_texts)


class ContextAwarePromptBuilder:
    """Build context-aware prompts for AI services"""

    @staticmethod
    def build_topic_prompt(question_text, image_text, subject_name, grade_name, topic_list):
        """Build comprehensive prompt for topic selection"""

        # Combine question text and OCR text
        full_question = question_text
        if image_text:
            full_question += f"\n\n[Image Content]: {image_text}"

        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', full_question)

        # Build topic list
        topic_names = '\n'.join([f"{i+1}. {t['name']}" for i, t in enumerate(topic_list)])

        prompt = f"""You are an expert educational content analyzer specializing in {subject_name} for Grade {grade_name}.

**TASK**: Analyze the following question and select the MOST appropriate topic from the provided list.

**QUESTION**:
{clean_text}

**AVAILABLE TOPICS** for {subject_name} - Grade {grade_name}:
{topic_names}

**INSTRUCTIONS**:
- Read the question carefully, including any image content
- Consider the subject ({subject_name}) and grade level ({grade_name})
- Select the topic that BEST matches the question's content
- Respond with ONLY the topic number (e.g., "3")
- Do NOT include explanations, just the number

**RESPONSE** (number only):"""

        return prompt, clean_text

    @staticmethod
    def build_lo_prompt(question_text, image_text, topic_name, subject_name, grade_name, lo_list):
        """Build comprehensive prompt for LO selection"""

        # Combine question text and OCR text
        full_question = question_text
        if image_text:
            full_question += f"\n\n[Image Content]: {image_text}"

        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', full_question)

        # Build LO list
        lo_descriptions = '\n'.join([
            f"{i+1}. [{lo['code']}] {lo['description']}"
            for i, lo in enumerate(lo_list)
        ])

        prompt = f"""You are an expert educational content analyzer specializing in {subject_name} for Grade {grade_name}.

**TASK**: Analyze the following question and select the MOST relevant learning objective(s) from the provided list.

**CONTEXT**:
- Subject: {subject_name}
- Grade: {grade_name}
- Topic: {topic_name}

**QUESTION**:
{clean_text}

**AVAILABLE LEARNING OBJECTIVES**:
{lo_descriptions}

**INSTRUCTIONS**:
- Read the question carefully, including any image content
- You may select MULTIPLE learning objectives if the question covers multiple concepts
- Select objectives that the question is specifically assessing
- Respond with ONLY the numbers separated by commas (e.g., "1,3,5")
- Do NOT include explanations, just the numbers

**RESPONSE** (numbers only):"""

        return prompt, clean_text


def call_lmstudio(prompt, logger, lmstudio_url='http://localhost:1234/v1/chat/completions'):
    """Call LMStudio with context-aware prompting"""
    try:
        logger.log_prompt('LMStudio', prompt)
        logger.log_api_call('lmstudio')

        response = requests.post(
            lmstudio_url,
            json={
                "model": "local-model",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert educational content analyzer. You analyze questions and categorize them accurately. Always respond with ONLY the requested numbers, no explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 100
            },
            timeout=60
        )

        if response.status_code == 200:
            response_data = response.json()
            response_text = response_data['choices'][0]['message']['content'].strip()
            logger.log_response('LMStudio', response_text)
            return response_text
        else:
            logger.log_error('LMStudio', f"HTTP {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.log_error('LMStudio', str(e))
        return None


def call_google_gemini(prompt, logger, api_key):
    """Call Google Gemini API"""
    try:
        logger.log_prompt('Google Gemini', prompt)
        logger.log_api_call('gemini')

        google_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"

        response = requests.post(
            google_url,
            json={
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            },
            timeout=30
        )

        if response.status_code == 200:
            response_data = response.json()
            response_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
            logger.log_response('Google Gemini', response_text)
            return response_text
        else:
            logger.log_error('Google Gemini', f"HTTP {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.log_error('Google Gemini', str(e))
        return None


def call_anthropic(prompt, logger, api_key):
    """Call Anthropic Claude API"""
    if not ANTHROPIC_AVAILABLE:
        return None

    try:
        logger.log_prompt('Anthropic Claude', prompt)
        logger.log_api_call('anthropic')

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        response_text = message.content[0].text.strip()
        logger.log_response('Anthropic Claude', response_text)
        return response_text

    except Exception as e:
        logger.log_error('Anthropic Claude', str(e))
        return None
