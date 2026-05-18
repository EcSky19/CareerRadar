from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from uuid import UUID

from app.database import get_db
from app.auth import get_current_user, CurrentUser
from app.models import User

router = APIRouter()


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    graduation_year: Optional[int] = None
    school: Optional[str] = None
    major: Optional[str] = None
    minor: Optional[str] = None
    preferred_locations: Optional[List[str]] = None
    alert_email: Optional[str] = None
    alert_frequency: Optional[str] = None
    minimum_match_score: Optional[int] = None
    notifications_enabled: Optional[bool] = None


@router.get("/me")
async def get_current_user_profile(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user.id))
    u = result.scalar_one_or_none()

    if not u:
        # First login — auto-create user row
        u = User(id=user.id, email=user.email)
        db.add(u)
        await db.commit()

    return {
        "id": str(u.id),
        "email": u.email,
        "full_name": u.full_name,
        "graduation_year": u.graduation_year,
        "school": u.school,
        "major": u.major,
        "minor": u.minor,
        "preferred_locations": u.preferred_locations,
        "alert_email": u.alert_email,
        "alert_frequency": u.alert_frequency,
        "minimum_match_score": u.minimum_match_score,
        "notifications_enabled": u.notifications_enabled,
        "created_at": u.created_at.isoformat(),
    }


@router.patch("/me")
async def update_user_profile(
    payload: UserUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession  = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user.id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(u, field, value)

    await db.commit()
    return {"status": "updated"}
