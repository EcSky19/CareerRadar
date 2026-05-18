"""alerts.py — Alert history and settings router"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update
from uuid import UUID
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user, CurrentUser
from app.models import Alert, User

router = APIRouter()


@router.get("")
async def list_alerts(
    limit: int        = 50,
    channel: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    q = (
        select(Alert)
        .where(Alert.user_id == user.id)
        .order_by(desc(Alert.created_at))
        .limit(limit)
    )
    if channel:
        q = q.where(Alert.channel == channel)

    result = await db.execute(q)
    alerts = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "channel": a.channel,
            "recipient": a.recipient,
            "subject": a.subject,
            "status": a.status,
            "sent_at": a.sent_at.isoformat() if a.sent_at else None,
            "error_message": a.error_message,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


@router.get("/stats")
async def alert_stats(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    from sqlalchemy import func
    total = await db.scalar(select(func.count()).where(Alert.user_id == user.id))
    sent  = await db.scalar(select(func.count()).where(
        Alert.user_id == user.id, Alert.status == "sent"
    ))
    failed = await db.scalar(select(func.count()).where(
        Alert.user_id == user.id, Alert.status == "failed"
    ))
    return {"total": total or 0, "sent": sent or 0, "failed": failed or 0}
