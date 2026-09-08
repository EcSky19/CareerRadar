# Contributing to Career Radar

## Setup
1. Clone the repo
2. Copy `backend/.env.example` to `backend/.env` and fill in values
3. Run `docker build -t career-radar-api backend/`
4. Run `cd frontend && npm install && npm run dev`

## Architecture
- **Backend**: FastAPI + SQLAlchemy async + PostgreSQL (Supabase)
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS
- **Hosting**: Hetzner + Nginx + Docker + PM2

## ATS Adapters
Add new adapters in `backend/app/services/ingestion/`
Register them in `runner.py` `_ADAPTERS` dict

## Matching Engine
Scoring logic in `backend/app/services/matching/engine.py`
100-point scale: title(25) + role_type(15) + keywords(15) + location(10) + category(10) + domain(10) + priority(5) + freshness(5) + campus(5)
