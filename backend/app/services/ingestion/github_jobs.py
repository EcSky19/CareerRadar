"""
GitHub Jobs Adapter
===================
Fetches new grad / internship job listings from community-maintained
GitHub README repos. Completely free, no API key required.
Updated multiple times daily by thousands of contributors.
"""
from __future__ import annotations
import re
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.services.ingestion.base import (
    JobSourceAdapter, NormalizedJob, AdapterError, AdapterEmpty
)

logger = logging.getLogger(__name__)

GITHUB_REPOS = [
    # ── New Grad Full-Time ──────────────────────────────────────────────────
    {
        "name": "SimplifyJobs New Grad",
        "url": "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md",
        "type": "new_grad",
    },
    {
        "name": "jobright-ai New Grad 2026",
        "url": "https://raw.githubusercontent.com/jobright-ai/2026-Software-Engineer-New-Grad/master/README.md",
        "type": "new_grad",
    },
    {
        "name": "zapplyjobs New Grad 2027",
        "url": "https://raw.githubusercontent.com/zapplyjobs/New-Grad-Software-Engineering-Jobs-2027/main/README.md",
        "type": "new_grad",
    },
    {
        "name": "vanshb03 New Grad 2027",
        "url": "https://raw.githubusercontent.com/vanshb03/New-Grad-2027/main/README.md",
        "type": "new_grad",
    },
    {
        "name": "speedyapply SWE College Jobs 2027",
        "url": "https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main/README.md",
        "type": "new_grad",
    },
    # ── Internships ─────────────────────────────────────────────────────────
    {
        "name": "SimplifyJobs Summer 2027 Internships",
        "url": "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md",
        "type": "internship",
    },
    {
        "name": "vanshb03 Summer 2027 Internships",
        "url": "https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/main/README.md",
        "type": "internship",
    },
]

INTL_SIGNALS = {
    "canada", "ontario", "toronto", "vancouver", "montreal", "ottawa",
    "uk", "united kingdom", "london", "england", "scotland",
    "germany", "berlin", "munich", "frankfurt",
    "india", "bangalore", "delhi", "mumbai", "hyderabad",
    "australia", "sydney", "melbourne",
    "singapore", "japan", "china", "ireland", "dublin",
    "netherlands", "amsterdam", "sweden", "france", "paris",
}


