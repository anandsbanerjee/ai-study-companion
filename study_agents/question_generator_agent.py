import json
import re
from typing import List, Optional, Literal

from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
# from study_agents.planner_agent import StudyPlan, extract_json_from_text

from study_agents.planner_agent import (
    StudyPlan,
    extract_json_from_text,
    APP_NAME,
    USER_ID,
    SESSION_ID,
    session_service as planner_session_service,
)

#Step 1 – Define Question Models (Pydantic)
class Question(BaseModel):
    id: int = Field(description="Question index in the worksheet (starting from 1).")
    q_type: Literal["mcq", "short"] = Field(
        description="Type of the question: 'mcq' for multiple-choice, 'short' for short answer."
    )
    question_text: str = Field(description="The actual text of the question.")
    
    # For MCQ
    options: Optional[List[str]] = Field(
        default=None,
        description="List of options for MCQ questions, e.g. ['A', 'B', 'C', 'D']."
    )
    correct_option: Optional[str] = Field(
        default=None,
        description="The correct option value for MCQs, e.g. 'B' or '3'."
    )
    
    # For short answer
    answer: Optional[str] = Field(
        default=None,
        description="The correct answer for short answer questions as a string."
    )
    
    difficulty: Literal["easy", "medium", "hard"] = Field(
        description="Difficulty level of the question."
    )
    skill_tag: str = Field(
        description="Short tag describing the skill, e.g. 'fractions-addition'."
    )

class QuestionSet(BaseModel):
    questions: List[Question] = Field(
        description="List of all questions generated for this session."
    )

# Step 2 – Design the Question Generator Instruction. We want the agent to:
# Respect the plan: mcq_count, short_count, difficulty distribution
# Use grade/subject/topic
# Return JSON only (no prose)

QUESTION_GENERATOR_INSTRUCTION = """
You are a question generation agent for an AI Study Companion.

Your job is to generate PRACTICE QUESTIONS for a given student session, based on a STUDY PLAN.
You do NOT generate a plan here; the plan is already given.

You receive:
- grade: e.g. "Year 5"
- subject: e.g. "Maths"
- topic: e.g. "Fractions"
- study_plan: a JSON object with:
  - total_questions (int)
  - mcq_count (int)
  - short_count (int)
  - difficulty_distribution (dict of 'easy'/'medium'/'hard' -> int)
  - estimated_time_minutes (int)

Your tasks:
1. Generate EXACTLY `total_questions` questions.
2. Ensure:
   - Exactly `mcq_count` questions have q_type = "mcq".
   - Exactly `short_count` questions have q_type = "short".
   - The counts of 'easy', 'medium', 'hard' across all questions match difficulty_distribution.
3. For each question, produce a JSON object with:
   - id: integer starting at 1
   - q_type: "mcq" or "short"
   - question_text: the question text
   - options: list of options (only for MCQ; set to null for short answers)
   - correct_option: correct option (only for MCQ; set to null for short answers)
   - answer: correct answer as a string (only for short; set to null for MCQ)
   - difficulty: "easy" or "medium" or "hard"
   - skill_tag: short tag like "fractions-addition", "fractions-of-a-quantity", etc.

For Maths (primary years), make sure:
- Numbers are reasonable (small whole numbers where possible).
- Fractions are simple and age-appropriate.
- Word problems are clear and not overly long.

OUTPUT FORMAT (IMPORTANT):
Return ONLY a JSON object with a single key "questions" whose value is a list of question objects.

Example shape (not real data):
{
  "questions": [
    {
      "id": 1,
      "q_type": "mcq",
      "question_text": "...",
      "options": ["A", "B", "C", "D"],
      "correct_option": "B",
      "answer": null,
      "difficulty": "easy",
      "skill_tag": "fractions-addition"
    },
    {
      "id": 2,
      "q_type": "short",
      "question_text": "...",
      "options": null,
      "correct_option": null,
      "answer": "3/4",
      "difficulty": "medium",
      "skill_tag": "fractions-of-a-quantity"
    }
  ]
}

STRICT RULES:
- Do NOT include explanations or commentary.
- Do NOT wrap the JSON in markdown or backticks.
- Do NOT prefix it with any text. The response must start with '{' and end with '}'.
"""
# Step 3 – Create the Question Generator Agent

# Configuration items
MODEL_NAME = "gemini-2.0-flash"


# ---------- Create Question Generator Agent & Runner ----------

question_generator_agent = LlmAgent(
    model=MODEL_NAME,
    name="question_generator_agent",
    description="Generates MCQ and short-answer questions based on a study plan.",
    instruction=QUESTION_GENERATOR_INSTRUCTION,
    # We'll parse JSON manually (like with planner) for now
)

# We do not need to create a new session; we can reuse SESSION_ID that already exists.
# Both agents share the same underlying InMemorySessionService.
q_runner = Runner(
    agent=question_generator_agent,
    app_name=APP_NAME,
    session_service=planner_session_service,
)

# ---------- Public function: generate_questions ----------

def generate_questions(
    plan: StudyPlan,
    grade: str,
    subject: str,
    topic: str,
):
    """
    Calls the question_generator_agent to create a list of questions based on the StudyPlan.
    Returns a QuestionSet object.
    """
    # Convert StudyPlan to pure dict for JSON
    plan_dict = plan.model_dump()

    user_payload = {
        "grade": grade,
        "subject": subject,
        "topic": topic,
        "study_plan": plan_dict,
    }

    prompt = (
        "Generate questions for the following student session:\n"
        + json.dumps(user_payload, indent=2)
    )

    content = types.Content(role="user", parts=[types.Part(text=prompt)])

    response_text = None

    for event in q_runner.run(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    ):
        # Uncomment to inspect the event flow:
        # print("QGEN EVENT:", event)
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text.strip()

    if not response_text:
        raise RuntimeError("Question generator agent did not return a final response.")

    # Use the robust JSON extractor we defined earlier
    try:
        qset_dict = extract_json_from_text(response_text)
    except Exception as e:
        print("Raw response_text from question_generator_agent:\n")
        print(response_text)
        raise e

    qset = QuestionSet.model_validate(qset_dict)
    return qset