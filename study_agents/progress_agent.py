# study_agents/progress_agent.py

import json
from typing import Dict, List

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


# ---------- Progress Profile Models (numeric long-term memory) ----------

class SkillStat(BaseModel):
    attempts: int = Field(default=0, description="How many times this skill has been practiced.")
    correct: int = Field(default=0, description="How many times the student was correct.")
    accuracy: float = Field(default=0.0, description="Correct / attempts * 100.")


class TopicProgress(BaseModel):
    skills: Dict[str, SkillStat] = Field(
        default_factory=dict,
        description="Mapping from skill_tag to SkillStat.",
    )


class ProgressProfile(BaseModel):
    student_id: str = Field(description="Unique ID for the student.")
    grade: str = Field(description="Student's grade (e.g. 'Year 5').")
    subject: str = Field(description="Subject (e.g. 'Maths').")
    topics: Dict[str, TopicProgress] = Field(
        default_factory=dict,
        description="Mapping from topic name (e.g. 'Fractions') to TopicProgress.",
    )
    total_sessions: int = Field(default=0, description="Total number of sessions practiced.")
    last_topic: str = Field(default="", description="Most recent topic practiced.")
    last_percentage: float = Field(default=0.0, description="Latest worksheet percentage score.")


# ---------- Narrative Progress Summary Model (LLM output) ----------

class ProgressSummary(BaseModel):
    summary_text: str = Field(
        description="A short narrative summary of the student's recent performance and progress."
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="List of strengths (skills or topics where the student is doing well).",
    )
    weaknesses: List[str] = Field(
        default_factory=list,
        description="List of weaknesses or areas needing improvement.",
    )
    recommended_next_topics: List[str] = Field(
        default_factory=list,
        description="Topics or skills the student should focus on next.",
    )
    motivational_message: str = Field(
        description="Encouraging message tailored to the student."
    )


# ---------- In-memory "DB" for long-term progress ----------

# Simple in-memory store: student_id -> ProgressProfile
PROGRESS_DB: Dict[str, ProgressProfile] = {}


def load_progress_profile(student_id: str, grade: str, subject: str) -> ProgressProfile:
    """
    Load a student's progress profile from the in-memory DB.
    If none exists, create a new default profile.
    """
    if student_id in PROGRESS_DB:
        return PROGRESS_DB[student_id]

    profile = ProgressProfile(
        student_id=student_id,
        grade=grade,
        subject=subject,
        topics={},
        total_sessions=0,
        last_topic="",
        last_percentage=0.0,
    )
    PROGRESS_DB[student_id] = profile
    return profile


def save_progress_profile(profile: ProgressProfile) -> None:
    """
    Save/update the profile in the in-memory DB.
    """
    PROGRESS_DB[profile.student_id] = profile


def update_profile_with_session(
    profile: ProgressProfile,
    topic: str,
    result: WorksheetResult,
    evaluation: WorksheetEvaluation,
) -> ProgressProfile:
    """
    Update the numeric profile with data from a single worksheet session.
    - Increments attempts & correct for each skill_tag.
    - Updates accuracy per skill.
    - Updates total_sessions, last_topic, and last_percentage.
    """

    # Ensure topic exists
    if topic not in profile.topics:
        profile.topics[topic] = TopicProgress(skills={})

    topic_progress = profile.topics[topic]

    # Build a quick lookup for evaluation by question_id
    eval_by_qid = {ev.question_id: ev for ev in evaluation.evaluations}

    for q in result.questions:
        ev = eval_by_qid.get(q.id)
        if not ev:
            continue

        skill_tag = q.skill_tag or "unknown-skill"

        if skill_tag not in topic_progress.skills:
            topic_progress.skills[skill_tag] = SkillStat(attempts=0, correct=0, accuracy=0.0)

        stat = topic_progress.skills[skill_tag]

        stat.attempts += 1
        # Consider >= 0.99 as fully correct
        if ev.score >= 0.99:
            stat.correct += 1

        # Recompute accuracy
        if stat.attempts > 0:
            stat.accuracy = round((stat.correct / stat.attempts) * 100.0, 2)

        topic_progress.skills[skill_tag] = stat

    profile.topics[topic] = topic_progress
    profile.total_sessions += 1
    profile.last_topic = topic
    profile.last_percentage = evaluation.summary.percentage

    save_progress_profile(profile)
    return profile


