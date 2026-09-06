# Career Radar

Automated job monitoring + resume optimization platform.

Monitors ATS job boards (Greenhouse, Lever, Ashby) daily, scores every new listing against
your target profiles using a 100-point matching engine, sends email alerts for strong matches,
and includes a Resume Intelligence Engine for keyword gap analysis and AI-powered bullet rewrites.

## Architecture

```
frontend/   Next.js 14 (App Router)  →  Vercel (free)
backend/    FastAPI + SQLAlchemy      →  Render Starter ($7/mo)
database    PostgreSQL via Supabase   →  Supabase (free)
scheduler   GitHub Actions cron       →  GitHub (free)
alerts      Resend email API          →  Resend (free)
resume AI   Anthropic Claude API      →  ~$0.50/mo personal use
```

## Setup

See the full step-by-step deployment guide at:
https://github.com/YOUR_USERNAME/career-radar

### Quick start (local)

```bash
# 1. Database — run schema.sql in Supabase SQL editor

# 2. Backend
cd backend
cp .env.example .env          # fill in your credentials
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend
cp .env.example .env.local    # fill in your credentials
npm install
npm run dev
```

Open http://localhost:3000

## Project structure

```
career-radar/
├── schema.sql                    ← Run this first in Supabase
├── backend/
│   ├── .env.example              ← Copy to .env, fill credentials
│   ├── requirements.txt
│   ├── Dockerfile
│   └── app/
│       ├── main.py               ← FastAPI app entry point
│       ├── auth.py               ← Supabase JWT verification
│       ├── config.py             ← All env var settings
│       ├── database.py           ← Async SQLAlchemy engine
│       ├── models.py             ← All 20 ORM models
│       ├── routers/              ← API endpoints
│       └── services/
│           ├── ingestion/        ← ATS adapters + runner
│           ├── matching/         ← Scoring engine
│           ├── resume/           ← Parser + analyzer + optimizer
│           ├── alert_service.py  ← Email via Resend
│           └── scheduler.py     ← APScheduler cron
├── frontend/
│   ├── .env.example              ← Copy to .env.local, fill credentials
│   ├── package.json
│   ├── tailwind.config.js
│   └── src/
│       ├── app/                  ← Next.js pages
│       ├── components/           ← Sidebar, shared UI
│       ├── lib/                  ← API client, utilities
│       └── types/                ← TypeScript types
└── .github/
    └── workflows/
        └── daily_ingestion.yml   ← Runs scanner at 6am UTC daily
```

## Deployment

### Render (backend)
- Root directory: `backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Plan: Starter ($7/mo) for always-on

### Vercel (frontend)
- Root directory: `frontend`
- Framework: Next.js (auto-detected)

### GitHub Actions (daily scanner)
Add two repository secrets:
- `API_URL` — your Render service URL
- `SERVICE_ROLE_JWT` — your Supabase service role key
