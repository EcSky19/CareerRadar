"""
JSearch Adapter (OpenWebNinja)
==============================
Fetches jobs from OpenWebNinja JSearch API which aggregates
LinkedIn, Indeed, Glassdoor, ZipRecruiter and more.
Scans weekly (Mondays) to stay within free tier limits.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional
import httpx
from app.services.ingestion.base import (
    JobSourceAdapter, NormalizedJob, AdapterError, AdapterEmpty
)

logger = logging.getLogger(__name__)

JSEARCH_API_URL = "https://api.openwebninja.com/jsearch/search"
PAGE_SIZE = 10  # Max per request


class JSearchAdapter(JobSourceAdapter):
    ATS_PROVIDER = "jsearch"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def fetch_jobs(self, company) -> list[NormalizedJob]:
        if not self.api_key:
            raise AdapterError("JSearch API key not configured")

        all_jobs = []
        # Search for software/tech roles at this company
        queries = [
            f"software engineer early career new grad 2026 2027 {company.name}",
        ]

        async with httpx.AsyncClient(timeout=20) as client:
            for query in queries:
                try:
                    r = await client.get(
                        JSEARCH_API_URL,
                        headers={"x-api-key": self.api_key},
                        params={
                            "query": query,
                            "num_pages": "1",
                            "date_posted": "month",
                        }
                    )
                    if r.status_code == 429:
                        raise AdapterError("JSearch rate limit hit", http_status=429)
                    if r.status_code != 200:
                        raise AdapterError(
                            f"JSearch HTTP {r.status_code} for {company.name}",
                            http_status=r.status_code
                        )
                    data = r.json()
                    jobs = data.get("data", [])
                    all_jobs.extend(jobs)
                except httpx.RequestError as e:
                    raise AdapterError(f"JSearch network error: {e}")

        # Deduplicate by job_id
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            job_id = job.get("job_id", "")
            if job_id not in seen:
                seen.add(job_id)
                unique_jobs.append(job)

        if not unique_jobs:
            raise AdapterEmpty()

        normalized = []
        for raw in unique_jobs:
            try:
                normalized.append(self._normalize(raw, company))
            except Exception as e:
                logger.warning(f"JSearch normalize error: {e}")
                continue

        logger.info("JSearch [%s]: fetched %d jobs", company.name, len(normalized))
        return normalized

    def _normalize(self, raw: dict, company) -> NormalizedJob:
        job_id     = raw.get("job_id", "")
        title      = (raw.get("job_title") or "").strip()
        location   = raw.get("job_city") or raw.get("job_state") or raw.get("job_country") or ""
        is_remote  = raw.get("job_is_remote", False)
        description = raw.get("job_description", "") or ""
        apply_url  = raw.get("job_apply_link") or raw.get("job_google_link") or ""
        employer   = raw.get("employer_name") or company.name

        posted = None
        posted_ms = raw.get("job_posted_at_timestamp")
        if posted_ms:
            try:
                posted = datetime.fromtimestamp(posted_ms, tz=timezone.utc)
            except Exception:
                posted = datetime.now(timezone.utc)

        emp_type = raw.get("job_employment_type")

        return NormalizedJob(
            external_job_id=job_id,
            title=title,
            company_name=employer,
            location=location,
            is_remote=bool(is_remote),
            description=description[:5000],
            application_url=apply_url,
            source_url=apply_url,
            posted_at=posted,
            employment_type=emp_type,
            department=None,
            role_type=None,
        )

    @staticmethod
    def detect_from_url(careers_url: str) -> Optional[str]:
        return None
