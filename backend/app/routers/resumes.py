from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.auth import get_current_user, CurrentUser
from app.models import Resume, ResumeVersion, ResumeJobAnalysis, ResumeKeyword, ResumeBulletSuggestion
from app.config import get_settings

router = APIRouter()
settings = get_settings()


# ── Upload + Parse ─────────────────────────────────────────────────────────────

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile     = File(...),
    name: str            = Form(default="Base Resume"),
    is_base: bool        = Form(default=True),
    user: CurrentUser    = Depends(get_current_user),
    db: AsyncSession     = Depends(get_db),
):
    if file.size and file.size > settings.max_resume_size_bytes:
        raise HTTPException(status_code=413, detail="File exceeds 10MB limit")

    allowed_types = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                     "text/plain"}
    if file.content_type not in allowed_types and not file.filename.endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(status_code=422, detail="Unsupported file type. Use PDF, DOCX, or TXT.")

    content = await file.read()
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "txt"

    from app.services.resume.parser import parse_resume
    parsed = await parse_resume(content, file.filename)

    resume = Resume(
        user_id=user.id,
        name=name,
        file_format=ext,
        file_size_bytes=len(content),
        parsed_text=parsed.raw_text,
        parsed_json=parsed.to_json(),
        parse_warnings=parsed.parse_warnings,
        is_base=is_base,
    )
    db.add(resume)
    await db.commit()

    return {
        "id": str(resume.id),
        "name": resume.name,
        "file_format": resume.file_format,
        "parse_warnings": resume.parse_warnings,
        "sections_detected": [
            k for k, v in parsed.to_json().items()
            if v and k != "contact"
        ],
        "contact": parsed.contact,
        "skills_count": len(parsed.skills),
        "experience_count": len(parsed.experience),
        "projects_count": len(parsed.projects),
    }


@router.get("")
async def list_resumes(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == user.id, Resume.is_archived == False)
        .order_by(Resume.created_at.desc())
    )
    resumes = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "file_format": r.file_format,
            "is_base": r.is_base,
            "parse_warnings": r.parse_warnings,
            "created_at": r.created_at.isoformat(),
        }
        for r in resumes
    ]


