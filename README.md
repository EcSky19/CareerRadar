# Career Radar 🎯

Automated job monitoring and matching platform for new grad and entry-level candidates.

## Live
- Frontend: https://careerradar.mingly.ai
- API: https://api.mingly.ai

## Features
- 🔍 Monitors your target companies daily
- 🤖 AI-powered job matching engine (100-point scoring)
- 👤 Multiple career profiles — customize job titles, keywords, locations
- 🏢 Target company management
- 📊 Multi-source job ingestion — real-time ATS + GitHub + JSearch
- 🆓 Primarily free — minimal API costs
- 📄 Resume AI optimization (coming soon)
- 🗂️ Application tracker (coming soon)

## Job Sources

### Direct ATS (Real-time, Free, Unlimited)
| Adapter | Quality | Notes |
|---|---|---|
| Greenhouse | ⭐⭐⭐⭐⭐ | Direct API, real-time |
| Lever | ⭐⭐⭐⭐⭐ | Direct API, real-time |
| Ashby | ⭐⭐⭐⭐⭐ | Direct API, real-time |
| WorkdayCXS | ⭐⭐⭐⭐ | Hidden API, near real-time |

### GitHub Community Repos (Daily, Free, Unlimited)
- SimplifyJobs/New-Grad-Positions (16k⭐)
- SimplifyJobs/Summer2027-Internships (47k⭐)
- jobright-ai/2026-Software-Engineer-New-Grad
- zapplyjobs/New-Grad-Software-Engineering-Jobs-2027
- vanshb03/New-Grad-2027
- vanshb03/Summer2027-Internships
- speedyapply/2027-SWE-College-Jobs

### JSearch Broad Search (Daily, 5 calls/scan)
Searches LinkedIn, Indeed, Glassdoor, ZipRecruiter via OpenWebNinja API.
5 broad queries filter results to all monitored companies.

## Tech Stack
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python, SQLAlchemy async
- **Database**: PostgreSQL (Supabase)
- **Hosting**: Hetzner (self-hosted)
- **Auth**: Supabase JWT

## Setup
See backend/.env.example for required environment variables.
