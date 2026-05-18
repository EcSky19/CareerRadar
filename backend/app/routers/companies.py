from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from app.database import get_db
from app.auth import get_current_user, CurrentUser
from app.models import Company, CompanyCategoryAssignment, CompanyCategory
from app.schemas.company import (
    CompanyCreate, CompanyUpdate, CompanyResponse,
    ATSDetectRequest, ATSDetectResponse
)
from app.services.ingestion.ats_detector import detect_ats_provider

router = APIRouter()

# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_company_or_404(
    company_id: UUID,
    user: CurrentUser,
    db: AsyncSession,
) -> Company:
    result = await db.execute(
        select(Company)
        .where(Company.id == company_id, Company.user_id == user.id)
        .options(selectinload(Company.category_assignments).selectinload(
            CompanyCategoryAssignment.category))
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


def _build_response(company: Company) -> CompanyResponse:
    from app.schemas.company import CategoryBrief
    cats = [
        CategoryBrief(id=a.category.id, slug=a.category.slug, name=a.category.name)
        for a in company.category_assignments
        if a.category is not None
    ]
    data = CompanyResponse.model_validate(company)
    data.categories = cats
    return data


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = Company(
        user_id=user.id,
        name=payload.name,
        domain=payload.domain,
        careers_url=payload.careers_url,
        ats_provider=payload.ats_provider.value,
        ats_slug=payload.ats_slug,
        source_url=payload.source_url,
        priority=payload.priority.value,
        notes=payload.notes,
    )
    db.add(company)
    await db.flush()   # get company.id before category assignments

    for cat_id in payload.category_ids:
        db.add(CompanyCategoryAssignment(company_id=company.id, category_id=cat_id))

    await db.commit()
    await db.refresh(company)

    # Reload with categories
    return await _get_company_or_404(company.id, user, db)


@router.get("", response_model=List[CompanyResponse])
async def list_companies(
    active_only: bool = False,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Company)
        .where(Company.user_id == user.id)
        .options(selectinload(Company.category_assignments).selectinload(
            CompanyCategoryAssignment.category))
        .order_by(Company.name)
    )
    if active_only:
        q = q.where(Company.is_active == True)

    result = await db.execute(q)
    companies = result.scalars().all()
    return [_build_response(c) for c in companies]


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return _build_response(await _get_company_or_404(company_id, user, db))


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company_or_404(company_id, user, db)

    for field, value in payload.model_dump(exclude_none=True, exclude={"category_ids"}).items():
        if hasattr(company, field):
            setattr(company, field, value.value if hasattr(value, "value") else value)

    if payload.category_ids is not None:
        await db.execute(
            delete(CompanyCategoryAssignment).where(
                CompanyCategoryAssignment.company_id == company_id
            )
        )
        for cat_id in payload.category_ids:
            db.add(CompanyCategoryAssignment(company_id=company.id, category_id=cat_id))

    await db.commit()
    return _build_response(await _get_company_or_404(company_id, user, db))


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company_or_404(company_id, user, db)
    await db.delete(company)
    await db.commit()


@router.post("/{company_id}/pause", response_model=CompanyResponse)
async def pause_company(
    company_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company_or_404(company_id, user, db)
    company.is_active = False
    await db.commit()
    return _build_response(await _get_company_or_404(company_id, user, db))


@router.post("/{company_id}/activate", response_model=CompanyResponse)
async def activate_company(
    company_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company_or_404(company_id, user, db)
    company.is_active = True
    company.last_error = None
    company.consecutive_errors = 0
    await db.commit()
    return _build_response(await _get_company_or_404(company_id, user, db))


@router.post("/{company_id}/test")
async def test_company_source(
    company_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run a one-off ingestion check for this company and return a job count.
    Does NOT persist results or send alerts.
    """
    from app.services.ingestion.runner import ingest_one_company_preview
    company = await _get_company_or_404(company_id, user, db)
    result = await ingest_one_company_preview(company)
    return result


@router.post("/detect-ats", response_model=ATSDetectResponse)
async def detect_ats(
    payload: ATSDetectRequest,
    user: CurrentUser = Depends(get_current_user),
):
    return await detect_ats_provider(payload.careers_url, payload.company_name)


# ── Company categories (read-only reference data) ─────────────────────────────

@router.get("/categories/all")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CompanyCategory).order_by(CompanyCategory.sort_order)
    )
    return result.scalars().all()
