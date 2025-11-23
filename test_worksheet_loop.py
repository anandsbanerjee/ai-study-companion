# test_worksheet_loop.py

import os
from dotenv import load_dotenv

from study_agents.planner_agent import get_study_plan
from study_agents.question_generator_agent import generate_questions, QuestionSet, Question
from study_agents.worksheet_loop import run_worksheet_session, WorksheetResult, StudentAnswer


def main():
    # 1. Load env
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set. Check .env file.")

    print("GOOGLE_API_KEY found. Running Planner + Question Generator + Worksheet Loop...\n")

    # 2. Plan session
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

    # 3. Generate questions
    qset: QuestionSet = generate_questions(
        plan=plan,
        grade="Year 5",
        subject="Maths",
        topic="Fractions",
    )
    
    print("=== GENERATED QUESTIONS ===")
    print(f"Total questions: {len(qset.questions)}")
    print()
    print("LOOP 2")
    for q in qset.questions:
        print(f"Q{q.id} [{q.q_type.upper()} | {q.difficulty} | {q.skill_tag}]")
        print(q.question_text)
        print("-" * 40)
    print()
    print("LOOP 3")
    # 4. Define a dummy answer provider (non-interactive)
    def dummy_answer_provider(q: Question) -> str:
        # For MCQ, pretend student always picks option 1
        if q.q_type == "mcq":
            return "1"
        # For short, pretend student says "I don't know"
        return "I don't know"

    # 5. Run worksheet session (non-interactive)
    result: WorksheetResult = run_worksheet_session(qset, answer_provider=dummy_answer_provider)

    print("=== WORKSHEET RESULT (Student Answers) ===")
    for ans in result.answers:
        print(f"Q{ans.question_id} ({ans.q_type}) -> {ans.student_answer}")


if __name__ == "__main__":
    main()