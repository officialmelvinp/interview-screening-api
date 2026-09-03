def generate_feedback(answer_text: str):
    length = len(answer_text)
    if length > 50:
        score = min(7 + length / 100, 10)
    else:
        score = 3.0
    score = round(score, 2)

    if score >= 8:
        feedback = "Good detail and structure"
    elif score >= 6:
        feedback = "Adequate answer"
    else:
        feedback = "Too brief or lacking detail"

    return score, feedback