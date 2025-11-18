# AI Study Companion – A Multi-Agent Learning System
Automated planning, question generation, evaluation, explanations & progress reporting for K–10 students
Built using Google ADK, Gemini Models, and Streamlit

## Overview
AI Study Companion is a multi-agent learning platform that automatically generates personalised study sessions for school students, evaluates their responses, provides concept-level explanations, tracks long-term progress, and produces reports for students, parents, and teachers.

This project was developed as part of the Kaggle x Google Agentic AI 5-Day Intensive, following the Capstone specification.

The system demonstrates:
🧠 7 autonomous LLM agents
🔁 A full multi-agent loop
🛠️ Custom tools (Worksheet Loop, In-memory Progress Store)
🧭 Shared sessions & state
📊 Long-term skill memory
🖥️ Interactive Streamlit UI
📄 Structured schema-based inputs & outputs
🎓 Real student-style learning experience

## System Capabilities
✔ Personalized study plan
Planner Agent creates question counts, difficulty mix, and types based on grade & topic.

✔ Automatic question generation
Generator Agent produces MCQs and short-answer questions following strict JSON schemas.

✔ Interactive worksheet
Streamlit UI presents questions to students and collects responses.

✔ Automatic evaluation
    Evaluator Agent scores every answer and identifies mistake types:
    - correct
    - minor error
    - calculation error
    - conceptual error
    - guess
    - blank
    - incorrect

✔ Adaptive explanations
Explanation Agent provides per-question hints and full explanations.

✔ Long-term memory
Progress Agent updates a persistent skill profile for each student.

✔ Multi-audience reports

Report Agent generates:
- Student Summary
- Parent Feedback Report
- Teacher Diagnostic Report

## Architecture
🔧 Multi-Agent Pipeline
Planner → Question Generator → Worksheet → Evaluator → Explanation → Progress → Report

    UI --> Orchestrator
    Orchestrator --> Planner
    Planner --> QGen
    QGen --> Worksheet
    Worksheet --> Orchestrator
    Orchestrator --> Evaluator
    Evaluator --> Explanation
    Explanation --> Progress
    Progress --> Report
    Report --> UI

📁 Repository Structure
    ai-study-companion/
    │
    ├── study_agents/
    │   ├── planner_agent.py
    │   ├── question_generator_agent.py
    │   ├── worksheet_loop.py
    │   ├── evaluator_agent.py
    │   ├── explanation_agent.py
    │   ├── progress_agent.py
    │   ├── report_agent.py
    │
    ├── services/
    │   └── study_flow.py
    │
    ├── app.py                    # Streamlit UI
    ├── requirements.txt
    ├── .env.example              # env variable template (safe)
    ├── .gitignore
    └── README.md

## Local Environment
1️⃣ Clone the repo
    git clone https://github.com/<your-username>/<repo-name>.git
    cd <repo-name>

2️⃣ Create & activate a virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Set up environment variables
cp .env.example .env
Edit .env and add your Google API Key:
GOOGLE_API_KEY=YOUR_REAL_KEY_HERE

5️⃣ Start the UI
streamlit run app.py

A browser will launch with AI Companion app. Flow the instructions in the browser to see the app in action:
- Pick grade/subject/topic
- Attempt questions
- Receive explanations
- View progress
- Get detailed reports

## Technology Stack
1. LLM Agents       :   Google ADK, Gemini 2.0 Flash
2. Tools            :   Custom Tools (Worksheet, Progress Store)
3. State & Memory   :   InMemorySessionService
4. UI               :   Streamlit
5. Models           :   Pydantic v2
6. Orchestration    :   Python service layer

🧠 About Agents
1. Planner Agent                :   Creates a personalised worksheet layout.
2. Question Generator Agent     :   Produces well-formatted MCQ and short-response questions.
3. Worksheet Loop               :   Non-LLM tool for administering student interactions.
4. Evaluator Agent              :   Scores answers and labels mistake types.
5. Explanation Agent            :   Provides guidance, hints, and correct reasoning.
6. Progress Agent               :   Maintains long-term skill memory for each student.
7. Report Agent                 :   Generates Student, Parent, and Teacher reports.

## Memory
The system maintains per-student metrics:
- Attempts per skill
- Correct answers
- Accuracy percentage
- Strengths / weaknesses
- Improvement trend
This is stored in an in-memory dictionary. Future improvement could be have a database configured.

⭐ Acknowledgements
Google – Agent Development Kit
Gemini Models
Kaggle – 5-Day Agentic AI Intensive