from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class ATSProvider(str, Enum):
    greenhouse       = "greenhouse"
    lever            = "lever"
    ashby            = "ashby"
    workday          = "workday"
    icims            = "icims"
    smartrecruiters  = "smartrecruiters"
    oracle_recruiting= "oracle_recruiting"
    sap_successfactors="sap_successfactors"
    custom_html      = "custom_html"
    unknown          = "unknown"


class CompanyPriority(str, Enum):
    high   = "high"
    medium = "medium"
    low    = "low"


# ── Request schemas ────────────────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    careers_url: Optional[str] = None
    ats_provider: ATSProvider = ATSProvider.unknown
    ats_slug: Optional[str] = None
    source_url: Optional[str] = None
    priority: CompanyPriority = CompanyPriority.medium
    notes: Optional[str] = None
    category_ids: List[UUID] = []

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Company name cannot be empty")
        return v.strip()


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    careers_url: Optional[str] = None
    ats_provider: Optional[ATSProvider] = None
    ats_slug: Optional[str] = None
    source_url: Optional[str] = None
    priority: Optional[CompanyPriority] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    category_ids: Optional[List[UUID]] = None


class ATSDetectRequest(BaseModel):
    careers_url: str
    company_name: Optional[str] = None


# ── Response schemas ───────────────────────────────────────────────────────────

class CategoryBrief(BaseModel):
    id: UUID
    slug: str
    name: str

    model_config = {"from_attributes": True}


class CompanyResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    domain: Optional[str]
    careers_url: Optional[str]
    ats_provider: ATSProvider
    ats_slug: Optional[str]
    source_url: Optional[str]
    ats_detection_confidence: Optional[float]
    ats_detection_warning: Optional[str]
    priority: CompanyPriority
    is_active: bool
    notes: Optional[str]
    last_checked_at: Optional[datetime]
    last_successful_check_at: Optional[datetime]
    last_error: Optional[str]
    consecutive_errors: int
    total_jobs_found: int
    total_matching_jobs: int
    categories: List[CategoryBrief] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ATSDetectResponse(BaseModel):
    provider_name: ATSProvider
    confidence_score: float
    detected_source_url: Optional[str]
    required_slug_or_token: Optional[str]
    warning_message: Optional[str]
