# test_question_generator.py

import os
from dotenv import load_dotenv

from study_agents.planner_agent import get_study_plan
from study_agents.question_generator_agent import generate_questions, QuestionSet, Question


def main():
    # 1. Load environment variables
    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set. Check your .env file.")

    print("✅ GOOGLE_API_KEY found. Calling Planner + Question Generator...\n")

    # 2. First, get a study plan
    plan = get_study_plan(
        grade="Year 5",
        subject="Maths",
        topic="Fractions",
        time_minutes=20,
        difficulty="mixed",
    )

    print("=== STUDY PLAN ===")
    print(plan)
    print()

    # 3. Generate questions using the plan
    qset: QuestionSet = generate_questions(
        plan=plan,
        grade="Year 5",
        subject="Maths",
        topic="Fractions",
    )

    print("=== GENERATED QUESTIONS ===")
    print(f"Total questions: {len(qset.questions)}\n")

    for q in qset.questions:
        print(f"Q{q.id} [{q.q_type.upper()} | {q.difficulty} | {q.skill_tag}]")
        print(q.question_text)
        if q.q_type == "mcq" and q.options:
            print("Options:")
            for i, opt in enumerate(q.options, start=1):
                print(f"  {i}. {opt}")
            print("Correct option:", q.correct_option)
        elif q.q_type == "short":
            print("Correct answer:", q.answer)
        print("-" * 80)


if __name__ == "__main__":
    main()