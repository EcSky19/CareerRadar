"""
Scheduler
=========
Runs the daily ingestion pipeline.

MVP trigger options (choose one):
  A) GitHub Actions cron  →  calls POST /api/v1/ingestion/run with service key
  B) Vercel Cron          →  same HTTP call, authenticated via CRON_SECRET header
  C) APScheduler          →  in-process scheduler, runs inside the FastAPI worker

This module provides the APScheduler variant (option C) as a drop-in for
development and small deployments. For production, GitHub Actions is preferred
because it keeps the scheduler outside the API process and gives you free logs.

GitHub Actions cron example (.github/workflows/daily_ingest.yml):
  schedule:
    - cron: '0 6 * * *'   # 6am UTC = ~2am ET / ~11pm PT
  steps:
    - run: |
        curl -X POST https://your-api.render.com/api/v1/ingestion/run \
          -H "Authorization: Bearer ${{ secrets.SERVICE_ROLE_KEY }}" \
          -H "X-Cron-Secret: ${{ secrets.CRON_SECRET }}"
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import AsyncSessionLocal
from app.services.ingestion.runner import run_full_ingestion

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def start_scheduler(cron_hour: int = 6, cron_minute: int = 0):
    """
    Start the in-process APScheduler.
    Call this from the FastAPI lifespan event if using in-process scheduling.

    cron_hour / cron_minute: UTC time to run the daily ingestion.
    """
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _daily_ingestion_job,
        trigger=CronTrigger(hour=cron_hour, minute=cron_minute),
        id="daily_ingestion",
        name="Daily job ingestion",
        replace_existing=True,
        misfire_grace_time=3600,  # run even if missed by up to 1 hour
    )
    _scheduler.start()
    logger.info(
        "Scheduler started — daily ingestion at %02d:%02d UTC",
        cron_hour, cron_minute
    )


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")


async def _daily_ingestion_job():
    """The actual async task executed by APScheduler."""
    logger.info("Daily ingestion job starting at %s UTC", datetime.now(timezone.utc))
    async with AsyncSessionLocal() as db:
        try:
            run = await run_full_ingestion(db, triggered_by="scheduler")
            logger.info(
                "Daily ingestion completed: %d companies / %d new jobs / %d matches / %d alerts",
                run.companies_checked,
                run.new_jobs_found,
                run.matches_found,
                run.alerts_sent,
            )
        except Exception as exc:
            logger.exception("Daily ingestion job failed: %s", exc)
