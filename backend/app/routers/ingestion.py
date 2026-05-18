from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user, CurrentUser
from app.models import IngestionRun, CompanyCheckLog, SourceError, Company
from app.config import get_settings

router = APIRouter()
settings = get_settings()


class RunTriggerResponse(BaseModel):
    run_id: str
    status: str
    message: str


# ── Trigger routes ────────────────────────────────────────────────────────────

@router.post("/run", response_model=RunTriggerResponse)
async def trigger_full_run(
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    """
    Trigger an ingestion run for all of the current user's active companies.
    Runs in the background so the response returns immediately.
    """
    from app.services.ingestion.runner import run_full_ingestion
    from app.models import IngestionRun
    import uuid

    # Create a run record immediately so caller has an ID to poll
    run = IngestionRun(triggered_by=f"manual:{user.id}", status="running")
    db.add(run)
    await db.commit()
    run_id = str(run.id)

    background_tasks.add_task(
        _background_full_run, run_id=run.id, user_id=user.id
    )

    return RunTriggerResponse(
        run_id=run_id,
        status="running",
        message="Ingestion started in background. Poll /ingestion/runs/{run_id} for status.",
    )


@router.post("/run/company/{company_id}")
async def trigger_company_run(
    company_id: UUID,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    """Trigger ingestion for a single company (must belong to the current user)."""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")

    background_tasks.add_task(_background_company_run, company_id=company_id)

    return {"status": "running", "company_id": str(company_id)}


# ── Status / log routes ───────────────────────────────────────────────────────

@router.get("/runs")
async def list_runs(
    limit: int        = 20,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    result = await db.execute(
        select(IngestionRun)
        .order_by(desc(IngestionRun.started_at))
        .limit(limit)
    )
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "triggered_by": r.triggered_by,
            "status": r.status,
            "companies_checked": r.companies_checked,
            "new_jobs_found": r.new_jobs_found,
            "matches_found": r.matches_found,
            "alerts_sent": r.alerts_sent,
            "error_count": r.error_count,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "duration_seconds": (
                (r.finished_at - r.started_at).total_seconds()
                if r.finished_at else None
            ),
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
async def get_run(
    run_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    result = await db.execute(
        select(IngestionRun).where(IngestionRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Fetch per-company logs for this run
    logs_result = await db.execute(
        select(CompanyCheckLog, Company)
        .join(Company, Company.id == CompanyCheckLog.company_id)
        .where(
            CompanyCheckLog.ingestion_run_id == run_id,
            Company.user_id == user.id,
        )
        .order_by(CompanyCheckLog.started_at)
    )
    check_logs = [
        {
            "company_name": company.name,
            "company_id": str(company.id),
            "status": log.status,
            "jobs_found": log.jobs_found,
            "new_jobs_found": log.new_jobs_found,
            "matches_found": log.matches_found,
            "error_message": log.error_message,
            "duration_seconds": (
                (log.finished_at - log.started_at).total_seconds()
                if log.finished_at else None
            ),
        }
        for log, company in logs_result.all()
    ]

    return {
        "id": str(run.id),
        "triggered_by": run.triggered_by,
        "status": run.status,
        "companies_checked": run.companies_checked,
        "jobs_found": run.jobs_found,
        "new_jobs_found": run.new_jobs_found,
        "matches_found": run.matches_found,
        "alerts_sent": run.alerts_sent,
        "error_count": run.error_count,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "check_logs": check_logs,
    }


@router.get("/errors")
async def list_recent_errors(
    limit: int        = 50,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    """Recent source errors for the user's companies."""
    result = await db.execute(
        select(SourceError, Company)
        .join(Company, Company.id == SourceError.company_id)
        .where(Company.user_id == user.id)
        .order_by(desc(SourceError.occurred_at))
        .limit(limit)
    )
    return [
        {
            "id": str(err.id),
            "company_name": company.name,
            "error_type": err.error_type,
            "error_message": err.error_message,
            "source_url": err.source_url,
            "http_status": err.http_status,
            "occurred_at": err.occurred_at.isoformat(),
        }
        for err, company in result.all()
    ]


# ── Background helpers ────────────────────────────────────────────────────────

async def _background_full_run(run_id, user_id):
    from app.database import AsyncSessionLocal
    from app.services.ingestion.runner import run_full_ingestion
    async with AsyncSessionLocal() as db:
        try:
            await run_full_ingestion(db, triggered_by=f"manual:{user_id}")
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Background full ingestion run failed"
            )


async def _background_company_run(company_id):
    from app.database import AsyncSessionLocal
    from app.services.ingestion.runner import run_single_company
    async with AsyncSessionLocal() as db:
        try:
            await run_single_company(company_id, db, triggered_by="manual")
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Background company run failed for %s", company_id
            )