@router.get("/{resume_id}")
async def get_resume(
    resume_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    r = await _get_resume_or_404(resume_id, user, db)
    return {
        "id": str(r.id),
        "name": r.name,
        "file_format": r.file_format,
        "is_base": r.is_base,
        "parsed_text": r.parsed_text,
        "parsed_json": r.parsed_json,
        "parse_warnings": r.parse_warnings,
        "created_at": r.created_at.isoformat(),
    }


# ── Analysis ───────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    job_description: str
    job_title: Optional[str] = ""
    company_name: Optional[str] = ""
    job_id: Optional[UUID] = None


@router.post("/{resume_id}/analyze")
async def analyze_resume(
    resume_id: UUID,
    payload: AnalyzeRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    r = await _get_resume_or_404(resume_id, user, db)

    from app.services.resume.parser import ParsedResume
    import json as _json

    parsed = ParsedResume(
        raw_text=r.parsed_text or "",
        **(r.parsed_json or {}),
    )
    # Re-populate structured fields from JSON
    parsed_data = r.parsed_json or {}
    parsed.contact = parsed_data.get("contact", {})
    parsed.education = parsed_data.get("education", [])
    parsed.experience = parsed_data.get("experience", [])
    parsed.projects = parsed_data.get("projects", [])
    parsed.skills = parsed_data.get("skills", [])
    parsed.certifications = parsed_data.get("certifications", [])
    parsed.leadership = parsed_data.get("leadership", [])
    parsed.awards = parsed_data.get("awards", [])
    parsed.summary = parsed_data.get("summary", "")

    from app.services.resume.analyzer import ResumeAnalyzer
    analyzer = ResumeAnalyzer()
    result = analyzer.analyze(
        resume=parsed,
        job_description=payload.job_description,
        job_title=payload.job_title or "",
        company_name=payload.company_name or "",
    )

    # Persist analysis
    analysis = ResumeJobAnalysis(
        user_id=user.id,
        resume_id=resume_id,
        job_id=payload.job_id,
        job_description_text=payload.job_description,
        job_title_input=payload.job_title,
        job_company_input=payload.company_name,
        overall_score=result.overall_score,
        ats_keyword_score=result.ats_keyword_score,
        recruiter_scan_score=result.recruiter_scan_score,
        technical_depth_score=result.technical_depth_score,
        quantified_impact_score=result.quantified_impact_score,
        formatting_score=result.formatting_score,
        recruiter_verdict=result.recruiter_verdict,
        recruiter_6s_impression=result.recruiter_6s_impression,
        recruiter_main_reason=result.recruiter_main_reason,
        recruiter_biggest_weakness=result.recruiter_biggest_weakness,
        recruiter_fastest_fix=result.recruiter_fastest_fix,
        required_keywords_found=[k.keyword for k in result.keywords if k.importance == "required" and k.found_in_resume],
        required_keywords_missing=result.required_missing,
        preferred_keywords_found=[k.keyword for k in result.keywords if k.importance == "preferred" and k.found_in_resume],
        preferred_keywords_missing=result.preferred_missing,
        overused_vague_terms=result.overused_vague_terms,
        must_fix_items=result.must_fix,
        should_fix_items=result.should_fix,
        nice_to_have_items=result.nice_to_have,
        honesty_warnings=result.honesty_warnings,
        full_analysis_json={
            "keywords": [
                {
                    "keyword": k.keyword,
                    "importance": k.importance,
                    "found": k.found_in_resume,
                    "location": k.current_location,
                    "placement": k.recommended_placement,
                }
                for k in result.keywords
            ],
            "formatting_warnings": result.formatting_warnings,
        },
    )
    db.add(analysis)
    await db.flush()

    # Persist keyword rows
    for kw in result.keywords:
        db.add(ResumeKeyword(
            analysis_id=analysis.id,
            keyword=kw.keyword,
            importance=kw.importance,
            found_in_resume=kw.found_in_resume,
            current_location=kw.current_location,
            recommended_placement=kw.recommended_placement,
            suggested_wording=kw.suggested_wording,
        ))

    await db.commit()

    return {
        "analysis_id": str(analysis.id),
        "scores": {
            "overall": result.overall_score,
            "ats_keyword": result.ats_keyword_score,
            "recruiter_scan": result.recruiter_scan_score,
            "technical_depth": result.technical_depth_score,
            "quantified_impact": result.quantified_impact_score,
            "formatting": result.formatting_score,
        },
        "recruiter": {
            "verdict": result.recruiter_verdict,
            "impression": result.recruiter_6s_impression,
            "main_reason": result.recruiter_main_reason,
            "biggest_weakness": result.recruiter_biggest_weakness,
            "fastest_fix": result.recruiter_fastest_fix,
        },
        "keywords": {
            "required_found": [k.keyword for k in result.keywords if k.importance == "required" and k.found_in_resume],
            "required_missing": result.required_missing,
            "preferred_found": [k.keyword for k in result.keywords if k.importance == "preferred" and k.found_in_resume],
            "preferred_missing": result.preferred_missing,
            "all": [
                {"keyword": k.keyword, "importance": k.importance, "found": k.found_in_resume}
                for k in result.keywords
            ],
        },
        "priority_edits": {
            "must_fix": result.must_fix,
            "should_fix": result.should_fix,
            "nice_to_have": result.nice_to_have,
        },
        "formatting_warnings": result.formatting_warnings,
        "vague_terms": result.overused_vague_terms,
        "weak_bullets_count": len(result.weak_bullets),
    }


# ── Optimize ───────────────────────────────────────────────────────────────────

@router.post("/{resume_id}/optimize/{analysis_id}")
async def optimize_resume(
    resume_id: UUID,
    analysis_id: UUID,
    version_name: str = "Optimized Version",
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    r = await _get_resume_or_404(resume_id, user, db)
    analysis_result = await db.execute(
        select(ResumeJobAnalysis).where(
            ResumeJobAnalysis.id == analysis_id,
            ResumeJobAnalysis.user_id == user.id,
        )
    )
    analysis_row = analysis_result.scalar_one_or_none()
    if not analysis_row:
        raise HTTPException(status_code=404, detail="Analysis not found")

    from app.services.resume.parser import ParsedResume
    from app.services.resume.analyzer import AnalysisResult
    from app.services.resume.optimizer import optimize_full_resume, rewrite_bullets

    parsed_data = r.parsed_json or {}
    parsed = ParsedResume(raw_text=r.parsed_text or "")
    parsed.experience = parsed_data.get("experience", [])
    parsed.projects   = parsed_data.get("projects", [])
    parsed.skills     = parsed_data.get("skills", [])
    parsed.education  = parsed_data.get("education", [])
    parsed.contact    = parsed_data.get("contact", {})
    parsed.summary    = parsed_data.get("summary", "")

    # Reconstruct a minimal AnalysisResult for the optimizer
    ar = AnalysisResult(
        overall_score=analysis_row.overall_score or 0,
        required_missing=analysis_row.required_keywords_missing or [],
        preferred_missing=analysis_row.preferred_keywords_missing or [],
    )

    optimized_json = await optimize_full_resume(
        resume=parsed,
        analysis=ar,
        job_description=analysis_row.job_description_text or "",
        job_title=analysis_row.job_title_input or "",
        company_name=analysis_row.job_company_input or "",
    )

    version = ResumeVersion(
        resume_id=resume_id,
        user_id=user.id,
        version_name=version_name,
        target_company=analysis_row.job_company_input,
        target_job_title=analysis_row.job_title_input,
        optimized_json=optimized_json,
        analysis_id=analysis_id,
        ats_score=analysis_row.ats_keyword_score,
        recruiter_scan_score=analysis_row.recruiter_scan_score,
        keyword_coverage_score=analysis_row.ats_keyword_score,
        metric_strength_score=analysis_row.quantified_impact_score,
        formatting_score=analysis_row.formatting_score,
    )
    db.add(version)
    await db.commit()

    return {
        "version_id": str(version.id),
        "version_name": version.version_name,
        "optimized_json": optimized_json,
        "message": "Resume version created. Replace all [X] placeholders with your real numbers.",
    }


@router.get("/{resume_id}/versions")
async def list_versions(
    resume_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    await _get_resume_or_404(resume_id, user, db)
    result = await db.execute(
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume_id, ResumeVersion.user_id == user.id)
        .order_by(ResumeVersion.created_at.desc())
    )
    return [
        {
            "id": str(v.id),
            "version_name": v.version_name,
            "target_company": v.target_company,
            "target_job_title": v.target_job_title,
            "ats_score": v.ats_score,
            "recruiter_scan_score": v.recruiter_scan_score,
            "created_at": v.created_at.isoformat(),
        }
        for v in result.scalars().all()
    ]


@router.get("/{resume_id}/analyses")
async def list_analyses(
    resume_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    await _get_resume_or_404(resume_id, user, db)
    result = await db.execute(
        select(ResumeJobAnalysis)
        .where(ResumeJobAnalysis.resume_id == resume_id, ResumeJobAnalysis.user_id == user.id)
        .order_by(ResumeJobAnalysis.created_at.desc())
    )
    return [
        {
            "id": str(a.id),
            "job_title": a.job_title_input,
            "company": a.job_company_input,
            "overall_score": a.overall_score,
            "recruiter_verdict": a.recruiter_verdict,
            "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars().all()
    ]


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_resume_or_404(resume_id: UUID, user: CurrentUser, db: AsyncSession) -> Resume:
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")
    return r
