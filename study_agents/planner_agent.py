# study_agents/planner_agent.py


import re
from typing import Dict
import os
import json
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Define the structured output: StudyPlan model
class StudyPlan(BaseModel):
    total_questions: int = Field(description="Total number of questions in the session.")
    mcq_count: int = Field(description="Number of multiple-choice questions.")
    short_count: int = Field(description="Number of short answer questions.")
    difficulty_distribution: dict = Field(
        description="Map difficulty to count, e.g. {'easy':4,'medium':4,'hard':2}."
    )
    estimated_time_minutes: int = Field(
        description="Estimated total time in minutes for this plan."
    )

# Write the planner agent prompt

PLANNER_INSTRUCTION = """
You are a planning agent for an AI Study Companion.

Your task is to create a STUDY QUESTION PLAN, not the actual questions.

You receive:
- grade (e.g. "Year 5", "Year 8")
- subject (e.g. "Maths", "English")
- topic (e.g. "Fractions", "Algebra", "Reading Comprehension")
- time_minutes (integer, e.g. 20)
- difficulty (one of: "easy", "medium", "hard", "mixed")

You must:
1. Decide a suitable TOTAL number of questions that can be done in time_minutes.
2. Decide how many should be:
   - Multiple choice (MCQ)
   - Short answer
3. Decide a difficulty distribution, e.g.:
   {"easy": 4, "medium": 4, "hard": 2}
4. Ensure:
   - mcq_count + short_count == total_questions
   - Sum of difficulty_distribution values == total_questions
   - The plan is realistic for the time and grade.

OUTPUT FORMAT (IMPORTANT):
Return ONLY a valid JSON object matching this schema:
{
  "total_questions": <int>,
  "mcq_count": <int>,
  "short_count": <int>,
  "difficulty_distribution": {
    "easy": <int>,
    "medium": <int>,
    "hard": <int>
  },
  "estimated_time_minutes": <int>
}

STRICT RULES:
- Do NOT include any explanation, commentary, or extra text.
- Do NOT wrap the JSON in markdown or backticks.
- Do NOT prefix it with phrases like "Here is your JSON".
- The response must start with '{' and end with '}'.
"""

# Instantiate the planner_agent with ADK
MODEL_NAME = "gemini-2.0-flash"  # or the model they recommend in the course

planner_agent = LlmAgent(
    model=MODEL_NAME,
    name="planner_agent",
    description="Plans the number and mix of questions for a study session.",
    instruction=PLANNER_INSTRUCTION,
    # For now we'll parse JSON manually instead of output_schema to simplify debugging
)

# Set up Session + Runner (the ADK runtime loop)
APP_NAME = "study_companion_app"
USER_ID = "demo_user"
SESSION_ID = "planner_session_1"

# 1) Create the session service
session_service = InMemorySessionService()

# 2) Create a session synchronously (no async, no await)
session = session_service.create_session_sync(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID,
)

# 3) Create the runner
runner = Runner(
    agent=planner_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

# Helper function to call the Planner Agent -- Ensuring only JSON output
def extract_json_from_text(text: str) -> dict:
    """
    Try to extract a JSON object from the model's text output.
    Handles code fences and extra narration.
    """
    if not text:
        raise ValueError("Model returned empty response text.")

    raw = text.strip()

    # If wrapped in ```...```, strip the fences first
    if raw.startswith("```"):
        # remove starting fence with optional language label
        raw = re.sub(r"^```[a-zA-Z0-9_+-]*\s*", "", raw)
        # remove trailing fence
        if raw.endswith("```"):
            raw = raw[:-3].strip()

    # Find the first '{' and the last '}' to isolate the JSON object
    start = raw.find("{")
    end = raw.rfind("}")

    if start == -1 or end == -1 or end <= start:
        print("Could not locate JSON braces in output. Full text was:\n")
        print(raw)
        raise ValueError("Could not find JSON object in LLM output.")

    json_str = raw[start : end + 1]

    # Now try to load it
    return json.loads(json_str)

# Method to query LLM and get output
def get_study_plan(
    grade: str,
    subject: str,
    topic: str,
    time_minutes: int,
    difficulty: str,
):
    print("=== PLANNER AGENT ===")
    user_payload = {
        "grade": grade,
        "subject": subject,
        "topic": topic,
        "time_minutes": time_minutes,
        "difficulty": difficulty,
    }

    prompt = (
        "Create a study question plan using the provided input:\n"
        + json.dumps(user_payload, indent=2)
    )

    content = types.Content(role="user", parts=[types.Part(text=prompt)])

    response_text = None

    for event in runner.run(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text.strip()

    if not response_text:
        raise RuntimeError("Planner agent did not return a final response text.")

    # 🔽 Use the robust extractor here
    try:
        plan_dict = extract_json_from_text(response_text)
    except Exception as e:
        print("Raw response_text from planner_agent:\n")
        print(response_text)
        raise e

    plan = StudyPlan.model_validate(plan_dict)
    return plan