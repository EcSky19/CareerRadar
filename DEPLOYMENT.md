# Career Radar — Deployment Guide

## Infrastructure
- **Server**: Hetzner VPS (Ubuntu 24)
- **Backend**: Docker container on port 8000
- **Frontend**: PM2 process on port 3000
- **Reverse Proxy**: Nginx with SSL (Certbot)
- **Database**: Supabase PostgreSQL

## Live URLs
- Frontend: https://careerradar.mingly.ai
- API: https://api.mingly.ai

## Redeploy Commands
```bash
cd /opt/CareerRadar
git pull

# Backend
docker stop career-radar-api && docker rm career-radar-api
docker build -t career-radar-api backend/
docker run -d --name career-radar-api --restart unless-stopped \
  --network host --env-file backend/.env career-radar-api

# Frontend
cd frontend && npm run build
pm2 restart career-radar-frontend
```

## Environment Variables
See `backend/.env.example` for required variables.
