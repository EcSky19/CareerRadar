"""
Resume Optimizer
================
AI-powered resume improvement using the Claude API.

Responsibilities:
  1. Rewrite weak bullets with stronger verbs, metrics scaffolding, and keyword insertion
  2. Suggest missing keyword placements with natural wording
  3. Generate a complete optimized resume version for a specific job

Honesty rules:
  - NEVER fabricate experience, companies, dates, or credentials
  - NEVER invent specific metrics — use [X%] / [X] placeholders that the
    user must replace with their real numbers
  - All placeholders are flagged with requires_verification=True
  - The optimizer only rearranges and strengthens language, never adds
    fictional work history
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

import httpx

from app.services.resume.analyzer import AnalysisResult, BulletDiagnosis
from app.services.resume.parser import ParsedResume

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL   = "claude-sonnet-4-20250514"
MAX_TOKENS     = 1500

# Placeholder regex — any [X], [X%], [NUMBER], [METRIC] pattern
PLACEHOLDER_RE = re.compile(r"\[([A-Z%#0-9][A-Z0-9%#\s]*)\]")


# =============================================================================
# BULLET REWRITER
# =============================================================================

async def rewrite_bullets(
    weak_bullets: list[BulletDiagnosis],
    job_description: str,
    missing_keywords: list[str],
    max_bullets: int = 6,
) -> list[BulletDiagnosis]:
    """
    Rewrite the top weak bullets using Claude.
    Returns updated BulletDiagnosis objects with improved_bullet, why_stronger,
    keywords_added, metrics_added, and requires_verification fields filled in.
    """
    bullets_to_rewrite = weak_bullets[:max_bullets]
    if not bullets_to_rewrite:
        return []

    prompt = _build_bullet_rewrite_prompt(bullets_to_rewrite, job_description, missing_keywords)

    raw = await _call_claude(prompt)
    if not raw:
        return bullets_to_rewrite   # return originals on failure

    return _parse_bullet_rewrites(raw, bullets_to_rewrite)


async def optimize_full_resume(
    resume: ParsedResume,
    analysis: AnalysisResult,
    job_description: str,
    job_title: str,
    company_name: str,
) -> dict:
    """
    Generate a full optimized resume as structured JSON.
    Returns the same shape as ParsedResume.to_json() with improvements applied.
    """
    prompt = _build_full_resume_prompt(resume, analysis, job_description, job_title, company_name)
    raw = await _call_claude(prompt, max_tokens=2000)
    if not raw:
        return resume.to_json()

    try:
        # Strip markdown fences if present
        clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        result = json.loads(clean)
        # Verify it has the expected shape
        if not isinstance(result, dict) or "experience" not in result:
            logger.warning("Optimizer returned unexpected JSON shape, using original")
            return resume.to_json()
        return result
    except (json.JSONDecodeError, Exception) as exc:
        logger.warning("Optimizer JSON parse failed: %s", exc)
        return resume.to_json()


# =============================================================================
# PROMPT BUILDERS
# =============================================================================

def _build_bullet_rewrite_prompt(
    bullets: list[BulletDiagnosis],
    job_description: str,
    missing_keywords: list[str],
) -> str:
    bullets_json = json.dumps(
        [{"id": i, "original": b.original, "issues": b.issues}
         for i, b in enumerate(bullets)],
        indent=2
    )
    keywords_str = ", ".join(missing_keywords[:12]) if missing_keywords else "none identified"

    jd_excerpt = job_description[:1200] if job_description else ""

    return f"""You are a professional resume writer helping a job seeker improve their resume bullets.

JOB DESCRIPTION EXCERPT:
{jd_excerpt}

MISSING KEYWORDS TO INCORPORATE (only if they genuinely fit the experience):
{keywords_str}

BULLETS TO IMPROVE:
{bullets_json}

RULES — READ CAREFULLY:
1. Rewrite each bullet to start with a strong action verb (Built, Engineered, Designed, Reduced, Optimized, Deployed, Automated, etc.)
2. Move technology/keywords earlier in the bullet — within the first 10 words
3. Add quantified impact where plausible — use [X%], [X], [N users], [N ms] as placeholders the user will fill in
4. Show OUTCOME not just task — what changed because of this work?
5. NEVER fabricate companies, dates, technologies, or experience the user didn't list
6. NEVER add skills not present in the original bullet unless adding a missing keyword that logically applies to described work
7. Keep each bullet to 1–2 lines (under 25 words ideally)
8. keywords_added: list only keywords you actually inserted in the improved text
9. metrics_added: list only [X%] / [X] / [N] style placeholder strings you added

