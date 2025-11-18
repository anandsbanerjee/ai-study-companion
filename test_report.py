# test_report.py

import os
from dotenv import load_dotenv

from study_agents.progress_agent import ProgressProfile, TopicProgress, SkillStat, ProgressSummary
from study_agents.report_agent import generate_report, Report


def main():
    # 1. Load env and check API key
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set. Check your .env file.")

    print("✅ GOOGLE_API_KEY found. Calling Report Agent on dummy progress data...\n")

    # 2. Build a dummy numeric ProgressProfile
    fractions_topic = TopicProgress(
        skills={
            "fractions-addition": SkillStat(attempts=10, correct=9, accuracy=90.0),
            "fractions-of-a-quantity": SkillStat(attempts=8, correct=4, accuracy=50.0),
        }
    )

    profile = ProgressProfile(
        student_id="demo_student_1",
        grade="Year 5",
        subject="Maths",
        topics={"Fractions": fractions_topic},
        total_sessions=3,
        last_topic="Fractions",
        last_percentage=75.0,
    )

    # 3. Build a dummy narrative ProgressSummary
    progress_summary = ProgressSummary(
        summary_text=(
            "The student is developing strong understanding of basic fraction addition, "
            "but needs more practice finding fractions of quantities."
        ),
        strengths=["fractions-addition"],
        weaknesses=["fractions-of-a-quantity"],
        recommended_next_topics=["fractions-of-a-quantity", "fractions-comparison"],
        motivational_message="You're doing well—keep practicing fractions of a quantity and you'll improve quickly!",
    )

    # 4. Generate reports for each audience type (student, parent, teacher)
    for audience in ("student", "parent", "teacher"):
        print(f"=== REPORT for {audience.upper()} ===")
        report: Report = generate_report(profile, progress_summary, audience=audience)
        print("Audience:", report.audience)
        print("Headline:", report.headline)
        print("Strengths:", report.strengths_sentence)
        print("Weaknesses:", report.weaknesses_sentence)
        print("Next steps:", report.next_steps_sentence)
        print("Bullet points:")
        for bp in report.bullet_points:
            print(" -", bp)
        print("-" * 80)


if __name__ == "__main__":
    main()