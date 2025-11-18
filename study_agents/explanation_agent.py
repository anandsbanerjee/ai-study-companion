# study_agents/explanation_agent.py

import json
from typing import List

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
from study_agents.evaluator_agent import WorksheetEvaluation


# ---------- Explanation Models ----------

class QuestionExplanation(BaseModel):
    question_id: int = Field(description="ID of the question.")
    short_hint: str = Field(
        description="A short hint that nudges the student in the right direction without giving the full answer."
    )
    explanation: str = Field(
        description="A step-by-step explanation in clear, age-appropriate language."
    )


class ExplanationSet(BaseModel):
    explanations: List[QuestionExplanation] = Field(
        description="List of explanations for the questions in the worksheet."
    )


# ---------- Explanation Agent Instruction ----------

EXPLANATION_INSTRUCTION = """
You are an explanation agent for a Maths practice worksheet.

You are given:
1. A worksheet_result object:
   - questions: each has
     - id
     - q_type ("mcq" or "short")
     - question_text
     - options (for MCQ)
     - correct_option or answer
     - difficulty
     - skill_tag
   - answers: each has
     - question_id
     - q_type
     - student_answer

2. A worksheet_evaluation object:
   - evaluations: each has
     - question_id
     - q_type
     - student_answer
     - correct_answer
     - score
     - max_score
     - mistake_type (correct, minor-error, calculation-error, conceptual-error, guess, blank, other)
     - feedback
   - summary: overall performance

Your tasks:
- For EACH question in the worksheet:
  - Create a short_hint:
    - 1–2 sentences.
    - Do NOT reveal the full answer.
    - Focus on the next best step the student should think about.
  - Create a full step-by-step explanation:
    - Explain how to solve the question from start to finish.
    - Use clear, age-appropriate language for the given grade.
    - Emphasize any concept the student got wrong, based on mistake_type and feedback.

Output format:
You MUST output ONLY a JSON object with the following structure:

{
  "explanations": [
    {
      "question_id": 1,
      "short_hint": "...",
      "explanation": "..."
    },
    ...
  ]
}

Rules:
- Provide one entry in 'explanations' for every question in the worksheet_result.
- Use the student's mistake_type and feedback to tailor the explanation if they were wrong.
- If the answer was correct, still provide a brief explanation reinforcing the method.

STRICT OUTPUT RULES:
- Do NOT include any text outside of the JSON.
- Do NOT wrap the JSON in markdown or backticks.
- The response must start with '{' and end with '}'.
"""


# ---------- Create Explanation Agent & Runner ----------

MODEL_NAME = "gemini-2.0-flash"

explanation_agent = LlmAgent(
    model=MODEL_NAME,
    name="explanation_agent",
    description="Provides hints and step-by-step explanations for each worksheet question.",
    instruction=EXPLANATION_INSTRUCTION,
)

x_runner = Runner(
    agent=explanation_agent,
    app_name=APP_NAME,
    session_service=shared_session_service,  # 🔁 same SessionService as others
)


# ---------- Public function: generate_explanations ----------

def generate_explanations(
    result: WorksheetResult,
    evaluation: WorksheetEvaluation,
) -> ExplanationSet:
    """
    Call the explanation_agent to generate hints + step-by-step explanations
    for each question in the worksheet, based on both the student's answers
    and the evaluation.
    """

    payload = {
        "worksheet_result": result.model_dump(),
        "worksheet_evaluation": evaluation.model_dump(),
    }

    prompt = (
        "Generate hints and step-by-step explanations for this worksheet:\n"
        + json.dumps(payload, indent=2)
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )

    response_text = None

    for event in x_runner.run(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    ):
        # Uncomment for debugging:
        # print("EXPLANATION EVENT:", event)
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text.strip()

    if not response_text:
        raise RuntimeError("Explanation agent did not return a final response.")

    expl_dict = extract_json_from_text(response_text)
    explanation_set = ExplanationSet.model_validate(expl_dict)
    return explanation_set