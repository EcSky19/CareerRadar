from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user, CurrentUser
from app.models import (
    Job, JobMatch, ApplicationStatus, TargetProfile, Company
)

router = APIRouter()


# ── Response schemas ──────────────────────────────────────────────────────────

class JobMatchResponse(BaseModel):
    id: UUID
    job_id: UUID
    title: str
    company_name: str
    location: Optional[str]
    is_remote: Optional[bool]
    application_url: str
    posted_at: Optional[object]
    match_score: int
    match_reason: Optional[str]
    matched_title_terms: List[str]
    matched_keywords: List[str]
    profile_name: str
    is_saved: bool
    is_dismissed: bool
    alert_sent: bool
    application_status: Optional[str]
    first_seen_at: object

    model_config = {"from_attributes": True}


class ApplicationUpsert(BaseModel):
    status: str   # not_applied|saved|applied|interview|rejected|offer|archived
    applied_at: Optional[datetime] = None
    follow_up_date: Optional[object] = None
    notes: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/matches", response_model=List[dict])
async def list_job_matches(
    profile_id: Optional[UUID]  = Query(None),
    min_score: int              = Query(0),
    max_score: int              = Query(100),
    show_dismissed: bool        = Query(False),
    saved_only: bool            = Query(False),
    status_filter: Optional[str]= Query(None),   # open | closed
    limit: int                  = Query(50, le=200),
    offset: int                 = Query(0),
    user: CurrentUser           = Depends(get_current_user),
    db: AsyncSession            = Depends(get_db),
):
    q = (
        select(JobMatch, Job, TargetProfile)
        .join(Job, Job.id == JobMatch.job_id)
        .join(TargetProfile, TargetProfile.id == JobMatch.target_profile_id)
        .where(
            JobMatch.user_id == user.id,
            JobMatch.match_score.between(min_score, max_score),
        )
        .order_by(JobMatch.match_score.desc(), Job.first_seen_at.desc())
        .offset(offset)
        .limit(limit)
    )

    if profile_id:
        q = q.where(JobMatch.target_profile_id == profile_id)
    if not show_dismissed:
        q = q.where(JobMatch.is_dismissed == False)
    if saved_only:
        q = q.where(JobMatch.is_saved == True)
    if status_filter:
        q = q.where(Job.status == status_filter)

    rows = (await db.execute(q)).all()

    # Fetch application statuses in one query
    job_ids = [r[1].id for r in rows]
    app_result = await db.execute(
        select(ApplicationStatus).where(
            ApplicationStatus.user_id == user.id,
            ApplicationStatus.job_id.in_(job_ids),
        )
    ) if job_ids else None
    app_by_job = {}
    if app_result:
        for app in app_result.scalars().all():
            app_by_job[str(app.job_id)] = app.status

    return [
        {
            "id": str(match.id),
            "job_id": str(job.id),
            "title": job.title,
            "company_name": job.company_name,
            "location": job.location,
            "is_remote": job.is_remote,
            "application_url": job.application_url,
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
            "job_status": job.status,
            "match_score": match.match_score,
            "match_reason": match.match_reason,
            "matched_title_terms": match.matched_title_terms or [],
            "matched_keywords": match.matched_keywords or [],
            "domain_signals_found": match.domain_signals_found or [],
            "profile_name": profile.name,
            "profile_id": str(profile.id),
            "is_saved": match.is_saved,
            "is_dismissed": match.is_dismissed,
            "alert_sent": match.alert_sent,
            "application_status": app_by_job.get(str(job.id), "not_applied"),
            "first_seen_at": match.created_at.isoformat(),
        }
        for match, job, profile in rows
    ]


