# SmartOnboard

Verified Hiring Ecosystem & AI Hiring Operating System

SmartOnboard is a trust-first hiring platform designed to help recruiters discover qualified candidates through verification, intelligent matching, and AI-assisted hiring workflows.

## Core Principles

- Trust Over Volume
- AI As Copilot
- Verified Participants
- Better Hiring Decisions

## Current Status

Completed:
- Milestone 11.5 Security Foundation
- Milestone 12 Identity Layer

Current:
- Milestone 13 Candidate Workspace

## Documentation

Start Here:

1. AGENTS.md
2. AI_HANDOFF.md
3. CURRENT_STATUS.md

Product Documentation:

- docs/product/PRODUCT_VISION.md
- docs/product/PRD.md
- docs/product/TRD.md

Security:

- docs/security/SECURITY_ROADMAP.md
- docs/security/RISK_MATRIX.md

Reports:

- docs/reports/MILESTONE_11_5_REPORT.md
- docs/reports/MILESTONE_12_REPORT.md

## Running Locally

Backend:

uvicorn backend.server:app --reload

Frontend:

cd frontend
npm install
npm run dev

## Tech Stack

Frontend:
- React
- TypeScript

Backend:
- FastAPI

Database:
- PostgreSQL
- pgvector

Infrastructure:
- Docker

Billing:
- Stripe

SMS:
- Twilio