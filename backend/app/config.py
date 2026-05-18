from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "Personal Job Hunter"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"   # development | staging | production

    # ── Supabase ─────────────────────────────────────────────────────────────
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str     # used only in backend workers
    supabase_jwt_secret: str           # for verifying JWTs from frontend

    # ── Database (direct connection for SQLAlchemy) ───────────────────────────
    database_url: str                  # postgresql+asyncpg://user:pass@host/db

    # ── Email / Alerts ────────────────────────────────────────────────────────
    resend_api_key: Optional[str] = None
    alert_from_email: str = "alerts@personaljobhunter.app"
    alert_from_name: str = "Personal Job Hunter"

    # ── Ingestion ─────────────────────────────────────────────────────────────
    ingestion_request_timeout: int = 20        # seconds per HTTP request
    ingestion_request_delay: float = 1.5       # seconds between requests to same host
    ingestion_max_retries: int = 3
    ingestion_user_agent: str = (
        "Mozilla/5.0 (compatible; PersonalJobHunter/1.0; +https://personaljobhunter.app)"
    )

    # ── Matching ──────────────────────────────────────────────────────────────
    default_minimum_match_score: int = 70

    # ── Resume / Storage ──────────────────────────────────────────────────────
    supabase_storage_bucket: str = "resumes"
    max_resume_size_bytes: int = 10 * 1024 * 1024   # 10 MB

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
