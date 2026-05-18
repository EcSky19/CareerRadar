"""
Ashby Adapter
=============
Uses the Ashby Job Board API.

Ashby provides a public GraphQL-style JSON API:
  POST https://api.ashbyhq.com/posting-api/job-board/{company_slug}

Payload: {"$type":"PostingsApiV2QueryRequest","includeCompensation":true}

Returns: { results: [ { id, title, locationName, departmentName,
                         employmentType, descriptionHtml, applicationLink,
                         publishedDate, ... } ] }

The company_slug is the subdomain, e.g.:
  https://jobs.ashbyhq.com/Linear  →  slug = "Linear"
  https://jobs.ashbyhq.com/retool  →  slug = "retool"

Ashby slugs are case-sensitive — preserve original casing from the URL.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from app.services.ingestion.base import (
    JobSourceAdapter, NormalizedJob, AdapterError, AdapterEmpty, build_http_client
)

logger = logging.getLogger(__name__)

ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board"


class AshbyAdapter(JobSourceAdapter):
    ATS_PROVIDER = "ashby"

    async def fetch_jobs(self, company) -> list[NormalizedJob]:
        slug = company.ats_slug

        if not slug:
            slug = self._detect_slug(company.careers_url or "")
            if not slug:
                raise AdapterError(
                    f"No Ashby slug for {company.name}. "
                    "Set ats_slug in company settings (case-sensitive)."
                )

        url = f"{ASHBY_API}/{slug}"
        async with build_http_client() as client:
            try:
                resp = await client.post(
                    url,
                    json={
                        "$type": "PostingsApiV2QueryRequest",
                        "includeCompensation": True,
                    },
                    headers={"Content-Type": "application/json"},
                )
            except httpx.RequestError as exc:
                raise AdapterError(f"Network error fetching Ashby for {company.name}: {exc}")

            if resp.status_code == 404:
                raise AdapterError(
                    f"Ashby 404 for slug '{slug}'. Verify the slug in company settings.",
                    http_status=404,
                )
            if resp.status_code >= 400:
                raise AdapterError(
                    f"Ashby HTTP {resp.status_code} for {company.name}",
                    http_status=resp.status_code,
                )

            try:
                data = resp.json()
            except Exception as exc:
                raise AdapterError(f"Ashby JSON parse error for {company.name}: {exc}")

        raw_jobs = data.get("results") or data.get("jobs") or []
        if not raw_jobs:
            raise AdapterEmpty()

        normalized = [self._normalize(raw, company, slug) for raw in raw_jobs]
        logger.info("Ashby [%s]: fetched %d jobs", company.name, len(normalized))
        return normalized

    # ── Private ───────────────────────────────────────────────────────────────

    def _normalize(self, raw: dict, company, slug: str) -> NormalizedJob:
        job_id   = raw.get("id", "")
        title    = (raw.get("title") or "").strip()
        location = raw.get("locationName") or raw.get("location", {}).get("locationName")
        dept     = raw.get("departmentName") or None
        emp_type = raw.get("employmentType")
        desc     = raw.get("descriptionHtml") or raw.get("description") or ""
        posted   = self._parse_date(raw.get("publishedDate") or raw.get("updatedAt"))

        app_url  = (
            raw.get("applicationLink")
            or raw.get("applyUrl")
            or f"https://jobs.ashbyhq.com/{slug}/{job_id}"
        )

        return NormalizedJob(
            external_job_id=job_id,
            company_name=company.name,
            title=title,
            location=location,
            is_remote=self._infer_remote(title, location),
            department=dept,
            employment_type=emp_type,
            role_type=self._infer_role_type(emp_type, title),
            description=desc,
            application_url=app_url,
            source_url=f"https://jobs.ashbyhq.com/{slug}",
            ats_provider=self.ATS_PROVIDER,
            posted_at=posted,
            raw_data=raw,
        )

    @staticmethod
    def _infer_role_type(emp_type: Optional[str], title: str) -> Optional[str]:
        t = title.lower()
        e = (emp_type or "").lower()
        if "intern" in t or "intern" in e or "coop" in t or "co-op" in t:
            return "internship"
        if any(w in t for w in ("new grad", "new graduate", "university grad", "early career", "campus")):
            return "new_grad"
        if "contract" in e:
            return "contract"
        if "full" in e:
            return "full_time"
        return None

    @staticmethod
    def _detect_slug(careers_url: str) -> Optional[str]:
        m = re.search(r"jobs\.ashbyhq\.com/([^/?#]+)", careers_url)
        return m.group(1) if m else None
