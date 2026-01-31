from django.http import JsonResponse
from django.db.models import Count
from core.models import StudentAnswer, Question

def question_analytics(request, test_id):
    q_ids = request.GET.getlist("questions[]")

    answers = StudentAnswer.objects.filter(
        test_id=test_id,
        question_id__in=q_ids if q_ids else None
    ).select_related("question")

    data = {}

    for q in Question.objects.filter(id__in=answers.values("question_id")):
        q_ans = answers.filter(question=q)

        total = q_ans.count()
        correct = q_ans.filter(marks_awarded__gt=0).count()

        distractors = (
            q_ans.values("answer_text")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        data[q.id] = {
            "question": q.text[:120],
            "correct_pct": round(correct / total * 100, 2) if total else 0,
            "distractors": list(distractors),
        }

    return JsonResponse(data)

from core.models import LearningObjective

def lo_mastery_heatmap(request, test_id):
    answers = StudentAnswer.objects.filter(test_id=test_id)

    heatmap = {}

    for lo in LearningObjective.objects.all():
        lo_answers = answers.filter(question__learning_objectives=lo)

        if not lo_answers.exists():
            continue

        mastery = (
            lo_answers.filter(marks_awarded__gt=0).count()
            / lo_answers.count()
        ) * 100

        heatmap[lo.code] = round(mastery, 2)

    return JsonResponse(heatmap)


def risk_prediction(request, test_id):
    answers = StudentAnswer.objects.filter(test_id=test_id)

    risk = {}

    for student_id in answers.values_list("student_id", flat=True).distinct():
        s_ans = answers.filter(student_id=student_id)
        pct = (
            s_ans.filter(marks_awarded__gt=0).count()
            / s_ans.count()
        ) * 100

        risk_level = (
            "high" if pct < 40 else
            "medium" if pct < 60 else
            "low"
        )

        risk[student_id] = {
            "percentage": round(pct, 2),
            "risk": risk_level
        }

    return JsonResponse(risk)

import requests

def lmstudio_summary(request, test_id):
    stats = request.GET.get("stats")

    prompt = f"""
You are an educational examiner.

Given the following analytics summary for a test:
{stats}

Write:
- strengths of the cohort
- common misconceptions
- risk areas
- recommendations for teaching

Do not hallucinate. Base conclusions strictly on data.
"""

    response = requests.post(
        "http://localhost:1234/v1/chat/completions",
        json={
            "model": "local-model",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 300
        }
    )

    text = response.json()["choices"][0]["message"]["content"]
    return JsonResponse({"summary": text})
