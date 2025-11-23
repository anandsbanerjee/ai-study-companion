# app.py

import os
from typing import Dict

import streamlit as st
from dotenv import load_dotenv

from study_agents.question_generator_agent import QuestionSet, Question
from services.study_flow import (
    run_planning_and_generation,
    run_full_analysis,
)


# ---------- Setup ----------
# Prefer Streamlit secrets in deployed env, fallback to local .env for dev
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    # on Streamlit Cloud, this will be set in the Secrets section
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        os.environ["GOOGLE_API_KEY"] = api_key
    else:
        # local dev fallback if you still use .env
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    st.error("GOOGLE_API_KEY is not set. Please configure it in Streamlit secrets or .env.")

# Only for local setup
# load_dotenv()

# api_key = os.getenv("GOOGLE_API_KEY")
# if not api_key:
#     st.error("GOOGLE_API_KEY not set. Please configure your .env file.")
#     st.stop()

# st.set_page_config(
#     page_title="AI Study Companion",
#     page_icon="🧠",
#     layout="wide",
# )


# ---------- Session State Helpers ----------

def init_session_state():
    if "plan" not in st.session_state:
        st.session_state.plan = None
    if "qset" not in st.session_state:
        st.session_state.qset: QuestionSet | None = None
    if "answers" not in st.session_state:
        st.session_state.answers: Dict[int, str] = {}
    if "analysis" not in st.session_state:
        st.session_state.analysis = None


init_session_state()


# ---------- Sidebar: Config ----------

st.sidebar.title("📋 Session Setup")

student_id = st.sidebar.text_input("Student ID", value="demo_student_1")
grade = st.sidebar.selectbox("Grade", ["Year 3", "Year 4", "Year 5", "Year 6"], index=2)
subject = st.sidebar.selectbox("Subject", ["Maths"], index=0)
topic = st.sidebar.text_input("Topic", value="Fractions")
time_minutes = st.sidebar.slider("Time (minutes)", min_value=10, max_value=40, value=20, step=5)
difficulty = st.sidebar.selectbox("Difficulty", ["easy", "medium", "hard", "mixed"], index=3)

if st.sidebar.button("1️⃣ Plan & Generate Questions"):
    with st.spinner("Calling Planner and Question Generator agents..."):
        try:
            result = run_planning_and_generation(
                grade=grade,
                subject=subject,
                topic=topic,
                time_minutes=time_minutes,
                difficulty=difficulty,
            )
            st.session_state.plan = result["plan"]
            st.session_state.qset = result["qset"]
            st.session_state.answers = {}
            st.session_state.analysis = None
            st.success("Plan and questions generated!")
        except Exception as e:
            st.error(f"Error while generating plan/questions: {e}")

st.title("🧠 AI Study Companion – Worksheet Session")


# ---------- Main Area: Show Plan & Questions ----------

col_plan, col_questions = st.columns([1, 2])

with col_plan:
    st.subheader("📑 Study Plan")
    if st.session_state.plan is None:
        st.info("Click **'1️⃣ Plan & Generate Questions'** in the sidebar to start.")
    else:
        plan = st.session_state.plan
        st.write(f"**Total questions:** {plan.total_questions}")
        st.write(f"**MCQ:** {plan.mcq_count} | **Short:** {plan.short_count}")
        st.write("**Difficulty distribution:**")
        st.json(plan.difficulty_distribution)
        st.write(f"**Estimated time:** {plan.estimated_time_minutes} minutes")

with col_questions:
    st.subheader("❓ Questions")

    qset: QuestionSet | None = st.session_state.qset

    if qset is None:
        st.info("No questions yet. Generate a plan first.")
    else:
        with st.form(key="worksheet_form"):
            for q in qset.questions:
                st.markdown(f"**Q{q.id}.** {q.question_text}")

                if q.q_type == "mcq" and q.options:
                    # Use radio buttons with option labels
                    options = [f"{i+1}. {opt}" for i, opt in enumerate(q.options)]
                    default_idx = 0
                    selected = st.radio(
                        f"Your answer for Q{q.id}",
                        options,
                        index=None,
                        key=f"q_{q.id}_mcq",
                    )
                    if selected is None:
                        answer_text = ""
                    else:
                        # store just the index+1 as string (e.g. "1")
                        answer_text = selected.split(".")[0].strip()
                else:
                    answer_text = st.text_input(
                        f"Your answer for Q{q.id}",
                        value="",
                        key=f"q_{q.id}_short",
                    )

                # Update in a local dict; we will commit on submission
                st.session_state.answers[q.id] = answer_text

                st.markdown("---")

            submitted = st.form_submit_button("2️⃣ Submit Answers & Analyze")

        if submitted:
            with st.spinner("Evaluating answers and generating feedback..."):
                try:
                    analysis = run_full_analysis(
                        student_id=student_id,
                        grade=grade,
                        subject=subject,
                        topic=topic,
                        qset=qset,
                        answers_by_qid=st.session_state.answers,
                    )
                    st.session_state.analysis = analysis
                    st.success("Analysis complete!")
                except Exception as e:
                    st.error(f"Error during analysis: {e}")


