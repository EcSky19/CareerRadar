from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from enum import Enum

from app.database import get_db
from app.auth import get_current_user, CurrentUser
from app.models import TargetProfile, TargetProfileCategoryFilter, TargetProfileCompanyFilter

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class RoleType(str, Enum):
    internship = "internship"
    new_grad   = "new_grad"
    full_time  = "full_time"
    coop       = "coop"
    contract   = "contract"

class RemotePref(str, Enum):
    remote = "remote"; hybrid = "hybrid"; onsite = "onsite"; any = "any"

class SearchMode(str, Enum):
    strict_software_ai      = "strict_software_ai"
    balanced                = "balanced"
    finance_tech_balanced   = "finance_tech_balanced"
    finance_broad           = "finance_broad"
    investment_only         = "investment_only"
    broad                   = "broad"

class CategoryFilter(BaseModel):
    category_id: UUID
    filter_type: str   # "included" | "excluded"

class CompanyFilter(BaseModel):
    company_id: UUID
    filter_type: str

class TargetProfileCreate(BaseModel):
    name: str
    desired_titles: List[str] = []
    desired_keywords: List[str] = []
    desired_locations: List[str] = []
    excluded_keywords: List[str] = []
    role_types: List[RoleType] = []
    remote_preference: RemotePref = RemotePref.any
    minimum_match_score: int = 70
    search_mode: SearchMode = SearchMode.balanced
    alerts_enabled: bool = True
    category_filters: List[CategoryFilter] = []
    company_filters: List[CompanyFilter] = []

class TargetProfileUpdate(BaseModel):
    name: Optional[str] = None
    desired_titles: Optional[List[str]] = None
    desired_keywords: Optional[List[str]] = None
    desired_locations: Optional[List[str]] = None
    excluded_keywords: Optional[List[str]] = None
    role_types: Optional[List[RoleType]] = None
    remote_preference: Optional[RemotePref] = None
    minimum_match_score: Optional[int] = None
    search_mode: Optional[SearchMode] = None
    alerts_enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    category_filters: Optional[List[CategoryFilter]] = None
    company_filters: Optional[List[CompanyFilter]] = None

class TargetProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    desired_titles: List[str]
    desired_keywords: List[str]
    desired_locations: List[str]
    excluded_keywords: List[str]
    role_types: List[str]
    remote_preference: str
    minimum_match_score: int
    search_mode: str
    alerts_enabled: bool
    is_active: bool
    category_filters: List[dict] = []
    company_filters: List[dict] = []
    created_at: object
    updated_at: object

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_profile_or_404(profile_id: UUID, user: CurrentUser, db: AsyncSession) -> TargetProfile:
    result = await db.execute(
        select(TargetProfile)
        .where(TargetProfile.id == profile_id, TargetProfile.user_id == user.id)
        .options(
            selectinload(TargetProfile.category_filters),
            selectinload(TargetProfile.company_filters),
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Target profile not found")
    return p


async def _sync_filters(profile: TargetProfile, payload, db: AsyncSession):
    if payload.category_filters is not None:
        await db.execute(
            delete(TargetProfileCategoryFilter).where(
                TargetProfileCategoryFilter.profile_id == profile.id
            )
        )
        for f in payload.category_filters:
            db.add(TargetProfileCategoryFilter(
                profile_id=profile.id,
                category_id=f.category_id,
                filter_type=f.filter_type,
            ))

    if payload.company_filters is not None:
        await db.execute(
            delete(TargetProfileCompanyFilter).where(
                TargetProfileCompanyFilter.profile_id == profile.id
            )
        )
        for f in payload.company_filters:
            db.add(TargetProfileCompanyFilter(
                profile_id=profile.id,
                company_id=f.company_id,
                filter_type=f.filter_type,
            ))


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: TargetProfileCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = TargetProfile(
        user_id=user.id,
        name=payload.name,
        desired_titles=payload.desired_titles,
        desired_keywords=payload.desired_keywords,
        desired_locations=payload.desired_locations,
        excluded_keywords=payload.excluded_keywords,
        role_types=[r.value for r in payload.role_types],
        remote_preference=payload.remote_preference.value,
        minimum_match_score=payload.minimum_match_score,
        search_mode=payload.search_mode.value,
        alerts_enabled=payload.alerts_enabled,
    )
    db.add(profile)
    await db.flush()
    await _sync_filters(profile, payload, db)
    await db.commit()
    return await _get_profile_or_404(profile.id, user, db)


@router.get("", response_model=List[TargetProfileResponse])
async def list_profiles(
    active_only: bool = True,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(TargetProfile)
        .where(TargetProfile.user_id == user.id)
        .options(
            selectinload(TargetProfile.category_filters),
            selectinload(TargetProfile.company_filters),
        )
        .order_by(TargetProfile.name)
    )
    if active_only:
        q = q.where(TargetProfile.is_active == True)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{profile_id}")
async def get_profile(
    profile_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_profile_or_404(profile_id, user, db)


@router.patch("/{profile_id}")
async def update_profile(
    profile_id: UUID,
    payload: TargetProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile_or_404(profile_id, user, db)
    update_data = payload.model_dump(
        exclude_none=True,
        exclude={"category_filters", "company_filters"}
    )
    for field, value in update_data.items():
        if field == "role_types":
            value = [r.value if hasattr(r, "value") else r for r in value]
        elif hasattr(value, "value"):
            value = value.value
        setattr(profile, field, value)

    await _sync_filters(profile, payload, db)
    await db.commit()
    return await _get_profile_or_404(profile_id, user, db)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile_or_404(profile_id, user, db)
    await db.delete(profile)
    await db.commit()


@router.post("/{profile_id}/duplicate")
async def duplicate_profile(
    profile_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    source = await _get_profile_or_404(profile_id, user, db)
    copy = TargetProfile(
        user_id=user.id,
        name=f"{source.name} (Copy)",
        desired_titles=list(source.desired_titles),
        desired_keywords=list(source.desired_keywords),
        desired_locations=list(source.desired_locations),
        excluded_keywords=list(source.excluded_keywords),
        role_types=list(source.role_types),
        remote_preference=source.remote_preference,
        minimum_match_score=source.minimum_match_score,
        search_mode=source.search_mode,
        alerts_enabled=source.alerts_enabled,
    )
    db.add(copy)
    await db.commit()
    return await _get_profile_or_404(copy.id, user, db)
