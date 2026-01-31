# core/ai/utils.py

import re
import os
import requests

LMSTUDIO_URL = os.environ.get(
    "LMSTUDIO_URL", "http://localhost:1234/v1/chat/completions"
)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")


def clean_question_text(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def call_lmstudio(prompt):
    try:
        r = requests.post(
            LMSTUDIO_URL,
            json={
                "model": "local-model",
                "messages": [
                    {"role": "system", "content": "Respond ONLY with numbers."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 120,
            },
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def call_gemini(prompt):
    if not GOOGLE_API_KEY:
        return None
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=25,
        )
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        pass
    return None
