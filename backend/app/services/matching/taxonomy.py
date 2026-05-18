"""
Title Taxonomy
==============
Central reference for:
  1. Abbreviation / alias expansion (normalise_title)
  2. Per-category high-priority title sets
  3. Seniority penalty terms
  4. Role-type inference from title text

Used by both the matching engine and the title normalizer.
"""

from __future__ import annotations
import re
from functools import lru_cache

# =============================================================================
# 1. ABBREVIATION EXPANSION MAP
# =============================================================================

ABBREVIATIONS: dict[str, str] = {
    r"\bswe\b":     "software engineer",
    r"\bsde\b":     "software development engineer",
    r"\bml\b":      "machine learning",
    r"\bai\b":      "artificial intelligence",
    r"\bgenai\b":   "generative ai",
    r"\bllm\b":     "large language model",
    r"\bsre\b":     "site reliability engineer",
    r"\btpm\b":     "technical program manager",
    r"\bapm\b":     "associate product manager",
    r"\bqe\b":      "quality engineer",
    r"\bqa\b":      "quality assurance",
    r"\bbi\b":      "business intelligence",
    r"\bde\b":      "data engineer",
    r"\bds\b":      "data scientist",
    r"\bqr\b":      "quantitative researcher",
    r"\bqd\b":      "quantitative developer",
    r"\bstrat\b":   "strategist",
    r"\bseceng\b":  "security engineer",
    r"\bhft\b":     "high-frequency trading",
    r"\boms\b":     "order management system",
    r"\bems\b":     "execution management system",
}

# Early-career wording synonyms (for role type detection)
NEW_GRAD_SYNONYMS = {
    "new grad", "new graduate", "recent graduate", "university graduate",
    "college graduate", "early career", "early careers", "campus",
    "university grad", "college grad",
}
INTERN_SYNONYMS = {
    "intern", "internship", "summer intern", "summer analyst", "co-op", "coop",
}

# =============================================================================
# 2. SENIORITY PENALTY TERMS
# =============================================================================

SENIOR_PENALTY_EXACT = {
    "senior", "sr", "staff", "principal", "lead", "manager",
    "director", "vp", "vice president", "head of", "architect",
    "distinguished", "fellow", "executive",
}

EXPERIENCE_PENALTY_PATTERNS = [
    r"\b(\d+)\+?\s+years?\b",     # "5+ years", "7 years"
]

# Years threshold above which we apply heavy penalty for intern/new-grad profiles
INTERN_YEARS_THRESHOLD    = 1
NEW_GRAD_YEARS_THRESHOLD  = 2
FULLTIME_YEARS_THRESHOLD  = 5


# =============================================================================
# 3. ROLE-TYPE INFERENCE FROM TITLE / DESCRIPTION
# =============================================================================

def infer_role_type(title: str, description: str = "") -> str | None:
    """
    Best-effort role type inference from job title and description text.
    Returns one of: internship | new_grad | full_time | contract | None
    """
    text = (title + " " + description[:500]).lower()

    if any(s in text for s in INTERN_SYNONYMS):
        return "internship"

    if any(s in text for s in NEW_GRAD_SYNONYMS):
        return "new_grad"

    contract_signals = ["contract", "contractor", "temp", "temporary", "freelance"]
    if any(s in text for s in contract_signals):
        return "contract"

    return None


def extract_required_years(description: str) -> int:
    """
    Extract the maximum years of experience requirement from a job description.
    Returns 0 if none found.
    """
    matches = re.findall(r"(\d+)\+?\s*(?:-\s*\d+\s*)?years?", description.lower())
    years = [int(m) for m in matches if 1 <= int(m) <= 30]
    return max(years, default=0)


# =============================================================================
# 4. PER-CATEGORY HIGH-PRIORITY TITLE SETS
# =============================================================================
# Each set contains lowercased canonical terms that appear in high-priority
# titles for that company category. The matching engine checks whether the
# normalized job title contains any of these terms.

