# study_agents/evaluator_agent.py

import json
from typing import List, Literal

from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.genai import types

from study_agents.planner_agent import (
    APP_NAME,
    USER_ID,
    SESSION_ID,
    extract_json_from_text,
    session_service as shared_session_service,
)
from study_agents.worksheet_loop import WorksheetResult
from study_agents.question_generator_agent import Question


# ---------- Evaluation Models ----------

class QuestionEvaluation(BaseModel):
    question_id: int = Field(description="ID of the question.")
    q_type: str = Field(description="Question type: 'mcq' or 'short'.")
    student_answer: str = Field(description="Student's answer as entered.")
    correct_answer: str = Field(description="The correct answer in a concise form.")
    score: float = Field(
        description="Score for this question, typically 0.0, 0.5, or 1.0."
    )
    max_score: float = Field(
        description="Maximum possible score for this question, usually 1.0."
    )
    mistake_type: Literal[
        "correct",
        "minor-error",
        "incorrect",
        "calculation-error",
        "conceptual-error",
        "guess",
        "blank",
        "other",
    ] = Field(
        description="Short label describing the type of mistake, or 'correct'."
    )
    feedback: str = Field(
        description="Short feedback explaining why the answer is correct or incorrect, in student-friendly language."
    )


class EvaluationSummary(BaseModel):
    total_questions: int = Field(description="Total number of questions.")
    total_score: float = Field(description="Total score across all questions.")
    max_score: float = Field(description="Total maximum score.")
    percentage: float = Field(description="Percentage score (0–100).")


class WorksheetEvaluation(BaseModel):
    evaluations: List[QuestionEvaluation] = Field(
        description="Per-question evaluation results."
    )
    summary: EvaluationSummary = Field(
        description="Overall summary of the worksheet performance."
    )


# ---------- Evaluator Agent Instruction ----------

EVALUATOR_INSTRUCTION = """
You are an evaluation agent for a Maths practice worksheet.

You are given a worksheet_result object with:
- questions: each question has
  - id
  - q_type: "mcq" or "short"
  - question_text
  - options (for MCQ)
  - correct_option (for MCQ, the correct option text or index)
  - answer (for short questions: the correct answer)
  - difficulty
  - skill_tag
- answers: each answer has
  - question_id
  - q_type
  - student_answer (the student's response, e.g. "1", "3/4", "I don't know")

Your tasks:
1. For each question, compare the student's answer to the correct answer.
2. Decide a score:
   - For MCQ:
     - 1.0 if the student clearly chose the correct option.
     - 0.0 if the answer is clearly incorrect or blank.
   - For short-answer questions:
     - 1.0 if the answer is fully correct.
     - 0.5 if the answer is partially correct (e.g. correct idea, but small arithmetic or formatting mistake).
     - 0.0 if the answer is incorrect.
3. Set mistake_type:
   - "correct" if the answer is fully correct.
   - "minor-error" for small arithmetic or notation errors.
   - "calculation-error" for mistakes mainly in computation.
   - "conceptual-error" if the student does not understand the concept.
   - "guess" if the answer looks random or unrelated.
   - "blank" if the student left it empty or wrote "I don't know".
   - "other" if none of the above fits.
4. Provide short, student-friendly feedback explaining why the answer is correct or what went wrong.

You must output ONLY a JSON object with the following structure:

{
  "evaluations": [
    {
      "question_id": 1,
      "q_type": "mcq",
      "student_answer": "...",
      "correct_answer": "...",
      "score": 1.0,
      "max_score": 1.0,
      "mistake_type": "correct",
      "feedback": "..."
    },
    ...
  ],
  "summary": {
    "total_questions": 10,
    "total_score": 8.5,
    "max_score": 10.0,
    "percentage": 85.0
  }
}

Rules:
- max_score is normally 1.0 for each question.
- total_score is the sum of all per-question scores.
- percentage = (total_score / max_score) * 100, rounded reasonably.
- Be consistent with the student's answers and the correct answers provided.
- Use friendly, concise language in feedback.

STRICT OUTPUT RULES:
- Do NOT include any text outside of the JSON.
- Do NOT wrap the JSON in markdown or backticks.
- The response must start with '{' and end with '}'.
"""


# ---------- Create Evaluator Agent & Runner ----------

MODEL_NAME = "gemini-2.0-flash"

evaluator_agent = LlmAgent(
    model=MODEL_NAME,
    name="evaluator_agent",
    description="Evaluates student answers against correct answers and provides scores + feedback.",
    instruction=EVALUATOR_INSTRUCTION,
)

e_runner = Runner(
    agent=evaluator_agent,
    app_name=APP_NAME,
    session_service=shared_session_service,  # 🔁 same SessionService as Planner & QGen
)


# ---------- Public function: evaluate_worksheet ----------

def evaluate_worksheet(result: WorksheetResult) -> WorksheetEvaluation:
    """
    Call the evaluator_agent to evaluate a completed worksheet (questions + answers).
    Returns a WorksheetEvaluation with per-question scores and an overall summary.
    """

    payload = {
        "worksheet_result": result.model_dump(),
    }

    prompt = (
        "Evaluate this worksheet: assign scores and feedback per question, and a summary.\n"
        + json.dumps(payload, indent=2)
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )

    response_text = None

    for event in e_runner.run(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    ):
        # Uncomment to debug:
        # print("EVALUATOR EVENT:", event)
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text.strip()

    if not response_text:
        raise RuntimeError("Evaluator agent did not return a final response.")

    eval_dict = extract_json_from_text(response_text)
    evaluation = WorksheetEvaluation.model_validate(eval_dict)
    return evaluation