# ---------- Show Results (Evaluation, Explanations, Progress, Report) ----------

analysis = st.session_state.analysis

if analysis is not None:
    st.markdown("## 📊 Results & Feedback")

    tab_eval, tab_expl, tab_progress, tab_reports = st.tabs(
        ["Scores", "Explanations", "Progress", "Reports"]
    )

    # ---- Scores Tab ----
    with tab_eval:
        evaluation = analysis["evaluation"]
        result = analysis["worksheet_result"]

        st.subheader("Overall Score")
        st.write(
            f"**Score:** {evaluation.summary.total_score} / {evaluation.summary.max_score}  "
            f"(**{evaluation.summary.percentage}%**)"
        )

        st.subheader("Per-question Evaluation")
        eval_by_qid = {ev.question_id: ev for ev in evaluation.evaluations}

        for q in result.questions:
            ev = eval_by_qid.get(q.id)
            if not ev:
                continue
            st.markdown(f"**Q{q.id}.** {q.question_text}")
            st.write(f"- Your answer: `{ev.student_answer}`")
            st.write(f"- Correct answer: `{ev.correct_answer}`")
            st.write(f"- Score: **{ev.score} / {ev.max_score}**")
            st.write(f"- Mistake type: `{ev.mistake_type}`")
            st.write(f"- Feedback: {ev.feedback}")
            st.markdown("---")

    # ---- Explanations Tab ----
    with tab_expl:
        explanations = analysis["explanations"]
        st.subheader("Hints & Explanations")

        expl_by_qid = {e.question_id: e for e in explanations.explanations}

        for q in analysis["worksheet_result"].questions:
            ex = expl_by_qid.get(q.id)
            if not ex:
                continue
            st.markdown(f"**Q{q.id}.** {q.question_text}")
            st.write(f"**Hint:** {ex.short_hint}")
            st.write("**Explanation:**")
            st.write(ex.explanation)
            st.markdown("---")

    # ---- Progress Tab ----
    with tab_progress:
        profile = analysis["profile"]
        progress_summary = analysis["progress_summary"]

        st.subheader("Numeric Progress Profile")
        st.write(f"**Student:** {profile.student_id}")
        st.write(f"**Grade:** {profile.grade} | **Subject:** {profile.subject}")
        st.write(f"**Total sessions:** {profile.total_sessions}")
        st.write(f"**Last topic:** {profile.last_topic}")
        st.write(f"**Last percentage:** {profile.last_percentage}")

        for topic_name, tp in profile.topics.items():
            st.markdown(f"### Topic: {topic_name}")
            rows = []
            for skill_tag, stat in tp.skills.items():
                rows.append(
                    {
                        "Skill": skill_tag,
                        "Attempts": stat.attempts,
                        "Correct": stat.correct,
                        "Accuracy (%)": stat.accuracy,
                    }
                )
            if rows:
                st.table(rows)

        st.subheader("Narrative Summary")
        st.write(progress_summary.summary_text)
        st.write(f"**Strengths:** {', '.join(progress_summary.strengths) or '—'}")
        st.write(f"**Weaknesses:** {', '.join(progress_summary.weaknesses) or '—'}")
        st.write(
            f"**Recommended next topics:** "
            f"{', '.join(progress_summary.recommended_next_topics) or '—'}"
        )
        st.write(f"**Motivational message:** {progress_summary.motivational_message}")

    # ---- Reports Tab ----
    with tab_reports:
        st.subheader("Audience-specific Reports")

        report_student = analysis["report_student"]
        report_parent = analysis["report_parent"]
        report_teacher = analysis["report_teacher"]

        r_tab_student, r_tab_parent, r_tab_teacher = st.tabs(
            ["👦 Student", "👪 Parent", "👩‍🏫 Teacher"]
        )

        def render_report(r):
            st.markdown(f"### {r.headline}")
            st.write("**Strengths:**", r.strengths_sentence)
            st.write("**Areas to improve:**", r.weaknesses_sentence)
            st.write("**Next steps:**", r.next_steps_sentence)
            st.write("**Key points:**")
            for bp in r.bullet_points:
                st.write(f"- {bp}")

        with r_tab_student:
            render_report(report_student)

        with r_tab_parent:
            render_report(report_parent)

        with r_tab_teacher:
            render_report(report_teacher)
