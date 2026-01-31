# core/ai/lo_tagger.py

import re
from .utils import (
    clean_question_text,
    call_lmstudio,
    call_gemini,
)

def suggest_los_for_question(
    *,
    question_text,
    topic,
    los_qs,
):
    """
    SINGLE source of truth for LO tagging.
    """

    los = list(los_qs.values("id", "code", "description"))
    if not los:
        return []

    clean_text = clean_question_text(question_text)

    lo_list = "\n".join(
        f"{i+1}. [{lo['code']}] {lo['description']}"
        for i, lo in enumerate(los)
    )

    prompt = f"""
Analyze the question and select the MOST relevant learning objectives.

Topic: {topic.name}

Question:
{clean_text}

Learning objectives:
{lo_list}

Respond with ONLY numbers separated by commas.
"""

    response = call_lmstudio(prompt)
    if not response:
        response = call_gemini(prompt)

    if not response:
        return []

    nums = [int(n) for n in re.findall(r"\d+", response)]
    return [
        los[n - 1]["id"]
        for n in nums
        if 1 <= n <= len(los)
    ]
