def build_examiner_schema(test, signals):
    question_analysis = []

    for qid, qdata in signals["questions"].items():
        pct = qdata["correct_pct"]

        if pct >= 75:
            difficulty = "generally well answered"
        elif pct >= 40:
            difficulty = "moderately challenging"
        else:
            difficulty = "found challenging by many candidates"

        question_analysis.append({
            "question": qid,
            "difficulty": difficulty,
            "guessing": qdata["guessing"],
            "dominant_wrong_option": qdata["dominant_wrong_option"],
        })

    lo_analysis = []

    for lo_id, lodata in signals["learning_objectives"].items():
        mean = lodata["mean_pct"]

        if mean >= 70:
            summary = "strong understanding"
        elif mean >= 40:
            summary = "inconsistent understanding"
        else:
            summary = "weak understanding"

        lo_analysis.append({
            "learning_objective": lo_id,
            "mean_pct": mean,
            "consistency": lodata["consistency_pct"],
            "summary": summary,
        })

    return {
        "test_title": test.title,
        "question_analysis": question_analysis,
        "learning_objective_analysis": lo_analysis,
    }
