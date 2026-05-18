"""
Ingestion Runner
================
Orchestrates the full ingestion pipeline for one or all companies.

Pipeline per company:
  1. Select adapter by ats_provider
  2. Fetch jobs from adapter
  3. Normalise job data (role_type inference, title normalisation)
  4. Upsert jobs (dedup by external_job_id; close missing jobs)
  5. Run matching engine against all user's active profiles
  6. Upsert job_match records
  7. Enqueue alerts for new high-score matches
  8. Update company counters and log results
"""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from app.models import (
    Company, Job, JobMatch, IngestionRun, CompanyCheckLog,
    SourceError, TargetProfile, CompanyCategoryAssignment,
)
from app.services.ingestion.base import (
    NormalizedJob, AdapterError, AdapterEmpty, AdapterNotFound, AdapterRateLimited
)
from app.services.ingestion.greenhouse import GreenhouseAdapter
from app.services.ingestion.lever import LeverAdapter
from app.services.ingestion.ashby import AshbyAdapter
from app.services.ingestion.html_adapter import GenericHTMLAdapter
from app.services.matching.engine import MatchingEngine
from app.services.matching.taxonomy import normalise_title_cached, infer_role_type
from app.services.alert_service import AlertService

logger = logging.getLogger(__name__)

# Days after which a possibly_closed job is marked fully closed
CLOSE_AFTER_DAYS = 3

_ADAPTERS = {
    "greenhouse":   GreenhouseAdapter(),
    "lever":        LeverAdapter(),
    "ashby":        AshbyAdapter(),
    "custom_html":  GenericHTMLAdapter(),
    "unknown":      GenericHTMLAdapter(),
}

_matching_engine = MatchingEngine()


# =============================================================================
# PUBLIC ENTRY POINTS
# =============================================================================

async def run_full_ingestion(
    db: AsyncSession,
    triggered_by: str = "scheduler",
) -> IngestionRun:
    """Check all active companies across all users."""
    run = IngestionRun(triggered_by=triggered_by, status="running")
    db.add(run)
    await db.commit()

    result = await db.execute(
        select(Company).where(Company.is_active == True)
    )
    companies = result.scalars().all()

    for company in companies:
        await _ingest_company(company, run, db)

    run.status = "completed_with_errors" if run.error_count > 0 else "completed"
    run.finished_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info(
        "Ingestion run complete: %d companies, %d new jobs, %d matches, %d alerts",
        run.companies_checked, run.new_jobs_found, run.matches_found, run.alerts_sent
    )
    return run


async def run_single_company(
    company_id: UUID,
    db: AsyncSession,
    triggered_by: str = "manual",
) -> CompanyCheckLog:
    """Check a single company. Creates an ingestion run just for it."""
    run = IngestionRun(triggered_by=triggered_by, status="running")
    db.add(run)
    await db.commit()

    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise ValueError(f"Company {company_id} not found")

    check_log = await _ingest_company(company, run, db)

    run.status = "completed_with_errors" if run.error_count > 0 else "completed"
    run.finished_at = datetime.now(timezone.utc)
    await db.commit()
    return check_log


async def ingest_one_company_preview(company) -> dict:
    """
    Dry-run for a single company — fetch jobs but don't persist.
    Returns a summary dict for the /test endpoint.
    """
    adapter = _ADAPTERS.get(company.ats_provider, _ADAPTERS["unknown"])
    try:
        jobs = await adapter.fetch_jobs(company)
        return {
            "status": "success",
            "jobs_found": len(jobs),
            "sample_titles": [j.title for j in jobs[:5]],
            "ats_provider": company.ats_provider,
            "source_url": company.source_url or company.careers_url,
        }
    except AdapterEmpty:
        return {"status": "empty", "jobs_found": 0, "message": "No open jobs found"}
    except AdapterError as exc:
        return {"status": "error", "jobs_found": 0, "error": str(exc)}
    except Exception as exc:
        return {"status": "error", "jobs_found": 0, "error": f"Unexpected: {exc}"}


# =============================================================================
# INTERNAL PER-COMPANY PIPELINE
# =============================================================================