@router.get("/matches/stats")
async def match_stats(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    """Dashboard summary counts."""
    total = await db.scalar(
        select(func.count()).where(JobMatch.user_id == user.id)
    )
    high = await db.scalar(
        select(func.count()).where(
            JobMatch.user_id == user.id,
            JobMatch.match_score >= 80
        )
    )
    new_today = await db.scalar(
        select(func.count()).where(
            JobMatch.user_id == user.id,
            JobMatch.created_at >= func.now() - __import__("sqlalchemy").text("interval '1 day'"),
        )
    )
    applied = await db.scalar(
        select(func.count()).where(
            ApplicationStatus.user_id == user.id,
            ApplicationStatus.status == "applied",
        )
    )
    return {
        "total_matches": total or 0,
        "high_score_matches": high or 0,
        "new_today": new_today or 0,
        "applied_count": applied or 0,
    }


@router.post("/matches/{match_id}/save")
async def save_match(
    match_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    await db.execute(
        update(JobMatch)
        .where(JobMatch.id == match_id, JobMatch.user_id == user.id)
        .values(is_saved=True, is_dismissed=False)
    )
    await db.commit()
    return {"status": "saved"}


@router.post("/matches/{match_id}/dismiss")
async def dismiss_match(
    match_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    await db.execute(
        update(JobMatch)
        .where(JobMatch.id == match_id, JobMatch.user_id == user.id)
        .values(is_dismissed=True, is_saved=False)
    )
    await db.commit()
    return {"status": "dismissed"}


@router.post("/matches/{match_id}/unsave")
async def unsave_match(
    match_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    await db.execute(
        update(JobMatch)
        .where(JobMatch.id == match_id, JobMatch.user_id == user.id)
        .values(is_saved=False)
    )
    await db.commit()
    return {"status": "unsaved"}


@router.get("/{job_id}")
async def get_job(
    job_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    """Get a single job + user's match and application status."""
    result = await db.execute(
        select(Job)
        .join(Company, Company.id == Job.company_id)
        .where(Job.id == job_id, Company.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    match_result = await db.execute(
        select(JobMatch).where(
            JobMatch.job_id == job_id,
            JobMatch.user_id == user.id,
        ).order_by(JobMatch.match_score.desc()).limit(1)
    )
    match = match_result.scalar_one_or_none()

    app_result = await db.execute(
        select(ApplicationStatus).where(
            ApplicationStatus.job_id == job_id,
            ApplicationStatus.user_id == user.id,
        )
    )
    app = app_result.scalar_one_or_none()

    return {
        "id": str(job.id),
        "title": job.title,
        "company_name": job.company_name,
        "location": job.location,
        "is_remote": job.is_remote,
        "department": job.department,
        "description": job.description,
        "application_url": job.application_url,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "first_seen_at": job.first_seen_at.isoformat(),
        "status": job.status,
        "match_score": match.match_score if match else None,
        "match_reason": match.match_reason if match else None,
        "application_status": app.status if app else "not_applied",
        "applied_at": app.applied_at.isoformat() if app and app.applied_at else None,
        "notes": app.notes if app else None,
    }


# ── Application tracker ────────────────────────────────────────────────────────

@router.put("/{job_id}/application", status_code=status.HTTP_200_OK)
async def upsert_application(
    job_id: UUID,
    payload: ApplicationUpsert,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = (
        pg_insert(ApplicationStatus)
        .values(
            user_id=user.id,
            job_id=job_id,
            status=payload.status,
            applied_at=payload.applied_at,
            follow_up_date=payload.follow_up_date,
            notes=payload.notes,
        )
        .on_conflict_do_update(
            constraint="application_user_job_unique",
            set_={
                "status": payload.status,
                "applied_at": payload.applied_at,
                "follow_up_date": payload.follow_up_date,
                "notes": payload.notes,
                "updated_at": datetime.now(timezone.utc),
            },
        )
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "ok"}


@router.get("/tracker/all")
async def list_tracked_applications(
    status_filter: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    q = (
        select(ApplicationStatus, Job)
        .join(Job, Job.id == ApplicationStatus.job_id)
        .where(ApplicationStatus.user_id == user.id)
        .where(ApplicationStatus.status != "not_applied")
        .order_by(ApplicationStatus.updated_at.desc())
    )
    if status_filter:
        q = q.where(ApplicationStatus.status == status_filter)

    rows = (await db.execute(q)).all()
    return [
        {
            "id": str(app.id),
            "job_id": str(job.id),
            "title": job.title,
            "company_name": job.company_name,
            "location": job.location,
            "application_url": job.application_url,
            "status": app.status,
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "follow_up_date": str(app.follow_up_date) if app.follow_up_date else None,
            "notes": app.notes,
            "updated_at": app.updated_at.isoformat(),
        }
        for app, job in rows
    ]
