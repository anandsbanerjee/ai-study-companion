# services/study_flow.py

from typing import Dict, Any

from study_agents.planner_agent import get_study_plan, StudyPlan
from study_agents.question_generator_agent import (
    generate_questions,
    QuestionSet,
    Question,
)
from study_agents.worksheet_loop import (
    StudentAnswer,
    WorksheetResult,
)
from study_agents.evaluator_agent import evaluate_worksheet, WorksheetEvaluation
from study_agents.explanation_agent import (
    generate_explanations,
    ExplanationSet,
)
from study_agents.progress_agent import (
    generate_progress_summary,
    ProgressProfile,
    ProgressSummary,
)
from study_agents.report_agent import (
    generate_report,
    Report,
)


# ---------- Helper: Build WorksheetResult from UI answers ----------

def build_worksheet_result_from_answers(
    qset: QuestionSet,
    answers_by_qid: Dict[int, str],
) -> WorksheetResult:
    """
    Convert a QuestionSet + a dict of {question_id: answer_text}
    into a WorksheetResult that can be sent to Evaluator, Explanation, Progress.
    """
    answers = []

    for q in qset.questions:
        ans_text = answers_by_qid.get(q.id, "").strip()
        answers.append(
            StudentAnswer(
                question_id=q.id,
                q_type=q.q_type,
                student_answer=ans_text,
            )
        )

    result = WorksheetResult(
        questions=qset.questions,
        answers=answers,
    )
    return result


# ---------- Stage 1: Plan + Generate Questions ----------

def run_planning_and_generation(
    grade: str,
    subject: str,
    topic: str,
    time_minutes: int,
    difficulty: str,
) -> Dict[str, Any]:
    """
    Orchestrates:
      1) Planner Agent
      2) Question Generator Agent

    Returns:
      {
        "plan": StudyPlan,
        "qset": QuestionSet,
      }
    """
    plan: StudyPlan = get_study_plan(
        grade=grade,
        subject=subject,
        topic=topic,
        time_minutes=time_minutes,
        difficulty=difficulty,
    )

    qset: QuestionSet = generate_questions(
        plan=plan,
        grade=grade,
        subject=subject,
        topic=topic,
    )

    return {
        "plan": plan,
        "qset": qset,
    }


# ---------- Stage 2: Full analysis after student answers ----------

def run_full_analysis(
    student_id: str,
    grade: str,
    subject: str,
    topic: str,
    qset: QuestionSet,
    answers_by_qid: Dict[int, str],
) -> Dict[str, Any]:
    """
    Orchestrates:
      1) Build WorksheetResult
      2) Evaluator Agent
      3) Explanation Agent
      4) Progress Agent (numeric + narrative)
      5) Report Agent (student view by default)

    Returns:
      {
        "worksheet_result": WorksheetResult,
        "evaluation": WorksheetEvaluation,
        "explanations": ExplanationSet,
        "profile": ProgressProfile,
        "progress_summary": ProgressSummary,
        "report_student": Report,
        "report_parent": Report,
        "report_teacher": Report,
      }
    """

    # 1) Build WorksheetResult from answers
    result: WorksheetResult = build_worksheet_result_from_answers(qset, answers_by_qid)

    # 2) Evaluate answers
    evaluation: WorksheetEvaluation = evaluate_worksheet(result)

    # 3) Generate explanations
    explanations: ExplanationSet = generate_explanations(result, evaluation)

    # 4) Update progress + narrative summary
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

    # 5) Generate three reports for different audiences
    report_student: Report = generate_report(
        profile=profile,
        progress_summary=progress_summary,
        audience="student",
    )
    report_parent: Report = generate_report(
        profile=profile,
        progress_summary=progress_summary,
        audience="parent",
    )
    report_teacher: Report = generate_report(
        profile=profile,
        progress_summary=progress_summary,
        audience="teacher",
    )

    return {
        "worksheet_result": result,
        "evaluation": evaluation,
        "explanations": explanations,
        "profile": profile,
        "progress_summary": progress_summary,
        "report_student": report_student,
        "report_parent": report_parent,
        "report_teacher": report_teacher,
    }