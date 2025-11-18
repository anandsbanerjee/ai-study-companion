# AI Study Companion – Multi-Agent Learning App

## Overview
Short description of your project...

## Features
- Planner Agent
- Question Generator Agent
- Worksheet Loop (non-LLM)
- Evaluator Agent
- Explanation Agent
- Progress Agent
- Report Agent
- Streamlit UI

## Setup

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
python -m venv .venv
.venv\Scripts\activate  # on Windows
pip install -r requirements.txt
cp .env.example .env  # then edit .env and add your real Google API key
streamlit run app.py