# ---------- Progress Agent Instruction (LLM summary) ----------

PROGRESS_INSTRUCTION = """
You are a progress analysis agent for an AI Study Companion.

You are given:
1. A numeric progress_profile object:
   - student_id
   - grade
   - subject
   - topics: a mapping from topic name to:
     - skills: mapping from skill_tag to:
       - attempts
       - correct
       - accuracy (percentage)
   - total_sessions
   - last_topic
   - last_percentage

2. The latest worksheet_evaluation object:
   - evaluations: per-question evaluations (including mistake_type and feedback)
   - summary: total_questions, total_score, max_score, percentage

Your tasks:
- Analyze the student's current strengths and weaknesses based on:
  - skill accuracies
  - recent performance in last_topic
  - mistake types (conceptual-error, calculation-error, etc.)

- Produce:
  - summary_text: 2–4 sentences summarizing performance.
  - strengths: list of skills or topics where the student is strong.
  - weaknesses: list of skills or topics that need more practice.
  - recommended_next_topics: list of topics/skills to focus on next, in order of priority.
  - motivational_message: a short, encouraging note appropriate for the student's age/grade.

Output format:
You MUST output ONLY a JSON object like:

{
  "summary_text": "...",
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "recommended_next_topics": ["...", "..."],
  "motivational_message": "..."
}

Guidelines:
- Be specific: mention particular topics or skill_tags rather than generic phrases.
- If the student performed poorly overall, be honest but encouraging.
- If the student did well, celebrate their success and gently suggest next challenges.
- Keep the tone positive and growth-oriented.

STRICT OUTPUT RULES:
- Do NOT include any text outside of the JSON.
- Do NOT wrap the JSON in markdown or backticks.
- The response must start with '{' and end with '}'.
"""


# ---------- Create Progress Agent & Runner ----------

MODEL_NAME = "gemini-2.0-flash"

progress_agent = LlmAgent(
    model=MODEL_NAME,
    name="progress_agent",
    description="Analyzes numeric progress profile and latest evaluation to produce a narrative progress summary.",
    instruction=PROGRESS_INSTRUCTION,
)

p_runner = Runner(
    agent=progress_agent,
    app_name=APP_NAME,
    session_service=shared_session_service,  # Common session service object
)


# ---------- Public function: generate_progress_summary ----------

def generate_progress_summary(
    student_id: str,
    grade: str,
    subject: str,
    topic: str,
    result: WorksheetResult,
    evaluation: WorksheetEvaluation,
) -> tuple[ProgressProfile, ProgressSummary]:
    """
    Update the numeric progress profile based on this session and then
    call the progress_agent to generate a narrative ProgressSummary.

    Returns:
        (profile, progress_summary)
    """

    # 1) Load or create profile
    profile = load_progress_profile(student_id, grade, subject)

    # 2) Update with this session's result/evaluation
    profile = update_profile_with_session(profile, topic, result, evaluation)

    # 3) Prepare payload for LLM
    payload = {
        "progress_profile": profile.model_dump(),
        "worksheet_evaluation": evaluation.model_dump(),
    }

    prompt = (
        "Analyze this student's progress and generate a short summary and recommendations:\n"
        + json.dumps(payload, indent=2)
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )

    response_text = None

    for event in p_runner.run(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    ):
        # Uncomment for debugging:
        # print("PROGRESS EVENT:", event)
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text.strip()

    if not response_text:
        raise RuntimeError("Progress agent did not return a final response.")

    summary_dict = extract_json_from_text(response_text)
    progress_summary = ProgressSummary.model_validate(summary_dict)
    return profile, progress_summary