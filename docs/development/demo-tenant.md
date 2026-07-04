# Recruiter Demo Development Tenant

This guide explains how to set up and manage the developer demo tenant for testing the Recruiter Workspace.

## Quick Start

### Seeding the Demo Tenant
To seed or update the demo environment, execute the following script from the repository root:
```bash
python backend/seed.py
```
This command is idempotent: running it repeatedly updates existing records to their baseline state without creating duplicate entities.

### Resetting/Cleaning the Tenant
To remove all seeded demo entities (company, users, jobs, applications, interviews, scorecards, notes):
```bash
python backend/seed.py --clean
```

To perform a clean reset (clean first, then seed):
```bash
python backend/seed.py --reset
```

---

## Login Credentials

Use the following credentials on the Recruiter Login page (`http://localhost:5173/recruiter/login`):

*   **Email**: `recruiter.demo@smartonboard.com`
*   **Password**: `Recruiter123!`

---

## Seeded Data & Expected Dashboard Contents

Once logged in, the following dashboard views are populated:

### 1. Recruiter Cockpit Dashboard
*   **Today's Interviews**: Shows 1 scheduled technical interview for **Diana Ross** today.
*   **Recent Applications**: Lists newly submitted applications.
*   **Jobs Requiring Attention**: Lists active jobs requiring recruiter checks.

### 2. Jobs Page
*   **Jobs list**: Renders 3 active jobs:
    1.  *Senior Full Stack Engineer* (Engineering)
    2.  *Product Manager* (Product)
    3.  *Security Analyst* (Security)

### 3. Pipeline Board (Kanban)
*   Displays candidates in their columns:
    *   **Applied**: Grace Kelly, Hank Williams
    *   **Screened**: Frank Sinatra
    *   **Interview**: Diana Ross, Elvis Presley
    *   **Offer**: Charlie Brown
    *   **Hired**: Alice Cooper, Bob Marley
    *   **Rejected**: Iris Murdoch (visible in rejected filters)

### 4. Candidate Drawer
*   Clicking a card opens the side drawer showing matching/missing skills, resume highlights, scorecards (for interview candidates), and candidate logs.

### 5. Analytics Dashboard
*   Renders conversion funnel metrics and pipeline velocity KPIs based on realistic stage transitions and timestamps.

---

## Troubleshooting

*   **Database connection fails**: Ensure Docker PostgreSQL containers are running and database migrations are up-to-date:
    ```bash
    docker compose up -d
    alembic upgrade head
    ```
*   **AI-dependent features ( RAG / Ask AI )**: Sentence-transformer embeddings are calculated programmatically on the local CPU without external API dependencies. Conversational QA features require a valid `GROQ_API_KEY` configured in your `.env` file.