Respond with ONLY valid JSON, no preamble, no markdown fences:
{{
  "rewrites": [
    {{
      "id": 0,
      "improved": "...",
      "why_stronger": "...",
      "keywords_added": ["keyword1"],
      "metrics_added": ["[X%]"]
    }}
  ]
}}"""


def _build_full_resume_prompt(
    resume: ParsedResume,
    analysis: AnalysisResult,
    job_description: str,
    job_title: str,
    company_name: str,
) -> str:
    resume_json = json.dumps(resume.to_json(), indent=2)
    missing_required = ", ".join(analysis.required_missing[:10])
    missing_preferred = ", ".join(analysis.preferred_missing[:8])
    jd_excerpt = job_description[:1500]

    return f"""You are an expert resume writer. Optimize the following resume for the target role.

TARGET ROLE: {job_title} at {company_name}

JOB DESCRIPTION EXCERPT:
{jd_excerpt}

MISSING REQUIRED KEYWORDS: {missing_required}
MISSING PREFERRED KEYWORDS: {missing_preferred}

CURRENT RESUME (JSON):
{resume_json}

OPTIMIZATION INSTRUCTIONS:
1. Rewrite weak bullets (no metric, weak verb, task-not-outcome) using strong action verbs and outcomes
2. Add missing required keywords to the skills section and relevant bullets where they genuinely fit
3. Move technology mentions earlier in bullets
4. Use [X%], [X users], [N ms] placeholders for metrics — the user will fill in real numbers
5. Do NOT fabricate companies, roles, dates, certifications, or experience
6. Do NOT add skills the user clearly doesn't have based on their current resume
7. Keep all original section structure — return the same JSON shape
8. The skills list should be sorted: languages first, then frameworks, then tools

Return ONLY valid JSON in the same structure as the input resume JSON, with improvements applied.
No markdown fences, no explanation, just JSON."""


# =============================================================================
# CLAUDE API CALLER
# =============================================================================

async def _call_claude(prompt: str, max_tokens: int = MAX_TOKENS) -> Optional[str]:
    """
    Call the Anthropic Claude API with a single-turn prompt.
    Returns the text content or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                CLAUDE_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                },
            )

        if resp.status_code != 200:
            logger.error("Claude API error %d: %s", resp.status_code, resp.text[:300])
            return None

        data = resp.json()
        content_blocks = data.get("content", [])
        text_blocks = [b["text"] for b in content_blocks if b.get("type") == "text"]
        return "\n".join(text_blocks) if text_blocks else None

    except httpx.RequestError as exc:
        logger.error("Claude API network error: %s", exc)
        return None
    except Exception as exc:
        logger.exception("Unexpected error calling Claude API: %s", exc)
        return None


# =============================================================================
# RESPONSE PARSERS
# =============================================================================

def _parse_bullet_rewrites(
    raw: str,
    originals: list[BulletDiagnosis],
) -> list[BulletDiagnosis]:
    try:
        clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        data  = json.loads(clean)
        rewrites = {r["id"]: r for r in data.get("rewrites", [])}
    except Exception as exc:
        logger.warning("Failed to parse bullet rewrite response: %s", exc)
        return originals

    result = []
    for i, original in enumerate(originals):
        rw = rewrites.get(i)
        if not rw:
            result.append(original)
            continue

        improved      = rw.get("improved", original.original)
        has_placeholder = bool(PLACEHOLDER_RE.search(improved))

        original.improved_bullet    = improved
        original.why_stronger       = rw.get("why_stronger", "")
        original.keywords_added     = rw.get("keywords_added", [])
        original.metrics_added      = rw.get("metrics_added", [])
        original.requires_verification = has_placeholder
        original.verification_note  = (
            "Replace all [X] / [X%] placeholders with your actual measured values."
            if has_placeholder else ""
        )
        result.append(original)

    return result