CATEGORY_TITLE_SIGNALS: dict[str, set[str]] = {

    "big_tech": {
        "software engineer", "sde", "machine learning engineer", "ml engineer",
        "applied scientist", "site reliability engineer", "sre", "data engineer",
        "ai engineer", "platform engineer", "infrastructure engineer",
    },

    "nasdaq_100": {
        "software engineer", "sde", "machine learning engineer", "ml engineer",
        "applied scientist", "sre", "data engineer", "ai engineer",
        "platform engineer", "infrastructure engineer", "cloud engineer",
        "security engineer", "research engineer",
    },

    "saas": {
        "software engineer", "backend engineer", "full stack engineer",
        "product engineer", "platform engineer", "data engineer",
        "ai engineer", "security engineer",
    },

    "software_company": {
        "software engineer", "backend engineer", "full stack engineer",
        "frontend engineer", "platform engineer", "data engineer",
        "solutions engineer", "forward deployed engineer",
    },

    "data_company": {
        "data engineer", "analytics engineer", "data platform engineer",
        "data infrastructure engineer", "etl engineer", "data pipeline engineer",
        "data scientist", "machine learning engineer", "market data engineer",
    },

    "financial_technology": {
        "software engineer", "backend engineer", "full stack engineer",
        "payments engineer", "risk engineer", "fraud engineer",
        "data engineer", "machine learning engineer",
    },

    "banking_technology": {
        "technology analyst", "software engineering analyst",
        "engineering analyst", "quantitative analyst", "quantitative developer",
        "risk technology analyst", "data science analyst", "data engineer",
        "trading technology analyst",
    },

    "capital_markets_technology": {
        "technology analyst", "trading technology analyst",
        "quantitative analyst", "risk technology analyst",
        "software engineering analyst",
    },

    "exchange_market_infra": {
        "software engineer", "trading systems engineer", "market data engineer",
        "low latency software engineer", "c++ software engineer",
        "matching engine engineer",
    },

    "financial_data_provider": {
        "data engineer", "financial data engineer", "market data engineer",
        "software engineer", "quantitative developer", "analytics engineer",
    },

    "private_equity": {
        "investment technology analyst", "data engineer", "data science analyst",
        "portfolio analytics analyst", "technology analyst",
        "automation engineer", "ai engineer", "machine learning engineer",
        "business intelligence analyst",
    },

    "alt_asset_management": {
        "investment technology analyst", "data engineer", "data scientist",
        "portfolio analytics engineer", "risk analytics engineer",
        "machine learning engineer",
    },

    "hedge_fund": {
        "quantitative developer", "quant developer", "research engineer",
        "trading systems engineer", "data engineer", "machine learning engineer",
        "software engineer", "investment technology analyst",
    },

    "multi_manager_hedge_fund": {
        "quantitative developer", "quant developer", "data engineer",
        "machine learning engineer", "trading systems engineer",
        "portfolio analytics engineer",
    },

    "systematic_investing": {
        "quantitative developer", "systematic research engineer",
        "data engineer", "machine learning engineer",
        "portfolio analytics engineer",
    },

    "quant_trading": {
        "quantitative developer", "quant developer", "quantitative researcher",
        "trading systems engineer", "data engineer",
    },

    "algorithmic_trading": {
        "quantitative developer", "algorithmic trading developer",
        "trading systems engineer", "data engineer", "low latency engineer",
    },

    "high_frequency_trading": {
        "quantitative developer", "hft developer", "low latency software engineer",
        "c++ software engineer", "trading systems engineer",
        "market data engineer", "execution engineer",
    },

    "proprietary_trading": {
        "quantitative developer", "quant developer", "trading systems engineer",
        "market data engineer", "quantitative researcher",
    },

    "market_making": {
        "quantitative developer", "trading systems engineer",
        "market data engineer", "software engineer",
    },
}


# =============================================================================
# 5. TITLE NORMALIZER
# =============================================================================

def normalise_title(raw_title: str) -> str:
    """
    Lowercase and expand abbreviations in a job title.
    Returns a normalised string suitable for fuzzy matching.
    """
    title = raw_title.lower().strip()
    for pattern, replacement in ABBREVIATIONS.items():
        title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)
    # Strip punctuation except hyphens and slashes
    title = re.sub(r"[^\w\s\-/]", " ", title)
    return re.sub(r"\s+", " ", title).strip()


@lru_cache(maxsize=2000)
def normalise_title_cached(raw_title: str) -> str:
    return normalise_title(raw_title)


# =============================================================================
# 6. DOMAIN KEYWORDS BY CATEGORY
# =============================================================================
# Additional domain-specific signals checked in the job description.

DOMAIN_SIGNALS: dict[str, set[str]] = {
    "banking_technology": {
        "python", "java", "c++", "sql", "cloud", "data engineering",
        "machine learning", "trading systems", "market data", "risk technology",
        "apis", "platform engineering", "cybersecurity", "infrastructure",
        "application development",
    },
    "private_equity": {
        "python", "sql", "data analytics", "data engineering", "automation",
        "business intelligence", "machine learning", "ai", "cloud", "apis",
        "portfolio analytics", "investment systems", "reporting systems",
        "power bi", "tableau", "snowflake", "databricks", "alteryx",
    },
    "hedge_fund": {
        "python", "c++", "java", "sql", "linux", "market data",
        "trading systems", "portfolio construction", "risk models",
        "quantitative research", "systematic investing", "backtesting",
        "time series", "statistical modeling", "machine learning",
        "low latency", "alternative data",
    },
    "high_frequency_trading": {
        "c++", "python", "linux", "networking", "multithreading",
        "low latency", "kernel bypass", "lock-free", "market data",
        "order book", "exchange connectivity", "fix protocol",
        "algorithmic trading", "backtesting",
    },
}