async def _ingest_company(
    company: Company,
    run: IngestionRun,
    db: AsyncSession,
) -> CompanyCheckLog:
    now = datetime.now(timezone.utc)

    check_log = CompanyCheckLog(
        ingestion_run_id=run.id,
        company_id=company.id,
        status="success",
        started_at=now,
    )
    db.add(check_log)
    await db.flush()

    try:
        # 1. Select adapter
        adapter = _ADAPTERS.get(company.ats_provider, _ADAPTERS["unknown"])

        # 2. Fetch
        try:
            raw_jobs = await adapter.fetch_jobs(company)
        except AdapterEmpty:
            raw_jobs = []
        except (AdapterNotFound, AdapterRateLimited, AdapterError) as exc:
            await _record_error(company, check_log, exc, db)
            check_log.status = "failed"
            check_log.error_message = str(exc)
            check_log.finished_at = datetime.now(timezone.utc)
            company.last_error = str(exc)
            company.consecutive_errors += 1
            company.last_checked_at = now
            run.error_count += 1
            run.companies_checked += 1
            await db.commit()
            return check_log

        # 3. Upsert jobs and count new ones
        new_jobs, total_jobs = await _upsert_jobs(raw_jobs, company, db)

        # 4. Mark disappeared jobs as possibly_closed
        await _close_missing_jobs(raw_jobs, company, db)

        # 5. Run matching for all user profiles
        new_matches, alerts_sent = await _run_matching_for_new_jobs(
            new_jobs, company, db
        )

        # 6. Update company stats
        company.last_checked_at = now
        company.last_successful_check_at = now
        company.last_error = None
        company.consecutive_errors = 0
        company.total_jobs_found = (company.total_jobs_found or 0) + len(new_jobs)

        # 7. Update check log
        check_log.status = "success"
        check_log.jobs_found = total_jobs
        check_log.new_jobs_found = len(new_jobs)
        check_log.matches_found = new_matches
        check_log.finished_at = datetime.now(timezone.utc)

        # 8. Update run counters
        run.companies_checked += 1
        run.jobs_found += total_jobs
        run.new_jobs_found += len(new_jobs)
        run.matches_found += new_matches
        run.alerts_sent += alerts_sent

        await db.commit()
        logger.info(
            "[%s] %d total / %d new / %d matches / %d alerts",
            company.name, total_jobs, len(new_jobs), new_matches, alerts_sent
        )

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Unexpected error for company %s: %s\n%s", company.name, exc, tb)
        check_log.status = "failed"
        check_log.error_message = f"Unexpected: {exc}"
        check_log.finished_at = datetime.now(timezone.utc)
        company.last_error = str(exc)
        company.consecutive_errors += 1
        run.error_count += 1
        run.companies_checked += 1
        await db.commit()

    return check_log


# =============================================================================
# JOB UPSERT + DEDUPLICATION
# =============================================================================

async def _upsert_jobs(
    raw_jobs: list[NormalizedJob],
    company: Company,
    db: AsyncSession,
) -> tuple[list[Job], int]:
    """
    Insert new jobs; update existing ones.
    Returns (new_job_orm_objects, total_job_count).
    """
    new_jobs = []
    now = datetime.now(timezone.utc)

    for nj in raw_jobs:
        norm_title = normalise_title_cached(nj.title)
        inferred_role = nj.role_type or infer_role_type(nj.title, nj.description or "")

        # Build the "on conflict update" payload
        on_conflict_set = {
            "last_seen_at": now,
            "status": "open",
        }
        if nj.description:
            on_conflict_set["description"] = nj.description

        stmt = (
            pg_insert(Job)
            .values(
                company_id=company.id,
                external_job_id=nj.external_job_id or _synthetic_id(nj),
                company_name=company.name,
                title=nj.title,
                normalized_title=norm_title,
                location=nj.location,
                is_remote=nj.is_remote,
                department=nj.department,
                employment_type=nj.employment_type,
                role_type=inferred_role,
                description=nj.description,
                application_url=nj.application_url,
                source_url=nj.source_url,
                ats_provider=nj.ats_provider,
                posted_at=nj.posted_at,
                first_seen_at=now,
                last_seen_at=now,
                status="open",
                raw_data=nj.raw_data,
            )
            .on_conflict_do_update(
                constraint="jobs_company_external_id_unique",
                set_=on_conflict_set,
            )
            .returning(Job.id, Job.first_seen_at, Job.created_at)
        )

        row = (await db.execute(stmt)).fetchone()
        if row and row.first_seen_at == row.created_at:
            # first_seen == created → brand new job
            result = await db.execute(select(Job).where(Job.id == row[0]))
            job = result.scalar_one_or_none()
            if job:
                new_jobs.append(job)

    return new_jobs, len(raw_jobs)


def _synthetic_id(nj: NormalizedJob) -> str:
    """
    Fallback dedup key when the ATS does not provide a stable external ID.
    Uses a slug of title + location.
    """
    import hashlib
    slug = f"{nj.title}|{nj.location or ''}|{nj.application_url}"
    return hashlib.sha1(slug.encode()).hexdigest()[:20]


