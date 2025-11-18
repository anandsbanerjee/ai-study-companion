# test_explanation.py

import os
from dotenv import load_dotenv

from study_agents.question_generator_agent import Question, QuestionSet
from study_agents.worksheet_loop import StudentAnswer, WorksheetResult
from study_agents.evaluator_agent import evaluate_worksheet, WorksheetEvaluation
from study_agents.explanation_agent import generate_explanations, ExplanationSet


def main():
    # 1. Load env and check key
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set. Check your .env file.")

    print("✅ GOOGLE_API_KEY found. Calling Evaluator + Explanation Agents on a dummy worksheet...\n")

    # 2. Build a tiny dummy worksheet
    q1 = Question(
        id=1,
        q_type="mcq",
        question_text="What is 1/2 + 1/4?",
        options=["3/4", "1/4", "2/4"],
        correct_option="3/4",
        answer=None,
        difficulty="easy",
        skill_tag="fractions-addition",
    )

    q2 = Question(
        id=2,
        q_type="short",
        question_text="Find 3/4 of 20.",
        options=None,
        correct_option=None,
        answer="15",
        difficulty="medium",
        skill_tag="fractions-of-a-quantity",
    )

    questions = [q1, q2]
    qset = QuestionSet(questions=questions)

    # Student answers: one correct, one wrong
    a1 = StudentAnswer(
        question_id=1,
        q_type="mcq",
        student_answer="1",  # option 1 ("3/4") -> correct
    )

    a2 = StudentAnswer(
        question_id=2,
        q_type="short",
        student_answer="12",  # incorrect
    )

    result = WorksheetResult(
        questions=qset.questions,
        answers=[a1, a2],
    )

    # 3. Evaluate the worksheet
    evaluation: WorksheetEvaluation = evaluate_worksheet(result)

    print("=== EVALUATION SUMMARY ===")
    print("Total questions:", evaluation.summary.total_questions)
    print("Total score:", evaluation.summary.total_score, "/", evaluation.summary.max_score)
    print("Percentage:", evaluation.summary.percentage)
    print()

    # 4. Generate explanations
    explanations: ExplanationSet = generate_explanations(result, evaluation)

    print("=== EXPLANATIONS ===")
    for expl in explanations.explanations:
        print(f"Q{expl.question_id}")
        print("  Hint:", expl.short_hint)
        print("  Explanation:", expl.explanation)
        print("-" * 80)


if __name__ == "__main__":
    main()