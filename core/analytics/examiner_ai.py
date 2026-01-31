import json
import requests
import os

LMSTUDIO_URL = os.environ.get(
    "LMSTUDIO_URL", "http://localhost:1234/v1/chat/completions"
)

def generate_examiner_report(schema):
    prompt = f"""
You are writing a Principal Examiner Report for a multiple-choice test.

Base all statements strictly on the data.
Do not speculate about motivation or effort.

DATA:
{json.dumps(schema, indent=2)}

Write sections:
1. Overall Performance
2. Question Analysis
3. Learning Objective Analysis
4. Misconceptions and Guessing
"""

    r = requests.post(
        LMSTUDIO_URL,
        json={
            "model": "local-model",
            "messages": [
                {"role": "system", "content": "You are an experienced examiner."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        },
        timeout=60
    )

    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]
