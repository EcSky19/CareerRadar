"""
JSearch Broad Search Adapter (OpenWebNinja)
===========================================
Instead of per-company searches, uses 5 broad queries to find
entry-level / new grad roles across ALL companies.

5 calls per scan = ~150 calls/month on daily scanning.
Free tier = 200 calls/month.

Sources: LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google for Jobs
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

# 5 broad queries — covers all entry-level SWE roles
BROAD_QUERIES = [
    "software engineer new grad 2026 2027 United States",
    "entry level software engineer early career United States",
    "new graduate software engineer campus hire United States",
    "junior software developer associate engineer United States",
    "software engineer intern return offer full time 2027 United States",
]


class JSearchAdapter(JobSourceAdapter):
    ATS_PROVIDER = "jsearch"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def fetch_broad_jobs(self, company_names: set[str]) -> list[NormalizedJob]:
        """
        Run 5 broad searches and filter results to our target companies.
        Uses only 5 API calls regardless of company count.
        """
        if not self.api_key:
            raise AdapterError("JSearch API key not configured")

        all_raw = []

        async with httpx.AsyncClient(timeout=45) as client:
            for query in BROAD_QUERIES:
                try:
                    r = await client.get(
                        JSEARCH_API_URL,
                        headers={"x-api-key": self.api_key},
                        params={
                            "query": query,
                            "num_pages": "1",
                            "date_posted": "week",
                        }
                    )
                    if r.status_code == 429:
                        logger.warning("JSearch rate limited")
                        break
                    if r.status_code != 200:
                        logger.warning("JSearch HTTP %d for query: %s", r.status_code, query)
                        continue
                    data = r.json()
                    jobs = data.get("data", [])
                    all_raw.extend(jobs)
                    logger.info("JSearch query '%s': %d jobs", query[:40], len(jobs))
                except Exception as e:
                    logger.warning("JSearch error for query '%s': %s", query[:40], e)

        if not all_raw:
            raise AdapterEmpty()

        # Build fuzzy company lookup
        company_lower = {c.lower().strip(): c for c in company_names}

        normalized = []
        seen_ids = set()

        for raw in all_raw:
            employer = (raw.get("employer_name") or "").strip()
            employer_lower = employer.lower()

            # Match to our companies
            matched = None
            if employer_lower in company_lower:
                matched = company_lower[employer_lower]
            else:
                for db_co_lower, db_co in company_lower.items():
                    if employer_lower in db_co_lower or db_co_lower in employer_lower:
                        matched = db_co
                        break

            if not matched:
                continue

            job_id = raw.get("job_id", "")
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            title = (raw.get("job_title") or "").strip()
            location = raw.get("job_city") or raw.get("job_state") or raw.get("job_country") or ""
            is_remote = bool(raw.get("job_is_remote", False))
            description = (raw.get("job_description", "") or "").encode('utf-8', 'ignore').decode('utf-8')
            apply_url = raw.get("job_apply_link") or raw.get("job_google_link") or ""
            emp_type = raw.get("job_employment_type")

            posted = None
            posted_ms = raw.get("job_posted_at_timestamp")
            if posted_ms:
                try:
                    posted = datetime.fromtimestamp(posted_ms, tz=timezone.utc)
                except Exception:
                    posted = datetime.now(timezone.utc)

            normalized.append(NormalizedJob(
                external_job_id=job_id,
                title=title,
                company_name=matched,
                location=location,
                is_remote=is_remote,
                description=description[:5000],
                application_url=apply_url,
                source_url=apply_url,
                posted_at=posted,
                employment_type=emp_type,
                department=None,
                role_type=None,
            ))

        logger.info("JSearch broad: %d matching jobs from %d total", len(normalized), len(all_raw))
        return normalized

    async def fetch_jobs(self, company) -> list[NormalizedJob]:
        """Not used — JSearch is now a broad search, not per-company."""
        raise AdapterError("JSearch uses fetch_broad_jobs() — not per-company")

    @staticmethod
    def detect_from_url(careers_url: str) -> Optional[str]:
        return None
