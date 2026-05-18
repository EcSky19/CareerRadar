"""
Matching Engine
===============
Compares every newly discovered job against all active target profiles
for the companies' owner, producing scored JobMatch records.

Scoring model (total 100 points):
  title_score       25  — normalized title overlap with desired_titles
  role_type_score   15  — role type matches profile role_types list
  location_score    10  — location matches desired_locations
  keyword_score     15  — description/title keyword overlap
  category_score    10  — company's categories match profile's category filters
  domain_score      10  — domain-specific technical signals in description
  priority_score     5  — company priority (high/medium/low)
  freshness_score    5  — how recently the job was posted
  campus_score       5  — intern/new-grad relevance signals

Penalties applied before final clamp to [0, 100]:
  - Senior/Staff/Principal/Lead in title:     -40
  - Director/VP/Head/Manager in title:        -50
  - 5+ years required:                        -35
  - 3+ years required (intern/new-grad user): -25
  - Exclusion keyword found:                  -20 per term (max -40)
  - Location mismatch (when strict):          -15
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Optional

from app.services.matching.taxonomy import (
    normalise_title_cached,
    CATEGORY_TITLE_SIGNALS,
    DOMAIN_SIGNALS,
    SENIOR_PENALTY_EXACT,
    extract_required_years,
    infer_role_type,
    NEW_GRAD_SYNONYMS,
    INTERN_SYNONYMS,
)

logger = logging.getLogger(__name__)


# =============================================================================
# OUTPUT DATACLASS
# =============================================================================

@dataclass
class MatchResult:
    job_id: object               # UUID
    target_profile_id: object    # UUID
    user_id: object              # UUID

    match_score: int = 0

    # Sub-scores
    title_score: int = 0
    role_type_score: int = 0
    location_score: int = 0
    keyword_score: int = 0
    category_score: int = 0
    domain_score: int = 0
    priority_score: int = 0
    freshness_score: int = 0
    campus_score: int = 0

    # Evidence arrays
    matched_title_terms: list[str]       = field(default_factory=list)
    matched_keywords: list[str]          = field(default_factory=list)
    matched_location_terms: list[str]    = field(default_factory=list)
    matched_company_categories: list[str]= field(default_factory=list)
    excluded_terms_found: list[str]      = field(default_factory=list)
    technical_signals_found: list[str]   = field(default_factory=list)
    domain_signals_found: list[str]      = field(default_factory=list)

    match_reason: str = ""
    should_alert: bool = False

    total_penalty: int = 0
    penalty_reasons: list[str] = field(default_factory=list)


# =============================================================================
# ENGINE
# =============================================================================

class MatchingEngine:

    def score(
        self,
        job,                # SQLAlchemy Job ORM instance
        profile,            # SQLAlchemy TargetProfile ORM instance
        company,            # SQLAlchemy Company ORM instance
        company_category_slugs: list[str],  # slugs from category_assignments
    ) -> MatchResult:
        """
        Score a single (job, profile) pair. Returns a MatchResult.
        """
        result = MatchResult(
            job_id=job.id,
            target_profile_id=profile.id,
            user_id=profile.user_id,
        )

        norm_title = normalise_title_cached(job.title)
        description = (job.description or "").lower()
        title_lower = job.title.lower()
        full_text = f"{title_lower} {description}"

        # ── 1. Title score (25 pts) ────────────────────────────────────────────
        result.title_score, result.matched_title_terms = self._score_title(
            norm_title, title_lower, profile.desired_titles, company_category_slugs
        )

        # ── 2. Role type score (15 pts) ────────────────────────────────────────
        result.role_type_score = self._score_role_type(
            job, profile.role_types, full_text
        )

        # ── 3. Location score (10 pts) ─────────────────────────────────────────
        result.location_score, result.matched_location_terms = self._score_location(
            job.location or "", profile.desired_locations, profile.remote_preference
        )

        # ── 4. Keyword score (15 pts) ─────────────────────────────────────────
        result.keyword_score, result.matched_keywords = self._score_keywords(
            full_text, profile.desired_keywords
        )

        # ── 5. Category score (10 pts) ─────────────────────────────────────────
        result.category_score, result.matched_company_categories = self._score_categories(
            company_category_slugs, profile
        )

        # ── 6. Domain score (10 pts) ──────────────────────────────────────────
        result.domain_score, result.domain_signals_found = self._score_domain(
            full_text, company_category_slugs
        )

        # ── 7. Priority score (5 pts) ─────────────────────────────────────────
        result.priority_score = {"high": 5, "medium": 3, "low": 1}.get(
            company.priority, 3
        )

        # ── 8. Freshness score (5 pts) ────────────────────────────────────────
        result.freshness_score = self._score_freshness(job.first_seen_at)

        # ── 9. Campus score (5 pts) ───────────────────────────────────────────
        result.campus_score = self._score_campus(full_text, profile.role_types)

        # ── Subtotal ──────────────────────────────────────────────────────────
        subtotal = (
            result.title_score + result.role_type_score + result.location_score
            + result.keyword_score + result.category_score + result.domain_score
            + result.priority_score + result.freshness_score + result.campus_score
        )

        # ── 10. Exclusion keywords ────────────────────────────────────────────
        exclusion_penalty, result.excluded_terms_found = self._exclusion_penalty(
            full_text, profile.excluded_keywords
        )

        # ── 11. Seniority and experience penalties ─────────────────────────────
        seniority_penalty, seniority_reasons = self._seniority_penalty(
            title_lower, description, profile.role_types
        )

        result.total_penalty = exclusion_penalty + seniority_penalty
        result.penalty_reasons = seniority_reasons

        # ── Finance / description signal gate ────────────────────────────────
        # For banking, PE, and HF categories with vague titles,
        # require at least one technical signal in the description.
        if self._requires_technical_gate(title_lower, company_category_slugs):
            if not self._has_technical_signal(full_text):
                result.match_score = 0
                result.match_reason = (
                    f"'{job.title}' did not match: title is vague for a "
                    f"{', '.join(company_category_slugs)} company and description "
                    "contains no technical signals (Python, Java, SQL, ML, cloud, etc.)"
                )
                result.should_alert = False
                return result

        # ── Final score ────────────────────────────────────────────────────────
        raw_score = subtotal - result.total_penalty
        result.match_score = max(0, min(100, raw_score))

        # ── Alert threshold ────────────────────────────────────────────────────
        result.should_alert = (
            result.match_score >= profile.minimum_match_score
            and profile.alerts_enabled
        )

        result.match_reason = self._build_reason(result, job)
        return result

    # ==========================================================================
    # SUB-SCORERS
    # ==========================================================================

    def _score_title(
        self,
        norm_title: str,
        title_lower: str,
        desired_titles: list[str],
        category_slugs: list[str],
    ) -> tuple[int, list[str]]:
        matched = []

        # Check user's explicit desired titles
        for desired in desired_titles:
            d = desired.lower().strip()
            if d in norm_title or d in title_lower:
                matched.append(desired)

        # Check per-category high-priority title signals
        for slug in category_slugs:
            signals = CATEGORY_TITLE_SIGNALS.get(slug, set())
            for signal in signals:
                if signal in norm_title and signal not in matched:
                    matched.append(signal)

        if not matched:
            return 0, []

        # Score: full 25 for exact match of user's desired title, 15 for category signal
        explicit_match = any(
            d.lower().strip() in norm_title or d.lower().strip() in title_lower
            for d in desired_titles
        )
        score = 25 if explicit_match else 15
        return score, list(set(matched))

    def _score_role_type(
        self,
        job,
        profile_role_types: list[str],
        full_text: str,
    ) -> int:
        if not profile_role_types:
            return 8   # No preference → neutral

        job_role_type = job.role_type or infer_role_type(job.title, full_text)

        if job_role_type and job_role_type in profile_role_types:
            return 15
        if not job_role_type:
            return 5   # Unknown — small credit
        return 0

    def _score_location(
        self,
        job_location: str,
        desired_locations: list[str],
        remote_pref: str,
    ) -> tuple[int, list[str]]:
        if not desired_locations and remote_pref == "any":
            return 10, []

        job_loc_lower = job_location.lower()
        matched = []

        if remote_pref in ("remote", "any") and any(
            w in job_loc_lower for w in ("remote", "anywhere", "distributed")
        ):
            return 10, ["remote"]

        for loc in desired_locations:
            if loc.lower() in job_loc_lower or job_loc_lower in loc.lower():
                matched.append(loc)

        if matched:
            return 10, matched

        if not desired_locations:
            return 5, []

        return 0, []

    def _score_keywords(
        self,
        full_text: str,
        desired_keywords: list[str],
    ) -> tuple[int, list[str]]:
        if not desired_keywords:
            return 7, []

        matched = [kw for kw in desired_keywords if kw.lower() in full_text]
        if not matched:
            return 0, []

        ratio = len(matched) / len(desired_keywords)
        score = min(15, round(ratio * 15))
        return score, matched

    def _score_categories(
        self,
        company_category_slugs: list[str],
        profile,
    ) -> tuple[int, list[str]]:
        included_ids = {
            str(f.category_id)
            for f in (profile.category_filters or [])
            if f.filter_type == "included"
        }
        excluded_ids = {
            str(f.category_id)
            for f in (profile.category_filters or [])
            if f.filter_type == "excluded"
        }

        if not included_ids and not excluded_ids:
            return 5, []   # No category preference → neutral

        matched = [s for s in company_category_slugs if s in included_ids]
        if matched:
            return 10, matched
        if any(s in excluded_ids for s in company_category_slugs):
            return 0, []
        return 3, []

    def _score_domain(
        self,
        full_text: str,
        category_slugs: list[str],
    ) -> tuple[int, list[str]]:
        signals_found = []
        for slug in category_slugs:
            domain_kws = DOMAIN_SIGNALS.get(slug, set())
            for kw in domain_kws:
                if kw in full_text and kw not in signals_found:
                    signals_found.append(kw)

        if not signals_found:
            return 0, []

        score = min(10, len(signals_found) * 2)
        return score, signals_found[:10]

    @staticmethod
    def _score_freshness(first_seen_at) -> int:
        if first_seen_at is None:
            return 3
        try:
            now = datetime.now(timezone.utc)
            if hasattr(first_seen_at, "tzinfo") and first_seen_at.tzinfo is None:
                first_seen_at = first_seen_at.replace(tzinfo=timezone.utc)
            age_days = (now - first_seen_at).days
            if age_days <= 1:
                return 5
            if age_days <= 7:
                return 4
            if age_days <= 14:
                return 3
            if age_days <= 30:
                return 2
            return 1
        except Exception:
            return 2

    @staticmethod
    def _score_campus(full_text: str, role_types: list[str]) -> int:
        wants_campus = bool(
            {"internship", "new_grad", "coop"} & set(role_types)
        )
        has_campus_signal = any(
            s in full_text
            for s in [*INTERN_SYNONYMS, *NEW_GRAD_SYNONYMS,
                      "campus recruiting", "university recruiting",
                      "college recruiting", "early career", "rotational"]
        )
        if wants_campus and has_campus_signal:
            return 5
        if wants_campus and not has_campus_signal:
            return 0
        return 2

    @staticmethod
    def _exclusion_penalty(
        full_text: str,
        excluded_keywords: list[str],
    ) -> tuple[int, list[str]]:
        found = [kw for kw in excluded_keywords if kw.lower() in full_text]
        penalty = min(40, len(found) * 20)
        return penalty, found

    @staticmethod
    def _seniority_penalty(
        title_lower: str,
        description: str,
        role_types: list[str],
    ) -> tuple[int, list[str]]:
        penalty = 0
        reasons = []

        words = set(re.split(r"\W+", title_lower))
        for term in SENIOR_PENALTY_EXACT:
            if term in words or term in title_lower:
                penalty += 40
                reasons.append(f"Seniority term in title: '{term}'")
                break

        required_years = extract_required_years(description)
        is_early_career = bool({"internship", "new_grad", "coop"} & set(role_types))

        if required_years >= 5:
            penalty += 35
            reasons.append(f"{required_years}+ years required")
        elif required_years >= 3 and is_early_career:
            penalty += 25
            reasons.append(f"{required_years}+ years required (early-career profile)")

        return min(penalty, 60), reasons   # cap penalty contribution

    @staticmethod
    def _requires_technical_gate(title_lower: str, category_slugs: list[str]) -> bool:
        """
        Returns True if this (title, company-category) combination requires
        a technical signal in the description before matching.
        """
        gated_categories = {
            "banking_technology", "capital_markets_technology",
            "private_equity", "alt_asset_management",
            "hedge_fund", "multi_manager_hedge_fund",
        }
        if not any(s in gated_categories for s in category_slugs):
            return False
        # Only gate vague single-word titles
        vague_titles = {"analyst", "associate", "specialist", "officer",
                        "manager", "consultant", "strategist"}
        words = set(re.split(r"\W+", title_lower))
        return bool(words & vague_titles) and len(words) <= 3

    @staticmethod
    def _has_technical_signal(full_text: str) -> bool:
        tech_signals = {
            "python", "java", "c++", "javascript", "typescript", "sql", "go",
            "rust", "scala", "software engineer", "software development",
            "application development", "cloud", "data engineering",
            "machine learning", "trading systems", "market data", "risk technology",
            "automation", "platform engineering", "cybersecurity", "infrastructure",
            "data pipeline", "api", "kubernetes", "docker", "aws", "azure", "gcp",
        }
        return any(s in full_text for s in tech_signals)

    @staticmethod
    def _build_reason(result: MatchResult, job) -> str:
        parts = []
        if result.matched_title_terms:
            parts.append(f"Title matched: {', '.join(result.matched_title_terms[:3])}")
        if result.matched_keywords:
            parts.append(f"Keywords: {', '.join(result.matched_keywords[:4])}")
        if result.domain_signals_found:
            parts.append(f"Domain signals: {', '.join(result.domain_signals_found[:3])}")
        if result.matched_location_terms:
            parts.append(f"Location: {', '.join(result.matched_location_terms)}")
        if result.penalty_reasons:
            parts.append(f"Penalties: {'; '.join(result.penalty_reasons)}")
        if result.excluded_terms_found:
            parts.append(f"Exclusions hit: {', '.join(result.excluded_terms_found)}")

        base = ". ".join(parts) if parts else "No strong signals matched."
        return f"{job.title} at {job.company_name} — score {result.match_score}/100. {base}"
