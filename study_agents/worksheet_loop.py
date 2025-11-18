# study_agents/worksheet_loop.py

from typing import List, Callable

from pydantic import BaseModel, Field

from study_agents.question_generator_agent import Question, QuestionSet


# ---------- Models for Student Answers & Worksheet Result ----------

class StudentAnswer(BaseModel):
    question_id: int = Field(description="ID of the question answered.")
    q_type: str = Field(description="Question type: 'mcq' or 'short'.")
    student_answer: str = Field(description="The student's raw answer as entered/selected.")


class WorksheetResult(BaseModel):
    questions: List[Question] = Field(
        description="The list of questions presented in this worksheet."
    )
    answers: List[StudentAnswer] = Field(
        description="The list of student answers, matched by question_id."
    )


# ---------- Non-interactive Worksheet Session (for testing / automation) ----------

def run_worksheet_session(
    qset: QuestionSet,
    answer_provider: Callable[[Question], str],
) -> WorksheetResult:
    """
    Non-interactive worksheet runner.

    - qset: the QuestionSet to present.
    - answer_provider: a function that, given a Question, returns a student's answer as string.

    Returns a WorksheetResult containing the original questions and the collected answers.
    """
    answers: List[StudentAnswer] = []

    for q in qset.questions:
        # Get an answer from the provided function
        ans_text = answer_provider(q)

        answers.append(
            StudentAnswer(
                question_id=q.id,
                q_type=q.q_type,
                student_answer=ans_text,
            )
        )

    return WorksheetResult(
        questions=qset.questions,
        answers=answers,
    )


# ---------- Interactive Worksheet Session (optional, for CLI use) ----------

def run_worksheet_session_interactive(qset: QuestionSet) -> WorksheetResult:
    """
    Simple command-line interactive version of the worksheet.
    This is mainly for local/manual testing, not for Streamlit.
    """
    print("Starting interactive worksheet session...")
    answers: List[StudentAnswer] = []

    for q in qset.questions:
        print("-" * 60)
        print(f"Q{q.id} ({q.q_type.upper()} - {q.difficulty}, skill: {q.skill_tag})")
        print(q.question_text)

        if q.q_type == "mcq" and q.options:
            for i, opt in enumerate(q.options, start=1):
                print(f"  {i}. {opt}")
            ans_text = input("Your choice (e.g. 1, 2, 3): ").strip()
        else:
            ans_text = input("Your answer: ").strip()

        answers.append(
            StudentAnswer(
                question_id=q.id,
                q_type=q.q_type,
                student_answer=ans_text,
            )
        )

    print("\nWorksheet complete!")
    return WorksheetResult(
        questions=qset.questions,
        answers=answers,
    )