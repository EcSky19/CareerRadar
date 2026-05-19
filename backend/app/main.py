from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import engine, Base

from app.routers import (
    companies,
    profiles,
    jobs,
    ingestion,
    alerts,
    resumes,
    users,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Allow all origins — safe for a personal tool, tighten later if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
API = "/api/v1"

app.include_router(users.router,     prefix=f"{API}/users",           tags=["Users"])
app.include_router(companies.router, prefix=f"{API}/companies",       tags=["Companies"])
app.include_router(profiles.router,  prefix=f"{API}/target-profiles", tags=["Target Profiles"])
app.include_router(jobs.router,      prefix=f"{API}/jobs",            tags=["Jobs"])
app.include_router(ingestion.router, prefix=f"{API}/ingestion",       tags=["Ingestion"])
app.include_router(alerts.router,    prefix=f"{API}/alerts",          tags=["Alerts"])
app.include_router(resumes.router,   prefix=f"{API}/resumes",         tags=["Resumes"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}