"""
Background AI Tagging System
Handles async tagging operations that continue even when user navigates away
"""
import os
import json
import threading
import time
from datetime import datetime
from django.db.models import Q
from .models import Question, Topic, LearningObjective
from .ai_tagging_improved import (
    AITaggingLogger, ImageTextExtractor, ContextAwarePromptBuilder,
    call_lmstudio, call_google_gemini, call_anthropic
)

# In-memory task storage (in production, use Redis or database)
BACKGROUND_TASKS = {}


class BackgroundTaggingTask:
    """Manages a background tagging task"""

    def __init__(self, task_id, mode, questions):
        self.task_id = task_id
        self.mode = mode  # 'topics', 'los', or 'both'
        self.questions = list(questions)
        self.total = len(questions)
        self.processed = 0
        self.topics_tagged = 0
        self.los_tagged = 0
        self.errors = 0
        self.status = 'running'  # 'running', 'completed', 'failed'
        self.current_question = None
        self.logger = AITaggingLogger()
        self.thread = None

    def to_dict(self):
        """Convert task status to dictionary"""
        return {
            'task_id': self.task_id,
            'mode': self.mode,
            'total': self.total,
            'processed': self.processed,
            'topics_tagged': self.topics_tagged,
            'los_tagged': self.los_tagged,
            'errors': self.errors,
            'status': self.status,
            'current_question': self.current_question,
            'percent': int((self.processed / self.total * 100)) if self.total > 0 else 0
        }

    def start(self):
        """Start the background task"""
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        """Main tagging loop"""
        try:
            self.logger.log_start(self.total)

            for question in self.questions:
                try:
                    self.current_question = f"Q{question.id}: {question.question_text[:50]}..."
                    self.logger.log_question_start(question.id, question.question_text[:200])

                    if self.mode in ['topics', 'both']:
                        self._tag_topic(question)

                    if self.mode in ['los', 'both']:
                        self._tag_learning_objectives(question)

                    self.processed += 1
                    time.sleep(0.3)  # Rate limiting

                except Exception as e:
                    self.errors += 1
                    self.logger.log_error(question.id, str(e))
                    self.processed += 1

            self.status = 'completed'
            self.logger.log_summary()

        except Exception as e:
            self.status = 'failed'
            self.logger.log_error(0, f"Fatal error: {str(e)}")

    def _tag_topic(self, question):
        """Tag topic for a single question"""
        # Skip if already has topic
        if question.topic_id:
            self.logger.log_info(f"Question {question.id} already has topic, skipping")
            return

        # Need subject and grade
        if not question.subject_id or not question.grade_id:
            self.logger.log_warning(question.id, "Missing subject or grade")
            return

        # Get topics for this subject/grade
        topics = Topic.objects.filter(
            subject_id=question.subject_id,
            grade_id=question.grade_id
        ).values('id', 'name')
        topic_list = [{'id': t['id'], 'name': t['name']} for t in topics]

        if not topic_list:
            self.logger.log_warning(question.id, "No topics available")
            return

        # Extract OCR text from images
        image_text = ImageTextExtractor.extract_from_html(question.question_text)
        if image_text:
            self.logger.log_ocr_extraction(question.id, image_text)

        # Build context-aware prompt
        subject_name = question.subject.name
        grade_name = question.grade.name
        prompt, clean_text = ContextAwarePromptBuilder.build_topic_prompt(
            question.question_text, image_text, subject_name, grade_name, topic_list
        )

        # Try AI services in order: LMStudio → Gemini → Anthropic
        suggested_topic_id = None
        service_used = None

        # Try LMStudio
        lmstudio_url = os.environ.get('LMSTUDIO_URL', 'http://localhost:1234/v1/chat/completions')
        response_text = call_lmstudio(prompt, self.logger, lmstudio_url)
        if response_text:
            try:
                import re
                topic_number = int(re.search(r'\d+', response_text).group())
                if 0 < topic_number <= len(topic_list):
                    suggested_topic_id = topic_list[topic_number - 1]['id']
                    service_used = 'LMStudio'
            except:
                pass

        # Try Gemini
        if not suggested_topic_id:
            gemini_key = os.environ.get('GOOGLE_API_KEY', 'AIzaSyCzbW72vCJ3YfxBEkQNb8HZkBTXD3iL6QE')
            response_text = call_google_gemini(prompt, self.logger, gemini_key)
            if response_text:
                try:
                    import re
                    topic_number = int(re.search(r'\d+', response_text).group())
                    if 0 < topic_number <= len(topic_list):
                        suggested_topic_id = topic_list[topic_number - 1]['id']
                        service_used = 'Gemini'
                except:
                    pass

        # Try Anthropic
        if not suggested_topic_id:
            anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
            response_text = call_anthropic(prompt, self.logger, anthropic_key)
            if response_text:
                try:
                    import re
                    topic_number = int(re.search(r'\d+', response_text).group())
                    if 0 < topic_number <= len(topic_list):
                        suggested_topic_id = topic_list[topic_number - 1]['id']
                        service_used = 'Anthropic'
                except:
                    pass

        # Save the topic
        if suggested_topic_id:
            question.topic_id = suggested_topic_id
            question.save()
            self.topics_tagged += 1

            topic_name = next((t['name'] for t in topic_list if t['id'] == suggested_topic_id), 'Unknown')
            self.logger.log_topic_tagged(question.id, topic_name, service_used)
        else:
            self.logger.log_warning(question.id, "No AI service could suggest topic")

    def _tag_learning_objectives(self, question):
        """Tag learning objectives for a single question"""
        # Need a topic first
        if not question.topic_id:
            self.logger.log_warning(question.id, "No topic, skipping LO tagging")
            return

        # Skip if already has LOs
        if question.learning_objectives.count() > 0:
            self.logger.log_info(f"Question {question.id} already has LOs, skipping")
            return

        # Get LOs for this topic
        los = LearningObjective.objects.filter(topic_id=question.topic_id).values('id', 'code', 'description')
        lo_list = [{'id': lo['id'], 'code': lo['code'], 'description': lo['description']} for lo in los]

        if not lo_list:
            self.logger.log_warning(question.id, "No LOs available for this topic")
            return

        # Extract OCR text
        image_text = ImageTextExtractor.extract_from_html(question.question_text)

        # Build prompt
        subject_name = question.subject.name
        grade_name = question.grade.name
        topic_name = question.topic.name
        prompt, clean_text = ContextAwarePromptBuilder.build_lo_prompt(
            question.question_text, image_text, subject_name, grade_name, topic_name, lo_list
        )

        # Try AI services
        suggested_los = []
        service_used = None

        # Try LMStudio
        lmstudio_url = os.environ.get('LMSTUDIO_URL', 'http://localhost:1234/v1/chat/completions')
        response_text = call_lmstudio(prompt, self.logger, lmstudio_url)
        if response_text:
            try:
                import re
                lo_numbers = [int(n.strip()) for n in re.findall(r'\d+', response_text)]
                suggested_los = [lo_list[n - 1] for n in lo_numbers if 0 < n <= len(lo_list)]
                if suggested_los:
                    service_used = 'LMStudio'
            except:
                pass

        # Try Gemini
        if not suggested_los:
            gemini_key = os.environ.get('GOOGLE_API_KEY', 'AIzaSyCzbW72vCJ3YfxBEkQNb8HZkBTXD3iL6QE')
            response_text = call_google_gemini(prompt, self.logger, gemini_key)
            if response_text:
                try:
                    import re
                    lo_numbers = [int(n.strip()) for n in re.findall(r'\d+', response_text)]
                    suggested_los = [lo_list[n - 1] for n in lo_numbers if 0 < n <= len(lo_list)]
                    if suggested_los:
                        service_used = 'Gemini'
                except:
                    pass

        # Try Anthropic
        if not suggested_los:
            anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
            response_text = call_anthropic(prompt, self.logger, anthropic_key)
            if response_text:
                try:
                    import re
                    lo_numbers = [int(n.strip()) for n in re.findall(r'\d+', response_text)]
                    suggested_los = [lo_list[n - 1] for n in lo_numbers if 0 < n <= len(lo_list)]
                    if suggested_los:
                        service_used = 'Anthropic'
                except:
                    pass

        # Save the LOs
        if suggested_los:
            lo_ids = [lo['id'] for lo in suggested_los]
            question.learning_objectives.set(lo_ids)
            self.los_tagged += len(lo_ids)

            lo_codes = [lo['code'] for lo in suggested_los]
            self.logger.log_lo_tagged(question.id, lo_codes, service_used)
        else:
            self.logger.log_warning(question.id, "No AI service could suggest LOs")


def create_tagging_task(mode, questions):
    """Create and start a new background tagging task"""
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(BACKGROUND_TASKS)}"

    task = BackgroundTaggingTask(task_id, mode, questions)
    BACKGROUND_TASKS[task_id] = task
    task.start()

    return task


def get_task_status(task_id):
    """Get the status of a background task"""
    task = BACKGROUND_TASKS.get(task_id)
    if task:
        return task.to_dict()
    return None


def cleanup_old_tasks():
    """Remove completed tasks older than 1 hour"""
    current_time = time.time()
    to_remove = []

    for task_id, task in BACKGROUND_TASKS.items():
        if task.status in ['completed', 'failed']:
            # Check if task is old (simplified - would use task creation time in production)
            to_remove.append(task_id)

    for task_id in to_remove[:5]:  # Keep last 5 completed tasks
        if len(BACKGROUND_TASKS) > 10:
            BACKGROUND_TASKS.pop(task_id, None)
