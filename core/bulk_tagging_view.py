"""
Improved Bulk AI Tagging View with OCR and Context-Aware Prompting
"""
import os
import re
import json
import time
from django.http import StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Question, Topic, LearningObjective
from django.contrib.admin.views.decorators import staff_member_required
from .ai_tagging_improved import (
    AITaggingLogger, ImageTextExtractor, ContextAwarePromptBuilder,
    call_lmstudio, call_google_gemini, call_anthropic
)


@login_required
@staff_member_required
def bulk_ai_tag_questions_improved(request):
    """
    Improved bulk AI tagging with:
    - OCR text extraction from images
    - Context-aware prompting (subject, grade, topic context)
    - Comprehensive logging
    - LMStudio prioritization
    """

    # Initialize logger
    tag_logger = AITaggingLogger()

    # API Keys
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    gemini_key = os.environ.get('GOOGLE_API_KEY', 'AIzaSyCzbW72vCJ3YfxBEkQNb8HZkBTXD3iL6QE')
    lmstudio_url = os.environ.get('LMSTUDIO_URL', 'http://localhost:1234/v1/chat/completions')

    def event_stream():
        try:
            # Get all untagged questions
            untagged_questions = Question.objects.filter(
                Q(topic__isnull=True) | Q(learning_objectives__isnull=True)
            ).distinct().select_related('subject', 'grade', 'topic')

            total = untagged_questions.count()
            tag_logger.log_start(total)

            if total == 0:
                yield f'data: {json.dumps({"complete": True, "total": 0, "log_file": tag_logger.get_log_path()})}\n\n'
                return

            processed = 0

            for question in untagged_questions:
                try:
                    tag_logger.log_question_start(question.id, question.question_text or "")

                    # Skip if both topic and LOs are already set
                    has_topic = question.topic is not None
                    has_los = question.learning_objectives.count() > 0

                    if has_topic and has_los:
                        tag_logger.log_skip(question.id, "Already fully tagged")
                        processed += 1
                        tag_logger.stats['processed'] = processed
                        yield f'data: {json.dumps({"progress": processed, "total": total})}\n\n'
                        continue

                    # Check if question has required metadata
                    if not question.subject or not question.grade:
                        tag_logger.log_skip(question.id, "Missing subject or grade")
                        processed += 1
                        tag_logger.stats['processed'] = processed
                        yield f'data: {json.dumps({"progress": processed, "total": total})}\n\n'
                        continue

                    # Extract text from images using OCR
                    image_text = ""
                    if question.question_text and '<img' in question.question_text:
                        image_text = ImageTextExtractor.extract_from_html(question.question_text)
                        if image_text:
                            tag_logger.log_ocr_extraction(question.id, image_text)

                    # ===== TAG TOPIC =====
                    if not has_topic:
                        topics = Topic.objects.filter(
                            subject=question.subject,
                            grade=question.grade
                        ).values('id', 'name')

                        topic_list = [{'id': t['id'], 'name': t['name']} for t in topics]

                        if not topic_list:
                            tag_logger.log_skip(question.id, f"No topics for {question.subject.name} - {question.grade.name}")
                            processed += 1
                            tag_logger.stats['processed'] = processed
                            yield f'data: {json.dumps({"progress": processed, "total": total})}\n\n'
                            continue

                        # Build context-aware prompt
                        prompt, clean_text = ContextAwarePromptBuilder.build_topic_prompt(
                            question.question_text or "",
                            image_text,
                            question.subject.name,
                            question.grade.name,
                            topic_list
                        )

                        suggested_topic_id = None
                        used_service = None

                        # Try LMStudio FIRST (as requested)
                        response_text = call_lmstudio(prompt, tag_logger, lmstudio_url)
                        if response_text:
                            try:
                                topic_number = int(re.search(r'\d+', response_text).group())
                                if 0 < topic_number <= len(topic_list):
                                    suggested_topic_id = topic_list[topic_number - 1]['id']
                                    used_service = 'LMStudio'
                            except:
                                tag_logger.log_error(question.id, "Failed to parse LMStudio response")

                        # Fallback to Google Gemini
                        if not suggested_topic_id and gemini_key:
                            response_text = call_google_gemini(prompt, tag_logger, gemini_key)
                            if response_text:
                                try:
                                    topic_number = int(re.search(r'\d+', response_text).group())
                                    if 0 < topic_number <= len(topic_list):
                                        suggested_topic_id = topic_list[topic_number - 1]['id']
                                        used_service = 'Google Gemini'
                                except:
                                    tag_logger.log_error(question.id, "Failed to parse Gemini response")

                        # Fallback to Anthropic
                        if not suggested_topic_id and anthropic_key:
                            response_text = call_anthropic(prompt, tag_logger, anthropic_key)
                            if response_text:
                                try:
                                    topic_number = int(re.search(r'\d+', response_text).group())
                                    if 0 < topic_number <= len(topic_list):
                                        suggested_topic_id = topic_list[topic_number - 1]['id']
                                        used_service = 'Anthropic Claude'
                                except:
                                    tag_logger.log_error(question.id, "Failed to parse Anthropic response")

                        # Save topic
                        if suggested_topic_id:
                            question.topic_id = suggested_topic_id
                            question.save()
                            topic_name = next(t['name'] for t in topic_list if t['id'] == suggested_topic_id)
                            tag_logger.log_topic_tagged(question.id, topic_name, used_service)
                        else:
                            tag_logger.log_error(question.id, "All AI services failed to suggest topic")

                    # ===== TAG LEARNING OBJECTIVES =====
                    if question.topic and question.learning_objectives.count() == 0:
                        los = LearningObjective.objects.filter(
                            topic=question.topic
                        ).values('id', 'code', 'description')

                        lo_list = [{'id': lo['id'], 'code': lo['code'], 'description': lo['description']} for lo in los]

                        if not lo_list:
                            tag_logger.log_skip(question.id, f"No LOs for topic {question.topic.name}")
                            processed += 1
                            tag_logger.stats['processed'] = processed
                            yield f'data: {json.dumps({"progress": processed, "total": total})}\n\n'
                            continue

                        # Build context-aware prompt
                        prompt, clean_text = ContextAwarePromptBuilder.build_lo_prompt(
                            question.question_text or "",
                            image_text,
                            question.topic.name,
                            question.subject.name,
                            question.grade.name,
                            lo_list
                        )

                        suggested_los = []
                        used_service = None

                        # Try LMStudio FIRST
                        response_text = call_lmstudio(prompt, tag_logger, lmstudio_url)
                        if response_text:
                            try:
                                lo_numbers = [int(n.strip()) for n in re.findall(r'\d+', response_text)]
                                suggested_los = [lo_list[n - 1] for n in lo_numbers if 0 < n <= len(lo_list)]
                                if suggested_los:
                                    used_service = 'LMStudio'
                            except:
                                tag_logger.log_error(question.id, "Failed to parse LMStudio LO response")

                        # Fallback to Google Gemini
                        if not suggested_los and gemini_key:
                            response_text = call_google_gemini(prompt, tag_logger, gemini_key)
                            if response_text:
                                try:
                                    lo_numbers = [int(n.strip()) for n in re.findall(r'\d+', response_text)]
                                    suggested_los = [lo_list[n - 1] for n in lo_numbers if 0 < n <= len(lo_list)]
                                    if suggested_los:
                                        used_service = 'Google Gemini'
                                except:
                                    tag_logger.log_error(question.id, "Failed to parse Gemini LO response")

                        # Fallback to Anthropic
                        if not suggested_los and anthropic_key:
                            response_text = call_anthropic(prompt, tag_logger, anthropic_key)
                            if response_text:
                                try:
                                    lo_numbers = [int(n.strip()) for n in re.findall(r'\d+', response_text)]
                                    suggested_los = [lo_list[n - 1] for n in lo_numbers if 0 < n <= len(lo_list)]
                                    if suggested_los:
                                        used_service = 'Anthropic Claude'
                                except:
                                    tag_logger.log_error(question.id, "Failed to parse Anthropic LO response")

                        # Save LOs
                        if suggested_los:
                            lo_codes = []
                            for lo in suggested_los:
                                question.learning_objectives.add(lo['id'])
                                lo_codes.append(lo['code'])
                            tag_logger.log_lo_tagged(question.id, lo_codes, used_service)
                        else:
                            tag_logger.log_error(question.id, "All AI services failed to suggest LOs")

                    processed += 1
                    tag_logger.stats['processed'] = processed
                    yield f'data: {json.dumps({"progress": processed, "total": total})}\n\n'

                    # Small delay to avoid rate limiting
                    time.sleep(0.3)

                except Exception as e:
                    tag_logger.log_error(question.id, str(e))
                    processed += 1
                    tag_logger.stats['processed'] = processed
                    yield f'data: {json.dumps({"progress": processed, "total": total, "error": str(e)})}\n\n'

            # Complete
            tag_logger.log_complete()
            yield f'data: {json.dumps({"complete": True, "total": total, "stats": tag_logger.stats, "log_file": tag_logger.get_log_path()})}\n\n'

        except Exception as e:
            tag_logger.log_error('SYSTEM', str(e))
            yield f'data: {json.dumps({"error": str(e), "log_file": tag_logger.get_log_path()})}\n\n'

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
