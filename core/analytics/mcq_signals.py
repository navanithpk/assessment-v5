from collections import Counter, defaultdict
from decimal import Decimal

def compute_mcq_signals(test):
    """
    Computes examiner-grade MCQ analytics using
    answer_text + marks_awarded ONLY.
    """

    answers = (
        test.student_answers
        .select_related("question")
        .all()
    )

    # -------------------------------
    # Question-level signals
    # -------------------------------
    question_stats = {}

    for ans in answers:
        q = ans.question

        if q.id not in question_stats:
            question_stats[q.id] = {
                "question": q,
                "total": 0,
                "correct": 0,
                "option_counts": Counter(),
            }

        question_stats[q.id]["total"] += 1
        question_stats[q.id]["option_counts"][ans.answer_text] += 1

        if ans.marks_awarded > Decimal("0"):
            question_stats[q.id]["correct"] += 1

    question_results = {}

    for qid, data in question_stats.items():
        total = data["total"]
        correct = data["correct"]

        wrong_opts = {
            opt: cnt
            for opt, cnt in data["option_counts"].items()
            if cnt and (correct < total)
        }

        dominant_wrong = None
        guessing = False

        if wrong_opts:
            opt, freq = max(wrong_opts.items(), key=lambda x: x[1])
            if freq / total >= 0.4:
                dominant_wrong = opt

            if len(wrong_opts) >= 3:
                vals = list(wrong_opts.values())
                if max(vals) - min(vals) <= 1:
                    guessing = True

        question_results[qid] = {
            "question": data["question"],
            "correct_pct": round((correct / total) * 100, 1),
            "dominant_wrong_option": dominant_wrong,
            "guessing": guessing,
        }

    # -------------------------------
    # LO-level signals
    # -------------------------------
    lo_stats = defaultdict(lambda: {
        "attempts": 0,
        "correct": 0,
        "student_scores": defaultdict(list),
    })

    for ans in answers:
        for lo in ans.question.learning_objectives.all():
            lo_stats[lo.id]["attempts"] += 1
            lo_stats[lo.id]["student_scores"][ans.student_id].append(
                ans.marks_awarded > Decimal("0")
            )
            if ans.marks_awarded > Decimal("0"):
                lo_stats[lo.id]["correct"] += 1

    lo_results = {}

    for lo_id, data in lo_stats.items():
        mean = (
            (data["correct"] / data["attempts"]) * 100
            if data["attempts"] else 0
        )

        consistency = sum(
            all(scores) for scores in data["student_scores"].values()
        ) / max(len(data["student_scores"]), 1)

        lo_results[lo_id] = {
            "mean_pct": round(mean, 1),
            "consistency_pct": round(consistency * 100, 1),
        }

    return {
        "questions": question_results,
        "learning_objectives": lo_results,
    }
