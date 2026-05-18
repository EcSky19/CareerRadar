"""
Lever Adapter
=============
Uses the official Lever Postings API (public, no auth needed).

Official docs: https://github.com/lever/postings-api

Base URL: https://api.lever.co/v0/postings/{company_slug}

The company_slug is the subdomain used in Lever URLs, e.g.:
  https://jobs.lever.co/stripe  →  slug = "stripe"

Endpoint returns JSON array of job postings with full descriptions.
Supports ?mode=json (guaranteed JSON), ?skip and ?limit for pagination.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.services.ingestion.base import (
    JobSourceAdapter, NormalizedJob, AdapterError, AdapterEmpty, build_http_client
)

logger = logging.getLogger(__name__)

LEVER_API = "https://api.lever.co/v0/postings"
LEVER_PAGE_SIZE = 100


class LeverAdapter(JobSourceAdapter):
    ATS_PROVIDER = "lever"

    async def fetch_jobs(self, company) -> list[NormalizedJob]:
        slug = company.ats_slug

        if not slug:
            slug = self._detect_slug(company.careers_url or "", company.domain or "")
            if not slug:
                raise AdapterError(
                    f"No Lever slug for {company.name}. "
                    "Set ats_slug (e.g. 'stripe') in company settings."
                )

        all_jobs = []
        skip = 0

        async with build_http_client() as client:
            while True:
                url = f"{LEVER_API}/{slug}?mode=json&skip={skip}&limit={LEVER_PAGE_SIZE}"
                batch = await self._get_json(url, client)

                if not isinstance(batch, list):
                    raise AdapterError(f"Lever returned unexpected payload for {company.name}")

                if not batch:
                    break

                all_jobs.extend(batch)

                if len(batch) < LEVER_PAGE_SIZE:
                    break   # last page

                skip += LEVER_PAGE_SIZE

        if not all_jobs:
            raise AdapterEmpty()

        normalized = [self._normalize(raw, company, slug) for raw in all_jobs]
        logger.info("Lever [%s]: fetched %d jobs", company.name, len(normalized))
        return normalized

    # ── Private ───────────────────────────────────────────────────────────────

    def _normalize(self, raw: dict, company, slug: str) -> NormalizedJob:
        job_id = raw.get("id", "")
        title  = raw.get("text", "").strip()

        # Location: Lever returns a categories.location field
        cats     = raw.get("categories", {})
        location = cats.get("location") or raw.get("workplaceType")
        dept     = cats.get("department") or cats.get("team")
        commit   = cats.get("commitment")     # Full-time, Internship, etc.

        desc_parts = []
        for section in raw.get("descriptionBody", {}).get("content", []):
            desc_parts.append(section.get("text", ""))
        description = "\n".join(filter(None, desc_parts)) or raw.get("description", "")

        app_url = (
            raw.get("applyUrl")
            or f"https://jobs.lever.co/{slug}/{job_id}/apply"
        )
        post_url = raw.get("hostedUrl") or f"https://jobs.lever.co/{slug}/{job_id}"

        posted = self._parse_date_ms(raw.get("createdAt"))

        return NormalizedJob(
            external_job_id=job_id,
            company_name=company.name,
            title=title,
            location=location,
            is_remote=self._infer_remote(title, location),
            department=dept,
            employment_type=commit,
            role_type=self._infer_role_type(commit, title),
            description=description,
            application_url=app_url,
            source_url=post_url,
            ats_provider=self.ATS_PROVIDER,
            posted_at=posted,
            raw_data=raw,
        )

    @staticmethod
    def _parse_date_ms(ms_value) -> Optional[object]:
        """Lever timestamps are Unix epoch milliseconds."""
        if ms_value is None:
            return None
        try:
            from datetime import datetime
            return datetime.utcfromtimestamp(int(ms_value) / 1000).date()
        except (ValueError, TypeError, OSError):
            return None

    @staticmethod
    def _infer_role_type(commitment: Optional[str], title: str) -> Optional[str]:
        c = (commitment or "").lower()
        t = title.lower()
        if "intern" in c or "intern" in t or "co-op" in t or "coop" in t:
            return "internship"
        if any(w in t for w in ("new grad", "new graduate", "university grad", "campus")):
            return "new_grad"
        if "full" in c and "time" in c:
            return "full_time"
        if "contract" in c:
            return "contract"
        return None

    @staticmethod
    def _detect_slug(careers_url: str, domain: str) -> Optional[str]:
        # https://jobs.lever.co/{slug}
        m = re.search(r"jobs\.lever\.co/([^/?#]+)", careers_url)
        if m:
            return m.group(1)
        # Try domain root, e.g. stripe.com → "stripe"
        m = re.match(r"([a-z0-9-]+)\.[a-z]+$", domain.lower().removeprefix("www."))
        if m:
            return m.group(1)
        return None
