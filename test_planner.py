# test_planner.py

import os
#from dotenv import load_dotenv
from dotenv.main import load_dotenv

from study_agents.planner_agent import get_study_plan

def main():
    # 1. Load environment variables from .env
    load_dotenv()

    # Quick check that the API key is visible
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set. Check .env file.")

    print("GOOGLE_API_KEY found. Calling Planner Agent...\n")

    # 2. Call the planner
    plan = get_study_plan(
        grade="Year 5",
        subject="Maths",
        topic="Fractions",
        time_minutes=20,
        difficulty="mixed",
    )

    # 3. Print the result nicely
    print("=== STUDY PLAN RESULT ===")
    print(plan)
    print()
    print("Total questions:", plan.total_questions)
    print("MCQ:", plan.mcq_count, "Short:", plan.short_count)
    print("Difficulty distribution:", plan.difficulty_distribution)
    print("Estimated time (mins):", plan.estimated_time_minutes)


if __name__ == "__main__":
    main()