"""
Greenhouse Adapter
==================
Uses the official Greenhouse Job Board API v1 — no scraping needed.

Official docs: https://developers.greenhouse.io/job-board.html

Two endpoints are used:
  1. GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
     Returns summary list of all open jobs.
  2. GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true
     Returns full job details including description HTML.

The board_token is stored in company.ats_slug.

Detection hint: careers URLs containing "greenhouse.io" or embedded Greenhouse
widgets on custom career pages. The board token is often visible in the URL
as ?gh_jid= or embedded in a <script> tag with "greenhouse.io/embed/job_board".
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

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseAdapter(JobSourceAdapter):
    ATS_PROVIDER = "greenhouse"

    async def fetch_jobs(self, company) -> list[NormalizedJob]:
        """
        Fetch all open jobs for a Greenhouse-hosted company.

        Requires company.ats_slug to be set to the board token.
        Falls back to auto-detecting the board token from company.careers_url.
        """
        board_token = company.ats_slug

        if not board_token:
            board_token = await self._detect_board_token(company.careers_url or "")
            if not board_token:
                raise AdapterError(
                    f"No Greenhouse board token for {company.name}. "
                    "Set ats_slug in company settings."
                )

        async with build_http_client() as client:
            jobs_data = await self._get_json(
                f"{GREENHOUSE_API}/{board_token}/jobs?content=true",
                client,
            )

        raw_jobs = jobs_data.get("jobs", [])
        if not raw_jobs:
            raise AdapterEmpty()

        normalized = []
        for raw in raw_jobs:
            normalized.append(self._normalize(raw, company, board_token))

        logger.info(
            "Greenhouse [%s]: fetched %d jobs",
            company.name, len(normalized)
        )
        return normalized

    # ── Private ───────────────────────────────────────────────────────────────

    def _normalize(self, raw: dict, company, board_token: str) -> NormalizedJob:
        job_id   = str(raw.get("id", ""))
        title    = raw.get("title", "").strip()
        location = self._extract_location(raw)
        dept     = self._extract_department(raw)
        desc     = raw.get("content", "") or ""     # HTML description
        posted   = self._parse_date(raw.get("updated_at") or raw.get("first_published"))

        app_url  = (
            raw.get("absolute_url")
            or f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}"
        )

        return NormalizedJob(
            external_job_id=job_id,
            company_name=company.name,
            title=title,
            location=location,
            is_remote=self._infer_remote(title, location),
            department=dept,
            employment_type=self._extract_employment_type(raw),
            role_type=None,     # inferred by normalizer later
            description=desc,
            application_url=app_url,
            source_url=f"{GREENHOUSE_API}/{board_token}/jobs",
            ats_provider=self.ATS_PROVIDER,
            posted_at=posted,
            raw_data=raw,
        )

    @staticmethod
    def _extract_location(raw: dict) -> Optional[str]:
        loc = raw.get("location", {})
        if isinstance(loc, dict):
            return loc.get("name")
        return str(loc) if loc else None

    @staticmethod
    def _extract_department(raw: dict) -> Optional[str]:
        depts = raw.get("departments", [])
        if depts and isinstance(depts, list):
            return depts[0].get("name") if isinstance(depts[0], dict) else str(depts[0])
        return None

    @staticmethod
    def _extract_employment_type(raw: dict) -> Optional[str]:
        metadata = raw.get("metadata", [])
        for m in metadata:
            if isinstance(m, dict) and m.get("name", "").lower() in ("employment type", "job type"):
                return str(m.get("value", "")).strip() or None
        return None

    @staticmethod
    async def _detect_board_token(careers_url: str) -> Optional[str]:
        """
        Try to extract the Greenhouse board token from a careers page URL or
        an embedded script tag.

        Common patterns:
          - https://boards.greenhouse.io/{token}
          - https://jobs.lever.co/{slug}  (not Greenhouse, ignore)
          - embedded: Grnhse.Iframe.load('{token}')
          - embedded: greenhouse.io/embed/job_board?for={token}
        """
        # Direct board URL
        m = re.search(r"boards\.greenhouse\.io/([^/?#]+)", careers_url)
        if m:
            return m.group(1)

        # Sometimes token is in ?gh_src or ?t= params — skip those, unreliable

        # Try to fetch the careers page and look for the embed token
        if not careers_url:
            return None

        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(careers_url)
                html = resp.text
        except Exception:
            return None

        for pattern in (
            r"Grnhse\.Iframe\.load\('([^']+)'",
            r"greenhouse\.io/embed/job_board\?for=([^&\"']+)",
            r"boards\.greenhouse\.io/([A-Za-z0-9_-]+)",
        ):
            m = re.search(pattern, html)
            if m:
                return m.group(1)

        return None