def _clean(text: str) -> str:
    """Strip markdown, emoji, flags from text."""
    text = re.sub(r'\*+([^*]+)\*+', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text, flags=re.UNICODE)
    text = re.sub(r':[a-z_]+:', '', text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _extract_url(text: str) -> Optional[str]:
    """Extract first https URL from markdown cell."""
    match = re.search(r'\[(?:[^\]]*)\]\((https?://[^\)]+)\)', text)
    if match:
        url = match.group(1)
        # Clean HTML artifacts
        url = url.split('"')[0].split("'")[0].split('<')[0].strip()
        if url.startswith('http'):
            return url
    match = re.search(r'https?://[^\s"'<>]+', text)
    if match:
        url = match.group(0).rstrip(').,')
        return url
    return None


def _parse_table(content: str) -> list[dict]:
    """Parse all markdown tables in README into row dicts."""
    jobs = []
    lines = content.split('\n')
    headers = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith('|'):
            in_table = False
            headers = []
            continue

        cells = [c.strip() for c in stripped.split('|')[1:-1]]
        if not cells:
            continue

        # Separator row
        if all(re.match(r'^[-:\s]+$', c) for c in cells if c):
            continue

        cleaned_cells = [_clean(c).lower() for c in cells]

        # Header row detection
        if not in_table:
            if any(h in cleaned_cells for h in ['company', 'role', 'job title', 'position', 'name']):
                headers = cleaned_cells
                in_table = True
            continue

        if len(cells) < 2:
            continue

        row = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                row[headers[i]] = cell
        jobs.append(row)

    return jobs


def _row_to_job(row: dict, repo_type: str) -> Optional[dict]:
    """Convert a table row to a job dict."""
    # Company
    company = None
    for k in ['company', 'company name', 'name']:
        if k in row:
            v = _clean(row[k])
            if len(v) > 1:
                company = v
                break
    if not company:
        return None

    # Title
    title = None
    for k in ['role', 'job title', 'position', 'title']:
        if k in row:
            v = _clean(row[k])
            if len(v) > 1:
                title = v
                break
    if not title:
        return None

    # Skip closed roles
    raw_str = str(row)
    if '🔒' in raw_str or '\\U0001f512' in raw_str:
        return None

    # Location
    location = ''
    for k in ['location', 'locations', 'city']:
        if k in row:
            location = _clean(row[k])
            break

    # Apply URL - search all cells
    apply_url = None
    for cell_val in row.values():
        url = _extract_url(cell_val)
        if url:
            apply_url = url
            break

    # Validate apply URL
    if apply_url:
        # Reject clearly wrong domains
        bad_domains = ['arch.co', 'arch.com', 'statefarm.com', 
                       'glassdoor.com/job-listing', 'google.com/search']
        if any(bad in apply_url.lower() for bad in bad_domains):
            apply_url = ""
        
        # Prefer direct ATS links over company homepage
        good_domains = ['greenhouse.io', 'lever.co', 'ashbyhq.com', 
                        'workday.com', 'myworkdayjobs.com', 'linkedin.com/jobs',
                        'simplify.jobs', 'jobright.ai', 'careers.']
        has_good_link = any(good in apply_url.lower() for good in good_domains)
        # If URL is just company homepage (no path depth), deprioritize
        if not has_good_link and apply_url.count('/') <= 3:
            apply_url = ""

    return {
        "company": company,
        "title": title,
        "location": location,
        "apply_url": apply_url or "",
        "type": repo_type,
    }


class GitHubJobsAdapter(JobSourceAdapter):
    """
    Fetches jobs from 7 community GitHub repos (new grad + internships).
    Filters results to match our monitored companies.
    Completely free, no API key required.
    """
    ATS_PROVIDER = "github_jobs"

    async def fetch_all_jobs(self, company_names: set[str]) -> list[NormalizedJob]:
        """Fetch from all repos and filter to our target companies."""
        all_raw = []

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for repo in GITHUB_REPOS:
                try:
                    r = await client.get(repo["url"], headers={"User-Agent": "CareerRadar/1.0"})
                    if r.status_code != 200:
                        logger.warning("GitHub [%s]: HTTP %d", repo["name"], r.status_code)
                        continue

                    rows = _parse_table(r.text)
                    count = 0
                    for row in rows:
                        job = _row_to_job(row, repo["type"])
                        if job:
                            all_raw.append(job)
                            count += 1
                    logger.info("GitHub [%s]: %d jobs parsed", repo["name"], count)

                except Exception as e:
                    logger.warning("GitHub [%s] error: %s", repo["name"], e)

        if not all_raw:
            raise AdapterEmpty()

        # Build fuzzy company lookup
        company_lower = {c.lower().strip(): c for c in company_names}

        normalized = []
        seen_ids = set()

        for raw in all_raw:
            raw_co = raw["company"].lower().strip()

            # Match to our companies
            matched = None
            if raw_co in company_lower:
                matched = company_lower[raw_co]
            else:
                for db_co_lower, db_co in company_lower.items():
                    if raw_co in db_co_lower or db_co_lower in raw_co:
                        matched = db_co
                        break

            if not matched:
                continue

            # Skip international locations
            loc_lower = raw["location"].lower()
            if any(s in loc_lower for s in INTL_SIGNALS):
                continue

            # Deduplicate
            dedup = raw["apply_url"] or f"{matched}:{raw['title']}"
            job_id = hashlib.md5(dedup.encode()).hexdigest()[:16]
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            # Clean description
            desc = f"{raw['type'].replace('_', ' ').title()} role — {raw['title']} at {matched}"
            desc = desc.encode('utf-8', 'ignore').decode('utf-8')

            normalized.append(NormalizedJob(
                external_job_id=f"gh_{job_id}",
                title=raw["title"],
                company_name=matched,
                location=raw["location"],
                is_remote="remote" in loc_lower,
                description=desc,
                application_url=raw["apply_url"],
                source_url=raw["apply_url"],
                posted_at=datetime.now(timezone.utc),
                employment_type="FULLTIME" if raw["type"] == "new_grad" else "INTERN",
                department=None,
                role_type="new_grad" if raw["type"] == "new_grad" else "internship",
            ))

        logger.info(
            "GitHubJobs: %d matches found from %d total raw jobs",
            len(normalized), len(all_raw)
        )
        return normalized

    async def fetch_jobs(self, company) -> list[NormalizedJob]:
        raise AdapterError("Use fetch_all_jobs() for GitHub adapter")
