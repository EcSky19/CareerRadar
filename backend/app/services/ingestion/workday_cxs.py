"""
Workday CXS Adapter
===================
Uses Workday's internal CXS JSON API that powers their career pages.
URL format: https://{tenant}.wd{n}.myworkdayjobs.com/wday/cxs/{tenant}/{board}/jobs
"""
from __future__ import annotations
import logging
from typing import Optional
from datetime import datetime, timezone

import httpx

from app.services.ingestion.base import (
    JobSourceAdapter,
    JobSourceAdapter, NormalizedJob, AdapterError, AdapterEmpty, AdapterNotFound
)

logger = logging.getLogger(__name__)

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

PAGE_SIZE = 20


class WorkdayCXSAdapter(JobSourceAdapter):
    ATS_PROVIDER = "workday_cxs"

    async def fetch_jobs(self, company) -> list[NormalizedJob]:
        url = company.careers_url
        if not url or "wday/cxs" not in url:
            raise AdapterError(f"Invalid Workday CXS URL for {company.name}: {url}")

        all_jobs = []
        offset = 0

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            while True:
                try:
                    resp = await client.post(
                        url,
                        json={"limit": PAGE_SIZE, "offset": offset, "searchText": ""},
                        headers=HEADERS,
                    )
                except httpx.RequestError as e:
                    raise AdapterError(f"Network error for {company.name}: {e}")

                if resp.status_code != 200:
                    raise AdapterError(
                        f"Workday CXS HTTP {resp.status_code} for {company.name}",
                        http_status=resp.status_code,
                    )

                try:
                    data = resp.json()
                except Exception as e:
                    raise AdapterError(f"JSON parse error for {company.name}: {e}")

                postings = data.get("jobPostings", [])
                all_jobs.extend(postings)

                total = data.get("total", 0)
                offset += PAGE_SIZE
                if offset >= total or not postings:
                    break

        if not all_jobs:
            raise AdapterEmpty()

        normalized = []
        for raw in all_jobs:
            try:
                normalized.append(self._normalize(raw, company))
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Normalize error: {e} for {raw.get('title')}")
                continue

        logger.info("WorkdayCXS [%s]: fetched %d jobs", company.name, len(normalized))
        return normalized

    def _normalize(self, raw: dict, company) -> NormalizedJob:
        job_id = raw.get("bulletFields", [None])[0] if raw.get("bulletFields") else raw.get("externalPath", "").strip("/").split("/")[-1]
        title = (raw.get("title") or "").strip()
        location = raw.get("locationsText", "") or ""
        is_remote = "remote" in (location + title).lower()

        # Get job detail URL
        ext_path = raw.get("externalPath", "")
        base = company.careers_url.split("/wday/cxs/")[0]
        board_path = company.careers_url.split("/wday/cxs/")[1].rsplit("/jobs", 1)[0]
        apply_url = f"{base}/{board_path.split('/', 1)[1]}{ext_path}" if ext_path else company.careers_url

        posted = None
        posted_on = raw.get("postedOn", "")
        if posted_on:
            try:
                posted = datetime.fromisoformat(posted_on.replace("Z", "+00:00"))
            except Exception:
                posted = datetime.now(timezone.utc)

        return NormalizedJob(
            external_job_id=ext_path or job_id or title,
            title=title,
            company_name=company.name,
            location=location,
            is_remote=is_remote,
            description=raw.get("jobDescription", {}).get("descriptor", "") if isinstance(raw.get("jobDescription"), dict) else "",
            application_url=apply_url,
            source_url=apply_url,
            posted_at=posted,
            employment_type=None,
            department=None,
            role_type=None,
        )

    @staticmethod
    def detect_from_url(careers_url: str) -> Optional[str]:
        if careers_url and "wday/cxs" in careers_url:
            return careers_url.split("/wday/cxs/")[1].rsplit("/jobs", 1)[0].split("/", 1)[1] if "/" in careers_url.split("/wday/cxs/")[1] else None
        return None
