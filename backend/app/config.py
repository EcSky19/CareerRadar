from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "Career Radar"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # ── Supabase ─────────────────────────────────────────────────────────────
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str

    # ── Email / Alerts ────────────────────────────────────────────────────────
    resend_api_key: Optional[str] = None
    alert_from_email: str = "alerts@careeradar.app"
    alert_from_name: str = "Career Radar"

    # ── Ingestion ─────────────────────────────────────────────────────────────
    ingestion_request_timeout: int = 20
    ingestion_request_delay: float = 1.5
    ingestion_max_retries: int = 3
    ingestion_user_agent: str = (
        "Mozilla/5.0 (compatible; CareerRadar/1.0; +https://careeradar.app)"
    )

    # ── Matching ──────────────────────────────────────────────────────────────
    default_minimum_match_score: int = 70

    # ── Resume / Storage ──────────────────────────────────────────────────────
    supabase_storage_bucket: str = "resumes"
    max_resume_size_bytes: int = 10 * 1024 * 1024

    # ── Anthropic (Resume AI optimizer) ───────────────────────────────────────
    anthropic_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"          # silently ignore any unknown env vars


@lru_cache()
def get_settings() -> Settings:
    return Settings()