async def _close_missing_jobs(
    current_jobs: list[NormalizedJob],
    company: Company,
    db: AsyncSession,
):
    """Mark jobs no longer in the feed as possibly_closed or closed."""
    if not current_jobs:
        return

    current_ids = {nj.external_job_id for nj in current_jobs if nj.external_job_id}
    if not current_ids:
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=CLOSE_AFTER_DAYS)

    await db.execute(
        update(Job)
        .where(
            Job.company_id == company.id,
            Job.status == "open",
            Job.external_job_id.notin_(current_ids),
            Job.last_seen_at < cutoff,
        )
        .values(status="possibly_closed")
    )

    # Promote possibly_closed → closed after another cycle
    await db.execute(
        update(Job)
        .where(
            Job.company_id == company.id,
            Job.status == "possibly_closed",
            Job.external_job_id.notin_(current_ids),
        )
        .values(status="closed")
    )


# =============================================================================
# MATCHING PIPELINE FOR NEW JOBS
# =============================================================================

async def _run_matching_for_new_jobs(
    new_jobs: list[Job],
    company: Company,
    db: AsyncSession,
) -> tuple[int, int]:
    """
    Run the matching engine for each new job against all active profiles
    owned by the company's user.

    Returns (total_matches, total_alerts_sent).
    """
    if not new_jobs:
        return 0, 0

    # Fetch user's active profiles
    profile_result = await db.execute(
        select(TargetProfile)
        .where(
            TargetProfile.user_id == company.user_id,
            TargetProfile.is_active == True,
        )
        .options(
            selectinload(TargetProfile.category_filters),
            selectinload(TargetProfile.company_filters),
        )
    )
    profiles = profile_result.scalars().all()
    if not profiles:
        return 0, 0

    # Fetch company category slugs
    cat_result = await db.execute(
        select(CompanyCategoryAssignment)
        .where(CompanyCategoryAssignment.company_id == company.id)
        .options(selectinload(CompanyCategoryAssignment.category))
    )
    category_slugs = [
        a.category.slug for a in cat_result.scalars().all() if a.category
    ]

    total_matches = 0
    total_alerts = 0

    for job in new_jobs:
        for profile in profiles:
            # Check per-profile company exclusion
            excluded_company_ids = {
                str(f.company_id)
                for f in profile.company_filters
                if f.filter_type == "excluded"
            }
            if str(company.id) in excluded_company_ids:
                continue

            match_result = _matching_engine.score(job, profile, company, category_slugs)

            # Upsert job_match
            match_stmt = (
                pg_insert(JobMatch)
                .values(
                    user_id=profile.user_id,
                    job_id=job.id,
                    target_profile_id=profile.id,
                    match_score=match_result.match_score,
                    title_score=match_result.title_score,
                    role_type_score=match_result.role_type_score,
                    location_score=match_result.location_score,
                    keyword_score=match_result.keyword_score,
                    category_score=match_result.category_score,
                    domain_score=match_result.domain_score,
                    priority_score=match_result.priority_score,
                    freshness_score=match_result.freshness_score,
                    campus_score=match_result.campus_score,
                    matched_title_terms=match_result.matched_title_terms,
                    matched_keywords=match_result.matched_keywords,
                    matched_location_terms=match_result.matched_location_terms,
                    matched_company_categories=match_result.matched_company_categories,
                    excluded_terms_found=match_result.excluded_terms_found,
                    technical_signals_found=match_result.technical_signals_found,
                    domain_signals_found=match_result.domain_signals_found,
                    match_reason=match_result.match_reason,
                    should_alert=match_result.should_alert,
                    alert_sent=False,
                )
                .on_conflict_do_update(
                    constraint="job_match_unique",
                    set_={
                        "match_score": match_result.match_score,
                        "match_reason": match_result.match_reason,
                        "should_alert": match_result.should_alert,
                    },
                )
                .returning(JobMatch.id, JobMatch.alert_sent, JobMatch.should_alert)
            )
            row = (await db.execute(match_stmt)).fetchone()

            if row and match_result.should_alert:
                total_matches += 1
                job_match_id = row[0]
                already_sent = row[1]
                if not already_sent:
                    sent = await AlertService.send_job_alert(
                        job_match_id=job_match_id,
                        job=job,
                        match=match_result,
                        profile=profile,
                        db=db,
                    )
                    if sent:
                        total_alerts += 1

    await db.commit()
    return total_matches, total_alerts


async def _record_error(company, check_log, exc: Exception, db: AsyncSession):
    db.add(SourceError(
        company_id=company.id,
        check_log_id=check_log.id,
        error_type=type(exc).__name__,
        error_message=str(exc),
        stack_trace=traceback.format_exc(),
        source_url=company.source_url,
        http_status=getattr(exc, "http_status", None),
    ))
