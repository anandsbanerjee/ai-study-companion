# study_agents/report_agent.py

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
from study_agents.progress_agent import ProgressProfile, ProgressSummary


# ---------- Report Model ----------

class Report(BaseModel):
    audience: Literal["student", "parent", "teacher"] = Field(
        description="Intended audience for this report."
    )
    headline: str = Field(
        description="Short headline capturing the student's current status."
    )
    strengths_sentence: str = Field(
        description="Single sentence describing strengths."
    )
    weaknesses_sentence: str = Field(
        description="Single sentence describing weaknesses or areas for improvement."
    )
    next_steps_sentence: str = Field(
        description="Single sentence describing the recommended next steps."
    )
    bullet_points: List[str] = Field(
        description="3–6 bullet points summarizing key points in simple language."
    )


# ---------- Instruction for Report Agent ----------

REPORT_INSTRUCTION = """
You are a report-writing agent for an AI Study Companion.

You are given:
1. A progress_profile object:
   - student_id
   - grade
   - subject
   - topics: mapping from topic name to:
     - skills: mapping from skill_tag to:
       - attempts
       - correct
       - accuracy (percentage)
   - total_sessions
   - last_topic
   - last_percentage

2. A progress_summary object:
   - summary_text
   - strengths: list of strengths (skills/topics)
   - weaknesses: list of weaknesses
   - recommended_next_topics: list of topics/skills to focus on next
   - motivational_message

3. An audience value: one of "student", "parent", or "teacher".

Your task:
- Produce a short, human-readable progress report tailored to the audience.
- The report must be encouraging, specific, and easy to understand.

Guidelines by audience:
- For "student":
  - Use friendly, encouraging language.
  - Speak directly to the student ("You are...", "You can...", etc.).
  - Keep sentences simple and motivating.

- For "parent":
  - Be slightly more formal.
  - Focus on how the child is progressing and what support might help at home.
  - Mention specific topics/skills and how the child is tracking.

- For "teacher":
  - Focus more on skills, accuracy trends, and next instructional steps.
  - Use concise, professional language.
  - Include suggestions for targeted practice or interventions.

You must output ONLY a JSON object with the following keys:

{
  "audience": "student" | "parent" | "teacher",
  "headline": "...",
  "strengths_sentence": "...",
  "weaknesses_sentence": "...",
  "next_steps_sentence": "...",
  "bullet_points": [
    "...",
    "...",
    "..."
  ]
}

Details:
- headline: 1 short sentence capturing current status (e.g. "You are building strong fraction skills!")
- strengths_sentence: 1 sentence summarizing strengths.
- weaknesses_sentence: 1 sentence summarizing key areas to work on.
- next_steps_sentence: 1 sentence suggesting focus for the next few sessions.
- bullet_points: 3–6 short bullet points; each should be a crisp, standalone point.

STRICT OUTPUT RULES:
- Do NOT include any text outside the JSON.
- Do NOT wrap the JSON in markdown or backticks.
- The response must start with '{' and end with '}'.
"""


# ---------- Create Report Agent & Runner ----------

MODEL_NAME = "gemini-2.0-flash"

report_agent = LlmAgent(
    model=MODEL_NAME,
    name="report_agent",
    description="Turns a progress profile and summary into a short report tailored to a given audience.",
    instruction=REPORT_INSTRUCTION,
)

r_runner = Runner(
    agent=report_agent,
    app_name=APP_NAME,
    session_service=shared_session_service,  # reuse the same SessionService
)


# ---------- Public function: generate_report ----------

def generate_report(
    profile: ProgressProfile,
    progress_summary: ProgressSummary,
    audience: str = "student",
) -> Report:
    """
    Generate a human-readable progress report for the given audience
    using the numeric profile and the narrative progress summary.
    """

    if audience not in ("student", "parent", "teacher"):
        raise ValueError("audience must be one of: 'student', 'parent', 'teacher'")

    payload = {
        "audience": audience,
        "progress_profile": profile.model_dump(),
        "progress_summary": progress_summary.model_dump(),
    }

    prompt = (
        "Create a short progress report in JSON form for the given audience:\n"
        + json.dumps(payload, indent=2)
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )

    response_text = None

    for event in r_runner.run(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    ):
        # Uncomment for debugging:
        # print("REPORT EVENT:", event)
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text.strip()

    if not response_text:
        raise RuntimeError("Report agent did not return a final response.")

    report_dict = extract_json_from_text(response_text)
    report = Report.model_validate(report_dict)
    return report