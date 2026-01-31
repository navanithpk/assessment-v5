# core/ai/topic_tagger.py

import re
from .utils import (
    clean_question_text,
    call_lmstudio,
    call_gemini,
)

def suggest_topic_for_question(
    *,
    question_text,
    grade,
    subject,
    topics_qs,
):
    """
    SINGLE source of truth for topic tagging.
    Used by:
    - edit question AI button
    - bulk tagging
    - background tagging
    """

    topics = list(topics_qs.values("id", "name"))
    if not topics:
        return None

    clean_text = clean_question_text(question_text)

    topic_list = "\n".join(
        f"{i+1}. {t['name']}" for i, t in enumerate(topics)
    )

    prompt = f"""
Analyze the question below and choose the MOST appropriate topic.

Grade: {grade.name}
Subject: {subject.name}

Question:
{clean_text}

Available topics:
{topic_list}

Respond with ONLY the topic number.
"""

    # ---- LMStudio FIRST (matches edit button) ----
    response = call_lmstudio(prompt)
    if not response:
        response = call_gemini(prompt)

    if not response:
        return None

    try:
        n = int(re.search(r"\d+", response).group())
        if 1 <= n <= len(topics):
            return topics[n - 1]["id"]
    except Exception:
        pass

    return None
