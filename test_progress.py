# test_progress.py

import os
from dotenv import load_dotenv

from study_agents.question_generator_agent import Question, QuestionSet
from study_agents.worksheet_loop import StudentAnswer, WorksheetResult
from study_agents.evaluator_agent import evaluate_worksheet, WorksheetEvaluation
from study_agents.progress_agent import (
    generate_progress_summary,
    ProgressProfile,
    ProgressSummary,
)


def main():
    # 1. Load env and check key
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set. Check your .env file.")

    print("✅ GOOGLE_API_KEY found. Calling Evaluator + Progress Agent on a dummy worksheet...\n")

    # 2. Dummy worksheet (same as before)
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
        student_answer="1",  # option 1 -> "3/4"
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

    # 4. Generate/update progress profile & summary
    student_id = "demo_student_1"
    grade = "Year 5"
    subject = "Maths"
    topic = "Fractions"

    profile: ProgressProfile
    progress_summary: ProgressSummary

    profile, progress_summary = generate_progress_summary(
        student_id=student_id,
        grade=grade,
        subject=subject,
        topic=topic,
        result=result,
        evaluation=evaluation,
    )

    # 5. Print numeric profile
    print("=== NUMERIC PROGRESS PROFILE ===")
    print("Student:", profile.student_id)
    print("Grade:", profile.grade, "| Subject:", profile.subject)
    print("Total sessions:", profile.total_sessions)
    print("Last topic:", profile.last_topic)
    print("Last percentage:", profile.last_percentage)
    print()

    for topic_name, tp in profile.topics.items():
        print(f"Topic: {topic_name}")
        for skill_tag, stat in tp.skills.items():
            print(
                f"  Skill: {skill_tag} -> attempts={stat.attempts}, "
                f"correct={stat.correct}, accuracy={stat.accuracy}%"
            )
        print()

    # 6. Print narrative summary
    print("=== PROGRESS SUMMARY (Narrative) ===")
    print("Summary:", progress_summary.summary_text)
    print("Strengths:", progress_summary.strengths)
    print("Weaknesses:", progress_summary.weaknesses)
    print("Recommended next topics:", progress_summary.recommended_next_topics)
    print("Motivational message:", progress_summary.motivational_message)


if __name__ == "__main__":
    main()