# SmartOnboard

AI-powered HR recruitment and onboarding SaaS platform.

## Architecture

- **Backend**: FastAPI (Python) on port 8000 — runs from `backend/server.py` with `python -m uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload`
- **Frontend**: React + Vite (TypeScript) on port 5173 — runs from `frontend/` with `npm run dev`
- **AI**: Groq (llama-3.3-70b-versatile) via langchain-groq
- **AI Pipeline**: LangGraph multi-agent workflow (orchestrator → document → training → email agents)

## Key Features

- `/api/onboard` — POST employee details, returns documents, training plan, welcome email
- `/api/screen` — POST resume text or upload PDF, returns AI screening analysis

## Environment Variables

- `GROQ_API_KEY` — Groq API key for all AI agents (get one at https://console.groq.com/keys)
- `DATABASE_URL` — PostgreSQL connection (default: `postgresql+psycopg://smartonboard:smartonboard@localhost:5432/smartonboard`)
- `JWT_SECRET_KEY` — Secret for signing access tokens

## Database setup

```bash
docker compose up -d
alembic upgrade head
```

## API (Phase 1A)

- `POST /api/v1/auth/register` — Create company + owner user
- `POST /api/v1/auth/login` — Sign in
- `GET /api/v1/auth/me` — Current user
- `GET /api/v1/companies/me` — Tenant company
- `GET|POST /api/v1/jobs` — Jobs CRUD (tenant-scoped)
- `GET|POST /api/v1/applications` — Applications (tenant-scoped)

## User Preferences

- Professional SaaS look and feel
- No emojis in the UI
- Clean, modern design suitable for enterprise sales
