"""
Base ingestion adapter.

Every ATS adapter must:
  1. Subclass JobSourceAdapter
  2. Implement async fetch_jobs(company) -> list[NormalizedJob]
  3. Return only open, currently visible jobs (the runner handles diffing)

Design goals:
  - Prefer official structured ATS feeds / APIs over HTML scraping
  - Use HTML parsing only when no structured feed is available
  - Use Playwright only as an absolute last resort
  - Never bypass CAPTCHAs, login walls, or anti-bot systems
  - Log and raise on errors; do not silently return empty lists
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Any
from uuid import UUID

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Shared HTTP client ────────────────────────────────────────────────────────

def build_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=settings.ingestion_request_timeout,
        headers={"User-Agent": settings.ingestion_user_agent},
        follow_redirects=True,
    )


# ── Normalized job object ─────────────────────────────────────────────────────

@dataclass
class NormalizedJob:
    """
    Universal job representation returned by every adapter.
    Matches the `jobs` table schema exactly.
    """
    # Required
    title: str
    application_url: str
    company_name: str

    # Identity / dedup
    external_job_id: Optional[str]     = None
    source_url: Optional[str]          = None
    ats_provider: str                   = "unknown"

    # Classification
    location: Optional[str]            = None
    is_remote: Optional[bool]          = None
    department: Optional[str]          = None
    employment_type: Optional[str]     = None
    role_type: Optional[str]           = None   # internship | new_grad | full_time | coop | contract

    # Content
    description: Optional[str]         = None
    posted_at: Optional[date]          = None

    # Raw payload for debugging / re-normalization
    raw_data: dict[str, Any]           = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "external_job_id": self.external_job_id,
            "company_name":    self.company_name,
            "title":           self.title,
            "location":        self.location,
            "is_remote":       self.is_remote,
            "department":      self.department,
            "employment_type": self.employment_type,
            "role_type":       self.role_type,
            "description":     self.description,
            "application_url": self.application_url,
            "source_url":      self.source_url,
            "ats_provider":    self.ats_provider,
            "posted_at":       self.posted_at,
            "raw_data":        self.raw_data,
        }


# ── Adapter errors ────────────────────────────────────────────────────────────

class AdapterError(Exception):
    """Raised when an adapter fails and the company check should be logged as failed."""
    def __init__(self, message: str, http_status: Optional[int] = None):
        super().__init__(message)
        self.http_status = http_status

class AdapterRateLimited(AdapterError):
    """HTTP 429 received."""

class AdapterNotFound(AdapterError):
    """Career page or API endpoint returned 404."""

class AdapterEmpty(Exception):
    """
    Raised when the source returns successfully but zero jobs are found.
    This is a valid state (company is not hiring) and should NOT be logged
    as an error — just zero new jobs.
    """


# ── Base class ────────────────────────────────────────────────────────────────

class JobSourceAdapter(ABC):
    """
    Abstract base class for all ATS adapters.

    Usage:
        adapter = GreenhouseAdapter()
        jobs = await adapter.fetch_jobs(company_record)
    """

    ATS_PROVIDER: str = "unknown"

    @abstractmethod
    async def fetch_jobs(self, company) -> list[NormalizedJob]:
        """
        Fetch all currently open jobs for the given company.

        Args:
            company: SQLAlchemy Company ORM instance

        Returns:
            List of NormalizedJob objects (may be empty)

        Raises:
            AdapterError: on network, parse, or structural failure
        """

    # ── Shared helpers available to all subclasses ────────────────────────────

    async def _get_json(self, url: str, client: httpx.AsyncClient) -> Any:
        """GET + JSON parse with standardized error handling."""
        await asyncio.sleep(settings.ingestion_request_delay)
        try:
            response = await client.get(url)
        except httpx.TimeoutException:
            raise AdapterError(f"Request timed out: {url}")
        except httpx.RequestError as exc:
            raise AdapterError(f"Network error fetching {url}: {exc}")

        if response.status_code == 404:
            raise AdapterNotFound(f"404 from {url}", http_status=404)
        if response.status_code == 429:
            raise AdapterRateLimited(f"Rate limited by {url}", http_status=429)
        if response.status_code >= 400:
            raise AdapterError(
                f"HTTP {response.status_code} from {url}",
                http_status=response.status_code,
            )
        try:
            return response.json()
        except Exception as exc:
            raise AdapterError(f"JSON parse error from {url}: {exc}")

    async def _get_html(self, url: str, client: httpx.AsyncClient) -> str:
        """GET + return HTML text."""
        await asyncio.sleep(settings.ingestion_request_delay)
        try:
            response = await client.get(url)
        except httpx.TimeoutException:
            raise AdapterError(f"Request timed out: {url}")
        except httpx.RequestError as exc:
            raise AdapterError(f"Network error: {exc}")

        if response.status_code >= 400:
            raise AdapterError(
                f"HTTP {response.status_code} from {url}",
                http_status=response.status_code,
            )
        return response.text

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except (ValueError, TypeError):
                continue
        return None

    @staticmethod
    def _infer_remote(title: str, location: Optional[str]) -> Optional[bool]:
        haystack = f"{title} {location or ''}".lower()
        if any(w in haystack for w in ("remote", "anywhere", "distributed", "work from home")):
            return True
        return None
