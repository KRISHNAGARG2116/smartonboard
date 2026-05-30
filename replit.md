# SmartOnboard

AI-powered HR recruitment and onboarding SaaS platform.

## Architecture

- **Backend**: FastAPI (Python) on port 8000 — runs from `backend/server.py` with `python -m uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload`
- **Frontend**: React + Vite (TypeScript) on port 5173 — runs from `frontend/` with `npm run dev`
- **AI**: Google Gemini 2.0 Flash via langchain-google-genai
- **AI Pipeline**: LangGraph multi-agent workflow (orchestrator → document → training → email agents)

## Key Features

- `/api/onboard` — POST employee details, returns documents, training plan, welcome email
- `/api/screen` — POST resume text or upload PDF, returns AI screening analysis

## Environment Variables

- `GEMINI_API_KEY` — Google Gemini API key (stored in Replit Secrets)

## User Preferences

- Professional SaaS look and feel
- No emojis in the UI
- Clean, modern design suitable for enterprise sales
