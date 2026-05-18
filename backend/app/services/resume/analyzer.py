"""
Resume Analyzer
===============
Given a parsed resume and a job description text, produces:
  - Overall match score
  - ATS keyword coverage breakdown
  - Recruiter 6-second scan verdict
  - Missing keyword list (prioritized)
  - Weak bullet diagnosis
  - Suggested bullet improvements
  - ATS formatting warnings

This module contains the algorithmic analysis.
The AI-powered suggestion generation lives in optimizer.py.

HONESTY RULE:
  This module never fabricates keywords, metrics, experience, or credentials.
  Placeholder metrics (e.g. [X%]) are always explicitly flagged as requiring
  user verification before use.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

from app.services.resume.parser import ParsedResume

logger = logging.getLogger(__name__)


# =============================================================================
# JOB DESCRIPTION KEYWORD EXTRACTOR
# =============================================================================

# High-signal ATS keywords by category
_LANG_PATTERNS = re.compile(
    r"\b(python|java|c\+\+|javascript|typescript|sql|go|rust|scala|kotlin|swift|c#|r\b|matlab)\b",
    re.I
)
_FRAMEWORK_PATTERNS = re.compile(
    r"\b(react|next\.?js|node\.?js|fastapi|flask|django|spring\s*boot|graphql|"
    r"pytorch|tensorflow|scikit[\-\s]learn|hugging\s*face|langchain|"
    r"spark|kafka|airflow|snowflake|databricks|redis|kubernetes|docker|"
    r"aws|azure|gcp|terraform|ci/?cd)\b",
    re.I
)
_DOMAIN_PATTERNS = re.compile(
    r"\b(machine\s*learning|deep\s*learning|nlp|computer\s*vision|"
    r"data\s*engineering|data\s*pipeline|etl|trading\s*systems|"
    r"market\s*data|quantitative|low\s*latency|microservices|"
    r"distributed\s*systems|site\s*reliability|devops|cybersecurity|"
    r"reinforcement\s*learning|generative\s*ai|large\s*language|llm|"
    r"backtesting|portfolio\s*analytics)\b",
    re.I
)

# Weak verb patterns
_WEAK_VERBS = {
    "worked on", "helped with", "assisted", "involved in", "participated",
    "responsible for", "tasked with", "contributed to", "supported",
    "used", "utilized", "dealt with", "handled",
}

# Strong opening verbs
_STRONG_VERBS = {
    "built", "designed", "implemented", "developed", "engineered", "architected",
    "optimized", "reduced", "improved", "increased", "automated", "deployed",
    "led", "launched", "created", "migrated", "refactored", "scaled", "shipped",
    "delivered", "streamlined", "established", "integrated",
}

# ATS formatting anti-patterns
_FORMATTING_WARNINGS = {
    "two_column": "Two-column layout detected — some ATS systems parse these out of order.",
    "no_dates": "One or more experience entries appear to be missing dates.",
    "no_location": "No location found on resume — some ATS systems filter by location.",
    "table_layout": "Possible table-based layout — tables may not parse correctly in all ATS systems.",
    "skill_bars": "Skill bars (e.g. proficiency percentages) are not parseable by ATS — use plain text skills.",
}


# =============================================================================
# OUTPUT DATACLASS
# =============================================================================

@dataclass
class BulletDiagnosis:
    original: str
    problem: str
    issues: list[str]      = field(default_factory=list)   # weak_verb, no_metric, vague, etc.
    improved: str          = ""
    why_stronger: str      = ""
    keywords_added: list[str] = field(default_factory=list)
    metrics_added: list[str]  = field(default_factory=list)
    requires_verification: bool = False
    verification_note: str = ""


@dataclass
class KeywordResult:
    keyword: str
    importance: str          = "preferred"   # required / preferred / nice_to_have
    found_in_resume: bool    = False
    current_location: str    = ""
    recommended_placement: str = ""
    suggested_wording: str   = ""


@dataclass
class AnalysisResult:
    overall_score: int              = 0
    ats_keyword_score: int          = 0
    recruiter_scan_score: int       = 0
    technical_depth_score: int      = 0
    quantified_impact_score: int    = 0
    formatting_score: int           = 0

    recruiter_verdict: str          = "maybe"
    recruiter_6s_impression: str    = ""
    recruiter_main_reason: str      = ""
    recruiter_biggest_weakness: str = ""
    recruiter_fastest_fix: str      = ""

    keywords: list[KeywordResult]         = field(default_factory=list)
    required_missing: list[str]           = field(default_factory=list)
    preferred_missing: list[str]          = field(default_factory=list)
    overused_vague_terms: list[str]       = field(default_factory=list)
    weak_bullets: list[BulletDiagnosis]   = field(default_factory=list)
    formatting_warnings: list[str]        = field(default_factory=list)
    honesty_warnings: list[str]           = field(default_factory=list)

    must_fix: list[dict]   = field(default_factory=list)
    should_fix: list[dict] = field(default_factory=list)
    nice_to_have: list[dict] = field(default_factory=list)


# =============================================================================
# MAIN ANALYZER
# =============================================================================

class ResumeAnalyzer:

    def analyze(
        self,
        resume: ParsedResume,
        job_description: str,
        job_title: str = "",
        company_name: str = "",
    ) -> AnalysisResult:
        result = AnalysisResult()

        jd_lower  = job_description.lower()
        resume_text_lower = resume.raw_text.lower()

        # 1. Extract JD keywords
        jd_keywords = self._extract_jd_keywords(job_description)

        # 2. Check which keywords appear in resume
        result.keywords = self._check_keyword_coverage(
            jd_keywords, resume.raw_text, resume
        )

        # 3. Separate missing lists
        result.required_missing = [
            k.keyword for k in result.keywords
            if k.importance == "required" and not k.found_in_resume
        ]
        result.preferred_missing = [
            k.keyword for k in result.keywords
            if k.importance == "preferred" and not k.found_in_resume
        ]

        # 4. Score ATS keyword coverage
        result.ats_keyword_score = self._score_keyword_coverage(result.keywords)

        # 5. Diagnose bullets
        all_bullets = self._collect_bullets(resume)
        result.weak_bullets = self._diagnose_bullets(all_bullets, jd_keywords)

        # 6. Score quantified impact
        result.quantified_impact_score = self._score_quantified_impact(all_bullets)

        # 7. Score technical depth
        result.technical_depth_score = self._score_technical_depth(
            resume_text_lower, jd_lower
        )

        # 8. ATS formatting score
        result.formatting_score, result.formatting_warnings = self._score_formatting(resume)

        # 9. Recruiter scan score
        result.recruiter_scan_score = self._score_recruiter_scan(resume, job_title)

        # 10. Vague language check
        result.overused_vague_terms = self._find_vague_terms(resume.raw_text)

        # 11. Overall score
        result.overall_score = self._compute_overall(result)

        # 12. Recruiter verdict
        result.recruiter_verdict, \
        result.recruiter_6s_impression, \
        result.recruiter_main_reason, \
        result.recruiter_biggest_weakness, \
        result.recruiter_fastest_fix = self._recruiter_verdict(
            result, resume, job_title, company_name
        )

        # 13. Priority edits
        result.must_fix, result.should_fix, result.nice_to_have = \
            self._prioritise_edits(result)

        return result

    # =========================================================================
    # JD KEYWORD EXTRACTION
    # =========================================================================

    def _extract_jd_keywords(self, jd: str) -> list[tuple[str, str]]:
        """
        Returns list of (keyword, importance) tuples.
        importance = required | preferred | nice_to_have

        Heuristic: keywords near "required", "must have", "must-have" → required
                   keywords near "preferred", "nice to have", "plus" → preferred
                   everything else → preferred (conservative default)
        """
        results: list[tuple[str, str]] = []
        seen: set[str] = set()

        # Required section detection
        required_zone = self._extract_zone(jd, ["required", "must have", "must-have", "you have"])
        preferred_zone = self._extract_zone(jd, ["preferred", "nice to have", "bonus", "a plus", "ideally"])

        for pattern in [_LANG_PATTERNS, _FRAMEWORK_PATTERNS, _DOMAIN_PATTERNS]:
            for m in pattern.finditer(jd):
                kw = m.group(0).strip().lower()
                if kw in seen:
                    continue
                seen.add(kw)

                # Determine importance
                pos = m.start()
                if self._in_zone(pos, required_zone):
                    importance = "required"
                elif self._in_zone(pos, preferred_zone):
                    importance = "preferred"
                else:
                    # Count occurrences: >= 3 occurrences → treat as required
                    count = len(re.findall(re.escape(kw), jd, re.I))
                    importance = "required" if count >= 3 else "preferred"

                results.append((kw, importance))

        # Also extract repeated capitalized terms not caught by patterns
        capitalized = re.findall(r"\b([A-Z][a-zA-Z0-9+#]{2,})\b", jd)
        freq: dict[str, int] = {}
        for w in capitalized:
            freq[w.lower()] = freq.get(w.lower(), 0) + 1

        for word, count in freq.items():
            if count >= 2 and word not in seen and len(word) > 2:
                seen.add(word)
                results.append((word, "preferred"))

        return results

    @staticmethod
    def _extract_zone(text: str, anchors: list[str]) -> list[tuple[int, int]]:
        """Return character ranges for sections near anchor words."""
        zones = []
        for anchor in anchors:
            for m in re.finditer(re.escape(anchor), text, re.I):
                start = m.start()
                end   = min(len(text), start + 800)
                zones.append((start, end))
        return zones

    @staticmethod
    def _in_zone(pos: int, zones: list[tuple[int, int]]) -> bool:
        return any(s <= pos <= e for s, e in zones)

    # =========================================================================
    # KEYWORD COVERAGE
    # =========================================================================

    def _check_keyword_coverage(
        self,
        jd_keywords: list[tuple[str, str]],
        resume_text: str,
        resume: ParsedResume,
    ) -> list[KeywordResult]:
        resume_lower = resume_text.lower()
        results = []

        for kw, importance in jd_keywords:
            found = kw.lower() in resume_lower
            location = self._locate_keyword(kw, resume) if found else ""
            placement = self._recommend_placement(kw, found, resume)
            wording   = self._suggest_wording(kw, found)

            results.append(KeywordResult(
                keyword=kw,
                importance=importance,
                found_in_resume=found,
                current_location=location,
                recommended_placement=placement,
                suggested_wording=wording,
            ))

        return results

    @staticmethod
    def _locate_keyword(kw: str, resume: ParsedResume) -> str:
        kw_lower = kw.lower()
        if any(kw_lower in s.lower() for s in resume.skills):
            return "Skills section"
        for i, exp in enumerate(resume.experience):
            bullets = exp.get("bullets", [])
            if any(kw_lower in b.lower() for b in bullets):
                return f"Experience entry {i+1}"
        for i, proj in enumerate(resume.projects):
            bullets = proj.get("bullets", [])
            if any(kw_lower in b.lower() for b in bullets):
                return f"Project {i+1}"
        return "Resume body"

    @staticmethod
    def _recommend_placement(kw: str, found: bool, resume: ParsedResume) -> str:
        if found:
            return "Already present"
        # Programming languages / tools → skills section
        if _LANG_PATTERNS.match(kw) or _FRAMEWORK_PATTERNS.match(kw):
            return "Skills section + relevant experience or project bullets"
        return "Relevant experience or project bullets"

    @staticmethod
    def _suggest_wording(kw: str, found: bool) -> str:
        if found:
            return ""
        return (
            f"Add '{kw}' to skills section and reference it naturally in "
            "a bullet (only if you have genuine experience with it)."
        )

    @staticmethod
    def _score_keyword_coverage(keywords: list[KeywordResult]) -> int:
        if not keywords:
            return 50
        required = [k for k in keywords if k.importance == "required"]
        preferred = [k for k in keywords if k.importance == "preferred"]

        req_found = sum(1 for k in required if k.found_in_resume)
        pref_found = sum(1 for k in preferred if k.found_in_resume)

        req_score  = (req_found / len(required)  * 60) if required  else 40
        pref_score = (pref_found / len(preferred) * 40) if preferred else 20
        return min(100, round(req_score + pref_score))

    # =========================================================================
    # BULLET DIAGNOSIS
    # =========================================================================

    def _collect_bullets(self, resume: ParsedResume) -> list[tuple[str, str]]:
        """Returns list of (bullet_text, section_label)."""
        bullets = []
        for i, exp in enumerate(resume.experience):
            for b in exp.get("bullets", []):
                bullets.append((b, f"Experience — {exp.get('company', f'Entry {i+1}')}"))
        for i, proj in enumerate(resume.projects):
            for b in proj.get("bullets", []):
                bullets.append((b, f"Project — {proj.get('name', f'Project {i+1}')}"))
        return bullets

    def _diagnose_bullets(
        self,
        bullets: list[tuple[str, str]],
        jd_keywords: list[tuple[str, str]],
    ) -> list[BulletDiagnosis]:
        jd_kw_set = {kw.lower() for kw, _ in jd_keywords}
        diagnoses = []

        for bullet_text, section in bullets:
            if len(bullet_text.strip()) < 15:
                continue

            issues = []
            lower  = bullet_text.lower()

            # Weak verb check
            for phrase in _WEAK_VERBS:
                if lower.startswith(phrase) or f" {phrase} " in lower:
                    issues.append("weak_verb")
                    break

            # No metric check
            has_metric = bool(re.search(
                r"\d+%|\d+x|\d+\s*(ms|sec|seconds|hour|hours|day|days|users|"
                r"requests|records|endpoints|TB|GB|MB|K\b|M\b)",
                bullet_text, re.I
            ))
            if not has_metric:
                issues.append("no_metric")

            # Task not outcome
            task_phrases = ["responsible for", "tasked with", "worked on", "helped", "assisted"]
            if any(p in lower for p in task_phrases):
                issues.append("task_not_outcome")

            # Vague / overused language
            vague = ["various", "multiple", "several", "many", "some", "number of", "stuff"]
            if any(v in lower for v in vague):
                issues.append("vague_language")

            # Buries technology — tech term appears at end rather than early
            tech_in_bullet = [kw for kw in jd_kw_set if kw in lower]
            if tech_in_bullet:
                first_tech_pos = min(lower.find(kw) for kw in tech_in_bullet if kw in lower)
                if first_tech_pos > len(lower) * 0.6:
                    issues.append("buries_technology")

            if not issues:
                continue

            problem = self._describe_problem(issues)
            diagnoses.append(BulletDiagnosis(
                original=bullet_text,
                problem=problem,
                issues=issues,
                requires_verification="no_metric" in issues,
                verification_note=(
                    "Replace [X] placeholders with actual measured values before using."
                    if "no_metric" in issues else ""
                ),
            ))

        return diagnoses

    @staticmethod
    def _describe_problem(issues: list[str]) -> str:
        parts = []
        if "weak_verb" in issues:
            parts.append("Starts with a weak verb that hides your contribution")
        if "no_metric" in issues:
            parts.append("No quantified impact — recruiters can't gauge scale or results")
        if "task_not_outcome" in issues:
            parts.append("Describes a task, not an outcome")
        if "vague_language" in issues:
            parts.append("Contains vague language that adds no information")
        if "buries_technology" in issues:
            parts.append("Key technology appears late in the bullet — move it earlier")
        return "; ".join(parts)

    # =========================================================================
    # SCORING
    # =========================================================================

    @staticmethod
    def _score_quantified_impact(bullets: list[tuple[str, str]]) -> int:
        if not bullets:
            return 50
        metric_pattern = re.compile(
            r"\d+%|\d+x|\d+\s*(ms|sec|hours?|days?|users?|requests?|records?|"
            r"endpoints?|TB|GB|MB|K\b|M\b|billion|million|thousand)",
            re.I
        )
        count = sum(1 for b, _ in bullets if metric_pattern.search(b))
        ratio = count / len(bullets)
        if ratio >= 0.7:   return 100
        if ratio >= 0.5:   return 80
        if ratio >= 0.3:   return 60
        if ratio >= 0.1:   return 40
        return 15

    @staticmethod
    def _score_technical_depth(resume_lower: str, jd_lower: str) -> int:
        tech_terms = set(re.findall(r'\b[a-z][a-z0-9+#.\-]{2,}\b', jd_lower))
        found = sum(1 for t in tech_terms if t in resume_lower)
        if not tech_terms:
            return 50
        ratio = found / len(tech_terms)
        return min(100, round(ratio * 100))

    @staticmethod
    def _score_formatting(resume: ParsedResume) -> tuple[int, list[str]]:
        warnings = []
        score = 100

        if not resume.education:
            warnings.append("No Education section detected")
            score -= 10
        if not resume.experience and not resume.projects:
            warnings.append("No Experience or Projects section detected")
            score -= 20
        if not resume.skills:
            warnings.append("No Skills section detected")
            score -= 15
        if not resume.contact.get("email"):
            warnings.append("No email address found in contact information")
            score -= 10
        for exp in resume.experience:
            if not exp.get("dates"):
                warnings.append(_FORMATTING_WARNINGS["no_dates"])
                score -= 5
                break

        return max(0, score), warnings

    @staticmethod
    def _score_recruiter_scan(resume: ParsedResume, job_title: str) -> int:
        score = 100
        if not resume.contact.get("name"):
            score -= 10
        if not resume.skills:
            score -= 15
        if len(resume.experience) < 1 and len(resume.projects) < 1:
            score -= 20
        all_bullets = []
        for exp in resume.experience:
            all_bullets.extend(exp.get("bullets", []))
        if len(all_bullets) < 3:
            score -= 15
        # Check for impact verbs in the first 3 bullets
        strong_start = sum(
            1 for b in all_bullets[:3]
            if b and b.split()[0].lower().rstrip("ed") in
            {v.rstrip("ed") for v in _STRONG_VERBS}
        )
        if strong_start < 2:
            score -= 10
        return max(0, score)

    @staticmethod
    def _find_vague_terms(text: str) -> list[str]:
        vague = [
            "various", "multiple", "several", "many", "some", "stuff",
            "things", "etc", "and more", "a lot", "number of",
            "good understanding", "familiar with", "knowledge of",
            "exposure to", "basic knowledge",
        ]
        return [v for v in vague if v in text.lower()]

    @staticmethod
    def _compute_overall(r: AnalysisResult) -> int:
        return round(
            r.ats_keyword_score      * 0.25 +
            r.technical_depth_score  * 0.20 +
            r.quantified_impact_score* 0.20 +
            r.recruiter_scan_score   * 0.15 +
            r.formatting_score       * 0.10 +
            50                       * 0.10   # role title alignment placeholder
        )

    @staticmethod
    def _recruiter_verdict(
        r: AnalysisResult,
        resume: ParsedResume,
        job_title: str,
        company_name: str,
    ) -> tuple[str, str, str, str, str]:
        score = r.overall_score

        if score >= 80:
            verdict = "strong_move_forward"
            impression = "Strong technical resume with good keyword coverage and quantified impact."
            main_reason = "Resume closely matches the role requirements."
        elif score >= 65:
            verdict = "move_forward"
            impression = "Solid candidate with relevant experience. Some gaps visible."
            main_reason = "Meets core requirements, minor improvements would strengthen it."
        elif score >= 50:
            verdict = "maybe"
            impression = "Some relevant experience but gaps in key areas or missing keywords."
            main_reason = "Missing several required skills or lacks quantified impact."
        elif score >= 35:
            verdict = "weak_maybe"
            impression = "Relevant background is unclear. Keywords and metrics are sparse."
            main_reason = "Keyword gaps and unquantified bullets make it hard to assess fit."
        else:
            verdict = "likely_reject"
            impression = "Resume does not clearly show alignment with this role."
            main_reason = "Too many required keywords missing; impact not demonstrated."

        # Identify biggest weakness
        weaknesses = []
        if r.required_missing:
            weaknesses.append(f"Missing required keywords: {', '.join(r.required_missing[:3])}")
        if r.quantified_impact_score < 50:
            weaknesses.append("Very few quantified results in experience bullets")
        if r.formatting_score < 70:
            weaknesses.append("Formatting issues that may hurt ATS parsing")
        if not resume.skills:
            weaknesses.append("No explicit skills section")

        biggest_weakness = weaknesses[0] if weaknesses else "No major weaknesses identified"

        # Fastest fix
        if r.required_missing:
            fastest_fix = (
                f"Add '{r.required_missing[0]}' and "
                f"'{r.required_missing[1]}' to your skills section and "
                "demonstrate them in a bullet."
                if len(r.required_missing) > 1
                else f"Add '{r.required_missing[0]}' to your skills section."
            )
        elif r.quantified_impact_score < 60 and r.weak_bullets:
            fastest_fix = "Add a metric to your top 3 experience bullets."
        else:
            fastest_fix = "Review the keyword table and add the top 3 missing keywords."

        return verdict, impression, main_reason, biggest_weakness, fastest_fix

    @staticmethod
    def _prioritise_edits(r: AnalysisResult) -> tuple[list, list, list]:
        must_fix = []
        should_fix = []
        nice = []

        if r.required_missing:
            must_fix.append({
                "section": "Keywords",
                "description": f"Add missing required keywords: {', '.join(r.required_missing[:5])}",
            })
        if r.quantified_impact_score < 50:
            must_fix.append({
                "section": "Experience Bullets",
                "description": "Add quantified metrics to at least 3 bullets",
            })
        if not r.keywords or len([k for k in r.keywords if k.found_in_resume]) == 0:
            must_fix.append({
                "section": "Skills Section",
                "description": "Skills section is missing or not parsed",
            })

        if r.weak_bullets:
            should_fix.append({
                "section": "Bullets",
                "description": f"Rewrite {min(3, len(r.weak_bullets))} weak bullets with stronger verbs and outcomes",
            })
        if r.preferred_missing:
            should_fix.append({
                "section": "Keywords",
                "description": f"Add preferred keywords: {', '.join(r.preferred_missing[:4])}",
            })
        if r.formatting_warnings:
            should_fix.append({
                "section": "Formatting",
                "description": r.formatting_warnings[0],
            })

        if r.overused_vague_terms:
            nice.append({
                "section": "Language",
                "description": f"Replace vague terms: {', '.join(r.overused_vague_terms[:3])}",
            })

        return must_fix, should_fix, nice
