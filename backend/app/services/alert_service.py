"""
Alert Service
=============
Sends email alerts for new job matches.
Deduplicated at the DB level via UNIQUE (job_match_id, channel).

MVP: Email only via Resend.
Future: SMS (Twilio), Slack webhooks, Discord webhooks.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import get_settings
from app.models import Alert, JobMatch, User, Job, TargetProfile

logger = logging.getLogger(__name__)
settings = get_settings()


class AlertService:

    @staticmethod
    async def send_job_alert(
        job_match_id: UUID,
        job,             # Job ORM instance
        match,           # MatchResult dataclass
        profile,         # TargetProfile ORM instance
        db: AsyncSession,
    ) -> bool:
        """
        Send an email alert for a job match and record it in the alerts table.
        Returns True if the alert was sent successfully.
        """
        # Fetch user's alert email
        user_result = await db.execute(
            select(User).where(User.id == profile.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return False

        recipient_email = user.alert_email or user.email

        subject = f"New Job Match: {job.title} at {job.company_name}"
        body = AlertService._build_email_body(job, match, profile)

        # Insert alert row — will silently skip if (job_match_id, email) already exists
        stmt = (
            pg_insert(Alert)
            .values(
                user_id=profile.user_id,
                job_match_id=job_match_id,
                channel="email",
                recipient=recipient_email,
                subject=subject,
                body=body,
                status="pending",
            )
            .on_conflict_do_nothing(constraint="alert_match_channel_unique")
            .returning(Alert.id)
        )
        row = (await db.execute(stmt)).fetchone()
        if not row:
            # Already sent — dedup worked
            return False

        alert_id = row[0]

        # Send via Resend
        success, error_msg = await AlertService._send_via_resend(
            to=recipient_email, subject=subject, html=body
        )

        # Update alert status
        await db.execute(
            __import__("sqlalchemy").update(Alert)
            .where(Alert.id == alert_id)
            .values(
                status="sent" if success else "failed",
                sent_at=datetime.now(timezone.utc) if success else None,
                error_message=None if success else error_msg,
            )
        )

        # Mark job_match as alert_sent
        if success:
            await db.execute(
                __import__("sqlalchemy").update(JobMatch)
                .where(JobMatch.id == job_match_id)
                .values(alert_sent=True, alert_sent_at=datetime.now(timezone.utc))
            )

        return success

    @staticmethod
    def _build_email_body(job, match, profile) -> str:
        location_str = job.location or "Location not specified"
        score        = match.match_score
        terms        = ", ".join(match.matched_title_terms + match.matched_keywords)[:120]
        detected     = datetime.now(timezone.utc).strftime("%B %d, %Y")

        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f9fafb; margin: 0; padding: 20px; }}
    .card {{ background: white; border-radius: 8px; padding: 32px;
             max-width: 560px; margin: 0 auto;
             border: 1px solid #e5e7eb; }}
    .header {{ color: #111827; font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
    .sub {{ color: #6b7280; font-size: 14px; margin-bottom: 24px; }}
    .field {{ margin-bottom: 12px; }}
    .label {{ font-size: 12px; color: #9ca3af; text-transform: uppercase;
              letter-spacing: 0.05em; margin-bottom: 2px; }}
    .value {{ font-size: 15px; color: #111827; font-weight: 500; }}
    .score {{ display: inline-block; background: #ecfdf5; color: #059669;
              border-radius: 9999px; padding: 4px 12px;
              font-size: 13px; font-weight: 600; }}
    .btn {{ display: inline-block; background: #2563eb; color: white;
            text-decoration: none; padding: 12px 24px; border-radius: 6px;
            font-weight: 600; font-size: 15px; margin-top: 20px; }}
    .footer {{ color: #9ca3af; font-size: 12px; margin-top: 24px;
               text-align: center; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">New Job Match Found</div>
    <div class="sub">A new role matched your <strong>{profile.name}</strong> profile.</div>

    <div class="field">
      <div class="label">Company</div>
      <div class="value">{job.company_name}</div>
    </div>
    <div class="field">
      <div class="label">Title</div>
      <div class="value">{job.title}</div>
    </div>
    <div class="field">
      <div class="label">Location</div>
      <div class="value">{location_str}</div>
    </div>
    <div class="field">
      <div class="label">Match Score</div>
      <div class="value"><span class="score">{score}/100</span></div>
    </div>
    <div class="field">
      <div class="label">Matched On</div>
      <div class="value" style="font-size:13px;color:#6b7280;">{terms or 'See dashboard for details'}</div>
    </div>
    <div class="field">
      <div class="label">Detected</div>
      <div class="value">{detected}</div>
    </div>

    <a href="{job.application_url}" class="btn">Apply Now →</a>

    <div class="footer">
      Personal Job Hunter &nbsp;·&nbsp;
      <a href="https://personaljobhunter.app/settings" style="color:#9ca3af;">
        Manage alerts
      </a>
    </div>
  </div>
</body>
</html>"""

    @staticmethod
    async def _send_via_resend(
        to: str,
        subject: str,
        html: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Send an email via the Resend API.
        Returns (success, error_message).
        """
        api_key = settings.resend_api_key
        if not api_key:
            logger.warning("RESEND_API_KEY not set — email not sent to %s", to)
            return False, "RESEND_API_KEY not configured"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": f"{settings.alert_from_name} <{settings.alert_from_email}>",
                        "to": [to],
                        "subject": subject,
                        "html": html,
                    },
                )
            if resp.status_code in (200, 201):
                logger.info("Alert email sent to %s: %s", to, subject)
                return True, None
            else:
                error = resp.text[:200]
                logger.error("Resend error %d: %s", resp.status_code, error)
                return False, f"HTTP {resp.status_code}: {error}"
        except httpx.RequestError as exc:
            logger.error("Resend network error: %s", exc)
            return False, str(exc)
