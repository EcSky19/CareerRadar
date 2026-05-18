"""
ATS Provider Auto-Detector
===========================
Given a careers page URL, attempt to identify the ATS provider
before the user has to configure it manually.

Detection methods (in priority order):
  1. URL pattern matching (fastest, most reliable)
  2. HTTP redirect following (catches masked URLs)
  3. HTML source scanning for embedded widgets / script tags
  4. JSON-LD / structured data on the page
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from dataclasses import dataclass

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ATSDetectionResult:
    provider_name: str
    confidence_score: float
    detected_source_url: Optional[str]
    required_slug_or_token: Optional[str]
    warning_message: Optional[str]


# URL and HTML patterns for each ATS
_PATTERNS = {
    "greenhouse": {
        "url": [
            r"boards\.greenhouse\.io/([^/?#]+)",
            r"boards\.eu\.greenhouse\.io/([^/?#]+)",
        ],
        "html": [
            r"Grnhse\.Iframe\.load\('([^']+)'",
            r"greenhouse\.io/embed/job_board\?for=([^&\"']+)",
            r"greenhouse\.io",
        ],
        "token_group": 1,
    },
    "lever": {
        "url": [
            r"jobs\.lever\.co/([^/?#]+)",
        ],
        "html": [
            r"jobs\.lever\.co/([^/?#\"']+)",
            r"lever\.co",
        ],
        "token_group": 1,
    },
    "ashby": {
        "url": [
            r"jobs\.ashbyhq\.com/([^/?#]+)",
        ],
        "html": [
            r"jobs\.ashbyhq\.com/([^/?#\"']+)",
            r"ashbyhq\.com",
        ],
        "token_group": 1,
    },
    "workday": {
        "url": [
            r"([a-z0-9]+)\.wd\d+\.myworkdayjobs\.com",
            r"wd\d+\.myworkdayjobs\.com",
        ],
        "html": [
            r"myworkdayjobs\.com",
            r"workday\.com",
        ],
        "token_group": 1,
    },
    "icims": {
        "url": [
            r"careers\.([^.]+)\.icims\.com",
            r"([^.]+)-([^.]+)\.icims\.com",
        ],
        "html": [
            r"icims\.com",
            r"iCIMS",
        ],
        "token_group": None,
    },
    "smartrecruiters": {
        "url": [
            r"jobs\.smartrecruiters\.com/([^/?#]+)",
        ],
        "html": [
            r"smartrecruiters\.com",
        ],
        "token_group": 1,
    },
    "oracle_recruiting": {
        "url": [
            r"fa\.([^.]+)\.oraclecloud\.com",
            r"oraclecloud\.com.*recruit",
        ],
        "html": [
            r"oraclecloud\.com",
            r"Oracle Recruiting",
        ],
        "token_group": None,
    },
    "sap_successfactors": {
        "url": [
            r"([a-z0-9]+)\.successfactors\.com",
            r"successfactors\.com",
        ],
        "html": [
            r"successfactors\.com",
            r"SAP SuccessFactors",
        ],
        "token_group": None,
    },
}


async def detect_ats_provider(
    careers_url: str,
    company_name: Optional[str] = None,
) -> ATSDetectionResult:
    """
    Main entry point. Returns a detection result even on failure
    (falls back to provider='unknown').
    """
    if not careers_url:
        return ATSDetectionResult(
            provider_name="unknown",
            confidence_score=0.0,
            detected_source_url=None,
            required_slug_or_token=None,
            warning_message="No careers URL provided",
        )

    # Step 1: URL pattern
    result = _match_url_patterns(careers_url)
    if result and result.confidence_score >= 0.9:
        return result

    # Step 2: Fetch page and check HTML
    html, final_url = await _fetch_page(careers_url)
    if html:
        # Re-check URL patterns on the final (post-redirect) URL
        if final_url and final_url != careers_url:
            url_result = _match_url_patterns(final_url)
            if url_result and url_result.confidence_score >= 0.9:
                return url_result

        # HTML scan
        html_result = _match_html_patterns(html, final_url or careers_url)
        if html_result:
            return html_result

    return ATSDetectionResult(
        provider_name="unknown",
        confidence_score=0.0,
        detected_source_url=final_url or careers_url,
        required_slug_or_token=None,
        warning_message=(
            "Could not auto-detect ATS provider. "
            "Please select the provider and enter the board token manually."
        ),
    )


def _match_url_patterns(url: str) -> Optional[ATSDetectionResult]:
    for provider, config in _PATTERNS.items():
        for pattern in config["url"]:
            m = re.search(pattern, url, re.IGNORECASE)
            if m:
                token = m.group(config["token_group"]) if config["token_group"] else None
                source = _build_source_url(provider, token)
                return ATSDetectionResult(
                    provider_name=provider,
                    confidence_score=0.95,
                    detected_source_url=source or url,
                    required_slug_or_token=token,
                    warning_message=None,
                )
    return None


def _match_html_patterns(html: str, page_url: str) -> Optional[ATSDetectionResult]:
    for provider, config in _PATTERNS.items():
        for i, pattern in enumerate(config["html"]):
            m = re.search(pattern, html, re.IGNORECASE)
            if m:
                token = None
                if config["token_group"] and m.lastindex and m.lastindex >= config["token_group"]:
                    try:
                        token = m.group(config["token_group"])
                    except IndexError:
                        pass

                # Confidence decreases if we only found a vague HTML mention
                confidence = 0.85 if token else 0.60
                source = _build_source_url(provider, token)

                warning = None
                if not token:
                    warning = (
                        f"Detected {provider} from page HTML but could not extract "
                        "the board token. Please enter it manually in company settings."
                    )

                return ATSDetectionResult(
                    provider_name=provider,
                    confidence_score=confidence,
                    detected_source_url=source or page_url,
                    required_slug_or_token=token,
                    warning_message=warning,
                )
    return None


def _build_source_url(provider: str, token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    mapping = {
        "greenhouse": f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",
        "lever":      f"https://api.lever.co/v0/postings/{token}?mode=json",
        "ashby":      f"https://jobs.ashbyhq.com/{token}",
        "smartrecruiters": f"https://jobs.smartrecruiters.com/{token}",
    }
    return mapping.get(provider)


async def _fetch_page(url: str) -> tuple[Optional[str], Optional[str]]:
    """Fetch page HTML, return (html, final_url). Returns (None, None) on error."""
    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": settings.ingestion_user_agent},
        ) as client:
            resp = await client.get(url)
            return resp.text, str(resp.url)
    except Exception as exc:
        logger.warning("ATS detection fetch failed for %s: %s", url, exc)
        return None, None
