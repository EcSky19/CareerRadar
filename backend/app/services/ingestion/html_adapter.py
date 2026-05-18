"""
Generic HTML Adapter
====================
Last-resort HTML parser for career pages that don't use a standard ATS.

Strategy:
  1. Try to find embedded JSON-LD job schema (schema.org/JobPosting)
  2. Try to find JSON blobs in <script> tags that look like job arrays
  3. Fall back to heuristic link-based extraction

This adapter is inherently less reliable than structured API adapters.
It logs warnings when falling back to heuristics so operators can investigate
and set a proper ATS provider for the company.

IMPORTANT:
  - Never bypass CAPTCHA, login walls, or bot-detection systems
  - If the page returns a bot-detection response, log an error and abort
  - Playwright fallback is a separate adapter (PlaywrightAdapter) and
    should only be used with explicit per-company opt-in
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.ingestion.base import (
    JobSourceAdapter, NormalizedJob, AdapterError, AdapterEmpty, build_http_client
)

logger = logging.getLogger(__name__)

# Keywords that suggest a job listing anchor
JOB_LINK_SIGNALS = [
    "job", "career", "position", "opening", "role", "opportunity",
    "engineer", "developer", "analyst", "scientist", "intern",
]

BOT_DETECTION_SIGNALS = [
    "access denied", "cloudflare", "captcha", "robot", "please enable javascript",
    "403 forbidden", "security check",
]


class GenericHTMLAdapter(JobSourceAdapter):
    ATS_PROVIDER = "custom_html"

    async def fetch_jobs(self, company) -> list[NormalizedJob]:
        url = company.source_url or company.careers_url
        if not url:
            raise AdapterError(f"No source URL for {company.name}")

        async with build_http_client() as client:
            html = await self._get_html(url, client)

        self._check_for_bot_detection(html, url)

        # Strategy 1: JSON-LD
        jobs = self._extract_jsonld(html, url, company)
        if jobs:
            logger.info("GenericHTML [%s]: found %d jobs via JSON-LD", company.name, len(jobs))
            return jobs

        # Strategy 2: Embedded JSON blobs in <script> tags
        jobs = self._extract_script_json(html, url, company)
        if jobs:
            logger.info("GenericHTML [%s]: found %d jobs via script JSON", company.name, len(jobs))
            return jobs

        # Strategy 3: Heuristic link extraction
        jobs = self._extract_links(html, url, company)
        if jobs:
            logger.warning(
                "GenericHTML [%s]: found %d jobs via heuristic link extraction (lower confidence)",
                company.name, len(jobs)
            )
            return jobs

        raise AdapterEmpty()

    # ── Strategy 1: JSON-LD ───────────────────────────────────────────────────

    def _extract_jsonld(self, html: str, base_url: str, company) -> list[NormalizedJob]:
        soup = BeautifulSoup(html, "html.parser")
        results = []

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue

            # May be a single object or a list
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "JobPosting":
                    job = self._normalize_jsonld(item, company, base_url)
                    if job:
                        results.append(job)

        return results

    def _normalize_jsonld(self, item: dict, company, base_url: str) -> Optional[NormalizedJob]:
        title = item.get("title") or item.get("name", "")
        if not title:
            return None

        # Location
        loc_obj   = item.get("jobLocation", {})
        addr      = loc_obj.get("address", {}) if isinstance(loc_obj, dict) else {}
        city      = addr.get("addressLocality", "") if isinstance(addr, dict) else ""
        region    = addr.get("addressRegion", "")  if isinstance(addr, dict) else ""
        location  = ", ".join(filter(None, [city, region])) or None

        app_url   = item.get("url") or item.get("sameAs") or base_url
        desc      = item.get("description") or ""
        posted    = self._parse_date(item.get("datePosted"))
        emp_type  = item.get("employmentType")

        return NormalizedJob(
            external_job_id=item.get("identifier", {}).get("value") if isinstance(item.get("identifier"), dict) else None,
            company_name=company.name,
            title=title.strip(),
            location=location,
            is_remote=self._infer_remote(title, location),
            employment_type=emp_type,
            role_type=None,
            description=desc,
            application_url=urljoin(base_url, app_url),
            source_url=base_url,
            ats_provider=self.ATS_PROVIDER,
            posted_at=posted,
            raw_data=item,
        )

    # ── Strategy 2: Script JSON blobs ─────────────────────────────────────────

    def _extract_script_json(self, html: str, base_url: str, company) -> list[NormalizedJob]:
        soup = BeautifulSoup(html, "html.parser")
        results = []

        for script in soup.find_all("script"):
            text = script.string or ""
            if len(text) < 50:
                continue
            # Look for JSON arrays that might be job lists
            matches = re.findall(r'(\[{.{20,}}\])', text, re.DOTALL)
            for match in matches[:3]:  # try first 3 large arrays
                try:
                    items = json.loads(match)
                    if not isinstance(items, list) or not items:
                        continue
                    first = items[0]
                    if not isinstance(first, dict):
                        continue
                    # Heuristic: looks like a job object?
                    if any(k in first for k in ("title", "name", "position", "role")):
                        for item in items:
                            job = self._normalize_script_item(item, company, base_url)
                            if job:
                                results.append(job)
                        if results:
                            return results
                except (json.JSONDecodeError, ValueError):
                    continue

        return results

    def _normalize_script_item(self, item: dict, company, base_url: str) -> Optional[NormalizedJob]:
        title = (
            item.get("title") or item.get("name") or
            item.get("position") or item.get("role", "")
        ).strip()
        if not title:
            return None

        link  = item.get("url") or item.get("link") or item.get("applyUrl") or base_url
        loc   = item.get("location") or item.get("city") or None
        desc  = item.get("description") or item.get("content") or ""

        return NormalizedJob(
            external_job_id=str(item.get("id") or item.get("jobId") or ""),
            company_name=company.name,
            title=title,
            location=str(loc) if loc else None,
            is_remote=self._infer_remote(title, str(loc) if loc else None),
            description=str(desc),
            application_url=urljoin(base_url, link),
            source_url=base_url,
            ats_provider=self.ATS_PROVIDER,
            raw_data=item,
        )

    # ── Strategy 3: Heuristic link extraction ─────────────────────────────────

    def _extract_links(self, html: str, base_url: str, company) -> list[NormalizedJob]:
        soup = BeautifulSoup(html, "html.parser")
        results = []
        seen_urls: set[str] = set()

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("mailto:", "tel:", "#", "javascript:")):
                continue

            link_text = a.get_text(strip=True)
            if not link_text or len(link_text) < 5 or len(link_text) > 120:
                continue

            full_url = urljoin(base_url, href)
            if full_url in seen_urls:
                continue

            combined = (href + " " + link_text).lower()
            if not any(sig in combined for sig in JOB_LINK_SIGNALS):
                continue

            seen_urls.add(full_url)
            results.append(NormalizedJob(
                external_job_id=None,
                company_name=company.name,
                title=link_text,
                location=None,
                application_url=full_url,
                source_url=base_url,
                ats_provider=self.ATS_PROVIDER,
                raw_data={"href": href, "text": link_text},
            ))

            if len(results) >= 100:   # safety cap
                break

        return results

    # ── Bot detection ──────────────────────────────────────────────────────────

    @staticmethod
    def _check_for_bot_detection(html: str, url: str):
        lower = html[:3000].lower()
        if any(sig in lower for sig in BOT_DETECTION_SIGNALS):
            raise AdapterError(
                f"Bot detection or access restriction encountered at {url}. "
                "Consider using a Playwright adapter or manually adding this company's ATS slug."
            )
